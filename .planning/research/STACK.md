# Stack Research

**Domain:** Scale Hardening — asyncpg pool, SKIP LOCKED dispatch, composite indexes, APScheduler tuning, dispatcher isolation
**Researched:** 2026-03-30
**Confidence:** HIGH

---

## Context: Scope of This Milestone

This research covers only the NEW capabilities required for v17.0 Scale Hardening. The existing stack (FastAPI, SQLAlchemy async, asyncpg, APScheduler 3.x, aiosqlite) is validated and not re-researched. All findings are additive changes or configuration adjustments to existing components.

Target envelope: 20+ nodes / 200+ pending jobs / 1,000 scheduled definitions / 100 cron fires per minute without correctness regressions.

---

## Recommended Stack

### Core Technologies (Configuration Changes Only)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| SQLAlchemy asyncio | already installed (2.x) | Async ORM + pool management | `create_async_engine` accepts all QueuePool params directly; `AsyncAdaptedQueuePool` is the auto-selected pool class for async engines |
| asyncpg | already installed | PostgreSQL async driver | Native async, no threading overhead; pool params flow through SQLAlchemy engine kwargs |
| aiosqlite | already installed | SQLite async driver (dev/test) | Used in SQLite fallback path; does NOT support SELECT FOR UPDATE so fallback logic is required |
| APScheduler | `>=3.11.2,<4` | Cron scheduling | 3.11.2 is the current stable (released 2025-12-22); v4 is still alpha (4.0.0a6 as of 2025-04-27) — do not upgrade to v4 |

### Supporting Libraries (No New Installs Needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlalchemy[asyncio]` | already in requirements | Provides `AsyncAdaptedQueuePool`, `with_for_update(skip_locked=True)` | All async DB work; pool config at engine creation time |
| `aiosqlite` | already in requirements | SQLite async bridge | Local dev only; must detect dialect and use `UPDATE ... WHERE status='PENDING' LIMIT 1` fallback instead of SKIP LOCKED |

No new packages are required for this milestone. All changes are configuration, SQL query patterns, and code structure.

---

## Pool Configuration

### asyncpg Pool Parameters (Postgres production path)

Pass directly to `create_async_engine()`. SQLAlchemy automatically selects `AsyncAdaptedQueuePool` for async engines.

```python
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,           # persistent connections kept alive
    max_overflow=20,        # burst capacity; total = pool_size + max_overflow = 30
    pool_timeout=30.0,      # seconds to wait before raising; default is 30
    pool_recycle=300,       # recycle connections older than 5 min (prevents stale conn errors)
    pool_pre_ping=True,     # SELECT 1 health check at checkout; eliminates "connection closed" errors
)
```

**Sizing rationale for target envelope (20 nodes, single Uvicorn worker):**
- Each node polls `/work/pull` every N seconds; peak concurrent DB touches ≈ nodes + HTTP requests ≈ 30-40
- `pool_size=10` covers steady-state; `max_overflow=20` covers cron burst when 100 definitions fire simultaneously
- Formula: `workers * (pool_size + max_overflow) < postgres max_connections` — with 1 worker and pool=10+20, total connections = 30, well within Postgres default of 100
- `pool_pre_ping=True` is essential: Docker network restarts silently drop idle connections; without this, the first post-restart request fails

### SQLite fallback (dev/test path)

SQLite with aiosqlite does NOT support pool sizing parameters meaningfully. Use `NullPool` or accept the default `StaticPool`. Do not configure `pool_size`/`max_overflow` for SQLite — they are ignored or raise errors depending on SQLAlchemy version.

Detect via dialect:

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")
is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_async_engine(DATABASE_URL, echo=False)
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=300,
        pool_pre_ping=True,
    )
```

---

## SELECT FOR UPDATE SKIP LOCKED

### Postgres path

SQLAlchemy 2.x supports `with_for_update(skip_locked=True)` on `select()` statements in async sessions. This is the standard mechanism for lock-free job dispatch: the first session to touch a PENDING job locks it; all other concurrent dispatchers skip it atomically.

```python
from sqlalchemy import select, update

# In job_service.py assign_job() — postgres path
stmt = (
    select(Job)
    .where(Job.status == "PENDING")
    .order_by(Job.created_at.asc())
    .limit(1)
    .with_for_update(skip_locked=True)
)
result = await db.execute(stmt)
job = result.scalar_one_or_none()
if job:
    job.status = "ASSIGNED"
    job.node_id = node.node_id
    await db.flush()   # hold the lock until commit
    await db.commit()
```

**Key constraint:** The session must stay open and commit while the lock is held. Do not use `expire_on_commit=False` patterns that might release the session before the status update commits. Each concurrent dispatch call must use its own `AsyncSession` instance — sessions are not safe to share across concurrent tasks.

**Behavior:** If a PENDING job is already locked by another dispatcher, the query returns `None` instead of blocking. The caller should handle `None` gracefully (no work available). This eliminates double-assignment races entirely.

### SQLite fallback (dev/test)

SQLite does not support `SELECT FOR UPDATE`. SQLAlchemy renders nothing for `with_for_update()` on SQLite — it silently becomes a plain SELECT, which means races can occur. This is acceptable for dev/test (single-process, low concurrency) but must be detected and handled.

Recommended SQLite fallback: issue an `UPDATE ... SET status='ASSIGNED' WHERE guid = (SELECT guid FROM jobs WHERE status='PENDING' ... LIMIT 1)` in a single statement and check `rowcount`. SQLite's exclusive write lock ensures only one writer wins at a time.

```python
from sqlalchemy import text

# SQLite fallback: atomic update-and-claim
result = await db.execute(
    text("""
        UPDATE jobs SET status='ASSIGNED', node_id=:node_id
        WHERE guid = (
            SELECT guid FROM jobs WHERE status='PENDING'
            ORDER BY created_at ASC LIMIT 1
        )
    """),
    {"node_id": node_id}
)
await db.commit()
claimed = result.rowcount > 0
```

Detect which path to use via `db.bind.dialect.name == "sqlite"` or check the engine URL at startup.

---

## Composite Index on the Jobs Table

### Declaration pattern (no Alembic required)

Add `__table_args__` to the `Job` model in `db.py`. SQLAlchemy's `create_all()` will create the index on fresh deployments. For existing deployments, a manual `CREATE INDEX IF NOT EXISTS` migration SQL is required (same pattern as existing `migration_vN.sql` files).

```python
# In db.py — Job model
class Job(Base):
    __tablename__ = "jobs"
    # ... existing columns ...

    __table_args__ = (
        Index('idx_jobs_status_created_at', 'status', 'created_at'),
    )
```

**Why this index:** The job candidate query filters by `status = 'PENDING'` and orders by `created_at ASC`. Without an index, this requires a full table scan on every `/work/pull` call. At 200 pending jobs × 20 nodes polling every 5 seconds = 800 scans/minute. The composite index makes this a single B-tree seek.

**Column order matters:** `(status, created_at)` is correct. The index serves both `WHERE status = 'PENDING'` equality lookups and `ORDER BY created_at` range scans. Reversing them to `(created_at, status)` would not serve the status equality filter efficiently.

**Optional partial index (Postgres only):**

```python
Index(
    'idx_jobs_pending_created_at',
    'created_at',
    postgresql_where=(Job.status == 'PENDING')
)
```

A partial index on only PENDING rows is smaller and faster than the full composite index. However it is Postgres-only and cannot be used in SQLite dev environments. Use the full composite index for cross-dialect compatibility, or add both with dialect detection.

### Migration SQL for existing deployments

```sql
-- migration_v17.sql
CREATE INDEX IF NOT EXISTS idx_jobs_status_created_at ON jobs (status, created_at);
```

---

## APScheduler Pinning and Incremental Job Management

### Version pinning

```
apscheduler>=3.11.2,<4
```

Pin to `<4` explicitly. APScheduler 4 is pre-release (4.0.0a6 as of April 2025) with a completely rewritten API (add_job → add_schedule, different job store schema, new executor concept). The migration guide explicitly warns against using v4 in production. Pin `<4` to prevent accidental upgrade breaking the scheduler.

### misfire_grace_time tuning

The current `sync_scheduler()` sets `misfire_grace_time=60` per job. The APScheduler default is 1 second — this means any job that doesn't fire within 1 second of its scheduled time is marked as misfired and skipped.

At 100 cron fires per minute with a busy event loop, 1-second grace time guarantees missed fires under load. The existing 60-second per-job setting is correct. For global configuration:

```python
self.scheduler = AsyncIOScheduler(
    job_defaults={
        'misfire_grace_time': 60,  # seconds; overrides per-job default of 1s
        'coalesce': True,          # if multiple fires were missed, run once not N times
        'max_instances': 1,        # prevent overlapping runs of the same job
    }
)
```

Setting it globally via `job_defaults` removes the need to pass `misfire_grace_time=60` to every `add_job()` call.

### Incremental sync_scheduler (add/remove instead of remove_all_jobs)

The current `sync_scheduler()` calls `self.scheduler.remove_all_jobs()` then re-adds all definitions. At 1,000 definitions, this is a full rebuild every sync call, causing a brief window where no jobs are scheduled.

Replace with incremental diff:

```python
async def sync_scheduler(self):
    """Incremental sync: add/remove individual jobs instead of full rebuild."""
    async with db_module.AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScheduledJob).where(ScheduledJob.is_active == True)
        )
        db_jobs = {j.id: j for j in result.scalars().all()}

    # Jobs currently in the scheduler (excluding internal housekeeping jobs)
    scheduled_ids = {
        job.id for job in self.scheduler.get_jobs()
        if not job.id.startswith('__')
    }

    db_ids = set(db_jobs.keys())

    # Remove jobs no longer in DB or deactivated
    for job_id in scheduled_ids - db_ids:
        self.scheduler.remove_job(job_id)

    # Add new jobs not yet in scheduler
    for job_id in db_ids - scheduled_ids:
        j = db_jobs[job_id]
        self._schedule_one(j)

    # Reschedule modified jobs (cron expression changed)
    for job_id in db_ids & scheduled_ids:
        j = db_jobs[job_id]
        existing = self.scheduler.get_job(job_id)
        # CronTrigger fields are on existing.trigger; compare cron string via repr
        # Simplest: reschedule unconditionally for modified jobs is safe
        # Only reschedule if cron changed to avoid disrupting next_run_time
```

APScheduler 3.x provides `scheduler.get_job(job_id)` (single job by ID) and `scheduler.get_jobs()` (all jobs) for this diffing. `scheduler.reschedule_job(job_id, trigger=CronTrigger(...))` updates the trigger without removing/re-adding.

### AsyncIOScheduler and event loop coupling

`AsyncIOScheduler` runs jobs as coroutines scheduled onto the existing event loop. It does NOT create a separate process or thread. This means:
- Cron callbacks compete with HTTP request handlers on the same event loop
- Under burst load (100 fires/minute), cron callbacks can delay HTTP responses and vice versa
- `coalesce=True` prevents pileup when the loop is temporarily saturated

---

## Dispatcher Isolation from the HTTP Event Loop

### Problem

`AsyncIOScheduler` fires cron jobs as coroutines on the Uvicorn event loop. A burst of 100 cron fires per minute means 100 coroutines queued on the same loop that handles HTTP. Under load, this degrades HTTP response latency and can cause `misfire_grace_time` violations (the loop is busy when a job fires).

### Options and Recommendation

**Option 1: asyncio.create_task() with bounded semaphore (recommended for this milestone)**

No process isolation — stays on the same event loop but limits concurrency. Add a semaphore around `execute_scheduled_job` to cap concurrent cron callbacks:

```python
self._dispatch_semaphore = asyncio.Semaphore(10)  # max 10 concurrent cron dispatches

async def execute_scheduled_job(self, scheduled_job_id: str):
    async with self._dispatch_semaphore:
        # existing dispatch logic
```

This prevents cron burst from consuming all event loop capacity. Simple, no new dependencies, no inter-process complexity.

**Option 2: run_in_executor with ThreadPoolExecutor**

For CPU-bound or blocking work inside cron callbacks, offload via `asyncio.get_event_loop().run_in_executor()`. The existing cron callbacks are async DB operations (not CPU-bound), so this provides limited benefit and adds complexity.

**Option 3: Separate OS process via multiprocessing.Process**

True isolation — the dispatcher runs its own asyncio event loop in a separate process. HTTP latency is fully protected from scheduler load. However:
- Python multiprocessing cannot share SQLAlchemy async sessions or engines across processes (not picklable)
- IPC between the dispatcher process and HTTP process requires a queue or shared DB state
- Each process needs its own asyncpg pool (adds to total Postgres connections)
- Significantly more complex to implement and debug

**Recommendation:** Use Option 1 (semaphore) for this milestone. It provides the core protection against burst saturation without process isolation complexity. True process isolation is appropriate if profiling shows the HTTP event loop is measurably impacted at the target envelope — that is a v18+ concern.

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `apscheduler>=4` | Pre-release, completely rewritten API, no migration path yet | Pin `apscheduler>=3.11.2,<4` |
| `with_for_update(skip_locked=True)` on SQLite | Silently becomes plain SELECT; races remain | Detect dialect; use single-statement UPDATE fallback on SQLite |
| `pool_size`/`max_overflow` on SQLite engine | Ignored or error depending on version | Only configure pool params when `not is_sqlite` |
| `remove_all_jobs()` on every sync | Causes scheduling gap; slow at 1000+ definitions | Incremental diff via `get_jobs()` + `remove_job()` / `add_job()` |
| `multiprocessing.Process` for dispatcher | Cannot share async sessions; adds pool complexity | asyncio Semaphore for burst control (Option 1 above) |
| Alembic | Not used in this project; schema managed by `create_all` | Declare `Index()` in `__table_args__`; ship `migration_v17.sql` for existing DBs |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `with_for_update(skip_locked=True)` | Application-level distributed lock (Redis, etc.) | When running multiple Uvicorn workers or multiple server replicas; SKIP LOCKED handles single-process concurrency, not multi-process |
| Composite Index in `__table_args__` | Partial index `postgresql_where=(status == 'PENDING')` | Pure Postgres deployments; smaller index, faster scan; not cross-dialect compatible |
| Semaphore for dispatcher isolation | Separate worker process | Only if HTTP p99 latency degrades measurably under cron burst at the target envelope |
| APScheduler 3.11.2 incremental sync | Redis-backed Celery beat | When multi-server deployment is required; overkill for single-server homelab/enterprise target |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `apscheduler>=3.11.2,<4` | Python 3.8+, asyncio | 3.x API is stable and documented; 3.11.2 is latest as of 2025-12-22 |
| `sqlalchemy[asyncio]` 2.x | `asyncpg`, `aiosqlite` | Pool params only apply to QueuePool-based engines (Postgres); ignored for SQLite StaticPool |
| `asyncpg` (any current) | `sqlalchemy` 2.x | `AsyncAdaptedQueuePool` wraps asyncpg natively; no additional config needed |

---

## Installation

No new packages required. Version pin adjustment only:

```bash
# In puppeteer/requirements.txt — change:
apscheduler
# To:
apscheduler>=3.11.2,<4
```

All other changes are code modifications to existing files:
- `puppeteer/agent_service/db.py` — pool config in `create_async_engine`, `__table_args__` on `Job`
- `puppeteer/agent_service/services/job_service.py` — `with_for_update(skip_locked=True)` + SQLite fallback
- `puppeteer/agent_service/services/scheduler_service.py` — `AsyncIOScheduler(job_defaults=...)`, incremental sync, semaphore

---

## Sources

- [SQLAlchemy 2.0 Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html) — pool_size, max_overflow, pool_pre_ping, AsyncAdaptedQueuePool — HIGH confidence
- [SQLAlchemy Asyncio Extension](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — async session constraints, with_for_update — HIGH confidence
- [SQLAlchemy Constraints and Indexes](https://docs.sqlalchemy.org/en/21/core/constraints.html) — __table_args__ Index() declaration — HIGH confidence
- [APScheduler 3.11.2 User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) — AsyncIOScheduler, job_defaults, misfire_grace_time — HIGH confidence
- [APScheduler PyPI page](https://pypi.org/project/APScheduler/) — version 3.11.2 stable confirmed, v4.0.0a6 pre-release confirmed — HIGH confidence
- [APScheduler v4 progress issue](https://github.com/agronholm/apscheduler/issues/465) — v4 API breaking changes, do-not-use-in-production warning — HIGH confidence
- [SQLAlchemy SKIP LOCKED discussion](https://github.com/sqlalchemy/sqlalchemy/discussions/10460) — with_for_update(skip_locked=True) syntax confirmed — MEDIUM confidence (GitHub discussion, not official docs)
- [SQLite SELECT FOR UPDATE limitation](https://groups.google.com/g/sqlalchemy/c/RIBdLP_s6hk) — SQLite ignores with_for_update, fallback required — HIGH confidence
- [Pool sizing formula for ASGI apps](https://www.pythontutorials.net/blog/how-to-properly-set-pool-size-and-max-overflow-in-sqlalchemy-for-asgi-app/) — workers * (pool_size + max_overflow) formula — MEDIUM confidence (community article)
- [FastAPI BackgroundTasks blocks event loop discussion](https://github.com/fastapi/fastapi/discussions/11210) — confirms asyncio semaphore approach over process isolation — MEDIUM confidence

---

*Stack research for: v17.0 Scale Hardening — asyncpg pool, SKIP LOCKED dispatch, composite indexes, APScheduler tuning*
*Researched: 2026-03-30*
