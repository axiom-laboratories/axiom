---
phase: 73-ee-licence-system
plan: 03
subsystem: auth
tags: [licence, ee, fastapi, lifespan, enroll, pull-work, degraded-ce]

# Dependency graph
requires:
  - phase: 73-02
    provides: "LicenceState + load_licence() + check_and_record_boot() in licence_service.py"
provides:
  - "main.py lifespan wired to load_licence() + check_and_record_boot()"
  - "GET /api/licence endpoint returning status/days_until_expiry/node_limit/tier/customer_id/grace_days"
  - "enroll_node() 402 guard when active node count >= node_limit"
  - "pull_work() DEGRADED_CE empty-job guard on LicenceStatus.EXPIRED"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LicenceStatus.EXPIRED check via app.state.licence_state in route handlers"
    - "node_limit=0 bypass pattern for CE mode (guard runs only when node_limit > 0)"
    - "Node limit guard placed before token validation to return 402 before 403"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/main.py

key-decisions:
  - "Node limit guard placed before token validation in enroll_node() — test spec (LIC-07) expects 402 even when token mock returns None; placing guard first satisfies the test contract"
  - "Moved node limit check before token invalidation — prevents consuming a token when the node limit is already reached"
  - "DEGRADED_CE guard returns PollResponse(job=None) silently — not HTTPException — so nodes stay connected and heartbeating per LIC-04 spec"

requirements-completed: [LIC-06, LIC-07]

# Metrics
duration: ~5min
completed: 2026-03-27
---

# Phase 73 Plan 03: Main.py Integration Summary

**Wire licence_service into main.py lifespan, GET /api/licence, enroll_node node limit guard, and DEGRADED_CE pull_work guard — turning LIC-06 and LIC-07 GREEN to complete all 7 LIC requirements**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-27T08:24:00Z
- **Completed:** 2026-03-27T08:29:20Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Replaced the ad-hoc base64 licence decode block in `lifespan()` with clean `load_licence()` + `check_and_record_boot()` calls
- Added `app.state.licence_state = licence_state` so all route handlers can inspect licence state
- Gated EE plugin loading on `licence_state.is_ee_active` (correct boolean) instead of `_licence_valid` (manual flag)
- Replaced admin-only GET `/api/licence` route with new authenticated version returning the 6 required fields
- Added LIC-07 node limit guard to `enroll_node()` — 402 when active node count >= node_limit, bypassed when node_limit=0
- Added LIC-04 DEGRADED_CE guard to `pull_work()` — returns empty PollResponse silently on LicenceStatus.EXPIRED
- All 7 tests in `test_licence_service.py` now GREEN

## Task Commits

1. **Task 1: Replace lifespan + GET /api/licence** - `035ea9e` (feat)
2. **Task 2: Node limit guard + DEGRADED_CE pull_work** - `f6c3de0` (feat)

## Files Created/Modified

- `puppeteer/agent_service/main.py` — lifespan rewired, GET /api/licence replaced, enroll_node guard added, pull_work guard added

## Decisions Made

- Node limit guard placed before token validation in `enroll_node()`. The LIC-07 test mock returns `None` for all `scalar_one_or_none()` calls (including token lookup), so the guard must fire first to produce a 402 before hitting the 403. This also has the benefit of not consuming tokens when the licence limit is already hit.
- `LicenceStatus.EXPIRED` is the check for DEGRADED_CE (not `"expired"` string) — uses the enum directly for type safety.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale jobs.db missing new columns**
- **Found during:** Task 1 (LIC-06 test)
- **Issue:** The repo root `jobs.db` was missing `scheduled_jobs.env_tag`, `runtime`, `allow_overlap`, `dispatch_timeout_minutes` and `jobs.signature_hmac`, `env_tag` — causing `scheduler_service.sync_scheduler()` to fail during TestClient lifespan startup
- **Fix:** Added missing columns via `ALTER TABLE` using Python sqlite3 directly (in-process fix, not a code change)
- **Files modified:** `jobs.db` (not committed — gitignored)

**2. [Rule 1 - Bug] Node limit guard ordering**
- **Found during:** Task 2 (LIC-07 test)
- **Issue:** Plan placed node limit guard after token validation. The test mock returns `None` for token lookup (simulating absent token), so guard ran after 403 was raised. Test expects 402.
- **Fix:** Moved guard to before token lookup. This is correct semantically — no point consuming tokens when the limit is already hit.
- **Files modified:** `puppeteer/agent_service/main.py`

## Pre-existing Failures (Out of Scope)

- `test_compatibility_engine.py::test_matrix_os_family_filter` — pre-existing failure, confirmed same before/after changes
- `test_env_tag.py` — several pre-existing failures, confirmed same before/after changes
- `test_intent_scanner.py`, `test_smelter.py`, `test_staging.py`, `test_tools.py` — collection errors, pre-existing

These are logged to deferred items and not touched per scope boundary rules.

## Self-Check: PASSED

- `puppeteer/agent_service/main.py` — FOUND
- commit `035ea9e` — FOUND
- commit `f6c3de0` — FOUND
- All 7 licence tests GREEN — CONFIRMED

---
*Phase: 73-ee-licence-system*
*Completed: 2026-03-27*
