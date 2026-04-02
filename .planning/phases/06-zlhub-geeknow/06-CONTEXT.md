# Phase 6: zlhub-geeknow - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

在 `video_plugin_zlhub_seedance` 中补齐“实时日志窗口 + 任务日志窗口（含手动下载入口）”，并确保宿主可通过插件动作打开页面与获取数据；不扩展到新的视频生成能力或宿主改造。

</domain>

<decisions>
## Implementation Decisions

### 日志格式与字段契约（对齐 geeknow）
- **D-01:** 阶段 6 的日志输出格式与核心字段必须对齐 `docs/require/geeknow-logs.txt`，作为实现与验收基线。
- **D-02:** 实时日志条目采用结构化字段：`index`、`time`、`level`、`msg`（与 `video_plugin_geeknow` 的轮询渲染契约一致）。
- **D-03:** 任务日志记录至少覆盖：任务基础信息、状态、错误、输出路径/视频 URL，支持按时间倒序展示。

### 实时日志界面行为
- **D-04:** 新增独立 `live_log.html`，保留自动滚动开关、清空视图、2 秒轮询与“等待日志”状态提示。
- **D-05:** 前端与宿主交互沿用插件动作通道（`get_logs` action），避免引入额外通信机制。

### 任务日志界面行为
- **D-06:** 新增独立 `task_log.html`，提供状态筛选、批量勾选、批量下载、结果反馈区。
- **D-07:** 仅允许对存在可下载地址的任务执行“下载选中视频”，无 URL 的行默认禁用选择。
- **D-08:** 状态展示使用映射 badge（success/failed/running/download_failed 等），与任务实际状态解耦。

### 插件后端接口与存储
- **D-09:** 在 `main.py` 增加与 geeknow 同构的动作路由：`open_live_logs`、`open_task_logs`、`get_logs`、`get_task_logs`、`download_videos`。
- **D-10:** 任务日志采用 SQLite 本地库持久化（数据库结构与关键字段命名对齐 geeknow 方案）。
- **D-11:** 保持现有 `generate(context)` 主链路不变，仅增强调试与可观测性能力。

### the agent's Discretion
- 实时日志缓存上限（推荐与 geeknow 同级，避免无限增长）。
- 任务日志表格的列宽、截断长度、文案细节。
- 下载结果区展示样式（成功/失败信息分层方式）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 日志格式基准
- `docs/require/geeknow-logs.txt` - 参考日志样本与字段形态，Phase 6 必须对齐。

### 参考实现（Geeknow）
- `video_plugin_geeknow/main.py` - 日志缓冲、任务日志库、action 路由与下载流程。
- `video_plugin_geeknow/ui/live_log.html` - 实时日志页面结构、轮询与自动滚动交互。
- `video_plugin_geeknow/ui/task_log.html` - 任务日志筛选、批量选择与下载交互。
- `video_plugin_geeknow/ui/index.html` - 打开“实时日志/任务日志”入口按钮与动作触发方式。

### 目标实现（ZLHub）
- `video_plugin_zlhub_seedance/main.py` - 当前生成链路与可扩展 action 入口位置。
- `video_plugin_zlhub_seedance/ui/index.html` - 现有配置 UI，需增加日志入口。

### 项目范围约束
- `.planning/ROADMAP.md` - 阶段 6 定义与里程碑依赖关系。
- `.planning/REQUIREMENTS.md` - 已有需求边界（避免扩展到宿主改造）。
- `.planning/PROJECT.md` - 核心约束：不修改宿主程序。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `video_plugin_geeknow/main.py`: 已有可复用模式，包括日志缓冲结构、`handle_action` 路由、SQLite 任务日志读写、批量下载执行。
- `video_plugin_geeknow/ui/live_log.html`: 可直接迁移的实时日志视图框架（header/status/log-container + 轮询）。
- `video_plugin_geeknow/ui/task_log.html`: 可直接迁移的任务日志表格交互（筛选、全选、下载结果反馈）。

### Established Patterns
- 前端通过 `window.opener.postMessage` 与宿主通信，action 名称和载荷是稳定契约。
- 插件后端通过 `handle_action(action, data)` 暴露 UI 动作处理。
- 日志文本与结构化 JSON 事件共存（便于人工排障与机器解析）。

### Integration Points
- `video_plugin_zlhub_seedance/main.py`: 新增 action 分发、日志缓存与任务日志存储入口。
- `video_plugin_zlhub_seedance/ui/index.html`: 增加“实时日志”“任务日志”按钮并发送对应 action。
- `video_plugin_zlhub_seedance/ui/`: 新增 `live_log.html` 与 `task_log.html`。

</code_context>

<specifics>
## Specific Ideas

- [auto] 讨论模式为 `--auto`，自动选择全部灰区并采用推荐项。
- 明确结论：日志格式与字段对齐 `docs/require/geeknow-logs.txt`。
- 交互风格优先“可排障”：状态可见、错误可见、手动下载可见。

</specifics>

<deferred>
## Deferred Ideas

- 日志检索（关键词、高级过滤）与导出能力（CSV/JSON）不纳入本阶段。
- 远程日志上报/集中化监控不纳入本阶段。

</deferred>

---

*Phase: 06-zlhub-geeknow*
*Context gathered: 2026-04-02*
