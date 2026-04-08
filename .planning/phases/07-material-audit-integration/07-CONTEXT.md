# 阶段上下文: 07 — 素材审核集成

## 目标
为 `video_plugin_zlhub_seedance` 插件集成素材审核功能，确保在生成“仿真人风格”视频时，参考图片通过合规性检测并转换为 `Asset://` 资源。

## 关键决策

### 1. 安全信息存储 (Audit Credentials)
*   **方案**: 采用 UI 输入模式。
*   **实现**: 在 `index.html` 中新增 `audit_user_id` (数字) 和 `audit_aes_key` (64 字符 hex) 输入框。
*   **逻辑**: 参数将持久化至插件配置文件，并在运行时由 `main.py` 读取。

### 2. 技术栈
*   **库选择**: 使用环境中已有的 `cryptography` 库实现 AES-256-ECB 加解密。
*   **对齐**: 虽然文档示例使用 `pycryptodome`，但为保持环境纯净，我们将使用 `cryptography` 实现完全一致的加密逻辑（PKCS7 填充，ECB 模式）。

### 3. 触发与执行逻辑
*   **触发条件**: `video_style == "仿真人风格"` 且 `reference_images` 不为空。
*   **处理范围**: 如果存在多张参考图片，将**全部**提交审核。
*   **流程映射**:
    1. 提取所有参考图片路径。
    2. 将图片转换为 Base64 或使用原始 URL。
    3. 调用 `moderation/image` 接口（AES 加密请求，解密响应）。
    4. 提取响应中的 `asset_url` (`Asset://...`)。
    5. 将视频生成 Payload 中的 `image_url.url` 替换为审核后的 `asset_url`。

### 4. UI 布局
*   **视频风格**: 在“Model”或“分辨率”下拉框后新增“视频风格”选择（选项：仿真人风格、其他风格）。
*   **审核配置**: 将 `Audit User ID` 和 `AES Key` 放置在 `API Key` 附近，方便用户统一配置。

## 待办事项 (Next Steps)
1. `/gsd:plan-phase 7`: 根据此上下文制定详细的实施计划。
2. 更新 `main.py`: 实现加密工具类和审核调度逻辑。
3. 更新 `index.html`: 新增相关 UI 元素及参数保存逻辑。
