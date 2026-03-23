---
phase: 51-job-detail-resubmit-and-bulk-ops
plan: 01
subsystem: testing
tags: [pytest, vitest, radix-ui, checkbox, migration, tdd, stubs]

# Dependency graph
requires: []
provides:
  - migration_v40.sql with originating_guid ALTER TABLE for Postgres (IF NOT EXISTS) and SQLite comment
  - ui/checkbox.tsx Radix-backed Checkbox component with @radix-ui/react-checkbox
  - 4 failing pytest stubs for resubmit endpoint (test_job51_resubmit.py)
  - 4 failing pytest stubs for bulk endpoints (test_job51_bulk.py)
  - 3 it.todo stubs in Jobs.test.tsx for BULK-01 checkbox/bulk-bar behaviour
affects: [51-02, 51-03, 51-04]

# Tech tracking
tech-stack:
  added: ["@radix-ui/react-checkbox ^1.1.x"]
  patterns:
    - "Wave 0 stub convention: pytest.fail('not implemented') as first body line — tests collected and fail without import errors"
    - "Frontend stubs use it.todo() — vitest reports them as pending/todo, visible in output"

key-files:
  created:
    - puppeteer/migration_v40.sql
    - puppeteer/dashboard/src/components/ui/checkbox.tsx
    - puppeteer/agent_service/tests/test_job51_resubmit.py
    - puppeteer/agent_service/tests/test_job51_bulk.py
  modified:
    - puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx
    - puppeteer/dashboard/package.json
    - puppeteer/dashboard/package-lock.json

key-decisions:
  - "it.todo() chosen for BULK-01 frontend stubs (consistent with plan spec) — vitest marks as todo not skip"
  - "@radix-ui/react-checkbox installed via npm --save since it was absent from package.json"
  - "pytest.fail('not implemented') as first body line (not after awaits) — consistent with Phase 49 Wave 0 convention"

patterns-established:
  - "Wave 0 scaffold pattern: all test stubs fail immediately, no implementation logic"
  - "Migration SQL uses IF NOT EXISTS guard for Postgres + comment for SQLite manual path"

requirements-completed: [JOB-05, BULK-01, BULK-02, BULK-03, BULK-04]

# Metrics
duration: 3min
completed: 2026-03-23
---

# Phase 51 Plan 01: Wave 0 Scaffold Summary

**Migration SQL for originating_guid column, Radix checkbox component, and 11 failing test stubs establishing the Phase 51 resubmit + bulk-ops contract**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-23T14:06:47Z
- **Completed:** 2026-03-23T14:09:17Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- migration_v40.sql adds `originating_guid VARCHAR` to jobs table (Postgres IF NOT EXISTS guard, SQLite comment)
- ui/checkbox.tsx created as Radix-backed shadcn-pattern Checkbox with @radix-ui/react-checkbox installed
- 8 backend stubs across two test files — all fail with pytest.fail("not implemented"), zero import errors
- 3 it.todo frontend stubs in Jobs.test.tsx — vitest reports them as todo/pending, not passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration SQL + Checkbox component** - `374c3f8` (chore)
2. **Task 2: Backend test stubs for resubmit and bulk endpoints** - `9b77863` (test)
3. **Task 3: Frontend test stubs for BULK-01 checkbox and bulk action bar** - `49ea107` (test)

## Files Created/Modified
- `puppeteer/migration_v40.sql` - ALTER TABLE jobs ADD COLUMN IF NOT EXISTS originating_guid VARCHAR
- `puppeteer/dashboard/src/components/ui/checkbox.tsx` - Radix Checkbox wrapper (shadcn pattern)
- `puppeteer/agent_service/tests/test_job51_resubmit.py` - 4 pytest.fail stubs for resubmit endpoint (JOB-05)
- `puppeteer/agent_service/tests/test_job51_bulk.py` - 4 pytest.fail stubs for bulk endpoints (BULK-02/03/04)
- `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx` - 3 it.todo stubs for BULK-01 checkbox/bulk-bar
- `puppeteer/dashboard/package.json` - added @radix-ui/react-checkbox dependency
- `puppeteer/dashboard/package-lock.json` - updated lockfile

## Decisions Made
- `it.todo()` used for frontend stubs per plan spec — vitest marks as pending, not error
- `@radix-ui/react-checkbox` installed via `npm install --save` (was absent from package.json)
- pytest.fail as first body line (Wave 0 convention from Phase 49)

## Deviations from Plan

**1. [Rule 3 - Blocking] Installed missing @radix-ui/react-checkbox package**
- **Found during:** Task 1 (Checkbox component creation)
- **Issue:** @radix-ui/react-checkbox was not in package.json — needed before creating checkbox.tsx
- **Fix:** Ran `npm install @radix-ui/react-checkbox --save` in puppeteer/dashboard
- **Files modified:** puppeteer/dashboard/package.json, puppeteer/dashboard/package-lock.json
- **Verification:** package.json now includes @radix-ui/react-checkbox; checkbox.tsx imports cleanly
- **Committed in:** 374c3f8 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required to create checkbox.tsx. No scope creep.

## Issues Encountered
None beyond the missing package dependency handled above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Wave 0 artifacts ready for Plan 02 (resubmit endpoint implementation) and Plan 03 (bulk endpoints)
- Plan 04 can convert the 3 it.todo stubs to real assertions once the checkbox column exists
- migration_v40.sql is safe to apply to the production DB at any point before Plan 02 runs

---
*Phase: 51-job-detail-resubmit-and-bulk-ops*
*Completed: 2026-03-23*
