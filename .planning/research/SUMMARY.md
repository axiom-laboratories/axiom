# Project Research Summary

**Project:** Master of Puppets — v17.0 Scale Hardening
**Domain:** High-throughput distributed job dispatch and scheduler infrastructure (FastAPI + SQLAlchemy async + APScheduler 3.x)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

This milestone is a targeted hardening of the existing Axiom backend to sustain the target operating envelope: 20 nodes, 200+ pending jobs, 1,000 scheduled definitions, and 100 cron fires per minute. The system already runs correctly at lower scale. Research identifies five specific failure modes that emerge at the target envelope: connection pool exhaustion under concurrent node polling, a double-assignment race condition in job dispatch, full-table scans on every work-pull call, a scheduler dark window during definition changes, and event loop saturation when cron burst competes with HTTP request handling.

All four research agents converge on the same recommended approach: no new dependencies, no architectural overhaul. Every fix is a targeted code change to three existing files (`db.py`, `job_service.py`, `scheduler_service.py`) plus one new migration SQL file. The changes are ordered by dependency — pool sizing must come first because the SKIP LOCKED pattern and dispatcher isolation both require connections to be available before they deliver correctness benefits. Incremental scheduler sync and dispatcher isolation are independent of each other and can be combined into one phase after pool sizing is in place.

The primary implementation risk is the SQLite/Postgres dual-mode constraint: every DB-layer change requires dialect detection, and failures in this area are silent — tests pass on SQLite while the production Postgres deployment remains broken. A second risk is APScheduler version drift: v4 has a completely incompatible API and must be explicitly pinned out before any scheduler work begins. Both risks have concrete prevention patterns and must be addressed in the first commit of the milestone.

## Key Findings

### Recommended Stack

No new packages are required for this milestone. All changes are configuration and code modifications to the existing stack. The version pin for APScheduler must be tightened from the current unpinned state to `apscheduler>=3.11.2,<4` — this is the single most important dependency change, and it must land before any scheduler code is touched.

For the asyncpg pool, `create_async_engine` accepts all QueuePool parameters directly. SQLite must be excluded from pool parameter configuration via a `_IS_POSTGRES` flag exported from `db.py`. The `AsyncAdaptedQueuePool` is automatically selected for async engines and requires no manual specification.

**Core technologies:**
- SQLAlchemy asyncio 2.x: async ORM + pool management — `AsyncAdaptedQueuePool` auto-selected; all pool params flow through `create_async_engine` kwargs; no manual pool class specification needed
- asyncpg (current): PostgreSQL async driver — native async, supports `SELECT FOR UPDATE SKIP LOCKED` via SQLAlchemy's `with_for_update(skip_locked=True)`
- aiosqlite (current): SQLite async driver for dev/test — does NOT support `FOR UPDATE`; requires dialect branch in all locking code
- APScheduler `>=3.11.2,<4`: cron scheduling — v4 is a full rewrite (pre-release as of April 2025, 4.0.0a6); `<4` pin is mandatory; 3.11.2 is the current stable release

### Expected Features

All four capabilities are P1 for v17.0. Each addresses either a correctness failure or a performance failure that manifests within the target envelope. The feature dependency graph establishes Capability 1 (pool sizing) as a prerequisite for Capabilities 2 and 4.

**Must have (table stakes — v17.0):**
- DB connection pool right-sized to `pool_size=20, max_overflow=10` with `pool_pre_ping=True` and `pool_recycle=300` — eliminates pool exhaustion under 20-node concurrent polling
- Composite index on `jobs(status, created_at)` — eliminates full-table scan on every `/work/pull` call; required for SKIP LOCKED to be performant at scale
- `SELECT FOR UPDATE SKIP LOCKED` on dispatch with dialect branch — eliminates double-assignment race on Postgres; SQLite write serialisation provides equivalent correctness guarantee
- Incremental `sync_scheduler()` with three-way add/replace/remove diff — eliminates scheduler dark window during definition CRUD
- APScheduler dispatcher isolation via `asyncio.create_task` — decouples cron fire callbacks from the HTTP request event loop

**Operator-configurable (differentiators — v17.0):**
- `AXIOM_DB_POOL_SIZE` / `AXIOM_DB_MAX_OVERFLOW` env vars — lets operators tune for constrained Postgres deployments without forking compose files
- `AXIOM_SCHEDULER_MISFIRE_GRACE_SEC` / `AXIOM_SCHEDULER_COALESCE` env vars — controls cron fire tolerance under load; defaults to `grace=60, coalesce=True`
- Pool stats and event loop lag exposed at `GET /health/scheduling` — surfaces pool utilisation and scheduler health without requiring direct Postgres access

**Defer (v17.x and beyond):**
- Priority queue ordering — extend composite index to `(status, priority DESC, created_at)` once dispatch correctness is proven in production
- Separate OS process for dispatcher (`multiprocessing.Process` with `spawn`) — only warranted if profiling shows HTTP event loop is measurably saturated after `create_task` isolation at the target envelope
- APScheduler 4.x migration — fully rewritten async-native API; plan as a separate future milestone; blocked by complete API incompatibility
- PgBouncer sidecar — only warranted if Postgres is shared across multiple services and `max_connections` is the binding constraint

### Architecture Approach

All changes are confined to three existing files and one new migration SQL file. The `IS_POSTGRES` flag, introduced in `db.py`, threads through to `job_service.py` for the SKIP LOCKED guard. The `migration_v17.sql` file follows the project's established pattern of manual migration SQL files for existing deployments, using `CREATE INDEX CONCURRENTLY` to avoid table locks during live production deployment.

**Major components and required changes:**
1. `db.py` — add `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=300` under `_IS_POSTGRES` guard; add `Index("ix_jobs_status_created_at", "status", "created_at")` to `Job.__table_args__`; export `IS_POSTGRES` boolean for consumers
2. `job_service.py` — guard `with_for_update(skip_locked=True)` behind `if IS_POSTGRES` in the `pull_work()` candidate query (lines 647–660); add `IS_POSTGRES` to existing import from `..db`
3. `scheduler_service.py` — replace `remove_all_jobs()` + full reload with incremental three-way diff using `get_jobs()` / `add_job(replace_existing=True)` / `remove_job()`; rename `execute_scheduled_job` body to `_execute_scheduled_job_impl` and add thin `create_task` launcher; set `job_defaults={'misfire_grace_time': 60, 'coalesce': True}` on `AsyncIOScheduler` constructor
4. `migration_v17.sql` (new, `puppeteer/`) — `CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_status_created_at ON jobs (status, created_at)`; must run outside a transaction block via psql, not wrapped in `BEGIN/COMMIT`

### Critical Pitfalls

1. **SQLite silently ignores `SKIP LOCKED` — no error, no warning, tests pass** — gate all `with_for_update(skip_locked=True)` calls behind `if IS_POSTGRES`; emit a startup `logger.warning` when running on SQLite so the gap is explicit; never run concurrent dispatch correctness tests against SQLite
2. **APScheduler 4.x is a full API rewrite — `pip install --upgrade` silently destroys the scheduler** — pin `apscheduler>=3.11.2,<4` in `requirements.txt` before touching any scheduler code; add startup assertion `assert apscheduler.__version__.startswith("3.")`; annotate the pin in the requirements file so future maintainers do not remove it
3. **SKIP LOCKED lock must be committed in the same `session.begin()` block that acquires it** — if the SELECT and UPDATE span two transactions the lock is released before the status update is durable; use `async with session.begin()` wrapping both the locked SELECT and the status UPDATE; verify the existing `pull_work()` transaction boundary at implementation time
4. **`CREATE INDEX` without `CONCURRENTLY` locks the `jobs` table for the full build duration** — every node heartbeat and work-pull will hang; always use `CREATE INDEX CONCURRENTLY IF NOT EXISTS` in the migration file; run outside any `BEGIN/COMMIT` block; validate with `SELECT indexname FROM pg_indexes WHERE NOT indisvalid` after migration
5. **Full `sync_scheduler()` rebuild drops all jobs before re-adding them — dark window on every CRUD** — the `remove_all_jobs()` + full-reload pattern causes fires to be missed; implement incremental diff from the start; the full-rebuild approach is a correctness trap that looks correct in unit tests but fails under concurrent load

## Implications for Roadmap

Based on the dependency graph in FEATURES.md and the build order confirmed by ARCHITECTURE.md, the milestone should be structured as five sequential phases. Capabilities 1 and 2 (pool + index + SKIP LOCKED) share the same files and the index is a performance prerequisite for SKIP LOCKED, so they ship together. Capabilities 3 and 4 (incremental sync + dispatcher isolation) share `scheduler_service.py` and have no dependency on each other, so they are combined into one phase.

### Phase 1: Foundation — APScheduler Pin + IS_POSTGRES Flag

**Rationale:** APScheduler pin must precede all scheduler work to prevent v4 accidentally being pulled in. The `IS_POSTGRES` flag export is a prerequisite for Phases 2 and 3. Both changes are trivial in scope and zero-risk. The cost of skipping this phase is silent breakage in every subsequent phase.
**Delivers:** `apscheduler>=3.11.2,<4` in `requirements.txt`; startup version assertion; `_IS_POSTGRES` flag in `db.py` exported as `IS_POSTGRES`; SQLite startup warning for SKIP LOCKED gap
**Addresses:** APScheduler 4.x breakage pitfall (Pitfall 2); SQLite dual-mode constraint established for all downstream phases
**Avoids:** Any scenario where scheduler code is written before the version boundary is enforced

### Phase 2: DB Pool Tuning + Connection Health

**Rationale:** Pool exhaustion is the root cause that masks correctness wins from SKIP LOCKED and performance wins from dispatcher isolation. Must be resolved before those phases deliver their full value. Formula: `workers × (pool_size + max_overflow) < postgres max_connections`.
**Delivers:** `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=300` under `IS_POSTGRES` guard; operator env vars `AXIOM_DB_POOL_SIZE` / `AXIOM_DB_MAX_OVERFLOW` / `AXIOM_DB_POOL_RECYCLE`; pool stats (`db_pool_checked_out`) in `GET /health/scheduling`; `POSTGRES_MAX_CONNECTIONS=200` override in `compose.server.yaml`
**Uses:** SQLAlchemy `AsyncAdaptedQueuePool`; `create_async_engine` kwargs; `IS_POSTGRES` from Phase 1
**Avoids:** Pool exhaustion under 20-node concurrent polling (Pitfall 3); `pool_size × workers > max_connections` explosion

### Phase 3: Dispatch Correctness — Composite Index + SKIP LOCKED

**Rationale:** Composite index and SKIP LOCKED are deployed together because the index is a performance prerequisite for SKIP LOCKED at scale — without it each locked SELECT does a full table scan. The correctness fix (no double-assignment) and the performance baseline are established in a single deploy.
**Delivers:** `Index("ix_jobs_status_created_at")` in `Job.__table_args__`; `migration_v17.sql` with `CREATE INDEX CONCURRENTLY IF NOT EXISTS`; `with_for_update(skip_locked=True)` guarded by `IS_POSTGRES` in `pull_work()` covering both the candidate SELECT and the status UPDATE in one `session.begin()` block; integration test for concurrent dispatch against Postgres
**Uses:** SQLAlchemy `with_for_update(skip_locked=True)`; `IS_POSTGRES` from Phase 1; asyncpg pool from Phase 2
**Avoids:** Full-table scan on every work-pull (Scaling Consideration — 50+ nodes); double-assignment race (Pitfall 1); index table lock during live migration (Pitfall 7); SKIP LOCKED lock not committed atomically (Pitfall 4)

### Phase 4: Incremental Scheduler Sync + Dispatcher Isolation

**Rationale:** Both changes are in `scheduler_service.py` and address the scheduler's two failure modes: the dark window during CRUD and the event loop saturation during cron burst. Combining them into one phase avoids touching the same file in consecutive phases and keeps the PR diff cohesive.
**Delivers:** Incremental three-way diff in `sync_scheduler()` replacing `remove_all_jobs()`; internal job guard `if not job.id.startswith("__")` to protect `__prune_node_stats__` and related internal jobs from deletion; `execute_scheduled_job` refactored to thin `create_task` launcher with `_execute_scheduled_job_impl` containing the existing logic; `job_defaults={'misfire_grace_time': 60, 'coalesce': True, 'max_instances': 1}` on scheduler constructor; `AXIOM_SCHEDULER_MISFIRE_GRACE_SEC` and `AXIOM_SCHEDULER_COALESCE` env vars
**Uses:** APScheduler 3.x `get_jobs()` / `add_job(replace_existing=True)` / `remove_job()`; `asyncio.create_task`; pool from Phase 2
**Avoids:** Scheduler dark window on definition CRUD (Pitfall 5); event loop saturation under cron burst (Performance trap — misfire_grace_time too short); fork-inherited event loop risk (Pitfall 6 is avoided entirely because `create_task` keeps everything in-process)

### Phase 5: Observability + Validation Sign-off

**Rationale:** Health endpoint enhancements and integration tests validate that all prior phases delivered their intended guarantees. The concurrent dispatch correctness test against Postgres is the key gate for declaring the milestone complete.
**Delivers:** `db_pool_checked_out` and `event_loop_lag_ms_p95` in `GET /health/scheduling`; integration test verifying two concurrent `/work/pull` requests against a single PENDING job result in only one assignment; startup `logger.warning` for SQLite SKIP LOCKED gap (if not already added in Phase 1); "Looks Done But Isn't" checklist from PITFALLS.md verified against all eight items
**Avoids:** Silent correctness failures that pass all unit tests on SQLite but fail in production Postgres

### Phase Ordering Rationale

- Phase 1 must be first: APScheduler pin prevents accidental v4 installation during development; `IS_POSTGRES` is imported by Phases 2, 3, and 4
- Phase 2 must precede Phases 3 and 4: pool connections must be available for concurrent SKIP LOCKED sessions and for dispatcher fire-callback tasks to each acquire a connection without starvation
- Phase 3 and Phase 4 are independently orderable but share no code paths; grouping by file (Phase 3 touches `db.py` + `job_service.py`, Phase 4 touches only `scheduler_service.py`) keeps PR diffs clean and reviewable
- Phase 5 is last: validates cumulative guarantees of all prior phases, especially the Postgres-only concurrent dispatch test that cannot run against SQLite

### Research Flags

Phases with standard, well-documented patterns — skip `/gsd:research-phase`:
- **Phase 1:** APScheduler version pinning and SQLAlchemy dialect detection are trivially documented; implementation is mechanical
- **Phase 2:** `create_async_engine` pool parameters are from official SQLAlchemy 2.0 docs; pool sizing formula is established; no research needed
- **Phase 3:** `with_for_update(skip_locked=True)` syntax confirmed in SQLAlchemy GitHub discussion #10460; `CREATE INDEX CONCURRENTLY` is standard PostgreSQL DDL; no research needed
- **Phase 4:** APScheduler 3.x `get_jobs()` / `add_job(replace_existing=True)` / `remove_job()` are in the 3.x user guide; `asyncio.create_task` is stdlib; no research needed
- **Phase 5:** Correctness test patterns are standard pytest-asyncio; no new patterns needed

Phases that may benefit from targeted implementation-time checks (not full research phases):
- **Phase 5 (observability):** If `event_loop_lag_ms_p95` metric is implemented, verify the asyncio heartbeat-tick measurement approach against the specific uvicorn event loop version in use; this is a best-effort metric and can be deferred if implementation proves complex

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings from SQLAlchemy 2.0 official docs, APScheduler 3.x official docs, asyncpg docs, and PyPI version history; no new packages; version constraints verified against live package registry |
| Features | HIGH | Feature boundaries are conservative and derived from the existing codebase; dependency graph is internally consistent and confirmed independently by all four research files |
| Architecture | HIGH | Exact file paths, line numbers, and method signatures verified against existing codebase; build order confirmed by cross-referencing FEATURES.md dependency graph with PITFALLS.md phase mapping |
| Pitfalls | HIGH | Seven pitfalls sourced from official docs (SQLAlchemy, APScheduler, PostgreSQL), issue trackers, and verified community post-mortems; all pitfalls include detection signals and recovery strategies |

**Overall confidence:** HIGH

### Gaps to Address

- **`pool_recycle` value alignment:** STACK.md recommends `pool_recycle=300` (5 minutes); ARCHITECTURE.md uses `pool_recycle=1800` (30 minutes) in its example code. Either is acceptable; 300 seconds is more conservative and should be preferred for containers with network restarts. Confirm at Phase 2 implementation time.
- **Internal scheduler job ID naming conventions:** The incremental sync guard `if not job.id.startswith("__")` assumes all internal APScheduler jobs use the `__` prefix. Verify this against the actual job IDs registered in `scheduler_service.py` startup (`__prune_node_stats__`, `__prune_execution_history__`, `__dispatch_timeout_sweeper__`) before Phase 4 implementation to ensure no internal job uses a different naming pattern.
- **`event_loop_lag_ms_p95` measurement implementation:** No single canonical pattern exists in official asyncio docs; the asyncio heartbeat-tick approach is community consensus. Treat as a best-effort metric addition in Phase 5; skip if implementation complexity is disproportionate to the observability value.

## Sources

### Primary (HIGH confidence)
- [SQLAlchemy 2.0 — Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html) — pool_size, max_overflow, pool_pre_ping, AsyncAdaptedQueuePool defaults
- [SQLAlchemy 2.0 — Async I/O](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — AsyncSession usage patterns and transaction constraints
- [SQLAlchemy 2.0 — Constraints and Indexes](https://docs.sqlalchemy.org/en/20/core/constraints.html) — Index in __table_args__ declaration
- [SQLAlchemy GitHub Discussion #10460](https://github.com/sqlalchemy/sqlalchemy/discussions/10460) — confirms `with_for_update(skip_locked=True)` emits correct PostgreSQL syntax; confirms SQLite silently omits FOR UPDATE
- [APScheduler 3.11.2 User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) — AsyncIOScheduler, job_defaults, misfire_grace_time, coalesce, add_job, replace_existing
- [APScheduler 3.x → 4.x Migration Guide](https://apscheduler.readthedocs.io/en/master/migration.html) — breaking changes enumerated; confirmed v4 not production-ready
- [APScheduler PyPI page](https://pypi.org/project/APScheduler/) — 3.11.2 stable confirmed; v4.0.0a6 pre-release confirmed
- [PostgreSQL CREATE INDEX CONCURRENTLY](https://www.postgresql.org/docs/current/sql-createindex.html) — lock behaviour, CONCURRENTLY restrictions, invalid index detection

### Secondary (MEDIUM confidence)
- [Pool sizing formula for ASGI apps — pythontutorials.net](https://www.pythontutorials.net/blog/how-to-properly-set-pool-size-and-max-overflow-in-sqlalchemy-for-asgi-app/) — `workers × (pool_size + max_overflow)` formula; consistent with SQLAlchemy docs reasoning
- [APScheduler scale-out issue #514](https://github.com/agronholm/apscheduler/issues/514) — confirmed AsyncIOScheduler cannot scale beyond 1 CPU without process isolation
- [FastAPI BackgroundTasks event loop discussion #11210](https://github.com/fastapi/fastapi/discussions/11210) — confirms `asyncio.create_task` approach over process isolation for single-server deployment
- [PostgreSQL SKIP LOCKED — inferable.ai](https://www.inferable.ai/blog/posts/postgres-skip-locked) — SKIP LOCKED implementation pattern and transaction handling
- [Solid Queue SKIP LOCKED walkthrough — BigBinary](https://www.bigbinary.com/blog/solid-queue) — production job queue design reference using the same pattern
- [SQLAlchemy Discussion #10697](https://github.com/sqlalchemy/sqlalchemy/discussions/10697) — pool_size and max_overflow sizing guidance

### Tertiary (LOW confidence — inference or single source)
- [asyncpg connection pool best practices — johal.in](https://www.johal.in/gino-asyncpg-connection-pool-best-practices-2025/) — pool_size formula; consistent with official docs but community article
- [Python Bug Tracker #22087](https://bugs.python.org/issue22087) — asyncio multiprocessing fork unsafety; informs Pitfall 6 avoidance recommendation

---
*Research completed: 2026-03-30*
*Ready for roadmap: yes*
