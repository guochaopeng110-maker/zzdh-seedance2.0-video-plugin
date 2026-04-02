# Phase 6: zlhub-geeknow - Research

**Researched:** 2026-04-02
**Domain:** Python plugin observability UI (live log + task log)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 日志格式与字段必须对齐 `docs/require/geeknow-logs.txt`。
- 实时日志沿用 `index/time/level/msg` 条目契约。
- 任务日志支持筛选、批量选择与手动下载。
- 后端动作路由需覆盖 `open_live_logs/open_task_logs/get_logs/get_task_logs/download_videos`。
- 不改宿主程序，仅在 zlhub 插件内实现。

### the agent's Discretion
- 日志缓存上限与清理策略。
- 表格列宽、截断长度与提示文案。

### Deferred Ideas (OUT OF SCOPE)
- 日志导出（CSV/JSON）
- 高级检索（关键词/全文）
- 远程日志上报
</user_constraints>

<research_summary>
## Summary

Phase 6 的最稳妥方案是“同构迁移 geeknow 的日志能力到 zlhub 插件”，而不是重造新协议。当前 `video_plugin_geeknow` 已完整覆盖实时日志轮询、任务日志持久化、批量下载和动作分发；`video_plugin_zlhub_seedance` 已有稳定的生成主链路与 `_log_event` 基础，因此实施重点是补齐 UI 页面与 action 后端，而非改动生成流程。

标准实现路径：新增 `ui/live_log.html` + `ui/task_log.html`，在 `main.py` 增加日志缓冲与 SQLite 表，并扩展 `handle_action`。这样可直接复用宿主通信模型 (`postMessage -> plugin_action -> handle_action`) 与运维习惯，风险最低。

**Primary recommendation:** 采用“契约对齐 + 代码同构”策略，先保证日志字段与页面行为 1:1 对齐，再做最小必要适配到 zlhub 数据结构。
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `logging` | stdlib | 实时日志采集与格式化 | 无额外依赖，和现有插件一致 |
| Python `sqlite3` | stdlib | 任务日志持久化 | 轻量、可移植、已被 geeknow 验证 |
| `requests` | existing | 手动下载视频 | 已在插件链路内使用，行为稳定 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `threading.Lock` | stdlib | 日志缓冲并发安全 | 多线程/回调并发写日志时 |
| `collections.deque` | stdlib | 有界实时日志缓存 | 需要控制内存上限时 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sqlite3 本地 DB | JSON 文件 | JSON 简单但筛选/并发/更新性能差 |
| 轮询日志 | 流式 WebSocket | 宿主契约不需要 websocket，复杂度高 |

**Installation:**
```bash
# No new packages required for Phase 6
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
video_plugin_zlhub_seedance/
├─ main.py                # action 路由 + 日志缓存 + 任务日志 DB
└─ ui/
   ├─ index.html          # 新增日志入口按钮
   ├─ live_log.html       # 实时日志窗口
   └─ task_log.html       # 任务日志与手动下载
```

### Pattern 1: Action-Driven UI Bridge
**What:** 统一通过 `handle_action(action, data)` 处理 UI 请求。
**When to use:** 宿主通过 `postMessage` 转发动作到插件时。

### Pattern 2: Dual Log Layer
**What:** 实时日志使用内存缓冲，任务日志使用 SQLite 持久化。
**When to use:** 同时需要“正在发生什么”与“历史追溯”能力时。

### Anti-Patterns to Avoid
- 在 `generate(context)` 中混入 UI/数据库逻辑，导致主链路耦合。
- 定义与 geeknow 不兼容的日志字段名，增加联调成本。
- 无限增长日志缓存，造成长期运行内存膨胀。
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 任务日志检索 | 手写复杂内存索引 | SQLite 条件查询 | SQLite 过滤、排序、更新更可靠 |
| UI 通信协议 | 自定义新通道 | 复用现有 `plugin_action` 协议 | 宿主已支持且被 geeknow 验证 |
| 日志存储轮转 | 自研压缩轮转系统 | 有界缓冲 + 按需清理 | 当前阶段仅需可调试与可追溯 |

**Key insight:** 该阶段是“能力对齐”而不是“架构创新”，复用既有稳定模式优先。
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: 字段命名漂移
**What goes wrong:** UI 读取 `entry.message` 但后端写 `msg`，页面空白。
**How to avoid:** 明确实时日志字段固定为 `index/time/level/msg`。

### Pitfall 2: 任务状态语义不一致
**What goes wrong:** 后端写 `completed`，前端仅识别 `success`，badge 错乱。
**How to avoid:** 统一状态映射表并在 UI 端做兼容映射。

### Pitfall 3: 下载入口对无 URL 任务开放
**What goes wrong:** 批量下载大量失败，影响用户感知。
**How to avoid:** 仅允许有 `video_url` 的任务被勾选下载。
</common_pitfalls>

<code_examples>
## Code Examples

### 日志动作模型（参考）
- `video_plugin_geeknow/main.py`: `handle_action('get_logs')`
- `video_plugin_geeknow/ui/live_log.html`: 2 秒轮询 `get_logs`

### 任务日志模型（参考）
- `video_plugin_geeknow/main.py`: `handle_action('get_task_logs')` + SQLite
- `video_plugin_geeknow/ui/task_log.html`: 状态筛选 + 批量下载

### 目标接入点
- `video_plugin_zlhub_seedance/main.py`: 扩展 action 路由，不改主工作流函数职责边界
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

该问题域无明显新范式变化；对桌面插件而言，局部 UI + 本地日志持久化仍是主流低风险方案。关键不是“技术新”，而是“契约稳定 + 排障效率”。
</sota_updates>

<open_questions>
## Open Questions

1. **任务日志字段最小集合是否需要完全复制 geeknow 全字段？**
   - Recommendation: 先保证关键字段（任务标识、状态、错误、输出路径、URL），其余按需增补。

2. **实时日志是否需要磁盘落地副本？**
   - Recommendation: 本阶段保留控制台+内存缓冲；若后续有审计需求再扩展文件落地。
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `docs/require/geeknow-logs.txt` - 日志字段与示例基线
- `video_plugin_geeknow/main.py` - 参考实现（动作路由/日志缓冲/任务日志/下载）
- `video_plugin_geeknow/ui/live_log.html` - 实时日志 UI 行为
- `video_plugin_geeknow/ui/task_log.html` - 任务日志 UI 行为
- `video_plugin_zlhub_seedance/main.py` - 目标插件集成点

### Secondary (MEDIUM confidence)
- `video_plugin_geeknow/ui/index.html` - 日志入口触发模式
- `video_plugin_zlhub_seedance/ui/index.html` - 当前配置 UI 结构
</sources>

<metadata>
## Metadata

**Research scope:** 插件日志可观测性、UI 通信、任务日志持久化、下载链路

**Confidence breakdown:**
- Stack: HIGH
- Architecture: HIGH
- Pitfalls: HIGH
- Integration feasibility: HIGH

**Research date:** 2026-04-02
**Valid until:** 2026-05-02
</metadata>

---

*Phase: 06-zlhub-geeknow*
*Research completed: 2026-04-02*
*Ready for planning: yes*
