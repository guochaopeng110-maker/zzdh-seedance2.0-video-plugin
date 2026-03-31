# Phase 2: 参数处理 - Research

## 1. 分辨率与宽高比映射 (PARA-01)

根据 `docs/require/zlhub-seedance2.0-video-api.md`，Seedance 2.0 API 对分辨率和宽高比有严格的物理像素映射要求。

### 映射数据结构建议
建议使用嵌套字典结构，以 `resolution` 为外层键，`ratio` 为内层键：

```python
RESOLUTION_RATIO_MAP = {
    "480p": {
        "16:9": (864, 496),
        "4:3": (752, 560),
        "1:1": (640, 640),
        "3:4": (560, 752),
        "9:16": (496, 864),
        "21:9": (992, 432),
    },
    "720p": {
        "16:9": (1280, 720),
        "4:3": (1112, 834),
        "1:1": (960, 960),
        "3:4": (834, 1112),
        "9:16": (720, 1280),
        "21:9": (1470, 630),
    }
}
```

- **Adaptive 处理**: 文档提到 `ratio="adaptive"` 会由服务端自动处理，因此在本地映射时，如果 `ratio` 为 `adaptive`，不应强制映射物理像素，或者在构建 payload 时特殊处理。

## 2. 时长边界处理 (PARA-02)

### 约束规则
- 有效范围：`[4, 15]` 秒。
- 智能时长：`-1`。

### 处理逻辑
- 输入为 `-1`：保留 `-1` 透传。
- 输入 < 4：静默修正为 4。
- 输入 > 15：静默修正为 15。
- 默认值：`5`。

参考 `video_plugin_zzdhapi/main.py` 的 `_normalize_duration` 模式，但在本项目中应采用“截断”而非“回退到默认值”的策略。

## 3. 图像物理约束校验 (PARA-03)

### 校验项
- **格式**: `jpeg`, `png`, `webp`, `bmp`, `tiff`, `gif`。
- **大小**: 单张 `< 30 MB`。

### 实现建议
- 使用 `os.path.getsize()` 检查大小。
- 检查文件扩展名，或使用 `imghdr` / `PIL` 检查文件头。
- 几何约束（边长、宽高比）已决定交给服务端处理，本地不实现复杂逻辑。

## 4. 音频开关映射

### 映射规则
- 输入：`"true"`, `"false"`, `"1"`, `"0"`, `"enabled"`, `"disabled"` 等。
- 输出：布尔值 `True` / `False`。

参考 `video_plugin_zzdhapi/main.py` 的 `_normalize_audio_generation`，但返回值应改为 Python 原生布尔值。

## 5. 错误处理模式

### 异常类
- 统一使用 `PluginFatalError`，定义在 `main.py` 中。
- 错误消息必须带 `PLUGIN_ERROR:::` 前缀。

### 快速失败
- 参数校验（如图片路径不存在、格式不支持、大小超限）应立即抛出异常，阻止任务创建。

## 6. 参考实现模式 (Pattern Check)

### _normalize_* 函数族
建议在 `main.py` 中实现以下函数：
- `_normalize_resolution(res, model_config)`
- `_normalize_aspect_ratio(ratio, model_config)`
- `_normalize_duration(duration)`
- `_normalize_audio_generation(value)`
- `_validate_image_constraints(path)`

### _sanitize_params
作为统一的入口，清洗所有来自宿主或配置文件的参数，确保它们符合 API 要求。

## RESEARCH COMPLETE
What do I need to know to PLAN this phase well?
1. 明确了分辨率与比例的精确映射表。
2. 确定了时长的截断修正逻辑。
3. 锁定了图像校验的最小集（格式+大小）。
4. 统一了错误报告和异常处理的风格。

*Phase: 02-para-process*
*Date: 2026-03-31*
