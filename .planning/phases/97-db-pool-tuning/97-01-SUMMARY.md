---
phase: 97-db-pool-tuning
plan: "97-01"
subsystem: database
tags: [asyncpg, sqlalchemy, postgres, connection-pool, environment-config]

requires:
  - phase: 96-foundation
    provides: IS_POSTGRES flag importable from db module

provides:
  - asyncpg connection pool configured for 20 concurrent polling nodes
  - _pool_kwargs dict exported from db module (empty for SQLite, populated for Postgres)
  - ASYNCPG_POOL_SIZE env var knob with tuning formula documentation
  - puppeteer/.env.example template with all known env vars

affects: [98-dispatch-skip-locked, 99-scheduler-hardening, 100-docs-migration]

tech-stack:
  added: []
  patterns:
    - "Conditional pool kwargs: _pool_kwargs dict built at module import time, gated on IS_POSTGRES"
    - "Engine receives **_pool_kwargs: zero-arg SQLite stays unaffected, Postgres gets full pool config"

key-files:
  created:
    - puppeteer/tests/test_pool_phase97.py
    - puppeteer/.env.example
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/compose.server.yaml

key-decisions:
  - "_pool_kwargs dict is module-level (not function-scoped) so it can be imported by tests without triggering engine creation side effects"
  - "max_overflow=10 hardcoded (not env-var): keeps tuning surface minimal — pool_size is the only operator knob"
  - "pool_pre_ping=True: validates connections on checkout, prevents stale connection errors after db restart"

requirements-completed:
  - POOL-01
  - POOL-02
  - POOL-03
  - POOL-04

duration: 12min
completed: 2026-03-30
---

# Phase 97 Plan 01: asyncpg Pool Configuration Summary

**asyncpg pool right-sized for 20 concurrent nodes via conditional `_pool_kwargs` in `db.py`, with `ASYNCPG_POOL_SIZE` env-var knob, compose passthrough, and `.env.example` documenting the tuning formula**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-30T22:05:00Z
- **Completed:** 2026-03-30T22:17:00Z
- **Tasks:** 4 (Wave 0 stub + 3 production tasks)
- **Files modified:** 4

## Accomplishments

- `db.py` now exports `_pool_kwargs` dict — empty for SQLite (no change to existing dev behaviour), populated for Postgres with `pool_size=20`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=300`, `pool_pre_ping=True`
- `ASYNCPG_POOL_SIZE` env var controls `pool_size` at module import time; defaults to `"20"`
- `compose.server.yaml` agent block passes `ASYNCPG_POOL_SIZE=${ASYNCPG_POOL_SIZE:-20}` so operators can tune without editing compose
- `puppeteer/.env.example` created — comprehensive template covering all known env vars with inline comments and tuning formula
- All 9 tests in `test_pool_phase97.py` pass; zero regressions (6 pre-existing collection errors confirmed not introduced by this plan)

## Task Commits

1. **Wave 0 — test stubs** - `59b77a7` (test)
2. **Task 97-01-01 — db.py pool kwargs** - `2d70372` (feat)
3. **Task 97-01-02 — compose.server.yaml** - `7b9b2e0` (feat)
4. **Task 97-01-03 — .env.example** - `6cf780b` (docs)

## Files Created/Modified

- `puppeteer/agent_service/db.py` — added `_pool_kwargs` dict and `**_pool_kwargs` spread into `create_async_engine()`
- `puppeteer/compose.server.yaml` — added `ASYNCPG_POOL_SIZE=${ASYNCPG_POOL_SIZE:-20}` to agent environment block
- `puppeteer/.env.example` — new file: comprehensive env var template with inline comments
- `puppeteer/tests/test_pool_phase97.py` — new file: 9 tests covering POOL-01 through POOL-04

## Decisions Made

- `_pool_kwargs` is module-level (not function-scoped) so tests can import it without triggering engine creation or asyncpg import errors in SQLite test environments
- `max_overflow=10` is hardcoded, not an env var — keeps the operator-facing tuning surface minimal (pool_size is the only knob)
- `pool_pre_ping=True` included to guard against stale connections after db service restarts

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. The 6 pre-existing collection errors in `test_foundry_mirror.py`, `test_intent_scanner.py`, `test_lifecycle_enforcement.py`, `test_smelter.py`, `test_staging.py`, and `test_tools.py` were confirmed to preexist before this plan's changes (verified via `git stash` regression check).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Phase 97 Plan 01 complete. Phase 97 has one plan; phase is now complete.
Ready for Phase 98 (dispatch SKIP LOCKED).

---
*Phase: 97-db-pool-tuning*
*Completed: 2026-03-30*

## Self-Check: PASSED

- `puppeteer/tests/test_pool_phase97.py` exists on disk: YES
- `puppeteer/.env.example` exists on disk: YES
- `puppeteer/agent_service/db.py` modified: YES (contains `_pool_kwargs`)
- `puppeteer/compose.server.yaml` modified: YES (contains `ASYNCPG_POOL_SIZE`)
- All 9 tests green: YES
- `git log --oneline --all --grep="97-01"` returns ≥1 commit: YES (4 commits)
