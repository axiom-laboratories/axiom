---
phase: 90-job-script-versioning
plan: "90-01"
subsystem: database, api
tags: [sqlalchemy, fastapi, pydantic, versioning, scheduler]

requires:
  - phase: 87-research-design
    provides: schema design for two-table versioning approach
provides:
  - JobDefinitionVersion ORM model with immutable version snapshots
  - migration_v44.sql for existing deployments
  - _create_version_snapshot helper auto-creating versions on create/update
  - definition_version_id stamped on Job rows at dispatch time
  - GET /jobs/definitions/{id}/versions and /{version_num} endpoints
affects:
  - 90-job-script-versioning (subsequent plans using version data)
  - frontend (version history display)

tech-stack:
  added: []
  patterns:
    - "Immutable version snapshots: new JobDefinitionVersion row on every create/update"
    - "Dispatch stamping: execute_scheduled_job queries latest signed version and sets FK on Job"
    - "Change summary: derived from field diff (script updated / schedule updated / tags updated / re-signed)"
    - "is_signed derived from final job status: ACTIVE = True, DRAFT/REVOKED = False"

key-files:
  created:
    - puppeteer/migration_v44.sql
    - .planning/phases/90-job-script-versioning/90-01-SUMMARY.md
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/services/scheduler_service.py
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/main.py

key-decisions:
  - "Version snapshot created atomically after create_job_definition commit (second commit in same request)"
  - "update_job_definition snapshot created before final commit (atomic with job mutation)"
  - "change_summary derived at snapshot time from update_req field diff; defaults to 'updated' if no specific fields changed"
  - "is_signed = True only when final job status will be ACTIVE; DRAFT/unsigned changes get is_signed=False"
  - "ConfigDict used for JobDefinitionVersionResponse; pre-existing models keep legacy class-based Config"

patterns-established:
  - "Version auto-increment: MAX(version_number) per job_def_id + 1 computed at write time"

requirements-completed:
  - VER-01
  - VER-02
  - VER-03

duration: 18min
completed: 2026-03-29
---

# Phase 90 Plan 01: DB Model, Migration, and Backend Versioning Logic Summary

**Immutable job definition version snapshots via new JobDefinitionVersion table, stamped at dispatch, with two read-only version API endpoints**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-29T23:45:00Z
- **Completed:** 2026-03-29T23:57:10Z
- **Tasks:** 6
- **Files modified:** 4

## Accomplishments
- Added `JobDefinitionVersion` ORM model with `UniqueConstraint(job_def_id, version_number)` and `definition_version_id` column on `Job`
- `migration_v44.sql` with IF NOT EXISTS guards for Postgres-safe existing deployment upgrades
- `_create_version_snapshot()` helper wired into both `create_job_definition` (version 1, is_signed=True) and `update_job_definition` (auto-increment, change_summary from field diff)
- `execute_scheduled_job` now stamps `definition_version_id` from the latest signed version at dispatch time
- `GET /jobs/definitions/{id}/versions` and `GET /jobs/definitions/{id}/versions/{version_num}` endpoints added, gated on `jobs:read`
- `JobDefinitionVersionResponse` Pydantic model with JSON target_tags parsing; `JobResponse` extended with `definition_version_id` and `definition_version_number`

## Task Commits

Each task was committed atomically:

1. **Task 90-01-01: Add JobDefinitionVersion model to db.py** - `1ac7339` (feat)
2. **Task 90-01-02: Write migration_v44.sql** - `004abe3` (feat)
3. **Task 90-01-03 + 90-01-05: _create_version_snapshot + service methods** - `276ce34` (feat)
4. **Task 90-01-04: Stamp definition_version_id at dispatch time** - `614f8f1` (feat)
5. **Task 90-01-06: Add version API endpoints and response model** - `42baed4` (feat)

## Files Created/Modified
- `puppeteer/agent_service/db.py` - Added `JobDefinitionVersion` model + `definition_version_id` on `Job`
- `puppeteer/migration_v44.sql` - Postgres migration: creates table, adds column, adds indexes
- `puppeteer/agent_service/services/scheduler_service.py` - `_create_version_snapshot` helper, create/update wiring, dispatch stamping, two new service methods
- `puppeteer/agent_service/models.py` - `JobDefinitionVersionResponse` model, `JobResponse` extended, `ConfigDict` import added
- `puppeteer/agent_service/main.py` - Two new version endpoints, import updated

## Decisions Made
- Version snapshot for `update_job_definition` happens before the final commit to ensure atomicity with job mutations
- `change_summary` is built by comparing `update_req` fields to the existing job at call time — works correctly because field mutations happen before snapshot
- `is_signed` is derived from the post-update final status: only `ACTIVE` → True; this means re-sign flows that set status=ACTIVE correctly mark the snapshot as signed
- Pre-existing `class Config` style kept on existing models (only `JobDefinitionVersionResponse` uses `ConfigDict` to avoid unnecessary churn)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tasks 03 and 05 committed together**
- **Found during:** Task 03 (adding _create_version_snapshot)
- **Issue:** Plan had tasks 03 and 05 as separate items but they're both modifications to the same `scheduler_service.py` and were added in a single editing pass
- **Fix:** Combined into one atomic commit covering both the helper and the public methods
- **Files modified:** puppeteer/agent_service/services/scheduler_service.py
- **Verification:** Import check confirmed all three methods present
- **Committed in:** 276ce34

---

**Total deviations:** 1 auto-fixed (1 blocking — tasks combined for atomic commit)
**Impact on plan:** No scope change. All required functionality delivered as specified.

## Issues Encountered

- `test_intent_scanner.py`, `test_lifecycle_enforcement.py`, `test_smelter.py`, `test_staging.py`, `test_tools.py` have pre-existing collection errors (import failures, unrelated to this plan). `test_job_templates.py` has 2 pre-existing assertion failures confirmed present before this plan's changes.

## Next Phase Readiness
- DB model, migration, service layer, and API endpoints all in place
- Ready for Phase 90 Plan 02 (frontend version history UI) — all required backend contracts are available
- Existing deployments need `migration_v44.sql` applied before upgrading

---
*Phase: 90-job-script-versioning*
*Completed: 2026-03-29*
