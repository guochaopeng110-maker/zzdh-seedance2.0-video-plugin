# Phase 3: API Client - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段实现与 ZLHub Seedance 2.0 中转平台的通讯逻辑。包括：
1. 身份验证 (API-01)
2. 任务创建 (API-02)
3. 状态查询/轮询 (API-03)
4. 双重产物下载 (API-04)

本阶段不涉及 `main.py:generate()` 的完整编排（由阶段 5 完成），但需提供可被调用的独立函数或类。
</domain>

<decisions>
## Implementation Decisions

### 身份验证 (API-01)
- **D-01:** 使用 `Authorization: Bearer $ARK_API_KEY` 请求头。
- **D-02:** API Key 从插件配置中读取，若为空则抛出 `PluginFatalError`。

### 任务创建与 Payload (API-02)
- **D-03:** 媒体上传策略：初期采用 **Base64 嵌入**。单张图片限制 30MB，请求体总限制 64MB。
- **D-04:** 结构化 `content` 数组：将 Prompt、图片、视频、音频按 API 指定的 `type` 和 `role` 顺序排列。
- **D-05:** 角色映射逻辑：
    - 多图场景统一使用 `role: "reference_image"`。
    - 若用户意图为首帧/首尾帧效果，需在 Prompt 文本中自动/手动指定图片索引（如“首帧为图片 1”）。
- **D-06:** 联网搜索预留：
    - 仅在**纯文本**生成模式下，若配置开启，则在 `tools` 数组中添加 `{"type": "web_search"}`。
    - 非纯文本模式（有参考图/视频）时暂不启用工具。

### 状态查询 (API-03)
- **D-07:** 轮询端点：`GET /v1/proxy/ark/contents/generations/tasks/{id}`。
- **D-08:** 状态识别：
    - `running` -> 继续等待。
    - `completed` -> 提取下载链接。
    - `failed` -> 抛出异常并包含 `fail_reason`。

### 产物获取 (API-04)
- **D-09:** 实现**双重下载路径**：
    1. 首先尝试 `status` 响应中的 `video_url`。
    2. 若直接下载失败，尝试调用备份接口 `GET /v1/videos/{task_id}/content`。
- **D-10:** 下载时使用标准 `User-Agent` 和 `Referer: https://zlhub.xiaowaiyou.cn/` 以应对防盗链。

### Claude's Discretion
- 网络请求库的选择（建议使用 `requests` 以保持一致性）。
- `content` 数组构建工具函数的具体实现。
- 轮询时的进度百分比模拟逻辑（API 若未返回具体百分比则根据时间估算）。
</decisions>

<canonical_refs>
## Canonical References

### API 规范
- `docs/require/zlhub-seedance2.0-video-api.md` — 核心 API 契约、Payload 结构、状态字段。
- `video_plugin_zlhub_seedance/main.py` — 已定义的参数常量（`_BASE_URL_OPTIONS` 等）。

### 参考实现
- `video_plugin_zzdhapi/main.py` — 参考其 `file_to_base64` 和 `_build_standard_payload`。
- `video_plugin_geeknow/main.py` — 参考其 `_poll_video_status` 和 `_download_video`（特别是双重下载逻辑）。
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `video_plugin_zlhub_seedance/main.py` — `PluginFatalError` 类已就绪。
- `video_plugin_zzdhapi/main.py` — `file_to_base64` 函数（带压缩逻辑）。
- `video_plugin_geeknow/main.py` — 带有超时控制和异常处理的轮询循环。

### Integration Points
- 核心函数 `_create_task`：返回 `task_id`。
- 核心函数 `_poll_status`：返回 `video_url`。
- 核心函数 `_download`：返回本地路径。
</code_context>

<specifics>
## Specific Ideas

- "Payload 构建需严格遵循 content 数组 schema，不要将所有参数塞进顶层。"
- "对于 Base64，确保在图片 path 含有参数时先进行 strip 处理。"
- "下载时必须处理 HTTP 403 错误，并自动切换到备份接口。"
</specifics>

<deferred>
## Deferred Ideas

- 视频生视频 (ADV-01) — 阶段 4/v2。
- 联网搜索工具与多模态组合 (ADV-03) — v2。
- SQLite 任务历史数据库 (OPS-02) — v2。
</deferred>

---

*Phase: 03-api-client*
*Context gathered: 2026-03-31*
