# -*- coding: utf-8 -*-
"""
ZLHub Seedance 2.0 视频生成插件。
对接 ZLHub 中转平台，支持 Seedance 2.0 视频大模型。
"""

import os

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
        "timeout": 900,
        "max_poll_attempts": 300,
        "poll_interval": 5,
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


def get_params():
    """返回插件配置参数，由宿主程序调用以生成 UI"""
    raw_params = load_plugin_config(_PLUGIN_FILE) or {}
    params = _sanitize_params(raw_params)

    # 如果参数有变化（比如新增了字段或值被规范化），持久化一份
    if raw_params != params:
        save_plugin_config(_PLUGIN_FILE, params)

    return params


def generate(context):
    """插件主入口点 (阶段 5 实现)"""
    raise NotImplementedError("generate() 将在阶段 5 中实现")
