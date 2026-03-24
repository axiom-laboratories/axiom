---
phase: 52-queue-visibility-node-drawer-and-draining
plan: "03"
subsystem: api
tags: [fastapi, sqlalchemy, async, node-detail, job-service]

# Dependency graph
requires:
  - phase: 52-01
    provides: test scaffold (test_node_detail.py stubs with pytest.fail)
  - phase: 52-02
    provides: _node_is_eligible() static helper already extracted into JobService
provides:
  - JobService.get_node_detail() compound query method
  - GET /nodes/{node_id}/detail FastAPI endpoint
affects:
  - 52-05 (Node drawer frontend will consume this endpoint)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - compound-query service method returns dict with running_job, eligible_pending_jobs, recent_history, capabilities
    - eligibility reuse: _node_is_eligible() shared between pull_work, get_node_detail, and get_dispatch_diagnosis

key-files:
  created: []
  modified:
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/main.py
    - puppeteer/tests/test_node_detail.py

key-decisions:
  - "get_node_detail evaluates first 100 PENDING jobs via Python loop (not SQL subquery) to reuse _node_is_eligible without duplicating logic; caps result at 50"
  - "GET /nodes/{node_id}/detail placed before PATCH /nodes/{node_id} to prevent FastAPI routing ambiguity on /detail path segment"
  - "job_summary helper uses getattr for name/runtime fields for forward compatibility"
  - "concurrency_limit removed from _make_node test helper — field not in Node ORM model (only in migration SQL)"

patterns-established:
  - "Compound node detail: four focused queries, no joins, capped eligible list"

requirements-completed:
  - VIS-03

# Metrics
duration: 8min
completed: 2026-03-23
---

# Phase 52 Plan 03: Node Detail Aggregation Endpoint Summary

**JobService.get_node_detail() and GET /nodes/{id}/detail endpoint delivering running job, 50-capped eligible pending jobs, 24h history, and capabilities in a single response**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-23T16:25:00Z
- **Completed:** 2026-03-23T16:33:00Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Implemented `JobService.get_node_detail()` using four focused async queries (no joins)
- Eligible pending jobs capped at 50 by evaluating first 100 PENDING and filtering via `_node_is_eligible()` helper — no eligibility logic duplication
- Recent history filtered to jobs completed on this node in the past 24 hours
- `GET /nodes/{node_id}/detail` endpoint added before `PATCH /nodes/{node_id}` to avoid FastAPI routing ambiguity
- All 6 test_node_detail.py stubs pass with actual assertions replacing pytest.fail()

## Task Commits

1. **Task 1: Implement get_node_detail + GET /nodes/{id}/detail** - `e24c614` (feat)

## Files Created/Modified
- `puppeteer/agent_service/services/job_service.py` - Added `get_node_detail()` static async method (57 lines)
- `puppeteer/agent_service/main.py` - Added `GET /nodes/{node_id}/detail` endpoint
- `puppeteer/tests/test_node_detail.py` - Implemented all 6 stubs with full assertions

## Decisions Made
- `get_node_detail` evaluates first 100 PENDING jobs in Python (not pure SQL) to reuse `_node_is_eligible()` without duplicating the tag/env/capability matching logic
- `GET /nodes/{node_id}/detail` placed before `PATCH /nodes/{node_id}` to prevent FastAPI from matching `/detail` as a wildcard `{node_id}` value
- `job_summary` uses `getattr` for `name` and `runtime` fields to handle any schema evolution gracefully

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed concurrency_limit from _make_node test factory**
- **Found during:** Task 1 (implementing tests)
- **Issue:** `concurrency_limit` was passed to `Node()` ORM constructor but the field is not in the `Node` SQLAlchemy model (it was added via migration SQL only, never added to the ORM class)
- **Fix:** Removed `concurrency_limit` parameter from `_make_node()` helper
- **Files modified:** `puppeteer/tests/test_node_detail.py`
- **Verification:** All 6 tests pass after fix
- **Committed in:** e24c614

**2. [Rule 1 - Bug] Added completed_at to Job() constructor in _make_job factory**
- **Found during:** Task 1 (test_node_detail_recent_history was returning 0 results)
- **Issue:** `_make_job()` accepted `completed_at` as a parameter but did not pass it through to the `Job()` ORM constructor, so all COMPLETED jobs had `completed_at=None` and were excluded by the `>= cutoff` filter
- **Fix:** Added `completed_at=completed_at` to the `Job()` constructor call
- **Files modified:** `puppeteer/tests/test_node_detail.py`
- **Verification:** test_node_detail_recent_history now passes (3 recent jobs found, 1 old excluded)
- **Committed in:** e24c614

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
- Plan 52-02 was not yet summarized but its code changes (`_node_is_eligible`, DRAINING logic) were already applied to the codebase — `get_node_detail` could be implemented directly against the existing helper without issue.
- Pre-existing collection errors in `test_foundry_mirror.py`, `test_tools.py`, `test_lifecycle_enforcement.py` etc. (importing `Blueprint` not yet in db.py) are Phase 52 Wave 3 stubs — out of scope and left untouched.

## Self-Check: PASSED

- `puppeteer/agent_service/services/job_service.py` — FOUND
- `puppeteer/agent_service/main.py` — FOUND
- `puppeteer/tests/test_node_detail.py` — FOUND
- Commit `e24c614` — FOUND
- `pytest tests/test_node_detail.py` — 6 PASSED

## Next Phase Readiness
- VIS-03 backend complete: `GET /nodes/{id}/detail` returns the compound payload
- Plan 52-05 (Node drawer frontend) can consume this endpoint
- Plans 52-02 (draining/dispatch-diagnosis) and 52-04 (queue snapshot endpoint) are still pending

---
*Phase: 52-queue-visibility-node-drawer-and-draining*
*Completed: 2026-03-23*
