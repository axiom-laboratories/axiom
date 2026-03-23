---
phase: 52-queue-visibility-node-drawer-and-draining
plan: "01"
subsystem: testing
tags: [pytest, tdd, async, sqlite, node-draining, dispatch-diagnosis, node-detail]

# Dependency graph
requires: []
provides:
  - "VIS-04 test stubs: 8 failing tests documenting drain/undrain/pull_work/heartbeat/auto-offline contracts"
  - "VIS-01 test stubs: 6 failing tests documenting dispatch diagnosis API (reason codes + queue_position)"
  - "VIS-03 test stubs: 6 failing tests documenting node detail enrichment (running_job, eligible_pending_jobs, recent_history, capabilities)"
affects:
  - "52-02: implements backend to turn these stubs GREEN"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytest.fail('not implemented') as first body line in all stubs — consistent RED phase marker"
    - "Async in-memory SQLite fixture (aiosqlite) copied from test_pagination.py pattern"
    - "Docstrings document expected future call signatures for Wave 2 implementors"

key-files:
  created:
    - puppeteer/tests/test_draining.py
    - puppeteer/tests/test_dispatch_diagnosis.py
    - puppeteer/tests/test_node_detail.py
  modified: []

key-decisions:
  - "pytest.fail('not implemented') as first body line — consistent with Phase 49 Wave 0 stub convention so all stubs fail with marker (not skip or error)"
  - "Helper factories (_make_node, _make_job) defined in each file rather than a shared conftest to keep stubs self-contained"
  - "target_node_id field referenced in test_dispatch_diagnosis stubs as docstring-only (not used in stub body) — avoids collection errors if DB column is missing before Plan 02 adds it"

patterns-established:
  - "Wave 0 stub pattern: async fixture + factory helpers + docstring contract + pytest.fail as first body line"

requirements-completed:
  - VIS-01
  - VIS-03
  - VIS-04

# Metrics
duration: 4min
completed: 2026-03-23
---

# Phase 52 Plan 01: Queue Visibility Node Drawer and Draining Summary

**20 pytest.fail stubs across three files establishing RED phase for VIS-01 (dispatch diagnosis), VIS-03 (node detail enrichment), and VIS-04 (node draining state machine)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T16:19:41Z
- **Completed:** 2026-03-23T16:23:30Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `test_draining.py` with 8 stubs covering drain/undrain endpoints, pull_work exclusion for DRAINING nodes, heartbeat status preservation, list_nodes response, and auto-offline transition logic
- Created `test_dispatch_diagnosis.py` with 6 stubs covering all dispatch diagnosis reason codes (no_nodes_online, capability_mismatch, all_nodes_busy, target_node_unavailable, pending_dispatch) and queue position ordering
- Created `test_node_detail.py` with 6 stubs covering node detail enrichment fields (running_job presence/absence, eligible_pending_jobs with 50-cap, recent_history 24h window, capabilities)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_draining.py stub scaffold** - `0daa35b` (test)
2. **Task 2: Create test_dispatch_diagnosis.py stub scaffold** - `0b1aed4` (test)
3. **Task 3: Create test_node_detail.py stub scaffold** - `85ae900` (test)

## Files Created/Modified

- `puppeteer/tests/test_draining.py` - 8 VIS-04 stubs: drain/undrain endpoints, pull_work exclusion, heartbeat preservation, auto-offline transition
- `puppeteer/tests/test_dispatch_diagnosis.py` - 6 VIS-01 stubs: dispatch diagnosis reason codes and queue position
- `puppeteer/tests/test_node_detail.py` - 6 VIS-03 stubs: node detail enrichment fields

## Decisions Made

- `pytest.fail("not implemented")` as first body line — consistent with Phase 49 Wave 0 convention; ensures FAILED (not ERROR) marker before implementation lands
- Helper factories defined per-file (not shared conftest) to keep stubs self-contained and readable in isolation
- `target_node_id` referenced in dispatch diagnosis stub docstrings only — avoids DB collection errors if the column doesn't exist yet

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 20 stubs confirmed FAILED (not ERROR) — RED phase established for Plan 02
- Plan 02 implements backend: drain/undrain endpoints, `get_dispatch_diagnosis()`, `get_node_detail()` in `job_service.py`, and the DRAINING status machine in `db.py`/`main.py`
- Pre-existing EE-only test collection errors (test_foundry_mirror, test_intent_scanner, test_lifecycle_enforcement, test_smelter, test_staging, test_tools) are unchanged — not caused by this plan

---
*Phase: 52-queue-visibility-node-drawer-and-draining*
*Completed: 2026-03-23*

## Self-Check: PASSED

- FOUND: puppeteer/tests/test_draining.py
- FOUND: puppeteer/tests/test_dispatch_diagnosis.py
- FOUND: puppeteer/tests/test_node_detail.py
- FOUND: .planning/phases/52-queue-visibility-node-drawer-and-draining/52-01-SUMMARY.md
- FOUND commit: 0daa35b (test_draining.py)
- FOUND commit: 0b1aed4 (test_dispatch_diagnosis.py)
- FOUND commit: 85ae900 (test_node_detail.py)
