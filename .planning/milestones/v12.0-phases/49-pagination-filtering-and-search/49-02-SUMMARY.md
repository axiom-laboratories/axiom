---
phase: 49-pagination-filtering-and-search
plan: "02"
subsystem: database
tags: [sqlalchemy, pydantic, job-model, pagination, migration]

# Dependency graph
requires:
  - phase: 49-01
    provides: Phase 49 context and research on cursor pagination and filtering strategy
provides:
  - Job.name and Job.created_by nullable columns in db.py
  - migration_v39.sql with three pagination indexes
  - PaginatedJobResponse(items, total, next_cursor) model in models.py
  - JobCreate.name and JobCreate.created_by optional fields
  - JobResponse.name, created_by, created_at, runtime optional fields
  - Scheduler auto-stamps name+created_by on cron-fired jobs
  - POST /jobs stamps created_by from authenticated user
affects:
  - 49-03
  - 49-04

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "model_copy(update=...) to override immutable Pydantic fields before service call"
    - "getattr(job_req, 'name', None) for safe optional attribute reads in service layer"
    - "Cursor-based pagination contract: next_cursor=None signals last page"

key-files:
  created:
    - puppeteer/migration_v39.sql
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/services/scheduler_service.py
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/main.py

key-decisions:
  - "PaginatedJobResponse defined in models.py (not job_service.py) so Plans 03 and 04 share a single import path"
  - "POST /jobs uses model_copy(update={'created_by': username}) to stamp submitter without breaking validation"
  - "Scheduler stamps name+created_by directly on Job(...) constructor (not via JobCreate) to avoid re-triggering model_validator"

patterns-established:
  - "Pagination contract: PaginatedJobResponse.next_cursor=None means no more pages"
  - "created_by stamped at API boundary (main.py route), not in service layer, to keep service testable without auth context"

requirements-completed:
  - SRCH-01
  - SRCH-04

# Metrics
duration: 10min
completed: 2026-03-22
---

# Phase 49 Plan 02: DB Schema + Model Contracts Summary

**Job.name + Job.created_by columns, PaginatedJobResponse contract, and scheduler auto-stamping — foundation for cursor pagination and 9-axis filtering in Plans 03 and 04**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-22T21:08:00Z
- **Completed:** 2026-03-22T21:18:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `name` and `created_by` nullable columns to the `Job` DB model, with three supporting indexes for pagination queries
- Created `migration_v39.sql` with `IF NOT EXISTS` guards covering existing Postgres deployments
- Introduced `PaginatedJobResponse` (items, total, next_cursor) as the authoritative return type for Plans 03 and 04 to build against
- Wired `scheduler_service` to auto-stamp `name=s_job.name` and `created_by=s_job.created_by` on every cron-fired job
- Updated `POST /jobs` route to stamp `created_by` from the authenticated user via `model_copy`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Job.name and Job.created_by to DB model and create migration** - `9bba873` (feat)
2. **Task 2: Update Pydantic models and wire scheduler auto-populate** - `6bd47ff` (feat)

## Files Created/Modified
- `puppeteer/agent_service/db.py` - Added `name` and `created_by` mapped columns to Job class
- `puppeteer/migration_v39.sql` - ALTER TABLE + 3 CREATE INDEX statements with IF NOT EXISTS guards
- `puppeteer/agent_service/models.py` - JobCreate gains name/created_by; JobResponse gains name/created_by/created_at/runtime; PaginatedJobResponse class added
- `puppeteer/agent_service/services/scheduler_service.py` - Job(...) constructor in execute_scheduled_job now stamps name and created_by
- `puppeteer/agent_service/services/job_service.py` - create_job persists name and created_by from job_req
- `puppeteer/agent_service/main.py` - POST /jobs stamps created_by=current_user.username via model_copy

## Decisions Made
- `PaginatedJobResponse` placed in `models.py` (not in `job_service.py`) so both Plans 03 and 04 share a single canonical import path without circular dependency risk.
- POST /jobs uses `model_copy(update={"created_by": current_user.username})` to inject the authenticated username without touching the validated Pydantic model directly.
- Scheduler stamps `name` and `created_by` directly in the `Job(...)` ORM constructor (bypassing JobCreate) to avoid re-triggering the model_validator which enforces runtime requirements.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test collection errors for EE-only tests (`test_foundry_mirror.py`, `test_intent_scanner.py`, `test_lifecycle_enforcement.py`, `test_smelter.py`, `test_staging.py`, `test_tools.py`) — these fail because EE-only models (`Blueprint`, etc.) are not in the CE `db.py`. Confirmed pre-existing by stash check. Not caused by this plan's changes.
- Pre-existing failures in `test_retry_wiring.py` and `test_trigger_service.py` — also EE-dependent, pre-existing.

## User Setup Required
None - no external service configuration required.

Apply migration to existing Postgres deployments:
```sql
-- puppeteer/migration_v39.sql
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS name VARCHAR;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_by VARCHAR;
CREATE INDEX IF NOT EXISTS ix_jobs_name ON jobs(name);
CREATE INDEX IF NOT EXISTS ix_jobs_created_by ON jobs(created_by);
CREATE INDEX IF NOT EXISTS ix_jobs_created_at_guid ON jobs(created_at DESC, guid DESC);
```

## Next Phase Readiness
- Plan 03 (list_jobs pagination + filtering) and Plan 04 (frontend) can now import `PaginatedJobResponse` from `models.py` directly
- `Job.created_by` and `Job.name` are available in the DB for all new jobs created after deployment
- The `ix_jobs_created_at_guid` composite index is ready for cursor-based pagination queries

---
*Phase: 49-pagination-filtering-and-search*
*Completed: 2026-03-22*
