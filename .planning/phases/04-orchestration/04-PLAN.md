---
phase: 4
plan: 01
type: plan
name: 逻辑编排
objective: 在不实现 generate() 最终宿主接入的前提下，交付可复用的端到端执行编排函数，串联参数校验、任务创建、状态轮询与下载，并稳定映射终态结果。
wave: 1
depends_on: [3]
files_modified: [video_plugin_zlhub_seedance/main.py]
autonomous: true
requirements: [ORCH-01, ORCH-02, ORCH-03]
must_haves:
  - "编排入口必须按 sanitize -> create -> poll -> download 顺序执行"
  - "轮询必须尊重 timeout/max_poll_attempts/poll_interval 配置"
  - "终端状态必须收敛为 completed/failed/timeout 并返回明确结果结构"
  - "不提前实现 generate() 宿主最终接入（CONT-03 仍保留到 Phase 5）"
---

# Phase 4: 逻辑编排 - Plan

本阶段聚焦“工作流编排层”，将 Phase 2 参数处理与 Phase 3 API 客户端组合成可稳定调用的任务状态机。  
`generate(context)` 仍保持 Phase 5 决策，不在本阶段提前落地宿主最终接入。

## Wave 1: 编排核心链路

<task>
<name>建立编排结果模型与统一状态收敛</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/ROADMAP.md
- .planning/REQUIREMENTS.md
- .planning/phases/03-api-client/03-PLAN.md
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
在 `main.py` 新增状态收敛函数 `_normalize_terminal_status(status, error=None)`，将运行链路终态统一映射为 `completed`、`failed`、`timeout`。新增 `_build_orchestration_result(...)` 返回标准结构：`task_id`、`status`、`output_path`、`video_url`、`error`、`meta`。若异常来自 `PluginFatalError` 保留前缀；其他异常统一包装为 `PluginFatalError` 再输出。
</action>
<verify>
grep "def _normalize_terminal_status" video_plugin_zlhub_seedance/main.py
grep "def _build_orchestration_result" video_plugin_zlhub_seedance/main.py
grep "\"status\":" video_plugin_zlhub_seedance/main.py
grep "\"output_path\":" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 存在 `_normalize_terminal_status` 且返回值仅来自 `completed|failed|timeout`。
- 存在 `_build_orchestration_result` 且结果字段包含 `task_id/status/output_path/video_url/error/meta`。
- 异常归一化逻辑明确区分 `PluginFatalError` 与其他异常。
</acceptance_criteria>
<done>终端状态和返回结构统一，为编排入口提供稳定协议</done>
</task>

<task>
<name>实现端到端编排函数（ORCH-01）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/04-orchestration/04-PLAN.md
- .planning/phases/03-api-client/03-VERIFICATION.md
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
新增 `_run_seedance_orchestration(context)`（或同等命名），输入 `context` 后严格执行：`_sanitize_params -> _build_create_payload -> _create_task -> _poll_task_status -> _download_video`。从 `context` 提取 `prompt`、`reference_images`、`output_dir`、`viewer_index`、`progress_callback`，输出路径固定为 `{output_dir}/{viewer_index:04d}_seedance_{timestamp}.mp4`。在每个关键节点调用 `progress_callback`：`参数校验完成`、`任务已创建`、`状态轮询中`、`下载中`、`完成/失败`。
</action>
<verify>
grep "def _run_seedance_orchestration" video_plugin_zlhub_seedance/main.py
grep "_sanitize_params(" video_plugin_zlhub_seedance/main.py
grep "_create_task(" video_plugin_zlhub_seedance/main.py
grep "_poll_task_status(" video_plugin_zlhub_seedance/main.py
grep "_download_video(" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 编排函数存在且链路顺序与计划一致。
- 结果路径生成逻辑包含 `viewer_index` 与时间戳，后缀为 `.mp4`。
- 至少 5 个关键节点触发进度回调（含完成/失败节点）。
</acceptance_criteria>
<done>端到端编排函数可单次调用完成完整生命周期</done>
</task>

<task>
<name>实现轮询策略参数边界与超时收敛（ORCH-02）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- docs/require/zlhub-seedance2.0-video-api.md
- .planning/REQUIREMENTS.md
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
新增 `_normalize_polling_config(params)`，明确 `timeout`、`max_poll_attempts`、`poll_interval` 的整数化和最小边界（建议：`timeout>=30`、`max_poll_attempts>=1`、`poll_interval>=1`）。在编排入口中统一调用此函数并下发给 `_create_task/_poll_task_status/_download_video`。当轮询超过最大次数时，编排结果状态必须映射为 `timeout`，并在 `error` 字段写入 `PLUGIN_ERROR:::` 前缀消息。
</action>
<verify>
grep "def _normalize_polling_config" video_plugin_zlhub_seedance/main.py
grep "max_poll_attempts" video_plugin_zlhub_seedance/main.py
grep "poll_interval" video_plugin_zlhub_seedance/main.py
grep "\"timeout\"" video_plugin_zlhub_seedance/main.py
grep "timeout" video_plugin_zlhub_seedance/main.py | grep "_normalize_terminal_status"
</verify>
<acceptance_criteria>
- 存在 `_normalize_polling_config` 且显式处理三项轮询配置的类型与下界。
- 编排函数使用归一化后的轮询配置，而不是直接读原始参数。
- 轮询超限时结果状态为 `timeout`，并返回带 `PLUGIN_ERROR:::` 的错误文本。
</acceptance_criteria>
<done>轮询策略可配置且超时行为可预测</done>
</task>

<task>
<name>终端状态到插件结果映射（ORCH-03）</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- .planning/phases/04-orchestration/04-PLAN.md
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
新增 `_map_orchestration_to_plugin_output(result)`，将 `completed` 映射为 `[output_path]`，`failed/timeout` 抛 `PluginFatalError(result["error"])`。新增 `run_seedance_workflow(context)` 封装调用 `_run_seedance_orchestration` + 映射函数，作为 Phase 4 的对外编排入口；保留 `run_seedance_client` 兼容，不删除。
</action>
<verify>
grep "def _map_orchestration_to_plugin_output" video_plugin_zlhub_seedance/main.py
grep "def run_seedance_workflow" video_plugin_zlhub_seedance/main.py
grep "return \\[output_path\\]" video_plugin_zlhub_seedance/main.py
grep "PluginFatalError(result\\[\"error\"\\])" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- 成功状态返回 `list[str]` 形式的本地视频路径。
- 失败与超时状态统一抛 `PluginFatalError`，无裸 `Exception` 向外泄漏。
- `run_seedance_workflow` 存在且可作为 Phase 5 `generate()` 直接调用目标。
</acceptance_criteria>
<done>终态映射完成，编排层对外协议稳定</done>
</task>

<task>
<name>最小编排 smoke 验证与文档注记</name>
<files>
- video_plugin_zlhub_seedance/main.py
</files>
<read_first>
- video_plugin_zlhub_seedance/main.py
</read_first>
<action>
扩展 `__main__` smoke 检查，新增 `run_seedance_workflow`、`_run_seedance_orchestration`、`_normalize_polling_config`、`_map_orchestration_to_plugin_output` 的 callable 断言。更新 `generate(context)` docstring，明确“Phase 4 已完成编排函数，Phase 5 仅做宿主入口接线和 UI/日志集成”。
</action>
<verify>
grep "run_seedance_workflow" video_plugin_zlhub_seedance/main.py
grep "_run_seedance_orchestration" video_plugin_zlhub_seedance/main.py
grep "_normalize_polling_config" video_plugin_zlhub_seedance/main.py
grep "_map_orchestration_to_plugin_output" video_plugin_zlhub_seedance/main.py
grep "Phase 4" video_plugin_zlhub_seedance/main.py
</verify>
<acceptance_criteria>
- `__main__` smoke 检查覆盖新增编排函数。
- `generate()` 注释明确阶段边界，避免 Phase 4/5 责任重叠。
</acceptance_criteria>
<done>编排阶段产物可快速自检且边界清晰</done>
</task>

## Verification

### Automated Checks
- `python -m py_compile video_plugin_zlhub_seedance/main.py`
- `python -c "import importlib.util as iu; p=r'F:\\Projects\\zz-video-plugins\\video_plugin_zlhub_seedance\\main.py'; s=iu.spec_from_file_location('m', p); m=iu.module_from_spec(s); s.loader.exec_module(m); print(all(callable(getattr(m,n,None)) for n in ['_run_seedance_orchestration','_normalize_polling_config','_map_orchestration_to_plugin_output','run_seedance_workflow']))"`

### Manual Verification
- 用 mock `progress_callback` 调用 `run_seedance_workflow`（伪造客户端返回）确认回调顺序与状态映射。
- 人工确认成功场景返回 `[output_path]`，失败/超时场景抛 `PLUGIN_ERROR:::` 前缀错误。
