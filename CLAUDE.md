<!-- GSD:project-start source:PROJECT.md -->
## Project

**字字动画视频插件扩展（zlhub seedance2.0）**

这是一个在现有字字动画插件体系上新增业务插件的项目。项目将新增独立目录 `video_plugin_zlhub_seedance`，用于对接 zlhub 中转平台的 seedance2.0 视频大模型接口，并以插件形式被 `字字动画.exe` 加载。目标是独立接入 seedance2.0，同时在能力口径上与现有成熟插件保持同等级别。

**Core Value:** 新增的 zlhub seedance2.0 插件必须在不改宿主程序的前提下，被字字动画稳定加载并完成完整的视频生成主链路。

### Constraints

- **Compatibility**: 必须以插件方式被 `字字动画.exe` 加载 — 维持当前产品集成方式
- **Boundary**: 不修改宿主程序 — 用户明确边界，减少联调风险
- **Scope**: 仅接入 zlhub seedance2.0 — 先完成单点闭环，再考虑扩展
- **Quality Bar**: 能力口径需与成熟插件同级 — 避免“能跑但不可用”的低质量接入
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages & Runtime
- **Python 3.x** - Primary language
- No explicit runtime version constraints in code
## Dependencies
- `requests` - HTTP client for API calls
- `PIL` (Pillow) - Image processing for compression/resizing
- `sqlite3` - Built-in SQLite for task logging
- Standard library: `base64`, `json`, `os`, `sys`, `time`, `datetime`, `hashlib`, `re`, `shutil`, `tempfile`, `threading`, `zipfile`, `collections`, `math`, `pathlib`, `typing`, `urllib.parse`
## Configuration Files
- `video_plugin_zzdhapi/main.py` - Plugin file (also serves as config storage)
- `video_plugin_geeknow/main.py` - Plugin file with SQLite task log database
## Frameworks
- No web framework (direct API calls)
- Plugin architecture for external video generation services
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Code Style
- **snake_case** for functions and variables
- **PascalCase** for classes: `PluginFatalError`, `_BufferingHandler`
- **UPPER_CASE** for constants: `DEFAULT_MODEL`, `AUDIO_ENABLED`
- Chinese comments and docstrings for user-facing logic
- English for technical implementation details
## Function Naming
- `_normalize_*` - Parameter normalization/validation
- `_build_*` - Request payload construction
- `_get_*` - Configuration lookups
- `_extract_*` - Response parsing
- `_poll_*` - Status polling
- `_download_*` - Video download
## Error Handling
- Custom exception class: `PluginFatalError`
- Error prefix for UI: `PLUGIN_ERROR:::`
- Graceful degradation with warnings via `print()`
- Retry logic with configurable attempts
## Pattern Conventions
## Logging
- ZZDH: `print()` for output
- GeekNow: Custom `logging` module with buffered handler
- Sensitive data masking in logs (API keys, base64 images)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Overall Architecture
- **Plugin-based architecture** for video generation services
- Two independent plugins sharing common patterns
- Synchronous API calls with async polling for status
## Design Patterns
### 1. Model Configuration Pattern
- `MODEL_CONFIGS` (ZZDH) / `_MODEL_DISPLAY_MAP` + `_MODEL_INFO` (GeekNow)
- Each model has: resolutions, durations, generation modes, audio options
### 2. Parameter Sanitization
- `_sanitize_params()` / `_preprocess_params()` - Normalize and validate user parameters
- Fallback to defaults for invalid values
- Model-specific validation
### 3. Request Builder Pattern
- Separate payload builders per model type:
### 4. Polling Pattern
- Status polling loop with configurable intervals
- Progress callback support for UI updates
- Error handling with retry logic
### 5. Task Logging (GeekNow)
- SQLite-based task history
- Status tracking: running → success/failed/download_failed
- Error keyword filtering for retry decisions
## Data Flow
## Abstractions
- `plugin_utils` - Shared config load/save utilities
- `progress_callback` - UI progress updates
- Error prefix `PLUGIN_ERROR:::` for user-facing errors
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
