# -*- coding: utf-8 -*-
"""
ZLHub Seedance 2.0 视频生成插件。
对接 ZLHub 中转平台，支持 Seedance 2.0 视频大模型。
"""

import base64
import json
import mimetypes
import os
import time
from datetime import datetime

import requests

# 导入插件工具类
try:
    from plugin_utils import load_plugin_config, save_plugin_config
except ImportError:
    def load_plugin_config(path):
        return {}

    def save_plugin_config(path, config):
        return None


PLUGIN_ERROR_PREFIX = "PLUGIN_ERROR:::"


class PluginFatalError(Exception):
    """插件致命错误，宿主应直接提示用户并终止流程。"""

    def __init__(self, message):
        text = str(message)
        if not text.startswith(PLUGIN_ERROR_PREFIX):
            text = f"{PLUGIN_ERROR_PREFIX}{text}"
        super().__init__(text)


_PLUGIN_FILE = __file__

# 配置选项
_BASE_URL_OPTIONS = [
    ("ZLHub", "https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks"),
]
_DEFAULT_BASE_URL = _BASE_URL_OPTIONS[0][1]

DEFAULT_MODEL = "seedance-2.0"
DEFAULT_RESOLUTION = "720p"
DEFAULT_RATIO = "adaptive"
DEFAULT_DURATION = 5
DEFAULT_GENERATE_AUDIO = True

DEFAULT_RESOLUTIONS = ["480p", "720p"]
DEFAULT_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
DEFAULT_TIMEOUT = 900
DEFAULT_MAX_POLL_ATTEMPTS = 300
DEFAULT_POLL_INTERVAL = 5
DOWNLOAD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
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


def _log_event(event, **fields):
    payload = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "fields": fields or {},
    }
    print(f"[ZLHubSeedance] {json.dumps(payload, ensure_ascii=False)}")


def _safe_progress_callback(progress_callback):
    if callable(progress_callback):
        return progress_callback

    def _noop(_message):
        return None

    return _noop


def get_info():
    """返回插件元数据"""
    return {
        "name": "ZLHub Seedance 视频生成",
        "description": "对接 ZLHub 中转平台的 Seedance 2.0 视频大模型接口。",
        "version": "1.0.0",
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
    if path_text.startswith(("http://", "https://", "data:", "asset://")):
        return

    if not os.path.exists(path_text):
        raise PluginFatalError(f"参考图片不存在: {path_text}")

    ext = os.path.splitext(path_text)[1].lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise PluginFatalError(f"图片格式不支持: {ext or 'unknown'}，支持格式: {allowed}")

    size_bytes = os.path.getsize(path_text)
    if size_bytes >= MAX_IMAGE_SIZE_BYTES:
        raise PluginFatalError("图片大小超过 30MB 限制")


def _normalize_base_url(url):
    return str(url or "").strip().rstrip("/")


def _is_remote_or_asset(value):
    text = str(value or "")
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
        raise PluginFatalError(f"{operation_name}失败: HTTP {response.status_code} - {detail}")


def _normalize_list_or_single(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [item for item in value if item]
    if isinstance(value, dict):
        return [item for _, item in sorted(value.items(), key=lambda pair: str(pair[0])) if item]
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


def _build_content_items(prompt, reference_images=None, reference_videos=None, reference_audios=None, role_mode="reference_image"):
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        raise PluginFatalError("Prompt 不能为空")

    content = [{"type": "text", "text": prompt_text}]

    for image in _normalize_list_or_single(reference_images):
        image_url = file_to_base64(image)
        content.append({
            "type": "image_url",
            "image_url": {"url": image_url},
            "role": role_mode or "reference_image",
        })

    for video in _normalize_list_or_single(reference_videos):
        content.append({
            "type": "video_url",
            "video_url": {"url": str(video)},
            "role": "reference_video",
        })

    for audio in _normalize_list_or_single(reference_audios):
        content.append({
            "type": "audio_url",
            "audio_url": {"url": str(audio)},
            "role": "reference_audio",
        })

    return content


def _build_create_payload(params, prompt, reference_images=None, reference_videos=None, reference_audios=None):
    payload = {
        "model": params["model"],
        "content": _build_content_items(prompt, reference_images, reference_videos, reference_audios),
        "generate_audio": bool(params["generate_audio"]),
        "resolution": params["resolution"],
        "ratio": params["ratio"],
        "duration": int(params["duration"]),
    }

    has_media = bool(_normalize_list_or_single(reference_images) or _normalize_list_or_single(reference_videos) or _normalize_list_or_single(reference_audios))
    if params.get("web_search") and not has_media:
        payload["tools"] = [{"type": "web_search"}]

    return payload


def _create_task(api_key, base_url, payload, timeout):
    endpoint = _normalize_base_url(base_url)
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

    task_id = result.get("id") or result.get("task_id")
    if not task_id:
        raise PluginFatalError("创建任务失败: 响应中缺少 task_id/id")
    _log_event("create_task.success", task_id=task_id)
    return str(task_id), result


def _normalize_task_status(raw_status):
    status = str(raw_status or "").strip().lower()
    if status in {"running", "processing", "pending", "queued", "submitted", "in_progress"}:
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


def _poll_task_status(api_key, base_url, task_id, timeout, max_attempts, poll_interval, progress_callback=None):
    endpoint = f"{_normalize_base_url(base_url)}/{task_id}"
    headers = _build_auth_headers(api_key, include_content_type=True)
    previous_status = None

    for attempt in range(1, int(max_attempts) + 1):
        response = requests.get(endpoint, headers=headers, timeout=timeout)
        _ensure_success_response(response, "查询任务状态")

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise PluginFatalError(f"状态查询返回非 JSON 响应: {exc}") from exc

        status = _normalize_task_status(data.get("status"))
        if status != previous_status:
            _log_event("poll_task.status", task_id=task_id, status=status, attempt=attempt)
            previous_status = status
        if status == "running":
            if progress_callback:
                progress_callback(f"任务进行中 ({attempt}/{max_attempts})")
            time.sleep(poll_interval)
            continue
        if status == "completed":
            return data, _extract_video_url_from_status(data)
        if status == "failed":
            reason = data.get("fail_reason") or data.get("reason") or "未知原因"
            raise PluginFatalError(f"任务失败: {reason}")

    raise PluginFatalError(f"超过最大轮询次数({max_attempts})，任务未完成")


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

    params["resolution"] = _normalize_resolution(params.get("resolution"))
    params["ratio"] = _normalize_aspect_ratio(params.get("ratio"))
    params["duration"] = _normalize_duration(params.get("duration"))
    params["generate_audio"] = _normalize_audio_generation(params.get("generate_audio"))
    params["web_search"] = _normalize_web_search(params.get("web_search"))

    pixel_width, pixel_height = _get_physical_pixels(params["resolution"], params["ratio"])
    params["pixel_width"] = pixel_width
    params["pixel_height"] = pixel_height

    _validate_image_constraints(params.get("image_path"))

    return params


def _normalize_polling_config(params):
    timeout = int(params.get("timeout", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT)
    max_attempts = int(params.get("max_poll_attempts", DEFAULT_MAX_POLL_ATTEMPTS) or DEFAULT_MAX_POLL_ATTEMPTS)
    poll_interval = int(params.get("poll_interval", DEFAULT_POLL_INTERVAL) or DEFAULT_POLL_INTERVAL)
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
    polling = _normalize_polling_config(params)
    base_url = _normalize_base_url(params.get("base_url", _DEFAULT_BASE_URL))
    api_key = params.get("api_key", "")
    prompt = context.get("prompt", "")
    reference_images = context.get("reference_images")
    reference_videos = context.get("reference_videos")
    reference_audios = context.get("reference_audios")
    output_dir = context.get("output_dir", context.get("project_path", os.getcwd()))
    viewer_index = context.get("viewer_index", 0)

    task_id = None
    video_url = None
    try:
        _log_event("workflow.start", output_dir=output_dir, viewer_index=viewer_index)
        progress_callback("参数校验完成")

        payload = _build_create_payload(
            params=params,
            prompt=prompt,
            reference_images=reference_images,
            reference_videos=reference_videos,
            reference_audios=reference_audios,
        )

        task_id, _ = _create_task(api_key, base_url, payload, polling["timeout"])
        progress_callback("任务已创建")
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

        final_output_path = context.get("output_path") or _default_output_path(output_dir, viewer_index, task_id)
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

        return _build_orchestration_result(
            task_id=task_id,
            status=status_data.get("status"),
            output_path=downloaded_path,
            video_url=video_url,
            error=None,
            meta={"polling": polling},
        )
    except Exception as exc:
        wrapped_error = exc if isinstance(exc, PluginFatalError) else PluginFatalError(str(exc))
        progress_callback("失败")
        _log_event("workflow.failed", task_id=task_id, error=str(wrapped_error))
        return _build_orchestration_result(
            task_id=task_id,
            status="failed",
            output_path=None,
            video_url=video_url,
            error=wrapped_error,
            meta={"polling": polling},
        )


def _map_orchestration_to_plugin_output(result):
    if result.get("status") == "completed" and result.get("output_path"):
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

    try:
        outputs = run_seedance_workflow(ctx)
        _log_event("generate.success", outputs=outputs)
        return outputs
    except PluginFatalError:
        raise
    except Exception as exc:
        raise PluginFatalError(str(exc)) from exc


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
    ]
    missing = [name for name in required_funcs if not callable(globals().get(name))]
    if missing:
        raise SystemExit(f"smoke check failed, missing callables: {missing}")
    print("smoke check passed")
