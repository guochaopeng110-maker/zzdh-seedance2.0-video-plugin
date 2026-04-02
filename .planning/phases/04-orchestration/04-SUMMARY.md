---
phase: 04-orchestration
plan: 01
subsystem: orchestration
tags: [workflow, state-machine, polling, error-mapping]
requires:
  - phase: 03-api-client
    provides: API 创建/轮询/下载原子函数
provides:
  - 端到端编排函数 _run_seedance_orchestration
  - 轮询配置归一化 _normalize_polling_config
  - 终态收敛与结果协议标准化
  - 插件输出映射 run_seedance_workflow
affects: [phase-5-generate, host-integration]
tech-stack:
  added: []
  patterns: [_run_*, _normalize_*, _map_*, PluginFatalError]
key-files:
  created: []
  modified: [video_plugin_zlhub_seedance/main.py]
key-decisions:
  - "run_seedance_client 保持兼容，内部改为调用新编排函数"
  - "轮询超限收敛为 timeout，避免 unknown 状态外泄"
  - "编排层返回标准 result dict，插件层再映射到 list 输出"
patterns-established:
  - "编排入口返回结构化结果，便于 Phase 5 做宿主接线与日志扩展"
requirements-completed: [ORCH-01, ORCH-02, ORCH-03]
duration: 35 min
completed: 2026-04-02
---

# Phase 4 Plan 01: 逻辑编排 Summary

**端到端状态机已落地，参数→创建→轮询→下载链路可通过单入口函数稳定执行。**

## Accomplishments

- 新增 `_normalize_polling_config`，统一 `timeout/max_poll_attempts/poll_interval` 下界与类型。
- 新增 `_normalize_terminal_status` 与 `_build_orchestration_result`，统一终态与错误协议。
- 新增 `_run_seedance_orchestration(context)`，按固定顺序执行完整生命周期并回调进度。
- 新增 `_map_orchestration_to_plugin_output` 与 `run_seedance_workflow(context)`。
- `run_seedance_client` 变为兼容封装，内部走新编排流程。
- 修复下载落盘目录为空时的 `os.makedirs` 风险。
- 扩展 `__main__` smoke 检查覆盖 Phase 4 新函数。

## Validation Snapshot

- `python -m py_compile video_plugin_zlhub_seedance/main.py` 通过。
- `python video_plugin_zlhub_seedance/main.py` 输出 `smoke check passed`。
- mock 编排测试通过：创建→轮询→下载调用顺序正确，结果可映射为插件输出列表。

## Deviations from Plan

- 未在本阶段接入 `generate(context)` 到宿主入口，保持 Phase 5 边界不变。

## Next Phase Readiness

- Phase 5 可直接在 `generate(context)` 中调用 `run_seedance_workflow(context)` 完成宿主接线。

## Self-Check: PASSED
