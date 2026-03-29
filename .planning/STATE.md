---
gsd_state_version: 1.0
milestone: v16.0
milestone_name: — Competitive Observability
status: Ready to plan
stopped_at: Phase 87
last_updated: "2026-03-29T19:30:00.000Z"
last_activity: 2026-03-29 — Roadmap created for v16.0 (Phases 87–91)
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Milestone v16.0 — Competitive Observability — Phase 87: Research & Design

## Current Position

Phase: 87 of 91 (Research & Design)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-29 — v16.0 roadmap defined; 5 phases (87–91), 17 requirements mapped

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (this milestone)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 87. Research & Design | TBD | - | - |
| 88. Dispatch Diagnosis UI | TBD | - | - |
| 89. CE Alerting | TBD | - | - |
| 90. Job Script Versioning | TBD | - | - |
| 91. Output Validation | TBD | - | - |

## Accumulated Context

### Decisions

- [v16.0 roadmap]: Dispatch diagnosis backend endpoint (`/jobs/{guid}/dispatch-diagnosis`) already exists from v12.0 — Phase 88 is UI-only work
- [v16.0 roadmap]: CE alerting is SMTP email or single webhook URL — no EE licence boundary, no richer channel complexity deferred to EE
- [v16.0 roadmap]: Job script versioning requires new DB table (immutable version records) — schema design is a Phase 87 deliverable before Phase 90 executes
- [v16.0 roadmap]: Output validation contract (how nodes report structured results) must be designed in Phase 87 before Phase 91 backend work begins
- [v16.0 roadmap]: Phase 87 (Research) unblocks all four implementation phases — implementation phases (88–91) may execute in any order after 87 completes

### Pending Todos

Key items carried forward:
- Write upgrade runbook (migration SQL workflow end to end)
- Validate and document Windows local dev getting started path
- USP — hello world job under 30 mins signing UX
- Add screenshots/marketing images to marketing page

### Blockers/Concerns

- [Phase 90]: Job script versioning requires DB schema change (new table) — existing deployments will need a migration SQL file (`migration_v17.sql` or similar)
- [Phase 91]: Output validation requires node-side changes in `node.py` / `runtime.py` to report structured results — coordinate backend contract and node protocol in Phase 87 design

## Session Continuity

Last session: 2026-03-29T19:30:00.000Z
Stopped at: Roadmap written for v16.0 — ready to discuss/plan Phase 87
Resume file: None
