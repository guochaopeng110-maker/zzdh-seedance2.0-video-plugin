# huimeng API

绘梦 API 提供图像/视频生成和文本对话能力，两套接口、统一鉴权。

## 一：认证方式

### 1. API Key 认证

所有接口通过 `Authorization` 请求头传入 API Key 进行鉴权。

**HTTP Header**

HTTP

```
Authorization: Bearer hm-xxxxxxxxxxxxxxxx
```

> 💡 在 **控制台 → API 密钥** 页面创建和管理你的 API Key。请妥善保管密钥，不要将其暴露在客户端代码中。
> 

## 二：图像 / 视频模型

**异步任务模式**：提交任务获取 `task_id`，再轮询或通过 Webhook 获取结果。

### 1. 提交任务

- **Method:** `POST`
- **Path:** `/api/v1/tasks`
- **描述:** 提交生成任务，返回 `task_id`。根据所选模型传入对应的参数。

### 1.1.请求示例 (curl)

```bash
curl -X POST https://api.huimengi.com/api/v1/tasks \
  -H "Authorization: Bearer hm-xxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
  "model": "seedance-2.0",
  "params": {
    "prompt": "一只猫在海滩上漫步",
    "duration": 5,
    "ratio": "16:9"
  },
  "webhook_url": "https://your-server.com/callback"
}'
```

### 1.2.响应示例 (json)

```json
{
  "task_id": "a820e1b8-fb15-4ec9-a13c-bdd1d4eb6679",
  "status": "pending"
}
```

### 1.3.请求参数

| **参数** | **类型** | **必填** | **说明** |
| --- | --- | --- | --- |
| `model` | string | **必填** | 模型标识 |
| `params` | object | **必填** | 模型参数（各模型参数不同，视频模型的参数参考:视频模型的params参数说明.md）。图片/视频/音频参数仅支持公网可访问的 URL |
| `webhook_url` | string | 可选 | 回调地址，任务完成/失败时 POST 通知 |
| `idempotency_key` | string | 可选 | 幂等键，防止重复提交 |

参考图片的公网URL生成参考python代码:

```python
_IMAGE_UPLOAD_URL = "https://imageproxy.zhongzhuan.chat/api/upload"
def upload_image_to_host(image_path, timeout=60):
    try:
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f)}
            response = requests.post(_IMAGE_UPLOAD_URL, files=files, timeout=timeout)
        if response.status_code != 200:
            _log(
                f"[ref-image] upload failed status={response.status_code} path={image_path}",
                "WARNING",
            )
            return None
        data = response.json()
        image_url = data.get("url")
        if image_url:
            return str(image_url)
        _log(f"[ref-image] upload missing url path={image_path}", "WARNING")
        return None
    except Exception as e:
        _log(f"[ref-image] upload error path={image_path} err={e}", "WARNING")
        return None
```


### 2. 查询结果

- **Method:** `GET`
- **Path:** `/api/v1/tasks/{task_id}`
- **描述:** 轮询任务状态。`status` 为 `completed` 时获取结果 URL；为 `failed` 时查看错误原因。

### 2.1.请求示例 (curl)

```bash
curl -X GET https://api.huimengi.com/api/v1/tasks/{task_id} \
  -H "Authorization: Bearer hm-xxxxxxxxxxxxxxxx"
```

### 2.2.成功响应（视频模型）(json)

```json
{
  "id": "a820e1b8-...",
  "model": "seedance-2.0",
  "status": "completed",
  "result": {
    "video_url": "https://...",
    "duration": 5,
    "resolution": "720p",
    "ratio": "16:9"
  },
  "cost": 1.55,
  "created_at": "2026-04-24T10:00:00",
  "completed_at": "2026-04-24T10:01:20"
}
```

### 2.3.成功响应（图片模型）(json)

```json
{
  "id": "a820e1b8-...",
  "model": "seedream-4.5",
  "status": "completed",
  "result": {
    "image_url": "https://...",
    "image_urls": ["https://..."],
    "image_count": 1,
    "size": "2048x2048"
  },
  "cost": 0.09,
  "created_at": "2026-04-24T10:00:00",
  "completed_at": "2026-04-24T10:00:35"
}
```

### 2.3.失败响应 (json)

```json
{
  "id": "a820e1b8-...",
  "status": "failed",
  "error_message": "错误原因",
  "cost": 0
}
```

### 2.4响应字段

| **字段** | **类型** | **说明** |
| --- | --- | --- |
| `id` | string | 任务 ID |
| `model` | string | 模型标识 |
| `status` | string | 状态流转：`pending` → `processing` → `completed` / `failed` |
| `result` | object | 生成结果（仅 `completed` 时有值） |
| `error_message` | string | 错误信息（仅 `failed` 时有值） |
| `cost` | number | 消耗积分（失败为 0） |
| `created_at` | string | 任务创建时间 |
| `completed_at` | string | 任务完成时间 |

### 2.5.result 字段 — 视频模型

| **字段** | **类型** | **说明** |
| --- | --- | --- |
| `video_url` | string | 视频 URL（24 小时有效） |
| `duration` | integer | 视频时长（秒） |
| `resolution` | string | 分辨率 |
| `ratio` | string | 宽高比 |

### 2.6.result 字段 — 图片模型

| **字段** | **类型** | **说明** |
| --- | --- | --- |
| `image_url` | string | 图片 URL（24 小时有效） |
| `image_urls` | array | 所有图片 URL 列表 |
| `image_count` | integer | 图片数量 |
| `size` | string | 图片尺寸 |

## 三：Webhook 回调

提交任务时传入 `webhook_url`，任务完成或失败时平台会主动向该地址发送 POST 请求通知结果，免去轮询。

### 3.1.回调触发时机

| **事件 event 值** | **说明** |
| --- | --- |
| `task.completed` | 任务完成，`result` 包含结果数据 |
| `task.failed` | 任务失败，`error_message` 包含错误原因 |

### 3.2.回调 Payload (json)

```json
{
  "event": "task.completed",
  "task_id": "a820e1b8-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "data": {
    "status": "completed",
    "result": {
      "video_url": "https://...",
      "duration": 5
    },
    "error_message": null,
    "cost": 1.5,
    "created_at": "2026-05-07T12:00:00",
    "completed_at": "2026-05-07T12:01:30"
  }
}
```

### 3.3.签名验证

每次回调请求包含签名头，用于验证请求来自绘梦平台。

- **签名算法:** `HMAC-SHA256(secret_key, "{timestamp}.{body}")`

| **Header** | **说明** |
| --- | --- |
| `X-HuiMeng-Signature` | HMAC-SHA256 签名（hex） |
| `X-HuiMeng-Timestamp` | Unix 时间戳（秒） |
| `X-HuiMeng-Event` | 事件类型 |

### 3.4.Python 验证示例

```python
import hmac, hashlib, time

def verify_webhook(body: bytes, headers: dict, secret: str) -> bool:
    signature = headers["X-HuiMeng-Signature"]
    timestamp = headers["X-HuiMeng-Timestamp"]
    if abs(time.time() - int(timestamp)) > 300:
        return False
    expected = hmac.new(
        secret.encode(), f"{timestamp}.{body.decode()}".encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### 3.5.重试策略

回调投递失败时（网络错误、5xx、429），平台会按指数退避自动重试，最多 5 次：

第1次: 2s} →第2次: 4s → 第3次: 8s → 第4次: 16s →第5次: 60s

- 接收方返回 `2xx` 表示投递成功；
- 返回 `4xx`（非 429）不会重试；
- 所有重试失败后回调将被丢弃，不影响任务本身的状态。

## 四：可用模型列表

### 4.1.视频模型:

| **模型名称** | **模型标识** | **类型** | **价格** | **操作** |
| --- | --- | --- | --- | --- |
| **HappyHorse 1.0** | happyhorse-1.0 | 视频 | 0.225 积分/秒起 | [测试](https://api.huimengi.com/models/happyhorse-1.0) |
| **Seedance 2.0 定制版** | seedance-2.0-value | 视频 | 0.558 积分/秒起 | [测试](https://api.huimengi.com/models/seedance-2.0-value) |
| **Seedance 2.0 Fast 定制版** | seedance-2.0-fast-value | 视频 | 0.47 积分/秒起 | [测试](https://api.huimengi.com/models/seedance-2.0-fast-value) |
| **Seedance 2.0** | seedance-2.0 | 视频 | 0.46 积分/秒起 | [测试](https://api.huimengi.com/models/seedance-2.0) |
| **Seedance 2.0 Fast** | seedance-2.0-fast | 视频 | 0.37 积分/秒起 | [测试](https://api.huimengi.com/models/seedance-2.0-fast) |

### 4.2.图像模型：

| **模型名称** | **模型标识** | **类型** | **价格** | **操作** |
| --- | --- | --- | --- | --- |
| **Image 2官方** | image-2-official | 图像 | 0.29 积分/次起 | [测试](https://api.huimengi.com/models/image-2-official) |
| **Image 2** | image-2 | 图像 | 0.18 积分/次 | [测试](https://api.huimengi.com/models/image-2) |
| **NB 2官方** | nb-2-official | 图像 | 0.5 积分/次起 | [测试](https://api.huimengi.com/models/nb-2-official) |
| **NB 2** | nb-2 | 图像 | 0.12 积分/次 | [测试](https://api.huimengi.com/models/nb-2) |
| **NB Pro** | nb-pro | 图像 | 0.18 积分/次 | [测试](https://api.huimengi.com/models/nb-pro) |
| **NB Pro官方** | nb-pro-official | 图像 | 0.8 积分/次起 | [测试](https://api.huimengi.com/models/nb-pro-official) |
| **Z Image Turbo** | z-image-turbo | 图像 | 0.1 积分/次 | [测试](https://api.huimengi.com/models/z-image-turbo) |
| **Seedream 5.0 Lite** | seedream-5.0-lite | 图像 | 0.22 积分/次 | [测试](https://api.huimengi.com/models/seedream-5.0-lite) |
| **Seedream 4.5** | seedream-4.5 | 图像 | 0.25 积分/次 | [测试](https://api.huimengi.com/models/seedream-4.5) |


## 视频模型的params参数
见文件:视频模型的params参数说明.md
