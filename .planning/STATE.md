---
gsd_state_version: 1.0
milestone: v16.0
milestone_name: — Competitive Observability
status: Phase 89 verified — ready for Phase 90
stopped_at: Completed 89-VERIFICATION.md (passed)
last_updated: "2026-03-29T22:40:00Z"
last_activity: "2026-03-29 — Phase 89 verified: all 5 automated checks pass (operator test env limitation noted)"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 5
  completed_plans: 5
  percent: 60
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Milestone v16.0 — Competitive Observability — Phase 89: Complete

## Current Position

Phase: 89 of 91 (CE Alerting) — Complete
Plan: 02 of 02 complete
Status: Phase 89 complete — CE alerting backend + frontend delivered
Last activity: 2026-03-29 — Phase 89 plan 02 complete: NotificationsCard in Admin.tsx, Notifications tab with webhook config UI

Progress: [██████████] 100%

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
| Phase 87 P01 | 2 | 1 tasks | 1 files |
| Phase 88 P01 | 2min | 3 tasks | 3 files |
| Phase 88 P02 | 5min | 3 tasks | 1 files |
| Phase 89 P02 | 2min | 2 tasks | 1 files |

## Accumulated Context

### Decisions

- [v16.0 roadmap]: Dispatch diagnosis backend endpoint (`/jobs/{guid}/dispatch-diagnosis`) already exists from v12.0 — Phase 88 is UI-only work
- [v16.0 roadmap]: CE alerting is SMTP email or single webhook URL — no EE licence boundary, no richer channel complexity deferred to EE
- [v16.0 roadmap]: Job script versioning requires new DB table (immutable version records) — schema design is a Phase 87 deliverable before Phase 90 executes
- [v16.0 roadmap]: Output validation contract (how nodes report structured results) must be designed in Phase 87 before Phase 91 backend work begins
- [v16.0 roadmap]: Phase 87 (Research) unblocks all four implementation phases — implementation phases (88–91) may execute in any order after 87 completes
- [Phase 87]: Dispatch diagnosis: 5s auto-poll, server-side stuck-ASSIGNED detection via timeout*1.2 threshold formula
- [Phase 87]: CE alerting: single webhook URL (HTTP POST) to alerts.webhook_url Config key; EE boundary at multiple destinations
- [Phase 87]: Script versioning: two-table design (job_script_versions + job_definition_history), script_version_id FK on execution_records, Config key versioning.trigger_mode
- [Phase 87]: Output validation: validation_rules JSON column on scheduled_jobs, failure_reason enum with 4 values, dot-notation path syntax, evaluation in job_service.py
- [Phase 88 P02]: Poll useEffect uses stringified GUID join as dependency (array identity instability workaround); benign reason codes (pending_dispatch, not_pending) suppressed from inline display
- [Phase 89 P01]: Event filtering split between job_service (alert-eligible statuses: FAILED/DEAD_LETTER/SECURITY_REJECTED) and webhook_service (enabled flag + security_rejections opt-in); all three admin endpoints gated on nodes:write (accessible to operators)
- [Phase 89 P01]: last_delivery_status persisted as JSON string in existing Config table — no DB migration needed
- [Phase 89 P02]: NotificationsCard uses localUrl state synced from alertsConfig via useEffect; toggle greyed out until URL saved (disabled={!urlSaved}); inline test result via useState (not toast)

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

Last session: 2026-03-29T21:22:34.845Z
Stopped at: Completed 89-02-PLAN.md
Resume file: None
