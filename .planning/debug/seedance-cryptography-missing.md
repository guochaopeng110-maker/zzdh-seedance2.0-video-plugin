# seedance-cryptography-missing

## Symptoms
- 在字字动画里执行 `video_plugin_zlhub_seedance` 的 `generate` 后失败。
- 错误：`PLUGIN_ERROR:::素材审核依赖缺失: cryptography 未安装或不可用`

## Investigation
- 错误由 `video_plugin_zlhub_seedance/main.py` 的 `AuditAESCipher.__init__` 抛出。
- 素材审核流程会调用 AES-256-ECB-PKCS7，加密依赖 `cryptography`。
- 当前仓库环境 `D:\Anaconda\python.exe` 已安装 `cryptography`，说明缺失发生在“宿主字字动画的 Python 运行时”，而非仓库解释器。

## Root Cause
- 插件运行时的 Python 环境缺少 `cryptography`，导致素材审核初始化失败并中断工作流。

## Fix Applied
- 在 `video_plugin_zlhub_seedance/main.py` 增加运行时依赖诊断：
  - 报错中输出可直接执行的安装命令（绑定实际 `sys.executable`）。
  - `module.loaded` 日志输出运行时 Python 路径和 `cryptography` 可用性/版本。
  - 当依赖缺失时写入 `cryptography.unavailable` 提示行（含安装命令）。

## Validation
- `python -m py_compile video_plugin_zlhub_seedance/main.py` 通过。
- `python video_plugin_zlhub_seedance/main.py` 输出 `smoke check passed`。

## Next Action
1. 将修复后的插件目录重新复制到字字动画插件目录。
2. 启动字字动画并触发一次插件加载，查看插件目录中的 `debug_runtime.log`。
3. 执行日志中 `install_hint` 对应命令安装依赖，再次重试 `generate`。
