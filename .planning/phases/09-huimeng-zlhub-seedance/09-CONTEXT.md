# Phase 9: Huimeng 视频生成插件对接（参考 zlhub seedance 机制） - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

在不修改字字动画宿主程序的前提下，新增一个可被宿主直接加载的视频插件目录，用于对接 Huimeng 平台视频异步任务接口（创建任务/轮询状态/下载结果），并保持与现有 Seedance 系列插件同级的参数处理、错误封装、进度回调与日志能力。

</domain>

<decisions>
## Implementation Decisions

### 插件契约与结构
- **D-01:** 新插件保持与现有视频插件一致的宿主契约：实现 `get_info()`、`get_params()`、`generate(context)`，并提供 `ui/index.html` 配置界面。
- **D-02:** 新插件目录名称固定为 `video_plugin_huimeng_seedance`，并采用与 `video_plugin_zlhub_seedance` 相同的主文件组织方式（以 `main.py` 为核心承载 API、参数、编排、日志逻辑），优先减少宿主侧联调风险。

### Huimeng API 编排
- **D-03:** 采用异步任务主链路：`POST /api/v1/tasks` 创建任务，`GET /api/v1/tasks/{task_id}` 轮询状态，`status=completed` 后从 `result.video_url` 下载产物。
- **D-04:** 鉴权使用 `Authorization: Bearer hm-...`，并延续统一致命错误前缀 `PLUGIN_ERROR:::` 对宿主输出。
- **D-05:** 默认采用轮询模式完成闭环，`webhook_url` 先作为可选扩展参数保留，不作为首版必选依赖。

### 参数映射与媒体输入
- **D-06:** 界面上必须支持以下 5 种模型 ID 的显式可选项：`happyhorse-1.0`、`seedance-2.0-value`、`seedance-2.0-fast-value`、`seedance-2.0`、`seedance-2.0-fast`。
- **D-07:** 模型参数按模型差异映射：
  - `happyhorse-1.0` 支持 `prompt`、`ratio`、`duration`、`resolution`、`reference_images`，不传 `human_review`、`reference_videos`、`reference_audios`。
  - `seedance-2.0-value`、`seedance-2.0-fast-value`、`seedance-2.0`、`seedance-2.0-fast` 支持 `prompt`、`ratio`、`duration`、`resolution`、`generate_audio`、`human_review`，并兼容 `reference_images/reference_videos/reference_audios`。
- **D-07.1:** 不同模型下 `params` 字段（尤其 `ratio`、`resolution`，以及相关可选字段）的可选值必须严格遵循 `docs/require4/视频模型的params参数说明.md`，禁止跨模型复用不兼容枚举值。
- **D-08:** Huimeng 文档明确图片/视频/音频参数仅支持公网 URL，因此本插件沿用“本地文件先上传中转图床再回填 URL”的策略（参考文档给出的 `imageproxy.zhongzhuan.chat` 上传示例）。
- **D-09:** 参数合法性延续现有插件策略：时长边界、比例白名单、分辨率白名单、参考素材数量/大小约束在本地先校验，失败时直接返回标准错误。

### 可观测性与宿主体验
- **D-10:** 延续任务日志与运行时日志机制，保留任务状态演进、task_id、失败原因、下载路径等关键字段，便于插件内排障和宿主联调。
- **D-11:** 保持进度回调语义（参数校验中/任务已创建/轮询中/下载中/完成/失败），确保宿主 UI 可持续反馈。

### the agent's Discretion
- 轮询间隔、最大轮询次数、初始等待时长的默认值可根据 Huimeng 实测稳定性微调。
- 在不影响首版稳定性的前提下，可按模型差异补充可选参数（如 `scene_optimize`、`return_last_frame`）的 UI 暴露策略。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Huimeng 接口契约
- `docs/require4/huimeng-image-video-api.md` - Huimeng 认证方式、任务创建/查询接口、状态流转、结果字段与 Webhook 机制。

### 视频模型参数约束
- `docs/require4/视频模型的params参数说明.md` - Seedance/HappyHorse 模型 params 字段定义、默认值、可选值与多模态参考输入约束。

### 对标实现（插件机制）
- `video_plugin_zlhub_seedance/main.py` - 现有成熟插件的宿主入口契约、参数归一化、异步编排、统一错误封装、进度回调与日志体系。
- `video_plugin_zlhub_seedance/ui/index.html` - 现有配置界面字段组织与宿主配置交互方式。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `video_plugin_zlhub_seedance/main.py` 内部已形成可复用模式：参数清洗、任务创建/轮询/下载、统一错误封装、日志落盘、任务日志数据库。
- `video_plugin_zlhub_seedance/ui/index.html` 可直接复用 UI 字段布局与宿主配置回填方式。

### Established Patterns
- 插件以单文件 `main.py` 聚合核心能力（非多模块拆分），便于宿主加载和部署。
- 统一使用 `PLUGIN_ERROR:::` 前缀做可展示错误。
- 采用“异步任务 + 轮询 + 下载”标准链路，且通过 `progress_callback` 对宿主持续回报状态。

### Integration Points
- 新插件需要对接宿主已有上下文输入：`prompt`、`reference_images/videos/audios`、`output_dir/output_path`、`progress_callback`。
- 新插件输出需继续符合宿主预期：成功返回本地视频路径数组，失败抛出标准前缀异常。

</code_context>

<specifics>
## Specific Ideas

- 本期目标是“Huimeng 视频生成插件对接”，优先确保与现有插件同等稳定性和可维护性，再考虑扩展到更多 Huimeng 模型细节。
- 以 `video_plugin_zlhub_seedance` 作为机制参考而不是字面复制，重点替换 API 契约和参数映射。

</specifics>

<deferred>
## Deferred Ideas

- 基于 Webhook 的无轮询模式（可作为后续优化阶段）。
- Huimeng 图像模型统一接入（当前 Phase 9 聚焦视频生成链路）。
- 多平台抽象层（统一封装 Huimeng/ZLHub/TDUHub 的 provider 适配器）。

</deferred>

---

*Phase: 09-huimeng-zlhub-seedance*
*Context gathered: 2026-05-26*
