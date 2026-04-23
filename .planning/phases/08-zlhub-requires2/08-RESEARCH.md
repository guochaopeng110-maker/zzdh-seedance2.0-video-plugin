# Phase 8: zlhub-requires2 - Research

**Researched:** 2026-04-23
**Domain:** ZLHub requires2 video task API + material audit API migration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- V2 插件目录固定为 `video_plugin_zlhub_seedance_V2`，原插件目录不做兼容分支改造。
- 视频任务创建/查询切换到 `https://api.zlhub.cn/v1/task/create` 与 `https://api.zlhub.cn/v1/task/get/{id}`。
- 素材审核切换到 `https://asset.zlhub.cn` Header Token 鉴权，移除 AES-ECB。
- 审核输入只接受公网 URL，不接受 Base64/本地路径。
- 审核结果使用 `items[].downstream_asset_id` 转 `asset://<id>` 回填视频 payload。
- 对外错误前缀继续统一为 `PLUGIN_ERROR:::`。

### the agent's Discretion
- trace-id/track-id 的具体生成方式（UUID4 hex 或随机 32 位）
- 审核轮询超时阈值与失败重试细节

### Deferred Ideas (OUT OF SCOPE)
- callback 签名校验与重放防护
- 审核任务并发窗口优化
</user_constraints>

<research_summary>
## Summary

Phase 8 的最低风险路径是“复制现有插件为 V2 + 协议替换”，而不是在原目录做双协议兼容。已有 `video_plugin_zlhub_seedance/main.py` 具备完整编排、轮询、日志、任务记录能力，可复用执行框架；需要替换的是请求协议层（视频 endpoint 与审核 endpoint/鉴权/输入格式）。

关键迁移点：
1. 视频创建与查询 endpoint 必须拆分，不再依赖 `base_url + /{task_id}`。
2. 视频请求头新增 `X-Trace-ID`，每次请求唯一。
3. 审核链路改为 `X-Access-Token` + `X-Track-Id` + `POST /api/asset/upload/async` + `GET /api/task/{task_id}`。
4. 审核输入强制 URL 化，提前在插件侧快速失败，避免送审后才报错。
5. 审核结果消费以 `downstream_asset_id` 为准，统一转 `asset://` 后进入内容构建。

**Primary recommendation:** 一次性在 V2 目录完成“协议硬切换”，禁止旧协议分支，降低维护成本与状态分叉风险。
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | existing | 视频/审核 HTTP 调用 | 项目已在用，避免新增依赖 |
| `uuid` | stdlib | 生成 trace-id / track-id | 满足 32 位唯一标识要求 |
| `json` | stdlib | 请求与响应解析 | 当前链路已使用 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlite3` | stdlib | 任务日志与元数据落盘 | 保留既有可观测性 |
| `threading` + `deque` | stdlib | 实时日志缓冲 | 保持日志 UI 行为稳定 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Header Token 审核 | 保留 AES 适配层 | 与 requires2 冲突，增加死代码 |
| 异步审核 | 同步 `/upload/sync` | 宿主链路更易阻塞，吞吐差 |
| 软兼容旧 URL | 双端点自动切换 | 状态复杂、排障困难 |
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
video_plugin_zlhub_seedance_V2/
├─ main.py
├─ ui/
│  ├─ index.html
│  ├─ live_log.html
│  └─ task_log.html
└─ logs/ (runtime)
```

### Pattern 1: Endpoint Split + Explicit Config
**What:** 分离 `task_create_url` 与 `task_query_url`，不依赖字符串拼接推导。
**When to use:** 创建与查询地址不同且可能独立演进时。

### Pattern 2: Async Audit Pipeline
**What:** 审核先提交异步任务，再轮询查询；完成后转换 asset id。
**When to use:** 审核返回可能超 60 秒或批次处理时。

### Pattern 3: Early Input Rejection
**What:** 在插件侧直接拒绝 Base64/本地文件输入。
**When to use:** 上游接口明确限制 URL-only 时，减少无效请求。

### Anti-Patterns to Avoid
- 在 V2 中保留 `AuditAESCipher` 兼容分支。
- 审核失败时返回空数组继续生成任务（会放大故障）。
- 使用旧 `base_url` 拼接任务查询路径。
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 审核加密协议 | 自研 AES 封装 | 官方 Header Token 协议 | 已明确废弃 AES |
| 状态机二次封装 | 新建复杂中间状态层 | 复用现有 orchestration + 状态映射 | 降低改造面 |
| 追踪ID格式 | 自定义短ID格式 | 32 位 hex UUID | 文档有明确格式约束 |
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: 审核提交成功但未轮询查询
**What goes wrong:** 仅拿到 `202` 即当作通过，后续 payload 无 asset id。
**How to avoid:** 强制 `completed` 才消费 `result.items`。

### Pitfall 2: 混用大小写 `Asset://` 与 `asset://`
**What goes wrong:** 下游对协议前缀严格匹配时失效。
**How to avoid:** 统一输出小写 `asset://<downstream_asset_id>`。

### Pitfall 3: Trace/Track ID 复用
**What goes wrong:** 排障定位串线，平台侧难以关联失败请求。
**How to avoid:** 每次 HTTP 请求都生成新 32 位 ID。
</common_pitfalls>

<code_examples>
## Code Examples

### 视频接口参考
- `docs/requre2/视频生成接口.md`：
  - `POST https://api.zlhub.cn/v1/task/create`
  - `GET https://api.zlhub.cn/v1/task/get/{id}`
  - Header: `Authorization`, `Content-Type`, `X-Trace-ID`

### 审核接口参考
- `docs/requre2/素材审核接口.md`：
  - `POST https://asset.zlhub.cn/api/asset/upload/async`
  - `GET https://asset.zlhub.cn/api/task/{task_id}`
  - Header: `X-Access-Token`, `X-Track-Id`, `Content-Type`
  - Result: `result.items[].downstream_asset_id`

### 当前集成锚点
- `video_plugin_zlhub_seedance/main.py`：`_create_task`、`_poll_task_status`、`_call_material_audit_api`、`_run_seedance_orchestration`
</code_examples>

<open_questions>
## Open Questions

1. 审核 `callback_url` 是否默认开启？
- Recommendation: 字段保留为可选，默认空值，仅当用户配置时透传。

2. 审核失败 item 是否允许部分通过继续生成？
- Recommendation: 仅当所有提交素材都 `submit_review_status=1` 时继续，避免部分素材丢失导致生成质量不稳定。
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `docs/requre2/视频生成接口.md`
- `docs/requre2/素材审核接口.md`
- `docs/requre2/相对于之前的主要变化点.md`
- `.planning/phases/08-zlhub-requires2/08-CONTEXT.md`
- `video_plugin_zlhub_seedance/main.py`
- `video_plugin_zlhub_seedance/ui/index.html`

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
</sources>

<metadata>
## Metadata

**Research scope:** requires2 协议迁移、鉴权头切换、异步审核策略、现有编排复用可行性

**Confidence breakdown:**
- Stack: HIGH
- API mapping: HIGH
- Migration risk: MEDIUM-HIGH
- Integration feasibility: HIGH

**Research date:** 2026-04-23
**Valid until:** 2026-05-23
</metadata>

---

*Phase: 08-zlhub-requires2*
*Research completed: 2026-04-23*
*Ready for planning: yes*
