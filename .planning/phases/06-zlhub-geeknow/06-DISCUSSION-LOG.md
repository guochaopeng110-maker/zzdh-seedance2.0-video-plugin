# Phase 6: zlhub-geeknow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 06-zlhub-geeknow
**Areas discussed:** 日志格式契约, 实时日志界面, 任务日志界面, 后端动作与存储

---

## 日志格式契约

| Option | Description | Selected |
|--------|-------------|----------|
| 对齐 geeknow-logs 字段与输出顺序（Recommended） | 降低联调成本，方便复用现有日志阅读与排障习惯 | ✓ |
| 仅部分对齐，保留 zlhub 自定义字段 | 迁移成本更低，但验收口径会分叉 | |
| 完全重做新日志格式 | 灵活但与参考实现脱节，风险最高 | |

**User's choice:** [auto] 对齐 geeknow-logs 字段与输出顺序。
**Notes:** 用户已明确要求“日志格式与字段对齐 geeknow-logs.txt”。

---

## 实时日志界面

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 geeknow live_log 交互（Recommended） | 自动滚动、清空、2 秒轮询、状态提示，低风险快速落地 | ✓ |
| 精简为只读滚动文本 | 实现简单，但可用性下降 | |
| 增加高级筛选与搜索 | 体验更强，但超出当前阶段范围 | |

**User's choice:** [auto] 复用 geeknow live_log 交互。
**Notes:** 保持与参考插件一致，优先联调效率。

---

## 任务日志界面

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 geeknow task_log 表格能力（Recommended） | 支持筛选、勾选、批量下载、结果反馈，覆盖核心运维需求 | ✓ |
| 仅显示只读任务列表 | 成本低，但无法手动补下载 | |
| 引入分页与多维过滤 | 功能强但阶段内性价比低 | |

**User's choice:** [auto] 复用 geeknow task_log 表格能力。
**Notes:** 保留“只允许可下载任务被勾选”的保护逻辑。

---

## 后端动作与存储

| Option | Description | Selected |
|--------|-------------|----------|
| 增加与 geeknow 同构 action + SQLite（Recommended） | UI 与后端契约清晰，可直接映射前端动作 | ✓ |
| 仅内存日志，不持久化任务 | 开发快，但重启后丢失任务历史 | |
| 新建独立 RPC 层 | 可扩展性高，但复杂度超阶段目标 | |

**User's choice:** [auto] 增加同构 action 与 SQLite 任务日志存储。
**Notes:** 不改动现有 generate 主链路，仅增强调试与日志能力。

## the agent's Discretion

- 日志缓存上限与清理策略。
- 表格字段截断长度与 UI 文案细节。

## Deferred Ideas

- 任务日志导出（CSV/JSON）
- 高级检索与全文过滤
- 远程日志上报
