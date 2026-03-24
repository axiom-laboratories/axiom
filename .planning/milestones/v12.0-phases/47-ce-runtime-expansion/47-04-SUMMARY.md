---
phase: 47-ce-runtime-expansion
plan: "04"
subsystem: api
tags: [fastapi, dispatch, task_type, runtime, job-scheduling]

# Dependency graph
requires:
  - phase: 47-03
    provides: Runtime dropdown wired into job submission form and POST body
provides:
  - Fixed /api/dispatch endpoint that accepts ScheduledJob dispatch without 422
  - Removal of dead run_python_script() method from node.py
  - Corrected task_type comment in db.py
affects:
  - 47-ce-runtime-expansion CI/CD dispatch path
  - Any integration test that calls POST /api/dispatch

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "getattr(obj, 'field', None) or default pattern for backward-compatible field access on ORM objects"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/main.py
    - puppets/environment_service/node.py
    - puppeteer/agent_service/db.py

key-decisions:
  - "Runtime derived via getattr(s_job, 'runtime', None) or 'python' — mirrors scheduler_service.py pattern exactly"
  - "runtime added to both payload_dict and as a top-level JobCreate kwarg for dual-path compatibility"

patterns-established:
  - "Dispatch pattern: always derive runtime from ScheduledJob, inject into payload_dict and JobCreate"

requirements-completed:
  - RT-04
  - RT-07

# Metrics
duration: 5min
completed: 2026-03-22
---

# Phase 47 Plan 04: CE Runtime Expansion — Dispatch Fix Summary

**Fixed /api/dispatch HTTP 422 blocker by switching task_type from 'python_script' to 'script' and injecting runtime from ScheduledJob; removed dead run_python_script() method from node.py; updated stale db.py comment**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-22T18:45:00Z
- **Completed:** 2026-03-22T18:50:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Unblocked the CI/CD dispatch path — POST /api/dispatch now creates jobs with task_type='script' and correct runtime
- Removed 31-line dead `run_python_script()` method from node.py that was never called from `execute_task`
- Updated stale `task_type` comment in db.py to reflect current valid values (script, web_task, file_download)
- All 7 runtime expansion tests remain GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix /api/dispatch and clean up anti-patterns** - `74d2cee` (fix)
2. **Task 2: Run test suite** - (no new files, tests passed as part of Task 1 verification)

## Files Created/Modified
- `puppeteer/agent_service/main.py` - derive runtime, add to payload_dict, change task_type to "script"
- `puppets/environment_service/node.py` - removed dead run_python_script() method (lines 521-551)
- `puppeteer/agent_service/db.py` - updated task_type inline comment

## Decisions Made
- Runtime derivation pattern `getattr(s_job, 'runtime', None) or 'python'` mirrors the exact approach already used in `scheduler_service.py` `execute_scheduled_job` — no invention needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The three changes were mechanical and the import check plus test suite confirmed correctness immediately.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 47 runtime expansion is now complete (plans 01–04 done)
- The full CI/CD dispatch path is functional: ScheduledJob → POST /api/dispatch → Job(task_type='script', runtime=...) → node execute_task
- Phase 46 tech debt / security / branding work can proceed; Phase 48 (DRAFT signing safety) is unblocked

---
*Phase: 47-ce-runtime-expansion*
*Completed: 2026-03-22*
