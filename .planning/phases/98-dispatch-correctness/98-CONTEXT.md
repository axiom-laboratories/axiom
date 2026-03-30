# Phase 98: Dispatch Correctness - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate double-assignment races in job dispatch by adding `SELECT FOR UPDATE SKIP LOCKED` to `pull_work()` and a composite index on `(status, created_at)` to replace full-table scans. Covers Postgres path only — SQLite uses the existing unguarded query. No user-facing changes.

</domain>

<decisions>
## Implementation Decisions

### SKIP LOCKED scope
- **Two-phase locking**: the candidate scan (`.limit(50)`) runs as an unlocked read — identical to today. Once an eligible job is found via Python eligibility filtering, a second `SELECT FOR UPDATE SKIP LOCKED WHERE guid = <that job>` locks only that single row.
- If the single-row lock returns nothing (another node grabbed it first), iterate to the next candidate and retry.
- Only one row is held locked during the assignment transaction — minimal lock footprint, friendlier to 20 concurrent nodes.
- Candidate scan limit stays at 50 (unchanged) — the unlocked scan still sees all rows.

### RETRYING in the locked query
- SKIP LOCKED applies to **both PENDING and RETRYING** statuses — consistent with today's candidate query behaviour.
- The composite index is `(status, created_at)` only — `retry_after` time check remains in Python after the candidate fetch (cheap on 50 rows).

### Integration test (OBS-03)
- Env-var guard: test skips (`pytest.skip()`) if `DATABASE_URL` is not Postgres — passes locally on SQLite, runs in CI with Postgres.
- Self-contained isolated async session: test creates its own asyncpg connection, inserts a PENDING job, fires 5 concurrent `pull_work()` calls via `asyncio.gather()`, asserts exactly 1 ASSIGNED result and 0 double-assignments, then cleans up.
- File: `puppeteer/tests/test_dispatch_correctness_phase98.py`

### migration_v17.sql
- Phase 98 **creates** `migration_v17.sql` as the shared v17.0 migration file.
- Contains `CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_status_created_at ON jobs (status, created_at)`.
- Note: `CREATE INDEX CONCURRENTLY` cannot run inside a `BEGIN` block — the runbook must call it outside a transaction.
- Later phases (99, 100) append their own SQL to this same file so operators apply one file for the full v17.0 upgrade.

### Claude's Discretion
- Exact SQLAlchemy syntax for the two-phase lock query (e.g., `with_for_update(skip_locked=True)`)
- Whether the retry loop on lock contention is a `for` loop over candidates or a `while` with index tracking
- How to structure the test node setup/teardown within the isolated async session

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IS_POSTGRES` (db.py): already exported — gates the SKIP LOCKED path exactly as needed
- `pull_work()` (job_service.py:550): existing candidate query at line 647 — two-phase lock wraps the assignment block starting at line 675
- `test_pool_phase97.py`: env-var-gated skip pattern already used for Postgres-specific logic — follow same pattern
- `test_foundation_phase96.py`: established pattern for phase tests with simulation-based DB checks

### Established Patterns
- `IS_POSTGRES` import: `from agent_service.db import IS_POSTGRES` — same import in `job_service.py`
- SQLAlchemy async SKIP LOCKED: `select(Job).where(...).with_for_update(skip_locked=True)` then `await db.execute(...)`
- Migration files: prior migrations use `ALTER TABLE ... IF NOT EXISTS` style — `CONCURRENTLY` index creation follows same "safe for existing deployments" philosophy

### Integration Points
- `job_service.py:647–670` — candidate scan loop; the two-phase lock slot is between the eligible job selection (line 669) and the assignment block (line 675)
- `db.py:32` — `Job` model `__table_args__` is where `Index("ix_jobs_status_created_at", ...)` is declared
- `puppeteer/migration_v17.sql` — new file created by this phase

</code_context>

<specifics>
## Specific Ideas

- No specific references — standard SQLAlchemy asyncpg SKIP LOCKED pattern
- The two-phase approach (unlocked scan → single-row lock) was explicitly chosen over locking all candidates because it minimises lock footprint under 20 concurrent polling nodes

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 98-dispatch-correctness*
*Context gathered: 2026-03-30*
