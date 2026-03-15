---
phase: 19-dashboard-staging-view-and-governance-doc
plan: "02"
subsystem: ui
tags: [react, typescript, job-definitions, staging, script-inspection, publish, pushed_by]

# Dependency graph
requires:
  - phase: 17-backend-oauth-device-flow-and-job-staging
    provides: status field on ScheduledJob, pushed_by field, script_content field, PATCH /jobs/definitions/{id} accepting status updates
  - phase: 19-01
    provides: Status badges, tabbed view foundation, JobDefinition interface with status/pushed_by fields
provides:
  - Expandable script inspection panel (click chevron to reveal monospaced source payload inline)
  - Publish button on DRAFT rows — PATCH /jobs/definitions/{id} with { status: 'ACTIVE' }
  - pushed_by attribution displayed below job name in the definitions table
affects: [19-03, 19-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Expandable TableRow pattern: expandedRows Record<string,boolean> state + toggleRow() + sibling TableRow rendered when expandedRows[id] is true"
    - "Conditional publish button: rendered only when def.status === 'DRAFT' && onPublish prop provided"
    - "Attribution sub-label: pushed_by shown as italic text below job name when non-null"

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/JobDefinitions.tsx
    - puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx

key-decisions:
  - "Expandable row as sibling TableRow (not a nested component) — colSpan=7 gives full-width script panel without breaking table layout"
  - "Script panel uses <pre><code> with max-h-[400px] overflow-x-auto — handles long scripts without breaking page layout"
  - "Publish button only rendered when onPublish prop is provided AND status === 'DRAFT' — prevents accidental use on non-draft jobs"
  - "handlePublish() in JobDefinitions.tsx uses existing PATCH endpoint with { status: 'ACTIVE' } — no new backend route needed"
  - "pushed_by shown as italic sub-label below job name — inline, non-disruptive, visible without click"

patterns-established:
  - "Expandable row pattern: expandedRows state + toggleRow() + conditional sibling <TableRow> — reusable for any table needing inline detail panels"
  - "Conditional action button: check both prop presence and data condition before rendering — prevents ghost buttons from appearing"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 19 Plan 02: Staging Features & Publishing Summary

**Script inspection (expandable inline panel), one-click DRAFT-to-ACTIVE publish, and pushed_by attribution added to the Job Definitions table**

## Performance

- **Duration:** 2 min (work already in working tree from same commit as Plan 01)
- **Started:** 2026-03-15T15:30:14Z
- **Completed:** 2026-03-15T15:32:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Expandable script inspection row: clicking the chevron icon on any job row reveals the full script source in a monospaced panel with syntax-appropriate max-height and horizontal scroll
- Publish action button (Send icon) appears on DRAFT rows only — sends `PATCH /jobs/definitions/{id}` with `{ status: 'ACTIVE' }`, toasts success/failure, and refreshes the list
- pushed_by attribution shown inline as italic sub-label below the job name for all jobs that were pushed via the CLI

## Task Commits

All three tasks were implemented together in one commit alongside Plan 19-01 work:

1. **Task 1: Implement Script Inspection** - `8c0ce03` (feat)
2. **Task 2: Implement Publish Logic** - `8c0ce03` (feat)
3. **Task 3: Enhance Job Metadata Display (pushed_by)** - `8c0ce03` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified
- `puppeteer/dashboard/src/views/JobDefinitions.tsx` - Added `handlePublish()` function that PATCHes status to ACTIVE, passed as `onPublish` prop to `JobDefinitionList`
- `puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx` - Added `expandedRows` state and `toggleRow()`, expandable script panel as sibling TableRow, Publish (Send) button visible only for DRAFT jobs, pushed_by sub-label below job name

## Decisions Made
- Script panel as a sibling `<TableRow>` with `colSpan={7}` rather than a modal — keeps context in the table, no overlay required for a read-only view
- `max-h-[400px] overflow-x-auto` on the `<pre>` element — long scripts stay readable without pushing other rows off screen
- Publish button guard (`def.status === 'DRAFT' && onPublish`) — belt-and-suspenders; both the prop (ACTIVE tab hides it implicitly) and the status check must pass
- `toast.success` / `toast.error` feedback on publish — user gets immediate confirmation without needing to scan the list for the status change

## Deviations from Plan
None - all three tasks from the plan are implemented as specified. Work was already present in the working tree; this summary documents the implementation and records the commit.

## Issues Encountered
None — implementation was already complete in the working tree prior to this execution.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Script inspection and one-click publish are functional; Plan 19-04 E2E walkthrough (push DRAFT via CLI → inspect in Staging tab → publish → verify in Active tab) can proceed
- pushed_by field is visible; operators can trace CLI-pushed jobs back to their author

---
*Phase: 19-dashboard-staging-view-and-governance-doc*
*Completed: 2026-03-15*
