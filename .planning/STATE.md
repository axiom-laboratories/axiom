---
gsd_state_version: 1.0
milestone: v18.0
milestone_name: First-User Experience & E2E Validation
status: planning
stopped_at: Defining requirements
last_updated: "2026-03-31"
last_activity: "2026-03-31 — Milestone v18.0 started. Defining requirements."
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v18.0 — First-User Experience & E2E Validation

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-31 — Milestone v18.0 started

Progress: [██████████] 100%

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
- [Phase 99-01]: _make_cron_callback returns synchronous closure that calls create_task — APScheduler cron fires return immediately, no event-loop blocking under burst load (SCHED-03)
- [Phase 99-01]: diff-based sync_scheduler: internal __ jobs excluded from diff by startswith('__') — protected from any CRUD sync operation (SCHED-01, SCHED-02)
- [Phase 100-01]: require_auth (JWT only) used for /api/health/scale — no RBAC gate needed; scale metrics are observability-only with no sensitive data
- [Phase 100-02]: puppeteer/upgrade.md created as symlink to docs/docs/runbooks/upgrade.md — test path resolves puppeteer/upgrade.md; symlink avoids content duplication while making tests pass
- [Phase 100-02]: OBS-02, DOCS-01, DOCS-02 all complete; v17.0 milestone sign-off ready

### Pending Todos

None.

### Blockers/Concerns

None. CONCURRENTLY caveat documented in upgrade.md (DOCS-01 complete).

### Completed Prerequisites

- FOUND-01 (apscheduler pin): done — `requirements.txt` now `apscheduler>=3.10,<4.0`
- FOUND-02 (IS_POSTGRES flag): done — importable from `db`, `scheduler_service`, `job_service`
- FOUND-03 (job_defaults): done — AsyncIOScheduler configured with misfire_grace_time=60, coalesce=True, max_instances=1
- DISP-01 (composite index): done — `Job.__table_args__` declares `ix_jobs_status_created_at`
- DISP-02 (migration_v44): done — CREATE INDEX CONCURRENTLY IF NOT EXISTS with caveat comment
- DISP-03 (SKIP LOCKED): done — `with_for_update(skip_locked=True)` on Postgres path in pull_work()
- DISP-04 (IS_POSTGRES guard): done — SKIP LOCKED guarded by `if IS_POSTGRES:` in job_service.py
- OBS-03 (concurrent test): done — skip-guarded integration test; passes on SQLite (skipped)
- SCHED-01 (diff-based sync): done — sync_scheduler() never calls remove_all_jobs(); uses diff algorithm with replace_existing=True
- SCHED-02 (internal job protection): done — __ jobs excluded from diff by startswith('__') guard
- SCHED-03 (create_task wrapper): done — _make_cron_callback() returns sync closure; done-callback marks fire_log 'failed'; get_scheduling_health() counts 'failed' rows
- OBS-01 (scale health endpoint): done — GET /api/health/scale with ScaleHealthResponse model; null-safe on SQLite, pool stats on Postgres
- OBS-02 (admin scale metrics): done — Admin Repository Health card shows Pool checkout, Pending jobs, APScheduler rows; N/A guard on SQLite
- DOCS-01 (migration_v44 entry): done — upgrade.md migration table updated; CONCURRENTLY caveat warning block added
- DOCS-02 (v17.0 Scale Hardening docs): done — ASYNCPG_POOL_SIZE tuning formula, APScheduler pin rationale, correctness thresholds table

## Session Continuity

Last session: 2026-03-31T08:51:04.656Z
Stopped at: Completed 100-02-PLAN.md
Resume file: None
