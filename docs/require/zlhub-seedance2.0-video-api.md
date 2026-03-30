***

# zlhub 平台 Seedance 2.0 视频生成 API 文档

## 1. 业务流程 (Workflow)
该视频生成服务采用**异步机制**，标准调用流程如下：
1. **发起任务 (Create)**：调用 `POST` 接口创建视频生成任务，获取 `Task ID`。
2. **轮询状态 (Poll)**：使用 `Task ID` 定时调用 `GET` 接口查询任务状态。
   - 若状态为 `running`，则等待后继续查询。
   - 若状态为已完成，解析返回的视频下载链接。
3. **获取产物 (Download)**：在任务完成后的 **24 小时内**下载生成的视频文件。

---

## 2. 接口说明：创建视频生成任务 (Create Task)

### 2.1 基础信息
* **Method**: `POST`
* **URL**: `https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks`
* **Headers**:
  * `Content-Type`: `application/json`
  * `Authorization`: `Bearer $ARK_API_KEY`

### 2.2 请求参数 (Request Body)
| 字段名 | 类型 | 必填 | 默认值 | 描述 |
| :--- | :--- | :---: | :--- | :--- |
| `content` | `object[]` | **是** | - | 多模态输入内容数组，支持文本、图片、音视频的组合（详见 2.3 节）。 |
| `generate_audio` | `boolean` | 否 | `true` | 是否生成与画面同步的声音（单声道）。`true`: 基于提示词/视觉自动生成人声、音效、BGM；`false`: 无声。 |
| `resolution` | `string` | 否 | `720p` | 分辨率。可选值：`480p`, `720p`。 |
| `ratio` | `string` | 否 | `adaptive` | 视频宽高比。可选值：`16:9`, `4:3`, `1:1`, `3:4`, `9:16`, `21:9`, `adaptive`（自动适配最优比例）。 |
| `duration` | `integer` | 否 | `5` | 生成时长（秒）。有效范围 `[4, 15]`，或传入 `-1` 交由模型智能决定。 |
| `tools` | `object[]` | 否 | - | 工具调用配置。支持联网搜索：`[{"type": "web_search"}]`。 |
| `service_tier` | `string` | 否 | - | *此指定款暂不支持。* |
| `draft` | `boolean` | 否 | - | *此指定款暂不支持。* |
| `frames` | `integer` | 否 | - | *此指定款暂不支持。* |
| `camera_fixed` | `boolean` | 否 | - | *此指定款暂不支持。* |

### 2.3 `content` 数组对象定义及约束

`content` 数组可组合传入不同类型的媒体信息（文本、图片、视频、音频）。

#### 2.3.1 文本对象 (Text)
用于描述期望生成的视频内容。
* **Schema**: `{"type": "text", "text": "<string>"}`
* **约束**: 建议中文 ≤ 500字，英文 ≤ 1000词（字数过多可能导致模型忽略细节）。

#### 2.3.2 图片对象 (Image)
* **Schema**: `{"type": "image_url", "image_url": {"url": "<string>"}, "role": "<string>"}`
* **`url` 支持格式**:
  * 公网 URL
  * Base64 编码 (例如: `data:image/png;base64,...`，不推荐用于大文件)
  * 素材 ID (格式: `asset://<ASSET_ID>`)
* **图片物理约束**:
  * 格式：`jpeg`, `png`, `webp`, `bmp`, `tiff`, `gif`
  * 宽高比范围：`(0.4, 2.5)`
  * 边长限制：宽和高需在 `[300, 6000]` 像素之间
  * 文件大小：单张 `< 30 MB`，请求体总大小 `< 64 MB`
* **`role` 与组合场景规则 (🚨 互斥，不可混用)**:
  1. **首帧生视频**: 传 1 张图，`role` = `first_frame` (或不填)。
  2. **首尾帧生视频**: 传 2 张图，一张 `role` = `first_frame`，另一张 `role` = `last_frame`。
  3. **参考图生视频 (多模态)**: 传 1~9 张图，`role` 均为 `reference_image`。若需首尾帧效果，需在 Prompt 文本中显式指定哪张图是首/尾帧。

#### 2.3.3 视频对象 (Video)
* **Schema**: `{"type": "video_url", "video_url": {"url": "<string>"}, "role": "reference_video"}`
* **`url` 支持格式**: 公网 URL 或 素材 ID。
* **视频物理约束**:
  * 格式：`mp4`, `mov`
  * 分辨率：`480p`, `720p`
  * 宽高比范围：`[0.4, 2.5]`
  * 边长限制：`[300, 6000]` 像素
  * 总像素（宽×高）：`[409600, 927408]` (例如 640x640 到 834x1112)
  * 时长与数量：单个 `[2, 15]` 秒，最多传 3 个，总时长 `≤ 15` 秒
  * 文件大小：单个 `< 50 MB`
  * 帧率：`[24, 60] FPS`

#### 2.3.4 音频对象 (Audio)
不可单独传入，必须配合图片或视频使用。
* **Schema**: `{"type": "audio_url", "audio_url": {"url": "<string>"}, "role": "reference_audio"}`
* **`url` 支持格式**: 公网 URL, Base64 (小写协议头 `data:audio/wav;base64,...`), 素材 ID。
* **音频物理约束**:
  * 格式：`wav`, `mp3`
  * 时长与数量：单个 `[2, 15]` 秒，最多传 3 段，总时长 `≤ 15` 秒
  * 文件大小：单个 `< 15 MB`，请求体总大小 `< 64 MB`

---

## 3. 接口说明：查询视频生成任务 (Query Task)

### 3.1 基础信息
* **Method**: `GET`
* **URL**: `https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks/{id}`
  *(需将 `{id}` 替换为 Create 接口返回的任务 ID)*
* **Headers**:
  * `Content-Type`: `application/json`
  * `Authorization`: `Bearer $ARK_API_KEY`

### 3.2 响应参数片段 (Response Fields Extract)
以下是此指定款模型返回的关键字段说明：

| 字段路径 | 类型 | 描述 |
| :--- | :--- | :--- |
| `tools` | `object[]` | 模型实际调用的工具配置（如 `[{"type": "web_search"}]`）。 |
| `usage` | `object` | 本次请求的 Token 消耗信息。 |
| `usage.completion_tokens` | `integer` | 模型输出视频花费的 Token 数量。 |
| `usage.total_tokens` | `integer` | 本次请求消耗的总 Token 数量。 |
| `usage.tool_usage` | `object` | 工具使用统计信息。 |
| `usage.tool_usage.web_search` | `integer` | 实际调用联网搜索的次数（开启 `web_search` 且被触发时返回，`0` 表示未搜索）。 |

---

## 4. 宽高比与分辨率映射对照表
当配置 `ratio` 时，生成的物理像素严格按照下表执行：

| 分辨率 (`resolution`) | 宽高比 (`ratio`) | 实际宽高像素值 |
| :--- | :--- | :--- |
| **480p** | 16:9 | 864 × 496 |
| | 4:3 | 752 × 560 |
| | 1:1 | 640 × 640 |
| | 3:4 | 560 × 752 |
| | 9:16 | 496 × 864 |
| | 21:9 | 992 × 432 |
| **720p** | 16:9 | 1280 × 720 |
| | 4:3 | 1112 × 834 |
| | 1:1 | 960 × 960 |
| | 3:4 | 834 × 1112 |
| | 9:16 | 720 × 1280 |
| | 21:9 | 1470 × 630 |

> **`adaptive` 自动适配逻辑**:
> - **文生视频**: 依据提示词语义判断。
> - **首帧/首尾生视频**: 自动选择最接近上传图片的比例。
> - **多模态参考**: 若意图为首帧生/编辑/延长，以对应图/视频为准；否则以传入的第一个媒体文件为准（优先级：视频 > 图片）。

---

## 5. 接口调用示例代码 (cURL)

### 示例 1: 多模态参考
包含文本、2张参考图、1段参考视频、1段参考音频。

```bash
curl -X POST https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "{模型ID}",
    "content": [
         {
            "type": "text",
            "text": "全程使用视频1的第一视角构图，全程使用音频1作为背景音乐。第一人称视角果茶宣传广告，需替换牌「苹苹安安」苹果果茶限定款；首帧为图片1，你的手摘下一颗带晨露的阿克苏红苹果，轻脆的苹果碰撞声；2-4 秒：快速切镜，你的手将苹果块投入雪克杯，加入冰块与茶底，用力摇晃，冰块碰撞声与摇晃声卡点轻快鼓点，背景音：「鲜切现摇」；4-6 秒：第一人称成品特写，分层果茶倒入透明杯，你的手轻挤奶盖在顶部铺展，在杯身贴上粉红包标，镜头拉近看奶盖与果茶的分层纹理；6-8 秒：第一人称手持举杯，你将图片2中的果茶举到镜头前（模拟递到观众面前的视角），杯身标签清晰可见，背景音「来一口鲜爽」，尾帧定格为图片2。背景声音统一为女生音色。"
        },
        {
            "type": "image_url",
            "image_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/r2v_tea_pic1.jpg"},
            "role": "reference_image"
        },
        {
            "type": "image_url",
            "image_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/r2v_tea_pic2.jpg"},
            "role": "reference_image"
        },
        {
          "type": "video_url",
          "video_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/r2v_tea_video1.mp4"},
          "role": "reference_video"
        },
        {
          "type": "audio_url",
          "audio_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_audio/r2v_tea_audio1.mp3"},
          "role": "reference_audio"
        }
    ],
    "generate_audio": true,
    "ratio": "16:9",
    "duration": 11,
    "watermark": false
}'
```

### 示例 2: 编辑视频 (视频内容替换)

```bash
curl -X POST https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "{模型ID}",
    "content": [
        {
            "type": "text",
            "text": "将视频1礼盒中的香水替换成图片1中的面霜，运镜不变"
        },
        {
            "type": "image_url",
            "image_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/r2v_edit_pic1.jpg"},
            "role": "reference_image"
        },
        {
            "type": "video_url",
            "video_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/r2v_edit_video1.mp4"},
            "role": "reference_video"
        }
    ],
    "generate_audio": true,
    "ratio": "16:9",
    "duration": 5,
    "watermark": true
}'
```

### 示例 3: 延长视频 (多视频拼接)

```bash
curl -X POST https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "{模型ID}",
    "content": [
        {
            "type": "text",
            "text": "视频1中的拱形窗户打开，进入美术馆室内，接视频2，之后镜头进入画内，接视频3"
        },
        {
            "type": "video_url",
            "video_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/r2v_extend_video1.mp4"},
            "role": "reference_video"
        },
        {
            "type": "video_url",
            "video_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/r2v_extend_video2.mp4"},
            "role": "reference_video"
        },
        {
            "type": "video_url",
            "video_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/r2v_extend_video3.mp4"},
            "role": "reference_video"
        }
    ],
    "generate_audio": true,
    "ratio": "16:9",
    "duration": 8,
    "watermark": true
}'
```

### 示例 4: 联网搜索生视频 (纯文本)

```bash
curl -X POST https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "{模型ID}",
    "content": [
         {
            "type": "text",
            "text": "微距镜头对准叶片上翠绿的玻璃蛙。焦点逐渐从它光滑的皮肤，转移到它完全透明的腹部，一颗鲜红的心脏正在有力地、规律地收缩扩张。"
        }
    ],
    "generate_audio": true,
    "ratio": "16:9",
    "duration": 11,
    "watermark": true,
    "tools": [
         {
             "type": "web_search"
         }
     ]
}'
```

### 示例 5: 查询状态 (Polling)

```bash
# 请将 URL 最后的 ID 替换为实际生成的 Task ID
curl -X GET https://zlhub.xiaowaiyou.cn/zhonglian/api/v1/proxy/ark/contents/generations/tasks/cgt-2026****hzc2z \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY"
```

---

## 6. 其他注意事项
* **虚拟人像素材**: 若需使用自有虚拟人像素材 (`asset://` 格式)，请联系相关运营人员开通与获取 ID。