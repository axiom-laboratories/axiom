# Requirements: Axiom v17.0 Scale Hardening

**Defined:** 2026-03-30
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v17.0 Requirements

Target envelope: 20 concurrent polling nodes / 200+ pending jobs / 1,000 scheduled definitions / 100 cron fires per minute.

### Foundation

- [ ] **FOUND-01**: APScheduler pinned to `>=3.10,<4.0` in `requirements.txt` — prevents silent v4.x upgrade breakage (v4 is a complete rewrite, no migration path)
- [ ] **FOUND-02**: `IS_POSTGRES` dialect detection helper available at engine creation — gates all Postgres-only features and prevents SQLite path contamination
- [ ] **FOUND-03**: APScheduler `AsyncIOScheduler` configured with global `job_defaults` (`misfire_grace_time=60`, `coalesce=True`, `max_instances=1`) rather than per-job

### DB Pool

- [ ] **POOL-01**: asyncpg connection pool right-sized for 20+ concurrent polling nodes (`pool_size=20`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=300`)
- [ ] **POOL-02**: `pool_pre_ping=True` configured to detect and discard stale connections before checkout
- [ ] **POOL-03**: Pool size configurable via `ASYNCPG_POOL_SIZE` env var — operator can tune without code changes; documented in `.env.example`
- [ ] **POOL-04**: Pool configuration guarded by `IS_POSTGRES` — SQLite dev path uses default pool (no kwargs that cause SQLite errors)

### Dispatch Correctness

- [ ] **DISP-01**: Composite index `(status, created_at)` declared on `Job` model in `db.py` via `Index("ix_jobs_status_created_at", ...)` — `create_all` handles fresh deployments
- [ ] **DISP-02**: `migration_v17.sql` ships `CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_status_created_at` for existing Postgres deployments (cannot run inside `BEGIN` block)
- [ ] **DISP-03**: Job candidate query in `pull_work()` uses `SELECT FOR UPDATE SKIP LOCKED` to eliminate double-assignment races under concurrent node polling
- [ ] **DISP-04**: SKIP LOCKED guarded behind `IS_POSTGRES` — SQLite path uses existing unguarded query (SQLite serialised writes provide equivalent correctness)

### Scheduler

- [ ] **SCHED-01**: `sync_scheduler()` replaced with diff-based algorithm — computes add/modify/remove sets from current APScheduler state vs DB state, never calls `remove_all_jobs()`
- [ ] **SCHED-02**: Internal system jobs (IDs prefixed `__`) excluded from diff removal in `sync_scheduler()`
- [ ] **SCHED-03**: APScheduler fire callbacks (`execute_scheduled_job`) wrapped in `asyncio.create_task()` — scheduler callback returns immediately, freeing event loop for heartbeats and WebSocket

### Observability

- [ ] **OBS-01**: `GET /health/scale` endpoint returns pool stats (`pool_size`, `checked_out`, `available`, `overflow`), APScheduler job count, and current pending job depth
- [ ] **OBS-02**: Admin dashboard surfaces pool checkout count and pending job depth (extend existing Admin health section — no new page required)
- [ ] **OBS-03**: Integration test verifies zero double-assignment under 5 concurrent `pull_work()` calls against a real Postgres session (not SQLite)

### Documentation

- [ ] **DOCS-01**: `migration_v17.sql` steps added to upgrade runbook — includes pre-flight check, `CONCURRENTLY` caveat (cannot run in transaction block), and validity confirmation query
- [ ] **DOCS-02**: Scale limits section added/updated in operations docs — documents v17.0 thresholds, `ASYNCPG_POOL_SIZE` tuning formula (`pool_size ≤ max_connections / worker_count`), and APScheduler pin rationale

## Future Requirements

### Scale — Post-v17.0

- Dedicated dispatcher process — separate Docker service for cron firing, shares Postgres DB, eliminates event loop coupling entirely (appropriate above ~50 nodes)
- APScheduler 4.x migration — async-native scheduler, built-in distributed support; deferred until 4.x reaches stable release
- `pg_cron` / `procrastinate` evaluation — PostgreSQL-native job queue as alternative to APScheduler for horizontal scale

### Functional

- Job dependencies — job B runs only after job A succeeds (linear then DAG)
- Conditional triggers — run job based on outcome of previous job or external signal

## Out of Scope

| Feature | Reason |
|---------|--------|
| APScheduler 4.x upgrade | v4 pre-release (alpha only); API completely rewritten; no migration path — v17.0 pins away from it |
| Dedicated dispatcher process | Overkill at 20-node target; adds deployment complexity; deferred to post-v17.0 |
| Celery / Redis queue | Introduces external broker dependency; pull model with SKIP LOCKED is sufficient at this scale |
| `pg_cron` replacement | Architectural change; existing APScheduler works at target scale with incremental sync fix |
| Horizontal Puppeteer scaling (multiple replicas) | APScheduler memory store fires independently per replica — requires distributed lock; out of scope v17.0 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 96 | Pending |
| FOUND-02 | Phase 96 | Pending |
| FOUND-03 | Phase 96 | Pending |
| POOL-01 | Phase 97 | Pending |
| POOL-02 | Phase 97 | Pending |
| POOL-03 | Phase 97 | Pending |
| POOL-04 | Phase 97 | Pending |
| DISP-01 | Phase 98 | Pending |
| DISP-02 | Phase 98 | Pending |
| DISP-03 | Phase 98 | Pending |
| DISP-04 | Phase 98 | Pending |
| OBS-03 | Phase 98 | Pending |
| SCHED-01 | Phase 99 | Pending |
| SCHED-02 | Phase 99 | Pending |
| SCHED-03 | Phase 99 | Pending |
| OBS-01 | Phase 100 | Pending |
| OBS-02 | Phase 100 | Pending |
| DOCS-01 | Phase 100 | Pending |
| DOCS-02 | Phase 100 | Pending |

**Coverage:**
- v17.0 requirements: 19 total
- Mapped to phases: 19 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 — traceability complete after roadmap creation*
