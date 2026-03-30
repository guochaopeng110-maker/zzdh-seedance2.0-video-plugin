# 结构 - 目录布局

```
zz-video-plugins/
├── .claude/                    # Claude Code 配置
│   ├── get-shit-done/          # GSD 工作流模板
│   └── settings.json
├── .codex/                    # Codex 配置
├── .gemini/                   # Gemini 配置
├── .opencode/                 # OpenCode 配置
├── .planning/                 # GSD 规划目录
│   └── codebase/              # 本映射文档所在目录
├── docs/                      # 文档
├── video_plugin_geeknow/      # GeekNow API 插件
│   ├── main.py               # 主插件文件 (1830 行)
│   ├── info.json             # 插件元数据
│   └── video_task_logs.db    # SQLite 任务日志数据库
├── video_plugin_zzdhapi/     # ZZDH-API 插件
│   └── main.py              # 主插件文件 (~817 行)
└── ZZDH-API-seedance/        # 附加插件变体
```

## 关键位置

### 主要源文件
- `video_plugin_zzdhapi/main.py` - ZZDH API 插件 (1-817 行)
- `video_plugin_geeknow/main.py` - GeekNow API 插件 (1-1830 行)

### 入口点
- `generate(context)` - 两个插件中的主生成函数
- `get_info()` - 插件元数据
- `get_params()` - 配置检索
- `handle_action()` - 操作处理器 (仅限 GeekNow)

### 配置
- 插件配置存储在 main.py 同目录的 JSON 中
- 默认参数定义在 `_default_params` 字典中

## 命名规范
- 函数和变量使用 Snake_case
- 面向用户的 UI 字符串和注释使用中文 (例如: "文生视频", "首帧生视频")
- 模型名称使用原始 API 名称 (kling-*, wan2.6-*, 等)
- 私有函数使用下划线前缀: `_build_*`, `_normalize_*`
