
# Phase 1: 基础构建 - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary
本阶段的目标是建立 `video_plugin_zlhub_seedance` 插件的基础结构。这包括创建必要的目录、初始化 `main.py` 入口文件，并实现宿主程序（字字动画.exe）加载插件所需的元数据函数 `get_info()` 和 `get_params()`。

本阶段不涉及实际的 API 调用逻辑（阶段 3）或复杂的参数验证（阶段 2），但需要预留好相关的配置结构。
</domain>

<decisions>
## Implementation Decisions

### 插件标识与元数据
- **插件名称**: ZLHub Seedance 视频生成
- **插件描述**: 对接 ZLHub 中转平台的 Seedance 2.0 视频大模型接口。
- **版本**: 1.0.0
- **作者**: Z Code (Powered by Zhipu AI)

### 核心函数实现
- `get_info()`: 必须返回包含 `name`, `description`, `version`, `author` 的字典。
- `get_params()`: 
  - 必须包含 `api_key` (默认为空字符串)。
  - 必须包含 `base_url` (默认为 ZLHub 的标准地址)。
  - 必须包含模型配置相关的默认参数（如分辨率、比例等）。
  - 遵循 `video_plugin_zzdhapi` 的模式，实现 `_sanitize_params` 和配置持久化。

### 目录结构 (CONT-04)
- 根目录: `video_plugin_zlhub_seedance/`
- 入口文件: `video_plugin_zlhub_seedance/main.py`

### Claude's Discretion
- 参照 `video_plugin_zzdhapi/main.py` 的代码结构，因为其结构较为清晰且模块化程度高。
- 预定义 `MODEL_CONFIGS` 常量，为后续阶段的模型能力映射打下基础。
</decisions>

<canonical_refs>
## Canonical References
- `video_plugin_zzdhapi/main.py` — 核心参考实现（模型配置模式、参数清洗逻辑）。
- `.planning/PROJECT.md` — 项目核心价值和约束。
- `.planning/REQUIREMENTS.md` — 阶段 1 对应的 CONT-01, CONT-02, CONT-04 需求。
</canonical_refs>

<deferred>
## Deferred Ideas
- `generate()` 函数的具体实现 -> 阶段 5。
- 详细的 API 错误映射 (PLUGIN_ERROR:::) -> 阶段 5。
- 复杂的图像约束验证 (PARA-03) -> 阶段 2。
</deferred>

---
*Phase: 01-base-build*
*Context gathered: 2026-03-31*
