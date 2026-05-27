# -*- coding: utf-8 -*-
"""
Huimeng Seedance 视频生成插件。
对接 Huimeng 中转平台，支持多模型视频生成。
"""

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

try:
    from plugin_utils import load_plugin_config, save_plugin_config
except ImportError:

    def load_plugin_config(path):
        return {}

    def save_plugin_config(path, config):
        return None


PLUGIN_ERROR_PREFIX = "PLUGIN_ERROR:::"
_PLUGIN_VERSION = "1.0.0"
_PLUGIN_FILE = __file__
plugin_dir = Path(__file__).parent
_TASK_LOG_DB_PATH = plugin_dir / "video_task_logs.db"
_RUNTIME_LOG_DIR = plugin_dir / "logs"
_RUNTIME_LOG_FILE_PATH = (
    _RUNTIME_LOG_DIR / f"debug_runtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

_log_buffer = collections.deque(maxlen=2000)
_log_index = 0
_log_lock = threading.Lock()

_HUIMENG_TASKS_ENDPOINT = "https://api.huimengi.com/api/v1/tasks"
_IMAGE_UPLOAD_URL = "https://imageproxy.zhongzhuan.chat/api/upload"

MODEL_IDS = [
    "happyhorse-1.0",
    "seedance-2.0-value",
    "seedance-2.0-fast-value",
    "seedance-2.0",
    "seedance-2.0-fast",
]

MODEL_CONSTRAINTS = {
    "happyhorse-1.0": {
        "ratio": ["16:9", "9:16", "1:1", "4:3", "3:4"],
        "resolution": ["1080P", "720P"],
        "duration": [3, 15],
        "supports": {
            "generate_audio": False,
            "human_review": False,
            "reference_videos": False,
            "reference_audios": False,
            "reference_images": True,
        },
    },
    "seedance-2.0-value": {
        "ratio": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        "resolution": ["720p", "1080p"],
        "duration": [4, 15],
        "supports": {
            "generate_audio": True,
            "human_review": True,
            "reference_videos": True,
            "reference_audios": True,
            "reference_images": True,
        },
    },
    "seedance-2.0-fast-value": {
        "ratio": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        "resolution": ["720p", "1080p"],
        "duration": [4, 15],
        "supports": {
            "generate_audio": True,
            "human_review": True,
            "reference_videos": True,
            "reference_audios": True,
            "reference_images": True,
        },
    },
    "seedance-2.0": {
        "ratio": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        "resolution": ["480p", "720p", "1080p"],
        "duration": [4, 15],
        "supports": {
            "generate_audio": True,
            "human_review": True,
            "reference_videos": True,
            "reference_audios": True,
            "reference_images": True,
        },
    },
    "seedance-2.0-fast": {
        "ratio": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        "resolution": ["480p", "720p"],
        "duration": [4, 15],
        "supports": {
            "generate_audio": True,
            "human_review": True,
            "reference_videos": True,
            "reference_audios": True,
            "reference_images": True,
        },
    },
}


class PluginFatalError(Exception):
    def __init__(self, message):
        text = str(message)
        if not text.startswith(PLUGIN_ERROR_PREFIX):
            text = f"{PLUGIN_ERROR_PREFIX}{text}"
        super().__init__(text)


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
    line = f"[{ts}] [{str(level or 'INFO')}] {str(message or '')}\\n"
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
    text = f"[HuimengSeedance] {json.dumps(payload, ensure_ascii=False)}"
    print(text)
    _append_live_log("INFO", text)
    _append_file_log("INFO", text)


def _safe_progress_callback(progress_callback):
    if callable(progress_callback):
        return progress_callback

    def _noop(_message):
        return None

    return _noop


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
              prompt TEXT,
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
            (created_at, updated_at, api_task_id, model_name, prompt, status, error, video_url, local_path, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                entry.get("api_task_id"),
                entry.get("model_name"),
                entry.get("prompt"),
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


def _build_default_params():
    return {
        "api_key": "",
        "tasks_endpoint": _HUIMENG_TASKS_ENDPOINT,
        "model": "seedance-2.0",
        "ratio": "16:9",
        "resolution": "720p",
        "duration": 5,
        "generate_audio": True,
        "human_review": False,
        "timeout": 900,
        "max_poll_attempts": 180,
        "poll_interval": 180,
        "initial_poll_delay": 180,
    }


_default_params = _build_default_params()


def _normalize_model(model):
    model_text = str(model or "").strip()
    if model_text not in MODEL_IDS:
        return _default_params["model"]
    return model_text


def _normalize_bool(value, default=False):
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    return bool(default)


def _normalize_duration(duration, model):
    limits = MODEL_CONSTRAINTS[model]["duration"]
    try:
        val = int(duration)
    except Exception:
        val = _default_params["duration"]
    if val < limits[0]:
        return limits[0]
    if val > limits[1]:
        return limits[1]
    return val


def _normalize_by_enum(value, candidates, fallback):
    text = str(value or "").strip()
    return text if text in candidates else fallback


def _is_remote(value):
    text = str(value or "").strip().lower()
    return text.startswith(("http://", "https://", "data:", "asset://"))


def _normalize_multi_value_input(value, field_name="unknown"):
    if value is None:
        _log_event(
            "reference_input.normalized",
            field=field_name,
            raw_type="NoneType",
            normalized_count=0,
        )
        return []
    raw_type = type(value).__name__
    if isinstance(value, list):
        _log_event(
            "reference_input.normalized",
            field=field_name,
            raw_type=raw_type,
            normalized_count=len(value),
        )
        return value
    if isinstance(value, tuple):
        normalized = list(value)
        _log_event(
            "reference_input.normalized",
            field=field_name,
            raw_type=raw_type,
            normalized_count=len(normalized),
        )
        return normalized
    if isinstance(value, dict):
        # 兼容宿主传入的 {0: "...", 1: "..."} 形态
        items = []
        for k, v in value.items():
            try:
                sort_key = int(k)
            except Exception:
                sort_key = str(k)
            items.append((sort_key, v))
        items.sort(key=lambda x: x[0])
        normalized = [v for _, v in items]
        _log_event(
            "reference_input.normalized",
            field=field_name,
            raw_type=raw_type,
            normalized_count=len(normalized),
        )
        return normalized

    # 兼容可能的 JSON 字符串输入
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("[") or text.startswith("{"):
            try:
                parsed = json.loads(text)
                return _normalize_multi_value_input(parsed, field_name=field_name)
            except Exception:
                pass
    normalized = [value]
    _log_event(
        "reference_input.normalized",
        field=field_name,
        raw_type=raw_type,
        normalized_count=len(normalized),
    )
    return normalized


def _guess_mime_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


def upload_image_to_host(image_path, timeout=60):
    try:
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, _guess_mime_type(image_path))}
            response = requests.post(_IMAGE_UPLOAD_URL, files=files, timeout=timeout)
        if response.status_code != 200:
            _log_event("ref_image.upload_failed", status=response.status_code, path=image_path)
            return None
        data = response.json() if response.content else {}
        image_url = data.get("url")
        if image_url:
            return str(image_url)
        _log_event("ref_image.upload_missing_url", path=image_path)
        return None
    except Exception as e:
        _log_event("ref_image.upload_error", path=image_path, err=str(e))
        return None


def _normalize_reference_images(value):
    arr = _normalize_multi_value_input(value, field_name="reference_images")

    normalized = []
    for item in arr:
        path = str(item or "").strip()
        if not path:
            continue
        if _is_remote(path):
            normalized.append(path)
            continue
        if not os.path.exists(path):
            raise PluginFatalError(f"参考图片不存在: {path}")
        url = upload_image_to_host(path)
        if not url:
            raise PluginFatalError(f"参考图片上传失败: {path}")
        normalized.append(url)
    return normalized


def _normalize_reference_list(value, field_name):
    arr = _normalize_multi_value_input(value, field_name=field_name)
    out = []
    for item in arr:
        url = str(item or "").strip()
        if not url:
            continue
        if not _is_remote(url):
            raise PluginFatalError(f"{field_name} 仅支持公网 URL: {url}")
        out.append(url)
    return out


def _sanitize_params(raw_params=None):
    raw = raw_params or {}
    params = _default_params.copy()
    params.update(raw)

    model = _normalize_model(params.get("model"))
    cfg = MODEL_CONSTRAINTS[model]

    params["model"] = model
    params["ratio"] = _normalize_by_enum(params.get("ratio"), cfg["ratio"], cfg["ratio"][0])
    params["resolution"] = _normalize_by_enum(
        params.get("resolution"), cfg["resolution"], cfg["resolution"][0]
    )
    params["duration"] = _normalize_duration(params.get("duration"), model)

    supports = cfg["supports"]
    params["generate_audio"] = (
        _normalize_bool(params.get("generate_audio"), True)
        if supports["generate_audio"]
        else False
    )
    params["human_review"] = (
        _normalize_bool(params.get("human_review"), False)
        if supports["human_review"]
        else False
    )

    try:
        params["timeout"] = max(30, int(params.get("timeout", 900)))
    except Exception:
        params["timeout"] = 900
    try:
        params["max_poll_attempts"] = max(1, int(params.get("max_poll_attempts", 180)))
    except Exception:
        params["max_poll_attempts"] = 180
    try:
        params["poll_interval"] = max(1, int(params.get("poll_interval", 180)))
    except Exception:
        params["poll_interval"] = 180
    try:
        params["initial_poll_delay"] = max(
            0, int(params.get("initial_poll_delay", params["poll_interval"]))
        )
    except Exception:
        params["initial_poll_delay"] = params["poll_interval"]

    params["tasks_endpoint"] = str(params.get("tasks_endpoint") or _HUIMENG_TASKS_ENDPOINT).strip()
    params["api_key"] = str(params.get("api_key") or "").strip()

    return params


def _auth_headers(api_key, include_content_type=True):
    if not api_key:
        raise PluginFatalError("API Key 未设置")
    headers = {"Authorization": f"Bearer {api_key}"}
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _build_payload(params, prompt, reference_images=None, reference_videos=None, reference_audios=None):
    model = params["model"]
    supports = MODEL_CONSTRAINTS[model]["supports"]

    payload_params = {
        "prompt": str(prompt or "").strip(),
        "ratio": params["ratio"],
        "duration": params["duration"],
        "resolution": params["resolution"],
    }

    if supports["generate_audio"]:
        payload_params["generate_audio"] = bool(params["generate_audio"])
    if supports["human_review"]:
        payload_params["human_review"] = bool(params["human_review"])

    images = _normalize_reference_images(reference_images)
    if images and supports["reference_images"]:
        payload_params["reference_images"] = images

    if supports["reference_videos"]:
        vids = _normalize_reference_list(reference_videos, "reference_videos")
        if vids:
            payload_params["reference_videos"] = vids

    if supports["reference_audios"]:
        auds = _normalize_reference_list(reference_audios, "reference_audios")
        if auds:
            payload_params["reference_audios"] = auds

    return {"model": model, "params": payload_params}


def _create_task(api_key, tasks_endpoint, payload, timeout):
    _log_event("create_task.request", endpoint=tasks_endpoint, payload=payload)
    resp = requests.post(
        tasks_endpoint,
        headers=_auth_headers(api_key, include_content_type=True),
        json=payload,
        timeout=timeout,
    )
    if resp.status_code not in {200, 201}:
        _log_event(
            "create_task.failed",
            endpoint=tasks_endpoint,
            http_status=resp.status_code,
            response_text=(resp.text or "")[:1000],
        )
        raise PluginFatalError(f"创建任务失败: HTTP {resp.status_code} - {resp.text}")
    data = resp.json() if resp.content else {}
    task_id = data.get("task_id") or data.get("id")
    if not task_id:
        raise PluginFatalError("创建任务失败: 响应缺少 task_id")
    _log_event("create_task.success", endpoint=tasks_endpoint, task_id=str(task_id))
    return str(task_id), data


def _poll_task(api_key, tasks_endpoint, task_id, timeout, max_attempts, poll_interval, progress_callback):
    query_url = f"{tasks_endpoint.rstrip('/')}/{task_id}"
    for attempt in range(1, max_attempts + 1):
        resp = requests.get(query_url, headers=_auth_headers(api_key, include_content_type=False), timeout=timeout)
        if resp.status_code != 200:
            _log_event(
                "poll_task.attempt",
                task_id=task_id,
                attempt=attempt,
                max_attempts=max_attempts,
                http_status=resp.status_code,
                status="http_error",
            )
            if progress_callback:
                progress_callback(f"状态查询异常 HTTP {resp.status_code}，重试中")
            time.sleep(poll_interval)
            continue

        data = resp.json() if resp.content else {}
        status = str(data.get("status") or "").strip().lower()
        _log_event(
            "poll_task.attempt",
            task_id=task_id,
            attempt=attempt,
            max_attempts=max_attempts,
            http_status=resp.status_code,
            status=status or "unknown",
        )
        if status == "completed":
            result = data.get("result") or {}
            video_url = result.get("video_url")
            if not video_url:
                raise PluginFatalError("任务完成但未返回 video_url")
            _log_event(
                "poll_task.completed",
                task_id=task_id,
                status=status,
                video_url=str(video_url),
                response=data,
            )
            return data, str(video_url)

        if status == "failed":
            error_message = data.get("error_message") or data.get("message") or "未知错误"
            _log_event(
                "poll_task.failed",
                task_id=task_id,
                status=status,
                error_message=error_message,
                response=data,
            )
            raise PluginFatalError(f"任务失败: {error_message}")

        if progress_callback:
            progress_callback(f"任务状态: {status or 'unknown'} (第 {attempt} 次)")
        time.sleep(poll_interval)

    raise PluginFatalError("任务轮询超时")


def _download_video(video_url, output_path, timeout):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
    }
    resp = requests.get(video_url, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise PluginFatalError(f"下载视频失败: HTTP {resp.status_code}")
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "wb") as fw:
        fw.write(resp.content)
    return output_path


def _default_output_path(output_dir, viewer_index, task_id):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{int(viewer_index):04d}_huimeng_{task_id}_{stamp}.mp4"
    return os.path.join(output_dir, filename)


def _run_workflow(context):
    context = context or {}
    progress_callback = _safe_progress_callback(context.get("progress_callback"))
    params = _sanitize_params(context.get("plugin_params") if context.get("plugin_params") is not None else get_params())

    prompt = context.get("prompt", "")
    output_dir = context.get("output_dir", context.get("project_path", os.getcwd()))
    viewer_index = context.get("viewer_index", 0)

    task_log_id = None
    task_id = None
    video_url = None
    try:
        payload = _build_payload(
            params,
            prompt,
            reference_images=context.get("reference_images"),
            reference_videos=context.get("reference_videos"),
            reference_audios=context.get("reference_audios"),
        )

        task_log_id = _insert_task_log(
            {
                "api_task_id": None,
                "model_name": params["model"],
                "prompt": str(prompt or "")[:500],
                "status": "running",
                "metadata": {"payload": payload},
            }
        )

        progress_callback("任务创建中")
        task_id, _ = _create_task(params["api_key"], params["tasks_endpoint"], payload, params["timeout"])
        _update_task_log(task_log_id, api_task_id=task_id)

        progress_callback("状态轮询中")
        initial_poll_delay = int(params.get("initial_poll_delay", params["poll_interval"]))
        if initial_poll_delay > 0:
            progress_callback(f"任务已提交，等待 {initial_poll_delay} 秒后开始首次查询")
            time.sleep(initial_poll_delay)
        _, video_url = _poll_task(
            params["api_key"],
            params["tasks_endpoint"],
            task_id,
            params["timeout"],
            params["max_poll_attempts"],
            params["poll_interval"],
            progress_callback,
        )

        progress_callback("下载中")
        output_path = context.get("output_path") or _default_output_path(output_dir, viewer_index, task_id)
        final_path = _download_video(video_url, output_path, params["timeout"])

        _update_task_log(
            task_log_id,
            status="success",
            video_url=video_url,
            local_path=final_path,
            error=None,
        )
        _log_event(
            "workflow.success",
            task_id=task_id,
            video_url=video_url,
            output_path=final_path,
        )
        progress_callback("完成")
        return [final_path]
    except Exception as exc:
        wrapped = exc if isinstance(exc, PluginFatalError) else PluginFatalError(str(exc))
        _log_event(
            "workflow.failed",
            task_id=task_id,
            video_url=video_url,
            error=str(wrapped),
        )
        _update_task_log(task_log_id, status="failed", video_url=video_url, error=str(wrapped))
        progress_callback("失败")
        raise wrapped


def get_info():
    return {
        "name": "Huimeng Seedance 视频生成",
        "description": "对接 Huimeng 平台的视频生成插件。",
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
    _append_file_log("INFO", "generate.enter")
    ctx = dict(context or {})
    ctx["progress_callback"] = _safe_progress_callback(ctx.get("progress_callback"))
    return _run_workflow(ctx)


def get_buffered_logs(since_index=0):
    try:
        since = int(since_index or 0)
    except (TypeError, ValueError):
        since = 0
    with _log_lock:
        return [entry for entry in list(_log_buffer) if entry.get("index", 0) > since]


def handle_action(action, data=None):
    payload = data or {}
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
    return {"ok": False, "error": f"未知动作: {action}"}


_init_task_log_db()
_append_file_log("INFO", f"module.loaded version={_PLUGIN_VERSION}")


if __name__ == "__main__":
    required_funcs = [
        "get_info",
        "get_params",
        "generate",
        "handle_action",
        "_build_payload",
        "_create_task",
        "_poll_task",
        "_download_video",
    ]
    missing = [name for name in required_funcs if not callable(globals().get(name))]
    if missing:
        raise SystemExit(f"smoke check failed, missing callables: {missing}")
    print("smoke check passed")
