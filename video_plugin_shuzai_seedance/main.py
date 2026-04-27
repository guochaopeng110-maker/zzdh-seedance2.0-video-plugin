# -*- coding: utf-8 -*-
"""
Shuzai Seedance 2.0 视频生成插件
"""

import base64
import collections
import json
import mimetypes
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

import requests
from urllib.parse import urlparse

try:
    from plugin_utils import load_plugin_config, save_plugin_config
except ImportError:

    def load_plugin_config(path):
        return {}

    def save_plugin_config(path, config):
        return None


PLUGIN_ERROR_PREFIX = "PLUGIN_ERROR:::"
_PLUGIN_VERSION = "1.0.1"
_PLUGIN_FILE = __file__
plugin_dir = Path(__file__).parent

_TASK_LOG_DB_PATH = plugin_dir / "video_task_logs.db"
_MANUAL_DOWNLOAD_DIR = plugin_dir / "downloads"
_REQUEST_PAYLOAD_DIR = plugin_dir / "request_payloads"
_RUNTIME_LOG_DIR = plugin_dir / "logs"
_RUNTIME_LOG_FILE_PATH = (
    _RUNTIME_LOG_DIR / f"debug_runtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

_log_buffer = collections.deque(maxlen=2000)
_log_index = 0
_log_lock = threading.Lock()
_db_init_lock = threading.Lock()
_db_initialized = False

_DEFAULT_BASE_URL = "https://openai.shuzaiaigc.com"
_TASK_CREATE_PATH = "/v1/video/generations"
_TASK_QUERY_PATH = "/v1/video/generations/{task_id}"

DEFAULT_MODEL = "doubao-seedance-2-0-260128"
DEFAULT_RESOLUTION = "720p"
DEFAULT_RATIO = "16:9"
DEFAULT_DURATION = 5
DEFAULT_GENERATE_AUDIO = True
DEFAULT_WATERMARK = False
DEFAULT_WEB_SEARCH = False
DEFAULT_TIMEOUT = 900
DEFAULT_MAX_POLL_ATTEMPTS = 300
DEFAULT_POLL_INTERVAL = 15
DEFAULT_INITIAL_POLL_DELAY_SECONDS = 2
CONFIG_SCHEMA_VERSION = 1

DOWNLOAD_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
)
DOWNLOAD_REFERER = f"{_DEFAULT_BASE_URL}/"

SUPPORTED_IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp", ".bmp", ".tiff", ".gif"}
MAX_IMAGE_SIZE_BYTES = 30 * 1024 * 1024
DEFAULT_RESOLUTIONS = ["480p", "720p", "1080p"]
DEFAULT_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
DEFAULT_STANDARD_MODELS = ["doubao-seedance-2-0-260128", "seedance2.0-v", "seedance2.0-t"]
DEFAULT_HD_MODELS = ["seedance2.0-1080-v", "seedance2.0-1080-t"]


class PluginFatalError(Exception):
    def __init__(self, message):
        text = str(message)
        if not text.startswith(PLUGIN_ERROR_PREFIX):
            text = f"{PLUGIN_ERROR_PREFIX}{text}"
        super().__init__(text)


def _mask_api_key(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return f"{text[:2]}***"
    return f"{text[:4]}***{text[-2:]}"


def _sanitize_headers_for_debug(headers):
    safe = {}
    for key, value in (headers or {}).items():
        k = str(key or "")
        v = str(value or "")
        if k.lower() == "authorization":
            parts = v.split(" ", 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                safe[k] = f"Bearer {_mask_api_key(parts[1])}"
            else:
                safe[k] = "***"
        else:
            safe[k] = v
    return safe


def _append_live_log(level, message):
    global _log_index
    with _log_lock:
        _log_index += 1
        _log_buffer.append(
            {
                "index": _log_index,
                "time": datetime.now().strftime("%H:%M:%S"),
                "level": str(level or "INFO"),
                "msg": str(message or ""),
            }
        )


def _append_file_log(level, message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{str(level or 'INFO')}] {str(message or '')}\n"
    try:
        _RUNTIME_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_RUNTIME_LOG_FILE_PATH, "a", encoding="utf-8") as fw:
            fw.write(line)
    except Exception:
        return


def _log_event(event, **fields):
    payload = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "fields": fields or {},
    }
    text = f"[ShuzaiSeedance] {json.dumps(payload, ensure_ascii=False)}"
    print(text)
    _append_live_log("INFO", text)
    _append_file_log("INFO", text)


def get_buffered_logs(since_index=0):
    try:
        since = int(since_index or 0)
    except (TypeError, ValueError):
        since = 0
    with _log_lock:
        return [entry for entry in list(_log_buffer) if entry.get("index", 0) > since]


def _create_task_log_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS video_task_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT,
          updated_at TEXT,
          api_task_id TEXT,
          model_name TEXT,
          model_display TEXT,
          prompt TEXT,
          aspect_ratio TEXT,
          duration TEXT,
          generation_mode TEXT,
          status TEXT,
          error TEXT,
          video_url TEXT,
          local_path TEXT,
          metadata TEXT
        )
        """
    )


def _ensure_task_log_db():
    global _db_initialized
    if _db_initialized:
        return
    with _db_init_lock:
        if _db_initialized:
            return
        conn = sqlite3.connect(str(_TASK_LOG_DB_PATH))
        try:
            _create_task_log_table(conn)
            conn.commit()
            _db_initialized = True
        finally:
            conn.close()


def _db_conn():
    _ensure_task_log_db()
    conn = sqlite3.connect(str(_TASK_LOG_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_task_log_db():
    conn = sqlite3.connect(str(_TASK_LOG_DB_PATH))
    try:
        _create_task_log_table(conn)
        conn.commit()
        global _db_initialized
        _db_initialized = True
    finally:
        conn.close()


def _insert_task_log(entry):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO video_task_logs
            (created_at, updated_at, api_task_id, model_name, model_display, prompt, aspect_ratio,
             duration, generation_mode, status, error, video_url, local_path, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                entry.get("api_task_id"),
                entry.get("model_name"),
                entry.get("model_display"),
                entry.get("prompt"),
                entry.get("aspect_ratio"),
                entry.get("duration"),
                entry.get("generation_mode"),
                entry.get("status"),
                entry.get("error"),
                entry.get("video_url"),
                entry.get("local_path"),
                json.dumps(entry.get("metadata") or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _update_task_log(log_id, **fields):
    if not log_id:
        return
    updates = []
    values = []
    for key, value in fields.items():
        updates.append(f"{key} = ?")
        values.append(value)
    updates.append("updated_at = ?")
    values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    values.append(log_id)
    conn = _db_conn()
    try:
        conn.execute(
            f"UPDATE video_task_logs SET {', '.join(updates)} WHERE id = ?", values
        )
        conn.commit()
    finally:
        conn.close()


def _query_task_logs(limit=200, status=None):
    conn = _db_conn()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM video_task_logs WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM video_task_logs ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _safe_filename(name):
    return "".join(
        ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in str(name or "")
    )


def _persist_request_payload(payload, task_id=None):
    _REQUEST_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = _safe_filename(task_id) if task_id else "pending"
    file_path = _REQUEST_PAYLOAD_DIR / f"request_payload_{stamp}_{suffix}.json"
    with open(file_path, "w", encoding="utf-8") as fw:
        fw.write(json.dumps(payload or {}, ensure_ascii=False, indent=2))
    return str(file_path)


def _manual_download_video(task_row):
    url = task_row.get("video_url")
    if not url:
        return {"id": task_row.get("id"), "status": "manual_failed", "error": "缺少 video_url"}
    _MANUAL_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    base_name = _safe_filename(task_row.get("api_task_id") or f"task_{task_row.get('id')}")
    file_path = _MANUAL_DOWNLOAD_DIR / f"{base_name}.mp4"
    headers = {"User-Agent": DOWNLOAD_USER_AGENT, "Referer": DOWNLOAD_REFERER, "Accept": "*/*"}
    try:
        resp = requests.get(url, headers=headers, timeout=120)
        if resp.status_code != 200:
            raise PluginFatalError(f"下载失败: HTTP {resp.status_code}")
        with open(file_path, "wb") as fw:
            fw.write(resp.content)
        _update_task_log(task_row.get("id"), local_path=str(file_path), status="manual_success")
        return {"id": task_row.get("id"), "status": "manual_success", "path": str(file_path)}
    except Exception as exc:
        _update_task_log(task_row.get("id"), status="manual_failed", error=str(exc))
        return {"id": task_row.get("id"), "status": "manual_failed", "error": str(exc)}

def _safe_progress_callback(progress_callback):
    if callable(progress_callback):
        return progress_callback

    def _noop(_message):
        return None

    return _noop


def _normalize_bool(value, default=False):
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "1", "on", "yes", "enabled"}:
        return True
    if text in {"false", "0", "off", "no", "disabled"}:
        return False
    return bool(default)


def _allowed_models_for_resolution(resolution):
    if str(resolution or "").strip().lower() == "1080p":
        return list(DEFAULT_HD_MODELS)
    return list(DEFAULT_STANDARD_MODELS)


def _normalize_model(value, resolution):
    model = str(value or "").strip()
    allowed_models = _allowed_models_for_resolution(resolution)
    if model in allowed_models:
        return model
    return allowed_models[0]


def _normalize_resolution(value):
    resolution = str(value or "").strip().lower()
    return resolution if resolution in DEFAULT_RESOLUTIONS else DEFAULT_RESOLUTION


def _normalize_ratio(value):
    ratio = str(value or "").strip()
    return ratio if ratio in DEFAULT_RATIOS else DEFAULT_RATIO


def _normalize_duration(value):
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return DEFAULT_DURATION
    if duration < 1:
        return 1
    if duration > 15:
        return 15
    return duration


def _normalize_base_url(url):
    return str(url or "").strip().rstrip("/")


def _validate_image_constraints(image_path):
    if not image_path:
        return
    path_text = str(image_path)
    if path_text.lower().startswith(("http://", "https://", "data:")):
        return
    if not os.path.exists(path_text):
        raise PluginFatalError(f"参考图片不存在: {path_text}")
    ext = os.path.splitext(path_text)[1].lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise PluginFatalError(f"图片格式不支持: {ext or 'unknown'}，支持格式: {allowed}")
    if os.path.getsize(path_text) >= MAX_IMAGE_SIZE_BYTES:
        raise PluginFatalError("图片大小超过 30MB 限制")

def _build_auth_headers(api_key, include_content_type=True):
    key_text = str(api_key or "").strip()
    if not key_text:
        raise PluginFatalError("API Key 未配置")
    headers = {"Authorization": f"Bearer {key_text}"}
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _ensure_success_response(response, operation_name):
    if response.status_code != 200:
        raise PluginFatalError(
            f"{operation_name}??: HTTP {response.status_code} - {response.text}"
        )

def _normalize_list_or_single(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [item for item in value if item]
    if isinstance(value, dict):
        return [
            item for _, item in sorted(value.items(), key=lambda pair: str(pair[0])) if item
        ]
    return [value] if value else []


def _guess_mime_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


def _path_or_url_to_payload_value(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if text.lower().startswith(("http://", "https://", "data:")):
        return text
    if not os.path.exists(text):
        raise PluginFatalError(f"参考图片不存在: {text}")
    with open(text, "rb") as fp:
        encoded = base64.b64encode(fp.read()).decode("utf-8")
    return f"data:{_guess_mime_type(text)};base64,{encoded}"

def _build_create_payload(params, prompt, reference_images=None, reference_videos=None, reference_audios=None):
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        raise PluginFatalError("Prompt 不能为空")

    metadata = {
        "resolution": params["resolution"],
        "ratio": params["ratio"],
        "watermark": bool(params["watermark"]),
        "generate_audio": bool(params["generate_audio"]),
    }
    if params.get("web_search"):
        metadata["web_search"] = True

    images = _normalize_list_or_single(reference_images)
    videos = _normalize_list_or_single(reference_videos)
    audios = _normalize_list_or_single(reference_audios)
    if images:
        metadata["reference_images"] = [_path_or_url_to_payload_value(x) for x in images]
    if videos:
        metadata["reference_videos"] = [str(x) for x in videos]
    if audios:
        metadata["reference_audios"] = [str(x) for x in audios]

    return {
        "model": params["model"],
        "prompt": prompt_text,
        "seconds": str(int(params["duration"])),
        "metadata": metadata,
    }

def _extract_task_id(result):
    if not isinstance(result, dict):
        return None
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    return result.get("task_id") or result.get("id") or data.get("task_id") or data.get("id")


def _build_task_create_url(base_url):
    return f"{_normalize_base_url(base_url)}{_TASK_CREATE_PATH}"


def _build_task_query_url(base_url, task_id):
    return f"{_normalize_base_url(base_url)}{_TASK_QUERY_PATH.format(task_id=task_id)}"


def _create_task(api_key, base_url, payload, timeout):
    endpoint = _build_task_create_url(base_url)
    _log_event("create_task.request", endpoint=endpoint, timeout=timeout, api_key=_mask_api_key(api_key))
    response = requests.post(
        endpoint,
        headers=_build_auth_headers(api_key, include_content_type=True),
        json=payload,
        timeout=timeout,
    )
    _ensure_success_response(response, "创建任务")
    try:
        result = response.json()
    except json.JSONDecodeError as exc:
        raise PluginFatalError(f"创建任务返回非 JSON 响应: {exc}") from exc
    task_id = _extract_task_id(result)
    if not task_id:
        raise PluginFatalError("创建任务失败: 响应中缺少 task_id/id")
    _log_event("create_task.success", task_id=task_id)
    return str(task_id), result

def _normalize_task_status(raw_status):
    status = str(raw_status or "").strip().lower()
    if status in {"queued", "running", "processing", "pending", "submitted", "in_progress"}:
        return "running"
    if status in {"succeeded", "completed", "success"}:
        return "completed"
    if status in {"failed", "error", "failure"}:
        return "failed"
    return "unknown"


def _extract_status_from_task_data(task_data):
    if not isinstance(task_data, dict):
        return None
    data = task_data.get("data")
    if isinstance(data, dict):
        # Shuzai doc-preferred status path: data.data.status
        nested_data = data.get("data")
        if isinstance(nested_data, dict) and nested_data.get("status") is not None:
            return nested_data.get("status")
        if data.get("status") is not None:
            return data.get("status")
        task = data.get("task")
        if isinstance(task, dict) and task.get("status") is not None:
            return task.get("status")
    if task_data.get("status") is not None:
        return task_data.get("status")
    result = task_data.get("result")
    if isinstance(result, dict) and result.get("status") is not None:
        return result.get("status")
    return None


def _extract_video_url_from_status(task_data):
    if not isinstance(task_data, dict):
        return None
    content = task_data.get("content")
    if isinstance(content, dict):
        if content.get("video_url"):
            return content.get("video_url")
        if content.get("url"):
            return content.get("url")
    data = task_data.get("data")
    if isinstance(data, dict):
        if data.get("result_url"):
            return data.get("result_url")
        if data.get("video_url"):
            return data.get("video_url")
        if data.get("url"):
            return data.get("url")
        nested_data = data.get("data")
        if isinstance(nested_data, dict):
            if nested_data.get("result_url"):
                return nested_data.get("result_url")
            if nested_data.get("video_url"):
                return nested_data.get("video_url")
            if nested_data.get("url"):
                return nested_data.get("url")
            nested_content = nested_data.get("content")
            if isinstance(nested_content, dict):
                if nested_content.get("video_url"):
                    return nested_content.get("video_url")
                if nested_content.get("url"):
                    return nested_content.get("url")
        output = data.get("output")
        if isinstance(output, dict):
            if output.get("video_url"):
                return output.get("video_url")
            if output.get("url"):
                return output.get("url")
    return task_data.get("video_url") or task_data.get("url")

def _extract_failure_reason_from_status(task_data):
    if not isinstance(task_data, dict):
        return "未知原因"

    def _stringify_reason(value):
        if isinstance(value, dict):
            msg = value.get("message") or value.get("msg") or value.get("detail")
            code = value.get("code")
            if msg and code:
                return f"{msg} (code={code})"
            if msg:
                return str(msg)
            if code:
                return str(code)
            return ""
        return str(value or "").strip()

    def _is_likely_url(text):
        lowered = str(text or "").strip().lower()
        return lowered.startswith("http://") or lowered.startswith("https://")

    candidates = [
        task_data.get("fail_reason"),
        task_data.get("reason"),
        task_data.get("error"),
        task_data.get("message"),
    ]

    top_data = task_data.get("data")
    if isinstance(top_data, dict):
        candidates.extend(
            [
                top_data.get("fail_reason"),
                top_data.get("reason"),
                top_data.get("error"),
                top_data.get("message"),
            ]
        )

        result_url = top_data.get("result_url")
        if result_url and not _is_likely_url(result_url):
            candidates.append(result_url)

        nested_data = top_data.get("data")
        if isinstance(nested_data, dict):
            candidates.extend(
                [
                    nested_data.get("fail_reason"),
                    nested_data.get("reason"),
                    nested_data.get("message"),
                    nested_data.get("error"),
                ]
            )

    for item in candidates:
        text = _stringify_reason(item)
        if text:
            return text
    return "未知原因"

def _poll_task_status(api_key, base_url, task_id, timeout, max_attempts, poll_interval, progress_callback=None):
    endpoint = _build_task_query_url(base_url, task_id)
    headers = _build_auth_headers(api_key, include_content_type=True)
    parsed_endpoint = urlparse(endpoint)
    previous_status = None

    for attempt in range(1, int(max_attempts) + 1):
        _log_event("poll_task.request", attempt=attempt, endpoint=endpoint, task_id=task_id)
        try:
            response = requests.get(endpoint, headers=headers, timeout=timeout)
            _ensure_success_response(response, "查询任务状态")
            data = response.json()

            _persist_request_payload(
                {
                    "type": "poll_task_response",
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "task_id": str(task_id),
                    "attempt": int(attempt),
                    "endpoint": endpoint,
                    "request": {
                        "method": "GET",
                        "url": endpoint,
                        "path": parsed_endpoint.path or "/",
                        "query": parsed_endpoint.query or "",
                        "headers": _sanitize_headers_for_debug(headers),
                    },
                    "status_code": int(response.status_code),
                    "raw_status_candidates": {
                        "status": data.get("status") if isinstance(data, dict) else None,
                        "data.status": (
                            (data.get("data") or {}).get("status")
                            if isinstance(data, dict) and isinstance(data.get("data"), dict)
                            else None
                        ),
                        "data.data.status": (
                            ((data.get("data") or {}).get("data") or {}).get("status")
                            if isinstance(data, dict)
                            and isinstance(data.get("data"), dict)
                            and isinstance((data.get("data") or {}).get("data"), dict)
                            else None
                        ),
                        "data.task.status": (
                            ((data.get("data") or {}).get("task") or {}).get("status")
                            if isinstance(data, dict)
                            and isinstance(data.get("data"), dict)
                            and isinstance((data.get("data") or {}).get("task"), dict)
                            else None
                        ),
                    },
                    "response_json": data,
                },
                task_id=str(task_id),
            )
        except json.JSONDecodeError as exc:
            _log_event("poll_task.query_error", attempt=attempt, error=str(exc))
            if progress_callback:
                progress_callback(
                    f"查询任务状态响应 JSON 解析失败，第 {attempt} 次，{int(poll_interval)} 秒后重试"
                )
            time.sleep(poll_interval)
            continue
        except Exception as exc:
            _log_event("poll_task.query_error", attempt=attempt, error=str(exc))
            if progress_callback:
                progress_callback(
                    f"查询任务状态异常，第 {attempt} 次，{int(poll_interval)} 秒后重试"
                )
            time.sleep(poll_interval)
            continue

        raw_status = _extract_status_from_task_data(data)
        status = _normalize_task_status(raw_status)
        if status != previous_status:
            _log_event(
                "poll_task.status",
                task_id=task_id,
                status=status,
                raw_status=raw_status,
                attempt=attempt,
            )
            previous_status = status

        if status == "running":
            if progress_callback:
                progress_callback(f"任务状态轮询中，第 {attempt} 次")
            time.sleep(poll_interval)
            continue

        if status == "completed":
            return data, _extract_video_url_from_status(data)

        if status == "failed":
            reason = _extract_failure_reason_from_status(data)
            raise PluginFatalError(f"任务失败: {reason}")

        _log_event("poll_task.unknown_retry", task_id=task_id, attempt=attempt, raw_status=raw_status)
        if progress_callback:
            progress_callback(
                f"任务状态未知({raw_status})，将在 {int(poll_interval)} 秒后继续轮询"
            )
        time.sleep(poll_interval)

    raise PluginFatalError(f"超过最大轮询次数({int(max_attempts)})，任务仍未完成")

def _download_video(video_url, output_path, timeout):
    target_url = str(video_url or "").strip()
    if not target_url:
        raise PluginFatalError("下载视频失败: 缺少可下载 url")
    headers = {"User-Agent": DOWNLOAD_USER_AGENT, "Referer": DOWNLOAD_REFERER, "Accept": "*/*"}
    _log_event("download.try", url=target_url)
    response = requests.get(target_url, headers=headers, timeout=timeout)
    if response.status_code != 200:
        raise PluginFatalError(f"下载视频失败: HTTP {response.status_code}")
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "wb") as video_file:
        video_file.write(response.content)
    _log_event("download.success", output_path=output_path)
    return output_path

def _build_params_log_snapshot(params):
    params = params or {}
    api_key = str(params.get("api_key", "") or "").strip()
    return {
        "api_key_masked": _mask_api_key(api_key),
        "api_key_present": bool(api_key),
        "base_url": params.get("base_url"),
        "model": params.get("model"),
        "resolution": params.get("resolution"),
        "ratio": params.get("ratio"),
        "duration": params.get("duration"),
        "generate_audio": params.get("generate_audio"),
        "watermark": params.get("watermark"),
        "web_search": params.get("web_search"),
        "timeout": params.get("timeout"),
        "max_poll_attempts": params.get("max_poll_attempts"),
        "poll_interval": params.get("poll_interval"),
    }


def _build_default_params():
    return {
        "config_schema_version": CONFIG_SCHEMA_VERSION,
        "api_key": "",
        "base_url": _DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "resolution": DEFAULT_RESOLUTION,
        "ratio": DEFAULT_RATIO,
        "duration": DEFAULT_DURATION,
        "generate_audio": DEFAULT_GENERATE_AUDIO,
        "watermark": DEFAULT_WATERMARK,
        "web_search": DEFAULT_WEB_SEARCH,
        "timeout": DEFAULT_TIMEOUT,
        "max_poll_attempts": DEFAULT_MAX_POLL_ATTEMPTS,
        "poll_interval": DEFAULT_POLL_INTERVAL,
    }


_default_params = _build_default_params()


def _sanitize_params(raw_params=None):
    raw_params = raw_params or {}
    params = _default_params.copy()
    params.update(raw_params)
    params["config_schema_version"] = CONFIG_SCHEMA_VERSION
    params["base_url"] = _normalize_base_url(params.get("base_url") or _DEFAULT_BASE_URL)
    params["resolution"] = _normalize_resolution(params.get("resolution"))
    params["model"] = _normalize_model(params.get("model"), params["resolution"])
    params["ratio"] = _normalize_ratio(params.get("ratio"))
    params["duration"] = _normalize_duration(params.get("duration"))
    params["generate_audio"] = _normalize_bool(params.get("generate_audio"), DEFAULT_GENERATE_AUDIO)
    params["watermark"] = _normalize_bool(params.get("watermark"), DEFAULT_WATERMARK)
    params["web_search"] = _normalize_bool(params.get("web_search"), DEFAULT_WEB_SEARCH)

    timeout = int(params.get("timeout", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT)
    max_attempts = int(params.get("max_poll_attempts", DEFAULT_MAX_POLL_ATTEMPTS) or DEFAULT_MAX_POLL_ATTEMPTS)
    poll_interval = int(params.get("poll_interval", DEFAULT_POLL_INTERVAL) or DEFAULT_POLL_INTERVAL)
    params["timeout"] = max(timeout, 30)
    params["max_poll_attempts"] = max(max_attempts, 1)
    params["poll_interval"] = max(poll_interval, 1)

    _validate_image_constraints(params.get("image_path"))
    return params


def _normalize_terminal_status(status, error=None):
    normalized = _normalize_task_status(status)
    if normalized == "completed":
        return "completed"
    if error and "超过最大轮询次数" in str(error):
        return "timeout"
    return "failed"

def _build_orchestration_result(task_id=None, status="failed", output_path=None, video_url=None, error=None, meta=None):
    error_text = None
    if error:
        if isinstance(error, PluginFatalError):
            error_text = str(error)
        else:
            error_text = str(PluginFatalError(str(error)))
    return {
        "task_id": task_id,
        "status": _normalize_terminal_status(status, error_text),
        "output_path": output_path,
        "video_url": video_url,
        "error": error_text,
        "meta": meta or {},
    }


def _default_output_path(output_dir, viewer_index, task_id):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{int(viewer_index):04d}_seedance_{task_id}_{stamp}.mp4"
    return os.path.join(output_dir, filename)


def _run_seedance_orchestration(context):
    context = context or {}
    raw_params = context.get("plugin_params")
    progress_callback = _safe_progress_callback(context.get("progress_callback"))
    params = _sanitize_params(raw_params if raw_params is not None else get_params())

    api_key = params.get("api_key", "")
    base_url = params.get("base_url", _DEFAULT_BASE_URL)
    prompt = context.get("prompt", "")
    reference_images = context.get("reference_images")
    reference_videos = context.get("reference_videos")
    reference_audios = context.get("reference_audios")
    output_dir = context.get("output_dir", context.get("project_path", os.getcwd()))
    viewer_index = context.get("viewer_index", 0)

    task_id = None
    video_url = None
    task_log_id = None
    try:
        _log_event(
            "workflow.start",
            output_dir=output_dir,
            viewer_index=viewer_index,
            params=_build_params_log_snapshot(params),
        )
        progress_callback("参数校验完成")

        task_log_id = _insert_task_log(
            {
                "api_task_id": None,
                "model_name": params.get("model"),
                "model_display": params.get("model"),
                "prompt": str(prompt or "")[:500],
                "aspect_ratio": params.get("ratio"),
                "duration": str(params.get("duration")),
                "generation_mode": "shuzai_seedance",
                "status": "running",
                "metadata": {"polling": _build_params_log_snapshot(params)},
            }
        )

        payload = _build_create_payload(
            params=params,
            prompt=prompt,
            reference_images=reference_images,
            reference_videos=reference_videos,
            reference_audios=reference_audios,
        )
        payload_file = _persist_request_payload(payload)
        _log_event("create_task.payload", payload_file=payload_file)

        task_id, _ = _create_task(api_key, base_url, payload, params["timeout"])
        _update_task_log(task_log_id, api_task_id=task_id)
        progress_callback("任务已创建")

        if DEFAULT_INITIAL_POLL_DELAY_SECONDS > 0:
            progress_callback(
                f"等待任务落库 {DEFAULT_INITIAL_POLL_DELAY_SECONDS} 秒后开始轮询"
            )
            time.sleep(DEFAULT_INITIAL_POLL_DELAY_SECONDS)
        progress_callback("开始轮询")

        status_data, video_url = _poll_task_status(
            api_key=api_key,
            base_url=base_url,
            task_id=task_id,
            timeout=params["timeout"],
            max_attempts=params["max_poll_attempts"],
            poll_interval=params["poll_interval"],
            progress_callback=progress_callback,
        )

        final_output_path = context.get("output_path") or _default_output_path(output_dir, viewer_index, task_id)
        progress_callback("下载中")
        downloaded_path = _download_video(video_url=video_url, output_path=final_output_path, timeout=params["timeout"])
        progress_callback("完成")

        _update_task_log(task_log_id, status="success", video_url=video_url, local_path=downloaded_path, error=None)
        _log_event("workflow.success", task_id=task_id, output_path=downloaded_path)
        return _build_orchestration_result(
            task_id=task_id,
            status="completed",
            output_path=downloaded_path,
            video_url=video_url,
            error=None,
            meta={"model": params.get("model")},
        )
    except Exception as exc:
        wrapped_error = exc if isinstance(exc, PluginFatalError) else PluginFatalError(str(exc))
        progress_callback("??")
        _log_event("workflow.failed", task_id=task_id, error=str(wrapped_error))
        _update_task_log(task_log_id, status="failed", video_url=video_url, error=str(wrapped_error))
        return _build_orchestration_result(
            task_id=task_id,
            status="failed",
            output_path=None,
            video_url=video_url,
            error=wrapped_error,
            meta={},
        )

def _map_orchestration_to_plugin_output(result):
    if result.get("status") == "completed" and result.get("output_path"):
        return [result["output_path"]]
    raise PluginFatalError(result.get("error") or "工作流执行失败")

def run_seedance_workflow(context):
    return _map_orchestration_to_plugin_output(_run_seedance_orchestration(context))


def run_seedance_client(
    prompt,
    output_path=None,
    plugin_params=None,
    reference_images=None,
    reference_videos=None,
    reference_audios=None,
    progress_callback=None,
):
    context = {
        "prompt": prompt,
        "output_path": output_path,
        "plugin_params": plugin_params,
        "reference_images": reference_images,
        "reference_videos": reference_videos,
        "reference_audios": reference_audios,
        "progress_callback": progress_callback,
    }
    return _run_seedance_orchestration(context)


def get_info():
    return {
        "name": "Shuzai Seedance 视频生成插件",
        "description": "Shuzai Seedance 2.0 视频生成插件",
        "version": _PLUGIN_VERSION,
        "author": "Z Code",
    }

def get_params():
    raw_params = load_plugin_config(_PLUGIN_FILE) or {}
    params = _sanitize_params(raw_params)
    if raw_params != params:
        save_plugin_config(_PLUGIN_FILE, params)
    return params


def generate(context):
    ctx = dict(context or {})
    ctx["progress_callback"] = _safe_progress_callback(ctx.get("progress_callback"))
    _append_file_log("INFO", "generate.enter")
    try:
        outputs = run_seedance_workflow(ctx)
        _log_event("generate.success", outputs=outputs)
        return outputs
    except PluginFatalError:
        _append_file_log("ERROR", "generate.plugin_fatal_error")
        raise
    except Exception as exc:
        _append_file_log("ERROR", f"generate.unhandled_exception: {exc}")
        raise PluginFatalError(str(exc)) from exc


def handle_action(action, data=None):
    payload = data or {}
    _append_file_log("DEBUG", f"handle_action: {action}")
    if action == "open_live_logs":
        return {"ok": True, "open_page": "live_log.html"}
    if action == "open_task_logs":
        return {"ok": True, "open_page": "task_log.html"}
    if action == "get_logs":
        return {"ok": True, "entries": get_buffered_logs(payload.get("since_index", 0))}
    if action == "get_task_logs":
        status = payload.get("status")
        limit = payload.get("limit", 200)
        return {"ok": True, "logs": _query_task_logs(limit=limit, status=status)}
    if action == "download_videos":
        task_ids = payload.get("task_ids") or []
        if not task_ids:
            return {"ok": False, "error": "请选择任务"}
        rows = []
        conn = _db_conn()
        try:
            for task_id in task_ids:
                row = conn.execute("SELECT * FROM video_task_logs WHERE id = ?", (int(task_id),)).fetchone()
                if row:
                    rows.append(dict(row))
        finally:
            conn.close()
        results = [_manual_download_video(row) for row in rows]
        return {"ok": True, "results": results}
    return {"ok": False, "error": f"不支持的操作: {action}"}

if __name__ == "__main__":
    required_funcs = [
        "_build_auth_headers",
        "_build_create_payload",
        "_create_task",
        "_poll_task_status",
        "_download_video",
        "_normalize_terminal_status",
        "_build_orchestration_result",
        "_run_seedance_orchestration",
        "_map_orchestration_to_plugin_output",
        "run_seedance_workflow",
        "run_seedance_client",
        "handle_action",
    ]
    missing = [name for name in required_funcs if not callable(globals().get(name))]
    if missing:
        raise SystemExit(f"smoke check failed, missing callables: {missing}")
    print("smoke check passed")

