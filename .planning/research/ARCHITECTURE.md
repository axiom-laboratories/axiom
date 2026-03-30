# Architecture Research

**Domain:** Scale hardening integration — Axiom job scheduler (FastAPI + SQLAlchemy async + APScheduler 3.x)
**Researched:** 2026-03-30
**Confidence:** HIGH (verified against SQLAlchemy 2.0 docs, APScheduler 3.x docs, PostgreSQL docs, and existing codebase)

---

## System Overview

Current architecture (before scale hardening):

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Single FastAPI Process                            │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  HTTP API    │  │  WebSocket   │  │  APScheduler             │  │
│  │  Routes      │  │  /ws         │  │  AsyncIOScheduler        │  │
│  │  (main.py)   │  │              │  │  (same event loop)       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
│         │                 │                      │                  │
│         └─────────────────┴──────────────────────┘                  │
│                           │                                          │
│              ┌────────────▼────────────┐                            │
│              │  AsyncSession / engine  │                            │
│              │  (pool_size=5, default) │                            │
│              └────────────┬────────────┘                            │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  PostgreSQL /  │
                    │  SQLite (dev)  │
                    └────────────────┘
```

Problems at scale:
- APScheduler cron callbacks fire on the same event loop as HTTP request handling — 100 cron fires/min saturate the loop.
- `pull_work()` does `SELECT PENDING LIMIT 50` + status update with no row lock — two nodes polling simultaneously can both select the same job.
- `sync_scheduler()` calls `remove_all_jobs()` on every definition CRUD — causes a brief window where no cron jobs are registered.
- `pool_size=5` (implicit default) exhausts under concurrent node polling from 20+ nodes.
- No index on `(status, created_at)` on the `jobs` table — full scan on every `pull_work()` call.

Target architecture (after scale hardening):

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Single FastAPI Process                            │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  HTTP API    │  │  WebSocket   │  │  APScheduler (isolated)  │  │
│  │  Routes      │  │  /ws         │  │  create_task wrapping    │  │
│  │  (main.py)   │  │              │  │  (same event loop)       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
│         │                 │                      │                  │
│         └─────────────────┴──────────────────────┘                  │
│                           │                                          │
│              ┌────────────▼────────────┐                            │
│              │  AsyncSession / engine  │                            │
│              │  pool_size=20,          │                            │
│              │  max_overflow=10        │                            │
│              └────────────┬────────────┘                            │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │       PostgreSQL          │
              │  idx: (status,created_at) │
              └───────────────────────────┘
```

---

## Component Boundaries

| Component | File | Responsibility | Changes Required |
|-----------|------|----------------|-----------------|
| Engine creation | `db.py` line 14 | Creates the SQLAlchemy AsyncEngine | Add `pool_size`, `max_overflow`, `pool_pre_ping`, dialect guard |
| `pull_work()` | `job_service.py` line 550 | Selects + assigns a PENDING job to a node | Replace bare `select(Job).where(status=PENDING)` with `with_for_update(skip_locked=True)` on Postgres; keep existing pattern on SQLite |
| `sync_scheduler()` | `scheduler_service.py` line 120 | Keeps APScheduler in sync with DB definitions | Replace `remove_all_jobs()` + full reload with incremental add/remove using `get_job()` / `add_job(replace_existing=True)` / `remove_job()` |
| APScheduler isolation | `scheduler_service.py` `execute_scheduled_job` | Keeps cron callback work off the scheduler loop | Wrap method body with `asyncio.create_task` pattern |
| DB index | `db.py` `Job.__table_args__` + migration SQL | Index on `(status, created_at)` for `pull_work` query | Add to `__table_args__` for new deployments; provide migration SQL for existing DBs |

---

## Recommended Project Structure

No new files required except a migration SQL file. All changes are targeted modifications to existing files:

```
puppeteer/agent_service/
├── db.py                        # pool_size + IS_POSTGRES + index addition
├── services/
│   ├── job_service.py           # SKIP LOCKED in pull_work()
│   └── scheduler_service.py    # incremental sync_scheduler(), create_task isolation
└── main.py                     # no changes needed for dispatcher isolation at v17.0 scope

puppeteer/
└── migration_v17.sql            # CREATE INDEX CONCURRENTLY for existing Postgres DBs
```

---

## Architectural Patterns

### Pattern 1: Pool Size in `create_async_engine`

**What:** `create_async_engine` accepts `pool_size` and `max_overflow` directly as keyword arguments. The engine automatically uses `AsyncAdaptedQueuePool` (asyncio-safe variant of `QueuePool`) — no manual pool class specification needed. Default `pool_size=5`, `max_overflow=10`.

**Current code** (`db.py` line 14):
```python
engine = create_async_engine(DATABASE_URL, echo=False)
```

**Target code:**
```python
_IS_POSTGRES = DATABASE_URL.startswith("postgresql")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20 if _IS_POSTGRES else 5,
    max_overflow=10 if _IS_POSTGRES else 0,
    pool_pre_ping=True,
    pool_recycle=1800,
)

IS_POSTGRES = _IS_POSTGRES  # exported for use in services
```

**When to use:** Set at engine creation time. `pool_size` controls persistent connections kept open. `max_overflow` allows temporary burst beyond `pool_size`. Total max connections = `pool_size + max_overflow`. For a 20-node deployment, 20 simultaneous `/work/pull` calls each need one connection at the SELECT point — `pool_size=20` matches this 1:1.

**Trade-offs:** `pool_size=20` assumes Postgres `max_connections >= 100` (default is 100). For SQLite, `pool_size=5` is sufficient since SQLite serialises writes via file-level locking — more connections increase contention without benefit. The `_IS_POSTGRES` guard makes this safe for both environments. Confidence: HIGH (SQLAlchemy 2.0 docs, confirmed defaults).

---

### Pattern 2: SELECT FOR UPDATE SKIP LOCKED in async SQLAlchemy

**What:** Appending `.with_for_update(skip_locked=True)` to a `select()` statement generates `SELECT ... FOR UPDATE SKIP LOCKED` in PostgreSQL. SQLAlchemy silently ignores `with_for_update()` on SQLite — it emits no locking clause, which is safe because SQLite's write serialisation provides the same correctness guarantee for a single-process dev deployment.

**Current code** (`job_service.py` lines 647–660):
```python
result = await db.execute(
    select(Job).where(
        or_(Job.status == 'PENDING', and_(...RETRYING...))
    ).where(
        (Job.node_id == None) | (Job.node_id == node_id)
    ).order_by(Job.created_at.asc()).limit(50)
)
jobs = result.scalars().all()
```

**Target code:**
```python
from ..db import IS_POSTGRES

candidate_query = (
    select(Job).where(
        or_(Job.status == 'PENDING', and_(...RETRYING...))
    ).where(
        (Job.node_id == None) | (Job.node_id == node_id)
    ).order_by(Job.created_at.asc()).limit(50)
)
if IS_POSTGRES:
    candidate_query = candidate_query.with_for_update(skip_locked=True)

result = await db.execute(candidate_query)
jobs = result.scalars().all()
```

**Transaction scope note:** `SKIP LOCKED` requires the SELECT and UPDATE to happen inside the same transaction. The existing `pull_work` function commits at line 578 (after the node upsert) before reaching the candidate query. This means the candidate SELECT starts a new implicit transaction automatically — SQLAlchemy's `AsyncSession` starts a new transaction on the next `execute()` call after a commit. The `selected_job.status = 'ASSIGNED'` mutation and subsequent `db.commit()` at the end of `pull_work` completes the transaction. This is correct — no structural change to session handling required.

**SQLite fallback:** `with_for_update(skip_locked=True)` on SQLite: the clause is not emitted (confirmed by SQLAlchemy docs). The query runs as a plain `SELECT`. This is safe for single-process dev. Multi-process SQLite dispatch is not a supported configuration.

**Trade-offs:** `FOR UPDATE SKIP LOCKED` means: lock the rows I am evaluating; if another session already holds a lock on a row, skip that row and move to the next one. Two simultaneous `pull_work` calls on Postgres now see disjoint sets of candidate rows. The race condition (two nodes assigned the same job) is eliminated at the database level. Confidence: HIGH (SQLAlchemy GitHub discussion #10460 confirms correct PostgreSQL syntax generation).

---

### Pattern 3: Incremental `sync_scheduler()`

**What:** Replace the `remove_all_jobs()` + full-reload pattern with a three-way diff: add new definitions (using `add_job(replace_existing=True)` which is idempotent), remove deleted/inactive definitions, leave unchanged definitions alone.

**Current code** (`scheduler_service.py` lines 120–144) — problem:
```python
async def sync_scheduler(self):
    self.scheduler.remove_all_jobs()          # ALL jobs dark from here...
    async with db_module.AsyncSessionLocal() as session:
        result = await session.execute(...)   # ...until this completes
        jobs = result.scalars().all()
        for j in jobs:
            self.scheduler.add_job(...)       # ...and this loop finishes
```

**Target code:**
```python
async def sync_scheduler(self):
    """Incremental sync: add/replace changed jobs, remove deleted jobs, no dark window."""
    async with db_module.AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScheduledJob).where(ScheduledJob.is_active == True)
        )
        db_jobs = {j.id: j for j in result.scalars().all()}

    # IDs currently registered in the scheduler
    scheduled_ids = {job.id for job in self.scheduler.get_jobs()
                     if not job.id.startswith("__")}  # exclude internal jobs

    # Remove jobs no longer active in DB
    for jid in scheduled_ids - db_jobs.keys():
        self.scheduler.remove_job(jid)

    # Add or update jobs present in DB
    for jid, j in db_jobs.items():
        if not j.schedule_cron:
            continue
        parts = j.schedule_cron.split()
        if len(parts) != 5:
            continue
        try:
            self.scheduler.add_job(
                self.execute_scheduled_job,
                'cron',
                args=[j.id],
                minute=parts[0], hour=parts[1], day=parts[2],
                month=parts[3], day_of_week=parts[4],
                id=j.id,
                replace_existing=True,
                misfire_grace_time=60,
            )
        except Exception as e:
            logger.error(f"Failed to schedule {j.name}: {e}")
```

**`replace_existing=True` behaviour:** APScheduler replaces the job's trigger but retains its run count. If the cron expression is unchanged, recreating the trigger is effectively a no-op at the execution level. All other registered jobs (including the internal `__prune_node_stats__`, `__dispatch_timeout_sweeper__` jobs) are never touched. Confidence: HIGH (APScheduler 3.x docs).

---

### Pattern 4: Composite Index on `jobs(status, created_at)` Without Alembic

**What:** The `pull_work` candidate query has `WHERE status IN ('PENDING', 'RETRYING') ORDER BY created_at ASC LIMIT 50`. A composite index on `(status, created_at)` lets Postgres use an index range scan instead of a full table scan.

**For new deployments** — add `__table_args__` to `Job` in `db.py`:

The `Job` class currently has no `__table_args__`. Add it after the last column definition:

```python
class Job(Base):
    __tablename__ = "jobs"
    # ... all existing columns unchanged ...
    dispatch_timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
    )
```

`Base.metadata.create_all` creates this index when it creates the `jobs` table on a fresh database. For an existing database, `create_all` does NOT add new indexes to existing tables — it only creates objects that do not yet exist.

**For existing Postgres deployments** — `migration_v17.sql`:
```sql
-- Safe for live production: CONCURRENTLY does not block reads or writes.
-- NOTE: Cannot run inside a transaction block.
-- Run via: psql $DATABASE_URL -f migration_v17.sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_status_created_at
    ON jobs (status, created_at ASC);
```

`CREATE INDEX CONCURRENTLY` builds the index via two table scans without an exclusive lock — live traffic continues uninterrupted. `IF NOT EXISTS` makes it idempotent. The `CONCURRENTLY` keyword cannot be used inside a `BEGIN` block — the migration SQL file must be run directly via psql, not wrapped in a transaction.

**For SQLite dev environments:** The `Index(...)` in `__table_args__` is created by `create_all` on a fresh SQLite file without issue. SQLite does not have `CONCURRENTLY` but does not need it.

**Trade-offs:** A `(status, created_at)` B-tree index is most effective when `status` has low cardinality (it does: ~6 values). Postgres will use the index for both the `WHERE status IN (...)` filter and the `ORDER BY created_at` sort, potentially eliminating a sort step. On a table with 10,000+ jobs (mostly COMPLETED/FAILED), this index means `pull_work` scans only the small PENDING/RETRYING subset rather than the full table. Confidence: HIGH (PostgreSQL docs + SQLAlchemy index definition docs).

---

### Pattern 5: APScheduler Dispatcher Isolation

**What:** APScheduler's `AsyncIOScheduler` shares the main event loop with FastAPI. At 100 cron fires/minute, each `execute_scheduled_job` callback runs DB queries and creates job records — work that competes with HTTP request handlers for event loop time.

**v17.0 recommendation (single container, lowest risk):** Fire-and-forget via `asyncio.create_task`. The APScheduler callback becomes a thin launcher; the DB work runs as a background coroutine:

```python
async def execute_scheduled_job(self, scheduled_job_id: str):
    """APScheduler callback — returns immediately, work runs as background task."""
    asyncio.create_task(
        self._execute_scheduled_job_impl(scheduled_job_id),
        name=f"cron-fire-{scheduled_job_id[:8]}",
    )

async def _execute_scheduled_job_impl(self, scheduled_job_id: str):
    """Actual implementation — all existing logic moved here unchanged."""
    logger.info(f"Triggering Scheduled Job: {scheduled_job_id}")
    # ... existing body of execute_scheduled_job ...
```

This decouples the APScheduler callback duration from the job creation work. The scheduler loop returns in microseconds. At 100 fires/minute, 100 background tasks are launched per minute — each takes ~50ms for a DB round trip, so at any moment there are at most ~8 concurrent background tasks, well within asyncio's capacity.

**Future: true process isolation** (if event loop saturation becomes the next bottleneck after v17.0): Extract the scheduler into a separate entry point (`puppeteer/agent_service/dispatcher.py`) that runs its own `asyncio` event loop with its own APScheduler and its own DB engine, connecting to the same Postgres database via `DATABASE_URL`. Add a second service in `compose.server.yaml`:

```yaml
dispatcher:
  image: puppeteer-agent
  command: python -m agent_service.dispatcher
  environment:
    DATABASE_URL: ${DATABASE_URL}
  depends_on: [db]
```

This works cleanly because all coordination state (which jobs exist, their schedules, the `jobs` table) lives in Postgres. No in-memory state sharing between API and dispatcher processes is needed. The architecture already supports this — it requires no data model changes.

**Trade-offs:** The `create_task` pattern has near-zero risk and covers the v17.0 load target. True process isolation adds operational complexity (two services, startup ordering, log aggregation) and should only be implemented if profiling shows the event loop is actually saturated. Confidence: MEDIUM for the `create_task` pattern (standard asyncio); HIGH that the architecture supports process isolation cleanly.

---

## Data Flow Changes

### Current `pull_work` Data Flow (with race condition)

```
Node A polls /work/pull              Node B polls /work/pull (simultaneous)
    |                                    |
    v                                    v
SELECT Node, UPDATE last_seen        SELECT Node, UPDATE last_seen
    |                                    |
    v                                    v
SELECT Job WHERE status=PENDING      SELECT Job WHERE status=PENDING
    LIMIT 50                             LIMIT 50
    |                                    |
    v                                    v
Both select job X as candidate       Both select job X as candidate
    |                                    |
    v                                    v
job_X.status = ASSIGNED              job_X.status = ASSIGNED
    |                                    |
    v                                    v
await db.commit()                    await db.commit()  <-- last writer wins
                                     (both nodes assigned job X)
```

### Target `pull_work` Data Flow (with SKIP LOCKED)

```
Node A polls /work/pull              Node B polls /work/pull (simultaneous)
    |                                    |
    v                                    v
SELECT Node, UPDATE last_seen        SELECT Node, UPDATE last_seen
    |                                    |
    v                                    v
SELECT Job WHERE status=PENDING      SELECT Job WHERE status=PENDING
    LIMIT 50                             LIMIT 50
    FOR UPDATE SKIP LOCKED               FOR UPDATE SKIP LOCKED
    |                                    |
    v                                    v
Node A locks job X                   Job X is locked → skipped
Node A selects job X                 Node B skips to job Y
    |                                    |
    v                                    v
job_X.status = ASSIGNED              job_Y.status = ASSIGNED
    |                                    |
    v                                    v
await db.commit()                    await db.commit()
(lock released)
```

### Scheduler Sync Data Flow Change

```
Before CRUD:  sync_scheduler()
    |
    v
remove_all_jobs()           <- ALL jobs unregistered (dark window starts)
    |
    v
DB SELECT all active jobs   <- network round trip during dark window
    |
    v
add_job() for each          <- jobs re-registered (dark window ends)

After CRUD:   sync_scheduler()
    |
    v
DB SELECT all active jobs   <- read-only, no dark window
    |
    v
diff: scheduled_ids vs db_ids
    |
    +--> remove_job(id) for departed IDs   <- targeted removal
    +--> add_job(id, replace_existing=True) for all DB IDs   <- idempotent upsert
         (jobs not changing are re-registered with same trigger — effectively no-op)
```

---

## Scaling Considerations

| Scale | Bottleneck | Fix |
|-------|------------|-----|
| 10 nodes / 50 jobs | None | No changes needed |
| 20 nodes / 200 jobs | DB connection pool exhaustion | `pool_size=20` |
| 20 nodes / 200 jobs | Double-assignment race | `SKIP LOCKED` |
| 50 nodes / 500 jobs | Full-table scan on `pull_work` | Composite index `(status, created_at)` |
| 100 cron fires/min | Scheduler sync dark window | Incremental `sync_scheduler()` |
| 100 cron fires/min | Event loop saturation | `create_task` dispatcher isolation |
| 200+ nodes | Postgres `max_connections` | PgBouncer (out of scope for v17.0) |

**v17.0 target (20 nodes / 200 jobs / 1,000 definitions / 100 fires/min):** All five patterns above cover this range within the existing single-container Docker deployment topology.

---

## Anti-Patterns

### Anti-Pattern 1: `remove_all_jobs()` on Every CRUD

**What people do:** Call `sync_scheduler()` which calls `remove_all_jobs()` + full reload on every job definition create/update/delete.

**Why it's wrong:** During the reload window, all scheduled jobs are unregistered. Any cron fire due in that window is missed. Under burst load (many operators editing definitions concurrently), the dark windows can overlap or chain.

**Do this instead:** Incremental sync using `add_job(replace_existing=True)` and `remove_job()` for only the changed definitions. Internal scheduler jobs (`__prune_node_stats__`, `__dispatch_timeout_sweeper__`) are never touched.

---

### Anti-Pattern 2: Applying `SKIP LOCKED` Unconditionally

**What people do:** Add `with_for_update(skip_locked=True)` unconditionally to the candidate query.

**Why it's wrong:** SQLite silently ignores `with_for_update()` — the lock clause is not emitted. This is benign for correctness but creates a false expectation that SQLite is protected against multi-process dispatch races (it is not — switching to Postgres is the correct fix for multi-process production use).

**Do this instead:** Guard the `with_for_update` call behind `IS_POSTGRES` defined at engine creation. This makes the intent explicit and prevents future confusion when debugging dispatch issues on dev environments.

---

### Anti-Pattern 3: Setting `pool_size` Without a Dialect Guard

**What people do:** Hardcode `pool_size=20` for all dialects.

**Why it's wrong:** SQLite with `pool_size > 1` creates a queue of connections to a single file. Multiple concurrent write transactions on SQLite produce `database is locked` errors. The dev experience degrades unnecessarily.

**Do this instead:** `pool_size=20 if IS_POSTGRES else 5`. Single-line guard; same file as the engine.

---

### Anti-Pattern 4: `CREATE INDEX` in a Migration Transaction

**What people do:** Wrap `CREATE INDEX` inside a `BEGIN; ... COMMIT;` transaction in a migration SQL file.

**Why it's wrong:** `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block. The command will error with `ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block`. Regular `CREATE INDEX` (without `CONCURRENTLY`) inside a transaction is valid but takes an exclusive table lock, blocking `pull_work` calls during index creation on large job tables.

**Do this instead:** Run `CREATE INDEX CONCURRENTLY IF NOT EXISTS ...` outside any transaction, directly via psql.

---

## Integration Points — Exact File + Line

| Change | File | Location | Scope |
|--------|------|----------|-------|
| Add `pool_size`, `max_overflow`, `pool_pre_ping`, `pool_recycle` | `db.py` | Line 14: `engine = create_async_engine(...)` | Replace 1 line |
| Export `IS_POSTGRES` boolean | `db.py` | After line 12 (DATABASE_URL assignment) | Add 2 lines |
| Composite index on `jobs(status, created_at)` | `db.py` | After last column in `Job` class | Add `__table_args__` tuple, ~3 lines |
| Guard `with_for_update(skip_locked=True)` | `job_service.py` | Lines 647–660: candidate query in `pull_work()` | Wrap in `if IS_POSTGRES`, add import |
| Import `IS_POSTGRES` | `job_service.py` | Top of file, existing `from ..db import ...` line | Add `IS_POSTGRES` to existing import |
| Incremental `sync_scheduler()` | `scheduler_service.py` | Lines 120–144: full method body | Replace method body |
| Fire-and-forget dispatcher | `scheduler_service.py` | Lines 146–253: `execute_scheduled_job()` | Rename to `_execute_scheduled_job_impl`, add thin launcher |
| Migration SQL for composite index | `migration_v17.sql` (new) | `puppeteer/` directory | New file, 4 lines |

---

## Build Order

Recommended sequence — non-breaking changes first, correctness before performance, SQLite compat established before Postgres-only features:

**Step 1: Pool size tuning + `IS_POSTGRES` export** (`db.py`)
- Non-breaking. Changes `pool_size` from 5 to 20 on Postgres (increase; no existing connections affected). SQLite stays at 5.
- No schema changes. No migration. No test changes needed.
- Establishes `IS_POSTGRES` boolean used by all subsequent steps.

**Step 2: Composite index** (`db.py` `__table_args__` + `migration_v17.sql`)
- Non-breaking. `create_all` creates the index on fresh databases. Running `migration_v17.sql` via psql adds it to existing Postgres deployments without downtime.
- Deploy the migration SQL on the live Postgres instance before or immediately after code deploy — `CONCURRENTLY` is safe on live traffic.
- SQLite fresh databases get the index via `create_all` automatically.

**Step 3: Incremental `sync_scheduler()`** (`scheduler_service.py`)
- Correctness fix (eliminates scheduler dark window). No schema changes. No API changes.
- Must preserve the three internal jobs (`__prune_node_stats__`, `__prune_execution_history__`, `__dispatch_timeout_sweeper__`) — the incremental sync must not remove them. Guard by filtering `job.id.startswith("__")` from the set of IDs to remove.
- Test: verify that creating a new job definition does not cause existing job definitions to stop firing.

**Step 4: SKIP LOCKED on `pull_work()`** (`job_service.py`)
- Correctness fix (eliminates double-assignment race on Postgres). SQLite unaffected.
- Requires `IS_POSTGRES` from Step 1.
- Verify transaction scope: the candidate query executes after the first `db.commit()` at line 578 (node upsert). SQLAlchemy automatically begins a new implicit transaction on the next `execute()` call — no manual `BEGIN` needed. The `SKIP LOCKED` lock is held until the final `db.commit()` at the end of `pull_work()`.
- Test: two concurrent `/work/pull` requests against a single PENDING job on Postgres — only one should receive the job.

**Step 5: APScheduler dispatcher isolation** (`scheduler_service.py`)
- Performance fix. Lowest risk as `create_task` wrapping.
- No schema changes. No API changes. No change to `execute_scheduled_job`'s existing logic — just moved to an inner `_impl` method.
- Test: verify cron jobs still fire at the correct times after refactor.

---

## Sources

- [SQLAlchemy 2.0 — Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html) — pool_size, max_overflow defaults and AsyncAdaptedQueuePool
- [SQLAlchemy 2.0 — Async I/O](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — AsyncSession usage patterns
- [SQLAlchemy GitHub Discussion #10460](https://github.com/sqlalchemy/sqlalchemy/discussions/10460) — confirms `with_for_update(skip_locked=True)` emits correct PostgreSQL syntax
- [SQLAlchemy 2.0 — SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) — confirmed: `with_for_update` silently ignored on SQLite
- [APScheduler 3.x User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) — `add_job`, `replace_existing`, `get_jobs`
- [APScheduler 3.x Base Scheduler API](https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/base.html) — `add_job`, `remove_job`, `get_job` method signatures
- [SQLAlchemy 2.0 — Defining Constraints and Indexes](https://docs.sqlalchemy.org/en/20/core/constraints.html) — `Index` in `__table_args__`
- [PostgreSQL CREATE INDEX CONCURRENTLY guide](https://dev.to/mickelsamuel/create-index-concurrently-the-complete-postgresql-guide-b7m) — safe live index creation, transaction restriction

---

*Architecture research for: Axiom v17.0 Scale Hardening*
*Researched: 2026-03-30*
