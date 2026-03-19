---
phase: 31-environment-tags-cicd-dispatch
plan: 03
subsystem: api
tags: [fastapi, cicd, dispatch, env-tag, jobs]

# Dependency graph
requires:
  - phase: 31-01
    provides: DispatchRequest/DispatchResponse/DispatchStatusResponse models, env_tag DB columns
  - phase: 31-02
    provides: env_tag wiring in pull_work, heartbeat, job_service, scheduler_service

provides:
  - POST /api/dispatch route — creates a Job from a ScheduledJob definition with env_tag override
  - GET /api/dispatch/{job_guid}/status route — structured poll endpoint with is_terminal field
  - _TERMINAL_STATUSES constant in main.py for shared terminal state checking
affects:
  - phase-32-dashboard-ui
  - any CI/CD pipeline using dispatch API

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PUBLIC_URL env var fallback to request.base_url for poll_url construction in containerised environments"
    - "Machine-readable 404 JSON body pattern: detail dict with error key + resource identifier"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/main.py

key-decisions:
  - "poll_url built with PUBLIC_URL env var fallback to request.base_url — avoids localhost URLs in Docker where base_url is the container-internal address"
  - "audit() called with User object (not username string) per actual function signature — plan interface snippet showed username= kwarg which does not match real def"
  - "Both tasks implemented in single commit — routes are tightly coupled (POST creates, GET polls) and test coverage was already satisfied by Plan 01 model tests"
  - "_TERMINAL_STATUSES constant defined at module level in main.py — co-located with routes that use it, avoids import from job_service"

patterns-established:
  - "CI/CD Dispatch OpenAPI tag: all dispatch routes use tags=['CI/CD Dispatch'] for grouped API reference"
  - "Machine-readable 404: detail is a dict with error string + resource identifier (not a plain string)"

requirements-completed:
  - ENVTAG-04

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 31 Plan 03: CI/CD Dispatch Routes Summary

**POST /api/dispatch and GET /api/dispatch/{job_guid}/status added to main.py, closing ENVTAG-04 and completing the CI/CD dispatch API surface**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T17:31:26Z
- **Completed:** 2026-03-18T17:34:38Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- POST /api/dispatch: dispatches a job from a scheduled job definition, supports env_tag override, returns DispatchResponse with poll_url built using PUBLIC_URL env var fallback
- GET /api/dispatch/{job_guid}/status: returns DispatchStatusResponse with is_terminal derived from _TERMINAL_STATUSES; exit_code from most recent ExecutionRecord
- Both routes audited, permission-gated (jobs:write / jobs:read), and tagged CI/CD Dispatch in OpenAPI
- All 11 test_env_tag.py tests pass; full suite unchanged from baseline (12 pre-existing isolation failures unrelated to this plan)

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: POST /api/dispatch and GET /api/dispatch/{job_guid}/status** - `4390a64` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `puppeteer/agent_service/main.py` - Added _TERMINAL_STATUSES constant, POST /api/dispatch route handler, GET /api/dispatch/{job_guid}/status route handler; added DispatchRequest/DispatchResponse/DispatchStatusResponse to models import

## Decisions Made
- poll_url uses `os.getenv("PUBLIC_URL", str(request.base_url).rstrip("/"))` — avoids localhost URLs in Docker containers where `request.base_url` resolves to the internal container address
- audit() signature is `audit(db, user: User, action, resource_id, detail: dict)` — the plan's interface snippet showed `username=` kwarg which does not match the actual function. Used real signature.
- Both routes committed together as they form a coherent unit (dispatch creates, status polls)
- _TERMINAL_STATUSES defined as module-level constant adjacent to routes for clarity

## Deviations from Plan

**1. [Rule 1 - Bug] audit() call signature corrected**
- **Found during:** Task 1 (implement POST /api/dispatch)
- **Issue:** Plan interface snippet showed `audit(db, username=current_user.username, ...)` but actual function signature is `def audit(db, user: User, action, resource_id, detail: dict)` — kwarg form would raise TypeError at runtime
- **Fix:** Used correct positional form: `audit(db, current_user, "dispatch_job", job_guid, {...})`
- **Files modified:** puppeteer/agent_service/main.py
- **Verification:** All 11 test_env_tag.py tests pass
- **Committed in:** 4390a64

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan interface snippet)
**Impact on plan:** Minor — no scope change, just corrected the audit() call to match actual implementation.

## Issues Encountered
- Pre-existing test ordering failures in test_device_flow.py and test_compatibility_engine.py (12 tests) appear when running full suite but pass in isolation — confirmed to be pre-existing baseline issue unrelated to this plan (verified via git stash comparison).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ENVTAG-04 complete — CI/CD dispatch API surface fully implemented
- Phase 31 (Environment Tags + CI/CD Dispatch) is now complete: ENVTAG-01, ENVTAG-02, ENVTAG-04 all satisfied
- Phase 32 (Dashboard UI) can now build on env_tag columns, dispatch routes, and attestation endpoints from phases 29-31

## Self-Check: PASSED

- FOUND: 31-03-SUMMARY.md
- FOUND: commit 4390a64
- FOUND: 3 dispatch route references in main.py
- FOUND: 2 CI/CD Dispatch OpenAPI tags in main.py

---
*Phase: 31-environment-tags-cicd-dispatch*
*Completed: 2026-03-18*
