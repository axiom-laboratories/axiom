---
phase: 47-ce-runtime-expansion
plan: 03
subsystem: ui
tags: [react, typescript, jobs, runtime, display_type]

# Dependency graph
requires:
  - phase: 47-02
    provides: display_type and runtime columns in backend API responses

provides:
  - display_type column rendered in Jobs table (e.g. "script (bash)")
  - Runtime dropdown in job submission form (Python / Bash / PowerShell)
  - python_script task type removed from submission form, replaced by script
  - runtime field wired into POST /api/jobs body when task_type is script

affects: [47-ce-runtime-expansion, 48-draft-signing-safety, 50-guided-form]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conditional UI pattern: runtime dropdown shown only when task_type === 'script'"
    - "display_type ?? task_type fallback: server-computed display_type preferred; legacy task_type used as fallback"

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/Jobs.tsx

key-decisions:
  - "Runtime dropdown hidden when task_type is not script — avoids UI confusion for web_task and file_download"
  - "display_type ?? task_type fallback preserves backward compatibility for old python_script jobs that have no server-computed display_type"
  - "Default task_type changed from web_task to script — most common operator use case"

patterns-established:
  - "Conditional field injection: body.runtime only added when task_type === 'script' to keep non-script payloads clean"

requirements-completed: [RT-05]

# Metrics
duration: 15min
completed: 2026-03-22
---

# Phase 47 Plan 03: CE Runtime Expansion Dashboard Summary

**Jobs dashboard updated with display_type column and conditional runtime dropdown; python_script task type removed from form in favour of script + runtime selection**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-22T17:00:00Z
- **Completed:** 2026-03-22T17:15:00Z
- **Tasks:** 2 auto + 1 checkpoint (human-verify)
- **Files modified:** 1

## Accomplishments

- Jobs table Type column now shows server-computed display_type (e.g. "script (bash)", "script (python)") with fallback to raw task_type for legacy records
- Job submission form has a conditional Runtime dropdown (Python / Bash / PowerShell) that appears only when task type is Script
- python_script removed from task type dropdown; replaced by script as the default selection
- runtime field included in POST body only when task_type === 'script'
- Human verifier confirmed: Playwright tests passed — all UI behaviours correct; migration_v38.sql, migration_v36.sql, migration_v37.sql applied to DB; invalid runtime returns 422

## Task Commits

1. **Task 1: Add display_type to Job interface and update table column** - `23bdb6d` (feat)
2. **Task 2: Add runtime dropdown to submission form and wire to POST body** - `d58e833` (feat)

## Files Created/Modified

- `puppeteer/dashboard/src/views/Jobs.tsx` — display_type field added to Job interface; table column updated with display_type ?? task_type ?? '—' fallback; runtime dropdown added conditionally; python_script removed from task type select; runtime injected into POST body when task_type is script

## Decisions Made

- Runtime dropdown hidden for non-script task types — web_task and file_download do not use runtime concept; showing it would confuse operators
- display_type ?? task_type fallback chosen: old python_script jobs in DB have no display_type from server, so task_type acts as graceful degradation
- Default form task_type changed from web_task to script — aligns with most common operator workflow post-runtime-expansion

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. The human verifier noted that migration_v36.sql, migration_v37.sql, and migration_v38.sql were applied manually to the running DB (runtime columns on scheduled_jobs and jobs). These migrations were part of Plans 01 and 02 and were applied as expected side-work of this sprint.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 47 CE runtime expansion is complete across all three plans (node foundation, backend API, dashboard UX)
- Backend: runtime validation, display_type, scheduler runtime field, migration SQL in place
- Frontend: display_type column, runtime dropdown, form defaults all shipped
- Phase 48 (DRAFT signing safety) can begin; Phase 49 (pagination/filtering) can proceed in parallel

---
*Phase: 47-ce-runtime-expansion*
*Completed: 2026-03-22*
