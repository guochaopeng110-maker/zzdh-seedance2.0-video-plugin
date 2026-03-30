# 规范 - 代码风格

## 代码风格
- 函数和变量使用 **snake_case** (蛇形命名法)
- 类名使用 **PascalCase** (大驼峰命名法): `PluginFatalError`, `_BufferingHandler`
- 常量使用 **UPPER_CASE** (大写命名法): `DEFAULT_MODEL`, `AUDIO_ENABLED`
- 面向用户的逻辑使用中文注释和文档字符串
- 技术实现细节使用英文

## 函数命名
- `_normalize_*` - 参数规范化/校验
- `_build_*` - 请求 Payload 构建
- `_get_*` - 配置查询
- `_extract_*` - 响应解析
- `_poll_*` - 状态轮询
- `_download_*` - 视频下载

## 错误处理
- 自定义异常类: `PluginFatalError`
- UI 错误前缀: `PLUGIN_ERROR:::`
- 通过 `print()` 进行优雅降级并输出警告
- 带有可配置尝试次数的重试逻辑

## 模式规范
```python
# 参数规范化
def _normalize_duration(duration_value, model_config):
    # 带有回退到默认值的校验逻辑

# 模型配置查询
def _get_model_config(model_value):
    normalized_model = MODEL_ALIASES.get(model_value, model_value)
    return MODEL_CONFIGS.get(normalized_model, MODEL_CONFIGS[DEFAULT_MODEL])

# 带有回调的 Payload 构建
def _build_request_payload(..., progress_callback):
    if progress_callback:
        progress_callback("准备首帧图片")
```

## 日志
- ZZDH: 使用 `print()` 输出
- GeekNow: 自定义 `logging` 模块，带有缓冲处理器
- 日志中的敏感数据脱敏（API 密钥、Base64 图像）
