---
phase: 2
plan: 01
type: plan
name: 参数处理
objective: 实现插件参数的清洗、校验与 Seedance 2.0 API 规范化映射。
wave: 1
depends_on: [1]
files_modified: [video_plugin_zlhub_seedance/main.py]
autonomous: true
requirements: [PARA-01, PARA-02, PARA-03]
must_haves:
  - "必须包含 PLUGIN_ERROR::: 错误前缀"
  - "时长必须支持 -1 且其他值被限制在 [4, 15]"
  - "分辨率和比例必须映射到文档指定的物理像素"
  - "图像校验必须包含大小 (30MB) 和格式检查"
---

# Phase 2: 参数处理 - Plan

本阶段将实现在 `main.py` 中对宿主传入参数的完整处理逻辑，确保输出符合 Seedance 2.0 API 的物理约束。

## Wave 1: 核心参数处理逻辑

<task>
<name>实现异常类与基础常量</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/02-para-process/02-RESEARCH.md
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
在 `video_plugin_zlhub_seedance/main.py` 中定义 `PluginFatalError` 异常类。
定义 `RESOLUTION_RATIO_MAP` 字典，包含 480p 和 720p 下所有比例的物理像素映射。
更新 `_default_params` 以匹配 API 文档。
</action>
<verify>
grep "class PluginFatalError" video_plugin_zlhub_seedance/main.py
grep "RESOLUTION_RATIO_MAP =" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- `main.py` 包含 `class PluginFatalError(Exception)`。
- `RESOLUTION_RATIO_MAP` 包含 12 个组合的像素映射。
</acceptance_criteria>
<done>基础常量与异常类已定义</done>
</task>

<task>
<name>实现分辨率与比例规范化函数</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/02-para-process/02-RESEARCH.md
- video_plugin_zzdhapi/main.py
</read_first>
<action>
实现 `_normalize_resolution` 和 `_normalize_aspect_ratio` 函数。
`_normalize_resolution` 限制在 `["480p", "720p"]`。
`_normalize_aspect_ratio` 限制在 `["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"]`。
</action>
<verify>
grep "def _normalize_resolution" video_plugin_zlhub_seedance/main.py
grep "def _normalize_aspect_ratio" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- `_normalize_resolution` 处理无效输入时返回默认值 "720p"。
- `_normalize_aspect_ratio` 正确处理 "adaptive"。
</acceptance_criteria>
<done>分辨率与比例规范化函数已实现</done>
</task>

<task>
<name>实现时长与音频规范化函数</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/02-para-process/02-RESEARCH.md
</read_first>
<action>
实现 `_normalize_duration` 和 `_normalize_audio_generation` 函数。
`_normalize_duration`：支持 `-1`，其余截断至 `[4, 15]`。
`_normalize_audio_generation`：映射为 `True`/`False`。
</action>
<verify>
grep "def _normalize_duration" video_plugin_zlhub_seedance/main.py
grep "def _normalize_audio_generation" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- `_normalize_duration(20)` 返回 15。
- `_normalize_audio_generation("enabled")` 返回 True。
</acceptance_criteria>
<done>时长与音频规范化函数已实现</done>
</task>

<task>
<name>实现图像物理约束校验</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/02-para-process/02-RESEARCH.md
</read_first>
<action>
实现 `_validate_image_constraints(image_path)`。
检查文件大小 \u003c 30MB 且后缀为支持的格式。
校验失败抛出 `PluginFatalError` + `PLUGIN_ERROR:::` 前缀。
</action>
<verify>
grep "def _validate_image_constraints" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 校验逻辑包含文件大小和格式检查。
- 错误消息包含 `PLUGIN_ERROR:::`。
</acceptance_criteria>
<done>图像校验逻辑已实现</done>
</task>

<task>
<name>集成参数清洗与持久化</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
在 `_sanitize_params` 中调用上述 normalize 函数。
在 `get_params` 中实现修正后自动调用 `save_plugin_config`。
</action>
<verify>
grep "_sanitize_params" video_plugin_zlhub_seedance/main.py
grep "save_plugin_config" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- `get_params()` 返回规范化后的参数。
- 修正后的参数能持久化到 json。
</acceptance_criteria>
<done>参数清洗与持久化已集成</done>
</task>

## Verification

### Automated Tests
- 运行 `python video_plugin_zlhub_seedance/main.py` 进行逻辑自测。

### Manual Verification
- 修改配置文件并观察修正行为。
