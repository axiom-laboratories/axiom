---
phase: 51-job-detail-resubmit-and-bulk-ops
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, pytest, httpx, bulk-ops, job-resubmit]

# Dependency graph
requires:
  - phase: 51-01
    provides: failing test stubs for resubmit and bulk endpoints

provides:
  - "POST /jobs/{guid}/resubmit endpoint with originating_guid traceability"
  - "POST /jobs/bulk-cancel endpoint for bulk cancellation"
  - "POST /jobs/bulk-resubmit endpoint for bulk resubmission"
  - "DELETE /jobs/bulk endpoint for bulk deletion of terminal-state jobs"
  - "originating_guid column on Job ORM model and JobResponse"
  - "BulkJobActionRequest and BulkActionResponse Pydantic models"
  - "All 8 Phase 51 test stubs implemented and passing"

affects: [51-03, 51-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "bulk endpoints placed BEFORE /{guid} routes to prevent 'bulk' being parsed as guid"
    - "_job_to_response() helper in main.py for ORM→JobResponse serialization"
    - "httpx AsyncClient.request('DELETE', ..., json=...) for DELETE with body in tests"
    - "get_current_user override for admin auth bypass in tests (not require_permission)"

key-files:
  created:
    - "puppeteer/agent_service/tests/test_job51_resubmit.py"
    - "puppeteer/agent_service/tests/test_job51_bulk.py"
    - "puppeteer/migration_v41.sql"
  modified:
    - "puppeteer/agent_service/db.py"
    - "puppeteer/agent_service/models.py"
    - "puppeteer/agent_service/main.py"

key-decisions:
  - "Bulk endpoints (/jobs/bulk-cancel, /jobs/bulk-resubmit, DELETE /jobs/bulk) placed before /jobs/{guid}/resubmit to avoid FastAPI matching 'bulk' as a guid path parameter"
  - "Test auth override uses get_current_user (not require_permission) since admin role bypasses all permission checks in require_permission factory"
  - "DELETE with request body uses auth_client.request('DELETE', url, json=...) due to httpx not supporting json kwarg on .delete() method"
  - "Migration v41.sql added for existing PostgreSQL deployments; SQLite dev/test handled by create_all"

patterns-established:
  - "Bulk ops: CANCELLABLE_STATES, RESUBMITTABLE_STATES, TERMINAL_STATES module-level sets for clarity"
  - "_job_to_response(job): helper function in main.py to build JobResponse from ORM object"

requirements-completed: [JOB-05, BULK-02, BULK-03, BULK-04]

# Metrics
duration: 15min
completed: 2026-03-23
---

# Phase 51 Plan 02: Resubmit and Bulk Ops Backend Summary

**Four new job management endpoints with originating_guid traceability: resubmit, bulk-cancel, bulk-resubmit, and bulk-delete — all 8 test stubs passing**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-23T14:07:31Z
- **Completed:** 2026-03-23T14:22:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `originating_guid` column to Job ORM model and `JobResponse` for resubmit traceability
- Added `BulkJobActionRequest` and `BulkActionResponse` Pydantic models
- Implemented 4 new endpoints: `POST /jobs/{guid}/resubmit`, `POST /jobs/bulk-cancel`, `POST /jobs/bulk-resubmit`, `DELETE /jobs/bulk`
- All 8 Phase 51 test stubs implemented and turned green (was 17 failures, now 9 pre-existing)
- Migration file `migration_v41.sql` for existing PostgreSQL deployments

## Task Commits

Each task was committed atomically:

1. **Task 1: Add originating_guid to DB model + response models + new Pydantic models** - `ff3b9f4` (feat)
2. **Task 2: Four new backend endpoints + implement test stubs** - `5ab3e31` (feat)
3. **Migration file** - `7447940` (chore)

**Plan metadata:** (final docs commit — created with SUMMARY.md)

## Files Created/Modified

- `puppeteer/agent_service/db.py` - Added `originating_guid` mapped column to Job ORM model
- `puppeteer/agent_service/models.py` - Added `originating_guid` to JobResponse; added BulkJobActionRequest and BulkActionResponse
- `puppeteer/agent_service/main.py` - 4 new endpoints, `_job_to_response()` helper, module-level state constants
- `puppeteer/agent_service/tests/test_job51_resubmit.py` - 4 tests for resubmit endpoint (404, 409, 200 FAILED, 200 DEAD_LETTER)
- `puppeteer/agent_service/tests/test_job51_bulk.py` - 4 tests for bulk ops (bulk-cancel, skip terminal, bulk-resubmit, bulk-delete)
- `puppeteer/migration_v41.sql` - ALTER TABLE for existing Postgres deployments

## Decisions Made

- Bulk endpoints placed before `/{guid}/resubmit` to prevent FastAPI routing ambiguity where "bulk" would match as a guid parameter
- `get_current_user` dependency overridden in tests (not `require_permission`) since admin role bypasses all RBAC checks
- `httpx.AsyncClient.request("DELETE", url, json=...)` used for DELETE-with-body since `.delete()` method doesn't accept `json` kwarg in the installed httpx version

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `httpx.AsyncClient.delete()` doesn't accept a `json` body parameter in the installed version. Fixed by using `auth_client.request("DELETE", path, json=...)` instead. Classified as a minor blocking issue (Rule 3) — fixed inline in test file.

## User Setup Required

For existing PostgreSQL deployments, run:
```sql
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS originating_guid VARCHAR;
```
See `puppeteer/migration_v41.sql`.

## Next Phase Readiness

- All 4 backend endpoints are live and tested
- Plan 03 can add the Job Detail slide-over UI component on top of these endpoints
- Plan 04 can add bulk action controls to the Jobs list view
- No blockers

---
*Phase: 51-job-detail-resubmit-and-bulk-ops*
*Completed: 2026-03-23*

## Self-Check: PASSED

All files confirmed present:
- puppeteer/agent_service/db.py — FOUND
- puppeteer/agent_service/models.py — FOUND
- puppeteer/agent_service/main.py — FOUND
- puppeteer/agent_service/tests/test_job51_resubmit.py — FOUND
- puppeteer/agent_service/tests/test_job51_bulk.py — FOUND
- puppeteer/migration_v41.sql — FOUND
- .planning/phases/51-job-detail-resubmit-and-bulk-ops/51-02-SUMMARY.md — FOUND

All commits confirmed present: ff3b9f4, 5ab3e31, 7447940
