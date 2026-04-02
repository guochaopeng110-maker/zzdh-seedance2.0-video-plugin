---
phase: 03-api-client
plan: 01
subsystem: api-client
tags: [seedance, zlhub, api, polling, download]
requires:
  - phase: 02-para-process
    provides: 参数清洗、约束校验与统一错误前缀
provides:
  - Seedance 任务创建接口封装
  - 任务状态轮询与状态归一化
  - 直链下载 + content 回退下载
  - 单入口客户端执行函数 run_seedance_client
affects: [orchestration, ui-integration]
tech-stack:
  added: [requests]
  patterns: [_build_*, _poll_*, _download_*, PluginFatalError, PLUGIN_ERROR:::]
key-files:
  created: []
  modified: [video_plugin_zlhub_seedance/main.py]
key-decisions:
  - "任务状态统一映射为 running/completed/failed/unknown，避免上层处理分叉"
  - "下载优先 video_url，失败后自动回退 /v1/videos/{task_id}/content"
  - "仅纯文本模式 + web_search=true 时注入 tools.web_search"
patterns-established:
  - "API 客户端入口固定为 run_seedance_client，便于 Phase 4 编排调用"
  - "统一鉴权头构建函数 _build_auth_headers，减少重复请求代码"
requirements-completed: [API-01, API-02, API-03, API-04]
duration: 40 min
completed: 2026-04-02
---

# Phase 3 Plan 01: API 客户端 Summary

**ZLHub Seedance 2.0 客户端核心链路已落地：创建任务、状态轮询、产物下载均可通过单入口函数调用。**

## Accomplishments

- 增加网络与序列化依赖：`requests`、`json`、`base64`、`time`、`datetime`。
- 实现统一鉴权请求头：`_build_auth_headers`，并在 `api_key` 为空时抛 `PluginFatalError`。
- 实现 `content` 构建与创建任务：`_build_content_items`、`_build_create_payload`、`_create_task`。
- 实现状态轮询：`_normalize_task_status`、`_extract_video_url_from_status`、`_poll_task_status`。
- 实现下载回退：`_download_video` 先直链后 `/v1/videos/{task_id}/content`。
- 交付外部入口：`run_seedance_client(...)`，串联创建、轮询、下载并返回结构化结果。
- 增加 `__main__` smoke check，保证关键函数可调用。

## Files Modified

- `video_plugin_zlhub_seedance/main.py` - 增加 API 客户端完整执行链路与辅助函数。

## Validation Snapshot

- `python -m py_compile video_plugin_zlhub_seedance/main.py` 通过。
- 函数存在性检查通过：`_create_task`、`_poll_task_status`、`_download_video`、`run_seedance_client`。
- `python video_plugin_zlhub_seedance/main.py` 输出 `smoke check passed`。

## Deviations from Plan

- 未进行真实网络集成调用（缺少可直接使用的在线 API 凭据与可控测试任务）；已通过 `03-VERIFICATION.md` 标记为人工验证项。

## Next Phase Readiness

- Phase 4 可直接复用 `run_seedance_client` 作为端到端编排核心调用点。
- 已具备 ORCH 阶段需要的状态与下载回退基础能力。

## Self-Check: PASSED (Code-Level)
