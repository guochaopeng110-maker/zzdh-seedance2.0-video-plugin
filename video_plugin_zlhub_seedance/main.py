# -*- coding: utf-8 -*-
"""
ZLHub Seedance 2.0 视频生成插件。
对接 ZLHub 中转平台，支持 Seedance 2.0 视频大模型。
"""

import json
import os
import sys
import time
import requests
from datetime import datetime

# 导入插件工具类
try:
    from plugin_utils import load_plugin_config, save_plugin_config
except ImportError:
    def load_plugin_config(path):
        return {}

    def save_plugin_config(path, config):
        return None


class PluginFatalError(Exception):
    """插件致命错误，宿主应直接提示用户并终止流程。"""


_PLUGIN_FILE = __file__
PLUGIN_ERROR_PREFIX = "PLUGIN_ERROR:::"

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


def _sanitize_params(raw_params=None):
    """清洗并规范化参数"""
    raw_params = raw_params or {}
    params = _default_params.copy()
    params.update(raw_params)

    # 基础类型确保
    if not isinstance(params["duration"], int):
        try:
            params["duration"] = int(params["duration"])
        except Exception:
            params["duration"] = 5

    if not isinstance(params["generate_audio"], bool):
        params["generate_audio"] = str(params["generate_audio"]).lower() == "true"

    if not isinstance(params["web_search"], bool):
        params["web_search"] = str(params["web_search"]).lower() == "true"

    return params


def get_params():
    """返回插件配置参数，由宿主程序调用以生成 UI"""
    raw_params = load_plugin_config(_PLUGIN_FILE) or {}
    params = _sanitize_params(raw_params)

    # 如果参数有变化（比如新增了字段），持久化一份
    if raw_params != params:
        save_plugin_config(_PLUGIN_FILE, params)

    return params


def generate(context):
    """插件主入口点 (阶段 5 实现)"""
    raise NotImplementedError("generate() 将在阶段 5 中实现")
