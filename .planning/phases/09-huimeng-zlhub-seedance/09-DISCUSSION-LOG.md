# Phase 9: Huimeng 视频生成插件对接（参考 zlhub seedance 机制） - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md.

**Date:** 2026-05-26
**Phase:** 09-huimeng-zlhub-seedance
**Areas discussed:** 插件契约与结构, Huimeng API 编排, 参数映射与媒体输入, 可观测性

---

## 插件契约与结构

| Option | Description | Selected |
|--------|-------------|----------|
| 延续现有宿主契约与目录结构 | 复用 get_info/get_params/generate + ui 页面模式，最小化宿主联调风险 | ✓ |
| 重新设计插件契约 | 需要宿主配合改造，风险高 | |

**User's choice:** 延续现有宿主契约与目录结构（基于“参考 zlhub seedance 机制”）
**Notes:** 现有多个插件目录均已稳定运行，优先一致性。

---

## Huimeng API 编排

| Option | Description | Selected |
|--------|-------------|----------|
| 异步任务+轮询+下载 | 对齐 Huimeng 文档主流程，插件内可闭环 | ✓ |
| 仅 Webhook 回调 | 依赖外部回调服务，不适合首版 | |

**User's choice:** 异步任务+轮询+下载
**Notes:** 首版以宿主内闭环为主，Webhook 作为后续增强。

---

## 参数映射与媒体输入

| Option | Description | Selected |
|--------|-------------|----------|
| 兼容 Seedance 核心参数并增加 URL 上传转换 | 保持使用习惯一致，满足 Huimeng 仅公网 URL 的输入约束 | ✓ |
| 仅暴露最小参数集 | 实现更快，但会降低与现有插件的一致性 | |

**User's choice:** 兼容 Seedance 核心参数并增加 URL 上传转换
**Notes:** 文档已给出图片上传公网 URL 示例，可直接纳入实现。

---

## 可观测性

| Option | Description | Selected |
|--------|-------------|----------|
| 延续任务日志 + 运行时日志 + progress_callback | 与既有插件运维和联调方式一致 | ✓ |
| 仅保留基础打印 | 信息不足，排障成本高 | |

**User's choice:** 延续任务日志 + 运行时日志 + progress_callback
**Notes:** 与现有插件口径保持同级。

## the agent's Discretion

- 轮询参数默认值按 Huimeng 实测调优。
- 首版 UI 暴露字段范围在不增加复杂度前提下取平衡。

## Deferred Ideas

- Webhook 回调签名校验链路（后续阶段）
- 图像模型统一接入（后续阶段）
