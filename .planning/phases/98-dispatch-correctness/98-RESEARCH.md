# Phase 98: Dispatch Correctness — Research

**Phase:** 98 — Dispatch Correctness
**Requirements:** DISP-01, DISP-02, DISP-03, DISP-04, OBS-03
**Researched:** 2026-03-30

---

## Summary

Phase 98 adds two hardening layers to `pull_work()`: a composite index for efficient candidate scanning and `SELECT FOR UPDATE SKIP LOCKED` to eliminate double-assignment races under concurrent polling nodes. The change is Postgres-only (guarded by `IS_POSTGRES`) and requires a migration file plus an integration test. Three code files are touched: `db.py`, `job_service.py`, and a new migration file.

**Critical finding:** `migration_v17.sql` already exists in the repo (from Phase 4 / env tags). The phase must use a different migration file name. The next unused migration file based on the repo is `migration_v44.sql` (the last numbered file is `migration_v43.sql`).

---

## Technical Findings

### 1. Composite Index on `Job` (DISP-01)

SQLAlchemy `Index` in `__table_args__` is the standard way to declare named indexes that `create_all` will create on fresh deployments:

```python
from sqlalchemy import Index

class Job(Base):
    __tablename__ = "jobs"
    # ... columns ...

    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
    )
```

`__table_args__` must be a **tuple** (note trailing comma if only one element). `create_all` creates this index automatically; existing deployments need the migration.

**Current state of `db.py`:** The `Job` model has no `__table_args__` and `Index` is already imported at the top of the file. Only `UniqueConstraint` and `ForeignKey` and `Index` are already in the import line (line 4 confirms `Index` is imported). Adding `__table_args__` to `Job` is the sole db.py change.

### 2. Migration File (DISP-02)

**Key finding:** `migration_v17.sql` is already taken (Phase 4 — operator_tags). The REQUIREMENTS.md and ROADMAP refer to "migration_v17.sql" aspirationally (as the v17.0 migration file) but the actual filename on disk must not collide. The correct filename for this phase is:

```
puppeteer/migration_v44.sql
```

Content:
```sql
-- migration_v44.sql — Phase 98: Dispatch Correctness
-- Adds composite index for efficient job candidate scanning
-- IMPORTANT: CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
-- Run this file outside of a BEGIN/COMMIT block (psql -f migration_v44.sql).

-- Pre-flight check: confirm the jobs table exists
-- SELECT COUNT(*) FROM jobs;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_status_created_at
    ON jobs (status, created_at);

-- Validity confirmation:
-- SELECT indexname FROM pg_indexes WHERE tablename='jobs' AND indexname='ix_jobs_status_created_at';
```

**CONCURRENTLY caveat:** `CREATE INDEX CONCURRENTLY` cannot run inside an explicit transaction block (`BEGIN` / `COMMIT`). If the operator runs `psql -1 -f migration_v44.sql` (which wraps in a transaction), it will fail. The runbook (Phase 100 DOCS-01) must document this. The migration file itself must carry the warning comment.

**SQLite:** SQLite does not support `CONCURRENTLY`. The migration is Postgres-only and guarded by `IS_POSTGRES` in code. The migration file itself contains no SQLite variant (unlike prior migrations) because `CREATE INDEX CONCURRENTLY` has no SQLite equivalent — fresh SQLite deployments get the index via `create_all`.

### 3. SELECT FOR UPDATE SKIP LOCKED in `pull_work()` (DISP-03, DISP-04)

**Two-phase approach (from CONTEXT.md):**
1. Phase 1 (unlocked scan): existing query fetches up to 50 candidates — unchanged
2. Phase 2 (single-row lock): once `_node_is_eligible()` finds a match, lock just that one row with `SELECT FOR UPDATE SKIP LOCKED WHERE guid = <guid>`

SQLAlchemy async syntax:
```python
lock_result = await db.execute(
    select(Job)
    .where(Job.guid == candidate.guid)
    .with_for_update(skip_locked=True)
)
locked_job = lock_result.scalar_one_or_none()
if locked_job is None:
    continue  # Another node grabbed it — try next candidate
```

**Guard with IS_POSTGRES:** SQLite does not support `FOR UPDATE`. The Postgres path uses the two-phase lock; the SQLite path keeps the existing direct assignment.

**Code insertion point:** Between line 669 (selected_job = candidate; break) and line 675 (selected_job.status = 'ASSIGNED'). Replace the `break` with the two-phase lock loop.

**Loop restructure:** The current loop uses `break` after finding the first eligible job. The new loop must:
1. Continue iterating if the lock is lost (SKIP LOCKED returns None)
2. Break only when a lock is successfully acquired
3. Fall through to `return PollResponse(job=None)` if all candidates are locked away

Revised loop pattern:
```python
selected_job = None
for candidate in jobs:
    if not JobService._node_is_eligible(node, candidate, node_tags, node_caps_dict):
        continue
    if IS_POSTGRES:
        lock_result = await db.execute(
            select(Job)
            .where(Job.guid == candidate.guid)
            .with_for_update(skip_locked=True)
        )
        locked_job = lock_result.scalar_one_or_none()
        if locked_job is None:
            continue  # Grabbed by another node
        selected_job = locked_job
    else:
        selected_job = candidate
    break
```

### 4. Integration Test — Zero Double-Assignment (OBS-03)

**Pattern from `test_pool_phase97.py`:** Env-var guard via `pytest.skip()` at the top of each test that needs Postgres.

**Test strategy:** The test uses real asyncpg connections to a real Postgres DB. It:
1. Creates an isolated test job directly via SQL or ORM
2. Fires 5 concurrent `pull_work()` coroutines via `asyncio.gather()`
3. Asserts exactly 1 ASSIGNED result, 0 double-assignments
4. Cleans up

**Practical challenge:** `pull_work()` requires a `Node` record and an `AsyncSession`. The test must:
- Create 5 separate `AsyncSession` instances (to simulate 5 different concurrent DB connections)
- Create 5 minimal `Node` records (node1–node5) so the eligibility check passes
- Insert 1 PENDING job with no tags/capabilities requirements
- Run `pull_work(node_id=f"test-node-{i}", node_ip="127.0.0.1", db=sessions[i])` concurrently

**Using `AsyncSessionLocal` from `db.py`:** The test can import `AsyncSessionLocal` and create sessions directly — same pattern as the production code.

**Cleanup:** The test must clean up all inserted rows after itself. Use `try/finally` around the gather + cleanup block.

**Skip guard:**
```python
import pytest
from agent_service.db import IS_POSTGRES

pytestmark = pytest.mark.skipif(
    not IS_POSTGRES,
    reason="Double-assignment integration test requires Postgres (IS_POSTGRES=False)"
)
```

Or inline `pytest.skip()` at the top of each test function (matching phase 97 style).

**File:** `puppeteer/tests/test_dispatch_correctness_phase98.py`

---

## Code Targets Summary

| File | Change |
|------|--------|
| `puppeteer/agent_service/db.py` | Add `__table_args__` with `Index("ix_jobs_status_created_at", "status", "created_at")` to `Job` model |
| `puppeteer/agent_service/services/job_service.py` | Restructure candidate loop to use two-phase `SELECT FOR UPDATE SKIP LOCKED` on Postgres path |
| `puppeteer/migration_v44.sql` | New file — `CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_status_created_at` with CONCURRENTLY caveat |
| `puppeteer/tests/test_dispatch_correctness_phase98.py` | New file — integration test for zero double-assignment under 5 concurrent `pull_work()` calls |

**Note on migration naming:** The REQUIREMENTS.md and ROADMAP reference "migration_v17.sql" as the conceptual v17.0 migration. However, `migration_v17.sql` is already occupied (Phase 4 — operator_tags on nodes table). This phase creates `migration_v44.sql`. Phase 100 DOCS-01 should document `migration_v44.sql` in the upgrade runbook, not v17.

---

## Validation Architecture

### Test file location
`puppeteer/tests/test_dispatch_correctness_phase98.py`

### Test commands
- Quick: `cd puppeteer && pytest tests/test_dispatch_correctness_phase98.py -v`
- Full backend suite: `cd puppeteer && pytest`

### Coverage

| Requirement | Test | Type |
|-------------|------|------|
| DISP-01 (composite index in db.py) | `test_index_declared_in_job_model` | unit (code inspection) |
| DISP-02 (migration file) | `test_migration_v44_exists_and_contains_index` | unit (file check) |
| DISP-03 (SKIP LOCKED on Postgres) | `test_pull_work_uses_skip_locked_on_postgres` | unit (code inspection) + integration |
| DISP-04 (SQLite guard) | `test_sqlite_path_unguarded` | unit (IS_POSTGRES=False) |
| OBS-03 (zero double-assignment) | `test_no_double_assignment_concurrent_pull_work` | integration (Postgres required) |

All 5 requirements have automated test coverage. The integration tests (OBS-03, DISP-03 integration) are skip-guarded and run only when `IS_POSTGRES=True`.

---

## ## RESEARCH COMPLETE

**Confidence:** High — narrow, well-understood change with established patterns from Phase 96/97 and rich CONTEXT.md.
**Key risk:** The migration file naming collision (`migration_v17.sql` already exists). Use `migration_v44.sql` instead. The REQUIREMENTS.md references to "migration_v17.sql" are aspirational — the actual file name must not collide.
**Recommendation:** Single plan wave, single plan file. All 5 requirements fit in one focused change set covering: index declaration, migration file, SKIP LOCKED loop, and integration test.
