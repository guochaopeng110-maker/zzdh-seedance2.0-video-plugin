# 集成 - 外部服务

## 视频生成 API

### ZZDH-API 插件 (`video_plugin_zzdhapi/main.py`)
- **基础 URL**: `https://zizidonghua.com`
- **API 端点**: `/v1/videos`
- **身份验证**: 通过 `Authorization` 请求头发送 Bearer 令牌
- **支持的模型**:
  - `wan2.6-i2v` / `wan2.6-i2v-flash` / `wan2.2-i2v-plus` - 阿里 Wan 模型
  - `wan2.2-kf2v-flash` - 关键帧视频
  - `kling-3.0-omni` - 快手可灵
  - `vidu-q3-pro` / `vidu-q3-turbo` - 字节跳动 Vidu

### GeekNow 插件 (`video_plugin_geeknow/main.py`)
- **基础 URL**:
  - `https://www.geeknow.top` (海外 CN2 服务)
  - `https://api.geeknow.top` (CDN 服务 - 默认)
  - `https://geek.closeai.icu` (国内服务器)
- **API 端点**: `/v1/videos`
- **身份验证**: 通过 `Authorization` 请求头发送 Bearer 令牌
- **支持的模型**:
  - Sora2 变体 (sora-2, sora2-pro-*, sora3, sora-2-oai)
  - Veo 3.1 (veo_3_1, veo_3_1-fast)
  - Grok Video (grok-video-3, grok-video-3-pro, grok-video-3-max)
  - 豆包 Seedance (doubao-seedance-1-5-pro_*)
  - Wan2.6 (wan2.6-t2v:*, wan2.6-i2v:*)
  - Vidu (Vidu-q3-pro, Vidu-q3-turbo)
  - 可灵 Kling (Kling-3.0, Kling-3.0-Omni)
  - 海螺 Hailuo (Hailuo-2.3, Hailuo-2.3-fast)

## 数据存储
- **SQLite**: `video_task_logs.db` - 任务历史和日志 (GeekNow 插件)
- **配置存储**: 与插件同目录的 JSON 文件 (通过 `plugin_utils`)

## 无外部数据库
- 无 SQL 数据库依赖
- 无身份验证提供商 (使用 API 密钥)
- 无 Webhook 集成
