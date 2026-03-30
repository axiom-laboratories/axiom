---
gsd_state_version: 1.0
milestone: v16.0
milestone_name: — Competitive Observability
status: completed
stopped_at: Completed 91-03-PLAN.md
last_updated: "2026-03-30T10:26:33.311Z"
last_activity: "2026-03-30 — Phase 91 plan 02 complete: collapsible Validation Rules form in JobDefinitionModal, validation_rules serialization, failure_reason display in DefinitionHistoryPanel/Jobs/History"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 11
  completed_plans: 11
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Milestone v16.0 — Competitive Observability — Phase 90: In Progress

## Current Position

Phase: 91 of 91 (Output Validation) — Complete
Plan: 02 of 02 complete — Phase 91 fully done
Status: Phase 91 plan 02 complete — frontend validation rules form, serialization, and failure_reason display across all three execution history views
Last activity: 2026-03-30 — Phase 91 plan 02 complete: collapsible Validation Rules form in JobDefinitionModal, validation_rules serialization, failure_reason display in DefinitionHistoryPanel/Jobs/History

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
| Phase 90 P90-01 | 18min | 6 tasks | 5 files |
| Phase 90 P90-02 | 18min | 4 tasks | 4 files |
| Phase 90 P90-03 | 8min | 2 tasks | 3 files |
| Phase 91 P01 | 5min | 8 tasks | 6 files |
| Phase 91 P02 | 15min | 6 tasks | 6 files |
| Phase 91 P03 | 2min | 1 tasks | 2 files |

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
- [Phase 90 P01]: Version snapshot created in second commit after create_job_definition (atomicity with initial row); update_job_definition snapshot before final commit (atomic with mutations)
- [Phase 90 P01]: is_signed derived from final job status: ACTIVE=True, DRAFT/REVOKED=False; change_summary derived from field diff at snapshot time
- [Phase 90 P02]: ScriptViewerModal uses React.lazy for ReactDiffViewer to avoid loading diff library until needed; diff mode requires prevVersionNumber > 0
- [Phase 90 P02]: DefinitionHistoryPanel interleaved timeline uses _rowType marker (execution/version) + _sortTs for unified sort; version rows rendered as non-clickable lighter rows
- [Phase 90]: Batch query approach for version_number resolution: collect all definition_version_ids, execute single IN query against JobDefinitionVersion, annotate response objects — avoids N+1 in both list_executions and list_jobs
- [Phase 91 P01]: migration_v45.sql delivers output validation columns for existing deployments (v17 was already taken)
- [Phase 91 P01]: Validation stdout evaluated from raw report.output_log (pre-scrubbing) to preserve full pattern-matching fidelity; failure_reason stored on ExecutionRecord; validation failures are terminal (non-retriable)
- [Phase 91 P02]: Validation form fields are flat (validation_exit_code, validation_stdout_regex, etc.) serialized to nested validation_rules dict in buildValidationRules() at submit time; failure_reason display uses startsWith('validation_') guard to distinguish from runtime failures
- [Phase 91]: [Phase 91 P03]: importlib.util used to load executions_router directly in tests, bypassing ee/routers/__init__.py Blueprint import error (pre-existing foundry_router issue)

### Pending Todos

Key items carried forward:
- Write upgrade runbook (migration SQL workflow end to end)
- Validate and document Windows local dev getting started path
- USP — hello world job under 30 mins signing UX
- Add screenshots/marketing images to marketing page

### Blockers/Concerns

- [Phase 90]: migration_v44.sql delivered for existing deployments — must be applied before upgrading
- [Phase 91]: migration_v45.sql delivered — must be applied before upgrading to pick up validation_rules and failure_reason columns

## Session Continuity

Last session: 2026-03-30T10:26:33.309Z
Stopped at: Completed 91-03-PLAN.md
Resume file: None
