---
phase: 43-job-test-matrix
plan: 01
subsystem: api
tags: [fastapi, job-dispatch, validation, http-errors, job-service]

# Dependency graph
requires:
  - phase: 42-ee-validation-pass
    provides: working EE stack with node enrollment and job execution pipeline
provides:
  - dispatch_job() with REVOKED guard returning HTTP 409 (job_definition_revoked)
  - create_job() with no-eligible-node pre-flight returning HTTP 422 (no_eligible_node)
affects: [43-job-test-matrix, phase-44, mop_validation job test scripts]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guard ordering in dispatch_job(): 404 (not found) -> 409 (revoked) -> proceed"
    - "create_job() pre-flight: validate ONLINE node availability before constructing Job ORM object"
    - "Inline HTTPException import inside service method (matches existing pattern in job_service.py)"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/services/job_service.py

key-decisions:
  - "HTTP 409 (Conflict) used for REVOKED job definition dispatch — semantically correct for resource-in-conflicting-state"
  - "HTTP 422 (Unprocessable Entity) used for no-eligible-node — matches FastAPI validation error convention"
  - "no-eligible-node check only fires when env_tag is truthy — jobs with no env_tag pass through unchanged (any node can pick them up)"

patterns-established:
  - "dispatch_job guard order: existence check (404) then status check (409) before any business logic"
  - "Service-layer pre-flight validations raise HTTPException inline using local import (consistent with existing job_service.py dependency validation pattern)"

requirements-completed:
  - JOB-05
  - JOB-09

# Metrics
duration: 3min
completed: 2026-03-21
---

# Phase 43 Plan 01: Job Test Matrix Backend Patches Summary

**HTTP 409 REVOKED guard added to dispatch_job() and HTTP 422 no-eligible-node pre-flight added to create_job(), enabling JOB-05 and JOB-09 validation assertions to pass**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-21T20:02:12Z
- **Completed:** 2026-03-21T20:05:00Z
- **Tasks:** 3 of 3
- **Files modified:** 2

## Accomplishments

- `POST /api/dispatch` now returns HTTP 409 with `error=job_definition_revoked` when the referenced job definition has status REVOKED — previously silently created a PENDING job
- `create_job()` in `job_service.py` now returns HTTP 422 with `error=no_eligible_node` when env_tag is specified but no ONLINE node with that tag exists — previously created an unroutable PENDING job
- Both patches verified against live Docker stack: 404 on unknown dispatch ID (route live), 422 on NONEXISTENT env_tag (guard active)

## Task Commits

Each task was committed atomically:

1. **Task 1: REVOKED guard in dispatch_job()** - `65c76b1` (fix)
2. **Task 2: no-eligible-node validation in create_job()** - `232d35b` (fix)
3. **Task 3: Rebuild + smoke-test** — no source files, verified via live stack (no commit needed)

## Files Created/Modified

- `puppeteer/agent_service/main.py` — added `if s_job.status == "REVOKED": raise HTTPException(409, ...)` inside `dispatch_job()` after the 404 check and before env_tag resolution
- `puppeteer/agent_service/services/job_service.py` — added ONLINE node availability pre-flight at start of `create_job()` when `env_tag` is set

## Decisions Made

- HTTP 409 (Conflict) chosen for REVOKED guard: semantically correct — resource exists but is in a state that conflicts with the requested operation
- HTTP 422 chosen for no-eligible-node: matches FastAPI's unprocessable entity convention; the request is structurally valid but cannot be fulfilled given current cluster state
- No-eligible-node check is conditional on `env_tag` being truthy — jobs submitted without an env_tag deliberately target any available node and must not be blocked

## Deviations from Plan

None — plan executed exactly as written. The secrets.env file was found at `mop_validation/secrets.env` rather than `puppeteer/secrets.env` (smoke test only), which is consistent with project memory and did not affect any source changes.

## Issues Encountered

- `puppeteer/secrets.env` not present at expected path during smoke test; found at `mop_validation/secrets.env` instead. Admin JWT acquisition succeeded from that path. No impact on implementation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- JOB-05 and JOB-09 assertions now have the backend responses they require
- `mop_validation` job test scripts (verify_job_05_*.py, verify_job_09_*.py) can now run against the live stack and expect HTTP 409 / 422 respectively
- No schema changes, no migrations needed

---
*Phase: 43-job-test-matrix*
*Completed: 2026-03-21*
