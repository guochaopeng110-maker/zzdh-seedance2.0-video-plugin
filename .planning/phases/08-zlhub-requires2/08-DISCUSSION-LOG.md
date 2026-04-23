# Phase 8: 适配ZLHub新版视频任务与素材审核接口（requires2） - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md.

**Date:** 2026-04-23
**Phase:** 08-zlhub-requires2
**Mode:** discuss
**Areas discussed:** 视频任务接口迁移, 素材审核协议重构, 审核异步策略, 错误与可观测性
**User explicit constraints (2026-04-23):**
- Phase 8 采用 `video_plugin_zlhub_seedance_V2` 新目录开发（从原插件拷贝）。
- 不做新旧接口双轨兼容。
- 不兼容旧素材输入行为（不接受 Base64/旧加密协议）。

---

## 视频任务接口迁移

| Option | Description | Selected |
|--------|-------------|----------|
| 继续沿用旧地址拼接 | 保持 `.../tasks` + `/{id}` 的旧链路 | |
| 新建/查询分离（推荐） | 创建固定 `POST /v1/task/create`，查询固定 `GET /v1/task/get/{id}` | ✅ |
| 双轨兼容 | 新旧接口并存，按开关切换 | |

**User's choice:** 显式选择“新建/查询分离”，并明确禁止双轨兼容。
**Notes:** 与 requires2 文档一致，V2 仅保留新版任务接口实现。

---

## 素材审核协议重构

| Option | Description | Selected |
|--------|-------------|----------|
| 保留 AES-ECB 审核链路 | 继续 `encrypted_data` 与固定 AES key | |
| 迁移 Header Token（推荐） | 切换 `asset.zlhub.cn` 标准鉴权，移除 AES | ✅ |
| 仅替换域名 | 维持原数据格式，仅换 host | |

**User's choice:** 未显式交互，按执行模式默认采用推荐项。
**Notes:** 与新文档“取消 AES-ECB”要求一致。

---

## 素材输入与引用规范

| Option | Description | Selected |
|--------|-------------|----------|
| 接受 Base64 与 URL 混用 | 兼容旧行为 | |
| 仅接受公网 URL（推荐） | 本地/`data:` 输入先上传对象存储，再传 URL | ✅ |
| 内部自动上传 | 插件隐式上传后再审核 | |

**User's choice:** 显式选择“仅接受公网 URL”，并明确不兼容旧行为。
**Notes:** 审核通过后统一转换 `asset://<downstream_asset_id>` 供生成接口使用；V2 对 Base64/旧协议直接报错。

---

## 审核异步策略

| Option | Description | Selected |
|--------|-------------|----------|
| 同步审核优先 | 默认 `/upload/sync`，超时再降级 | |
| 异步审核优先（推荐） | 默认 `/upload/async` + `GET /api/task/{task_id}` 轮询，支持 callback | ✅ |
| 仅 callback | 不轮询，只依赖回调 | |

**User's choice:** 未显式交互，按执行模式默认采用推荐项。
**Notes:** 兼顾稳定性与可观测性，适配插件长任务场景。

---

## 错误与可观测性

| Option | Description | Selected |
|--------|-------------|----------|
| 仅保留原日志字段 | 不增加新追踪维度 | |
| 增强追踪字段（推荐） | 增加 trace-id / audit-task-id / video-task-id | ✅ |
| 新建独立审计系统 | 额外引入外部日志平台 | |

**User's choice:** 未显式交互，按执行模式默认采用推荐项。
**Notes:** 继续沿用 `PLUGIN_ERROR:::` 统一错误前缀，外部行为不破坏。

---

## the agent's Discretion

- Trace-ID 采用 UUIDv4 或随机 32 位串，具体实现由编码阶段确定。
- 审核轮询超时和重试参数在 plan-phase 细化为可验证阈值。

## Deferred Ideas

- callback 签名验签与重放保护策略。
- 审核批量并发调度优化（拆批、限流窗口）。

