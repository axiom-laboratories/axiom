---
phase: 31-environment-tags-cicd-dispatch
plan: 04
subsystem: api
tags: [env_tag, dispatch, job_service, pydantic, fastapi]

requires:
  - phase: 31-03
    provides: POST /api/dispatch route and DispatchRequest model
  - phase: 31-02
    provides: env_tag column on Job and Node DB models, HeartbeatPayload.env_tag
  - phase: 31-01
    provides: env_tag field on JobCreate model

provides:
  - "dispatch_job() passes payload as dict to JobCreate (not json.dumps string) — no Pydantic ValidationError at runtime"
  - "JobCreate model includes scheduled_job_id field — dispatch route can pass s_job.id without validation error"
  - "create_job() Job() constructor includes env_tag, max_retries, backoff_multiplier, timeout_minutes, scheduled_job_id — dispatched jobs persist all fields to DB"
  - "receive_heartbeat() else-branch Node() constructor includes env_tag=hb.env_tag — first-heartbeat nodes store env_tag, not NULL"

affects:
  - 32-dashboard-ui
  - ENVTAG-01
  - ENVTAG-04

tech-stack:
  added: []
  patterns:
    - "Direct dict pass to Pydantic model fields typed Dict — never json.dumps()"
    - "Job() constructor must mirror all Optional fields from JobCreate to avoid silent data loss"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/services/job_service.py

key-decisions:
  - "scheduled_job_id added to JobCreate as Optional[str] = None — dispatch route was already passing it, model needed to accept it"
  - "Direct attribute access (job_req.env_tag, etc.) used without hasattr guards — all fields are Optional on JobCreate with None defaults"

patterns-established:
  - "Gap-closure plan: three surgical one-line fixes, verified by targeted grep checks and test suite"

requirements-completed: [ENVTAG-01, ENVTAG-04]

duration: 8min
completed: 2026-03-18
---

# Phase 31 Plan 04: Environment Tags Bug Fix Summary

**Three surgical fixes: dispatch payload type (Pydantic ValidationError), Job() constructor missing env_tag/retry/timeout fields, and Node() first-heartbeat env_tag=NULL — all 11 ENVTAG tests pass**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-18T17:40:00Z
- **Completed:** 2026-03-18T17:48:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fixed `payload=json.dumps(payload_dict)` → `payload=payload_dict` so POST /api/dispatch no longer raises Pydantic v2 ValidationError at runtime
- Added `scheduled_job_id: Optional[str] = None` to `JobCreate` — the dispatch route was already passing it but the model silently rejected it
- Added `env_tag`, `max_retries`, `backoff_multiplier`, `timeout_minutes`, `scheduled_job_id` to `Job()` constructor in `create_job()` so these fields persist to DB on every dispatched job
- Added `env_tag=hb.env_tag` to `Node()` constructor in `receive_heartbeat()` else-branch so first-heartbeat node rows are never created with NULL env_tag

## Task Commits

Each task was committed atomically:

1. **Task 1 + 2: All three bug fixes** - `78c35e0` (fix)

**Plan metadata:** (final docs commit follows)

## Files Created/Modified
- `puppeteer/agent_service/main.py` - `payload=payload_dict` on line 1498
- `puppeteer/agent_service/models.py` - `scheduled_job_id: Optional[str] = None` added to `JobCreate`
- `puppeteer/agent_service/services/job_service.py` - `env_tag`, `max_retries`, `backoff_multiplier`, `timeout_minutes`, `scheduled_job_id` in `Job()` constructor; `env_tag=hb.env_tag` in `Node()` else-branch

## Decisions Made
- `scheduled_job_id` added to `JobCreate` (not just handled separately in `create_job`) — the dispatch route already passed it through `JobCreate()`, so the model must accept it; this also documents the field's intent at the API boundary
- Direct attribute access used without `hasattr` guards — all fields are declared `Optional[...] = None` on `JobCreate` so they always exist

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added scheduled_job_id to JobCreate model**
- **Found during:** Task 1 (reviewing models.py before editing)
- **Issue:** `dispatch_job()` was passing `scheduled_job_id=s_job.id` to `JobCreate()` constructor but `JobCreate` had no such field — Pydantic v2 would raise ValidationError (extra field rejected by default)
- **Fix:** Added `scheduled_job_id: Optional[str] = None` to `JobCreate` in models.py
- **Files modified:** `puppeteer/agent_service/models.py`
- **Verification:** Import succeeds; all 11 env_tag tests pass; no regression
- **Committed in:** 78c35e0 (combined task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: missing model field)
**Impact on plan:** Necessary for dispatch route to function; no scope creep. The plan noted "read models.py to confirm which fields exist" — this confirmed the gap.

## Issues Encountered
- 6 test files have pre-existing collection errors (`ModuleNotFoundError: No module named 'puppeteer.agent_service'` — tests import via wrong path). These are pre-existing and unrelated to this plan's changes. All Phase 29-31 functional tests pass cleanly.

## Next Phase Readiness
- ENVTAG-01, ENVTAG-02, and ENVTAG-04 requirements are now fully satisfied
- Phase 32 (Dashboard UI) can now use env_tag on nodes and jobs without NULL surprises
- POST /api/dispatch is runtime-correct end-to-end

---
*Phase: 31-environment-tags-cicd-dispatch*
*Completed: 2026-03-18*
