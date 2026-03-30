---
phase: 96-foundation
plan: "01"
subsystem: infra
tags: [apscheduler, postgres, sqlite, scheduler, safety, guards]

# Dependency graph
requires: []
provides:
  - IS_POSTGRES boolean constant exported from agent_service.db
  - APScheduler pinned to >=3.10,<4.0 in requirements.txt
  - AsyncIOScheduler global job_defaults (misfire_grace_time=60, coalesce=True, max_instances=1)
  - Runtime guard raising RuntimeError if APScheduler v4 detected at startup
  - SQLite dev-mode stderr warning on startup when not using Postgres
affects:
  - phase-97
  - phase-98
  - phase-99
  - any phase touching scheduler or job dispatch

# Tech tracking
tech-stack:
  added: []
  patterns:
    - IS_POSTGRES constant pattern for DB-conditional logic across services
    - APScheduler job_defaults centralized at constructor level (not per-job)
    - Startup version guards via importlib.metadata.version() + packaging.version.Version

key-files:
  created:
    - puppeteer/tests/test_foundation_phase96.py
  modified:
    - puppeteer/requirements.txt
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/services/scheduler_service.py
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/main.py

key-decisions:
  - "IS_POSTGRES uses startswith('postgresql') evaluated once at module import time — not a DB connection check"
  - "IS_POSTGRES test uses direct logic comparison rather than module reload to avoid asyncpg import in local dev"
  - "APScheduler job_defaults set at constructor level removes need for per-job misfire_grace_time arguments"

patterns-established:
  - "IS_POSTGRES pattern: import from db to conditionally branch on DB backend (used in Phase 97/98)"
  - "Startup version guard pattern: importlib.metadata.version() + packaging.version.Version comparison"

requirements-completed:
  - FOUND-01
  - FOUND-02
  - FOUND-03

# Metrics
duration: 3min
completed: "2026-03-30"
---

# Phase 96 Plan 01: Foundation Safety Prerequisites Summary

**APScheduler pinned to >=3.10,<4.0, IS_POSTGRES flag exported from db.py, and AsyncIOScheduler configured with global job_defaults — four startup guards making implicit constraints explicit**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-30T21:42:45Z
- **Completed:** 2026-03-30T21:46:00Z
- **Tasks:** 6
- **Files modified:** 5 modified, 1 created

## Accomplishments

- Pinned APScheduler to `>=3.10,<4.0` preventing silent v4 breakage
- Exported `IS_POSTGRES` boolean from `db.py`, available in both scheduler_service and job_service for Phase 97/98 use
- Configured `AsyncIOScheduler` with global `job_defaults` (misfire_grace_time=60, coalesce=True, max_instances=1), removing redundant per-job arguments
- Added runtime `RuntimeError` guard in lifespan if APScheduler v4 is detected
- Added SQLite dev-mode warning to stderr so engineers know SKIP LOCKED is not active
- All 7 phase-96 tests pass with zero regressions against the 145-pass baseline

## Task Commits

Each task was committed atomically:

1. **Task 96-01-01: Pin APScheduler in requirements.txt** - `cbb66b3` (chore)
2. **Task 96-01-02: Export IS_POSTGRES from db.py** - `6e50cea` (feat)
3. **Task 96-01-03: Configure AsyncIOScheduler job_defaults** - `5f57a8d` (feat)
4. **Task 96-01-04: Add IS_POSTGRES import to job_service.py** - `99ee3a0` (chore)
5. **Task 96-01-05: APScheduler guard and SQLite warning in lifespan** - `24bba25` (feat)
6. **Task 96-01-06: Write test_foundation_phase96.py** - `f3abee3` (test)

## Files Created/Modified

- `puppeteer/requirements.txt` - APScheduler pinned from bare `apscheduler` to `apscheduler>=3.10,<4.0`
- `puppeteer/agent_service/db.py` - Added `IS_POSTGRES: bool = DATABASE_URL.startswith("postgresql")` after DATABASE_URL definition
- `puppeteer/agent_service/services/scheduler_service.py` - IS_POSTGRES imported; AsyncIOScheduler constructor gets job_defaults; per-job misfire_grace_time removed from sync_scheduler
- `puppeteer/agent_service/services/job_service.py` - IS_POSTGRES added to db import for Phase 97/98 forward-compatibility
- `puppeteer/agent_service/main.py` - SQLite warning block after init_db(); APScheduler v4 version check before scheduler_service.start()
- `puppeteer/tests/test_foundation_phase96.py` - 7 tests covering all four success criteria (FOUND-01/02/03)

## Decisions Made

- `IS_POSTGRES` tests use direct string logic (`startswith("postgresql")`) rather than module reload — module reload would trigger asyncpg import which is unavailable in local dev environment (only in Docker). The logic is what matters, not live module state.
- Per-job `misfire_grace_time=60` removed from `sync_scheduler`'s `add_job()` call since it's now covered by `job_defaults`. This consolidates the default configuration in one place.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restructured IS_POSTGRES reload tests to avoid asyncpg import**
- **Found during:** Task 6 (test execution)
- **Issue:** `test_is_postgres_flag_true_for_postgresql` failed because `importlib.reload(db_mod)` with `postgresql+asyncpg://` URL triggered `asyncpg` import which is not installed in local dev venv (only in Docker containers)
- **Fix:** Replaced reload-based tests with direct logic tests that verify IS_POSTGRES uses `startswith("postgresql")` correctly by inspecting the module's DATABASE_URL constant. The plan explicitly anticipated this fallback: "If reload issues occur, restructure to inspect IS_POSTGRES by reading the DATABASE_URL string and applying startswith('postgresql') directly"
- **Files modified:** `puppeteer/tests/test_foundation_phase96.py`
- **Verification:** All 7 tests pass
- **Committed in:** `f3abee3` (Task 6 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - anticipated by plan)
**Impact on plan:** Zero scope change. Test restructure explicitly anticipated in plan instructions.

## Issues Encountered

None — plan executed cleanly within 3 minutes.

## Next Phase Readiness

- IS_POSTGRES now importable from `agent_service.db`, `agent_service.services.scheduler_service`, and `agent_service.services.job_service` — Phase 97 pool kwargs and Phase 98 SKIP LOCKED guard can proceed
- APScheduler v4 guard and version pin mean scheduler work in Phase 99 starts from a safe baseline
- Pre-existing test failures (108 of 253 tests) are unchanged — not caused by this plan

---
*Phase: 96-foundation*
*Completed: 2026-03-30*
