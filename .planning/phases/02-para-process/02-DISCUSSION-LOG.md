# Phase 2: 参数处理 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 02-para-process
**Areas discussed:** 分辨率/比例映射、时长边界处理、图像校验策略、音频开关、错误处理、轮询策略、参数持久化

---

## 分辨率/比例映射

| Option | Description | Selected |
|--------|-------------|----------|
| 严格像素映射 | 实现本地映射表，将 resolution + ratio 组合映射到具体物理像素值 | ✓ |
| 透传参数 | 直接将 480p/720p 等字符串传给 API，让 ZLHub 服务端解析 | |

**User's choice:** 严格像素映射

**Notes:** 用户确认分辨率按照像素映射，与 video_plugin_zzdhapi 的 MODEL_CONFIGS 模式一致。

---

## 时长边界处理

| Option | Description | Selected |
|--------|-------------|----------|
| 严格校验 | 超出 [4, 15] 范围的输入直接回退到默认值 5 | |
| 支持智能时长 | 允许传入 -1，其他越界值采用截断策略（静默修正） | ✓ |

**User's choice:** 支持智能时长 + 截断策略

**Notes:** 用户确认时长边界最长为 15s，支持 -1 智能时长。

---

## 图像校验策略

| Option | Description | Selected |
|--------|-------------|----------|
| 严格校验 | 本地检查所有约束（格式、大小、边长、宽高比），不满足则报错 | |
| 宽松校验 | 仅检查文件格式和文件大小 <30MB，其他交给服务端 | ✓ |
| 自动修正 | 尝试压缩/裁剪图片以满足约束，失败后再报错 | |

**User's choice:** 宽松校验（选项 A）

**Notes:** 用户确认宽松校验仅检查文件格式和文件大小 <30MB。

---

## 音频开关

| Option | Description | Selected |
|--------|-------------|----------|
| 布尔值 | 直接使用 true/false，无需封装 | ✓ |
| 常量封装 | 使用 AUDIO_ENABLED/AUDIO_DISABLED 常量 | |

**User's choice:** 布尔值

**Notes:** 用户确认音频开关为布尔值即可。

---

## 错误处理

| Option | Description | Selected |
|--------|-------------|----------|
| 抛出异常 | 参数校验失败时抛出 PLUGIN_ERROR::: 前缀的异常 | ✓ |
| 静默处理 | 仅打印警告并回退到默认值 | |

**User's choice:** 抛出异常（选项 A）

**Notes:** 与阶段 5 统一错误格式，便于宿主程序识别。

---

## 轮询策略

| Option | Description | Selected |
|--------|-------------|----------|
| 固定间隔 | 保持默认 5 秒间隔，300 次轮询上限 | ✓ |
| 动态间隔 | 前 2 分钟每 3 秒轮询，之后每 10 秒轮询 | |
| 长间隔 | 固定 10 秒间隔，180 次轮询上限（30 分钟） | |

**User's choice:** 固定间隔（选项 A）

**Notes:** 与现有插件保持一致，简单可控。

---

## 参数持久化策略

| Option | Description | Selected |
|--------|-------------|----------|
| 变化时持久化 | 仅在参数变化时持久化（减少磁盘 I/O） | ✓ |
| 每次都持久化 | 每次调用 get_params() 都持久化 | |

**User's choice:** 变化时持久化（选项 A）

**Notes:** Phase 1 实现已足够，减少磁盘 I/O。

---

## Claude's Discretion

以下领域用户授权 Claude 自行决定：
- 映射表的具体实现结构（可使用字典或独立常量）
- 图像校验工具函数的命名和模块化方式
- 时长截断时是否打印警告日志（建议打印，便于调试）

---

## Deferred Ideas

- API 客户端实现（任务创建、状态轮询、视频下载）— 阶段 3
- `generate()` 主流程编排 — 阶段 5
- 详细的 API 错误映射 — 阶段 5
- 高级重试策略（如指数退避）— v2 需求（OPS-02）
- SQLite 任务历史数据库 — v2 需求（OPS-02）
