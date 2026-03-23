---
phase: 52-queue-visibility-node-drawer-and-draining
plan: "02"
subsystem: api
tags: [fastapi, sqlalchemy, draining, node-lifecycle, dispatch-diagnosis, job-service]

requires:
  - phase: 52-01
    provides: test stubs (test_draining.py, test_dispatch_diagnosis.py) with pytest.fail placeholders

provides:
  - _node_is_eligible() static helper on JobService (extracted from pull_work inline loop)
  - DRAINING node lifecycle: drain/undrain endpoints, pull_work guard, heartbeat guard, auto-offline transition
  - get_dispatch_diagnosis() async static method returning structured {reason, message, queue_position}
  - GET /jobs/{guid}/dispatch-diagnosis endpoint
  - Job.target_node_id column in db.py
  - migration_v42.sql

affects:
  - 52-03-node-detail-drawer (uses drain/undrain endpoints for drain/undrain UI controls)
  - 52-04-pending-job-callout (uses dispatch-diagnosis endpoint for PENDING job explanations)

tech-stack:
  added: []
  patterns:
    - "_node_is_eligible() static helper reused in both pull_work and get_dispatch_diagnosis — single eligibility logic source"
    - "DRAINING guard before freshness override in list_nodes prevents status masking"
    - "DRAINING auto-transition runs after db.commit() in report_result so count query sees updated state"

key-files:
  created:
    - puppeteer/migration_v42.sql
  modified:
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/db.py
    - puppeteer/tests/test_draining.py
    - puppeteer/tests/test_dispatch_diagnosis.py

key-decisions:
  - "_node_is_eligible() extracted as static method — both pull_work and get_dispatch_diagnosis call it; no logic duplication"
  - "Job.target_node_id added to db.py (was only on ScheduledJob) — dispatch diagnosis requires it for target_node_unavailable case"
  - "DRAINING guard in receive_heartbeat preserves status but still updates last_seen — node stays visible in list_nodes without timing out to OFFLINE prematurely"
  - "report_result stores node_id before db.commit() since job.node_id may be cleared on RETRYING transition"
  - "Concurrency limit in get_dispatch_diagnosis defaults to 5 (same as pull_work) — no Node.concurrency_limit column exists in db.py"

patterns-established:
  - "DRAINING guard pattern: status in ('TAMPERED', 'DRAINING') → early return / preserve status"
  - "Auto-transition pattern: check count AFTER commit so query sees fully updated state"

requirements-completed: [VIS-01, VIS-04]

duration: 12min
completed: 2026-03-23
---

# Phase 52 Plan 02: Backend DRAINING Lifecycle and Dispatch Diagnosis Summary

**DRAINING node state machine (drain/undrain endpoints, pull_work guard, heartbeat preservation, auto-offline transition) plus structured dispatch diagnosis for PENDING jobs via _node_is_eligible() helper**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-23T16:20:00Z
- **Completed:** 2026-03-23T16:32:00Z
- **Tasks:** 2
- **Files modified:** 5 (+ 1 created)

## Accomplishments

- DRAINING node lifecycle implemented end-to-end: drain/undrain PATCH endpoints, pull_work early return, heartbeat status preservation, auto-offline transition on last job completion
- `_node_is_eligible()` extracted as a static helper reused by both `pull_work` (replaces 40-line inline loop) and `get_dispatch_diagnosis` (no duplication)
- `GET /jobs/{guid}/dispatch-diagnosis` returns one of five structured reasons: `no_nodes_online`, `capability_mismatch`, `all_nodes_busy`, `pending_dispatch`, `target_node_unavailable`
- All 8 test_draining.py and 6 test_dispatch_diagnosis.py tests pass (14 total)

## Task Commits

1. **Task 1: DRAINING lifecycle in job_service.py and main.py** - `1d8a4a7` (feat)
2. **Task 2: Dispatch diagnosis endpoint** - `ca75079` (feat)

## Files Created/Modified

- `puppeteer/agent_service/services/job_service.py` - Added _node_is_eligible(), DRAINING guards in pull_work/receive_heartbeat, report_result auto-transition, get_dispatch_diagnosis()
- `puppeteer/agent_service/main.py` - Fixed list_nodes DRAINING guard, added PATCH drain/undrain endpoints, added GET dispatch-diagnosis endpoint
- `puppeteer/agent_service/db.py` - Added Job.target_node_id column
- `puppeteer/migration_v42.sql` - Documents DRAINING (no DDL) + Job.target_node_id ALTER TABLE
- `puppeteer/tests/test_draining.py` - Replaced 8 pytest.fail stubs with passing assertions
- `puppeteer/tests/test_dispatch_diagnosis.py` - Replaced 6 pytest.fail stubs with passing assertions

## Decisions Made

- `_node_is_eligible()` extracted as a single static method rather than keeping inline logic in pull_work. Both pull_work and get_dispatch_diagnosis now call it. Prevents eligibility logic drift.
- `Job.target_node_id` added to db.py because the dispatch diagnosis target_node_unavailable case requires it and it only existed on ScheduledJob previously.
- Concurrency limit defaults to 5 in `get_dispatch_diagnosis` (same as pull_work constant) since Node model has no `concurrency_limit` column.
- `receive_heartbeat` preserves DRAINING status but still updates `last_seen` — keeps node visible in list_nodes without premature freshness timeout.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added Job.target_node_id to db.py**
- **Found during:** Task 2 (implementing get_dispatch_diagnosis)
- **Issue:** Plan's `get_dispatch_diagnosis` logic references `job.target_node_id` but the Job ORM model only had that field on ScheduledJob, not Job itself
- **Fix:** Added `target_node_id: Mapped[Optional[str]]` to Job model in db.py; updated migration_v42.sql with ALTER TABLE DDL
- **Files modified:** puppeteer/agent_service/db.py, puppeteer/migration_v42.sql
- **Verification:** In-memory SQLite test DB picks up new column via create_all; all 6 diagnosis tests pass
- **Committed in:** 1d8a4a7 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed test factory _make_node to remove non-existent concurrency_limit**
- **Found during:** Task 1 (running test_draining.py)
- **Issue:** Stub's _make_node factory passed `concurrency_limit=2` to Node constructor but Node model has no such column, causing TypeError on every test
- **Fix:** Removed `concurrency_limit` from _make_node factory in both test files
- **Files modified:** puppeteer/tests/test_draining.py, puppeteer/tests/test_dispatch_diagnosis.py
- **Verification:** All 14 tests pass
- **Committed in:** ca75079 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both fixes necessary for the feature to work. No scope creep.

## Issues Encountered

- `HeartbeatPayload` requires `node_id` field — stub test omitted it. Added to test fixture.

## Next Phase Readiness

- PATCH /nodes/{id}/drain and /undrain are ready for the node detail drawer (Plan 03)
- GET /jobs/{guid}/dispatch-diagnosis is ready for the PENDING job callout component (Plan 04)
- _node_is_eligible() is ready as the shared eligibility oracle for future scheduling work

---
*Phase: 52-queue-visibility-node-drawer-and-draining*
*Completed: 2026-03-23*

## Self-Check: PASSED

All files verified present. Both task commits (1d8a4a7, ca75079) verified in git history.
