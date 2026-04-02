---
phase: 3
plan: 01
type: plan
name: API 客户端
objective: 实现 ZLHub Seedance 2.0 的任务创建、状态轮询与产物下载能力，输出可被后续编排层直接调用的稳定接口。
wave: 1
depends_on: [2]
files_modified: [video_plugin_zlhub_seedance/main.py]
autonomous: true
requirements: [API-01, API-02, API-03, API-04]
must_haves:
  - "所有请求都使用 Authorization: Bearer $ARK_API_KEY"
  - "任务创建成功后必须拿到 task_id 或 id"
  - "轮询必须区分 running/completed(succeeded)/failed 并在失败时携带 fail_reason"
  - "下载必须先尝试 video_url，失败后回退 /v1/videos/{task_id}/content"
---

# Phase 3: API 客户端 - Plan

本阶段实现 `video_plugin_zlhub_seedance/main.py` 的核心网络客户端能力，不改动 `generate()` 入口编排，仅交付可复用的 API 层函数，供后续阶段串联。

## Wave 1: Seedance 客户端核心能力

<task>
<name>补齐网络依赖与统一请求配置</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/03-api-client/03-CONTEXT.md
- docs/require/zlhub-seedance2.0-video-api.md
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
在 `video_plugin_zlhub_seedance/main.py` 增加 `json`、`time`、`requests`、`datetime` 导入。新增常量：`DEFAULT_TIMEOUT = 900`、`DEFAULT_MAX_POLL_ATTEMPTS = 300`、`DEFAULT_POLL_INTERVAL = 5`、`DOWNLOAD_USER_AGENT`、`DOWNLOAD_REFERER = "https://zlhub.xiaowaiyou.cn/"`。新增 `_build_auth_headers(api_key, include_content_type=True)`，返回包含 `Authorization: Bearer {api_key}` 的请求头；当 `api_key` 为空时抛 `PluginFatalError("API Key 未设置")`。
</action>
<verify>
grep "import requests" video_plugin_zlhub_seedance/main.py
grep "DEFAULT_MAX_POLL_ATTEMPTS = 300" video_plugin_zlhub_seedance/main.py
grep "def _build_auth_headers" video_plugin_zlhub_seedance/main.py
grep "Authorization\": f\"Bearer {api_key}\"" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- `main.py` 包含 `import requests` 且包含 `_build_auth_headers`。
- `_build_auth_headers` 的返回值在源码中出现 `Authorization` 与 `Bearer` 拼接逻辑。
- 当 `api_key` 为空时存在 `PluginFatalError` 抛出分支。
</acceptance_criteria>
<done>网络基础能力就绪，可生成带鉴权头的请求</done>
</task>

<task>
<name>实现 content 构建与任务创建 API（API-02）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/03-api-client/03-CONTEXT.md
- docs/require/zlhub-seedance2.0-video-api.md
- video_plugin_zzdhapi/main.py
</read_first>
<action>
新增 `file_to_base64(file_path)`，将本地图片编码为 `data:image/...;base64,...`；若是 `http://`、`https://`、`data:`、`asset://` 直接原样返回。新增 `_build_content_items(prompt, reference_images=None, reference_videos=None, reference_audios=None, role_mode="reference_image")`：始终先写入 `{"type":"text","text":prompt}`；图片条目写入 `{"type":"image_url","image_url":{"url":...},"role":"reference_image"}`，视频条目写入 `{"type":"video_url","video_url":{"url":...},"role":"reference_video"}`，音频条目写入 `{"type":"audio_url","audio_url":{"url":...},"role":"reference_audio"}`。新增 `_build_create_payload(params, prompt, ...)`，生成字段 `model`、`content`、`generate_audio`、`resolution`、`ratio`、`duration`，且仅在“纯文本模式 + web_search 为 true”时附加 `tools: [{"type":"web_search"}]`。新增 `_create_task(api_key, base_url, payload, timeout)`，向 `${base_url}` 发 `POST`，从响应提取 `task_id = result.get("id") or result.get("task_id")`，无任务 ID 则抛 `PluginFatalError`。
</action>
<verify>
grep "def file_to_base64" video_plugin_zlhub_seedance/main.py
grep "def _build_content_items" video_plugin_zlhub_seedance/main.py
grep "def _build_create_payload" video_plugin_zlhub_seedance/main.py
grep "def _create_task" video_plugin_zlhub_seedance/main.py
grep "\"tools\": \\[{\"type\": \"web_search\"}\\]" video_plugin_zlhub_seedance/main.py
grep "result.get(\"id\") or result.get(\"task_id\")" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 存在 `file_to_base64` 并支持 `data:` 前缀输出或 URL 透传。
- `content` 构建逻辑包含 `text/image_url/video_url/audio_url` 四类对象。
- `_create_task` 存在 task id 提取兜底：`id` 与 `task_id` 两种键。
- `_build_create_payload` 只在纯文本模式启用 `tools.web_search`。
</acceptance_criteria>
<done>任务创建链路完成，返回可轮询的任务 ID</done>
</task>

<task>
<name>实现任务状态轮询（API-03）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/03-api-client/03-CONTEXT.md
- docs/require/zlhub-seedance2.0-video-api.md
- video_plugin_geeknow/main.py
</read_first>
<action>
新增 `_normalize_task_status(raw_status)`，统一将大小写状态映射为 `running | completed | failed | unknown`。新增 `_extract_video_url_from_status(task_data)`，按顺序读取 `content.video_url`、`video_url`、`url`。新增 `_poll_task_status(api_key, base_url, task_id, timeout, max_attempts, poll_interval, progress_callback=None)`：请求 `GET {base_url}/{task_id}`，循环等待；`running` 继续轮询并可触发进度回调；`completed` 返回视频 URL（允许空 URL，交给下载阶段回退）；`failed` 从 `fail_reason` 或 `reason` 取原因并抛 `PluginFatalError`；超过最大轮询次数抛 `PluginFatalError`。
</action>
<verify>
grep "def _normalize_task_status" video_plugin_zlhub_seedance/main.py
grep "def _extract_video_url_from_status" video_plugin_zlhub_seedance/main.py
grep "def _poll_task_status" video_plugin_zlhub_seedance/main.py
grep "GET" video_plugin_zlhub_seedance/main.py | grep "tasks/{task_id}"
grep "fail_reason" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 轮询函数存在 `max_attempts` 与 `poll_interval` 参数。
- 状态映射逻辑至少覆盖 `running`、`completed/succeeded`、`failed`。
- 失败路径明确读取 `fail_reason` 或 `reason` 并抛 `PluginFatalError`。
- 超时路径存在“超过轮询上限”的错误抛出分支。
</acceptance_criteria>
<done>状态轮询可稳定返回完成状态或可诊断失败原因</done>
</task>

<task>
<name>实现双路径下载与文件落盘（API-04）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/03-api-client/03-CONTEXT.md
- docs/require/zlhub-seedance2.0-video-api.md
- video_plugin_geeknow/main.py
</read_first>
<action>
新增 `_download_video(api_key, base_url, task_id, video_url, output_path, timeout)`：优先下载 `video_url`；若该请求非 200 或抛异常，则回退到 `GET {base_url.replace('/v1/proxy/ark/contents/generations/tasks', '')}/v1/videos/{task_id}/content`。下载请求头必须包含 `User-Agent` 与 `Referer: https://zlhub.xiaowaiyou.cn/`；当目标地址同源或回退接口时附加 `Authorization`。响应为 200 时将二进制写入 `output_path` 并返回该路径，否则抛 `PluginFatalError("下载视频失败")`。
</action>
<verify>
grep "def _download_video" video_plugin_zlhub_seedance/main.py
grep "Referer\": \"https://zlhub.xiaowaiyou.cn/\"" video_plugin_zlhub_seedance/main.py
grep "/v1/videos/{task_id}/content" video_plugin_zlhub_seedance/main.py
grep "with open(output_path, \"wb\")" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 下载函数同时包含直链下载和 `/v1/videos/{task_id}/content` 回退路径。
- 下载头中存在 `User-Agent` 与固定 `Referer`。
- 成功路径存在 `wb` 文件写入；失败路径抛 `PluginFatalError`。
</acceptance_criteria>
<done>视频下载具备防盗链头与失败回退能力</done>
</task>

<task>
<name>交付阶段 3 对外可调用接口与最小自测入口</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- video_plugin_zlhub_seedance/main.py
- .planning/phases/03-api-client/03-CONTEXT.md
</read_first>
<action>
新增对外组合函数 `run_seedance_client(...)`（命名可调整，但必须固定单一入口），按顺序调用 `_build_create_payload -> _create_task -> _poll_task_status -> _download_video`，返回 `{task_id, status, video_url, output_path}` 结构。保留 `generate()` 未实现状态，但在 docstring 中注明“阶段 4/5 负责编排调用”。在 `if __name__ == "__main__":` 下增加最小 smoke 检查（仅校验必需函数存在，不发真实网络请求），便于本地快速验证文件完整性。
</action>
<verify>
grep "def run_seedance_client" video_plugin_zlhub_seedance/main.py
grep "_create_task(" video_plugin_zlhub_seedance/main.py
grep "_poll_task_status(" video_plugin_zlhub_seedance/main.py
grep "_download_video(" video_plugin_zlhub_seedance/main.py
grep "__name__ == \"__main__\"" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 存在单入口客户端函数并串联创建、轮询、下载三个核心步骤。
- 返回结构包含 `task_id` 与 `output_path` 字段。
- 文件底部存在无网络依赖的最小 smoke 验证逻辑。
</acceptance_criteria>
<done>阶段 3 API 客户端功能闭环完成，供编排层接入</done>
</task>

## Verification

### Automated Checks
- `python -m py_compile video_plugin_zlhub_seedance/main.py`
- `python -c "import video_plugin_zlhub_seedance.main as m; print(callable(getattr(m, '_create_task', None)))"`
- `python -c "import video_plugin_zlhub_seedance.main as m; print(callable(getattr(m, '_poll_task_status', None)))"`
- `python -c "import video_plugin_zlhub_seedance.main as m; print(callable(getattr(m, '_download_video', None)))"`

### Manual Verification
- 使用一个有效 API Key 在本地脚本中调用 `run_seedance_client(...)`，确认返回包含 `task_id`。
- 人工模拟错误 Key，确认报错前缀为 `PLUGIN_ERROR:::`。
- 将直链下载 URL 人为置空或置为无效，确认触发 content 回退下载逻辑。
