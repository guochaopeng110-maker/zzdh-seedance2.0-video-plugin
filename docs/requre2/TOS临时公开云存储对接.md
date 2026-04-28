# TOS临时公开云存储对接

## **1. 基础信息**

本接口基于火山引擎 TOS 实现素材上传功能，返回的资源 **URL 有效期为 7 天**。

### **接口域名**

```
zlhub-asset-outside.tos-cn-beijing.volces.com
```

### **核心配置**

在正式调用接口前，请在代码配置项中填写以下固定配置：

| 配置项 | 必填 | 说明 |
| --- | --- | --- |
| `AK` | 是 | 找对接技术提供 |
| `SK` | 是 | 找对接技术提供 |
| `REGION` | 是 | 地域，当前为 `cn-beijing` |
| `BUCKET` | 是 | 存储桶名称，当前为 `zlhub-asset-outside` |
| `ENDPOINT` | 是 | 访问节点，当前为 `tos-cn-beijing.volces.com` |

> 💡 **提示**：为保障安全，请勿将 AK/SK 提交至公共代码仓库。建议通过环境变量或配置文件动态加载密钥信息。

---

## **2. Python 调用示例代码**

您可以直接复制以下完整的 Python 代码作为业务集成的参考。代码中已包含必要的 AK/SK 配置，所有素材将默认存储在云端的 `images/` 目录下，并自动使用 UUID 生成唯一文件名。

```
import os
import uuid
import tos

# ================= 核心配置 =================
AK = ""
SK = ""
ENDPOINT = "tos-cn-beijing.volces.com"
REGION = "cn-beijing"
BUCKET = "zlhub-asset-outside"
# ============================================

def upload_image_to_tos(local_file_path):
    """上传本地文件到 TOS 并返回公网访问链接"""

    # 1. 初始化 TOS 客户端
    client = tos.TosClientV2(AK, SK, ENDPOINT, REGION)

    # 2. 生成云端存储路径 (固定在 images/ 目录下)
    ext = os.path.splitext(local_file_path)[1].lower()
    object_key = f"images/{uuid.uuid4().hex}{ext}"

    # 3. 执行上传
    with open(local_file_path, "rb") as f:
        client.put_object(BUCKET, object_key, content=f)

    # 4. 拼接并返回最终访问的 URL
    return f"https://{BUCKET}.{ENDPOINT}/{object_key}"

if __name__ == "__main__":
    # 指定本地待上传的文件路径（请替换为真实的本地路径）
    file_path = "C:\\Users\\Downloads\\sample.png"

    if os.path.exists(file_path):
        print(f"开始上传文件: {file_path} ...")
        try:
            result_url = upload_image_to_tos(file_path)
            print(f"✅ 上传成功!")
            print(f"🔗 访问链接: {result_url}")
        except Exception as e:
            print(f"❌ 上传失败: {e}")
            print("请参考下方报错码进行排查。")
    else:
        print(f"❌ 找不到文件: {file_path}")
```

---

## **3. 常见报错码参考**

若上传失败，请根据控制台输出的 `code` 或 `ec` 字段进行对应排查。如无法解决，可将完整的 `request_id` 提供给管理员协助处理：

| 错误特征码 (code / ec) | 状态说明 |
| --- | --- |
| `AccessDenied` / `0003-00000012` | 访问被拒绝 |
| `InvalidAccessKeyId` | 访问密钥无效 |
| `NoSuchBucket` | 指定的存储桶不存在 |
| `SignatureDoesNotMatch` | 请求签名不匹配 |
| `ConnectionError` | 网络连接失败 |

> 💡 **提示**：遇到报错时，请优先核对 AK/SK 及基础配置是否正确填写。