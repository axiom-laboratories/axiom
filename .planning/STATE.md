---
gsd_state_version: 1.0
milestone: v17.0
milestone_name: — Scale Hardening
status: completed
stopped_at: Phase 99 context gathered
last_updated: "2026-03-31T08:01:53.460Z"
last_activity: "2026-03-30 — Phase 98 Plan 01 complete: SKIP LOCKED in pull_work(), composite index ix_jobs_status_created_at, migration_v44.sql"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 3
  completed_plans: 3
  percent: 60
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 98 — Dispatch Correctness (v17.0 Scale Hardening)

## Current Position

Phase: 98 of 100 (Dispatch Correctness)
Plan: 1 of 1 in current phase (phase complete)
Status: Phase 98 complete — ready for Phase 99
Last activity: 2026-03-30 — Phase 98 Plan 01 complete: SKIP LOCKED in pull_work(), composite index ix_jobs_status_created_at, migration_v44.sql

Progress: [██████░░░░] 60% (v17.0 — 3/5 phases done)

## Accumulated Context

### Key Decisions

- [v17.0 Roadmap]: OBS-03 (concurrent dispatch integration test) assigned to Phase 98 alongside DISP-03/04 — validates the SKIP LOCKED correctness claim at the point of implementation
- [v17.0 Roadmap]: Phase 99 (Scheduler Hardening) depends on Phase 96 only — independent of Phase 97/98; can be planned after Phase 96 completes
- [v17.0 Roadmap]: `apscheduler>=3.10,<4.0` pin (FOUND-01) must land before any scheduler code is touched; APScheduler 4.x is a complete rewrite with no migration path
- [Phase 96-01]: IS_POSTGRES evaluates startswith('postgresql') at module import time — not a DB connection check; test reload avoided in local dev to prevent asyncpg import error
- [Phase 96-01]: APScheduler job_defaults centralized at constructor level removes per-job misfire_grace_time arguments from sync_scheduler
- [Phase 97-01]: _pool_kwargs is module-level (not function-scoped) to allow test imports without asyncpg side effects; max_overflow=10 hardcoded to keep operator tuning surface minimal
- [Phase 98-01]: Two-phase SKIP LOCKED: unlocked 50-row scan + SELECT FOR UPDATE SKIP LOCKED on single chosen row — locks only chosen candidate, not full scan window
- [Phase 98-01]: migration_v44.sql uses CONCURRENTLY — must not run inside psql -1 transaction wrapper; caveat comment added to migration file

### Pending Todos

None.

### Blockers/Concerns

- `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block — migration_v44.sql carries this caveat; DOCS-01 in Phase 100 should cross-reference it

### Completed Prerequisites

- FOUND-01 (apscheduler pin): done — `requirements.txt` now `apscheduler>=3.10,<4.0`
- FOUND-02 (IS_POSTGRES flag): done — importable from `db`, `scheduler_service`, `job_service`
- FOUND-03 (job_defaults): done — AsyncIOScheduler configured with misfire_grace_time=60, coalesce=True, max_instances=1
- DISP-01 (composite index): done — `Job.__table_args__` declares `ix_jobs_status_created_at`
- DISP-02 (migration_v44): done — CREATE INDEX CONCURRENTLY IF NOT EXISTS with caveat comment
- DISP-03 (SKIP LOCKED): done — `with_for_update(skip_locked=True)` on Postgres path in pull_work()
- DISP-04 (IS_POSTGRES guard): done — SKIP LOCKED guarded by `if IS_POSTGRES:` in job_service.py
- OBS-03 (concurrent test): done — skip-guarded integration test; passes on SQLite (skipped)

## Session Continuity

Last session: 2026-03-31T08:01:53.458Z
Stopped at: Phase 99 context gathered
Resume file: .planning/phases/99-scheduler-hardening/99-CONTEXT.md
