# 实施计划: 07 — 素材审核集成

## 目标
为 `video_plugin_zlhub_seedance` 插件集成基于 AES 加密的素材审核接口，确保在生成“仿真人风格”视频时，参考图片通过安全合规检测并转换为 `Asset://` 资源。

## 详细任务

### 1. 技术底座 (Main.py)
- [ ] **加解密工具类实现**:
    - 引入 `cryptography` 库中的 `Cipher`, `algorithms`, `modes`, `padding`。
    - 实现 `AuditAESCipher` 类，提供基于 AES-256-ECB-PKCS7 的加解密方法。
- [ ] **素材审核客户端实现**:
    - 实现 `_call_material_audit_api` 函数。
    - 处理请求构造（JSON 加密、Base64 编码）及响应解析（解密、错误处理）。
- [ ] **参数规范化更新**:
    - 更新 `_build_default_params` 和 `_sanitize_params` 以包含 `video_style`, `audit_user_id`, `audit_aes_key`。
    - 确保 `video_style` 默认为 `其他风格`。

### 2. 逻辑编排 (Main.py)
- [ ] **重构编排器 `_run_seedance_orchestration`**:
    - 在创建视频任务前，检查触发条件：`video_style == "仿真人风格"` 且 `reference_images` 不为空。
    - 如果触发，调用审核接口并将本地路径/Base64 替换为返回的 `Asset://` 链接。
    - 将审核状态记录到实时日志和任务日志的 `metadata` 中。
- [ ] **兼容性增强**:
    - 确保 `_build_content_items` 能够识别并直接使用 `Asset://` 前缀的 URL。

### 3. UI 界面 (index.html)
- [ ] **新增配置项**:
    - 在 API Key 下方新增 `Audit User ID` 和 `Audit AES Key` (password 隐藏)。
    - 在 Model/分辨率 下方新增 `视频风格` (仿真人风格/其他风格) 下拉框。
- [ ] **参数同步逻辑**:
    - 更新 `onReady` 钩子，回显保存的审核参数。
    - 更新 `change` 事件监听器，实时保存新增参数。

### 4. 验证与联调
- [ ] **验证**: 通过单元测试（如 `pytest` 或脚本）验证 AES 加密结果是否与文档示例一致。
- [ ] **模拟模拟**: 在 `_call_material_audit_api` 失败时提供清晰的 `PLUGIN_ERROR:::` 提示。

## 成功标准
1. UI 成功保存并在重启后恢复审核参数。
2. 选择“仿真人”时，后台日志显示触发了素材审核。
3. 视频生成任务载荷中的参考图 URL 变为 `Asset://` 格式。
4. 插件在非人像风格下保持原有逻辑，不触发额外 API 调用。
