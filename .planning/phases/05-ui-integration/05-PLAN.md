---
phase: 5
plan: 01
type: plan
name: UI 与集成
objective: 完成 generate(context) 宿主入口接线，并交付统一错误前缀、进度回调与关键生命周期日志能力，使插件达到可上线主链路状态。
wave: 1
depends_on: [4]
files_modified: [video_plugin_zlhub_seedance/main.py, video_plugin_zlhub_seedance/ui/index.html]
autonomous: true
requirements: [ERR-01, ERR-02, ERR-03, CONT-03]
must_haves:
  - "generate(context) 必须调用 Phase 4 的 run_seedance_workflow(context)"
  - "所有对外抛出的错误都以 PLUGIN_ERROR::: 开头"
  - "生成过程必须向宿主回调关键进度节点"
  - "必须记录任务 ID、状态变化、失败原因等生命周期日志"
---

# Phase 5: UI 与集成 - Plan

本阶段目标是“完成插件宿主接线”，把前四阶段能力收敛为可被宿主直接触发的最终入口。  
重点交付：`generate(context)`、错误标准化、回调和日志可观测性。

## Wave 1: 最终集成与可观测性

<task>
<name>实现 generate(context) 作为宿主入口（CONT-03）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/04-orchestration/04-SUMMARY.md
- .planning/phases/04-orchestration/04-VERIFICATION.md
- .planning/REQUIREMENTS.md
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
将 `generate(context)` 从 `NotImplementedError` 改为实际实现。函数内部统一读取 `prompt`、`reference_images`、`output_dir`、`viewer_index`、`plugin_params`，并调用 `run_seedance_workflow(context)`。返回值必须为宿主可消费的 `list[str]` 本地视频路径。禁止在 `generate` 内重复实现 create/poll/download，避免与编排层逻辑分叉。
</action>
<verify>
grep "def generate(context)" video_plugin_zlhub_seedance/main.py
grep "run_seedance_workflow(context)" video_plugin_zlhub_seedance/main.py
grep "return" video_plugin_zlhub_seedance/main.py | grep "generate"
</verify>
<acceptance_criteria>
- `generate(context)` 不再抛 `NotImplementedError`。
- `generate(context)` 内存在 `run_seedance_workflow(context)` 调用。
- `generate(context)` 对成功场景返回 `list[str]` 输出路径。
</acceptance_criteria>
<done>宿主入口已接线，插件可触发完整工作流</done>
</task>

<task>
<name>统一错误前缀与异常边界（ERR-01）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- video_plugin_zlhub_seedance/main.py
- .planning/REQUIREMENTS.md
</read_first>
<action>
在 `generate(context)` 外围增加 `try/except`：捕获 `PluginFatalError` 直接透传；捕获其他异常时统一包装为 `PluginFatalError(str(exc))` 再抛出，确保面向宿主的错误都包含 `PLUGIN_ERROR:::`。检查并补齐仍可能抛出裸 `Exception` 的路径，统一转为 `PluginFatalError`。
</action>
<verify>
grep "except PluginFatalError" video_plugin_zlhub_seedance/main.py
grep "raise PluginFatalError" video_plugin_zlhub_seedance/main.py
grep "PLUGIN_ERROR:::" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- `generate(context)` 异常出口仅抛 `PluginFatalError`。
- 任意失败路径错误文本均带 `PLUGIN_ERROR:::` 前缀。
- 不存在面向宿主的裸 `Exception(...)` 抛出路径。
</acceptance_criteria>
<done>宿主可收到统一前缀错误，便于 UI 标准展示</done>
</task>

<task>
<name>实现宿主进度回调桥接（ERR-02）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/04-orchestration/04-PLAN.md
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
在 `generate(context)` 中桥接 `progress_callback`：若宿主传入回调则透传到 `run_seedance_workflow` 所用 context；若未传入则创建 no-op 回调，避免空引用。规范阶段进度消息集合（建议最少包含：`参数校验完成`、`任务已创建`、`状态轮询中`、`下载中`、`完成/失败`），并确保回调在成功和失败路径都触发收尾状态。
</action>
<verify>
grep "progress_callback" video_plugin_zlhub_seedance/main.py
grep "参数校验完成" video_plugin_zlhub_seedance/main.py
grep "任务已创建" video_plugin_zlhub_seedance/main.py
grep "下载中" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 宿主传入的 `progress_callback` 能贯穿整个执行链路。
- 无 `progress_callback` 时执行不报错。
- 失败路径也会产生最终进度状态（如“失败”）。
</acceptance_criteria>
<done>宿主可实时感知生成进度并正确结束状态</done>
</task>

<task>
<name>补齐生命周期日志（ERR-03）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- video_plugin_zlhub_seedance/main.py
- .planning/REQUIREMENTS.md
</read_first>
<action>
新增轻量日志函数（例如 `_log_event(event, **fields)`），默认输出到控制台（可选写入本地日志文件，路径放插件目录）。在关键节点写日志：开始请求、创建成功（含 `task_id`）、轮询状态变化、下载开始/成功、失败原因。日志内容避免暴露完整 API Key（只保留掩码长度或前后缀）。
</action>
<verify>
grep "def _log_event" video_plugin_zlhub_seedance/main.py
grep "task_id" video_plugin_zlhub_seedance/main.py
grep "轮询" video_plugin_zlhub_seedance/main.py
grep "失败" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 至少覆盖 5 类生命周期事件日志（开始、创建、轮询、下载、失败/完成）。
- 日志中不出现完整明文 API Key。
- 失败日志包含可定位问题的错误摘要字段。
</acceptance_criteria>
<done>关键执行路径可观测，便于宿主排障与回溯</done>
</task>

<task>
<name>UI 参数与集成一致性收尾</name>
<files>
- video_plugin_zlhub_seedance/ui/index.html
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- video_plugin_zlhub_seedance/ui/index.html
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
检查 UI 配置项与后端参数字段完全一致：`api_key/base_url/resolution/ratio/duration/generate_audio/web_search/timeout`。若后端使用 `max_poll_attempts/poll_interval/retry_count` 且期望用户可调，则在 `index.html` 增加对应输入并持久化到 `PluginSDK.saveParam`。保证 `PluginSDK.onReady` 可回填所有新增字段，避免宿主重启后参数丢失。
</action>
<verify>
grep "saveParam('max_poll_attempts'" video_plugin_zlhub_seedance/ui/index.html
grep "saveParam('poll_interval'" video_plugin_zlhub_seedance/ui/index.html
grep "saveParam('retry_count'" video_plugin_zlhub_seedance/ui/index.html
grep "onReady" video_plugin_zlhub_seedance/ui/index.html
</verify>
<acceptance_criteria>
- UI 与后端参数字段集合一致（至少不缺后端必需字段）。
- 新增字段可保存并在 `onReady` 回填。
- 无因字段缺失导致的默认值污染或运行时 KeyError。
</acceptance_criteria>
<done>配置页与运行时参数模型对齐，减少集成偏差</done>
</task>

## Verification

### Automated Checks
- `python -m py_compile video_plugin_zlhub_seedance/main.py`
- `python -c "import importlib.util as iu; p=r'F:\\Projects\\zz-video-plugins\\video_plugin_zlhub_seedance\\main.py'; s=iu.spec_from_file_location('m', p); m=iu.module_from_spec(s); s.loader.exec_module(m); print(callable(getattr(m,'generate',None))); print(callable(getattr(m,'run_seedance_workflow',None)))"`

### Manual Verification
- 在宿主环境触发一次成功任务，确认：有进度更新、最终输出视频路径列表、日志包含 task_id。
- 使用错误 API Key 触发失败，确认宿主显示错误前缀为 `PLUGIN_ERROR:::`。
- 重启宿主后检查 UI 参数回填是否完整（含新增轮询参数，如已加入）。
