# 视频模型的params参数说明
### seedance模型的params必须具备的参数
```jsx
{
    "prompt": "你的提示词",
    "ratio": "16:9",
    "duration": 5,
    "resolution": "1080P"，
    "reference_images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]，
    "human_review": false
}
```

### happhorse模型的params必须具备的参数
```jsx
{
    "prompt": "你的提示词",
    "ratio": "16:9",
    "duration": 5,
    "resolution": "1080P"，
    "reference_images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]，
}
```

### 1. HappyHorse 1.0

阿里云HappyHorse视频生成模型，支持文生视频、首帧图生视频、参考生视频、视频编辑，720P/1080P，时长3-15秒。

**请求示例**

```jsx
POST /api/v1/tasks
{
  "model": "happyhorse-1.0",
  "params": {
    "prompt": "你的提示词",
    "ratio": "16:9",
    "duration": 5,
    "watermark": false,  //默认是false
    "resolution": "1080P",
    "reference_images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
  }
}
```

**参数说明**

| **参数** | **类型** | **必填** | **说明** |
| --- | --- | --- | --- |
| ratio | string | 否 | 宽高比可选值: 16:9 | 9:16 | 1:1 | 4:3 | 3:4默认: 16:9 |
| prompt | string | 是 | 视频描述文本(最大2500字符) |
| duration | integer | 否 | 视频时长(秒)默认: 5 |
| image_url | string | 否 | 首帧图片URL(i2v模式) |
| video_url | string | 否 | 输入视频URL(视频编辑模式) |
| resolution | string | 否 | 分辨率可选值: 1080P | 720P默认: 1080P |
| audio_setting | string | 否 | 声音控制(视频编辑模式)可选值: auto | origin默认: auto |
| reference_images | array | 否 | 参考图片URL列表(r2v模式1-9张，视频编辑模式0-5张) |

### 2.Seedance 2.0 定制版

Seedance 2.0 定制版，低成本生成 + 智能画质增强，以更低价格获得720p/1080p高清视频。支持真人/动漫场景优化。

**请求示例:**

```jsx
POST /api/v1/tasks
{
  "model": "seedance-2.0-value",
  "params": {
    "prompt": "你的提示词",
    "duration": 5,
    "resolution": "720p",
    "generate_audio": true,
    "scene_optimize": "realistic"
  }
}
```

**参数说明:**

| **参数** | **类型** | **必填** | **说明** |
| --- | --- | --- | --- |
| ratio | string | 否 | 可选值: 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | 21:9 | adaptive默认: adaptive |
| prompt | string | 是 | 视频描述文本(支持中英日印尼西葡，建议500字以内) |
| duration | integer | 否 | 默认: 5 |
| image_url | string | 否 | 首帧图片URL(图生视频-首帧) |
| resolution | string | 否 | 分辨率可选值: 720p | 1080p默认: 720p |
| human_review | boolean | 否 | 真人审核模式默认: false |
| generate_audio | boolean | 否 | 默认: true |
| scene_optimize | string | 否 | 场景优化可选值: realistic | anime默认: realistic |
| last_frame_image | string | 否 | 尾帧图片URL(图生视频-首尾帧) |
| reference_audios | array | 否 | 参考音频URL列表(0-3段，总时长不超过15s) |
| reference_images | array | 否 | 参考图片URL列表(1-9张，多模态参考生视频) |
| reference_videos | array | 否 | 参考视频URL列表(0-3个，总时长不超过15s) |
| first_frame_image | string | 否 | 首帧图片URL(图生视频-首尾帧) |
| return_last_frame | boolean | 否 | 默认: false |

### 3. Seedance 2.0 Fast定制版

Seedance 2.0 Fast 定制版，极速生成 + 智能画质增强，以更低价格获得720p/1080p高清视频。支持真人/动漫场景优化。

**请求示例:**

```jsx
POST /api/v1/tasks
{
  "model": "seedance-2.0-fast-value",
  "params": {
    "prompt": "你的提示词",
    "duration": 5,
    "resolution": "720p",
    "generate_audio": true,
    "scene_optimize": "realistic"
  }
}
```

**参数说明:**

### **参数说明**

| **参数** | **类型** | **必填** | **说明** |
| --- | --- | --- | --- |
| ratio | string | 否 | 可选值: 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | 21:9 | adaptive默认: adaptive |
| prompt | string | 是 | 视频描述文本(支持中英日印尼西葡，建议500字以内) |
| duration | integer | 否 | 默认: 5 |
| image_url | string | 否 | 首帧图片URL(图生视频-首帧) |
| resolution | string | 否 | 分辨率可选值: 720p | 1080p默认: 720p |
| human_review | boolean | 否 | 真人审核模式默认: false |
| generate_audio | boolean | 否 | 默认: true |
| scene_optimize | string | 否 | 场景优化可选值: realistic | anime默认: realistic |
| last_frame_image | string | 否 | 尾帧图片URL(图生视频-首尾帧) |
| reference_audios | array | 否 | 参考音频URL列表(0-3段，总时长不超过15s) |
| reference_images | array | 否 | 参考图片URL列表(1-9张，多模态参考生视频) |
| reference_videos | array | 否 | 参考视频URL列表(0-3个，总时长不超过15s) |
| first_frame_image | string | 否 | 首帧图片URL(图生视频-首尾帧) |
| return_last_frame | boolean | 否 | 默认: false |

### 4. Seedance 2.0

新一代旗舰视频生成模型，最高画质。支持有声视频、多模态参考(图/视频/音频)。

**请求示例:**

```jsx
POST /api/v1/tasks
{
  "model": "seedance-2.0",
  "params": {
    "prompt": "你的提示词",
    "duration": 5,
    "resolution": "720p",
    "generate_audio": true
  }
}
```

**参数说明:**

| **参数** | **类型** | **必填** | **说明** |
| --- | --- | --- | --- |
| ratio | string | 否 | 宽高比可选值: 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | 21:9 | adaptive默认: adaptive |
| prompt | string | 是 | 视频描述文本(支持中英日印尼西葡，建议500字以内) |
| duration | integer | 否 | 视频时长(秒)，取值[4,15]默认: 5 |
| image_url | string | 否 | 首帧图片URL(图生视频-首帧) |
| resolution | string | 否 | 分辨率可选值: 480p | 720p | 1080p默认: 720p |
| human_review | boolean | 否 | 真人审核模式：开启后素材将自动上传资产库审核加白，支持含真人人脸的素材默认: false |
| generate_audio | boolean | 否 | 是否生成同步音频默认: true |
| last_frame_image | string | 否 | 尾帧图片URL(图生视频-首尾帧) |
| reference_audios | array | 否 | 参考音频URL列表(0-3段，总时长不超过15s) |
| reference_images | array | 否 | 参考图片URL列表(1-9张，多模态参考生视频) |
| reference_videos | array | 否 | 参考视频URL列表(0-3个，总时长不超过15s) |
| first_frame_image | string | 否 | 首帧图片URL(图生视频-首尾帧) |
| return_last_frame | boolean | 否 | 是否返回尾帧图像默认: false |

### 5. Seedance 2.0 Fast

新一代快速视频生成模型，支持有声视频、多模态参考(图/视频/音频)。

**请求示例:**

```
POST /api/v1/tasks
{
  "model": "seedance-2.0-fast",
  "params": {
    "prompt": "你的提示词",
    "duration": 5,
    "resolution": "720p",
    "generate_audio": true
  }
}
```

**参数说明:**

| **参数** | **类型** | **必填** | **说明** |
| --- | --- | --- | --- |
| ratio | string | 否 | 宽高比可选值: 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | 21:9 | adaptive默认: adaptive |
| prompt | string | 是 | 视频描述文本(支持中英日印尼西葡，建议500字以内) |
| duration | integer | 否 | 视频时长(秒)，取值[4,15]默认: 5 |
| image_url | string | 否 | 首帧图片URL(图生视频-首帧) |
| resolution | string | 否 | 分辨率(不支持1080p)可选值: 480p | 720p默认: 720p |
| human_review | boolean | 否 | 真人审核模式：开启后素材将自动上传资产库审核加白，支持含真人人脸的素材默认: false |
| generate_audio | boolean | 否 | 是否生成同步音频默认: true |
| last_frame_image | string | 否 | 尾帧图片URL(图生视频-首尾帧) |
| reference_audios | array | 否 | 参考音频URL列表(0-3段，总时长不超过15s) |
| reference_images | array | 否 | 参考图片URL列表(1-9张，多模态参考生视频) |
| reference_videos | array | 否 | 参考视频URL列表(0-3个，总时长不超过15s) |
| first_frame_image | string | 否 | 首帧图片URL(图生视频-首尾帧) |
| return_last_frame | boolean | 否 | 是否返回尾帧图像默认: false6. NB Pro官方 |
