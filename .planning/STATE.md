---
gsd_state_version: 1.0
milestone: v17.0
milestone_name: — Scale Hardening
status: planning
stopped_at: Phase 96 context gathered
last_updated: "2026-03-30T20:36:48.261Z"
last_activity: 2026-03-30 — v17.0 roadmap created; phases 96–100 defined
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 96 — Foundation (v17.0 Scale Hardening)

## Current Position

Phase: 96 of 100 (Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-30 — v17.0 roadmap created; phases 96–100 defined

Progress: [░░░░░░░░░░] 0% (v17.0)

## Accumulated Context

### Key Decisions

- [v17.0 Roadmap]: OBS-03 (concurrent dispatch integration test) assigned to Phase 98 alongside DISP-03/04 — validates the SKIP LOCKED correctness claim at the point of implementation
- [v17.0 Roadmap]: Phase 99 (Scheduler Hardening) depends on Phase 96 only — independent of Phase 97/98; can be planned after Phase 96 completes
- [v17.0 Roadmap]: `apscheduler>=3.10,<4.0` pin (FOUND-01) must land before any scheduler code is touched; APScheduler 4.x is a complete rewrite with no migration path

### Pending Todos

None.

### Blockers/Concerns

- FOUND-02 (IS_POSTGRES flag) is a hard prerequisite for Phase 97 pool kwargs and Phase 98 SKIP LOCKED guard — Phase 96 must complete before either can start
- `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block — migration_v17.sql must carry this caveat explicitly (covered by DOCS-01 in Phase 100)

## Session Continuity

Last session: 2026-03-30T20:36:48.259Z
Stopped at: Phase 96 context gathered
Resume file: .planning/phases/96-foundation/96-CONTEXT.md
