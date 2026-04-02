---
phase: 06-zlhub-geeknow
plan: 01
subsystem: plugin-observability
tags: [logs, ui, sqlite, manual-download, action-routing]
requires:
  - phase: 05-ui-integration
    provides: run_seedance_workflow / generate entrypoint
provides:
  - 实时日志窗口（live_log.html）
  - 任务日志窗口（task_log.html）
  - 插件动作路由（open/get/download）
  - 任务日志 SQLite 持久化
  - 日志字段契约对齐 geeknow-logs.txt
affects: [debuggability, host-ops, observability]
tech-stack:
  added: [sqlite3 stdlib, collections.deque stdlib, threading stdlib]
  patterns: [handle_action bridge, dual-log-layer]
key-files:
  created: [video_plugin_zlhub_seedance/ui/live_log.html, video_plugin_zlhub_seedance/ui/task_log.html, video_plugin_zlhub_seedance/video_task_logs.db]
  modified: [video_plugin_zlhub_seedance/main.py, video_plugin_zlhub_seedance/ui/index.html]
key-decisions:
  - "日志格式与字段对齐 docs/require/geeknow-logs.txt"
  - "实时日志使用 index/time/level/msg 增量拉取协议"
  - "任务日志使用 SQLite 持久化并支持手动下载"
patterns-established:
  - "UI 通过 PluginSDK.sendAction 与 handle_action 通道交互"
  - "实时日志内存缓冲 + 任务日志持久化双层模型"
requirements-completed: []
duration: 45 min
completed: 2026-04-02
---

# Phase 6 Plan 01: 实时日志与任务日志界面 - Summary

**phase 6 的日志可观测性能力已落地：zlhub 插件现在具备实时日志页面、任务日志页面、手动下载链路与后端动作路由。**

## Accomplishments

- `main.py` 新增实时日志缓冲（`deque + lock`）与 `get_buffered_logs`。
- `main.py` 新增任务日志 SQLite（`video_task_logs.db`）及增改查函数。
- `main.py` 新增 `handle_action`，支持：
  - `open_live_logs`
  - `open_task_logs`
  - `get_logs`
  - `get_task_logs`
  - `download_videos`
- `_run_seedance_orchestration` 集成任务日志状态更新（running/success/failed/download_failed）。
- 新增 `ui/live_log.html`：2 秒轮询、自动滚动、清空功能。
- 新增 `ui/task_log.html`：状态筛选、批量勾选、批量下载、结果反馈。
- 更新 `ui/index.html`：增加“任务日志 / 手动拉取”“实时日志”入口按钮并发送动作。

## Validation Snapshot

- `python -m py_compile video_plugin_zlhub_seedance/main.py` 通过。
- 模块级 smoke：`handle_action('open_live_logs/open_task_logs/get_logs/get_task_logs')` 返回 `ok=true`。
- 实时日志字段检查通过：条目含 `index/time/level/msg`。
- 页面动作关键字检查通过：
  - `live_log.html` 含 `get_logs` 增量轮询
  - `task_log.html` 含 `get_task_logs/download_videos`
  - `index.html` 含 `open_live_logs/open_task_logs` 按钮绑定

## Deviations from Plan

- `task_log.html` 直接复用了 geeknow 参考页面结构（同构迁移），未做视觉层重设计。
- `requirements` 字段仍为空（ROADMAP Phase 6 当前为 TBD），待后续补齐 REQ-ID 映射后可追加。

## Self-Check: PASSED
