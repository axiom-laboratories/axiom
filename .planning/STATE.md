---
gsd_state_version: 1.0
milestone: v17.0
milestone_name: — Scale Hardening
status: completed
stopped_at: Completed 97-01-PLAN.md
last_updated: "2026-03-30T21:14:22.946Z"
last_activity: "2026-03-30 — Phase 97 Plan 01 complete: asyncpg pool kwargs, ASYNCPG_POOL_SIZE env var, .env.example"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 2
  completed_plans: 2
  percent: 40
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 97 — DB Pool Tuning (v17.0 Scale Hardening)

## Current Position

Phase: 97 of 100 (DB Pool Tuning)
Plan: 1 of 1 in current phase (phase complete)
Status: Phase 97 complete — ready for Phase 98
Last activity: 2026-03-30 — Phase 97 Plan 01 complete: asyncpg pool kwargs, ASYNCPG_POOL_SIZE env var, .env.example

Progress: [████░░░░░░] 40% (v17.0 — 2/5 phases done)

## Accumulated Context

### Key Decisions

- [v17.0 Roadmap]: OBS-03 (concurrent dispatch integration test) assigned to Phase 98 alongside DISP-03/04 — validates the SKIP LOCKED correctness claim at the point of implementation
- [v17.0 Roadmap]: Phase 99 (Scheduler Hardening) depends on Phase 96 only — independent of Phase 97/98; can be planned after Phase 96 completes
- [v17.0 Roadmap]: `apscheduler>=3.10,<4.0` pin (FOUND-01) must land before any scheduler code is touched; APScheduler 4.x is a complete rewrite with no migration path
- [Phase 96-01]: IS_POSTGRES evaluates startswith('postgresql') at module import time — not a DB connection check; test reload avoided in local dev to prevent asyncpg import error
- [Phase 96-01]: APScheduler job_defaults centralized at constructor level removes per-job misfire_grace_time arguments from sync_scheduler
- [Phase 97-01]: _pool_kwargs is module-level (not function-scoped) to allow test imports without asyncpg side effects; max_overflow=10 hardcoded to keep operator tuning surface minimal

### Pending Todos

None.

### Blockers/Concerns

- `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block — migration_v17.sql must carry this caveat explicitly (covered by DOCS-01 in Phase 100)

### Completed Prerequisites

- FOUND-01 (apscheduler pin): done — `requirements.txt` now `apscheduler>=3.10,<4.0`
- FOUND-02 (IS_POSTGRES flag): done — importable from `db`, `scheduler_service`, `job_service`
- FOUND-03 (job_defaults): done — AsyncIOScheduler configured with misfire_grace_time=60, coalesce=True, max_instances=1

## Session Continuity

Last session: 2026-03-30T21:11:40.739Z
Stopped at: Completed 97-01-PLAN.md
Resume file: None
