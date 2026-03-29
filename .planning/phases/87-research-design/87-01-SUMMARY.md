---
phase: 87-research-design
plan: "01"
subsystem: documentation
tags: [design, v16.0, dispatch-diagnosis, alerting, script-versioning, output-validation, competitor-research]

# Dependency graph
requires:
  - phase: 87-research-design
    provides: 87-CONTEXT.md with all resolved decisions
provides:
  - 87-DESIGN-DECISIONS.md — authoritative design document for all four v16.0 features
  - RSH-01 through RSH-05 all satisfied
affects:
  - 88-dispatch-diagnosis-ui
  - 89-ce-alerting
  - 90-job-script-versioning
  - 91-output-validation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Design-first approach: CONTEXT.md → DESIGN-DECISIONS.md → implementation phases"

key-files:
  created:
    - .planning/phases/87-research-design/87-DESIGN-DECISIONS.md
  modified: []

key-decisions:
  - "Dispatch diagnosis: inline badge at 5s poll, server-side stuck-ASSIGNED detection using timeout*1.2 threshold"
  - "CE alerting: single webhook URL (HTTP POST), alerts.webhook_url Config key, 6-field payload, EE boundary at multiple destinations"
  - "Script versioning: two tables — job_script_versions (immutable snapshots) + job_definition_history (metadata diffs), script_version_id FK on execution_records"
  - "Versioning trigger: script_changes_only default, any_edit alternate, Config key versioning.trigger_mode"
  - "Output validation: validation_rules JSON column on scheduled_jobs, failure_reason enum (execution_error/validation_exit_code/validation_regex/validation_json_field), dot-notation path, backend evaluation in job_service.py"

patterns-established:
  - "Design decisions doc: each requirement gets its own section with full spec including API shapes, DB schemas, and UI surface"
  - "CE/EE boundary: single-destination is CE, multi-destination routing is EE — explicit boundary documented in Phase 87"

requirements-completed: [RSH-01, RSH-02, RSH-03, RSH-04, RSH-05]

# Metrics
duration: 2min
completed: 2026-03-29
---

# Phase 87 Plan 01: Write v16.0 Design Decisions Document Summary

**All five v16.0 design decisions captured: webhook alerting, inline dispatch diagnosis badges, two-table script versioning with execution linkage, and server-evaluated output validation rules**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T19:13:06Z
- **Completed:** 2026-03-29T19:14:45Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `87-DESIGN-DECISIONS.md` with all five RSH-01 through RSH-05 sections
- Mapped competitor pain points (Airflow/Temporal/Prefect/Rundeck/Nomad) to the four v16.0 features
- Specified dispatch diagnosis badge surface, 5s poll interval, stuck-ASSIGNED threshold formula, and server-side endpoint extension requirement
- Specified CE alerting webhook mechanism with payload schema, config key, and CE/EE boundary
- Specified script versioning two-table DB schema with all column definitions, execution_records FK, trigger mode config, API endpoints, and migration file requirement
- Specified output validation JSON schema, all four failure_reason enum values, dot-notation path syntax, and backend evaluation location

## Task Commits

Each task was committed atomically:

1. **Task 87-01-01: Write design decisions document** - `bf9b7f8` (docs)

**Plan metadata:** (upcoming)

## Files Created/Modified
- `.planning/phases/87-research-design/87-DESIGN-DECISIONS.md` — Final v16.0 design decisions document for all four implementation phases

## Decisions Made
- **Auto-poll interval:** 5 seconds (not 10) — chosen for consistency with existing WebSocket cadence; 10s would create visible lag between status update and badge appearing
- **Stuck-ASSIGNED detection location:** Server-side — the endpoint computes the threshold, not the frontend timer, to prevent clock skew issues
- **JSON path syntax:** Dot notation (`result.status`) — simpler than full JSONPath and covers all common use cases

## Deviations from Plan

None — plan executed exactly as written. This was a documentation-only phase; all decisions were pre-resolved in `87-CONTEXT.md`.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `87-DESIGN-DECISIONS.md` is complete and final — all four implementation phases (88–91) are unblocked
- Phases 88–91 may execute in any order; each has its integration point identified in the Cross-Phase Integration Notes section of the design document
- No blockers or concerns

## Self-Check: PASSED

All required files and commits verified present.

---
*Phase: 87-research-design*
*Completed: 2026-03-29*
