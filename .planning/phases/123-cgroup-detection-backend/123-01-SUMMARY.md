---
phase: 123-cgroup-detection-backend
plan: 1
subsystem: Node + Orchestrator
tags: [cgroup-detection, node-telemetry, heartbeat-integration]
dependency_graph:
  requires: []
  provides: [cgroup-version-reporting, heartbeat-payload-extension, db-schema-v51]
  affects: [Phase 127 dashboard, cgroup-aware job scheduling]
tech_stack:
  added:
    - CgroupDetector class (pathlib, os-based detection)
  patterns:
    - Module-level detection caching (reusing NODE_ID pattern)
    - Optional fields in HeartbeatPayload (backward compatible)
    - Nullable DB columns with IF NOT EXISTS migrations
decision_list:
  - "Pure v2: /proc/self/cgroup has single 0:: line + /sys/fs/cgroup/cgroup.controllers exists"
  - "Pure v1: /proc/self/cgroup has numbered lines (1:, 2:, 3:) without v2 markers"
  - "Hybrid detection (mixed v1+v2): conservative report as v1 (triggers amber warning path)"
  - "Unsupported: permission errors, missing /proc, inconsistent v2 format without controllers"
  - "Startup logging: info for v1/v2, warning for unsupported"
  - "Heartbeat stateless: both fields sent every heartbeat, no change-detection needed"
  - "Orchestrator unconditional update: node.detected_cgroup_version = hb.detected_cgroup_version"
key_files_created:
  - puppets/environment_service/tests/test_cgroup_detector.py (168 lines, 14 test cases)
  - puppeteer/migration_v51.sql (6 lines, two ADD COLUMN statements)
key_files_modified:
  - puppets/environment_service/node.py (added CgroupDetector class + module-level caching + heartbeat integration)
  - puppeteer/agent_service/models.py (HeartbeatPayload + NodeResponse fields)
  - puppeteer/agent_service/db.py (Node table columns)
  - puppeteer/agent_service/services/job_service.py (receive_heartbeat persistence)
metrics:
  duration: ~25 minutes
  tasks_completed: 3/3
  tests_passing: 14/14
  commits: 3
---

# Phase 123 Plan 01: Cgroup Detection Backend — Summary

**Objective:** Implement node-side cgroup detection (v1 vs v2 vs unsupported) and orchestrator persistence.

**Purpose:** Enable Phase 127 dashboard to show operators which cgroup version each node is running, supporting informed decisions about workload compatibility and enforcement guarantees. Addresses CGRP-01 (node detects at startup) and CGRP-02 (reports in heartbeat).

## Completion Status

✅ All 3 tasks complete
✅ All 14 tests passing
✅ All Python syntax checks pass
✅ CGRP-01 requirement satisfied: Node detects cgroup v1 vs v2 vs unsupported at startup
✅ CGRP-02 requirement satisfied: Node reports detected version in every heartbeat

## Tasks Executed

### Task 1: CgroupDetector class + node-side integration ✓

**Status:** Complete — 14/14 tests passing

**Implementation:**
- Added `CgroupDetector` class to `puppets/environment_service/node.py` with static `detect()` method
  - Reads `/proc/self/cgroup` to identify v1 (numbered lines: `1:`, `2:`, etc.) vs v2 (single `0::` line)
  - Confirms v2 by checking `/sys/fs/cgroup/cgroup.controllers` existence
  - Hybrid detection (mixed v1+v2): conservatively reports as v1
  - Exception handling: `FileNotFoundError`, `PermissionError`, `OSError` → returns unsupported
  - Returns tuple: (version_str: "v1" | "v2" | "unsupported", raw_info_str: detailed detection info)

- Module-level caching following NODE_ID pattern:
  - Function `_detect_cgroup_version()` runs once at module load
  - Caches result in globals: `DETECTED_CGROUP_VERSION`, `DETECTED_CGROUP_RAW`
  - Startup logging: `logger.info()` for v1/v2, `logger.warning()` for unsupported

- Integrated into `heartbeat_loop()` payload construction:
  - Added two fields to heartbeat dict: `detected_cgroup_version`, `cgroup_raw`
  - Both included in every heartbeat (stateless, no change-detection)

**Test Coverage (14 tests):**
- `test_detect_cgroup_v2_pure`: Pure v2 detection with cgroup.controllers present ✓
- `test_detect_cgroup_v1_pure`: Pure v1 detection with numbered hierarchy ✓
- `test_detect_cgroup_hybrid_conservatively_v1`: Mixed v1+v2 reported as v1 ✓
- `test_detect_cgroup_unsupported_permission_error`: PermissionError handling ✓
- `test_detect_cgroup_unsupported_file_not_found`: FileNotFoundError handling ✓
- `test_detect_cgroup_unsupported_os_error`: OSError handling ✓
- `test_detect_cgroup_unsupported_v2_format_no_controllers`: Inconsistent v2 detection ✓
- `test_detect_cgroup_logs_v1_info`: v1 logging path ✓
- `test_detect_cgroup_logs_v2_info`: v2 logging path ✓
- `test_detect_raw_data_contains_line_count`: Raw data format validation ✓
- `test_detect_raw_data_contains_content_preview`: Raw data includes content ✓
- `test_detect_empty_cgroup_file`: Empty file handling ✓
- `test_detect_whitespace_only_cgroup_file`: Whitespace-only file handling ✓
- `test_detect_malformed_cgroup_content`: Malformed content handling ✓

**Commits:**
- `3fb6d67`: feat(123-cgroup-detection-backend): implement CgroupDetector class + node-side integration

### Task 2: Orchestrator data models + DB schema ✓

**Status:** Complete — All syntax checks pass

**Implementation:**
- `puppeteer/agent_service/models.py`:
  - Added `detected_cgroup_version: Optional[str] = None` to `HeartbeatPayload`
  - Added `cgroup_raw: Optional[str] = None` to `HeartbeatPayload`
  - Added `detected_cgroup_version: Optional[str] = None` to `NodeResponse` (for Phase 127 dashboard)
  - No validators needed (raw data passed through)

- `puppeteer/agent_service/db.py`:
  - Added `detected_cgroup_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)` to Node table
  - Added `cgroup_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` to Node table
  - Both columns nullable (backward compatible, fresh create_all handles them)

- `puppeteer/agent_service/services/job_service.py`:
  - Updated `receive_heartbeat()` to unconditionally persist both fields:
    ```python
    node.detected_cgroup_version = hb.detected_cgroup_version
    node.cgroup_raw = hb.cgroup_raw
    ```
  - Stateless update: every heartbeat overwrites (consistent with stats/tags pattern)
  - Placed after env_tag logic, before db.commit()

**Backward Compatibility:** All new fields are Optional[str] with None defaults. Old nodes without cgroup fields will send None; orchestrator stores None; dashboard handles gracefully.

**Commits:**
- `bc99855`: feat(123-cgroup-detection-backend): orchestrator data models + db schema

### Task 3: Migration SQL + test file confirmation ✓

**Status:** Complete

**Implementation:**
- Created `puppeteer/migration_v51.sql`:
  ```sql
  -- Migration v51: Add cgroup detection columns to nodes table
  ALTER TABLE nodes ADD COLUMN IF NOT EXISTS detected_cgroup_version VARCHAR(255);
  ALTER TABLE nodes ADD COLUMN IF NOT EXISTS cgroup_raw TEXT;
  ```
  - Follows existing migration pattern (migration_v50.sql was previous)
  - Uses `IF NOT EXISTS` for idempotency (safe to run multiple times)
  - Column names match Node model definition
  - VARCHAR(255) for version ("v1", "v2", "unsupported" all fit)
  - TEXT for raw data (full /proc contents, typically < 1KB)
  - Postgres-compatible (SQLite will auto-create via create_all on next startup)

- Confirmed test file exists:
  - `puppets/environment_service/tests/test_cgroup_detector.py`
  - 168 lines, 14 test cases, all passing

**Commits:**
- `50a1c6c`: feat(123-cgroup-detection-backend): migration sql + test file confirmation

## Verification Results

### Unit Test Verification
```
14 passed in 1.00s ✓
```

All test categories passing:
- CgroupDetector v2 detection: ✓
- CgroupDetector v1 detection: ✓
- CgroupDetector hybrid detection: ✓
- CgroupDetector error handling (4 scenarios): ✓
- CgroupDetector logging behavior: ✓
- CgroupDetector raw data format: ✓
- CgroupDetector edge cases (3 scenarios): ✓

### Syntax Verification
- `node.py` compiles: ✓
- `models.py` compiles: ✓
- `db.py` compiles: ✓
- `job_service.py` compiles: ✓

### Code Integration Verification
- HeartbeatPayload fields optional and backward compatible: ✓
- Node DB columns nullable with IF NOT EXISTS: ✓
- receive_heartbeat() persistence unconditional: ✓
- Heartbeat payload construction includes both cgroup fields: ✓
- Module-level detection caching reuses NODE_ID pattern: ✓

## Requirements Traceability

**CGRP-01: Node detects cgroup at startup**
- Status: ✅ SATISFIED
- Implementation: `_detect_cgroup_version()` runs at module load, caches in globals
- Evidence: All 14 tests pass, logging verified

**CGRP-02: Node reports in heartbeat**
- Status: ✅ SATISFIED
- Implementation: `detected_cgroup_version` and `cgroup_raw` added to heartbeat payload
- Evidence: heartbeat_loop() includes both fields in payload dict

## Deviations from Plan

None — plan executed exactly as written.

## Known Limitations & Future Work

**Phase 127 (Dashboard Integration) — Deferred:**
- Dashboard display of detected_cgroup_version (amber warning for v1?)
- UI placement (Nodes view badge? node detail drawer?)
- Recommendation: Phase 127 CONTEXT.md will decide based on operator feedback

**Phase 124+ (Enforcement Validation) — Deferred:**
- Job scheduling based on cgroup version compatibility
- Blocking unsupported cgroups for enforcement-critical jobs
- Recommendation: After Phase 127 dashboard provides visibility

## Testing Strategy for Deployment

**Fresh Deployment (create_all from db.py):**
```bash
cd puppeteer && python -c "from agent_service.db import Base, engine; Base.metadata.create_all(engine)"
# Both columns auto-created by SQLAlchemy ✓
```

**Existing Postgres Deployment:**
```bash
docker exec puppeteer-db-1 psql -d jobs -f migration_v51.sql
# Manually run SQL migration (if not auto-managed by deployment pipeline)
```

**Local SQLite Dev:**
```bash
rm jobs.db  # Start fresh
python -m agent_service.main
# Tables created automatically on startup ✓
```

**Node Verification:**
```bash
# Run any node and check logs during startup:
# Expected output:
# [node-xxxxx] 💓 Detected cgroup: v1 (numbered hierarchy)
# or
# [node-xxxxx] 💓 Detected cgroup: v2 (cgroup.controllers found at /sys/fs/cgroup/)
# or
# [node-xxxxx] ⚠️ Detected cgroup: unsupported — node may have restricted cgroup access
```

**Heartbeat Verification:**
```bash
# Monitor a live heartbeat (API or logs):
curl -s https://localhost:8001/api/heartbeat-sample | jq '.detected_cgroup_version'
# Expected output: "v1" or "v2" or "unsupported"
```

## Remaining Work for Next Phases

**Phase 124 (Ephemeral Guarantee):** Depends on Phase 122 (node limit integration) because limits already require container isolation.

**Phase 127 (Dashboard & Monitoring):** Can start as soon as Phase 123 complete (this phase). Consumes `detected_cgroup_version` from NodeResponse.

**Phase 125-126 (Enforcement Validation):** Uses cgroup version info for workload compatibility checks.

## Summary

Phase 123 successfully implements complete node-side cgroup detection and orchestrator persistence. The CgroupDetector class is production-ready with comprehensive test coverage. Module-level caching follows project patterns. Heartbeat integration is transparent and stateless. All requirements (CGRP-01, CGRP-02) satisfied. Ready for Phase 127 dashboard integration.

**Total duration:** ~25 minutes
**Commits:** 3 (one per task)
**Test coverage:** 14/14 passing
**Files created:** 2 (test file, migration)
**Files modified:** 4 (node.py, models.py, db.py, job_service.py)
