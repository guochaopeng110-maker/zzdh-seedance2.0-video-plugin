# Requirements: video_plugin_zlhub_seedance

**Defined:** 2026-03-30
**Core Value:** 新增的 zlhub seedance2.0 插件必须在不改宿主程序的前提下，被字字动画稳定加载并完成完整的视频生成主链路。

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Plugin Contract (Host Compatibility)

- [ ] **CONT-01**: Implement `get_info()` returning plugin metadata (name, version, icon).
- [ ] **CONT-02**: Implement `get_params()` returning supported UI configuration schema.
- [ ] **CONT-03**: Implement `generate(context)` entry point for the host to trigger tasks.
- [ ] **CONT-04**: Ensure plugin directory structure matches `字字动画.exe` loading requirements.

### API Client (ZLHub Seedance 2.0)

- [ ] **API-01**: Implement authentication via `Authorization: Bearer $ARK_API_KEY`.
- [ ] **API-02**: Implement Task Creation (POST) with support for text and image inputs.
- [ ] **API-03**: Implement Task Query (GET) for polling status.
- [ ] **API-04**: Implement Artifact Retrieval (Download) for the generated .mp4 file.

### Task Orchestration

- [ ] **ORCH-01**: Implement sequential workflow: parameter validation -> task creation -> status polling -> result download.
- [ ] **ORCH-02**: Implement polling logic with configurable intervals and max timeout (Seedance recommendation).
- [ ] **ORCH-03**: Handle task terminal states (completed, failed) and map to plugin outcomes.

### Media & Parameters

- [ ] **PARA-01**: Support `resolution` (480p, 720p) and `ratio` (16:9, 9:16, etc.) parameters.
- [ ] **PARA-02**: Support `duration` (4-15s) and `generate_audio` toggle.
- [ ] **PARA-03**: Implement physical constraint validation for images (size < 30MB, format, dimensions).

### Error & Observability

- [ ] **ERR-01**: Map API errors to unified `PLUGIN_ERROR:::` prefix for host display.
- [ ] **ERR-02**: Implement progress callbacks to update host UI during polling/downloading.
- [ ] **ERR-03**: Log key lifecycle events (Task ID, status transitions, failures) to local file/console.

## v2 Requirements

Deferred to future release.

### Advanced Media

- **ADV-01**: Support video-to-video (reference_video role).
- **ADV-02**: Support multiple reference images (role = reference_image).
- **ADV-03**: Support web_search tool integration.

### Operations

- **OPS-01**: Advanced retry strategies with exponential backoff (Tenacity).
- **OPS-02**: Local task history database (SQLite).

## Out of Scope

| Feature | Reason |
|---------|--------|
| Host UI Modification | Strictly prohibited by project constraints |
| Multi-model support | Milestone focus is solely on Seedance 2.0 |
| Real-time streaming | API is asynchronous task-based |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONT-01 | Phase 1 | Pending |
| CONT-02 | Phase 1 | Pending |
| CONT-04 | Phase 1 | Pending |
| PARA-01 | Phase 2 | Pending |
| PARA-02 | Phase 2 | Pending |
| PARA-03 | Phase 2 | Pending |
| API-01 | Phase 3 | Pending |
| API-02 | Phase 3 | Pending |
| API-03 | Phase 3 | Pending |
| API-04 | Phase 3 | Pending |
| ORCH-01 | Phase 4 | Pending |
| ORCH-02 | Phase 4 | Pending |
| ORCH-03 | Phase 4 | Pending |
| ERR-01 | Phase 5 | Pending |
| ERR-02 | Phase 5 | Pending |
| ERR-03 | Phase 5 | Pending |
| CONT-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-30*
