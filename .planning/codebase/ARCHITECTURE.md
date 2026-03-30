# 架构 - 设计模式

## 整体架构
- **基于插件的架构**，用于视频生成服务
- 两个独立的插件共享通用的模式
- 同步 API 调用配合异步状态轮询

## 设计模式

### 1. 模型配置模式 (Model Configuration Pattern)
两个插件都使用特定于模型的配置字典：
- `MODEL_CONFIGS` (ZZDH) / `_MODEL_DISPLAY_MAP` + `_MODEL_INFO` (GeekNow)
- 每个模型包含：分辨率、时长、生成模式、音频选项

### 2. 参数清洗 (Parameter Sanitization)
- `_sanitize_params()` / `_preprocess_params()` - 规范化并校验用户参数
- 对无效值回退到默认值
- 特定于模型的校验

### 3. 请求构建器模式 (Request Builder Pattern)
- 针对不同模型类型使用独立的 Payload 构建器：
  - `_build_standard_payload()` - 通用模型处理器
  - `_build_kling_payload()` - 可灵 (Kling) 专用
  - `_build_vidu_payload()` - Vidu 专用
  - `_build_doubao_payload()` - 豆包 (Doubao) (使用 multipart/form-data)
  - `_build_hailuo_payload()` - 海螺 (Hailuo) (使用 JSON)

### 4. 轮询模式 (Polling Pattern)
- 具有可配置间隔的状态轮询循环
- 支持进度回调以进行 UI 更新
- 带有重试逻辑的错误处理

### 5. 任务日志 (GeekNow)
- 基于 SQLite 的任务历史记录
- 状态追踪：运行中 → 成功/失败/下载失败
- 错误关键字过滤以辅助重试决策

## 数据流
1. `generate(context)` 接收提示词、参考图、插件参数
2. 参数清洗和模型配置查询
3. 根据模型类型构建请求 Payload
4. 发送 POST 请求到视频 API → 获取 task_id
5. 轮询状态接口直到任务完成
6. 从 URL 下载视频
7. 以带时间戳的文件名保存到输出目录

## 抽象
- `plugin_utils` - 共享的配置加载/保存工具
- `progress_callback` - UI 进度更新
- 面向用户的错误使用 `PLUGIN_ERROR:::` 前缀
