# Phase 100: Observability + Sign-off — Research

**Phase:** 100
**Requirements:** OBS-01, OBS-02, DOCS-01, DOCS-02
**Date:** 2026-03-31

---

## Summary

Phase 100 is a bounded implementation phase: one new FastAPI endpoint, a small Admin dashboard extension, and two documentation sections appended to an existing runbook. All dependencies (Phases 96–99) are complete. No schema changes, no new DB tables.

---

## Codebase Findings

### 1. asyncpg pool stats access

`puppeteer/agent_service/db.py` creates:
```python
engine = create_async_engine(DATABASE_URL, echo=False, **_pool_kwargs)
```

For a SQLAlchemy `AsyncEngine` backed by asyncpg, the underlying connection pool is reachable via:
```python
pool = engine.pool           # QueuePool (sync-level SQLAlchemy pool)
pool.size()                  # configured pool_size
pool.checkedout()            # connections currently in use
pool.overflow()              # overflow connections in use
pool.checkedin()             # idle connections
```
`available = pool.checkedin()` — SQLAlchemy QueuePool exposes this directly. No need for asyncpg-level introspection or a raw connection.

`IS_POSTGRES` is already exported from `db.py` — gate all pool stat access on this flag. SQLite path returns nulls with `is_postgres: false`.

### 2. APScheduler job count

`scheduler_service.py` exposes `scheduler_service.scheduler` (an `AsyncIOScheduler` instance). The APScheduler job count is:
```python
len(scheduler_service.scheduler.get_jobs())
```
This returns all registered jobs including internal `__`-prefixed jobs. The endpoint should expose the full count (operators want to know total active cron slots).

### 3. Pending job depth

Count `Job` rows with `status='PENDING'` in the database. The query is a simple `SELECT COUNT(*)`:
```python
result = await db.execute(select(func.count(Job.guid)).where(Job.status == "PENDING"))
pending_depth = result.scalar()
```
This is inexpensive — `ix_jobs_status_created_at` (added in Phase 98) covers `status` filtering.

### 4. Existing health endpoint pattern (main.py:757)

```python
@app.get("/api/health/scheduling", response_model=SchedulingHealthResponse, tags=["Health"])
async def get_scheduling_health_endpoint(
    window: str = "24h",
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
```
`GET /health/scale` follows the same pattern: `require_auth` (no specific permission — JWT-only), `db: AsyncSession = Depends(get_db)`. Place it immediately after the scheduling health route.

### 5. Pydantic model pattern

`SchedulingHealthResponse` (models.py:432) is the reference. New model:
```python
class ScaleHealthResponse(BaseModel):
    is_postgres: bool
    pool_size: Optional[int]
    checked_out: Optional[int]
    available: Optional[int]
    overflow: Optional[int]
    apscheduler_jobs: int
    pending_job_depth: int
```
All pool fields are `Optional[int]` — null on SQLite. `apscheduler_jobs` and `pending_job_depth` are always populated.

### 6. Admin.tsx Repository Health section (lines 1126–1171)

The `SmelterHealthPanel` component owns this card. It already has a `useQuery` for `/api/smelter/mirror-health` with `refetchInterval: 30000`. The scale health fetch is independent — add a second `useQuery` in the same component for `/api/health/scale`. The scale rows append after the existing disk/mirror rows.

Rows to add (matching the `flex items-center justify-between` pattern already used):
- `Pool checkout  {checked_out} / {pool_size}` (or "N/A (SQLite)" when `is_postgres: false`)
- `Pending jobs   {pending_job_depth}`
- `APScheduler    {apscheduler_jobs} jobs active`

### 7. upgrade.md — current state

File: `docs/docs/runbooks/upgrade.md`
- Migration table ends at `migration_v43.sql` (line 184)
- `migration_v17.sql` already appears in the table (line 159) — it covers `nodes.operator_tags` (Phase 4)
- `migration_v44.sql` does NOT yet appear in the migration table

CONTEXT.md decision captures the naming caveat: the Phase 98 dispatch index migration is `migration_v44.sql` — the `migration_v17.sql` filename was already used in Phase 4. DOCS-01 must add `migration_v44.sql` row with the CONCURRENTLY callout, not `migration_v17.sql`.

The migration_v44.sql file itself already contains:
- Pre-flight check comment: `SELECT COUNT(*) FROM jobs;`
- CONCURRENTLY caveat: "Do NOT use: `psql -1 -f migration_v44.sql`"
- Validity confirmation: `SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'jobs'`

These must be surfaced as runbook steps in upgrade.md.

### 8. operations docs — DOCS-02 target

DOCS-02 requires a "v17.0 Scale Hardening" section documenting:
- `ASYNCPG_POOL_SIZE` tuning formula: `pool_size ≤ max_connections / worker_count`
- Default values: pool_size=20, max_overflow=10, pool_timeout=30
- APScheduler pin rationale: `>=3.10,<4.0` — 4.x is a complete API rewrite, no migration path
- v17.0 thresholds (from CONTEXT.md / STATE.md)

Target: append to `docs/docs/runbooks/upgrade.md` as a new section after the migration table. No mkdocs.yml change required.

---

## Validation Architecture

### What needs automated tests

| Req | What to test | Test type |
|-----|-------------|-----------|
| OBS-01 | `GET /api/health/scale` returns 200 with correct schema on SQLite | pytest (existing async test client) |
| OBS-01 | `is_postgres: false`, all pool fields null, `apscheduler_jobs >= 0`, `pending_job_depth >= 0` on SQLite | pytest |
| OBS-01 | Pool fields populated when IS_POSTGRES=True (unit / structural) | pytest structural |
| OBS-02 | `ScaleHealthResponse` Pydantic model has all required fields (model field existence) | pytest structural |
| DOCS-01 | `migration_v44.sql` entry present in upgrade.md | pytest (file content scan) |
| DOCS-01 | CONCURRENTLY caveat present in upgrade.md for migration_v44 section | pytest (file content scan) |
| DOCS-02 | `ASYNCPG_POOL_SIZE` tuning formula present in upgrade.md | pytest (file content scan) |
| DOCS-02 | APScheduler pin rationale present in upgrade.md | pytest (file content scan) |

Test file: `puppeteer/tests/test_observability_phase100.py`

### Manual-only verifications

| Behavior | Why manual |
|----------|-----------|
| Dashboard shows pool rows in Admin → Foundry Health section | Requires running Docker stack + authenticated browser session |
| Scale endpoint returns live pool stats on Postgres deployment | Requires live Postgres DB connection |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `engine.pool` API not available on async engine | Tested: `create_async_engine` wraps `QueuePool`; `.pool` attribute is stable since SQLAlchemy 1.4 |
| `pool.checkedin()` returns wrong count | Use `pool.checkedin()` for available; `pool.checkedout()` for checked_out. Both are O(1) counter reads |
| Admin.tsx — SmelterHealthPanel is CE-only or EE-gated | `SmelterHealthPanel` renders unconditionally in the Foundry tab of Admin.tsx — no feature flag gate on Repository Health card |
| Scale endpoint called before scheduler starts | `scheduler_service.scheduler.get_jobs()` returns empty list before start — returns 0, which is correct |

---

## RESEARCH COMPLETE

All implementation patterns confirmed. No blockers. Proceed to planning.
