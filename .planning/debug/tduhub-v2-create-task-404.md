# tduhub-v2-create-task-404

## Symptoms
- 实时日志显示 `create_task.request` 使用 endpoint: `https://apihub.tduvr.club/v1/task/create`。
- 接口返回：`HTTP 404 - Invalid URL (POST /v1/task/create)`。
- 整体报错：`PLUGIN_ERROR:::创建任务失败`。

## Investigation
- 当前宿主实际运行插件目录是：`video_plugin_tduhub_seedance_V2`（非 `video_plugin_zlhub_seedance_V2`）。
- `video_plugin_tduhub_seedance_V2/main.py` 的 `_sanitize_params()` 会使用持久化 `base_url` 动态拼接任务 endpoint。
- 用户持久化配置中的 `base_url` 为 `https://apihub.tduvr.club`，导致拼接后的 `/v1/task/create` 在该域名不可用。

## Root Cause
- 任务 endpoint 来源被旧版可配置 `base_url` 覆盖，导致运行时路由漂移到不支持 requires2 路径的域名，最终 404。

## Fix Applied
- 文件：`video_plugin_tduhub_seedance_V2/main.py`
1. 固定 requires2 默认地址：
   - `_DEFAULT_API_BASE_URL = "https://api.zlhub.cn"`
   - `_DEFAULT_TASK_CREATE_URL = "https://api.zlhub.cn/v1/task/create"`
   - `_DEFAULT_TASK_QUERY_URL = "https://api.zlhub.cn/v1/task/get"`
2. 在 `_sanitize_params()` 中忽略旧 `base_url` 对 endpoint 的影响：
   - 记录 `config.source.deprecated_base_url_ignored` 日志；
   - 强制写回固定 `base_url/task_create_url/task_query_url`。

## Validation
- `python -m py_compile video_plugin_tduhub_seedance_V2/main.py` 通过。
- 用 `base_url=https://apihub.tduvr.club` 做输入模拟后，`_sanitize_params()` 输出：
  - `base_url=https://api.zlhub.cn`
  - `task_create_url=https://api.zlhub.cn/v1/task/create`
  - `task_query_url=https://api.zlhub.cn/v1/task/get`

## Next Action
1. 让宿主重新加载 `video_plugin_tduhub_seedance_V2`（重启宿主或刷新插件）。
2. 再执行一次生成，确认实时日志里 `create_task.request.endpoint` 已变为 `https://api.zlhub.cn/v1/task/create`。
