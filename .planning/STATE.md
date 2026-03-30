---
gsd_state_version: 1.0
milestone: v17.0
milestone_name: — Scale Hardening
status: executing
stopped_at: Completed 96-01-PLAN.md
last_updated: "2026-03-30T21:46:00.000Z"
last_activity: 2026-03-30 — Phase 96 Plan 01 complete (FOUND-01/02/03)
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 1
  completed_plans: 1
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 96 — Foundation (v17.0 Scale Hardening)

## Current Position

Phase: 96 of 100 (Foundation)
Plan: 1 of 1 in current phase (phase complete)
Status: Phase 96 complete — ready for Phase 97
Last activity: 2026-03-30 — Phase 96 Plan 01 complete: IS_POSTGRES, APScheduler pin, job_defaults, startup guards

Progress: [██░░░░░░░░] 20% (v17.0 — 1/5 phases done)

## Accumulated Context

### Key Decisions

- [v17.0 Roadmap]: OBS-03 (concurrent dispatch integration test) assigned to Phase 98 alongside DISP-03/04 — validates the SKIP LOCKED correctness claim at the point of implementation
- [v17.0 Roadmap]: Phase 99 (Scheduler Hardening) depends on Phase 96 only — independent of Phase 97/98; can be planned after Phase 96 completes
- [v17.0 Roadmap]: `apscheduler>=3.10,<4.0` pin (FOUND-01) must land before any scheduler code is touched; APScheduler 4.x is a complete rewrite with no migration path
- [Phase 96-01]: IS_POSTGRES evaluates startswith('postgresql') at module import time — not a DB connection check; test reload avoided in local dev to prevent asyncpg import error
- [Phase 96-01]: APScheduler job_defaults centralized at constructor level removes per-job misfire_grace_time arguments from sync_scheduler

### Pending Todos

None.

### Blockers/Concerns

- `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block — migration_v17.sql must carry this caveat explicitly (covered by DOCS-01 in Phase 100)

### Completed Prerequisites

- FOUND-01 (apscheduler pin): done — `requirements.txt` now `apscheduler>=3.10,<4.0`
- FOUND-02 (IS_POSTGRES flag): done — importable from `db`, `scheduler_service`, `job_service`
- FOUND-03 (job_defaults): done — AsyncIOScheduler configured with misfire_grace_time=60, coalesce=True, max_instances=1

## Session Continuity

Last session: 2026-03-30T20:47:21.990Z
Stopped at: Completed 96-01-PLAN.md
Resume file: None
