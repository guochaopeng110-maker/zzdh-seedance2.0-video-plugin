# -*- coding: utf-8 -*-
"""
TDu&ZLHub Seedance 2.0 视频生成插件。
对接 ZLHub 中转平台，支持 Seedance 2.0 视频大模型。
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

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
except Exception:
    default_backend = None
    padding = None
    Cipher = None
    algorithms = None
    modes = None

# 导入插件工具类
try:
    from plugin_utils import load_plugin_config, save_plugin_config
except ImportError:

    def load_plugin_config(path):
        return {}

    def save_plugin_config(path, config):
        return None


PLUGIN_ERROR_PREFIX = "PLUGIN_ERROR:::"
_PLUGIN_VERSION = "1.1.0"
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


class PluginFatalError(Exception):
    """插件致命错误，宿主应直接提示用户并终止流程。"""

    def __init__(self, message):
        text = str(message)
        if not text.startswith(PLUGIN_ERROR_PREFIX):
            text = f"{PLUGIN_ERROR_PREFIX}{text}"
        super().__init__(text)


_PLUGIN_FILE = __file__


class AuditAESCipher:
    """素材审核接口专用的 AES-256-ECB-PKCS7 加解密类"""

    def __init__(self, key_hex):
        if not all([Cipher, algorithms, modes, padding, default_backend]):
            raise PluginFatalError("素材审核依赖缺失: cryptography 未安装或不可用")
        try:
            self.key = bytes.fromhex(key_hex)
            if len(self.key) != 32:
                raise ValueError("AES Key 长度必须为 32 字节 (64 位 hex)")
        except Exception as e:
            raise PluginFatalError(f"AES Key 格式错误: {str(e)}")
        self.backend = default_backend()

    def encrypt(self, plaintext):
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode("utf-8")) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.key), modes.ECB(), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(ciphertext).decode("utf-8")

    def decrypt(self, ciphertext_b64):
        ciphertext = base64.b64decode(ciphertext_b64)
        cipher = Cipher(algorithms.AES(self.key), modes.ECB(), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        return data.decode("utf-8")


# 配置选项
_BASE_URL_OPTIONS = [
    (
        "ZLHub",
        "https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks",
    ),
]
_DEFAULT_BASE_URL = _BASE_URL_OPTIONS[0][1]
_DEFAULT_AUDIT_API_URL = "http://118.196.112.236:3428/api/moderation/image"
_AUDIT_API_URL_ENV_KEYS = ("ZLHUB_AUDIT_API_URL", "AUDIT_API_URL")
_FIXED_AUDIT_AES_KEY = (
    "25ef2ee94546a00817f68d5bc2b7c6e62a5ca11dd2acdb876defdbc0c48a9944"
)

DEFAULT_MODEL = "doubao-seedance-2.0"
DEFAULT_RESOLUTION = "720p"
DEFAULT_RATIO = "adaptive"
DEFAULT_DURATION = 5
DEFAULT_GENERATE_AUDIO = True

DEFAULT_RESOLUTIONS = ["480p", "720p"]
DEFAULT_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
DEFAULT_TIMEOUT = 900
DEFAULT_MAX_POLL_ATTEMPTS = 300
DEFAULT_POLL_INTERVAL = 180
DEFAULT_INITIAL_POLL_DELAY_SECONDS = 180
DOWNLOAD_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
)
DOWNLOAD_REFERER = "https://zlhub.xiaowaiyou.cn/"

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
        "audit_user_id": params.get("audit_user_id"),
        "audit_test_only": bool(params.get("audit_test_only")),
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
        resp = requests.get(url, headers=headers, timeout=120)
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
    _REQUEST_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = _safe_filename(task_id) if task_id else "pending"
    file_path = _REQUEST_PAYLOAD_DIR / f"request_payload_{stamp}_{suffix}.json"
    with open(file_path, "w", encoding="utf-8") as fw:
        fw.write(json.dumps(payload or {}, ensure_ascii=False, indent=2))
    return str(file_path)


def _safe_progress_callback(progress_callback):
    if callable(progress_callback):
        return progress_callback

    def _noop(_message):
        return None

    return _noop


def get_info():
    """返回插件元数据"""
    return {
        "name": "TDu&ZLHub Seedance 视频生成",
        "description": "对接 ZLHub 中转平台的 Seedance 2.0 视频大模型接口。",
        "version": _PLUGIN_VERSION,
        "author": "Z Code",
    }


def _build_default_params():
    """构建默认参数，与 API 文档及 UI 保持一致"""
    return {
        "api_key": "",
        "base_url": _DEFAULT_BASE_URL,
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
        "audit_user_id": "",
        "audit_aes_key": "",
        "audit_test_only": False,
    }


_default_params = _build_default_params()


def _normalize_resolution(value):
    resolution = str(value or "").strip().lower()
    if resolution in DEFAULT_RESOLUTIONS:
        return resolution
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


def _is_remote_or_asset(value):
    text = str(value or "").strip().lower()
    return text.startswith(("http://", "https://", "data:", "asset://"))


def _build_auth_headers(api_key, include_content_type=True):
    key_text = str(api_key or "").strip()
    if not key_text:
        raise PluginFatalError("API Key 未设置")

    headers = {"Authorization": f"Bearer {key_text}"}
    if include_content_type:
        headers["Content-Type"] = "application/json"
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


def file_to_base64(file_path):
    path_text = str(file_path or "").strip()
    if not path_text:
        raise PluginFatalError("图片路径为空")
    if _is_remote_or_asset(path_text):
        return path_text
    if not os.path.exists(path_text):
        raise PluginFatalError(f"参考图片不存在: {path_text}")

    with open(path_text, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    mime_type = _guess_mime_type(path_text)
    return f"data:{mime_type};base64,{encoded}"


def _env_first(keys):
    for key in keys:
        value = str(os.environ.get(key, "")).strip()
        if value:
            return value
    return ""


def _resolve_audit_api_url():
    return _env_first(_AUDIT_API_URL_ENV_KEYS) or _DEFAULT_AUDIT_API_URL


def _resolve_audit_aes_key(audit_aes_key):
    _ = audit_aes_key
    return _FIXED_AUDIT_AES_KEY


def _call_material_audit_api(audit_user_id, audit_aes_key, images, timeout=120):
    image_list = []
    for image in _normalize_list_or_single(images):
        item = str(image or "").strip()
        if item:
            image_list.append(item)
    if not image_list:
        raise PluginFatalError("素材审核失败: images 不能为空")

    try:
        user_id = int(str(audit_user_id or "").strip())
    except (TypeError, ValueError) as exc:
        raise PluginFatalError("素材审核失败: audit_user_id 必须为数字") from exc
    if user_id <= 0:
        raise PluginFatalError("素材审核失败: audit_user_id 必须大于 0")

    cipher = AuditAESCipher(_resolve_audit_aes_key(audit_aes_key))
    payload_plain = json.dumps(
        {"images": image_list}, ensure_ascii=False, separators=(",", ":")
    )
    request_payload = {
        "user_id": user_id,
        "encrypted_data": cipher.encrypt(payload_plain),
    }

    endpoint = _resolve_audit_api_url()
    request_timeout = max(5, min(int(timeout or 120), 120))
    _log_event(
        "audit.request",
        endpoint=endpoint,
        user_id=user_id,
        image_count=len(image_list),
    )
    try:
        response = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            json=request_payload,
            timeout=request_timeout,
        )
    except requests.RequestException as exc:
        raise PluginFatalError(f"素材审核请求失败: {exc}") from exc

    if response.status_code != 200:
        raise PluginFatalError(
            f"素材审核请求失败: HTTP {response.status_code} - {response.text}"
        )

    try:
        response_json = response.json()
    except json.JSONDecodeError as exc:
        raise PluginFatalError("素材审核返回非 JSON 响应") from exc

    if not response_json.get("encrypted_data"):
        code = response_json.get("code")
        message = response_json.get("message") or response_json.get("msg") or "未知错误"
        suffix = f" (code={code})" if code is not None else ""
        raise PluginFatalError(f"素材审核失败: {message}{suffix}")

    try:
        decrypted = cipher.decrypt(response_json["encrypted_data"])
        decrypted_json = json.loads(decrypted)
    except Exception as exc:
        raise PluginFatalError(f"素材审核响应解密失败: {exc}") from exc

    if response_json.get("code") not in (None, 200):
        code = response_json.get("code")
        message = response_json.get("message") or "未知错误"
        raise PluginFatalError(f"素材审核失败: {message} (code={code})")

    items = decrypted_json.get("items")
    if not isinstance(items, list):
        raise PluginFatalError("素材审核失败: 响应缺少 items")

    asset_urls = []
    for item in items:
        if not isinstance(item, dict):
            continue
        asset_url = str(item.get("asset_url") or "").strip()
        if not asset_url:
            continue
        if not asset_url.lower().startswith("asset://"):
            raise PluginFatalError(f"素材审核失败: 非法资源地址 {asset_url}")
        asset_urls.append(asset_url)

    if len(asset_urls) < len(image_list):
        raise PluginFatalError(
            f"素材审核失败: 返回资源数不足 ({len(asset_urls)}/{len(image_list)})"
        )

    _log_event(
        "audit.success",
        review_batch_id=decrypted_json.get("review_batch_id"),
        asset_count=len(asset_urls),
    )
    return asset_urls


def _build_content_items(
    prompt,
    reference_images=None,
    reference_videos=None,
    reference_audios=None,
    role_mode="reference_image",
):
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        raise PluginFatalError("Prompt 不能为空")

    content = [{"type": "text", "text": prompt_text}]

    for image in _normalize_list_or_single(reference_images):
        image_url = file_to_base64(image)
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_url},
                "role": role_mode or "reference_image",
            }
        )

    for video in _normalize_list_or_single(reference_videos):
        content.append(
            {
                "type": "video_url",
                "video_url": {"url": str(video)},
                "role": "reference_video",
            }
        )

    for audio in _normalize_list_or_single(reference_audios):
        content.append(
            {
                "type": "audio_url",
                "audio_url": {"url": str(audio)},
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
            prompt, reference_images, reference_videos, reference_audios
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


def _create_task(api_key, base_url, payload, timeout):
    endpoint = _normalize_base_url(base_url)
    _log_event(
        "create_task.request",
        endpoint=endpoint,
        timeout=timeout,
        api_key=_mask_api_key(api_key),
    )
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

    task_id = result.get("id") or result.get("task_id")
    if not task_id:
        raise PluginFatalError("创建任务失败: 响应中缺少 task_id/id")
    _log_event("create_task.success", task_id=task_id)
    return str(task_id), result


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
    base_url,
    task_id,
    timeout,
    max_attempts,
    poll_interval,
    progress_callback=None,
):
    endpoint = f"{_normalize_base_url(base_url)}/{task_id}"
    headers = _build_auth_headers(api_key, include_content_type=True)
    previous_status = None
    request_snapshot = {
        "endpoint": endpoint,
        "task_id": str(task_id),
        "timeout": int(timeout),
        "max_attempts": int(max_attempts),
        "poll_interval": int(poll_interval),
        "headers": {
            "Authorization": f"Bearer {_mask_api_key(api_key)}",
            "Content-Type": headers.get("Content-Type"),
        },
    }

    attempt = 0
    while True:
        attempt += 1
        _log_event(
            "poll_task.request",
            attempt=attempt,
            request=request_snapshot,
        )

        try:
            response = requests.get(endpoint, headers=headers, timeout=timeout)
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

        status = _normalize_task_status(data.get("status"))
        if status != previous_status:
            _log_event(
                "poll_task.status", task_id=task_id, status=status, attempt=attempt
            )
            previous_status = status
        if status == "running":
            if progress_callback:
                progress_callback(f"任务进行中 (第 {attempt} 次查询)")
            time.sleep(poll_interval)
            continue
        if status == "completed":
            return data, _extract_video_url_from_status(data)
        if status == "failed":
            raw_error = data.get("error")
            if isinstance(raw_error, dict):
                raw_error = (
                    raw_error.get("message")
                    or raw_error.get("reason")
                    or json.dumps(raw_error, ensure_ascii=False)
                )
            reason = (
                data.get("fail_reason")
                or data.get("reason")
                or data.get("message")
                or raw_error
                or "未知原因"
            )
            _log_event(
                "poll_task.failed_retry",
                task_id=task_id,
                attempt=attempt,
                reason=reason,
                retry_after_seconds=int(poll_interval),
            )
            if progress_callback:
                progress_callback(
                    f"任务状态失败({reason})，将在 {int(poll_interval)} 秒后继续查询"
                )
            time.sleep(poll_interval)
            continue

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


def _task_root_from_base_url(base_url):
    endpoint = _normalize_base_url(base_url)
    marker = "/v1/proxy/ark/contents/generations/tasks"
    if marker in endpoint:
        return endpoint.split(marker, 1)[0]
    return ""


def _download_video(api_key, base_url, task_id, video_url, output_path, timeout):
    root = _task_root_from_base_url(base_url)
    fallback_url = f"{root}/v1/videos/{task_id}/content" if root else None

    headers = {
        "User-Agent": DOWNLOAD_USER_AGENT,
        "Referer": DOWNLOAD_REFERER,
        "Accept": "*/*",
    }
    if root:
        headers["Authorization"] = f"Bearer {str(api_key or '').strip()}"

    tried = []
    for target_url in [video_url, fallback_url]:
        if not target_url:
            continue
        tried.append(target_url)
        _log_event("download.try", task_id=task_id, url=target_url)
        try:
            response = requests.get(target_url, headers=headers, timeout=timeout)
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

    params["model"] = _normalize_model(params.get("model"))
    params["resolution"] = _normalize_resolution(params.get("resolution"))
    params["ratio"] = _normalize_aspect_ratio(params.get("ratio"))
    params["duration"] = _normalize_duration(params.get("duration"))
    params["generate_audio"] = _normalize_audio_generation(params.get("generate_audio"))
    params["web_search"] = _normalize_web_search(params.get("web_search"))
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
    params["audit_user_id"] = str(params.get("audit_user_id", "")).strip()
    params["audit_aes_key"] = str(params.get("audit_aes_key", "")).strip()
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
    base_url = _normalize_base_url(params.get("base_url", _DEFAULT_BASE_URL))
    api_key = params.get("api_key", "")
    prompt = context.get("prompt", "")
    reference_images = context.get("reference_images")
    reference_videos = context.get("reference_videos")
    reference_audios = context.get("reference_audios")
    output_dir = context.get("output_dir", context.get("project_path", os.getcwd()))
    viewer_index = context.get("viewer_index", 0)
    prompt_text = str(prompt or "")

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
        if params.get("video_style") == "仿真人风格" and reference_images:
            audit_triggered = True
            progress_callback("正在进行人像素材审核...")
            _log_event("workflow.audit_trigger", style="仿真人风格")

            # 转换为 Base64 列表
            raw_images = _normalize_list_or_single(reference_images)
            b64_images = [file_to_base64(img) for img in raw_images]

            # 调用审核接口
            asset_urls = _call_material_audit_api(
                params.get("audit_user_id"), params.get("audit_aes_key"), b64_images
            )

            if asset_urls:
                audited_images = asset_urls
                _log_event("workflow.audit_completed", asset_urls=asset_urls)
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
                    "request_payload": payload_snapshot,
                    "request_payload_file": payload_file,
                },
                ensure_ascii=False,
            ),
        )

        task_id, _ = _create_task(api_key, base_url, payload, polling["timeout"])
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
            base_url=base_url,
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
            base_url=base_url,
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
            meta={"polling": polling},
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
