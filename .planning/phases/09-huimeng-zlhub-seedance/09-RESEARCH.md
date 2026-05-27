# Phase 09 Research: Huimeng 视频生成插件对接

## Scope
- 新增插件目录：`video_plugin_huimeng_seedance`
- 延续宿主契约：`get_info()` / `get_params()` / `generate(context)` / `ui/index.html`
- 主链路：创建任务 -> 轮询状态 -> 下载视频

## Canonical Inputs
- `docs/require4/huimeng-image-video-api.md`
- `docs/require4/视频模型的params参数说明.md`
- `video_plugin_zlhub_seedance/main.py`
- `video_plugin_zlhub_seedance/ui/index.html`

## Key Findings

### 1. API 协议
- 鉴权：`Authorization: Bearer hm-...`
- 创建：`POST /api/v1/tasks`
- 查询：`GET /api/v1/tasks/{task_id}`
- 完成结果：`result.video_url`
- 状态流转：`pending` -> `processing` -> `completed` / `failed`

### 2. 输入素材约束
- 图片/视频/音频参数仅支持公网 URL。
- 本地参考图需先上传再回填 URL（文档给出 `imageproxy.zhongzhuan.chat` 示例）。

### 3. 模型与参数差异
- UI 必须支持 5 个模型：
  - `happyhorse-1.0`
  - `seedance-2.0-value`
  - `seedance-2.0-fast-value`
  - `seedance-2.0`
  - `seedance-2.0-fast`
- `happyhorse-1.0` 不传：`human_review`、`reference_videos`、`reference_audios`。
- 不同模型下 `ratio`、`resolution` 等可选值必须严格按 `视频模型的params参数说明.md`。

### 4. 参考实现复用点
- `video_plugin_zlhub_seedance/main.py` 已具备成熟模式：
  - 参数归一化与合法性校验
  - 异步任务编排（创建/轮询/下载）
  - 错误前缀 `PLUGIN_ERROR:::`
  - 进度回调与日志机制

## Risks & Mitigations
- 风险：跨模型误用枚举值导致 API 400。
  - 对策：按模型维度维护独立枚举映射并在本地前置校验。
- 风险：本地素材未转公网 URL 导致任务失败。
  - 对策：统一素材 URL 预处理层；上传失败立即中断并返回标准错误。
- 风险：直接迁移 zlhub 字段造成 payload 不兼容。
  - 对策：建立 Huimeng 专属 payload builder，并对照文档字段白名单。

## Validation Architecture
- 静态验证：`python -m py_compile`
- 结构验证：`rg` 校验模型列表、模型差异字段、接口路径、错误前缀
- 行为验证：smoke check 调用主流程函数，确保创建/轮询/下载路径可达
