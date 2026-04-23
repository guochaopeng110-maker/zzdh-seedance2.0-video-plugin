# Phase 8: 适配ZLHub新版视频任务与素材审核接口（requires2） - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

在不改变宿主调用契约（`get_info/get_params/generate`）的前提下，将 `video_plugin_zlhub_seedance` 从旧版 ZLHub 任务接口与旧版素材审核链路迁移到 requires2 定义的新接口：
1. 视频任务创建与查询切换到 `https://api.zlhub.cn/v1/task/create` 与 `https://api.zlhub.cn/v1/task/get/{id}`。
2. 素材审核切换到 `https://asset.zlhub.cn` 的 Header Token 鉴权模型，取消 AES-ECB。
3. 审核输入仅接受公网 URL，不再接受 Base64。
4. 支持审核异步结果获取（查询或 callback）并与视频生成编排打通。

</domain>

<decisions>
## Implementation Decisions

### 视频任务接口迁移
- **D-01:** `base_url` 从旧地址改为固定新建任务地址 `https://api.zlhub.cn/v1/task/create`，并同步更新 UI 默认值。
- **D-02:** 任务查询不再使用 `base_url + /{task_id}` 拼接；改为独立查询根 `https://api.zlhub.cn/v1/task/get/{id}`。
- **D-03:** 请求鉴权继续使用 `Authorization: Bearer <API_KEY>`，但增加可选 `X-Trace-ID`（每次请求唯一），用于排障追踪。

### 素材审核协议重构
- **D-04:** 移除 `AuditAESCipher`、固定 AES key、`encrypted_data` 请求体方案；改用标准 Header Token 鉴权调用 `asset.zlhub.cn`。
- **D-05:** 审核请求统一传 `images: [http/https URL]`；若输入为本地文件或 `data:` Base64，直接报错并提示先上传公网存储。
- **D-06:** 审核返回以 `items[].downstream_asset_id` 为主，统一转换为 `asset://<id>` 供视频生成 `content.*_url.url` 使用。

### 审核异步策略
- **D-07:** 以异步提交为主路径（`POST /api/asset/upload/async`），通过 `GET /api/task/{task_id}` 轮询；保留 callback_url 透传能力。
- **D-08:** 审核轮询默认间隔按文档建议使用 3 秒级别，并设置超时兜底；超时时给出明确可重试错误。

### 错误与可观测性
- **D-09:** 对外错误前缀维持 `PLUGIN_ERROR:::` 不变；新增 trace-id、audit task id、video task id 的结构化日志字段。
- **D-10:** `audit_test_only` 模式保留，但行为调整为“仅走新审核链路，不触发视频创建”，用于联调验证。

### the agent's Discretion
- Trace-ID 生成细节（UUIDv4 或 32 位随机串）由实现阶段选择，但必须保证请求级唯一。
- 审核查询状态枚举与重试策略的内部映射（running/completed/failed）可在计划阶段细化。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase / Scope Definition
- `.planning/ROADMAP.md` — Phase 8 scope, dependency, and planning target.
- `.planning/REQUIREMENTS.md` — existing plugin contract and non-goals boundary.

### New API Contracts (requires2)
- `docs/requre2/视频生成接口.md` — new create/query endpoints, auth header, trace-id, and content requirements.
- `docs/requre2/素材审核接口.md` — new audit domain, sync/async semantics, query endpoint, callback rules, and response schema.

### Legacy Contracts (for migration diff)
- `docs/require/zlhub-seedance2.0-video-api.md` — legacy video API assumptions currently embedded in plugin.
- `docs/require/zlhub-seedance-check-picture-api.md` — legacy AES-based audit contract to be removed.

### Current Implementation Anchors
- `video_plugin_zlhub_seedance/main.py` — current orchestration, API calls, and audit pipeline.
- `video_plugin_zlhub_seedance/ui/index.html` — current configurable endpoint defaults and audit-related UI params.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `video_plugin_zlhub_seedance/main.py` 已有完整任务编排骨架：参数清洗、任务创建、轮询、下载、日志、任务库记录，可复用。
- `_build_auth_headers`, `_poll_task_status`, `_build_orchestration_result` 可在保留行为一致性的前提下扩展新接口。

### Established Patterns
- 插件保持统一错误包装：`PluginFatalError` + `PLUGIN_ERROR:::`。
- 运行时日志与任务日志已打通（`_log_event` + sqlite task log），适合承载 trace-id/audit-task-id。
- UI 参数通过 `get_params` 与 `ui/index.html` 对齐，变更需双端同步。

### Integration Points
- 视频创建入口：`_create_task`（当前使用旧 base_url）。
- 视频状态查询入口：`_poll_task_status`（当前用旧拼接路径）。
- 素材审核入口：`_call_material_audit_api`（当前 AES + base64，需整体替换）。
- 审核触发与编排耦合点：`_run_seedance_orchestration` 中 `video_style == 仿真人风格` 分支。

</code_context>

<specifics>
## Specific Ideas

- 本阶段默认采用“审核异步主路径 + 查询兜底 + callback透传”的实现，避免长阻塞同步审核造成插件超时。
- 任务创建与任务查询应显式拆分为两个 URL 配置（创建 URL / 查询 URL），避免旧逻辑隐式拼接再次引入协议耦合。
- 旧日志中出现大量旧域名请求记录，应在迁移后通过关键字回归验证（禁止再出现 `zlhub.xiaowaiyou.cn/.../tasks`）。

</specifics>

<deferred>
## Deferred Ideas

- 审核 callback 的签名校验与重放防护（若平台后续补充签名协议）可作为后续增强阶段。
- 更细粒度的审核并发调度（批次拆分、并发窗口）暂不纳入本阶段。

Reviewed Todos (not folded):
- 无（`todo match-phase 8` 返回空）。

</deferred>

---

*Phase: 08-zlhub-requires2*
*Context gathered: 2026-04-23*
