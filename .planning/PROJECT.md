# 字字动画视频插件扩展（zlhub seedance2.0）

## What This Is

这是一个在现有字字动画插件体系上新增业务插件的项目。项目将新增独立目录 `video_plugin_zlhub_seedance`，用于对接 zlhub 中转平台的 seedance2.0 视频大模型接口，并以插件形式被 `字字动画.exe` 加载。目标是独立接入 seedance2.0，同时在能力口径上与现有成熟插件保持同等级别。

## Core Value

新增的 zlhub seedance2.0 插件必须在不改宿主程序的前提下，被字字动画稳定加载并完成完整的视频生成主链路。

## Requirements

### Validated

- ✓ 字字动画已具备插件加载模式，可加载独立业务插件目录 — existing
- ✓ 现有插件已具备“提交任务 → 轮询状态 → 下载产物”的视频生成主流程 — existing
- ✓ 现有插件已具备参数预处理、错误封装、进度回调等插件级通用能力模式 — existing

### Active

- [ ] 新增独立目录 `video_plugin_zlhub_seedance`，作为字字动画可加载插件
- [ ] 完成 zlhub seedance2.0 接口接入，打通提交、查询、下载全链路
- [ ] 插件能力口径与现有成熟插件同级（配置项、日志、错误码映射、重试/容错策略、可观测性）
- [ ] 在不改动 `字字动画.exe` 宿主侧代码的边界内完成上线可用版本

### Out of Scope

- 多模型/多平台扩展（除 zlhub seedance2.0 外） — 本期聚焦单模型单平台接入，避免范围膨胀
- 宿主程序功能改造 — 本期明确仅新增插件目录，不改宿主

## Context

- 当前仓库已有三个业务目录：`video_plugin_geeknow`、`video_plugin_zzdhapi`、`ZZDH-API_seedance`。
- `video_plugin_zzdhapi` 可作为能力口径参考；`ZZDH-API_seedance` 因为是二进制插件，不可直接作为代码实现参考。
- 技术栈以 Python 插件实现为主，现有代码模式包含请求构造、参数清洗、状态轮询、结果下载与统一错误前缀机制。
- 新需求文档位于 `docs/require/zlhub-seedance2.0-video-api.md`。

## Constraints

- **Compatibility**: 必须以插件方式被 `字字动画.exe` 加载 — 维持当前产品集成方式
- **Boundary**: 不修改宿主程序 — 用户明确边界，减少联调风险
- **Scope**: 仅接入 zlhub seedance2.0 — 先完成单点闭环，再考虑扩展
- **Quality Bar**: 能力口径需与成熟插件同级 — 避免“能跑但不可用”的低质量接入

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 新目录命名为 `video_plugin_zlhub_seedance` | 用户明确指定目录名，便于与现有插件并列管理 | — Pending |
| 采用 seedance2.0 独立插件形态 | 与目标模型能力边界一致，避免在通用插件上耦合补丁 | — Pending |
| 以 `video_plugin_zzdhapi` 作为能力口径参考而非代码基底 | 用户要求独立实现，且 `ZZDH-API_seedance` 为二进制不可参考 | — Pending |
| 验收优先“主程序可稳定加载” | 先确保宿主集成可用，再逐步扩展深度能力 | — Pending |
| 本期不改宿主程序且不做多模型扩展 | 明确边界，控制实施风险与范围 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-30 after initialization*
