# -*- coding: utf-8 -*-
"""
TDu&ZLHub Seedance 2.0 视频生成插件。
对接 ZLHub 中转平台，支持 Seedance 2.0 视频大模型。
"""

import base64
import collections
import io
import json
import mimetypes
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests

try:
    import tos
except ImportError:
    tos = None

# 导入插件工具类
try:
    from plugin_utils import load_plugin_config, save_plugin_config
except ImportError:

    def load_plugin_config(path):
        return {}

    def save_plugin_config(path, config):
        return None


PLUGIN_ERROR_PREFIX = "PLUGIN_ERROR:::"
_PLUGIN_VERSION = "2.0.0"
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
_request_trace_lock = threading.Lock()
_REQUEST_TRACE_FILE_PATH = None
_REQUEST_TRACE_ONCE_KEYS = set()


class PluginFatalError(Exception):
    """插件致命错误，宿主应直接提示用户并终止流程。"""

    def __init__(self, message):
        text = str(message)
        if not text.startswith(PLUGIN_ERROR_PREFIX):
            text = f"{PLUGIN_ERROR_PREFIX}{text}"
        super().__init__(text)


_PLUGIN_FILE = __file__


# 配置选项（V2 固定 requires2 协议）
_DEFAULT_API_BASE_URL = "https://api.zlhub.cn"
_DEFAULT_TASK_CREATE_URL = f"{_DEFAULT_API_BASE_URL}/v1/task/create"
_DEFAULT_TASK_QUERY_URL = f"{_DEFAULT_API_BASE_URL}/v1/task/get"
_DEFAULT_ASSET_BASE_URL = "https://asset.zlhub.cn"
_DEFAULT_TOS_ENDPOINT = "tos-cn-beijing.volces.com"
_DEFAULT_TOS_REGION = "cn-beijing"
_DEFAULT_TOS_BUCKET = "zlhub-asset-outside"

_TOS_LOCAL_LIB_DIR = plugin_dir / ".deps"
_TOS_IMPORT_ERROR = None

DEFAULT_MODEL = "doubao-seedance-2.0"
DEFAULT_RESOLUTION = "720p"
DEFAULT_RATIO = "adaptive"
DEFAULT_DURATION = 5
DEFAULT_GENERATE_AUDIO = True

DEFAULT_RESOLUTIONS = ["480p", "720p", "1080p"]
DEFAULT_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
FAST_MODEL_WITHOUT_1080P = "doubao-seedance-2.0-fast"
DEFAULT_TIMEOUT = 900
DEFAULT_MAX_POLL_ATTEMPTS = 300
DEFAULT_POLL_INTERVAL = 180
DEFAULT_AUDIT_POLL_INTERVAL = 30
DEFAULT_INITIAL_POLL_DELAY_SECONDS = 180
CONFIG_SCHEMA_VERSION = 2
LEGACY_DEFAULT_POLL_INTERVAL = 5
DOWNLOAD_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
)
DOWNLOAD_REFERER = "https://api.zlhub.cn/"

SUPPORTED_IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp", ".bmp", ".tiff", ".gif"}
MAX_IMAGE_SIZE_BYTES = 30 * 1024 * 1024

RESOLUTION_RATIO_MAP = {
    "480p": {
        "16:9": (864, 496),
        "4:3": (752, 560),
        "1:1": (640, 640),
        "3:4": (560, 752),
        "9:16": (496, 864),
        "21:9": (992, 432),
    },
    "720p": {
        "16:9": (1280, 720),
        "4:3": (1112, 834),
        "1:1": (960, 960),
        "3:4": (834, 1112),
        "9:16": (720, 1280),
        "21:9": (1470, 630),
    },
    "1080p": {
        "16:9": (1920, 1088),
        "4:3": (1664, 1248),
        "1:1": (1440, 1440),
        "3:4": (1248, 1664),
        "9:16": (1088, 1920),
        "21:9": (2176, 928),
    },
}


def _mask_api_key(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return f"{text[:2]}***"
    return f"{text[:4]}***{text[-2:]}"


def _build_params_log_snapshot(params):
    params = params or {}
    api_key = str(params.get("api_key", "") or "").strip()
    return {
        "api_key_masked": _mask_api_key(api_key),
        "api_key_present": bool(api_key),
        "base_url": params.get("base_url"),
        "task_create_url": params.get("task_create_url"),
        "task_query_url": params.get("task_query_url"),
        "asset_base_url": params.get("asset_base_url"),
        "model": params.get("model"),
        "resolution": params.get("resolution"),
        "ratio": params.get("ratio"),
        "duration": params.get("duration"),
        "generate_audio": params.get("generate_audio"),
        "web_search": params.get("web_search"),
        "timeout": params.get("timeout"),
        "max_poll_attempts": params.get("max_poll_attempts"),
        "poll_interval": params.get("poll_interval"),
        "retry_count": params.get("retry_count"),
        "video_style": params.get("video_style"),
        "audit_access_token_present": bool(
            str(params.get("audit_access_token", "")).strip()
        ),
        "audit_callback_url": params.get("audit_callback_url"),
        "audit_test_only": bool(params.get("audit_test_only")),
        "tos_ak_present": bool(str(params.get("tos_ak", "")).strip()),
        "tos_sk_present": bool(str(params.get("tos_sk", "")).strip()),
        "tos_endpoint": params.get("tos_endpoint"),
        "tos_region": params.get("tos_region"),
        "tos_bucket": params.get("tos_bucket"),
    }


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
        # Never break plugin flow because file logging failed.
        return


def get_buffered_logs(since_index=0):
    try:
        since = int(since_index or 0)
    except (TypeError, ValueError):
        since = 0
    with _log_lock:
        return [entry for entry in list(_log_buffer) if entry.get("index", 0) > since]


def _db_conn():
    conn = sqlite3.connect(str(_TASK_LOG_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_task_log_db():
    conn = _db_conn()
    try:
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
        conn.commit()
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


def _manual_download_video(task_row):
    url = task_row.get("video_url")
    if not url:
        return {
            "id": task_row.get("id"),
            "status": "manual_failed",
            "error": "任务无 video_url",
        }
    _MANUAL_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    base_name = _safe_filename(
        task_row.get("api_task_id") or f"task_{task_row.get('id')}"
    )
    file_path = _MANUAL_DOWNLOAD_DIR / f"{base_name}.mp4"
    headers = {
        "User-Agent": DOWNLOAD_USER_AGENT,
        "Referer": DOWNLOAD_REFERER,
        "Accept": "*/*",
    }
    try:
        resp = _request_with_trace(
            method="GET",
            url=url,
            headers=headers,
            timeout=120,
            interface_name="manual_download_video",
            task_id=str(task_id or ""),
        )
        if resp.status_code != 200:
            raise PluginFatalError(f"下载失败: HTTP {resp.status_code}")
        with open(file_path, "wb") as fw:
            fw.write(resp.content)
        _update_task_log(
            task_row.get("id"), local_path=str(file_path), status="manual_success"
        )
        return {
            "id": task_row.get("id"),
            "status": "manual_success",
            "path": str(file_path),
        }
    except Exception as exc:
        _update_task_log(task_row.get("id"), status="manual_failed", error=str(exc))
        return {"id": task_row.get("id"), "status": "manual_failed", "error": str(exc)}


def _log_event(event, **fields):
    payload = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "fields": fields or {},
    }
    text = f"[ZLHubSeedance] {json.dumps(payload, ensure_ascii=False)}"
    print(text)
    _append_live_log("INFO", text)
    _append_file_log("INFO", text)


def _truncate_value(value, max_len=1000):
    text = str(value or "")
    if len(text) <= int(max_len):
        return text
    return f"{text[: int(max_len)]}...(truncated, total={len(text)})"


def _build_payload_log_snapshot(payload):
    if isinstance(payload, dict):
        result = {}
        for key, value in payload.items():
            if key == "content" and isinstance(value, list):
                items = []
                for item in value:
                    if isinstance(item, dict):
                        item_copy = dict(item)
                        if item_copy.get("type") == "text" and isinstance(
                            item_copy.get("text"), str
                        ):
                            item_copy["text"] = _truncate_value(
                                item_copy.get("text"), max_len=1000
                            )
                        if item_copy.get("type") in {
                            "image_url",
                            "video_url",
                            "audio_url",
                        }:
                            media_field = item_copy.get(item_copy.get("type"))
                            if isinstance(media_field, dict) and isinstance(
                                media_field.get("url"), str
                            ):
                                media_field = dict(media_field)
                                media_field["url"] = _truncate_value(
                                    media_field.get("url"), max_len=400
                                )
                                item_copy[item_copy.get("type")] = media_field
                        items.append(item_copy)
                    else:
                        items.append(item)
                result[key] = items
                continue

            if isinstance(value, str):
                result[key] = _truncate_value(value, max_len=200)
                continue

            result[key] = value
        return result
    return payload


def _persist_request_payload(payload, task_id=None):
    global _REQUEST_TRACE_FILE_PATH
    _REQUEST_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with _request_trace_lock:
        if _REQUEST_TRACE_FILE_PATH is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            suffix = _safe_filename(task_id) if task_id else "pending"
            _REQUEST_TRACE_FILE_PATH = str(
                _REQUEST_PAYLOAD_DIR / f"request_payload_{stamp}_{suffix}.json"
            )

        file_path = Path(_REQUEST_TRACE_FILE_PATH)
        container = {"entries": []}
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as fr:
                    loaded = json.loads(fr.read() or "{}")
                    if isinstance(loaded, dict) and isinstance(
                        loaded.get("entries"), list
                    ):
                        container = loaded
            except Exception:
                container = {"entries": []}

        container["entries"].append(payload or {})
        with open(file_path, "w", encoding="utf-8") as fw:
            fw.write(json.dumps(container, ensure_ascii=False, indent=2))
        return str(file_path)


def _start_request_trace_session(task_id=None):
    global _REQUEST_TRACE_FILE_PATH
    global _REQUEST_TRACE_ONCE_KEYS
    with _request_trace_lock:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        suffix = _safe_filename(task_id) if task_id else "pending"
        _REQUEST_TRACE_FILE_PATH = str(
            _REQUEST_PAYLOAD_DIR / f"request_payload_{stamp}_{suffix}.json"
        )
        _REQUEST_TRACE_ONCE_KEYS = set()


_SENSITIVE_KEYS = {
    "authorization",
    "x-access-token",
    "api_key",
    "audit_access_token",
    "tos_ak",
    "tos_sk",
}


def _mask_sensitive_value(key, value):
    key_text = str(key or "").strip().lower()
    text = str(value or "")
    if key_text == "authorization":
        if text.lower().startswith("bearer "):
            token = text[7:].strip()
            return f"Bearer {_mask_api_key(token)}"
        return _mask_api_key(text)
    if key_text in {
        "x-access-token",
        "api_key",
        "audit_access_token",
        "tos_ak",
        "tos_sk",
    }:
        return _mask_api_key(text)
    return value


def _sanitize_for_log(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            key_text = str(key or "")
            key_lc = key_text.lower()
            if key_lc in _SENSITIVE_KEYS:
                result[key_text] = _mask_sensitive_value(key_lc, item)
            else:
                result[key_text] = _sanitize_for_log(item)
        return result
    if isinstance(value, list):
        return [_sanitize_for_log(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_for_log(item) for item in list(value)]
    if isinstance(value, str):
        return _truncate_value(value, max_len=5000)
    return value


def _safe_json_loads(text):
    try:
        return json.loads(str(text or ""))
    except Exception:
        return None


def _serialize_http_response(response):
    if response is None:
        return None
    headers = dict(getattr(response, "headers", {}) or {})
    content_type = str(headers.get("Content-Type", "")).lower()
    body_json = None
    body_text = None
    body_size = 0
    try:
        body_size = len(getattr(response, "content", b"") or b"")
    except Exception:
        body_size = 0

    if "json" in content_type:
        try:
            body_json = response.json()
        except Exception:
            body_json = _safe_json_loads(getattr(response, "text", ""))

    if body_json is None:
        if any(
            text_type in content_type
            for text_type in (
                "json",
                "text",
                "xml",
                "html",
                "javascript",
                "x-www-form-urlencoded",
            )
        ):
            body_text = _truncate_value(getattr(response, "text", ""), max_len=5000)
        else:
            body_text = f"<binary content, {body_size} bytes>"

    return {
        "status_code": int(getattr(response, "status_code", 0) or 0),
        "headers": _sanitize_for_log(headers),
        "body_json": _sanitize_for_log(body_json) if body_json is not None else None,
        "body_text": body_text,
        "body_size": int(body_size),
    }


def _persist_interface_trace(
    interface_name, request_data, response=None, error=None, task_id=None
):
    trace_payload = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "http_trace",
        "interface": str(interface_name or "unknown"),
        "request": _sanitize_for_log(request_data or {}),
        "response": _serialize_http_response(response),
        "error": _truncate_value(str(error), max_len=5000) if error else None,
    }
    return _persist_request_payload(trace_payload, task_id=task_id)


def _request_with_trace(
    method,
    url,
    headers=None,
    params=None,
    json_payload=None,
    data=None,
    timeout=None,
    interface_name=None,
    task_id=None,
    log_once_key=None,
):
    global _REQUEST_TRACE_ONCE_KEYS
    request_meta = {
        "method": str(method or "").upper(),
        "url": str(url or ""),
        "headers": dict(headers or {}),
        "params": params,
        "json": json_payload,
        "data": data
        if isinstance(data, (str, int, float, bool, type(None)))
        else "<non-scalar>",
        "timeout": timeout,
    }
    begin = time.time()
    should_persist = True
    if log_once_key:
        with _request_trace_lock:
            if log_once_key in _REQUEST_TRACE_ONCE_KEYS:
                should_persist = False
            else:
                _REQUEST_TRACE_ONCE_KEYS.add(log_once_key)
    try:
        response = requests.request(
            method=str(method or "").upper(),
            url=url,
            headers=headers,
            params=params,
            json=json_payload,
            data=data,
            timeout=timeout,
        )
        elapsed_ms = int((time.time() - begin) * 1000)
        request_meta["elapsed_ms"] = elapsed_ms
        trace_file = None
        if should_persist:
            trace_file = _persist_interface_trace(
                interface_name=interface_name,
                request_data=request_meta,
                response=response,
                task_id=task_id,
            )
        _log_event(
            "http.trace",
            interface=interface_name,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            trace_file=trace_file,
        )
        return response
    except requests.RequestException as exc:
        elapsed_ms = int((time.time() - begin) * 1000)
        request_meta["elapsed_ms"] = elapsed_ms
        trace_file = None
        if should_persist:
            trace_file = _persist_interface_trace(
                interface_name=interface_name,
                request_data=request_meta,
                error=exc,
                task_id=task_id,
            )
        _log_event(
            "http.trace",
            interface=interface_name,
            elapsed_ms=elapsed_ms,
            error=str(exc),
            trace_file=trace_file,
        )
        raise


def _safe_progress_callback(progress_callback):
    if callable(progress_callback):
        return progress_callback

    def _noop(_message):
        return None

    return _noop


def get_info():
    """返回插件元数据"""
    return {
        "name": "TDu&ZLHub Seedance 视频生成 V2",
        "description": "对接 ZLHub 第二代协议的 Seedance 2.0 视频生成插件。",
        "version": _PLUGIN_VERSION,
        "author": "Z Code",
    }


def _build_default_params():
    """构建默认参数，与 API 文档及 UI 保持一致"""
    return {
        "config_schema_version": CONFIG_SCHEMA_VERSION,
        "api_key": "",
        "base_url": _DEFAULT_API_BASE_URL,
        "task_create_url": _DEFAULT_TASK_CREATE_URL,
        "task_query_url": _DEFAULT_TASK_QUERY_URL,
        "asset_base_url": _DEFAULT_ASSET_BASE_URL,
        "audit_access_token": "",
        "audit_callback_url": "",
        "tos_ak": "",
        "tos_sk": "",
        "tos_endpoint": _DEFAULT_TOS_ENDPOINT,
        "tos_region": _DEFAULT_TOS_REGION,
        "tos_bucket": _DEFAULT_TOS_BUCKET,
        "model": DEFAULT_MODEL,
        "resolution": DEFAULT_RESOLUTION,
        "ratio": DEFAULT_RATIO,
        "duration": DEFAULT_DURATION,
        "generate_audio": DEFAULT_GENERATE_AUDIO,
        "web_search": False,
        "timeout": DEFAULT_TIMEOUT,
        "max_poll_attempts": DEFAULT_MAX_POLL_ATTEMPTS,
        "poll_interval": DEFAULT_POLL_INTERVAL,
        "retry_count": 3,
        "video_style": "其他风格",
        "audit_test_only": False,
    }


_default_params = _build_default_params()


def _get_supported_resolutions(model):
    normalized_model = _normalize_model(model)
    if normalized_model == FAST_MODEL_WITHOUT_1080P:
        return [item for item in DEFAULT_RESOLUTIONS if item != "1080p"]
    return list(DEFAULT_RESOLUTIONS)


def _normalize_resolution(value, model=None):
    resolution = str(value or "").strip().lower()
    supported = _get_supported_resolutions(model)
    if resolution in supported:
        return resolution
    if DEFAULT_RESOLUTION in supported:
        return DEFAULT_RESOLUTION
    if supported:
        return supported[0]
    return DEFAULT_RESOLUTION


def _normalize_aspect_ratio(value):
    ratio = str(value or "").strip()
    if ratio in DEFAULT_RATIOS:
        return ratio
    return DEFAULT_RATIO


def _normalize_duration(value):
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return DEFAULT_DURATION

    if duration == -1:
        return -1
    if duration < 4:
        return 4
    if duration > 15:
        return 15
    return duration


def _normalize_model(value):
    model = str(value or "").strip()
    if not model:
        return DEFAULT_MODEL
    return model


def _normalize_audio_generation(value):
    if isinstance(value, bool):
        return value

    text = str(value or "").strip().lower()
    if text in {"true", "1", "on", "yes", "enabled", "有声"}:
        return True
    if text in {"false", "0", "off", "no", "disabled", "无声"}:
        return False
    return DEFAULT_GENERATE_AUDIO


def _normalize_web_search(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "on", "yes", "enabled"}


def _get_physical_pixels(resolution, ratio):
    if ratio == "adaptive":
        return None, None
    pair = RESOLUTION_RATIO_MAP.get(resolution, {}).get(ratio)
    if not pair:
        return None, None
    return pair[0], pair[1]


def _validate_image_constraints(image_path):
    if not image_path:
        return

    path_text = str(image_path)
    if path_text.lower().startswith(("http://", "https://", "data:", "asset://")):
        return

    if not os.path.exists(path_text):
        raise PluginFatalError(f"参考图片不存在: {path_text}")

    ext = os.path.splitext(path_text)[1].lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise PluginFatalError(
            f"图片格式不支持: {ext or 'unknown'}，支持格式: {allowed}"
        )

    size_bytes = os.path.getsize(path_text)
    if size_bytes >= MAX_IMAGE_SIZE_BYTES:
        raise PluginFatalError("图片大小超过 30MB 限制")


def _normalize_base_url(url):
    return str(url or "").strip().rstrip("/")


def _build_task_endpoints(base_url):
    base = _normalize_base_url(base_url or _DEFAULT_API_BASE_URL)
    return (
        f"{base}/v1/task/create",
        f"{base}/v1/task/get",
    )


def _is_remote_or_asset(value):
    text = str(value or "").strip().lower()
    return text.startswith(("http://", "https://", "data:", "asset://"))


def _is_public_url(value):
    text = str(value or "").strip().lower()
    return text.startswith(("http://", "https://"))


def _new_trace_id():
    # requires2 要求 32 位无横杠追踪 ID，便于平台侧排障。
    return uuid.uuid4().hex


def _build_auth_headers(api_key, include_content_type=True, trace_id=None):
    key_text = str(api_key or "").strip()
    if not key_text:
        raise PluginFatalError("API Key 未设置")

    headers = {"Authorization": f"Bearer {key_text}"}
    if include_content_type:
        headers["Content-Type"] = "application/json"
    if trace_id:
        headers["X-Trace-ID"] = str(trace_id)
    return headers


def _build_audit_headers(audit_access_token, include_content_type=True, track_id=None):
    token_text = str(audit_access_token or "").strip()
    if not token_text:
        raise PluginFatalError("素材审核失败: audit_access_token 未设置")
    headers = {"X-Access-Token": token_text}
    if include_content_type:
        headers["Content-Type"] = "application/json"
    if track_id:
        headers["X-Track-Id"] = str(track_id)
    return headers


def _ensure_success_response(response, operation_name):
    if response.status_code != 200:
        detail = response.text
        raise PluginFatalError(
            f"{operation_name}失败: HTTP {response.status_code} - {detail}"
        )


def _normalize_list_or_single(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [item for item in value if item]
    if isinstance(value, dict):
        return [
            item
            for _, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if item
        ]
    return [value] if value else []


def _guess_mime_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


def _resolve_tos_module():
    global tos
    global _TOS_IMPORT_ERROR
    if tos is not None:
        return tos

    try:
        import tos as imported_tos

        tos = imported_tos
        return tos
    except ImportError as exc:
        _TOS_IMPORT_ERROR = exc

    local_lib = str(_TOS_LOCAL_LIB_DIR)
    if local_lib not in sys.path:
        sys.path.insert(0, local_lib)
    try:
        import tos as imported_tos

        tos = imported_tos
        _TOS_IMPORT_ERROR = None
        return tos
    except ImportError as exc:
        _TOS_IMPORT_ERROR = exc

    install_env = dict(os.environ)
    current_pythonpath = str(install_env.get("PYTHONPATH", "")).strip()
    install_env["PYTHONPATH"] = (
        f"{local_lib}{os.pathsep}{current_pythonpath}"
        if current_pythonpath
        else local_lib
    )

    def _run_pip(args, timeout_seconds=120):
        cmd = (
            [sys.executable, "-m", "pip", "install"]
            + list(args)
            + [
                "--disable-pip-version-check",
                "--no-warn-script-location",
            ]
        )
        start_at = time.time()
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=install_env,
            )
            _persist_request_payload(
                {
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "pip_install_trace",
                    "command": cmd,
                    "returncode": int(result.returncode),
                    "elapsed_ms": int((time.time() - start_at) * 1000),
                    "stdout": _truncate_value(result.stdout, max_len=8000),
                    "stderr": _truncate_value(result.stderr, max_len=8000),
                }
            )
            return result
        except Exception as exc:
            stdout = getattr(exc, "stdout", "")
            stderr = getattr(exc, "stderr", "")
            _persist_request_payload(
                {
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "pip_install_trace",
                    "command": cmd,
                    "returncode": int(getattr(exc, "returncode", -1)),
                    "elapsed_ms": int((time.time() - start_at) * 1000),
                    "stdout": _truncate_value(stdout, max_len=8000),
                    "stderr": _truncate_value(stderr, max_len=8000),
                    "error": _truncate_value(str(exc), max_len=4000),
                }
            )
            raise

    try:
        _TOS_LOCAL_LIB_DIR.mkdir(parents=True, exist_ok=True)

        # Attempt 1: keep dependencies inside plugin folder first.
        _run_pip(["setuptools", "wheel", "-t", local_lib], timeout_seconds=90)
        _run_pip(["tos", "--no-build-isolation", "-t", local_lib], timeout_seconds=180)

        import tos as imported_tos

        tos = imported_tos
        _TOS_IMPORT_ERROR = None
        _log_event("tos_sdk.autoinstall.success", mode="plugin_local", target=local_lib)
        return tos
    except Exception as first_exc:
        first_detail = str(first_exc)
        if isinstance(first_exc, subprocess.CalledProcessError):
            first_detail = (
                f"{first_detail}; stderr={str(first_exc.stderr or '').strip()[:1000]}"
            )
        _log_event(
            "tos_sdk.autoinstall.retry",
            mode="plugin_local_failed",
            error=first_detail,
            target=local_lib,
        )

    try:
        # Attempt 2: repair embedded Python build backend, then retry plugin-local install.
        _run_pip(["setuptools", "wheel"], timeout_seconds=120)
        _run_pip(["tos", "--no-build-isolation", "-t", local_lib], timeout_seconds=180)

        import tos as imported_tos

        tos = imported_tos
        _TOS_IMPORT_ERROR = None
        _log_event(
            "tos_sdk.autoinstall.success",
            mode="global_backend_then_plugin_local",
            target=local_lib,
        )
        return tos
    except Exception as second_exc:
        second_detail = str(second_exc)
        if isinstance(second_exc, subprocess.CalledProcessError):
            second_detail = (
                f"{second_detail}; stderr={str(second_exc.stderr or '').strip()[:1000]}"
            )
        _log_event(
            "tos_sdk.autoinstall.retry",
            mode="global_backend_failed",
            error=second_detail,
            target=local_lib,
        )

    try:
        # Attempt 3: final fallback, install tos into embedded runtime directly.
        _run_pip(["tos"], timeout_seconds=240)
        import tos as imported_tos

        tos = imported_tos
        _TOS_IMPORT_ERROR = None
        _log_event("tos_sdk.autoinstall.success", mode="global_tos", target=local_lib)
        return tos
    except Exception as final_exc:
        final_detail = str(final_exc)
        if isinstance(final_exc, subprocess.CalledProcessError):
            final_detail = (
                f"{final_detail}; stderr={str(final_exc.stderr or '').strip()[:1500]}"
            )
        _TOS_IMPORT_ERROR = Exception(final_detail)
        _log_event("tos_sdk.autoinstall.failed", error=final_detail, target=local_lib)
        return None


def _ensure_tos_config(params):
    params = params or {}
    required_fields = [
        ("tos_ak", "tos_ak"),
        ("tos_sk", "tos_sk"),
        ("tos_endpoint", "tos_endpoint"),
        ("tos_region", "tos_region"),
        ("tos_bucket", "tos_bucket"),
    ]
    missing = [
        label for key, label in required_fields if not str(params.get(key, "")).strip()
    ]
    if missing:
        raise PluginFatalError(
            "TOS 配置不完整，缺少: {}。请先配置 TOS，或改用公网 URL".format(
                ", ".join(missing)
            )
        )
    if _resolve_tos_module() is None:
        detail = str(_TOS_IMPORT_ERROR) if _TOS_IMPORT_ERROR else "未知原因"
        raise PluginFatalError(
            "缺少 tos SDK，且自动安装失败。可手动执行: "
            f"`{sys.executable} -m pip install tos`。"
            f" 详细信息: {detail}"
        )


def _build_tos_public_url(bucket, endpoint, object_key):
    endpoint_text = str(endpoint or "").strip()
    endpoint_text = re.sub(r"^https?://", "", endpoint_text, flags=re.IGNORECASE).strip(
        "/"
    )
    return f"https://{bucket}.{endpoint_text}/{object_key}"


def _upload_file_to_tos(local_file_path, params):
    text_path = str(local_file_path or "").strip()
    if not text_path:
        raise PluginFatalError("本地素材路径不能为空")
    if not os.path.exists(text_path):
        raise PluginFatalError(f"本地素材不存在: {text_path}")

    _ensure_tos_config(params)

    bucket = str(params.get("tos_bucket", "")).strip()
    endpoint = str(params.get("tos_endpoint", "")).strip()
    region = str(params.get("tos_region", "")).strip()
    ak = str(params.get("tos_ak", "")).strip()
    sk = str(params.get("tos_sk", "")).strip()

    ext = os.path.splitext(text_path)[1].lower()
    if not ext:
        guessed_ext = mimetypes.guess_extension(_guess_mime_type(text_path)) or ".bin"
        ext = guessed_ext if guessed_ext.startswith(".") else f".{guessed_ext}"

    object_key = f"images/{uuid.uuid4().hex}{ext}"
    content_type = _guess_mime_type(text_path)

    try:
        client = tos.TosClientV2(ak=ak, sk=sk, endpoint=endpoint, region=region)
        with open(text_path, "rb") as fr:
            file_bytes = fr.read()
        try:
            client.put_object(
                bucket=bucket,
                key=object_key,
                content=file_bytes,
                content_type=content_type,
            )
        except TypeError:
            client.put_object(bucket=bucket, key=object_key, content=file_bytes)
    except Exception as exc:
        raise PluginFatalError(f"TOS 上传失败: {exc}") from exc

    return _build_tos_public_url(bucket, endpoint, object_key)


def _upload_data_url_to_tos(data_url, params):
    data_text = str(data_url or "").strip()
    if not data_text.lower().startswith("data:"):
        raise PluginFatalError("data URL 格式无效")

    match = re.match(r"^data:([^;,]+)?;base64,(.+)$", data_text, flags=re.IGNORECASE)
    if not match:
        raise PluginFatalError("data URL 解析失败，要求 base64 编码")

    mime_type = (match.group(1) or "application/octet-stream").strip().lower()
    payload_b64 = match.group(2).strip()
    try:
        raw_bytes = base64.b64decode(payload_b64, validate=True)
    except Exception as exc:
        raise PluginFatalError(f"data URL Base64 解码失败: {exc}") from exc

    tmp_dir = plugin_dir / "tmp_uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ext = mimetypes.guess_extension(mime_type) or ".bin"
    if not ext.startswith("."):
        ext = f".{ext}"
    temp_path = tmp_dir / f"{uuid.uuid4().hex}{ext}"
    try:
        with open(temp_path, "wb") as fw:
            fw.write(raw_bytes)
        return _upload_file_to_tos(str(temp_path), params)
    finally:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass


def _normalize_or_upload_media_url(media_value, field_name, params):
    text = str(media_value or "").strip()
    if not text:
        raise PluginFatalError(f"{field_name} 不能为空")
    lowered = text.lower()
    if lowered.startswith("asset://"):
        return text
    if _is_public_url(text):
        return text
    if lowered.startswith("data:"):
        return _upload_data_url_to_tos(text, params)
    if os.path.exists(text):
        return _upload_file_to_tos(text, params)
    if re.match(r"^[a-zA-Z]:[\\/]", text) or text.startswith(
        ("./", ".\\", "../", "..\\")
    ):
        raise PluginFatalError(f"{field_name} 本地文件不存在: {text}")
    raise PluginFatalError(
        f"{field_name} 不支持该格式，请提供公网 URL、asset://、data: 或本地文件路径"
    )


def _normalize_media_url(media_value, field_name):
    # Backward-compatible wrapper for existing call sites.
    return _normalize_or_upload_media_url(media_value, field_name, {})


def _call_material_audit_api(
    asset_base_url,
    audit_access_token,
    images,
    callback_url="",
    timeout=120,
    poll_interval=3,
):
    image_list = []
    for image in _normalize_list_or_single(images):
        item = str(image or "").strip()
        if not item:
            continue
        if not _is_public_url(item):
            raise PluginFatalError("不支持base64或本地文件，请提供公网URL")
        image_list.append(item)
    if not image_list:
        raise PluginFatalError("素材审核失败: images 不能为空")

    base_url = _normalize_base_url(asset_base_url or _DEFAULT_ASSET_BASE_URL)
    submit_endpoint = f"{base_url}/api/asset/upload/async"
    request_timeout = max(5, min(int(timeout or 120), 120))
    submit_track_id = _new_trace_id()
    request_payload = {"images": image_list, "asset_type": "Image"}
    callback_text = str(callback_url or "").strip()
    if callback_text:
        request_payload["callback_url"] = callback_text

    _log_event(
        "audit.request",
        endpoint=submit_endpoint,
        track_id=submit_track_id,
        image_count=len(image_list),
    )
    try:
        response = _request_with_trace(
            method="POST",
            url=submit_endpoint,
            headers=_build_audit_headers(
                audit_access_token, include_content_type=True, track_id=submit_track_id
            ),
            json_payload=request_payload,
            timeout=request_timeout,
            interface_name="audit_submit_async",
            task_id=None,
        )
    except requests.RequestException as exc:
        raise PluginFatalError(f"素材审核请求失败: {exc}") from exc

    if response.status_code not in (200, 202):
        raise PluginFatalError(
            f"素材审核请求失败: HTTP {response.status_code} - {response.text}"
        )

    try:
        response_json = response.json()
    except json.JSONDecodeError as exc:
        raise PluginFatalError("素材审核返回非 JSON 响应") from exc

    task_id = str(response_json.get("task_id") or "").strip()
    if not task_id:
        raise PluginFatalError("素材审核失败: 响应中缺少 task_id")

    query_endpoint = f"{base_url}/api/task/{task_id}"
    query_timeout = max(5, min(int(timeout or 120), 300))
    max_attempts = max(1, int(query_timeout / max(1, int(poll_interval or 3))) + 1)
    result_json = None
    for attempt in range(1, max_attempts + 1):
        query_track_id = _new_trace_id()
        _log_event(
            "audit.query",
            task_id=task_id,
            endpoint=query_endpoint,
            attempt=attempt,
            track_id=query_track_id,
        )
        try:
            query_response = _request_with_trace(
                method="GET",
                url=query_endpoint,
                headers=_build_audit_headers(
                    audit_access_token,
                    include_content_type=False,
                    track_id=query_track_id,
                ),
                timeout=query_timeout,
                interface_name="audit_query_task",
                task_id=task_id,
            )
        except requests.RequestException as exc:
            if attempt >= max_attempts:
                raise PluginFatalError(f"素材审核查询失败: {exc}") from exc
            time.sleep(max(1, int(poll_interval)))
            continue

        if query_response.status_code != 200:
            if attempt >= max_attempts:
                raise PluginFatalError(
                    f"素材审核查询失败: HTTP {query_response.status_code} - {query_response.text}"
                )
            time.sleep(max(1, int(poll_interval)))
            continue

        try:
            query_json = query_response.json()
        except json.JSONDecodeError:
            if attempt >= max_attempts:
                raise PluginFatalError("素材审核查询返回非 JSON 响应")
            time.sleep(max(1, int(poll_interval)))
            continue

        status = str(query_json.get("status") or "").strip().lower()
        if status == "completed":
            result_json = query_json
            break
        if status in {"failed", "error"}:
            raise PluginFatalError(
                f"素材审核失败: {query_json.get('error_message') or query_json.get('message') or '未知原因'}"
            )
        time.sleep(max(1, int(poll_interval)))

    if result_json is None:
        raise PluginFatalError("素材审核失败: 查询超时，请稍后重试")

    result_block = result_json.get("result") or {}
    items = result_block.get("items")
    if not isinstance(items, list):
        raise PluginFatalError("素材审核失败: 查询结果缺少 items")

    asset_urls = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source_url = str(item.get("source_url") or "").strip()
        status_ok = int(item.get("submit_review_status") or 0) == 1
        downstream_asset_id = str(item.get("downstream_asset_id") or "").strip()
        if not status_ok or not downstream_asset_id:
            raise PluginFatalError(
                f"素材审核失败: {source_url or 'unknown'} - "
                f"{item.get('error_code') or 'AUDIT_FAILED'}: "
                f"{item.get('error_message') or '素材未通过审核'}"
            )
        asset_urls.append(f"asset://{downstream_asset_id}")

    if len(asset_urls) < len(image_list):
        raise PluginFatalError(
            f"素材审核失败: 返回资源数不足 ({len(asset_urls)}/{len(image_list)})"
        )

    _log_event(
        "audit.success",
        audit_task_id=task_id,
        review_batch_id=result_block.get("review_batch_id"),
        asset_count=len(asset_urls),
        track_id=submit_track_id,
    )
    return asset_urls, task_id, submit_track_id


def _build_content_items(
    prompt,
    reference_images=None,
    reference_videos=None,
    reference_audios=None,
    params=None,
    role_mode="reference_image",
):
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        raise PluginFatalError("Prompt 不能为空")

    content = [{"type": "text", "text": prompt_text}]

    for image in _normalize_list_or_single(reference_images):
        image_url = _normalize_or_upload_media_url(image, "参考图片", params)
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_url},
                "role": role_mode or "reference_image",
            }
        )

    for video in _normalize_list_or_single(reference_videos):
        video_url = _normalize_or_upload_media_url(video, "参考视频", params)
        content.append(
            {
                "type": "video_url",
                "video_url": {"url": video_url},
                "role": "reference_video",
            }
        )

    for audio in _normalize_list_or_single(reference_audios):
        audio_url = _normalize_or_upload_media_url(audio, "参考音频", params)
        content.append(
            {
                "type": "audio_url",
                "audio_url": {"url": audio_url},
                "role": "reference_audio",
            }
        )

    return content


def _build_create_payload(
    params, prompt, reference_images=None, reference_videos=None, reference_audios=None
):
    payload = {
        "model": params["model"],
        "content": _build_content_items(
            prompt, reference_images, reference_videos, reference_audios, params=params
        ),
        "generate_audio": bool(params["generate_audio"]),
        "resolution": params["resolution"],
        "ratio": params["ratio"],
        "duration": int(params["duration"]),
    }

    has_media = bool(
        _normalize_list_or_single(reference_images)
        or _normalize_list_or_single(reference_videos)
        or _normalize_list_or_single(reference_audios)
    )
    if params.get("web_search") and not has_media:
        payload["tools"] = [{"type": "web_search"}]

    return payload


def _create_task(api_key, task_create_url, payload, timeout):
    endpoint = _normalize_base_url(task_create_url)
    trace_id = _new_trace_id()
    _log_event(
        "create_task.request",
        endpoint=endpoint,
        timeout=timeout,
        api_key=_mask_api_key(api_key),
        trace_id=trace_id,
    )
    response = _request_with_trace(
        method="POST",
        url=endpoint,
        headers=_build_auth_headers(
            api_key, include_content_type=True, trace_id=trace_id
        ),
        json_payload=payload,
        timeout=timeout,
        interface_name="create_task",
    )
    if response.status_code != 200:
        raise PluginFatalError(
            f"创建任务失败: HTTP {response.status_code} - {response.text}"
        )

    try:
        result = response.json()
    except json.JSONDecodeError as exc:
        raise PluginFatalError(f"创建任务返回非 JSON 响应: {exc}") from exc

    if str(result.get("code") or "").lower() not in {"", "success", "200"}:
        raise PluginFatalError(f"创建任务失败: {result.get('message') or '未知错误'}")
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    task_id = data.get("id") or data.get("task_id")
    if not task_id:
        raise PluginFatalError("创建任务失败: 响应中缺少 task_id/id")
    _log_event("create_task.success", task_id=task_id, trace_id=trace_id)
    return str(task_id), data


def _normalize_task_status(raw_status):
    status = str(raw_status or "").strip().lower()
    if status in {
        "running",
        "processing",
        "pending",
        "queued",
        "submitted",
        "in_progress",
    }:
        return "running"
    if status in {"completed", "succeeded", "success"}:
        return "completed"
    if status in {"failed", "error", "failure"}:
        return "failed"
    return "unknown"


def _extract_video_url_from_status(task_data):
    if not isinstance(task_data, dict):
        return None
    content = task_data.get("content", {})
    if isinstance(content, dict):
        if content.get("video_url"):
            return content.get("video_url")
        if content.get("url"):
            return content.get("url")
    return task_data.get("video_url") or task_data.get("url")


def _poll_task_status(
    api_key,
    task_query_url,
    task_id,
    timeout,
    max_attempts,
    poll_interval,
    progress_callback=None,
):
    endpoint = f"{_normalize_base_url(task_query_url)}/{task_id}"
    previous_status = None

    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        trace_id = _new_trace_id()
        headers = _build_auth_headers(
            api_key, include_content_type=True, trace_id=trace_id
        )
        request_snapshot = {
            "endpoint": endpoint,
            "task_id": str(task_id),
            "timeout": int(timeout),
            "max_attempts": int(max_attempts),
            "poll_interval": int(poll_interval),
            "trace_id": trace_id,
            "headers": {
                "Authorization": f"Bearer {_mask_api_key(api_key)}",
                "Content-Type": headers.get("Content-Type"),
                "X-Trace-ID": trace_id,
            },
        }
        _log_event(
            "poll_task.request",
            attempt=attempt,
            request=request_snapshot,
            video_task_id=str(task_id),
        )

        try:
            response = _request_with_trace(
                method="GET",
                url=endpoint,
                headers=headers,
                timeout=timeout,
                interface_name="query_task_status",
                task_id=str(task_id),
                log_once_key=f"query_task_status:{str(task_id)}",
            )
        except requests.RequestException as exc:
            _log_event(
                "poll_task.query_error",
                task_id=task_id,
                attempt=attempt,
                error=f"请求异常: {exc}",
            )
            if progress_callback:
                progress_callback(
                    f"状态查询异常，第 {attempt} 次将在 {int(poll_interval)} 秒后重试"
                )
            time.sleep(poll_interval)
            continue

        try:
            _ensure_success_response(response, "查询任务状态")
        except PluginFatalError as exc:
            _log_event(
                "poll_task.query_error",
                task_id=task_id,
                attempt=attempt,
                error=str(exc),
            )
            if progress_callback:
                progress_callback(
                    f"状态查询失败，第 {attempt} 次将在 {int(poll_interval)} 秒后重试"
                )
            time.sleep(poll_interval)
            continue

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            _log_event(
                "poll_task.query_error",
                task_id=task_id,
                attempt=attempt,
                error=f"状态查询返回非 JSON 响应: {exc}",
            )
            if progress_callback:
                progress_callback(
                    f"状态查询返回非 JSON，第 {attempt} 次将在 {int(poll_interval)} 秒后重试"
                )
            time.sleep(poll_interval)
            continue

        payload = data.get("data") if isinstance(data.get("data"), dict) else data
        status = _normalize_task_status(payload.get("status"))
        if status != previous_status:
            _log_event(
                "poll_task.status",
                task_id=task_id,
                video_task_id=str(task_id),
                status=status,
                attempt=attempt,
                trace_id=trace_id,
            )
            previous_status = status
        if status == "running":
            if progress_callback:
                progress_callback(f"任务进行中 (第 {attempt} 次查询)")
            time.sleep(poll_interval)
            continue
        if status == "completed":
            return payload, _extract_video_url_from_status(payload)
        if status == "failed":
            raw_error = payload.get("error")
            if isinstance(raw_error, dict):
                raw_error = (
                    raw_error.get("message")
                    or raw_error.get("reason")
                    or json.dumps(raw_error, ensure_ascii=False)
                )
            reason = (
                payload.get("fail_reason")
                or payload.get("reason")
                or payload.get("message")
                or raw_error
                or "未知原因"
            )
            _log_event(
                "poll_task.failed_stop",
                task_id=task_id,
                attempt=attempt,
                reason=reason,
            )
            raise PluginFatalError(f"任务失败: {reason}")

        _log_event(
            "poll_task.unknown_retry",
            task_id=task_id,
            attempt=attempt,
            raw_status=data.get("status"),
            retry_after_seconds=int(poll_interval),
        )
        if progress_callback:
            progress_callback(
                f"任务状态未知({data.get('status')})，将在 {int(poll_interval)} 秒后继续查询"
            )
        time.sleep(poll_interval)

    _log_event(
        "poll_task.max_attempts_exceeded",
        task_id=task_id,
        max_attempts=int(max_attempts),
        poll_interval=int(poll_interval),
    )
    raise PluginFatalError(f"超过最大轮询次数({int(max_attempts)})，任务仍未完成")


def _task_root_from_base_url(base_url):
    _ = base_url
    return ""


def _download_video(api_key, task_query_url, task_id, video_url, output_path, timeout):
    _ = task_query_url

    headers = {
        "User-Agent": DOWNLOAD_USER_AGENT,
        "Referer": DOWNLOAD_REFERER,
        "Accept": "*/*",
    }
    if str(api_key or "").strip():
        headers["Authorization"] = f"Bearer {str(api_key or '').strip()}"

    tried = []
    for target_url in [video_url]:
        if not target_url:
            continue
        tried.append(target_url)
        _log_event("download.try", task_id=task_id, url=target_url)
        try:
            response = _request_with_trace(
                method="GET",
                url=target_url,
                headers=headers,
                timeout=timeout,
                interface_name="download_video",
                task_id=str(task_id),
            )
            if response.status_code == 200:
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                with open(output_path, "wb") as video_file:
                    video_file.write(response.content)
                _log_event("download.success", task_id=task_id, output_path=output_path)
                return output_path
        except requests.RequestException:
            continue

    raise PluginFatalError(f"下载视频失败，已尝试: {', '.join(tried)}")


def _sanitize_params(raw_params=None):
    """清洗并规范化参数"""
    raw_params = raw_params or {}
    params = _default_params.copy()
    params.update(raw_params)

    try:
        raw_schema_version = int(raw_params.get("config_schema_version", 1) or 1)
    except (TypeError, ValueError):
        raw_schema_version = 1

    # Migrate legacy configs that inherited the old default poll interval (5s).
    if (
        raw_schema_version < CONFIG_SCHEMA_VERSION
        and raw_params.get("poll_interval") == LEGACY_DEFAULT_POLL_INTERVAL
    ):
        params["poll_interval"] = DEFAULT_POLL_INTERVAL

    params["config_schema_version"] = CONFIG_SCHEMA_VERSION

    params["model"] = _normalize_model(params.get("model"))
    params["resolution"] = _normalize_resolution(
        params.get("resolution"), params["model"]
    )
    params["ratio"] = _normalize_aspect_ratio(params.get("ratio"))
    params["duration"] = _normalize_duration(params.get("duration"))
    params["generate_audio"] = _normalize_audio_generation(params.get("generate_audio"))
    params["web_search"] = _normalize_web_search(params.get("web_search"))
    params["base_url"] = _normalize_base_url(
        params.get("base_url") or _DEFAULT_API_BASE_URL
    )
    task_create_url, task_query_url = _build_task_endpoints(params["base_url"])
    params["task_create_url"] = task_create_url
    params["task_query_url"] = task_query_url
    params["asset_base_url"] = _DEFAULT_ASSET_BASE_URL
    params["audit_access_token"] = str(params.get("audit_access_token", "")).strip()
    params["audit_callback_url"] = str(params.get("audit_callback_url", "")).strip()
    params["tos_ak"] = str(params.get("tos_ak", "")).strip()
    params["tos_sk"] = str(params.get("tos_sk", "")).strip()
    params["tos_endpoint"] = _DEFAULT_TOS_ENDPOINT
    params["tos_region"] = _DEFAULT_TOS_REGION
    params["tos_bucket"] = _DEFAULT_TOS_BUCKET
    style = str(params.get("video_style", "其他风格") or "").strip()
    style_lc = style.lower()
    if (
        "仿真" in style
        or "真人" in style
        or style_lc in {"human", "human_style", "realistic"}
    ):
        params["video_style"] = "仿真人风格"
    else:
        params["video_style"] = "其他风格"
    params["audit_test_only"] = _normalize_web_search(params.get("audit_test_only"))

    pixel_width, pixel_height = _get_physical_pixels(
        params["resolution"], params["ratio"]
    )
    params["pixel_width"] = pixel_width
    params["pixel_height"] = pixel_height

    _validate_image_constraints(params.get("image_path"))

    return params


def _normalize_polling_config(params):
    timeout = int(params.get("timeout", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT)
    max_attempts = int(
        params.get("max_poll_attempts", DEFAULT_MAX_POLL_ATTEMPTS)
        or DEFAULT_MAX_POLL_ATTEMPTS
    )
    poll_interval = int(
        params.get("poll_interval", DEFAULT_POLL_INTERVAL) or DEFAULT_POLL_INTERVAL
    )
    return {
        "timeout": max(timeout, 30),
        "max_poll_attempts": max(max_attempts, 1),
        "poll_interval": max(poll_interval, 1),
    }


def _normalize_terminal_status(status, error=None):
    normalized = _normalize_task_status(status)
    if normalized == "completed":
        return "completed"
    if error and "超过最大轮询次数" in str(error):
        return "timeout"
    return "failed"


def _build_orchestration_result(
    task_id=None,
    status="failed",
    output_path=None,
    video_url=None,
    error=None,
    meta=None,
):
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
    polling = _normalize_polling_config(params)
    task_create_url = _normalize_base_url(
        params.get("task_create_url", _DEFAULT_TASK_CREATE_URL)
    )
    task_query_url = _normalize_base_url(
        params.get("task_query_url", _DEFAULT_TASK_QUERY_URL)
    )
    asset_base_url = _normalize_base_url(
        params.get("asset_base_url", _DEFAULT_ASSET_BASE_URL)
    )
    api_key = params.get("api_key", "")
    prompt = context.get("prompt", "")
    reference_images = context.get("reference_images")
    reference_videos = context.get("reference_videos")
    reference_audios = context.get("reference_audios")
    output_dir = context.get("output_dir", context.get("project_path", os.getcwd()))
    viewer_index = context.get("viewer_index", 0)
    prompt_text = str(prompt or "")
    _start_request_trace_session(task_id=f"viewer_{int(viewer_index)}")

    task_id = None
    video_url = None
    task_log_id = None
    try:
        _log_event("workflow.start", output_dir=output_dir, viewer_index=viewer_index)
        _log_event(
            "workflow.params",
            params=_build_params_log_snapshot(params),
            prompt_length=len(prompt_text),
            has_reference_images=bool(reference_images),
            has_reference_videos=bool(reference_videos),
            has_reference_audios=bool(reference_audios),
        )
        progress_callback("参数校验完成")

        # --- 素材审核集成逻辑 ---
        audit_test_only = bool(params.get("audit_test_only"))
        audited_images = reference_images
        audit_triggered = False
        audit_task_id = None
        audit_track_id = None
        if params.get("video_style") == "仿真人风格" and reference_images:
            audit_triggered = True
            progress_callback("正在进行人像素材审核...")
            _log_event("workflow.audit_trigger", style="仿真人风格")

            # V2 审核链路只允许公网 URL，拒绝本地文件和 Base64。
            raw_images = _normalize_list_or_single(reference_images)
            url_images = [
                _normalize_or_upload_media_url(img, "审核参考图", params)
                for img in raw_images
            ]

            # 调用审核接口
            asset_urls, audit_task_id, audit_track_id = _call_material_audit_api(
                asset_base_url=asset_base_url,
                audit_access_token=params.get("audit_access_token"),
                images=url_images,
                callback_url=params.get("audit_callback_url"),
                timeout=polling["timeout"],
                poll_interval=DEFAULT_AUDIT_POLL_INTERVAL,
            )

            if asset_urls:
                audited_images = asset_urls
                _log_event(
                    "workflow.audit_completed",
                    asset_urls=asset_urls,
                    audit_task_id=audit_task_id,
                    track_id=audit_track_id,
                )
            else:
                _log_event("workflow.audit_failed", reason="未获取到 Asset URL")
                raise PluginFatalError("素材审核未能返回有效的资源链接")

        if audit_test_only:
            if not audit_triggered:
                raise PluginFatalError(
                    "审核测试模式要求：视频风格为“仿真人风格”且至少提供 1 张参考图"
                )
            progress_callback("审核测试完成（未调用视频生成接口）")
            _log_event("workflow.audit_test_only.success", asset_urls=audited_images)
            task_log_id = _insert_task_log(
                {
                    "api_task_id": None,
                    "model_name": params.get("model"),
                    "model_display": params.get("model"),
                    "prompt": str(prompt or "")[:500],
                    "aspect_ratio": params.get("ratio"),
                    "duration": str(params.get("duration")),
                    "generation_mode": "audit_test_only",
                    "status": "success",
                    "metadata": {
                        "polling": polling,
                        "video_style": params.get("video_style"),
                        "audited": True,
                        "audit_test_only": True,
                        "audit_assets": audited_images,
                        "audit_task_id": audit_task_id,
                        "audit_track_id": audit_track_id,
                    },
                }
            )
            return _build_orchestration_result(
                task_id=f"audit-test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                status="completed",
                output_path=None,
                video_url=None,
                error=None,
                meta={
                    "polling": polling,
                    "audit_test_only": True,
                    "audit_assets": audited_images,
                    "audit_task_id": audit_task_id,
                    "audit_track_id": audit_track_id,
                    "task_log_id": task_log_id,
                },
            )

        task_log_id = _insert_task_log(
            {
                "api_task_id": None,
                "model_name": params.get("model"),
                "model_display": params.get("model"),
                "prompt": str(prompt or "")[:500],
                "aspect_ratio": params.get("ratio"),
                "duration": str(params.get("duration")),
                "generation_mode": "zlhub_seedance",
                "status": "running",
                "metadata": {
                    "polling": polling,
                    "video_style": params.get("video_style"),
                    "audited": bool(audit_triggered),
                    "audit_test_only": False,
                    "audit_task_id": audit_task_id,
                    "audit_track_id": audit_track_id,
                },
            }
        )

        payload = _build_create_payload(
            params=params,
            prompt=prompt,
            reference_images=audited_images,
            reference_videos=reference_videos,
            reference_audios=reference_audios,
        )
        payload_snapshot = _build_payload_log_snapshot(payload)
        payload_file = _persist_request_payload(payload)
        _log_event(
            "create_task.payload",
            payload=payload_snapshot,
            payload_file=payload_file,
        )
        _update_task_log(
            task_log_id,
            metadata=json.dumps(
                {
                    "polling": polling,
                    "video_style": params.get("video_style"),
                    "audited": bool(audit_triggered),
                    "audit_test_only": False,
                    "audit_task_id": audit_task_id,
                    "audit_track_id": audit_track_id,
                    "request_payload": payload_snapshot,
                    "request_payload_file": payload_file,
                },
                ensure_ascii=False,
            ),
        )

        task_id, _ = _create_task(api_key, task_create_url, payload, polling["timeout"])
        _update_task_log(task_log_id, api_task_id=task_id)
        progress_callback("任务已创建")
        initial_poll_delay = int(DEFAULT_INITIAL_POLL_DELAY_SECONDS)
        _log_event(
            "poll_task.initial_delay",
            task_id=task_id,
            delay_seconds=initial_poll_delay,
            reason="等待任务落库，避免创建后立刻查询出现 404",
        )
        progress_callback(f"任务已创建，等待 {initial_poll_delay} 秒后开始状态轮询")
        time.sleep(initial_poll_delay)
        progress_callback("状态轮询中")

        status_data, video_url = _poll_task_status(
            api_key=api_key,
            task_query_url=task_query_url,
            task_id=task_id,
            timeout=polling["timeout"],
            max_attempts=polling["max_poll_attempts"],
            poll_interval=polling["poll_interval"],
            progress_callback=progress_callback,
        )

        final_output_path = context.get("output_path") or _default_output_path(
            output_dir, viewer_index, task_id
        )
        progress_callback("下载中")

        downloaded_path = _download_video(
            api_key=api_key,
            task_query_url=task_query_url,
            task_id=task_id,
            video_url=video_url,
            output_path=final_output_path,
            timeout=polling["timeout"],
        )
        progress_callback("完成")
        _log_event("workflow.success", task_id=task_id, output_path=downloaded_path)
        _update_task_log(
            task_log_id,
            status="success",
            video_url=video_url,
            local_path=downloaded_path,
            error=None,
        )

        return _build_orchestration_result(
            task_id=task_id,
            status=status_data.get("status"),
            output_path=downloaded_path,
            video_url=video_url,
            error=None,
            meta={
                "polling": polling,
                "audit_task_id": audit_task_id,
                "audit_track_id": audit_track_id,
                "video_task_id": task_id,
            },
        )
    except Exception as exc:
        wrapped_error = (
            exc if isinstance(exc, PluginFatalError) else PluginFatalError(str(exc))
        )
        progress_callback("失败")
        _log_event("workflow.failed", task_id=task_id, error=str(wrapped_error))
        status = "download_failed" if "下载视频失败" in str(wrapped_error) else "failed"
        _update_task_log(
            task_log_id, status=status, video_url=video_url, error=str(wrapped_error)
        )
        return _build_orchestration_result(
            task_id=task_id,
            status="failed",
            output_path=None,
            video_url=video_url,
            error=wrapped_error,
            meta={"polling": polling},
        )


def _map_orchestration_to_plugin_output(result):
    if result.get("status") == "completed":
        meta = result.get("meta") or {}
        if meta.get("audit_test_only"):
            return []
        if result.get("output_path"):
            output_path = result["output_path"]
            return [output_path]
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
    """Phase 3 compatibility wrapper. Prefer run_seedance_workflow(context) in Phase 4+."""
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


def get_params():
    """返回插件配置参数，由宿主程序调用以生成 UI"""
    raw_params = load_plugin_config(_PLUGIN_FILE) or {}
    params = _sanitize_params(raw_params)

    # 如果参数有变化（比如新增了字段或值被规范化），持久化一份
    if raw_params != params:
        save_plugin_config(_PLUGIN_FILE, params)

    return params


def generate(context):
    """插件主入口点（Phase 4 已完成编排函数，Phase 5 进行宿主入口接线与 UI/日志集成）"""
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
            return {"ok": False, "error": "未选择任务"}
        rows = []
        conn = _db_conn()
        try:
            for task_id in task_ids:
                row = conn.execute(
                    "SELECT * FROM video_task_logs WHERE id = ?", (int(task_id),)
                ).fetchone()
                if row:
                    rows.append(dict(row))
        finally:
            conn.close()
        results = [_manual_download_video(row) for row in rows]
        return {"ok": True, "results": results}
    return {"ok": False, "error": f"未知动作: {action}"}


_init_task_log_db()
_append_file_log("INFO", f"module.loaded version={_PLUGIN_VERSION}")


if __name__ == "__main__":
    required_funcs = [
        "_build_auth_headers",
        "_build_create_payload",
        "_create_task",
        "_poll_task_status",
        "_download_video",
        "_normalize_polling_config",
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
