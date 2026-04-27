---
status: investigating
trigger: "Investigate issue: shuzai-seedance-video-task-logs-table-missing"
created: 2026-04-27T16:42:58.0983914+08:00
updated: 2026-04-27T16:48:06.4579496+08:00
---

## Current Focus

hypothesis: Cross-machine runtime may execute a code path where table creation is not guaranteed before inserts, potentially due stale/alternate module loading.
test: Inspect runtime logs and call sites for indicators of module version/path and DB-init execution ordering.
expecting: Find evidence tying `workflow.failed` to missing pre-insert table initialization.
next_action: inspect plugin runtime logs for `workflow.failed` and module load markers

## Symptoms

expected: On any machine, after plugin folder copy and normal setup, clicking generate should create task and proceed without DB errors.
actual: Generate action fails on other machines with workflow.failed and DB table missing.
errors: "[ShuzaiSeedance] {\"ts\": \"2026-04-27 16:34:59\", \"event\": \"workflow.failed\", \"fields\": {\"task_id\": null, \"error\": \"PLUGIN_ERROR:::no such table: video_task_logs\"}}"
reproduction: Copy `video_plugin_shuzai_seedance` directory to another machine under plugin directory, open plugin UI, click generate.
started: Works on original machine; fails on other machine after copy.

## Eliminated

## Evidence

- timestamp: 2026-04-27T16:44:05.5038459+08:00
  checked: .planning/debug/knowledge-base.md
  found: No knowledge base content/match available.
  implication: Proceed with fresh hypothesis investigation.

- timestamp: 2026-04-27T16:44:57.2130717+08:00
  checked: repo file inventory for shuzai seedance plugin
  found: Plugin contains `video_plugin_shuzai_seedance/main.py` and a committed `video_plugin_shuzai_seedance/video_task_logs.db`.
  implication: Copying plugin directory can include a pre-existing DB state that may differ across machines.

- timestamp: 2026-04-27T16:46:18.5022168+08:00
  checked: `video_plugin_shuzai_seedance/main.py` and local sqlite schema
  found: Source code calls `_ensure_task_log_db()` from `_db_conn()` and creates `video_task_logs` via `CREATE TABLE IF NOT EXISTS`; local DB currently includes `video_task_logs`.
  implication: Reported failure likely comes from code/version/path mismatch on target machine, not from current source snapshot behavior.

- timestamp: 2026-04-27T16:47:22.9372183+08:00
  checked: git history metadata and plugin artifacts
  found: `main.py` has multiple recent revisions; plugin folder includes `__pycache__/main.cpython-311.pyc`, which can be copied between machines.
  implication: Copied artifacts can cause execution differences from expected source snapshot.

- timestamp: 2026-04-27T16:48:06.4579496+08:00
  checked: git diff of DB init patterns (`6c0bd82` vs current)
  found: Older code had plain `_db_conn()` plus module-level `_init_task_log_db()` call; current code moved to `_ensure_task_log_db()` invoked inside `_db_conn()`.
  implication: There is known historical variation in DB-init strategy, supporting a version-skew hypothesis across machines.

## Resolution

root_cause:
fix:
verification:
files_changed: []
