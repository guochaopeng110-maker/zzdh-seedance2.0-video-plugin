---
phase: 6
plan: 01
type: plan
name: 实时日志与任务日志界面
objective: 在不改宿主程序与不破坏现有生成链路的前提下，为 zlhub 插件补齐实时日志窗口、任务日志窗口和手动下载能力，且日志格式与字段对齐 geeknow-logs.txt。
wave: 1
depends_on: [5]
files_modified: [video_plugin_zlhub_seedance/main.py, video_plugin_zlhub_seedance/ui/index.html, video_plugin_zlhub_seedance/ui/live_log.html, video_plugin_zlhub_seedance/ui/task_log.html]
autonomous: true
requirements: []
must_haves:
  - "实时日志输出字段必须包含 index/time/level/msg，并与 geeknow-logs.txt 对齐"
  - "任务日志页面支持状态筛选、批量勾选、批量下载，仅可下载存在 video_url 的任务"
  - "main.py 必须提供 open_live_logs/open_task_logs/get_logs/get_task_logs/download_videos 动作路由"
  - "generate(context) 主链路行为保持不变，新增能力仅限可观测性与日志界面"
---

# Phase 6: 实时日志与任务日志界面 - Plan

本计划将 Phase 6 收敛为单波次实现：
1) 后端补齐日志缓存与任务日志持久化；
2) UI 增加实时日志与任务日志页面；
3) 首页增加日志入口按钮；
4) 用结构化自检确保字段契约和动作路由完整。

## Wave 1: 日志能力同构接入

<task>
<name>扩展 main.py：日志缓冲、任务日志存储与动作路由</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- docs/require/geeknow-logs.txt
- video_plugin_geeknow/main.py
- video_plugin_zlhub_seedance/main.py
- .planning/phases/06-zlhub-geeknow/06-CONTEXT.md
</read_first>
<action>
在 `video_plugin_zlhub_seedance/main.py` 中新增与 geeknow 同构的日志层：
1. 实时日志缓冲：使用 `deque + threading.Lock`，并提供 `get_buffered_logs(since_index)`。
2. 任务日志 SQLite：初始化 `video_task_logs.db`，至少包含 `id/created_at/model_name/model_display/prompt/status/error/video_url/local_path/generation_mode/duration` 字段。
3. 在现有生成链路关键节点写入日志与任务状态变更（running/success/failed/download_failed/manual_success/manual_failed）。
4. 新增 `handle_action(action, data=None)`，支持：
   - `open_live_logs` -> `{'ok': true, 'open_page': 'live_log.html'}`
   - `open_task_logs` -> `{'ok': true, 'open_page': 'task_log.html'}`
   - `get_logs` / `get_task_logs` / `download_videos`
5. 保持 `generate(context)` 行为不变：只在内部补日志，不改输入输出契约。
</action>
<verify>
rg -n "def handle_action|open_live_logs|open_task_logs|get_logs|get_task_logs|download_videos|sqlite3|deque|threading.Lock|video_task_logs" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- `main.py` 可检索到 5 个动作关键字：`open_live_logs/open_task_logs/get_logs/get_task_logs/download_videos`。
- 存在实时日志缓冲结构（`deque` + 索引）和读取函数。
- 存在任务日志 SQLite 初始化与基本增改查流程。
- 不移除或破坏现有 `run_seedance_workflow` / `generate(context)` 输出语义。
</acceptance_criteria>
<done>后端日志基础设施与宿主动作路由可用</done>
</task>

<task>
<name>新增 live_log.html：实时日志页面</name>
<files>
- video_plugin_zlhub_seedance/ui/live_log.html
</files>
<read_first>
- video_plugin_geeknow/ui/live_log.html
- .planning/phases/06-zlhub-geeknow/06-CONTEXT.md
</read_first>
<action>
新增 `ui/live_log.html`，复用 geeknow 交互模型：
- 顶栏包含标题、状态文本、自动滚动开关、清空按钮。
- 日志区域按 `time + msg` 渲染，支持 `ERROR/WARNING/INFO/DEBUG` 样式。
- 每 2 秒发送 `get_logs` 动作，携带 `since_index` 增量拉取。
- 无日志时显示“等待日志”提示。
- 与宿主通信使用 `window.opener.postMessage` 协议，消息结构保持兼容。
</action>
<verify>
rg -n "get_logs|since_index|setInterval\(poll, 2000\)|autoScroll|clearBtn|logContainer" video_plugin_zlhub_seedance/ui/live_log.html
</verify>
<acceptance_criteria>
- 页面存在 2 秒轮询 `get_logs` 逻辑。
- 支持自动滚动开关和清空视图。
- 可正确消费 `entries[index,time,level,msg]` 格式。
</acceptance_criteria>
<done>实时日志页面可独立打开并显示增量日志</done>
</task>

<task>
<name>新增 task_log.html：任务日志与手动下载页面</name>
<files>
- video_plugin_zlhub_seedance/ui/task_log.html
</files>
<read_first>
- video_plugin_geeknow/ui/task_log.html
- .planning/phases/06-zlhub-geeknow/06-CONTEXT.md
</read_first>
<action>
新增 `ui/task_log.html`，实现：
- 状态筛选（全部/success/manual_success/download_failed/failed/no_retry_error/running）。
- 表格展示核心字段（ID/时间/模型/状态/模式/时长/提示词/错误信息）。
- 勾选与全选：仅对有 `video_url` 的任务可勾选。
- 点击“下载选中视频”发送 `download_videos` 动作并显示结果。
- 刷新动作调用 `get_task_logs`，默认按时间倒序。
</action>
<verify>
rg -n "get_task_logs|download_videos|statusFilter|checkAll|status-badge|video_url" video_plugin_zlhub_seedance/ui/task_log.html
</verify>
<acceptance_criteria>
- 页面可触发 `get_task_logs` 并渲染表格。
- 页面可触发 `download_videos` 并显示逐项结果。
- 无 `video_url` 行默认禁用勾选。
</acceptance_criteria>
<done>任务日志页面可筛选、可批量下载、可反馈下载结果</done>
</task>

<task>
<name>更新 index.html：增加日志入口并联通后端动作</name>
<files>
- video_plugin_zlhub_seedance/ui/index.html
</files>
<read_first>
- video_plugin_geeknow/ui/index.html
- video_plugin_zlhub_seedance/ui/index.html
</read_first>
<action>
在 `ui/index.html` 增加两个按钮：
- `实时日志` -> 发送 `open_live_logs`
- `任务日志 / 手动拉取` -> 发送 `open_task_logs`
并复用当前 `PluginSDK.sendAction` 调用方式，保持现有参数配置区和保存逻辑不受影响。
</action>
<verify>
rg -n "open_live_logs|open_task_logs|sendAction\(" video_plugin_zlhub_seedance/ui/index.html
</verify>
<acceptance_criteria>
- 首页存在两个日志入口按钮。
- 按钮动作名与后端 `handle_action` 一致。
- 不影响现有参数保存/回填逻辑。
</acceptance_criteria>
<done>用户可从插件主配置页进入两个日志子页面</done>
</task>

<task>
<name>结构化自检：字段契约与行为回归</name>
<files>
- video_plugin_zlhub_seedance/main.py
- video_plugin_zlhub_seedance/ui/live_log.html
- video_plugin_zlhub_seedance/ui/task_log.html
- video_plugin_zlhub_seedance/ui/index.html
</files>
<read_first>
- docs/require/geeknow-logs.txt
- .planning/phases/06-zlhub-geeknow/06-CONTEXT.md
</read_first>
<action>
执行最小验证：
1. 语法检查：`python -m py_compile video_plugin_zlhub_seedance/main.py`。
2. 契约检查：grep 确认实时日志字段 `index/time/level/msg` 与动作路由关键字完整。
3. UI 交互检查：grep 确认 live/task/index 三页动作名一致。
4. 回归检查：grep `generate(`、`run_seedance_workflow(` 确认主链路入口仍在。
</action>
<verify>
python -m py_compile video_plugin_zlhub_seedance/main.py
rg -n "index|time|level|msg|open_live_logs|open_task_logs|get_logs|get_task_logs|download_videos|run_seedance_workflow|def generate\(" video_plugin_zlhub_seedance/main.py video_plugin_zlhub_seedance/ui/live_log.html video_plugin_zlhub_seedance/ui/task_log.html video_plugin_zlhub_seedance/ui/index.html
</verify>
<acceptance_criteria>
- `main.py` 语法检查通过。
- 字段契约与动作路由关键字齐全。
- `generate(context)` 入口和 `run_seedance_workflow` 未被破坏。
</acceptance_criteria>
<done>阶段交付具备执行前最小可信度，满足后续 execute-phase 输入要求</done>
</task>

## Verification

### Automated Checks
- `python -m py_compile video_plugin_zlhub_seedance/main.py`
- `rg -n "open_live_logs|open_task_logs|get_logs|get_task_logs|download_videos" video_plugin_zlhub_seedance/main.py`
- `rg -n "setInterval\(poll, 2000\)|get_logs|get_task_logs|download_videos" video_plugin_zlhub_seedance/ui/live_log.html video_plugin_zlhub_seedance/ui/task_log.html`

### Manual Verification
- 宿主打开插件配置页后，点击“实时日志”可弹窗并持续更新日志。
- 宿主打开“任务日志 / 手动拉取”后，可筛选状态并下载选中任务。
- 生成任务成功/失败都能在日志中看到关键事件与状态。
