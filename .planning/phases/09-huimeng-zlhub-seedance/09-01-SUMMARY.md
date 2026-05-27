---
phase: 09-huimeng-zlhub-seedance
plan: 01
subsystem: plugin
tags: [huimeng, seedance, happyhorse, video-plugin]
requires:
  - phase: 08-zlhub-requires2
    provides: Seedance 插件机制与宿主契约基础能力
provides:
  - 新插件目录 video_plugin_huimeng_seedance
  - Huimeng 任务接口 create/query/download 适配
  - 5 模型 UI 选择与模型差异化 params 映射
  - happyhorse 参数排除规则（不传 human_review/reference_videos/reference_audios）
affects: [phase-09, video_plugin_huimeng_seedance]
key-files:
  modified: [video_plugin_huimeng_seedance/main.py, video_plugin_huimeng_seedance/ui/index.html]
duration: 1h
completed: 2026-05-27
---

# Phase 09 Plan 01 Summary

## Accomplishments

- 创建独立插件目录 `video_plugin_huimeng_seedance`，保留宿主契约函数 `get_info/get_params/generate`。
- `main.py` 完成 Huimeng 主链路：
  - `POST /api/v1/tasks` 创建任务
  - `GET /api/v1/tasks/{task_id}` 轮询状态
  - `result.video_url` 下载视频
- 模型与参数约束落地：
  - UI 支持 5 个模型 ID：`happyhorse-1.0`、`seedance-2.0-value`、`seedance-2.0-fast-value`、`seedance-2.0`、`seedance-2.0-fast`
  - `happyhorse-1.0` 不传 `human_review/reference_videos/reference_audios`
  - `ratio/resolution` 按模型独立枚举
- 增加参考图本地文件上传公网 URL 预处理（`imageproxy.zhongzhuan.chat`）并回填 payload。
- 保留统一错误前缀 `PLUGIN_ERROR:::`、进度回调与任务日志机制。

## Verification

- `python -m py_compile video_plugin_huimeng_seedance/main.py` 通过。
- `python video_plugin_huimeng_seedance/main.py` 输出 `smoke check passed`。
- `rg` 校验通过：
  - 5 个模型 ID 存在
  - `happyhorse` 分支不支持字段标记存在
  - Huimeng 接口路径 `/api/v1/tasks` 存在
  - `PLUGIN_ERROR:::` 常量存在
  - 上传接口 `imageproxy.zhongzhuan.chat` 存在

## Notes

- 本次为代码级与静态校验完成；宿主侧联调（真实任务提交、轮询、下载链路）需在字字动画环境做一轮人工验证。
