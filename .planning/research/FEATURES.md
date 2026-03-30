# Feature Research

**Domain:** Scale Hardening — High-throughput job dispatch, scheduler isolation, and DB queue correctness (Axiom v17.0)
**Researched:** 2026-03-30
**Confidence:** HIGH (well-established patterns from PostgreSQL queue literature and APScheduler docs; SQLite dual-mode constraints verified)

---

## Scope

Four capability areas for v17.0. Each covers: what high-throughput job systems do in this tier, what operators can observe, what configuration surface should be exposed, what stays internal, and what SQLite/Postgres dual-mode constraints apply.

Target scale: 20 nodes, 200+ pending jobs, 1,000 scheduled definitions, 100 cron fires/minute.

---

## Capability 1: DB Connection Pool Right-Sizing

**Context:** The current asyncpg pool (via SQLAlchemy async) defaults to 5 connections. At 20 nodes polling every few seconds plus HTTP traffic plus cron fires, this pools exhausts under concurrent load and queries serialize. The fix is raising `pool_size` and `max_overflow` to match the actual concurrency footprint.

### Table Stakes

| Feature | Why Expected | Complexity | Notes | SQLite impact |
|---------|--------------|------------|-------|---------------|
| Pool size ≥ 20 connections | Standard formula: N cores × 2 + disk spindles; 20 nodes polling = 20+ near-simultaneous queries | LOW | SQLAlchemy async `create_async_engine(pool_size=20, max_overflow=10)` in `db.py` | SQLite ignores pool_size (single writer; no pool semantics); guard with `if "postgresql" in DATABASE_URL` |
| `pool_pre_ping=True` | Prevents stale connection errors after DB restart or idle timeout | LOW | Already a supported kwarg on `create_async_engine` | N/A for SQLite |
| Idle connection timeout (`pool_recycle`) | Long-lived connections fail silently in containerised Postgres when TCP keepalives expire | LOW | `pool_recycle=300` (5 min) is a safe default; configurable via env var | N/A for SQLite |
| `max_overflow` capped at 2× pool_size | Prevents unbounded connection storm under sudden burst | LOW | `max_overflow=10` with `pool_size=20` = 30 max connections | N/A |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `AXIOM_DB_POOL_SIZE` and `AXIOM_DB_MAX_OVERFLOW` env vars | Operators deploying on constrained Postgres (e.g., Postgres 15 with `max_connections=100` shared across services) need to tune without forking compose files | LOW | Read in `db.py`; fallback to `pool_size=20, max_overflow=10`; document in `.env.example` |
| Pool exhaustion logged as WARN with current stats | Without visibility, pool starvation looks like random slowness; a WARN at checkout-timeout threshold surfaces the issue | MEDIUM | SQLAlchemy `QueuePool` emits events; hook `checkout` to log when pool is exhausted |
| Health endpoint includes pool stats | `GET /health/scheduling` already exists; extend with `db_pool_size`, `db_pool_checked_out` | MEDIUM | Uses `engine.pool.status()` or `engine.pool.checkedout()` |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| PgBouncer as sidecar | "Better connection pooling" | Adds a service to maintain; adds auth configuration complexity; SQLAlchemy's built-in pool handles the target scale cleanly | Only add PgBouncer if Postgres is shared across multiple services and `max_connections` is genuinely constrained |
| Unbounded `max_overflow=0` (no overflow) | "Predictable" | Under burst load this causes HTTP 500s on all requests when pool is full instead of queuing | Allow overflow; set it to a bounded value |
| Per-request DB connection (no pooling) | Simpler to reason about | Creates one connection per request; 20 nodes × poll interval means hundreds of connections/sec; Postgres crashes above ~200 active connections | Pool is non-negotiable at this tier |

### Operator-Visible Impact

- Before: intermittent slow responses under concurrent node polling; no visibility into why
- After: consistent response times; `GET /health/scheduling` shows `db_pool_checked_out: 8/20`; WARN log if pool exhaustion is observed

### Configuration to Expose

| Env Var | Default | Purpose |
|---------|---------|---------|
| `AXIOM_DB_POOL_SIZE` | `20` | asyncpg pool minimum connections |
| `AXIOM_DB_MAX_OVERFLOW` | `10` | Connections above pool_size allowed during burst |
| `AXIOM_DB_POOL_RECYCLE` | `300` | Seconds before idle connection is recycled |

---

## Capability 2: Dispatch Correctness — Composite Index + SELECT FOR UPDATE SKIP LOCKED

**Context:** The current job candidate query does a full table scan (`WHERE status = 'pending' ORDER BY created_at`) and has no row-level locking. Two nodes polling simultaneously can both read the same PENDING job row and both claim it before either commits — double-assignment. At 200+ pending jobs and 20 polling nodes, this race window is large enough to be hit in normal operation. Two changes are needed: a composite index to speed up candidate selection, and `SELECT FOR UPDATE SKIP LOCKED` to make the claim atomic.

### Table Stakes

| Feature | Why Expected | Complexity | Notes | SQLite impact |
|---------|--------------|------------|-------|---------------|
| Composite index on `(status, created_at)` | Without this index, every `/work/pull` does a full `jobs` table scan; at 200+ rows this degrades linearly | LOW | `CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs (status, created_at)` in `init_db()` or migration file | SQLite supports composite indexes; identical DDL works on both |
| `SELECT FOR UPDATE SKIP LOCKED` on dispatch | Eliminates double-assignment race; each polling node atomically claims a job row or skips it | MEDIUM | Requires raw SQL in `job_service.py`; ORM does not generate `SKIP LOCKED` via standard query API; use `text()` or SQLAlchemy `with_for_update(skip_locked=True)` | **SQLite does not support FOR UPDATE.** SQLite's write serialization (only one writer at a time) provides equivalent correctness but different syntax; must branch on dialect |
| Dialect-conditional dispatch path | Maintain correctness on both SQLite (dev) and Postgres (prod) | MEDIUM | `if engine.dialect.name == "postgresql": use SKIP LOCKED else: BEGIN IMMEDIATE` serialization; SQLite write lock via `PRAGMA journal_mode=WAL` + `BEGIN IMMEDIATE` is equivalent for single-process dev | Necessary; cannot drop SQLite support |
| Transaction wraps SELECT + UPDATE atomically | The SELECT and the status UPDATE must be in the same transaction; not two separate round-trips | LOW | Standard within `async with session.begin()` | Both dialects |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `EXPLAIN ANALYZE` captured in DEBUG log on first dispatch | Operators with direct Postgres access can confirm the index is being used | LOW | One-time on startup; log the plan; no runtime overhead |
| Dispatch metrics in health endpoint | `GET /health/scheduling` includes `dispatch_claimed_last_minute`, `dispatch_skipped_locked_last_minute` | MEDIUM | Track counts in memory; reset every minute; surfaces contention at scale |
| Priority column + `ORDER BY priority DESC, created_at ASC` | Once index exists, adding priority ordering is a single `ORDER BY` change that already uses the composite index if `priority` is prepended | MEDIUM | Add `priority` to composite index as `(status, priority DESC, created_at)` if priority column exists |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Application-level optimistic locking (CAS on status column) | "Avoids raw SQL" | Creates a retry loop at the application layer; under high contention many workers waste round-trips; SKIP LOCKED does this in the database with zero retry overhead | Use SKIP LOCKED |
| Redis-based distributed lock for dispatch | "Proper distributed locking" | Adds a new service dependency for a problem Postgres solves natively; Redis lock timeouts add their own failure modes | Postgres SKIP LOCKED is the right tool |
| `NOWAIT` instead of `SKIP LOCKED` | "Faster to fail than skip" | NOWAIT raises an error when a row is locked; the caller must catch and retry; SKIP LOCKED silently skips to the next available row — exactly what a queue consumer needs | SKIP LOCKED |

### Operator-Visible Impact

- Before: occasional duplicate jobs visible in execution history; two `RUNNING` records for the same job ID; nodes receiving the same job payload
- After: each job claimed exactly once; no duplicate execution records; dispatch path is faster on large job backlogs
- SQLite dev behaviour unchanged (correctness guaranteed by write serialization)

### Configuration to Expose

None — this is an internal correctness fix. No operator-facing knobs. Document in ARCHITECTURE.md and migration notes only.

### Migration Note

The composite index is non-destructive and can be added online (`CREATE INDEX CONCURRENTLY` on Postgres; `CREATE INDEX IF NOT EXISTS` on SQLite). Include in `migration_v17.sql`.

---

## Capability 3: Incremental Scheduler Sync

**Context:** `sync_scheduler()` currently rebuilds the entire APScheduler job set on every definition change — remove all, re-add all. At 1,000 scheduled definitions, this full rebuild pauses the scheduler (APScheduler acquires an internal lock during `remove_all_jobs()`), blocks the asyncio event loop for tens of milliseconds, and drops any cron that fires during the rebuild window. The fix is a per-definition add/modify/remove operation that only touches the changed definition.

### Table Stakes

| Feature | Why Expected | Complexity | Notes | SQLite impact |
|---------|--------------|------------|-------|---------------|
| Per-definition `scheduler.add_job()` / `scheduler.reschedule_job()` / `scheduler.remove_job()` | Removes O(N) rebuild; each change is O(1) | MEDIUM | Compare DB definition ID+cron expression against in-memory scheduler jobs; only sync the delta | None; same APScheduler API on both |
| `misfire_grace_time` tuned for burst load | Default is 1 second; at 100 fires/min a scheduler restart that takes 2 seconds will drop 3+ fires | LOW | Set `misfire_grace_time=30` at the scheduler level; overridable per-job on high-frequency definitions | Same |
| `coalesce=True` default on scheduler | Prevents cascade of missed fires triggering in rapid succession after scheduler recovery | LOW | `scheduler.configure(job_defaults={'coalesce': True, 'misfire_grace_time': 30})` | Same |
| APScheduler version pinned | APScheduler 3.x and 4.x have incompatible APIs; pinning prevents silent breakage | LOW | Pin `apscheduler>=3.10,<4.0` in `requirements.txt`; document the 4.x migration path as a future item | Same |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Scheduler health endpoint shows rebuild duration | `GET /health/scheduling` includes `last_sync_duration_ms`; high values indicate rebuild is still being triggered | LOW | Time `sync_scheduler()` on each call; store last value; surface in health endpoint |
| In-memory definition hash cache | On definition read, compare cron expression + target + enabled flag hash against last-synced hash; skip sync if unchanged | MEDIUM | Prevents spurious syncs on read-only admin operations that touch the DB row without changing schedule |
| `max_instances` configurable per definition | Prevents a slow job from spawning 100+ running instances when it falls behind | LOW | Expose `max_instances` field on `ScheduledJob` model; passed to `scheduler.add_job(max_instances=N)` |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| APScheduler 4.x migration | "Use the modern version" | APScheduler 4.x rewrites the API entirely; every `add_job()` call site changes; SQLAlchemy jobstore APIs differ; high risk for a hardening milestone | Pin 3.x; plan migration as a separate milestone after hardening is proven |
| DB-backed APScheduler jobstore | "Persistent scheduler across restarts" | APScheduler's DB jobstore adds a second writer to the jobs table, complicating the SKIP LOCKED dispatch logic; at 1,000 definitions the in-memory store is sufficient | Keep in-memory store; rebuild from DB definitions on startup (already the current pattern) |
| Distributed multi-process scheduler | "Horizontal scale" | Requires a distributed lock (e.g., pg_advisory_lock) to prevent duplicate fires from two scheduler instances; adds significant complexity for a target of 20 nodes | Single-process scheduler is correct at this tier |

### Operator-Visible Impact

- Before: creating/editing a definition causes all cron fires to pause for ~50–200ms; visible as LATE entries in the scheduling health log at 1,000 definitions
- After: definition edits are instant; no pause; `last_sync_duration_ms` drops from hundreds of ms to single-digit ms
- `max_instances` field on definitions lets operators prevent runaway job fan-out

### Configuration to Expose

| Env Var | Default | Purpose |
|---------|---------|---------|
| `AXIOM_SCHEDULER_MISFIRE_GRACE_SEC` | `30` | Seconds a cron job can be late before being dropped |
| `AXIOM_SCHEDULER_COALESCE` | `true` | Roll up missed fires into one when scheduler recovers |

Field on `ScheduledJob` model:

| Field | Default | Purpose |
|-------|---------|---------|
| `max_instances` | `1` | Maximum concurrent running instances of this cron job |

---

## Capability 4: Scheduler Process Isolation

**Context:** APScheduler's `AsyncIOScheduler` runs its fire callbacks directly on the uvicorn event loop. Each cron fire dispatches a job (DB write), and at 100 fires/min this is ~1.7 fires/second competing with HTTP requests and WebSocket heartbeats on the same event loop. Under burst load (e.g., hourly job burst at :00) the event loop saturates: heartbeat ACKs arrive late, nodes flip OFFLINE, HTTP responses stall. The fix is decoupling the scheduler from the HTTP-serving event loop.

### Table Stakes

| Feature | Why Expected | Complexity | Notes | SQLite impact |
|---------|--------------|------------|-------|---------------|
| Scheduler fires in an isolated context | High-throughput job systems universally separate scheduling (tick/fire) from request serving | HIGH | Two options: (a) `run_in_executor` with `ThreadPoolExecutor` for the fire callback; (b) separate OS process via `multiprocessing`. Option (a) is lower risk and sufficient at this tier | SQLite writer serialization means a separate process needs careful IPC; ThreadPoolExecutor is safer for dual-mode |
| Fire callback is non-blocking (no sync DB calls) | If the fire callback does a synchronous DB write on the event loop thread, isolation provides no benefit | MEDIUM | Ensure `dispatch_scheduled_job()` is a proper `async def`; all DB calls use `await session.execute()` | Same requirement |
| Event loop lag metric in health endpoint | Without measurement, saturation is invisible | MEDIUM | Track time between asyncio heartbeat ticks; `GET /health/scheduling` includes `event_loop_lag_ms_p95` | Same |
| Graceful degradation: cron fires queue in memory if DB is slow | At 100 fires/min, a 2-second DB stall means 3 fires back up; they should not block the next fire | MEDIUM | APScheduler `coalesce=True` handles this at the scheduler level; see Capability 3 | Same |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `AXIOM_SCHEDULER_EXECUTOR` env var (`inline` / `thread`) | Operators can choose `inline` for dev (simpler debugging) and `thread` for prod (isolation) | LOW | Default `thread`; `inline` reproduces current behaviour for local dev/SQLite scenarios |
| Thread executor pool size configurable | At 100 fires/min the thread pool needs enough slots to handle burst; default 4 threads is reasonable | LOW | `AXIOM_SCHEDULER_THREAD_WORKERS=4` env var; passed to `ThreadPoolExecutor(max_workers=N)` |
| Separate process option documented as advanced | A separate process (`multiprocessing.Process`) provides true CPU isolation but requires IPC design (shared DB as message bus); document as a future option | LOW | Documentation only for v17.0; implementation deferred |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Celery for scheduling | "Industry standard" | Adds Redis/RabbitMQ broker dependency, Celery worker containers, and a completely different task serialization model; massively disproportionate to the target of 100 fires/min | APScheduler with ThreadPoolExecutor isolates the event loop without new dependencies |
| Gunicorn multi-worker process | "Easy horizontal scale" | Multiple uvicorn workers means multiple APScheduler instances; each fires its own cron, causing duplicate dispatches without distributed locking | Stay single process for the scheduler; scale stateless HTTP separately if needed |
| asyncio.create_task() for fire callbacks | "Keeps everything on one event loop cleanly" | The problem IS the event loop being saturated; adding more tasks makes it worse | Move to ThreadPoolExecutor to give the fire callbacks OS-level threads off the event loop |

### Operator-Visible Impact

- Before: under burst cron load (e.g., 20 jobs scheduled at :00), heartbeat WebSocket messages stall; nodes show as OFFLINE briefly; dashboard WebSocket reconnects
- After: event loop stays responsive; heartbeats acknowledged on time; `event_loop_lag_ms_p95` < 50ms under burst load
- No dashboard UX changes; improvement is observable via health endpoint and node online/offline stability

### Configuration to Expose

| Env Var | Default | Purpose |
|---------|---------|---------|
| `AXIOM_SCHEDULER_EXECUTOR` | `thread` | `inline` (dev, event loop) or `thread` (prod, ThreadPoolExecutor) |
| `AXIOM_SCHEDULER_THREAD_WORKERS` | `4` | Thread pool size for cron fire callbacks |

---

## Feature Dependencies

```
[Capability 1: DB Pool Right-Sizing]
    prerequisite for --> [Capability 2: SKIP LOCKED] (SKIP LOCKED requires connections
                         to be available when multiple nodes poll simultaneously)
    prerequisite for --> [Capability 4: Scheduler Isolation] (fire callback threads
                         each need a DB connection)

[Capability 2: Dispatch Correctness — Index + SKIP LOCKED]
    requires         --> Postgres dialect branch (dual-mode SQLite/Postgres)
    requires         --> transaction context in job_service.py dispatch path
    enhances         --> [Capability 1] (index makes pool connections return faster)

[Capability 3: Incremental Scheduler Sync]
    independent from --> [Capability 2] (different code paths)
    enhances         --> [Capability 4] (smaller sync operations mean less time
                         holding the scheduler lock during fire window)

[Capability 4: Scheduler Process Isolation]
    requires         --> [Capability 1] (needs pool to handle dispatcher threads)
    enhanced by      --> [Capability 3] (incremental sync reduces lock contention
                         competing with fire callback threads)
```

### Dependency Notes

- **Capability 1 should be built first.** Pool starvation will mask correctness wins from Capability 2 and perf wins from Capability 4 if not addressed first.
- **Capability 2 is the highest correctness risk.** The dialect branch for SKIP LOCKED vs SQLite serialization is the most error-prone piece; it needs dedicated testing.
- **Capabilities 3 and 4 are independently deliverable** after Capability 1. They address different bottlenecks (scheduler rebuild time vs event loop saturation) with no shared code paths.
- **SQLite dual-mode is a constraint throughout.** Every DB-layer change must be gated on `engine.dialect.name`. Failing to do this will break local dev and the CI suite.

---

## MVP Definition

### Launch With (v17.0)

All four capabilities are in scope. Recommended build order based on dependencies and risk:

- [ ] Capability 1: DB pool right-sizing — `pool_size=20, max_overflow=10, pool_recycle=300, pool_pre_ping=True`; env vars in `.env.example`; health endpoint DB pool stats
- [ ] Capability 2: Composite index + SKIP LOCKED — `migration_v17.sql` with index DDL; dialect-conditional dispatch in `job_service.py`; correctness test for concurrent dispatch
- [ ] Capability 3: Incremental scheduler sync — per-definition add/modify/remove in `scheduler_service.py`; misfire grace + coalesce defaults tuned; `max_instances` field on `ScheduledJob`
- [ ] Capability 4: Scheduler thread isolation — fire callbacks routed to `ThreadPoolExecutor`; `AXIOM_SCHEDULER_EXECUTOR` env var; `event_loop_lag_ms_p95` in health endpoint

### Add After Validation (v17.x)

- [ ] Priority queue ordering — extend composite index to `(status, priority DESC, created_at)` once dispatch correctness is proven
- [ ] Dispatcher metrics dashboard panel — visualise `dispatch_claimed_last_minute`, `event_loop_lag_ms_p95` in the existing scheduling health tab
- [ ] Separate process scheduler — full OS-level isolation via `multiprocessing`; requires IPC design; defer until thread isolation proves insufficient

### Future Consideration (v18+)

- [ ] APScheduler 4.x migration — new API, async-native, better distributed support; blocked by API incompatibility with current 3.x codebase
- [ ] PgBouncer sidecar — only warranted if Postgres is shared with other services and `max_connections` is the binding constraint
- [ ] Horizontal scaling (multiple uvicorn workers + distributed scheduler lock) — only needed beyond 50+ nodes; requires `pg_advisory_lock` or equivalent

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| DB pool right-sizing (Cap 1) | HIGH — eliminates root cause of intermittent slowness | LOW | P1 |
| Composite index + SKIP LOCKED (Cap 2) | HIGH — eliminates correctness bug; double-assignment is data integrity failure | MEDIUM | P1 |
| Incremental scheduler sync (Cap 3) | MEDIUM — observable only at 1,000 definitions; affects cron fire reliability | MEDIUM | P1 |
| Scheduler thread isolation (Cap 4) | MEDIUM — observable under burst cron load; node online/offline stability | HIGH | P1 |
| Priority queue ordering | MEDIUM — operator convenience | LOW | P2 |
| `event_loop_lag_ms_p95` metric | MEDIUM — observability without it is blind | LOW | P2 |
| Separate process scheduler | LOW — overkill at 20 nodes | HIGH | P3 |
| APScheduler 4.x migration | LOW for v17.0 scope | HIGH | P3 |

---

## Competitor Feature Analysis

How comparable systems handle the same scale tier:

| Feature | Solid Queue (Rails) | BullMQ (Node.js) | Temporal (Go) | Axiom v17.0 Approach |
|---------|---------------------|------------------|---------------|----------------------|
| Dispatch correctness | `FOR UPDATE SKIP LOCKED` — core design | Redis atomic operations | DB-backed with optimistic locking | `FOR UPDATE SKIP LOCKED` on Postgres; dialect branch for SQLite |
| Connection pool | ActiveRecord pool, configurable | ioredis connection pool | gRPC connection pool | asyncpg via SQLAlchemy; env-var configurable |
| Scheduler isolation | Separate Solid Queue dispatcher process | Separate BullMQ worker process | Separate workflow worker | ThreadPoolExecutor in same process (sufficient for target scale) |
| Incremental sync | Jobs stored in DB; no in-memory rebuild | Redis entries modified individually | Workflow definitions versioned individually | Per-definition add/modify/remove; no full rebuild |
| Misfire handling | configurable `discard_after` | `removeOnFail`, `removeOnComplete` | Retry policies per workflow | `misfire_grace_time=30`, `coalesce=True` defaults |

---

## Sources

- [PostgreSQL SKIP LOCKED documentation (inferable.ai)](https://www.inferable.ai/blog/posts/postgres-skip-locked) — SKIP LOCKED implementation pattern, transaction handling; confidence HIGH
- [Postgres queue scaling to 100K events (RudderStack)](https://www.rudderstack.com/blog/scaling-postgres-queue/) — composite index patterns for queue workloads; confidence HIGH
- [APScheduler 3.x user guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) — `misfire_grace_time`, `coalesce`, executor configuration; confidence HIGH (official docs)
- [APScheduler executor asyncio issue #304](https://github.com/agronholm/apscheduler/issues/304) — ThreadPoolExecutor default behaviour on AsyncIOScheduler; confidence HIGH
- [asyncpg connection pool best practices (2025, johal.in)](https://www.johal.in/gino-asyncpg-connection-pool-best-practices-2025/) — pool_size formulas, idle timeout; confidence MEDIUM
- [SQLite transaction types (SQLite docs)](https://docs.sqlitecloud.io/docs/sqlite/lang_transaction) — BEGIN IMMEDIATE for write serialization; confidence HIGH (official docs)
- [SQLite FOR UPDATE absence (SQLAlchemy group)](https://groups.google.com/g/sqlalchemy/c/RIBdLP_s6hk) — confirmed SQLite does not support FOR UPDATE; writer serialization is the SQLite equivalent; confidence HIGH
- [Solid Queue SKIP LOCKED walkthrough (BigBinary)](https://www.bigbinary.com/blog/solid-queue) — production job queue using SKIP LOCKED at scale; confidence HIGH
- [APScheduler scale-out issue #514](https://github.com/agronholm/apscheduler/issues/514) — confirmed AsyncIOScheduler cannot scale to more than 1 CPU without process isolation; confidence HIGH
- Axiom codebase: `puppeteer/agent_service/services/job_service.py`, `scheduler_service.py`, `db.py`, `main.py` — primary source; confidence HIGH

---

*Feature research for: Axiom v17.0 Scale Hardening*
*Researched: 2026-03-30*
