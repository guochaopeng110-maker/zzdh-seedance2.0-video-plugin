# 技术栈 - Technology Stack

## 语言与运行时
- **Python 3.x** - 主要语言
- 代码中没有明确的运行时版本约束

## 依赖项
- `requests` - 用于 API 调用的 HTTP 客户端
- `PIL` (Pillow) - 用于压缩/缩放的图像处理库
- `sqlite3` - 内置的 SQLite，用于任务日志记录
- 标准库: `base64`, `json`, `os`, `sys`, `time`, `datetime`, `hashlib`, `re`, `shutil`, `tempfile`, `threading`, `zipfile`, `collections`, `math`, `pathlib`, `typing`, `urllib.parse`

## 配置文件
- `video_plugin_zzdhapi/main.py` - 插件文件 (同时也作为配置存储)
- `video_plugin_geeknow/main.py` - 插件文件，带有 SQLite 任务日志数据库

## 框架
- 无 Web 框架 (直接进行 API 调用)
- 用于外部视频生成服务的插件架构
