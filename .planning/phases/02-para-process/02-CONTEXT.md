# Phase 2: 参数处理 - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段实现将宿主输入清洗、校验并规范化为 Seedance 2.0 API 特定约束的逻辑。包括分辨率/比例映射、时长边界处理、图像物理约束校验、音频开关映射。

本阶段不涉及实际的 API 调用逻辑（阶段 3）或 `generate()` 主流程编排（阶段 5）。
</domain>

<decisions>
## Implementation Decisions

### 分辨率/比例映射 (PARA-01)
- **D-01:** 实现本地映射表，将 `resolution` + `ratio` 组合映射到具体物理像素值（如 `720p` + `16:9` → `1280×720`）。
- **D-02:** 映射表参照 API 文档对照表实现，覆盖 `480p`/`720p` × 所有 `ratio` 组合。
- **D-03:** `adaptive` 比例由服务端处理，本地透传。

### 时长边界处理 (PARA-02)
- **D-04:** 支持传入 `-1` 表示智能时长，透传给 API。
- **D-05:** 其他越界值采用截断策略：小于 4 的设为 4，大于 15 的设为 15（静默修正，不报错）。
- **D-06:** 默认时长保持 `5` 秒。

### 图像物理约束校验 (PARA-03)
- **D-07:** 采用宽松校验策略 — 仅检查文件格式（`jpeg/png/webp/bmp/tiff/gif`）和文件大小 `<30MB`。
- **D-08:** 边长 `[300, 6000]` 和宽高比 `(0.4, 2.5)` 约束交给服务端处理，本地不校验。
- **D-09:** 校验失败时抛出 `PLUGIN_ERROR:::` 前缀的异常（快速失败）。

### 音频开关映射
- **D-10:** 直接使用布尔值（`true`/`false`），无需封装为常量。
- **D-11:** `_sanitize_params` 中实现字符串到布尔的转换（`"true"`/`"false"`/`"1"`/`"0"` 等）。

### 错误处理与重试策略
- **D-12:** 参数校验失败时抛出 `PLUGIN_ERROR:::` 前缀的异常，与阶段 5 统一错误格式。
- **D-13:** 使用 `PluginFatalError` 异常类（参照 `video_plugin_zzdhapi` 模式）。

### 轮询策略
- **D-14:** 保持默认 5 秒间隔，300 次轮询上限（与现有插件保持一致）。
- **D-15:** `timeout=900` 秒（15 分钟），`max_poll_attempts=300`，`poll_interval=5`。

### 参数持久化策略
- **D-16:** 仅在参数变化时持久化（减少磁盘 I/O，Phase 1 实现已足够）。

### Claude's Discretion
- 映射表的具体实现结构（可使用字典或独立常量）。
- 图像校验工具函数的命名和模块化方式。
- 时长截断时是否打印警告日志（建议打印，便于调试）。
</decisions>

<canonical_refs>
## Canonical References

### 参数处理规范
- `docs/require/zlhub-seedance2.0-video-api.md` — API 参数约束、分辨率/比例对照表、图像物理约束。
- `video_plugin_zzdhapi/main.py` — 参考实现（`MODEL_CONFIGS` 模式、`_sanitize_params` 逻辑、`PluginFatalError` 异常类）。

### 项目需求
- `.planning/REQUIREMENTS.md` — Phase 2 对应的 PARA-01, PARA-02, PARA-03 需求。
- `.planning/PROJECT.md` — 项目核心价值和约束。
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `video_plugin_zlhub_seedance/main.py` — Phase 1 已实现 `get_info()`、`get_params()`、`_sanitize_params()` 骨架。
- `video_plugin_zzdhapi/main.py` — 完整的 `_normalize_*` 函数族、`MODEL_CONFIGS` 配置模式、`PluginFatalError` 异常类。
- `plugin_utils` — 配置加载/持久化通用工具（`load_plugin_config`/`save_plugin_config`）。

### Established Patterns
- 参数清洗函数命名：`_normalize_*`（如 `_normalize_resolution`、`_normalize_duration`）。
- 错误前缀：`PLUGIN_ERROR:::` 用于所有面向用户的错误消息。
- 异常类：`PluginFatalError` 用于致命错误。

### Integration Points
- `get_params()` — 宿主调用以获取 UI 配置参数，需返回清洗后的参数。
- `_sanitize_params()` — 内部工具函数，被 `get_params()` 和 `generate()` 调用。
</code_context>

<specifics>
## Specific Ideas

- "分辨率映射参照 API 文档对照表实现，确保每个组合对应正确的物理像素值。"
- "时长支持 `-1` 智能时长，其他越界值静默截断到 `[4, 15]` 范围内。"
- "图像校验只做格式和大小检查，复杂的几何约束交给 ZLHub 服务端处理。"
- "错误处理统一使用 `PLUGIN_ERROR:::` 前缀，便于宿主程序识别。"
</specifics>

<deferred>
## Deferred Ideas

- API 客户端实现（任务创建、状态轮询、视频下载）— 阶段 3。
- `generate()` 主流程编排 — 阶段 5。
- 详细的 API 错误映射（如 HTTP 状态码到 `PLUGIN_ERROR:::` 的映射）— 阶段 5。
- 高级重试策略（如指数退避）— v2 需求（OPS-02）。
- SQLite 任务历史数据库 — v2 需求（OPS-02）。

### Reviewed Todos (not folded)
- 无 — 讨论保持在 Phase 2 范围内。
</deferred>

---

*Phase: 02-para-process*
*Context gathered: 2026-03-31*
