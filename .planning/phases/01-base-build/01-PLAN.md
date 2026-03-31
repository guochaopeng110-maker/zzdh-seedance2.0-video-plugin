
# Phase 1: 基础构建 - Plan

**Wave 1: 目录与基础骨架**

- **Task 01: 创建插件目录结构**
  - `<read_first>`: `.planning/PROJECT.md`
  - `<action>`: 创建目录 `video_plugin_zlhub_seedance/`。
  - `<acceptance_criteria>`: `ls -d video_plugin_zlhub_seedance/` 返回成功。

- **Task 02: 初始化 main.py 并实现元数据函数**
  - `<read_first>`: `video_plugin_zzdhapi/main.py`
  - `<action>`: 在 `video_plugin_zlhub_seedance/main.py` 中实现：
    - 导入必要的库 (json, os, sys, requests 等)。
    - 实现 `get_info()` 函数。
    - 定义初始的 `_default_params` 和 `MODEL_CONFIGS`。
    - 实现基础的 `_sanitize_params` 和 `get_params()` 逻辑。
  - `<acceptance_criteria>`: 
    - `video_plugin_zlhub_seedance/main.py` 文件存在。
    - 代码中包含 `def get_info():` 和 `def get_params():`。
    - `get_info()` 返回的字典包含 "ZLHub Seedance" 关键字。

**Wave 2: 验证与校准**

- **Task 03: 验证宿主加载契约**
  - `<read_first>`: `video_plugin_zlhub_seedance/main.py`
  - `<action>`: 使用 Python 交互模式或脚本尝试调用 `get_info()` 和 `get_params()`，确保无语法错误且返回预期结构。
  - `<acceptance_criteria>`: 脚本 `python -c "from video_plugin_zlhub_seedance.main import get_info; print(get_info())"` 执行无报错且输出正确。

## Verification Criteria
- [ ] 目录 `video_plugin_zlhub_seedance` 已创建。
- [ ] `main.py` 包含符合宿主要求的 `get_info` 函数。
- [ ] `main.py` 包含 `get_params` 函数，能够处理默认配置。
- [ ] `get_info().name` 为 "ZLHub Seedance 视频生成"。

## Must Haves
- `video_plugin_zlhub_seedance/main.py` 必须能够被导入而不产生 ImportError (除了预期的共享工具类)。
