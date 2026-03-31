---
status: testing
phase: 01-base-build
source: [01-SUMMARY.md]
started: 2026-03-31T12:00:00Z
updated: 2026-03-31T12:00:00Z
---

## Current Test

number: 1
name: 插件目录与文件验证
expected: |
  目录 `video_plugin_zlhub_seedance/` 存在，且其中包含 `main.py` 文件。
awaiting: user response

## Tests

### 1. 插件目录与文件验证
expected: 目录 `video_plugin_zlhub_seedance/` 存在，且其中包含 `main.py` 文件。
result: [pending]

### 2. 插件元数据验证 (get_info)
expected: 调用 `get_info()` 返回名称为 "ZLHub Seedance 视频生成"，描述包含 "ZLHub" 关键字。
result: [pending]

### 3. 插件参数验证 (get_params)
expected: 调用 `get_params()` 返回包含 `api_key`, `ratio`, `generate_audio` 等字段的字典。
result: [pending]

### 4. UI 界面完整性验证 (index.html)
expected: `ui/index.html` 包含对 `ratio` (含 adaptive), `generate_audio`, `duration` 和 `web_search` 的配置项。
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

[none yet]
