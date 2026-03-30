# -*- coding: utf-8 -*-
"""
ZZDH-API 视频生成插件。

当前支持：
1. wan2.6-i2v / wan2.6-i2v-flash / wan2.2-i2v-plus
   - 文生视频
   - 图生视频
2. wan2.2-kf2v-flash
   - 首帧生视频
   - 首尾帧生视频
3. kling-3.0-omni
   - 文生视频
   - 图生视频
   - 根据分辨率 / 音频开关 / 是否有参考图，自动映射到 8 个最终调用名称
"""

import base64
import json
import os
import sys
import time
import traceback
from datetime import datetime

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from plugin_utils import load_plugin_config, save_plugin_config

_PLUGIN_FILE = __file__

_BASE_URL_OPTIONS = [
    ("ZZDH-API", "https://zizidonghua.com"),
]
_DEFAULT_BASE_URL = _BASE_URL_OPTIONS[0][1]

DEFAULT_RESOLUTIONS = ["480p", "720p", "1080p"]
DEFAULT_ASPECT_RATIOS = ["16:9", "9:16", "4:3", "3:4", "1:1"]
KLING_RESOLUTIONS = ["720p", "1080p"]
VIDU_Q3_RESOLUTIONS = ["540p", "720p", "1080p"]
VIDU_Q3_DURATIONS = ["5", "8", "10", "12", "16"]

MODE_TEXT_TO_VIDEO = "文生视频"
MODE_IMAGE_TO_VIDEO = "图生视频"
MODE_FIRST_FRAME = "首帧生视频"
MODE_FIRST_LAST_FRAME = "首尾帧生视频"

AUDIO_ENABLED = "Enabled"
AUDIO_DISABLED = "Disabled"

DEFAULT_MODEL = "wan2.6-i2v"
KLING_MODEL = "kling-v3-omni"
KLING_MODEL_KIND = "kling_omni"
VIDU_Q3_MODEL_KIND = "vidu_q3"
MODEL_ALIASES = {
    "kling-3.0-omni": KLING_MODEL,
}


def _normalize_base_url(url):
    if not url:
        return ""
    return str(url).rstrip("/")


_VALID_BASE_URLS = {_normalize_base_url(url) for _, url in _BASE_URL_OPTIONS}


def _get_valid_base_url(url):
    normalized = _normalize_base_url(url)
    if normalized in _VALID_BASE_URLS:
        return normalized
    return _normalize_base_url(_DEFAULT_BASE_URL)


def _create_model_config(config):
    base = {
        "label": "",
        "model_kind": "hybrid",
        "generation_modes": [MODE_TEXT_TO_VIDEO, MODE_IMAGE_TO_VIDEO],
        "default_generation_mode": MODE_IMAGE_TO_VIDEO,
        "durations": ["5", "10", "15"],
        "resolutions": DEFAULT_RESOLUTIONS,
        "aspect_ratios": DEFAULT_ASPECT_RATIOS,
        "input_field": "input_reference",
        "audio_options": [],
        "default_audio_generation": AUDIO_DISABLED,
        "info": "",
    }
    base.update(config)
    return base


MODEL_CONFIGS = {
    "wan2.6-i2v": _create_model_config({
        "label": "wan2.6-i2v（文生/图生视频）",
        "info": "阿里万相 wan2.6，支持文生视频和图生视频。",
    }),
    "wan2.6-i2v-flash": _create_model_config({
        "label": "wan2.6-i2v-flash（文生/图生视频）",
        "info": "阿里万相 wan2.6 Flash，支持文生视频和图生视频。",
    }),
    "wan2.2-i2v-plus": _create_model_config({
        "label": "wan2.2-i2v-plus（文生/图生视频）",
        "info": "阿里万相 wan2.2 Plus，支持文生视频和图生视频。",
    }),
    "wan2.2-kf2v-flash": _create_model_config({
        "label": "wan2.2-kf2v-flash（首帧/首尾帧）",
        "model_kind": "kf2v",
        "generation_modes": [MODE_FIRST_FRAME, MODE_FIRST_LAST_FRAME],
        "default_generation_mode": MODE_FIRST_FRAME,
        "durations": ["2", "3", "4", "5"],
        "input_field": None,
        "info": "阿里万相 wan2.2 kf2v Flash，支持首帧生视频和首尾帧生视频。",
    }),
    KLING_MODEL: _create_model_config({
        "label": "可灵 3.0 Omni",
        "model_kind": KLING_MODEL_KIND,
        "durations": ["5", "10"],
        "resolutions": KLING_RESOLUTIONS,
        "audio_options": [AUDIO_DISABLED, AUDIO_ENABLED],
        "default_audio_generation": AUDIO_DISABLED,
        "info": "可灵 3.0 Omni 支持文生视频和图生视频，后端会自动映射到 8 个最终调用名称。",
    }),
    "vidu-q3-pro": _create_model_config({
        "label": "Vidu Q3 Pro",
        "model_kind": VIDU_Q3_MODEL_KIND,
        "durations": VIDU_Q3_DURATIONS,
        "resolutions": VIDU_Q3_RESOLUTIONS,
        "audio_options": [AUDIO_DISABLED, AUDIO_ENABLED],
        "default_audio_generation": AUDIO_ENABLED,
        "info": "Vidu Q3 Pro",
    }),
    "vidu-q3-turbo": _create_model_config({
        "label": "Vidu Q3 Turbo",
        "model_kind": VIDU_Q3_MODEL_KIND,
        "durations": VIDU_Q3_DURATIONS,
        "resolutions": VIDU_Q3_RESOLUTIONS,
        "audio_options": [AUDIO_DISABLED, AUDIO_ENABLED],
        "default_audio_generation": AUDIO_ENABLED,
        "info": "Vidu Q3 Turbo",
    }),
}


def _get_model_config(model_value):
    normalized_model = MODEL_ALIASES.get(model_value, model_value)
    return MODEL_CONFIGS.get(normalized_model, MODEL_CONFIGS[DEFAULT_MODEL])


def _build_default_params():
    default_model_config = _get_model_config(DEFAULT_MODEL)
    return {
        "api_key": "",
        "base_url": _DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "resolution": default_model_config["resolutions"][1],
        "aspect_ratio": default_model_config["aspect_ratios"][0],
        "duration": default_model_config["durations"][0],
        "generation_mode": default_model_config["default_generation_mode"],
        "audio_generation": default_model_config["default_audio_generation"],
        "timeout": 900,
        "max_poll_attempts": 300,
        "poll_interval": 5,
        "retry_count": 3,
    }


_default_params = _build_default_params()
_MODEL_INFO = {model: config["info"] for model, config in MODEL_CONFIGS.items()}
_MODEL_DISPLAY_MAP = {model: model for model in MODEL_CONFIGS}
_MODEL_REAL_TO_DISPLAY = {value: key for key, value in _MODEL_DISPLAY_MAP.items()}


def _normalize_duration(duration_value, model_config):
    allowed_durations = {int(item) for item in model_config.get("durations", [_default_params["duration"]])}
    fallback_duration = int(model_config.get("durations", [_default_params["duration"]])[0])
    try:
        duration_int = int(duration_value)
    except (TypeError, ValueError):
        print(f"警告: 无法识别时长 {duration_value}，改用默认值 {fallback_duration}")
        return fallback_duration

    if duration_int not in allowed_durations:
        allowed_text = "/".join(str(item) for item in sorted(allowed_durations))
        print(f"警告: 当前模型不支持时长 {duration_int}，改用默认值 {fallback_duration}，可用值: {allowed_text}")
        return fallback_duration
    return duration_int


def _normalize_model(model_value):
    normalized_model = MODEL_ALIASES.get(str(model_value or "").strip(), str(model_value or "").strip())
    if normalized_model in MODEL_CONFIGS:
        return normalized_model
    print(f"警告: 未知视频模型 {model_value}，回退到默认模型 {DEFAULT_MODEL}")
    return DEFAULT_MODEL


def _normalize_resolution(resolution_value, model_config):
    normalized_resolution = str(resolution_value or "").strip().lower()
    available_resolutions = model_config.get("resolutions", DEFAULT_RESOLUTIONS)
    if normalized_resolution in available_resolutions:
        return normalized_resolution
    return available_resolutions[0]


def _normalize_aspect_ratio(aspect_ratio_value, model_config):
    normalized_aspect_ratio = str(aspect_ratio_value or "").strip()
    available_aspect_ratios = model_config.get("aspect_ratios", DEFAULT_ASPECT_RATIOS)
    if normalized_aspect_ratio in available_aspect_ratios:
        return normalized_aspect_ratio
    return available_aspect_ratios[0]


def _normalize_generation_mode(generation_mode_value, model_config):
    normalized_generation_mode = str(generation_mode_value or "").strip()
    available_generation_modes = model_config.get("generation_modes", [model_config.get("default_generation_mode")])
    if normalized_generation_mode in available_generation_modes:
        return normalized_generation_mode
    return model_config.get("default_generation_mode", _default_params["generation_mode"])


def _normalize_audio_generation(value):
    text = str(value or "").strip().lower()
    if text in {"enabled", "enable", "true", "1", "on", "有声"}:
        return AUDIO_ENABLED
    return AUDIO_DISABLED


def _sanitize_params(raw_params=None):
    raw_params = raw_params or {}
    params = _default_params.copy()
    params.update(raw_params)

    params["base_url"] = _get_valid_base_url(params.get("base_url", _DEFAULT_BASE_URL))
    params["model"] = _normalize_model(params.get("model", DEFAULT_MODEL))

    model_config = _get_model_config(params["model"])
    params["resolution"] = _normalize_resolution(params.get("resolution", _default_params["resolution"]), model_config)
    params["aspect_ratio"] = _normalize_aspect_ratio(params.get("aspect_ratio", _default_params["aspect_ratio"]), model_config)
    params["generation_mode"] = _normalize_generation_mode(params.get("generation_mode", _default_params["generation_mode"]), model_config)
    params["duration"] = str(_normalize_duration(params.get("duration", _default_params["duration"]), model_config))

    audio_options = model_config.get("audio_options", [])
    normalized_audio = _normalize_audio_generation(params.get("audio_generation", model_config.get("default_audio_generation", AUDIO_DISABLED)))
    params["audio_generation"] = normalized_audio if normalized_audio in audio_options else model_config.get("default_audio_generation", AUDIO_DISABLED)
    return params


def get_info():
    return {
        "name": "ZZDH-API 视频生成插件",
        "description": "通过 ZZDH-API 调用 wan 与可灵视频模型生成视频。",
        "version": "1.1.0",
        "author": "ZZDH",
    }


def get_params():
    raw_params = load_plugin_config(_PLUGIN_FILE) or {}
    params = _sanitize_params(raw_params)

    keys_to_validate = (
        "base_url",
        "model",
        "resolution",
        "aspect_ratio",
        "duration",
        "generation_mode",
        "audio_generation",
    )
    unexpected_keys = set(raw_params.keys()) - set(_default_params.keys())
    should_persist = any(
        key in raw_params and raw_params.get(key) != params.get(key)
        for key in keys_to_validate
    ) or bool(unexpected_keys)

    if should_persist:
        save_plugin_config(_PLUGIN_FILE, {key: params[key] for key in _default_params.keys()})

    return params


def compress_image(input_path, output_path, max_size_kb=100, quality=70):
    try:
        from PIL import Image

        image = Image.open(input_path)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        image.save(output_path, "JPEG", quality=quality)
        file_size = os.path.getsize(output_path) / 1024
        while file_size > max_size_kb and quality > 10:
            quality -= 10
            image.save(output_path, "JPEG", quality=quality)
            file_size = os.path.getsize(output_path) / 1024
        return True
    except Exception as exc:
        print(f"[压缩失败] {exc}")
        return False


def file_to_base64(file_path, compress=False, max_size_kb=80):
    try:
        if not os.path.exists(file_path):
            return None, 0

        original_size = os.path.getsize(file_path) / 1024
        if compress and original_size > max_size_kb:
            temp_path = file_path.replace(".jpg", "_compressed.jpg").replace(".png", "_compressed.jpg")
            if compress_image(file_path, temp_path, max_size_kb=max_size_kb):
                file_path = temp_path

        with open(file_path, "rb") as file:
            image_data = file.read()

        b64_str = base64.b64encode(image_data).decode("utf-8")
        mime_type = "image/jpeg" if file_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        return f"data:{mime_type};base64,{b64_str}", len(b64_str)
    except Exception as exc:
        print(f"[读取文件失败] {exc}")
        return None, 0


def _normalize_reference_images(reference_images):
    if reference_images and all(isinstance(key, int) for key in reference_images.keys()):
        return {"参考图片MAP": reference_images.copy()}
    return dict(reference_images or {})


def _pick_first_reference_from_map(reference_images):
    reference_map = reference_images.get("参考图片MAP", {})
    if isinstance(reference_map, dict):
        for _, value in sorted(reference_map.items(), key=lambda item: item[0]):
            if value:
                return value
    return None


def _pick_last_reference_from_map(reference_images):
    reference_map = reference_images.get("参考图片MAP", {})
    if isinstance(reference_map, dict):
        items = [value for _, value in sorted(reference_map.items(), key=lambda item: item[0]) if value]
        if items:
            return items[-1]
    return None


def _get_reference_frames(reference_images):
    first_frame = reference_images.get("首帧") or _pick_first_reference_from_map(reference_images)
    last_frame = reference_images.get("尾帧") or _pick_last_reference_from_map(reference_images)
    return first_frame, last_frame


def _load_required_image(image_path, missing_error_message, convert_error_message):
    if not image_path:
        raise Exception(missing_error_message)

    # 已经是图床 URL，直接返回
    if str(image_path).startswith("http://") or str(image_path).startswith("https://"):
        return image_path

    if not os.path.exists(image_path):
        raise Exception(missing_error_message)

    image_b64, _ = file_to_base64(image_path, compress=True, max_size_kb=80)
    if not image_b64:
        raise Exception(convert_error_message)
    return image_b64


def _build_base_payload(model, prompt, duration_int, resolution, aspect_ratio):
    metadata = {
        "aspect_ratio": aspect_ratio,
        "ratio": aspect_ratio,
        "resolution": resolution,
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "duration": duration_int,
        "resolution": resolution.upper(),
        "metadata": metadata,
    }
    return payload, metadata


def _append_prompt_content(content, prompt):
    if prompt:
        content.append({
            "type": "text",
            "text": prompt,
        })


def _append_frame_content(content, image_urls, image_b64, role):
    image_urls.append(image_b64)
    content.append({
        "type": "image_url",
        "image_url": {"url": image_b64},
        "role": role,
    })


def _build_standard_payload(prompt, model, model_config, generation_mode, resolution, aspect_ratio, duration_int,
                            reference_images, progress_callback):
    payload, metadata = _build_base_payload(model, prompt, duration_int, resolution, aspect_ratio)
    content = []
    image_urls = []
    _append_prompt_content(content, prompt)

    first_frame, end_frame = _get_reference_frames(reference_images)
    input_field = model_config.get("input_field")

    if generation_mode == MODE_TEXT_TO_VIDEO:
        print(f"模式: {MODE_TEXT_TO_VIDEO}")
    elif generation_mode in (MODE_IMAGE_TO_VIDEO, MODE_FIRST_FRAME):
        print(f"模式: {generation_mode}")
        if progress_callback:
            progress_callback("准备首帧图片")
        first_b64 = _load_required_image(
            first_frame,
            "PLUGIN_ERROR:::当前模式需要提供首帧图片",
            "PLUGIN_ERROR:::首帧图片转换失败",
        )
        _append_frame_content(content, image_urls, first_b64, "first_frame")
        if generation_mode == MODE_IMAGE_TO_VIDEO and input_field:
            payload[input_field] = first_b64
    elif generation_mode == MODE_FIRST_LAST_FRAME:
        print(f"模式: {MODE_FIRST_LAST_FRAME}")
        if progress_callback:
            progress_callback("准备首尾帧图片")
        first_b64 = _load_required_image(
            first_frame,
            "PLUGIN_ERROR:::首尾帧生视频模式需要提供首帧图片",
            "PLUGIN_ERROR:::首帧图片转换失败",
        )
        end_b64 = _load_required_image(
            end_frame,
            "PLUGIN_ERROR:::首尾帧生视频模式需要提供尾帧图片",
            "PLUGIN_ERROR:::尾帧图片转换失败",
        )
        _append_frame_content(content, image_urls, first_b64, "first_frame")
        _append_frame_content(content, image_urls, end_b64, "last_frame")
    else:
        raise Exception(f"PLUGIN_ERROR:::不支持的生成模式: {generation_mode}")

    if image_urls:
        payload["images"] = image_urls
    if content:
        metadata["content"] = content
    return payload


def _resolve_kling_model_name(resolution, audio_generation, has_reference):
    resolution_part = "1080p" if str(resolution).lower() == "1080p" else "720p"
    reference_part = "ref" if has_reference else "noref"
    audio_part = "audio" if audio_generation == AUDIO_ENABLED else "mute"
    return f"kling-3.0-omni-{resolution_part}-{reference_part}-{audio_part}"


def _build_kling_output_config(aspect_ratio, resolution, duration_int, audio_generation):
    return {
        "aspect_ratio": aspect_ratio,
        "resolution": str(resolution).upper(),
        "duration": duration_int,
        "audio_generation": audio_generation,
    }


def _build_kling_payload(prompt, resolution, aspect_ratio, duration_int, generation_mode,
                         reference_images, audio_generation, progress_callback):
    first_frame, _ = _get_reference_frames(reference_images)
    has_reference = generation_mode == MODE_IMAGE_TO_VIDEO
    resolved_model_name = _resolve_kling_model_name(resolution, audio_generation, has_reference)

    payload, metadata = _build_base_payload(resolved_model_name, prompt, duration_int, resolution, aspect_ratio)
    metadata["output_config"] = _build_kling_output_config(aspect_ratio, resolution, duration_int, audio_generation)

    if generation_mode == MODE_TEXT_TO_VIDEO:
        print(f"模式: {MODE_TEXT_TO_VIDEO}")
        return payload

    if generation_mode != MODE_IMAGE_TO_VIDEO:
        raise Exception(f"PLUGIN_ERROR:::可灵 3.0 Omni 不支持当前生成模式: {generation_mode}")

    print(f"模式: {MODE_IMAGE_TO_VIDEO}")
    if progress_callback:
        progress_callback("准备参考图片")

    first_b64 = _load_required_image(
        first_frame,
        "PLUGIN_ERROR:::可灵图生视频模式需要提供首帧图片",
        "PLUGIN_ERROR:::可灵参考图片转换失败",
    )
    metadata["image_list"] = [{
        "image_url": first_b64,
        "type": "first_frame",
    }]
    payload["images"] = [first_b64]
    return payload


def _resolve_vidu_model_name(model, resolution):
    resolution_part = str(resolution).lower()
    if resolution_part not in {"540p", "720p", "1080p"}:
        resolution_part = "720p"
    return f"{model}-{resolution_part}"


def _build_vidu_payload(prompt, model, resolution, aspect_ratio, duration_int, generation_mode,
                        reference_images, audio_generation, progress_callback):
    if generation_mode not in (MODE_TEXT_TO_VIDEO, MODE_IMAGE_TO_VIDEO):
        raise Exception(f"PLUGIN_ERROR:::Vidu Q3 涓嶆敮鎸佸綋鍓嶇敓鎴愭ā寮? {generation_mode}")

    resolved_model_name = _resolve_vidu_model_name(model, resolution)
    payload, metadata = _build_base_payload(resolved_model_name, prompt, duration_int, resolution, aspect_ratio)
    metadata["audio"] = audio_generation == AUDIO_ENABLED
    if metadata["audio"]:
        metadata["audio_type"] = "all"

    if generation_mode == MODE_TEXT_TO_VIDEO:
        print(f"妯″紡: {MODE_TEXT_TO_VIDEO}")
        return payload

    print(f"妯″紡: {MODE_IMAGE_TO_VIDEO}")
    first_frame, _ = _get_reference_frames(reference_images)
    if progress_callback:
        progress_callback("鍑嗗棣栧抚鍥剧墖")

    first_b64 = _load_required_image(
        first_frame,
        "PLUGIN_ERROR:::Vidu Q3 鍥剧敓瑙嗛闇€瑕佹彁渚涢甯у浘鐗?",
        "PLUGIN_ERROR:::Vidu Q3 棣栧抚鍥剧墖杞崲澶辫触",
    )
    payload["images"] = [first_b64]
    return payload


def _build_request_payload(prompt, model, model_config, generation_mode, resolution, aspect_ratio, duration_int,
                           reference_images, audio_generation, progress_callback):
    model_kind = model_config.get("model_kind", "hybrid")
    if model_kind == KLING_MODEL_KIND:
        return _build_kling_payload(
            prompt=prompt,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            duration_int=duration_int,
            generation_mode=generation_mode,
            reference_images=reference_images,
            audio_generation=audio_generation,
            progress_callback=progress_callback,
        )

    if model_kind == VIDU_Q3_MODEL_KIND:
        return _build_vidu_payload(
            prompt=prompt,
            model=model,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            duration_int=duration_int,
            generation_mode=generation_mode,
            reference_images=reference_images,
            audio_generation=audio_generation,
            progress_callback=progress_callback,
        )

    return _build_standard_payload(
        prompt=prompt,
        model=model,
        model_config=model_config,
        generation_mode=generation_mode,
        resolution=resolution,
        aspect_ratio=aspect_ratio,
        duration_int=duration_int,
        reference_images=reference_images,
        progress_callback=progress_callback,
    )


def _extract_task_data(status_data):
    if isinstance(status_data, dict):
        if isinstance(status_data.get("data"), dict):
            return status_data["data"]
        return status_data
    return {}


def _extract_video_url(task_data):
    data = task_data.get("data")
    nested_output = data.get("output", {}) if isinstance(data, dict) else {}
    return (
        task_data.get("video_url")
        or task_data.get("url")
        or task_data.get("content_url")
        or nested_output.get("video_url")
        or nested_output.get("url")
    )


class PluginFatalError(Exception):
    pass


def generate(context):
    print("\n" + "=" * 60)
    print("[ZZDH-API Plugin] 开始生成视频")
    print("=" * 60)

    prompt = context.get("prompt", "")
    reference_images = _normalize_reference_images(context.get("reference_images", {}))
    output_dir = context.get("output_dir", context.get("project_path", "."))
    raw_plugin_params = context.get("plugin_params")
    plugin_params = _sanitize_params(raw_plugin_params if raw_plugin_params is not None else get_params())
    progress_callback = context.get("progress_callback")

    first_frame_path = context.get("first_frame_path")
    end_frame_path = context.get("end_frame_path")
    if first_frame_path:
        reference_images["首帧"] = first_frame_path
    if end_frame_path:
        reference_images["尾帧"] = end_frame_path

    api_key = plugin_params.get("api_key", "")
    base_url = plugin_params.get("base_url", _DEFAULT_BASE_URL)
    model = plugin_params.get("model", DEFAULT_MODEL)
    resolution = plugin_params.get("resolution", "720p")
    aspect_ratio = plugin_params.get("aspect_ratio", "16:9")
    duration_str = plugin_params.get("duration", "5")
    generation_mode = plugin_params.get("generation_mode", MODE_IMAGE_TO_VIDEO)
    audio_generation = plugin_params.get("audio_generation", AUDIO_DISABLED)
    timeout = plugin_params.get("timeout", 900)
    max_poll_attempts = plugin_params.get("max_poll_attempts", 300)
    poll_interval = plugin_params.get("poll_interval", 5)
    retry_count = plugin_params.get("retry_count", 3)
    retry_delay_seconds = 2

    model_config = _get_model_config(model)
    model_kind = model_config.get("model_kind", "hybrid")

    print(f"提示词: {prompt}")
    print(f"模型: {model}")
    print(f"模型类型: {model_kind}")
    print(f"生成模式: {generation_mode}")
    print(f"分辨率: {resolution}")
    print(f"宽高比: {aspect_ratio}")
    print(f"时长: {duration_str}秒")
    if model_kind == KLING_MODEL_KIND:
        print(f"音频: {'有声' if audio_generation == AUDIO_ENABLED else '静音'}")
    print(f"重试次数: {retry_count}")
    print(f"API Key: {'已设置(' + str(len(api_key)) + '字符)' if api_key else '未设置'}")

    if not api_key:
        raise Exception("PLUGIN_ERROR:::API Key 未设置，请在插件设置中配置")

    max_attempts = retry_count + 1
    endpoint = f"{base_url}/v1/videos"

    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                print(f"\n第 {attempt + 1}/{max_attempts} 次尝试")
            else:
                print("正在调用 ZZDH-API...")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            duration_int = _normalize_duration(duration_str, model_config)
            payload = _build_request_payload(
                prompt=prompt,
                model=model,
                model_config=model_config,
                generation_mode=generation_mode,
                resolution=resolution,
                aspect_ratio=aspect_ratio,
                duration_int=duration_int,
                reference_images=reference_images,
                audio_generation=audio_generation,
                progress_callback=progress_callback,
            )

            if progress_callback:
                progress_callback("提交任务")

            print(f"请求端点: {endpoint}")
            print(f"请求体: {json.dumps(payload, indent=2, ensure_ascii=False)[:800]}")

            response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
            if response.status_code != 200:
                raise Exception(f"PLUGIN_ERROR:::API 错误: {response.status_code} - {response.text}")

            result = response.json()
            print(f"API 响应: {result}")

            task_id = result.get("id") or result.get("task_id")
            if not task_id:
                raise Exception("PLUGIN_ERROR:::API 响应中缺少任务 ID")

            print(f"任务 ID: {task_id}")
            print("等待视频生成...")

            attempts = 0
            video_url = None
            last_status = "unknown"
            poll_headers = {"Authorization": f"Bearer {api_key}"}

            while attempts < max_poll_attempts:
                time.sleep(poll_interval)
                attempts += 1

                try:
                    status_response = requests.get(
                        f"{base_url}/v1/videos/{task_id}",
                        headers=poll_headers,
                        timeout=timeout,
                    )
                    if status_response.status_code != 200:
                        print(f"状态查询失败: {status_response.status_code}")
                        continue

                    task_data = _extract_task_data(status_response.json())
                    status = str(task_data.get("status", "unknown"))
                    last_status = status
                    progress = task_data.get("progress", "0%")

                    if status in {"SUCCESS", "SUCCEEDED", "succeeded", "COMPLETED", "completed"}:
                        video_url = _extract_video_url(task_data)
                        print(f"视频生成成功: {video_url}")
                        break
                    if status in {"FAIL", "FAILED", "FAILURE", "failed"}:
                        reason = task_data.get("fail_reason") or task_data.get("reason") or "Unknown"
                        raise PluginFatalError(f"PLUGIN_ERROR:::{reason}")

                    if progress_callback:
                        if status in {"pending", "queued", "submitted"}:
                            progress_callback("排队中")
                        elif status in {"processing", "in_progress", "running"}:
                            progress_callback("生成中")

                    mins = int(attempts * poll_interval // 60)
                    secs = int(attempts * poll_interval % 60)
                    print(f"[{attempts}/{max_poll_attempts}] 状态: {status}, 进度: {progress}, 已等待: {mins:02d}:{secs:02d}", end="\r")
                except requests.exceptions.RequestException as exc:
                    print(f"状态查询网络失败，将继续轮询: {exc}")
                except PluginFatalError:
                    raise
                except Exception as exc:
                    error_text = str(exc)
                    if error_text.startswith("PLUGIN_ERROR:::"):
                        raise
                    print(f"状态查询异常: {exc}")
                    raise

            if not video_url and last_status not in {"COMPLETED", "completed"}:
                raise Exception(f"PLUGIN_ERROR:::超过最大轮询次数({max_poll_attempts})，视频未生成")

            if progress_callback:
                progress_callback("下载中")

            print(f"正在下载视频: {video_url}")
            content_url = f"{base_url}/v1/videos/{task_id}/content"
            download_url = video_url or content_url
            download_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            if str(download_url).startswith(base_url):
                download_headers["Authorization"] = f"Bearer {api_key}"

            video_response = requests.get(download_url, headers=download_headers, timeout=timeout)
            if video_response.status_code != 200 and download_url != content_url:
                download_headers["Authorization"] = f"Bearer {api_key}"
                video_response = requests.get(content_url, headers=download_headers, timeout=timeout)
            if video_response.status_code != 200:
                raise Exception(f"PLUGIN_ERROR:::下载视频失败: {video_response.status_code}")

            viewer_index = context.get("viewer_index", 0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename_prefix = "wan"
            if model_kind == KLING_MODEL_KIND:
                filename_prefix = "kling"
            elif model_kind == VIDU_Q3_MODEL_KIND:
                filename_prefix = "vidu"
            filename = f"{viewer_index:04d}_{filename_prefix}_{timestamp}.mp4"
            output_path = os.path.join(output_dir, filename)

            with open(output_path, "wb") as file:
                file.write(video_response.content)

            file_size = len(video_response.content) / (1024 * 1024)
            print(f"视频已保存: {output_path}")
            print(f"文件大小: {file_size:.2f} MB")
            print("=" * 60)
            return [output_path]

        except Exception as exc:
            error_text = str(exc)
            print(f"失败原因: {error_text}")

            is_last_attempt = attempt == max_attempts - 1
            if is_last_attempt:
                print("已达到最大重试次数，停止")
                traceback.print_exc()
                final_error = f"生成失败（已尝试 {max_attempts} 次）: {error_text}"
                if not final_error.startswith("PLUGIN_ERROR:::"):
                    final_error = f"PLUGIN_ERROR:::{final_error}"
                raise Exception(final_error)

            print(f"[WARN] 第 {attempt + 1}/{max_attempts} 次尝试失败，将在 {retry_delay_seconds}s 后重试")
            time.sleep(retry_delay_seconds)
