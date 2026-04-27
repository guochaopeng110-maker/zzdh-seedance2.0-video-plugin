# shuzai的视频API

# 快速开始

你将使用一个 API 令牌（形如 `sk-...`）通过 HTTP 调用视频生成模型。生成是异步任务：提交后返回 `task_id`，再通过轮询查询状态，成功后获取视频地址或从代理接口下载。

## 可用的视频模型id
seedance2.0-v
seedance2.0-t
seedance2.0-1080-v
seedance2.0-1080-t
doubao-seedance-2-0-260128

## 服务地址（Base URL）

你的服务方会提供一个域名（例如 `https://openai.shuzaiaigc.com`）。后续示例默认使用：

```
https://openai.shuzaiaigc.com
```

如果示例里出现 `localhost`，通常是服务端“服务器地址”尚未配置为公网域名。

## 鉴权

所有 API 请求都需要在请求头中带上令牌：

```
Authorization: Bearer sk-your_token复制
```

令牌泄露等同于余额泄露。请妥善保管，不要上传到 GitHub 或公开日志。

# 视频生成（Task API）

推荐使用任务接口（更稳定、适配多供应商）。主要有 3 个端点：

- `POST /v1/video/generations`：提交生成任务（text2video / image2video / edit 统一入口）
- `GET /v1/video/generations/{task_id}`：查询任务状态
- `GET /v1/videos/{task_id}/content`：下载视频代理（可选）

## 1）提交任务

最小请求只需要 `model` 与 `prompt`。更多参数通过 `metadata` 传递（不同模型可用参数不同）。

```
curl "https://openai.shuzaiaigc.com/v1/video/generations" \
  -H "Authorization: Bearer sk-your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seedance-2-0-260128",
    "prompt": "一个宇航员在月球上行走，电影质感",
    "seconds": "5",
    "metadata": {
      "resolution": "720p",
      "ratio": "16:9",
      "watermark": false
    }
  }'复制
```

说明：`seconds` 可以传字符串，服务端会自动兼容。你也可以把可选参数放入 `metadata`。

## 2）轮询任务状态

提交后会返回一个 `task_id`（形如 `task_xxx`）。使用它轮询：

```
curl "https://openai.shuzaiaigc.com/v1/video/generations/task_xxxxxx" \
  -H "Authorization: Bearer sk-your_token"复制
```

当任务完成后，响应里通常会包含：

- `status`：`queued` / `running` / `succeeded` / `failed`
- `url`：成功时的视频地址
- `usage.total_tokens`：成功时用于计费的 token 总量
- 响应参数如下:
{
    "code": "success",
    "data": {
        "action": "generate",
        "channel_id": 1,
        "created_at": 1777267527,
        "data": {
            "content": {
                "video_url": "https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/doubao-seedance-2-0/02177726752719100000000000000000000ffffac1838801a1396.mp4?X-Tos-Algorithm=TOS4-HMAC-SHA256&X-Tos-Credential=AKLTYWJkZTExNjA1ZDUyNDc3YzhjNTM5OGIyNjBhNDcyOTQ%2F20260427%2Fcn-beijing%2Ftos%2Frequest&X-Tos-Date=20260427T052830Z&X-Tos-Expires=86400&X-Tos-Signature=b325a0c1673df20c307bc66add779e44d7ef622e71092e0d9e3e3e3caf36663f&X-Tos-SignedHeaders=host"
            },
            "created_at": 1777267527,
            "draft": false,
            "duration": 5,
            "execution_expires_after": 172800,
            "framespersecond": 24,
            "generate_audio": true,
            "id": "cgt-20260427132527-srqlq",
            "model": "doubao-seedance-2-0-260128",
            "ratio": "16:9",
            "resolution": "720p",
            "seed": 14105,
            "service_tier": "default",
            "status": "succeeded",
            "updated_at": 1777267730,
            "usage": {
                "completion_tokens": 108900,
                "total_tokens": 108900
            }
        },
        "fail_reason": "",
        "finish_time": 1777267746,
        "group": "default",
        "id": 924,
        "platform": "54",
        "progress": "100%",
        "properties": {
            "input": "",
            "origin_model_name": "seedance2.0-t",
            "upstream_model_name": "doubao-seedance-2-0-260128"
        },
        "quota": 1102739,
        "result_url": "https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/doubao-seedance-2-0/02177726752719100000000000000000000ffffac1838801a1396.mp4?X-Tos-Algorithm=TOS4-HMAC-SHA256&X-Tos-Credential=AKLTYWJkZTExNjA1ZDUyNDc3YzhjNTM5OGIyNjBhNDcyOTQ%2F20260427%2Fcn-beijing%2Ftos%2Frequest&X-Tos-Date=20260427T052830Z&X-Tos-Expires=86400&X-Tos-Signature=b325a0c1673df20c307bc66add779e44d7ef622e71092e0d9e3e3e3caf36663f&X-Tos-SignedHeaders=host",
        "start_time": 1777267537,
        "status": "SUCCESS",
        "submit_time": 1777267527,
        "task_id": "task_w0XiKE7VASocb6syKm3On1XPccmuiSsu",
        "updated_at": 1777267746,
        "user_id": 11
    },
    "message": ""
}
