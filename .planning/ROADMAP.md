# Roadmap: video_plugin_zlhub_seedance

## Overview

**5 phases** | **17 requirements mapped** | All v1 requirements covered ✓

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Foundation | Create plugin shell and host metadata | CONT-01, CONT-02, CONT-04 | 3 |
| 2 | Parameters | Implement validation and capability mapping | PARA-01, PARA-02, PARA-03 | 3 |
| 3 | API Client | Build ZLHub Seedance 2.0 integration | API-01, API-02, API-03, API-04 | 4 |
| 4 | Orchestration | Wire end-to-end task lifecycle (Poll/Download) | ORCH-01, ORCH-02, ORCH-03 | 3 |
| 5 | UI & Integration | Finalize host callbacks and error handling | ERR-01, ERR-02, ERR-03, CONT-03 | 4 |

---

## Phase Details

### Phase 1: Foundation
**Goal:** Create the directory structure and the host-facing entry point metadata so `字字动画.exe` can recognize the plugin.

**Requirements:**
- **CONT-01**: `get_info()` metadata.
- **CONT-02**: `get_params()` UI schema.
- **CONT-04**: Directory structure.

**Success Criteria:**
1. `video_plugin_zlhub_seedance/` directory exists.
2. `main.py` exists with `get_info()` and `get_params()`.
3. Host (simulated/mocked) can read plugin info.

---

### Phase 2: Parameters
**Goal:** Implement the logic to sanitize, validate, and normalize host inputs into Seedance-specific constraints.

**Requirements:**
- **PARA-01**: Resolution/Ratio mapping.
- **PARA-02**: Duration/Audio settings.
- **PARA-03**: Image physical validation.

**Success Criteria:**
1. Invalid aspect ratios or resolutions are rejected/clamped.
2. Image size/format checks pass for valid files and fail for invalid ones.
3. Parameter objects are correctly transformed for API consumption.

---

### Phase 3: API Client
**Goal:** Implement the core network logic for talking to ZLHub.

**Requirements:**
- **API-01**: Auth headers.
- **API-02**: Create Task payload.
- **API-03**: Query Task status.
- **API-04**: Download logic.

**Success Criteria:**
1. Successful authentication with ZLHub.
2. `Task ID` received upon creation.
3. Polling returns `running` or `completed` states.
4. Video file is successfully downloaded to disk.

---

### Phase 4: Orchestration
**Goal:** Combine the client and parameters into a robust state machine for task execution.

**Requirements:**
- **ORCH-01**: End-to-end workflow logic.
- **ORCH-02**: Polling strategy (intervals/timeouts).
- **ORCH-03**: Terminal state mapping.

**Success Criteria:**
1. A single call to the orchestrator completes the full lifecycle.
2. Polling respects timeouts and stops on failure.
3. The plugin doesn't hang indefinitely.

---

### Phase 5: UI & Integration
**Goal:** Finalize the connection to the host via callbacks and standardized error reporting.

**Requirements:**
- **ERR-01**: Unified error prefixes.
- **ERR-02**: Progress callbacks.
- **ERR-03**: Lifecycle logging.
- **CONT-03**: `generate()` implementation.

**Success Criteria:**
1. User-facing errors start with `PLUGIN_ERROR:::`.
2. Host receives percentage/status updates during the process.
3. Logs capture enough detail to debug a failed task.
4. `main.py:generate()` successfully triggers the full orchestrator.

---
*Last updated: 2026-03-30*
