---
phase: 43-job-test-matrix
plan: "06"
subsystem: api
tags: [fastapi, exception-handling, http-422, job-routing]

requires:
  - phase: 43-01
    provides: POST /jobs route handler with HTTPException(422) from create_job()

provides:
  - "POST /jobs returns HTTP 422 (not 500) when no ONLINE node matches env_tag"
  - "HTTPException passthrough pattern in create_job route handler"

affects:
  - 43-VERIFICATION
  - verify_job_05_env_routing.py

tech-stack:
  added: []
  patterns:
    - "except HTTPException: raise — FastAPI pattern for propagating intended HTTP errors before generic except clause"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/main.py

key-decisions:
  - "except HTTPException: raise inserted before generic except in create_job() — standard FastAPI pattern; HTTPException is subclass of Exception so ordering matters"

patterns-established:
  - "FastAPI route handlers: place 'except HTTPException: raise' before any generic 'except Exception' clause to prevent HTTP error re-wrapping"

requirements-completed:
  - JOB-05

duration: 5min
completed: 2026-03-21
---

# Phase 43 Plan 06: HTTPException Passthrough in POST /jobs Summary

**Single two-line fix to `create_job()` route handler so HTTP 422 from job_service propagates to client instead of being re-wrapped as HTTP 500**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-21T20:50:00Z
- **Completed:** 2026-03-21T20:55:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Inserted `except HTTPException: raise` before the generic `except Exception as e` clause in the `create_job` route handler
- Rebuilt agent container and confirmed live stack returns HTTP 422 with structured `no_eligible_node` detail for unmatched `env_tag`
- Closes the gap that was causing `verify_job_05_env_routing.py` to fail even with nodes online

## Task Commits

Each task was committed atomically:

1. **Task 1: Add HTTPException passthrough to POST /jobs route handler** - `97664a4` (fix)
2. **Task 2: Rebuild agent and verify 422 response live** - no source change (rebuild + verification only)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `puppeteer/agent_service/main.py` - Added `except HTTPException: raise` before `except Exception as e` in `create_job()` at line 1026

## Decisions Made
- The `except HTTPException: raise` clause is placed immediately before `except Exception as e: raise HTTPException(status_code=500, detail=str(e))` — this is the standard FastAPI exception handling pattern. Since `HTTPException` is a subclass of `Exception`, without this ordering the generic clause always fires first, converting all intended 4xx errors to 500.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `secrets.env` not found at `puppeteer/secrets.env` — found at `mop_validation/secrets.env` instead. Used correct path for live verification. No impact on code changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `verify_job_05_env_routing.py` can now pass on a stack with no ONLINE node matching the requested env_tag
- Gap 1 from 43-VERIFICATION.md is closed
- Plan 43-07 (if any) may proceed

---
*Phase: 43-job-test-matrix*
*Completed: 2026-03-21*
