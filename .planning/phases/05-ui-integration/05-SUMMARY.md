---
phase: 05-ui-integration
plan: 01
subsystem: host-integration
tags: [generate, error-prefix, progress-callback, logging, ui]
requires:
  - phase: 04-orchestration
    provides: run_seedance_workflow / orchestration result mapping
provides:
  - generate(context) 宿主入口接线
  - 统一错误前缀输出
  - 宿主进度回调桥接
  - 生命周期日志打点
  - UI 参数与后端模型一致性
affects: [host-runtime, user-feedback, observability]
tech-stack:
  added: []
  patterns: [_log_event, _safe_progress_callback, PluginFatalError]
key-files:
  created: []
  modified: [video_plugin_zlhub_seedance/main.py, video_plugin_zlhub_seedance/ui/index.html]
key-decisions:
  - "generate 只做入口接线和错误边界，不复制编排逻辑"
  - "日志默认输出控制台 JSON，便于宿主与调试工具采集"
  - "UI 补齐轮询与重试参数，避免后端默认值漂移"
patterns-established:
  - "所有宿主可见错误统一为 PluginFatalError 前缀格式"
  - "进度回调无传入时自动降级 noop，保证流程安全"
requirements-completed: [ERR-01, ERR-02, ERR-03, CONT-03]
duration: 30 min
completed: 2026-04-02
---

# Phase 5 Plan 01: UI 与集成 Summary

**最终宿主入口已接线，错误、进度与日志可观测能力已落地。**

## Accomplishments

- 实现 `generate(context)`，直接调用 `run_seedance_workflow(context)`。
- 增加 `generate` 异常边界：非 `PluginFatalError` 统一包装为 `PluginFatalError`。
- 新增 `_log_event` 与 `_mask_api_key`，在创建/轮询/下载/成功/失败节点输出日志。
- 新增 `_safe_progress_callback`，保障无回调时流程可安全执行。
- UI 新增并持久化：`base_url`、`max_poll_attempts`、`poll_interval`、`retry_count`。
- `PluginSDK.onReady` 回填扩展字段，避免参数丢失。

## Validation Snapshot

- `python -m py_compile video_plugin_zlhub_seedance/main.py` 通过。
- `python video_plugin_zlhub_seedance/main.py` 输出 `smoke check passed`。
- 生成入口 mock 测试通过：成功场景返回路径列表，异常场景返回 `PLUGIN_ERROR:::` 前缀错误。

## Deviations from Plan

- 暂未完成真实宿主端联调（需在 `字字动画.exe` 环境人工确认进度 UI 与日志展示）。

## Self-Check: PASSED (Code-Level)
