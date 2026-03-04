---
phase: 01-output-capture
plan: "01"
subsystem: database
tags: [sqlalchemy, pydantic, postgres, sqlite, migration]

# Dependency graph
requires: []
provides:
  - ExecutionRecord SQLAlchemy ORM model in db.py (table: execution_records)
  - Extended ResultReport Pydantic model with output_log, exit_code, security_rejected fields
  - ExecutionRecordResponse Pydantic model for API responses
  - migration_v14.sql for existing Postgres deployments
affects:
  - 01-02 (job_service.py writes ExecutionRecord rows)
  - 01-03 (main.py exposes GET endpoint returning ExecutionRecordResponse)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ExecutionRecord uses Python-level default=False on Boolean columns (no server_default — SQLite compat)"
    - "ResultReport backward-compat extension: all new fields Optional with defaults"
    - "Index defined via __table_args__ = (Index(...),) pattern"

key-files:
  created:
    - puppeteer/migration_v14.sql
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/models.py

key-decisions:
  - "output_log stored as TEXT (JSON string) in DB, deserialized to List[Dict[str,str]] in Pydantic layer"
  - "truncated column uses Python-level default=False only — no server_default (SQLite compat per RESEARCH.md Pitfall 6)"
  - "ResultReport extended with Optional fields and defaults — existing node code that omits them continues to work"
  - "ExecutionRecordResponse uses List[Dict[str,str]] not a named OutputLine type — avoids Pydantic coercion issues with raw JSON dict arrays"

patterns-established:
  - "Schema contracts defined in plan 01 before any service or route work — all downstream tasks depend on these"

requirements-completed:
  - OUT-01
  - OUT-02
  - OUT-03

# Metrics
duration: 3min
completed: 2026-03-04
---

# Phase 1 Plan 01: Data Contracts Summary

**ExecutionRecord ORM table + extended ResultReport + ExecutionRecordResponse Pydantic models establishing the output capture data contracts**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-04T21:14:06Z
- **Completed:** 2026-03-04T21:16:41Z
- **Tasks:** 3
- **Files modified:** 3 (db.py, models.py, migration_v14.sql)

## Accomplishments
- ExecutionRecord SQLAlchemy ORM class with 9 columns and job_guid index, picked up by create_all at startup
- ResultReport extended with three backward-compatible Optional fields (output_log, exit_code, security_rejected)
- New ExecutionRecordResponse Pydantic model with duration_seconds computed field slot
- migration_v14.sql idempotent SQL for existing Postgres deployments

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ExecutionRecord ORM model to db.py** - `93a58ca` (feat)
2. **Task 2: Extend ResultReport and add ExecutionRecordResponse in models.py** - `d6b1322` (feat)
3. **Task 3: Write migration_v14.sql for existing Postgres deployments** - `419a316` (feat)

## Files Created/Modified
- `puppeteer/agent_service/db.py` - Added Index import + ExecutionRecord class (9 columns, job_guid index)
- `puppeteer/agent_service/models.py` - Extended ResultReport with 3 new Optional fields; added ExecutionRecordResponse
- `puppeteer/migration_v14.sql` - Idempotent CREATE TABLE IF NOT EXISTS execution_records + index

## Decisions Made
- output_log stored as TEXT in DB: The ORM column is TEXT (JSON string). Pydantic model type is List[Dict[str,str]]. Serialization/deserialization is handled in the service layer (plan 02).
- truncated uses Python-level default only: SQLite doesn't support server_default="false" on Boolean — using default=False at Python level consistent with NodeStats pattern.
- List[Dict[str,str]] not named type: Per RESEARCH.md Pattern 2, raw dict arrays from nodes avoid Pydantic coercion issues when using plain dict typing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing aiosqlite dependency for verification**
- **Found during:** Task 1 verification
- **Issue:** Venv lacked aiosqlite; `from agent_service.db import ExecutionRecord` raised ModuleNotFoundError on engine creation
- **Fix:** Ran `pip install aiosqlite` in the project venv
- **Files modified:** None (venv only)
- **Verification:** Import succeeded after install
- **Committed in:** Not committed (dev environment setup only)

---

**Total deviations:** 1 auto-fixed (1 blocking — environment setup)
**Impact on plan:** Fix was necessary to run verification steps. No code changes required. No scope creep.

## Issues Encountered
- `python` command not found in shell (linux env uses `python3`) — used `python3` and then venv path directly
- pytest not installed in venv — installed it with pytest-asyncio and httpx
- Pre-existing test failures: `test_main.py` and `test_sprint3.py` have import errors (`puppeteer` module not on path) that predate this plan. 25 other agent_service tests pass cleanly.

## User Setup Required
None - no external service configuration required. For existing Postgres deployments, run:
```sql
psql -U <user> -d <db> -f puppeteer/migration_v14.sql
```

## Next Phase Readiness
- Data contracts are complete and verified
- Plan 02 (job_service.py) can now import ExecutionRecord from db.py and ResultReport from models.py
- Plan 03 (main.py routes) can import ExecutionRecordResponse for response typing
- No blockers for plans 02 or 03

## Self-Check: PASSED

- puppeteer/agent_service/db.py: FOUND
- puppeteer/agent_service/models.py: FOUND
- puppeteer/migration_v14.sql: FOUND
- .planning/phases/01-output-capture/01-01-SUMMARY.md: FOUND
- Commit 93a58ca (Task 1): FOUND
- Commit d6b1322 (Task 2): FOUND
- Commit 419a316 (Task 3): FOUND

---
*Phase: 01-output-capture*
*Completed: 2026-03-04*
