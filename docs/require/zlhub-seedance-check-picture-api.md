***

# 素材审核接口(虚拟人像创建接口)

如果视频生成接口中传入的参考图片里面涉及真人/仿真人，必须先调用 虚拟人像创建接口进行创建后，得到Asset开头的资源链接，传入 `image_url.url` 参数。注意上传的图片不要侵害他人权益，否则产生法律后果自行承担。

调用该接口，大概 6s-8s 会马上返回审核结果，接口返回成功就能马上使用。

## 加密说明

本接口的业务参数通过 AES-256-ECB 对称加密传输，每个用户持有独立的加密密钥。

### 加密参数

| 参数 | 说明 |
| :--- | :--- |
| **算法** | AES |
| **密钥长度** | 256 位（32 字节） |
| **模式** | ECB |
| **填充** | PKCS7 |
| **密钥格式** | 64 字符 hex 字符串 |
| **密文编码** | base64 |

### 加密流程

1. 将业务参数组装为 JSON 字符串（UTF-8 编码）
2. 对 JSON 字符串进行 PKCS7 填充（块大小 16 字节）
3. 使用用户密钥进行 AES-256-ECB 加密
4. 将密文进行 base64 编码，作为请求体中 `encrypted_data` 的值

### 各语言加密示例

**Python**（依赖 `pycryptodome`）

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64, json

key = bytes.fromhex("your_64_char_hex_key")
plaintext = json.dumps({"images": ["https://example.com/1.jpg", "data:image/png;base64,iVBOR..."]}).encode("utf-8")
cipher = AES.new(key, AES.MODE_ECB)
encrypted_data = base64.b64encode(cipher.encrypt(pad(plaintext, AES.block_size))).decode()
```

**Java**

```java
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

byte[] key = hexStringToBytes("your_64_char_hex_key");
Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"));
String plaintext = "{\"images\":[\"https://example.com/1.jpg\",\"data:image/png;base64,iVBOR...\"]}";
String encryptedData = Base64.getEncoder().encodeToString(cipher.doFinal(plaintext.getBytes("UTF-8")));
```

**JavaScript / Node.js**（依赖 `crypto`）

```javascript
const crypto = require('crypto');

const key = Buffer.from('your_64_char_hex_key', 'hex');
const cipher = crypto.createCipheriv('aes-256-ecb', key, null);
let encrypted = cipher.update(JSON.stringify({images: ['https://example.com/1.jpg', 'data:image/png;base64,iVBOR...']}), 'utf8', 'base64');
encrypted += cipher.final('base64');
// encrypted 即为 encrypted_data
```

### 各语言解密示例

响应体中的 `encrypted_data` 字段使用相同的密钥和算法解密。

**Python**（依赖 `pycryptodome`）

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64, json

key = bytes.fromhex("your_64_char_hex_key")
ciphertext = base64.b64decode(encrypted_data)
cipher = AES.new(key, AES.MODE_ECB)
result = json.loads(unpad(cipher.decrypt(ciphertext), AES.block_size).decode("utf-8"))
```

**Java**

```java
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

byte[] key = hexStringToBytes("your_64_char_hex_key");
Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"));
byte[] decrypted = cipher.doFinal(Base64.getDecoder().decode(encryptedData));
String result = new String(decrypted, "UTF-8");
```

**JavaScript / Node.js**（依赖 `crypto`）

```javascript
const crypto = require('crypto');

const key = Buffer.from('your_64_char_hex_key', 'hex');
const decipher = crypto.createDecipheriv('aes-256-ecb', key, null);
let decrypted = decipher.update(encryptedData, 'base64', 'utf8');
decrypted += decipher.final('utf8');
const result = JSON.parse(decrypted);
```

密钥由管理员分配，请妥善保管，不要在客户端代码中硬编码或提交到版本控制。

---

## 图片素材审核接口文档

提交图片进行审核。

### 请求

* **URL：** `http://118.196.112.236:3428/api/moderation/image`
* **Content-Type:** `application/json`

### 请求体

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `user_id` | int | 是 | 用户ID |
| `encrypted_data` | string | 是 | 加密后的业务数据（base64编码），加密方式见上方「加密说明」 |

### 业务参数（加密前的 JSON）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `images` | list[string] | 是 | - | 图片列表，每项为 URL 或 base64 字符串 |

**images 字段说明：**

每项必须为以下两种格式之一：

* **URL**：以 `http://` 或 `https://` 开头，服务端会下载图片
* **Data URI**：格式为 `data:image/<图片格式>;base64,<Base64编码>`，`<图片格式>` 需小写（如 `png`、`jpg`、`jpeg`、`webp`），单张不超过 30MB

两种格式可混用，建议较小图片使用base64形式传输。

---

### 响应

请求解密成功后，所有响应（包括业务错误）均经过加密返回。HTTP 状态码统一为 200，实际业务状态码在解密后的 JSON 中。

仅在解密前的错误（参数缺失、用户不存在、密钥未配置、解密失败）返回明文 JSON。

### 响应体（解密前）

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 业务状态码 |
| `message` | string | 响应简单描述 |
| `encrypted_data` | string | 加密后的业务响应（base64编码），解密方式与请求加密相同 |

### 业务响应（解密后）

```json
{
  "review_batch_id": "review-20260321232207-d2a295d1",
  "items": [
    {
      "asset_id": "local-20260321232208-1998e81a",
      "asset_type": "Image",
      "asset_url": "Asset://Asset-20260321232209-rz5xb",
      "downstream_asset_id": "asset-20260321232209-rz5xb",
      "downstream_final_url": "https://ark-media-asset.tos-cn-beijing.volces.com/2109594849/032123220891851394.png?X-Tos-Algorithm=...",
      "source_url": "https://seedancs.tos-cn-beijing.volces.com/...",
      "submit_review_status": 1,
      "tos_url": "https://seedancs.tos-cn-beijing.volces.com/..."
    }
  ]
}
```

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `review_batch_id` | string | 本次审核批次ID |
| `items[].asset_id` | string | 本地素材ID |
| `items[].asset_type` | string | 素材类型 |
| `items[].asset_url` | string | 素材引用地址（Asset协议） |
| `items[].downstream_asset_id` | string | 下游审核系统的素材ID |
| `items[].downstream_final_url` | string | 下游审核系统生成的带签名的访问地址（有效期有限） |
| `items[].source_url` | string | 原始图片地址 |
| `items[].submit_review_status` | int | 提交审核状态，1 表示已提交 |
| `items[].tos_url` | string | 上传到 TOS 后的访问地址 |

### 业务错误（解密前）

```json
{
  "code": 400,
  "message": "images不能为空且必须是list"
}
```

### 错误码

| code | 说明 |
| :--- | :--- |
| 200 | 成功，`encrypted_data` 中包含业务数据 |
| 400 | 参数缺失、解密失败、images 为空、URL 无效、图片下载失败 |
| 401 | 用户不存在/已禁用/未配置加密密钥 |
| 500 | 服务端内部错误 |

### 完整请求响应示例

#### 请求

**加密前的业务参数：**

```json
{
  "images": [
    "https://example.com/1.jpg",
    "data:image/png;base64,iVBORw0KGgo..."
  ]
}
```

**实际发送的请求体（加密后）：**

```json
{
  "user_id": 6,
  "encrypted_data": "U2FsdGVkX1+abc123...（base64密文）"
}
```

#### 响应

**实际收到的响应体（加密后）：**

```json
{
  "status": 200,
  "encrypted_data": "Xk9pQ2abc456...（base64密文）"
}
```

**解密后的业务响应：**

```json
{
  "review_batch_id": "review-20260321232207-d2a295d1",
  "items": [
    {
      "asset_id": "local-20260321232208-1998e81a",
      "asset_type": "Image",
      "asset_url": "Asset://Asset-20260321232209-rz5xb",
      "downstream_asset_id": "asset-20260321232209-rz5xb",
      "downstream_final_url": "https://ark-media-asset.tos-cn-beijing.volces.com/...",
      "source_url": "https://seedancs.tos-cn-beijing.volces.com/...",
      "submit_review_status": 1,
      "tos_url": "https://seedancs.tos-cn-beijing.volces.com/..."
    }
  ]
}
```

---

### 调用示例（Python）

```python
import base64
import json
from urllib.request import urlopen, Request
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# 配置
API_URL = "http://localhost:5000/api/moderation/image"
USER_ID = 1
KEY_HEX = "your_64_char_hex_key_here"

# 加密业务参数
payload = {
    "images": [
        "https://example.com/1.jpg",
        "data:image/png;base64,iVBORw0KGgo..."
    ]
}
key = bytes.fromhex(KEY_HEX)
data = json.dumps(payload).encode("utf-8")
cipher = AES.new(key, AES.MODE_ECB)
encrypted = base64.b64encode(cipher.encrypt(pad(data, AES.block_size))).decode()

# 发送请求
body = json.dumps({"user_id": USER_ID, "encrypted_data": encrypted}).encode("utf-8")
req = Request(API_URL, data=body, headers={"Content-Type": "application/json"})
resp = urlopen(req)
resp_json = json.loads(resp.read().decode("utf-8"))

# 解密响应
if "encrypted_data" in resp_json:
    ciphertext = base64.b64decode(resp_json["encrypted_data"])
    cipher = AES.new(key, AES.MODE_ECB)
    result = json.loads(unpad(cipher.decrypt(ciphertext), AES.block_size).decode("utf-8"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
```
