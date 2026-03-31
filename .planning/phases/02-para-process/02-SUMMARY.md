---
phase: 02-para-process
plan: 01
subsystem: api
tags: [seedance, params, validation, plugin]
requires:
  - phase: 01-base-build
    provides: 插件壳与参数读取入口
provides:
  - 参数规范化与物理像素映射
  - 时长与音频开关标准化
  - 图片格式/大小约束校验
affects: [api-client, orchestration]
tech-stack:
  added: []
  patterns: [_normalize_*, PluginFatalError, PLUGIN_ERROR:::]
key-files:
  created: []
  modified: [video_plugin_zlhub_seedance/main.py]
key-decisions:
  - "ratio=adaptive 不做本地像素映射，交由服务端处理"
  - "duration 支持 -1，其余值截断到 [4,15]"
patterns-established:
  - "参数入口统一经 _sanitize_params 清洗后持久化"
  - "图片物理约束只做本地格式/大小校验，几何约束由服务端兜底"
requirements-completed: [PARA-01, PARA-02, PARA-03]
duration: 13 min
completed: 2026-03-31
---

# Phase 2 Plan 01: 参数处理 Summary

**Seedance 参数清洗链路已落地，覆盖分辨率/比例映射、时长边界处理与图片约束校验。**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-31T07:30:00Z
- **Completed:** 2026-03-31T07:42:54Z
- **Tasks:** 5
- **Files modified:** 1

## Accomplishments
- 补齐 `PluginFatalError` 并统一 `PLUGIN_ERROR:::` 错误前缀。
- 实现 `_normalize_resolution`、`_normalize_aspect_ratio`、`_normalize_duration`、`_normalize_audio_generation`。
- 集成 `RESOLUTION_RATIO_MAP` 与 `_get_physical_pixels`，补充 `pixel_width/pixel_height` 输出。
- 增加 `_validate_image_constraints`，校验图片格式与 `<30MB` 大小限制。

## Task Commits

1. **Task 1: 实现异常类与基础常量** - `529c9e3` (feat)
2. **Task 2-5: 规范化与校验逻辑集成** - `dd26490` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `video_plugin_zlhub_seedance/main.py` - 新增参数规范化函数族、图片约束校验、像素映射与参数集成清洗。

## Decisions Made
- 使用字符串集合映射音频开关，统一返回布尔值。
- `adaptive` 比例不映射固定像素，保留为服务端自适应。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- 本地 `python -m py_compile` 在当前 shell 环境不可用，改为通过 git diff 与函数落地检查完成实现验证。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 参数对象已具备 API 客户端可直接消费的标准字段。
- Phase 3 可直接在此基础上实现任务创建/轮询/下载。

---
*Phase: 02-para-process*
*Completed: 2026-03-31*
