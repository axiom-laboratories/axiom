---
phase: 91-output-validation
plan: "91-01"
subsystem: api
tags: [validation, job-service, scheduler, pydantic, db]

requires:
  - phase: 90-job-script-versioning
    provides: job_definition_versions table and dispatch stamping pattern

provides:
  - validation_rules column on ScheduledJob DB table
  - failure_reason column on ExecutionRecord DB table
  - validation evaluation logic in job_service.process_result()
  - validation_rules serialized in dispatch payload
  - API models updated: JobDefinitionCreate, JobDefinitionResponse, JobDefinitionUpdate, ExecutionRecordResponse
  - migration_v45.sql for existing deployments
  - Full unit test suite for validation rule evaluation

affects: [92-output-validation-ui, future-alerting-phases]

tech-stack:
  added: []
  patterns:
    - "Validation evaluation extracts stdout from output_log before truncation to preserve full output"
    - "validation_rules stored as JSON string in DB, deserialized via field_validator on response model"
    - "Validation failures guard the retry block with not _validation_failed to ensure terminal FAILED"

key-files:
  created:
    - puppeteer/tests/test_output_validation.py
    - puppeteer/migration_v45.sql
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/services/scheduler_service.py

key-decisions:
  - "Migration file created as v45 (not v17 as plan specified) because migration_v17.sql already existed for a different phase"
  - "re module added as module-level import (not inline) since job_service.py had no prior import"
  - "Validation stdout extracted from report.output_log before truncation (consistent with stdout_text extraction later in same function)"
  - "Test file written with full real implementations from the stub step (not trivial pass stubs) since the pure helper function made tests concrete from the start"

requirements-completed: [VALD-01, VALD-02]

duration: 5min
completed: 2026-03-30
---

# Phase 91 Plan 91-01: Backend — Validation Logic, DB Schema, and API Models Summary

**Output validation delivered end-to-end: DB columns, dispatch stamping, process_result() evaluation with exit_code/stdout_regex/json_path rules, API model exposure, migration SQL, and 6 unit tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-30T09:40:43Z
- **Completed:** 2026-03-30T09:45:33Z
- **Tasks:** 8 (W0 + 01–07)
- **Files modified:** 6

## Accomplishments

- `ScheduledJob.validation_rules` and `ExecutionRecord.failure_reason` columns added to DB + migration SQL
- Three validation rule types implemented: `exit_code`, `stdout_regex`, `json_path`+`json_expected`
- Validation failures are terminal (FAILED, non-retriable) with `failure_reason` code stored in ExecutionRecord
- All four Pydantic models updated (`JobDefinitionCreate`, `JobDefinitionResponse`, `JobDefinitionUpdate`, `ExecutionRecordResponse`)
- `dispatch_scheduled_job()` stamps `validation_rules` from ScheduledJob into the job payload
- 6 unit tests all pass; zero new test regressions introduced

## Task Commits

Each task was committed atomically:

1. **Task W0: Create test stub file** - `9108443` (test)
2. **Task 91-01-01: Add DB columns** - `43d6868` (feat)
3. **Task 91-01-02: Update Pydantic models** - `2d0e9b7` (feat)
4. **Task 91-01-03: Stamp validation_rules in dispatch** - `88fd2a8` (feat)
5. **Task 91-01-04: Implement validation evaluation** - `6f54196` (feat)
6. **Task 91-01-05: Wire validation_rules through create/update routes** - `d359f59` (feat)
7. **Task 91-01-06: Migration SQL** - `c7741b1` (chore)

## Files Created/Modified

- `puppeteer/agent_service/db.py` - Added `validation_rules` to `ScheduledJob`, `failure_reason` to `ExecutionRecord`
- `puppeteer/agent_service/models.py` - Added fields + `deserialize_validation_rules` validator to 4 models
- `puppeteer/agent_service/services/job_service.py` - Added `re` import; validation evaluation block; `failure_reason` in ExecutionRecord constructor; retry guard
- `puppeteer/agent_service/services/scheduler_service.py` - Stamped `validation_rules` in dispatch payload; serialized in create/update handlers
- `puppeteer/tests/test_output_validation.py` - 6 unit tests covering all rule types, null-rules, no-retry, schema
- `puppeteer/migration_v45.sql` - ALTER TABLE SQL for existing PostgreSQL deployments

## Decisions Made

- Migration file named `migration_v45.sql` (plan said v17 but v17 already existed). Deviation rule 1 applied.
- `re` module added at module level (top of `job_service.py`) rather than inline in the validation block.
- Validation stdout computed directly from `report.output_log` before the scrubbing/truncation pipeline — this is correct because the secrets scrubbing loop mutates `output_log` entries in-place, and we want raw (unscrubbed) content for pattern matching. The later `stdout_text` variable used for storage is extracted from the *scrubbed* log.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Migration filename conflict — plan specified migration_v17.sql which already existed**
- **Found during:** Task 91-01-06 (Write migration SQL)
- **Issue:** `puppeteer/migration_v17.sql` already existed (Phase 4 operator_tags migration)
- **Fix:** Created `migration_v45.sql` (next sequential number)
- **Files modified:** `puppeteer/migration_v45.sql`
- **Verification:** File created with correct SQL content
- **Committed in:** `c7741b1`

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug)
**Impact on plan:** No scope change; all deliverables met. Migration file functionally identical to plan spec.

## Issues Encountered

None — all tasks executed cleanly. Pre-existing test failures (84 tests) were confirmed pre-existing and unrelated to this plan's changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend output validation complete. All must_haves delivered.
- For existing PostgreSQL deployments: `psql -f puppeteer/migration_v45.sql` before upgrading the agent container.
- Phase 91 plan 91-02 (if planned) or milestone complete for Phase 91 if this is the only plan.

---
*Phase: 91-output-validation*
*Completed: 2026-03-30*
