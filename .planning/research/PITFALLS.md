# Pitfalls Research

**Domain:** Scale hardening additions to an existing FastAPI + SQLAlchemy async + APScheduler 3.x application — SKIP LOCKED, asyncpg pool tuning, incremental sync_scheduler, and dispatcher process isolation
**Researched:** 2026-03-30
**Confidence:** HIGH (findings drawn from SQLAlchemy official docs, APScheduler 3.x and 4.x official docs, asyncpg issue tracker, and verified community post-mortems; confidence levels noted per pitfall)

---

## Critical Pitfalls

### Pitfall 1: SQLite Silently Ignores SKIP LOCKED — Dual-Mode Deployments Break Without Error

**What goes wrong:**
Axiom supports SQLite for local dev and PostgreSQL for production. `with_for_update(skip_locked=True)` in SQLAlchemy on a SQLite backend emits no SQL clause — the `FOR UPDATE SKIP LOCKED` is silently dropped. The query runs, returns rows, and the application proceeds as if the lock was acquired. Under SQLite, two concurrent coroutines (e.g. two `/work/pull` polls hitting the same job row) will both receive the same job and both mark it `RUNNING`, producing double-assignment.

The failure is **silent in logs** — no exception, no warning, no `CompileError`. Tests written against SQLite will pass even after introducing SKIP LOCKED because SQLite's file-level lock serialises writes anyway under low concurrency, masking the gap. The bug only appears when running the PostgreSQL stack with multiple nodes polling simultaneously.

**Why it happens:**
SQLite has no row-level locking at the SQL layer. SQLAlchemy's SQLite dialect omits `FOR UPDATE` constructs rather than raising an error, matching SQLite's "best effort" philosophy. Developers assume "if it compiles and runs, it works."

**How to avoid:**
- Gate the `with_for_update(skip_locked=True)` path behind a dialect check at startup:
  ```python
  # In lifespan or init_db():
  if engine.dialect.name == "sqlite":
      logger.warning("SKIP LOCKED not supported on SQLite — job dispatch race protection disabled")
  ```
- Add an integration test that connects two concurrent async sessions and verifies only one claims the same job row. Run this test against PostgreSQL only (skip marker for SQLite).
- Never rely on SQLite as a proxy for PostgreSQL locking behaviour. The dev stack must also run against PostgreSQL (via Docker Compose) for any locking-related test suite.

**Warning signs:**
- Duplicate `RUNNING` entries for the same job GUID in the `jobs` table (the real canary — query `SELECT guid, COUNT(*) FROM jobs WHERE status='RUNNING' GROUP BY guid HAVING COUNT(*) > 1`)
- Test suite passes on SQLite but fails on PostgreSQL for concurrency tests
- Node logs show two nodes claiming the same job in overlapping heartbeats

**Phase to address:** The phase introducing `with_for_update(skip_locked=True)`. Guard clause and integration test must ship in the same commit as the locking query.

---

### Pitfall 2: APScheduler 3.x → 4.x Is a Full Rewrite — `pip install --upgrade` Silently Destroys the Scheduler

**What goes wrong:**
APScheduler 4.x is a near-complete architectural rewrite. The scheduler class hierarchy, method names, job store interfaces, trigger API, and timezone library are all changed. If the package version is not pinned in `requirements.txt` (or `pyproject.toml`) and a developer runs `pip install --upgrade apscheduler`, or if a dependency resolver pulls in 4.x, the application will fail at import or at first scheduler call — often with cryptic `AttributeError: 'Scheduler' has no attribute 'start'` or `ImportError` messages, not a clean deprecation warning.

Key incompatibilities:
- `BlockingScheduler` and `BackgroundScheduler` → removed; replaced by unified `Scheduler` / `AsyncScheduler`
- `add_job()` → `add_schedule()` (a new `add_job()` exists but means something different: one-shot execution)
- `BackgroundScheduler(jobstores={...}, executors={...})` constructor pattern → keyword args only, no `configure()` method
- `CronTrigger` weekday numbering changed (Sunday=0 in 4.x vs Monday=0 in 3.x) — cron expressions silently fire on wrong days
- `pytz` timezone objects → `zoneinfo` required; `pytz`-based datetimes silently miscalculate in 4.x
- `IntervalTrigger` fires immediately on start in 4.x (not after first interval) — every scheduled job fires once unexpectedly on deploy
- Persistent job store data from 3.x is incompatible with 4.x; no automatic migration exists

**Why it happens:**
PyPI does not enforce semver breaking-change semantics. `apscheduler>=3.0` in a requirements file allows 4.x to be installed. The package author changed the major version specifically to signal incompatibility, but tools like `pip install -U` and loose version specifiers ignore this.

**How to avoid:**
- Pin to `apscheduler>=3.10,<4.0` in `requirements.txt` (or `pyproject.toml`). This is the single most important line for this milestone.
- Add a startup assertion:
  ```python
  import apscheduler
  assert apscheduler.__version__.startswith("3."), \
      f"APScheduler 4.x is not supported — pin to <4.0 (got {apscheduler.__version__})"
  ```
- Add `apscheduler` to a `pip-compile` lockfile or `requirements.lock` with the exact resolved version hash so indirect upgrades cannot slip through.
- Document the pin rationale in a comment adjacent to the dependency so future maintainers do not "fix" it.

**Warning signs:**
- `ImportError: cannot import name 'AsyncIOScheduler' from 'apscheduler.schedulers.asyncio'`
- `AttributeError: 'AsyncScheduler' object has no attribute 'add_job'`
- `TypeError: Scheduler.__init__() got an unexpected keyword argument 'jobstores'`
- Any of these at container startup are the APScheduler 4.x fingerprint

**Phase to address:** The APScheduler pinning phase (explicitly set `<4.0` upper bound). Must be done before any other scheduler work in the milestone.

---

### Pitfall 3: asyncpg Pool Size Increase Exhausts PostgreSQL `max_connections` Across Multiple Workers

**What goes wrong:**
Increasing `pool_size` and `max_overflow` in `create_async_engine()` without accounting for the number of uvicorn workers multiplies the actual connection count at the PostgreSQL server. With 4 workers, `pool_size=10, max_overflow=20` means up to `4 × (10 + 20) = 120` connections. PostgreSQL's default `max_connections=100` is then exceeded, producing `FATAL: sorry, too many clients already` errors that appear as 500s on random requests — not as a clear pool error.

The failure mode is intermittent and load-dependent, making it look like a transient stability problem rather than a configuration misconfiguration.

**Why it happens:**
SQLAlchemy's pool parameters are per-engine, per-process. Developers tuning pool size in isolation (or from docs that show single-process examples) do not multiply by worker count. The PostgreSQL connection limit is also often left at the default value from the base Docker image.

**How to avoid:**
- Calculate: `max_connections ≥ (uvicorn_workers × (pool_size + max_overflow)) + headroom_for_migrations_and_psql`
- For Axiom's target (20 nodes, 4 uvicorn workers): `pool_size=5, max_overflow=10` per worker = 60 connections max, well within a `max_connections=100` default
- Set `pool_pre_ping=True` to detect and discard stale connections from the pool before use (prevents "connection closed" errors after PostgreSQL restarts or idle timeouts)
- Set `pool_recycle=1800` (30 min) to prevent connections from sitting idle long enough to be terminated server-side
- In `compose.server.yaml`, set `POSTGRES_MAX_CONNECTIONS=200` (or equivalent `postgresql.conf` parameter) as an explicit override so the ceiling is known and controlled
- Log pool checkout wait times: configure SQLAlchemy's `pool_timeout` event to emit a warning when a checkout blocks for more than 1 second

**Warning signs:**
- `asyncpg.exceptions.TooManyConnectionsError` or `FATAL: sorry, too many clients already` in logs
- Pool checkout exceptions: `sqlalchemy.exc.TimeoutError: QueuePool limit of size X overflow Y reached`
- PostgreSQL `pg_stat_activity` showing connections from the application at or near `max_connections`

**Phase to address:** The asyncpg pool tuning phase. Set explicit values and add the `max_connections` override to compose files in the same PR.

---

### Pitfall 4: SKIP LOCKED Transaction Not Committed Before Next Poll — Row Locked But Not Updated

**What goes wrong:**
The SKIP LOCKED pattern requires that the lock acquisition (SELECT), the status update (UPDATE to `RUNNING`), and the commit happen atomically within a single transaction. In async SQLAlchemy with autocommit disabled (the default), if the coroutine does `await session.execute(select(...).with_for_update(skip_locked=True))` and then `await session.execute(update(...))` but the `await session.commit()` is reached after the connection is released back to the pool (e.g. due to an exception path), the lock is held until the connection times out, not until the work is done. Other workers skip that row indefinitely.

A related failure: if the session context manager exits (e.g. `async with AsyncSession() as session`) due to an exception before commit, SQLAlchemy issues a `ROLLBACK`, releasing the lock — but the job row is still `PENDING`. Another worker picks it up correctly on the next poll. This path actually works, but developers sometimes add outer `try/except` blocks that swallow the exception before the context manager rolls back, leaving the lock held.

**Why it happens:**
The asyncio call stack can be confusing — `await` points are not always obvious places where control yields and connection state changes. Developers familiar with synchronous SQLAlchemy assume that session state is simpler.

**How to avoid:**
- Always use the `async with session.begin():` pattern (not `session.begin_nested()`), which auto-commits on exit and auto-rolls back on exception:
  ```python
  async with AsyncSession(engine) as session:
      async with session.begin():
          job = await session.execute(
              select(Job).where(Job.status == "PENDING")
              .with_for_update(skip_locked=True)
              .limit(1)
          )
          # update status immediately in same transaction
          job.status = "RUNNING"
      # auto-committed here; lock released
  ```
- Never let a locked row span more than one `session.begin()` block
- Add a database-level `lock_timeout` (e.g. `SET lock_timeout = '5s'`) to prevent runaway lock holds during debugging

**Warning signs:**
- Jobs stuck in `PENDING` indefinitely despite nodes being available (lock is held but transaction never committed)
- PostgreSQL `pg_locks` shows row-level locks (`relation` type with `granted=true`) for sessions that have no active query
- `pg_stat_activity` shows idle connections in transaction state (`state = 'idle in transaction'`)

**Phase to address:** The SKIP LOCKED implementation phase. Review the transaction boundary in `job_service.py` dispatch path as part of the implementation.

---

### Pitfall 5: Full `sync_scheduler()` Rebuild Drops and Re-adds Live Jobs — Misfire Window During Hot Reload

**What goes wrong:**
If `sync_scheduler()` is implemented as "remove all jobs, then re-add all active definitions," there is a window (however brief) where every cron job has been removed. Any cron trigger that would have fired during that window is missed. At 100 fires/minute with 1,000 definitions, even a 50ms rebuild window can drop 1–2 triggers. Additionally, removing and re-adding a job resets APScheduler's internal `next_run_time` calculation, potentially causing a job to fire sooner or later than expected.

Under the existing `LATE/MISSED` detection in APScheduler ScheduledFireLog (v12.0), these rebuilds will produce false MISSED entries in the health log, creating noise that masks real scheduling failures.

**Why it happens:**
A full rebuild is the simplest correct implementation — it avoids the need to diff the current scheduler state against the DB state. Developers reach for it because it is easy to reason about correctness.

**How to avoid:**
- Implement a proper diff: compare the set of job IDs currently in the scheduler against the set of active definitions in the DB. Add only the newly active ones; remove only the deactivated/deleted ones; modify-in-place (via `scheduler.modify_job()`) for changed cron expressions.
- Use APScheduler 3.x's `scheduler.get_job(job_id)` to check existence before adding/removing:
  ```python
  existing_ids = {job.id for job in scheduler.get_jobs()}
  db_ids = {str(defn.id) for defn in active_definitions}
  for add_id in db_ids - existing_ids:
      scheduler.add_job(...)
  for remove_id in existing_ids - db_ids:
      scheduler.remove_job(remove_id)
  ```
- Wrap the entire diff operation in a threading lock (or asyncio lock) to prevent concurrent `sync_scheduler()` calls from racing each other

**Warning signs:**
- Spike of `MISSED` entries in `ScheduledFireLog` immediately after any API call that modifies a job definition
- APScheduler job count briefly drops to 0 in scheduler metrics between a `remove_all_jobs()` and `add_job()` sequence
- Cron jobs that should fire every minute occasionally skip a beat in load tests

**Phase to address:** The incremental `sync_scheduler()` phase. Design the diff algorithm before writing any code — the full-rebuild approach is a trap that looks correct in unit tests but fails under load.

---

### Pitfall 6: Dispatcher Process Isolation — `fork` Inherits Parent's asyncio Event Loop

**What goes wrong:**
If a dedicated dispatcher worker process is created using `multiprocessing.Process` with the default `fork` start method on Linux, the child process inherits the parent's asyncio event loop. The inherited loop may be in a "running" state, causing `RuntimeError: This event loop is already running` when the child tries to start its own scheduling loop. Even if the error is not raised immediately, the child shares the parent's `epoll` file descriptor, meaning I/O events registered by the parent (e.g. WebSocket connections, DB pool sockets) can be "received" by the child process, silently consuming events that should go to the parent.

Additionally, `asyncpg` connection pool connections created in the parent process are inherited by the child. These connections are not safe to use after fork — the child and parent share the same underlying TCP socket, leading to interleaved protocol frames and `asyncpg.exceptions.ConnectionDoesNotExistError` or corrupted query responses.

**Why it happens:**
Linux defaults to `fork` for `multiprocessing.Process`. Asyncio and asyncpg both assume single-process ownership of their internal state. The failure is not immediate on Python 3.10–3.12 (it depends on event loop state at fork time) but becomes consistent under load.

**How to avoid:**
- Use `multiprocessing.set_start_method("spawn")` at the top-level entry point (before any asyncio or asyncpg state is created), or explicitly pass `context=multiprocessing.get_context("spawn")` to `multiprocessing.Process`
- Alternatively, isolate the dispatcher using a subprocess (`asyncio.create_subprocess_exec`) rather than `multiprocessing` — this guarantees a clean Python interpreter with no inherited state
- If using `spawn`, ensure that all configuration is passed via queue/pipe/env, not via shared in-process globals
- **Simplest isolation for this codebase:** move the dispatcher to a separate asyncio coroutine within the same process but running under a separate `asyncio.Task`, communicating with the HTTP API via the DB (not in-memory queues). This avoids multiprocessing entirely while still decoupling scheduling from the request handler path.

**Warning signs:**
- `RuntimeError: This event loop is already running` in the dispatcher child process
- `asyncpg.exceptions.ConnectionDoesNotExistError` immediately after fork
- Parent HTTP API becomes slow or unresponsive when dispatcher fires many jobs (shared epoll fd contention)
- Log messages from the dispatcher and HTTP API interleaved in unexpected ways (stdout not flushed before fork)

**Phase to address:** The dispatcher isolation phase. Architecture decision (multiprocessing vs. subprocess vs. in-process coroutine) must be made before implementation begins.

---

### Pitfall 7: `CREATE INDEX` Without `CONCURRENTLY` Locks the `jobs` Table for the Full Build Duration

**What goes wrong:**
Adding a composite index on `(status, created_at)` to the `jobs` table using a standard `CREATE INDEX` statement acquires a `SHARE` lock on the table for the entire index build duration. This blocks all `INSERT`, `UPDATE`, and `DELETE` operations on the table — including job dispatch, heartbeat updates, and status transitions. On a table with 200+ pending jobs and 20 active nodes polling, this lock can cause:
- Every `/work/pull` endpoint to hang for the duration of the index build
- Node heartbeat timeouts, triggering false OFFLINE transitions
- SQLAlchemy pool exhaustion as connections queue up waiting for the lock

Standard `CREATE INDEX` on a 10k-row jobs table takes under 100ms, but any long-running transaction that was open before the DDL can extend the lock wait indefinitely.

Additionally, if `CREATE INDEX IF NOT EXISTS` is used and a partially-built index exists (e.g. from a previous failed migration), the `IF NOT EXISTS` check passes and the statement is a no-op — leaving the invalid index in place. `CREATE INDEX CONCURRENTLY IF NOT EXISTS` has a known PostgreSQL bug where an invalid index is not reported and the statement completes "successfully" while leaving the index non-functional.

**Why it happens:**
SQLAlchemy's `create_all()` and manual `execute("CREATE INDEX ...")` both use non-concurrent index creation by default. Developers running migrations in staging (low load, fast) don't observe the lock duration and assume production will be fine.

**How to avoid:**
- Always use `CREATE INDEX CONCURRENTLY` for indexes added to hot tables in production migrations:
  ```sql
  CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_status_created_at
      ON jobs (status, created_at);
  ```
- Note: `CREATE INDEX CONCURRENTLY` cannot be run inside a transaction block. Migration scripts must run it outside `BEGIN/COMMIT`.
- After running `CREATE INDEX CONCURRENTLY`, verify the index is not marked invalid:
  ```sql
  SELECT indexname, indisvalid FROM pg_indexes
  JOIN pg_index ON indexrelid = (SELECT oid FROM pg_class WHERE relname = 'jobs')
  WHERE NOT indisvalid;
  ```
- Drop and recreate any invalid indexes found before marking the migration complete
- For SQLite (local dev), `CREATE INDEX IF NOT EXISTS` is fine — SQLite has no concurrent build issue but also no production correctness concern at dev scale

**Warning signs:**
- Application-wide slowdown lasting seconds during migration deployment (lock contention)
- Node heartbeat failures and OFFLINE transitions immediately after a migration run
- `pg_stat_activity` showing many connections blocked waiting on `relation` lock for `jobs`
- `SELECT * FROM pg_indexes WHERE indisvalid = false` returns rows after migration

**Phase to address:** The composite index phase. Migration script must use `CONCURRENTLY` and include the validity check.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Full `sync_scheduler()` rebuild instead of diff | Simple implementation, easy to reason about | MISSED entries in fire log, brief gap in scheduling under load | Never for production — implement diff from the start |
| `pool_size` set to a large value "to be safe" | Fewer pool exhaustion errors in testing | PostgreSQL connection limit exceeded in multi-worker production; harder to debug | Never — calculate from first principles |
| Skipping the dialect guard for SKIP LOCKED | No extra code | SQLite dev deployments silently skip race protection, masking bugs until production | Never — the guard costs 3 lines and prevents a class of production-only race conditions |
| `multiprocessing.fork` for dispatcher | Works in simple test | Inherited event loop / socket corruption under load | Never for async applications — use `spawn` or `subprocess` |
| Non-concurrent index creation in migration | One line simpler | Table lock blocks all job dispatch for build duration | Only on tables guaranteed to be empty (e.g. new tables in the same migration) |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| asyncpg + SQLAlchemy + PgBouncer (transaction mode) | `pool_pre_ping=True` sends `SELECT 1` as a prepared statement, which PgBouncer in transaction mode rejects | Set `connect_args={"prepared_statement_cache_size": 0}` in `create_async_engine` when PgBouncer is in the stack |
| APScheduler 3.x + asyncpg | APScheduler job callbacks that open DB sessions create new connections outside the pool, exhausting PostgreSQL connections | Pass the existing engine/session factory into job callbacks; do not create a new engine inside the job function |
| APScheduler 3.x `AsyncIOScheduler` + multiple uvicorn workers | Each worker starts its own scheduler instance, causing each cron job to fire N times (once per worker) | Use a single-worker deployment for the scheduler process, or use a DB-backed job store with `coalesce=True` to deduplicate across instances |
| `with_for_update(skip_locked=True)` + SQLAlchemy ORM `lazy="select"` relationships | Lazy loading inside a `with_for_update` transaction triggers a second SELECT that does not hold the lock, allowing the relationship data to be stale or race | Use `selectinload()` or `joinedload()` explicitly in the same locked query |
| `CREATE INDEX CONCURRENTLY` + SQLAlchemy `create_all()` | `create_all()` does not support `CONCURRENTLY` — will use standard `CREATE INDEX` | Run index creation as a separate raw SQL migration outside of `create_all()` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| SKIP LOCKED query without index on `(status, created_at)` | Each `/work/pull` call does a full table scan, growing from microseconds to seconds | Add composite index on `(status, created_at)` before enabling SKIP LOCKED at scale | Around 1,000 rows in `jobs` table with normal churn |
| `sync_scheduler()` called on every DB change event via WebSocket broadcast | Scheduler rebuild triggered 10x/second under dashboard activity | Debounce or batch sync calls; only call on job definition CRUD, not on job state changes | >5 concurrent dashboard users with live refresh |
| APScheduler `misfire_grace_time` set too short for burst load | Jobs marked MISSED that were actually only delayed by 1–2 seconds due to event loop saturation | Set `misfire_grace_time=30` (seconds) for cron jobs that tolerate late firing; set to `None` for jobs that must not fire late | >50 simultaneously due cron triggers (e.g. 1,000 definitions all with `*/1 * * * *`) |
| asyncpg `max_overflow=0` (strict pool) | Request latency spikes when all pool connections are busy; `TimeoutError` under bursts | Set `max_overflow` to allow burst headroom (2× `pool_size` is a reasonable default) | >80% pool utilisation, which occurs at ~16 concurrent in-flight requests with `pool_size=5` |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging the full SKIP LOCKED query including job payload on DEBUG | Job script content (which may include credentials or secrets) written to log files | Log only job GUID and status change, never script content or environment variables |
| Setting `pool_pre_ping=True` with a custom `DO $$ BEGIN ... END $$` ping query | Custom ping queries can be used for SQL injection if the query is interpolated | Use the default ping (SQLAlchemy uses `SELECT 1` for asyncpg) — never interpolate user data into pool events |
| Dispatcher process inheriting JWT `SECRET_KEY` from parent environment | Child process has the signing secret; if the child is compromised, arbitrary JWTs can be forged | Pass only the configuration the dispatcher needs; use a separate secret or restrict dispatcher to DB-only operations |

---

## "Looks Done But Isn't" Checklist

- [ ] **SKIP LOCKED implementation:** Verify the lock and the status update are in the same `session.begin()` block — if they span two transactions, SKIP LOCKED provides no protection
- [ ] **APScheduler pin:** Verify `requirements.txt` (or `pyproject.toml`) contains `apscheduler>=3.10,<4.0` — not just `apscheduler>=3.0` which allows 4.x
- [ ] **Pool size calculation:** Verify `pool_size × uvicorn_workers ≤ postgres_max_connections / 2` (leaving headroom for psql, migrations, and monitoring)
- [ ] **Incremental sync test:** Verify that adding a new job definition while another definition's cron fires does not cause the firing to be missed (run concurrent load test)
- [ ] **Index validity check:** After running the `CREATE INDEX CONCURRENTLY` migration, query `pg_index WHERE NOT indisvalid` before marking migration complete
- [ ] **SQLite guard:** Verify that the SKIP LOCKED path emits a warning (not silently succeeds) when `engine.dialect.name == "sqlite"`
- [ ] **Dispatcher isolation:** Verify the dispatcher cannot exhaust the HTTP API's connection pool (they should share the pool or be independently bounded)
- [ ] **Misfire grace time set:** Verify `job_defaults={'misfire_grace_time': 30}` is present in the scheduler constructor — APScheduler 3.x default is 1 second, which is too tight for event-loop-saturated deployments

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| APScheduler 4.x accidentally installed | LOW (if caught immediately) / HIGH (if jobs ran on 4.x API and persisted) | Pin `<4.0` in requirements, rebuild Docker image, restart. If 4.x ran and stored job data, restore from DB backup — no automatic 4.x→3.x migration exists |
| Double-assignment race (SKIP LOCKED missed on SQLite) | MEDIUM | Identify all jobs with duplicate `RUNNING` status; cancel the duplicate; resubmit if output was lost. Add dialect guard before re-deploying |
| Pool exhaustion in production | LOW (recoverable via restart) | Scale down uvicorn workers temporarily, restart app, adjust `pool_size` and `max_overflow` before scaling back up. `PGPASSWORD=... psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name='...' AND state='idle in transaction'"` to clear stuck connections |
| Invalid index left by failed `CREATE INDEX CONCURRENTLY` | LOW | `DROP INDEX CONCURRENTLY ix_jobs_status_created_at` then re-run `CREATE INDEX CONCURRENTLY` during low-traffic window |
| `sync_scheduler()` rebuild causing MISSED entries | LOW | Set `coalesce=True` on affected jobs to absorb the missed fire; investigate and rewrite as incremental diff |
| Fork-inherited event loop in dispatcher | HIGH (requires architecture change) | Switch to `spawn` or `subprocess` approach. Cannot be fixed with a configuration change alone |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SQLite silently ignores SKIP LOCKED | Phase: SKIP LOCKED implementation | Run concurrent dispatch test against PostgreSQL; verify no duplicate RUNNING rows |
| APScheduler 4.x upgrade breakage | Phase: APScheduler pinning (first phase of milestone) | `python -c "import apscheduler; assert apscheduler.__version__ < '4'"` in CI |
| Pool exhaustion across workers | Phase: asyncpg pool tuning | Load test with 4 workers × 20 node polls simultaneously; verify `pg_stat_activity` connection count stays below `max_connections` |
| SKIP LOCKED lock not committed atomically | Phase: SKIP LOCKED implementation | Inspect `job_service.py` dispatch path; verify single `session.begin()` scope covers SELECT and UPDATE |
| Full sync_scheduler rebuild misfires | Phase: incremental sync_scheduler | Benchmark sync under 1,000 active definitions; assert zero MISSED entries during sync |
| Fork inherits asyncio event loop | Phase: dispatcher isolation | Use `spawn` or `subprocess`; verify no `RuntimeError: This event loop is already running` in dispatcher startup |
| Non-concurrent index creation locks table | Phase: composite index migration | Migration script uses `CONCURRENTLY`; post-migration validity check passes |

---

## Sources

- [APScheduler 3.x User Guide — misfire_grace_time, coalesce, max_instances](https://apscheduler.readthedocs.io/en/3.x/userguide.html)
- [APScheduler 3.x → 4.x Migration Guide — breaking changes and architectural overhaul](https://apscheduler.readthedocs.io/en/master/migration.html)
- [SQLAlchemy Discussion #10460 — SKIP LOCKED PostgreSQL only; SQLite silently omits FOR UPDATE](https://github.com/sqlalchemy/sqlalchemy/discussions/10460)
- [SQLAlchemy Issue #5578 — MySQL 5.7 invalid syntax for skip_locked; confirms dialect-specific support](https://github.com/sqlalchemy/sqlalchemy/issues/5578)
- [SQLAlchemy Discussion #10697 — pool_size and max_overflow sizing guidance](https://github.com/sqlalchemy/sqlalchemy/discussions/10697)
- [SQLAlchemy Issue #6467 — prepared_statement_cache_size=0 required for PgBouncer transaction mode](https://github.com/sqlalchemy/sqlalchemy/issues/6467)
- [PostgreSQL Documentation — CREATE INDEX CONCURRENTLY, lock behaviour, invalid index handling](https://www.postgresql.org/docs/current/sql-createindex.html)
- [PostgreSQL Index Locking Considerations — SHARE UPDATE EXCLUSIVE vs SHARE lock](https://www.postgresql.org/docs/current/index-locking.html)
- [Netdata — FOR UPDATE SKIP LOCKED for queue-based workflows](https://www.netdata.cloud/academy/update-skip-locked/)
- [Shayon Chang — Wait, Even SELECT Starts a Transaction? SQLAlchemy session transaction behaviour](https://shanechang.com/p/wait-even-select-starts-a-transaction/)
- [Python Docs — asyncio and fork semantics](https://docs.python.org/3/library/asyncio-dev.html)
- [Python Bug Tracker #22087 — asyncio multiprocessing fork unsafety](https://bugs.python.org/issue22087)
- [pythontutorials.net — asyncio + multiprocessing on Unix: fixing event loop already running](https://www.pythontutorials.net/blog/asyncio-multiprocessing-unix/)
- [Shayon Dovetail — How to safely create unique indexes in PostgreSQL](https://medium.com/dovetail-engineering/how-to-safely-create-unique-indexes-in-postgresql-e35980e6beb5)
- [APScheduler Discussion #913 — single-instance scheduler with multiple uvicorn workers](https://github.com/agronholm/apscheduler/discussions/913)

---
*Pitfalls research for: Scale hardening (v17.0) — SKIP LOCKED, asyncpg pool tuning, incremental sync_scheduler, dispatcher isolation*
*Researched: 2026-03-30*
