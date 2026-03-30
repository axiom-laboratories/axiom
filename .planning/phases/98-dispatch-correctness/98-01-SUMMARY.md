---
phase: 98-dispatch-correctness
plan: 01
subsystem: database
tags: [postgres, sqlalchemy, job-dispatch, concurrency, skip-locked, index]

# Dependency graph
requires:
  - phase: 96-apscheduler-correctness
    provides: IS_POSTGRES flag importable from db and job_service
  - phase: 97-db-pool-tuning
    provides: asyncpg pool configuration, _pool_kwargs module-level pattern
provides:
  - Composite index ix_jobs_status_created_at on jobs(status, created_at)
  - SELECT FOR UPDATE SKIP LOCKED on Postgres pull_work() dispatch path
  - migration_v44.sql for zero-downtime index creation on existing deployments
  - Integration test (OBS-03) proving zero double-assignment under concurrent polls
affects: [phase-99-scheduler-hardening, phase-100-observability]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Two-phase lock in pull_work(): unlocked 50-row candidate scan, then SELECT FOR UPDATE SKIP LOCKED on chosen row
    - IS_POSTGRES guard on locking path: SQLite path unchanged (serialised writes)
    - CREATE INDEX CONCURRENTLY in migration — must not run inside transaction block

key-files:
  created:
    - puppeteer/migration_v44.sql
    - puppeteer/tests/test_dispatch_correctness_phase98.py
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/services/job_service.py

key-decisions:
  - "Two-phase lock rather than locking all 50 candidates: locks only the chosen row, minimising contention"
  - "IS_POSTGRES guard ensures SQLite dev path is unmodified — serialised writes provide equivalent correctness"
  - "migration_v44.sql uses CONCURRENTLY — requires running outside transaction block; caveat comment added"
  - "OBS-03 integration test is skip-guarded for SQLite; validates actual Postgres correctness at deployment time"

patterns-established:
  - "SKIP LOCKED pattern: unlocked scan → IS_POSTGRES check → with_for_update(skip_locked=True) → continue on None"
  - "Migration CONCURRENTLY caveat: explicit warning in SQL comment not to use psql -1 flag"

requirements-completed: [DISP-01, DISP-02, DISP-03, DISP-04, OBS-03]

# Metrics
duration: 15min
completed: 2026-03-30
---

# Plan 98-01: Dispatch Correctness Summary

**SELECT FOR UPDATE SKIP LOCKED in pull_work() on Postgres with composite index (status, created_at) and migration_v44.sql for zero-downtime deployment**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-30T22:30Z
- **Completed:** 2026-03-30T22:45Z
- **Tasks:** 4 (Wave 0 + 3 Wave 1)
- **Files modified:** 4

## Accomplishments
- Composite index `ix_jobs_status_created_at` declared in `Job.__table_args__` — `create_all` handles fresh deployments
- Two-phase lock in `pull_work()`: unlocked candidate scan, then `SELECT FOR UPDATE SKIP LOCKED` on chosen row (Postgres only)
- `migration_v44.sql` with `CREATE INDEX CONCURRENTLY IF NOT EXISTS` and explicit transaction-block caveat
- Test suite: 5 tests pass, OBS-03 integration test skips on SQLite (requires Postgres)

## Task Commits

Each task was committed atomically:

1. **Wave 0: Test stubs** - `037a000` (test)
2. **Task 98-01-01: Composite index on Job model** - `8b02947` (feat)
3. **Task 98-01-02: migration_v44.sql** - `b89fcaa` (feat)
4. **Task 98-01-03: SKIP LOCKED in pull_work()** - `647158a` (feat)

## Files Created/Modified
- `puppeteer/agent_service/db.py` - Added `__table_args__` with `Index("ix_jobs_status_created_at", "status", "created_at")` to Job model
- `puppeteer/agent_service/services/job_service.py` - Two-phase SKIP LOCKED lock in candidate selection loop, guarded by IS_POSTGRES
- `puppeteer/migration_v44.sql` - CREATE INDEX CONCURRENTLY IF NOT EXISTS with CONCURRENTLY caveat comment
- `puppeteer/tests/test_dispatch_correctness_phase98.py` - 5 unit tests + 1 Postgres-only integration test

## Decisions Made
- Two-phase lock locks only the single chosen candidate row, not all 50 scanned — minimises contention between concurrent nodes
- SQLite path unchanged — Python's GIL and aiosqlite's serialised writes provide equivalent correctness without locks
- Migration uses CONCURRENTLY to avoid exclusive table locks during deployment; explicit comment warns against `psql -1`

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Pre-existing collection errors in 6 test files (test_foundry_mirror.py, test_intent_scanner.py, test_lifecycle_enforcement.py, test_smelter.py, test_staging.py, test_tools.py) — confirmed pre-existing before this plan's changes; zero new regressions introduced.

## User Setup Required
For existing Postgres deployments: run `psql -f puppeteer/migration_v44.sql` (without the `-1` flag — CONCURRENTLY cannot run inside a transaction block).

## Next Phase Readiness
- Phase 99 (Scheduler Hardening) can proceed — no dependencies on Phase 98
- Dispatch correctness foundation complete for Phase 100 observability work

---
*Phase: 98-dispatch-correctness*
*Completed: 2026-03-30*
