---
phase: 90-job-script-versioning
plan: "02"
subsystem: ui
tags: [react, typescript, diff-viewer, versioning, job-definitions]

requires:
  - phase: 90-01
    provides: JobDefinitionVersion table, version API endpoints, definition_version_id on Job responses

provides:
  - ScriptViewerModal component with lazy-loaded diff viewer
  - Interleaved timeline in DefinitionHistoryPanel (executions + version change events)
  - Version badges on execution rows linking to ScriptViewerModal
  - "View script (vN)" button in Jobs.tsx job detail sheet

affects: [90-job-script-versioning, Jobs.tsx, JobDefinitions.tsx]

tech-stack:
  added: [react-diff-viewer-continued ^4.2.0]
  patterns:
    - Lazy-loaded diff library with React.Suspense fallback
    - Interleaved timeline via useMemo merge + sort by _sortTs
    - ScriptViewerModal as shared component imported by both Jobs and JobDefinitions

key-files:
  created:
    - puppeteer/dashboard/src/components/ScriptViewerModal.tsx
  modified:
    - puppeteer/dashboard/src/views/JobDefinitions.tsx
    - puppeteer/dashboard/src/views/Jobs.tsx
    - puppeteer/dashboard/package.json

key-decisions:
  - "ScriptViewerModal fetches version content via useQuery when versionNumber provided; uses scriptContent prop directly for pre-phase-90 jobs"
  - "DefinitionHistoryPanel keeps existing grouped execution logic; adds separate versions query and merges into timeline via useMemo"
  - "View script button in Jobs.tsx only visible when scheduled_job_id or payload.script_content present (covers both versioned and unversioned jobs)"
  - "definition_version_number, definition_version_id, scheduled_job_id added to Job interface in Jobs.tsx"

patterns-established:
  - "Interleaved timeline pattern: merge two query results by _rowType marker, sort by _sortTs, render conditionally per row type"
  - "Version badge pattern: text-[10px] blue-tinted clickable badge that opens ScriptViewerModal"

requirements-completed: [VER-01, VER-02, VER-03]

duration: 18min
completed: 2026-03-30
---

# Phase 90 Plan 02: Frontend — Script Viewer, Interleaved Timeline, and Job Detail Integration Summary

**ScriptViewerModal with diff view, interleaved execution+version timeline in DefinitionHistoryPanel, and "View script (vN)" action in Jobs.tsx job detail sheet**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-30T00:00:00Z
- **Completed:** 2026-03-30T00:18:00Z
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments
- New `ScriptViewerModal` component: fetches version script via react-query, copy button, lazy-loaded diff view with react-diff-viewer-continued dark theme
- `DefinitionHistoryPanel` refactored to fetch versions in parallel with executions and render an interleaved timeline — version change rows show GitCommit icon, change_summary, and DRAFT badge
- Execution rows in history panel now show clickable `v{N}` badges (blue) that open ScriptViewerModal
- Jobs.tsx job detail sheet has "View script (vN)" button in the Payload section — versioned jobs show version number, unversioned show plain "View script"

## Task Commits

Each task was committed atomically:

1. **Task 90-02-01: Install react-diff-viewer-continued** - `bdd36ba` (chore)
2. **Task 90-02-02: Create ScriptViewerModal component** - `9e519ec` (feat)
3. **Task 90-02-03: Update DefinitionHistoryPanel** - `b4a9352` (feat)
4. **Task 90-02-04: Add View Script action to Jobs.tsx** - `f99f107` (feat)

## Files Created/Modified
- `puppeteer/dashboard/src/components/ScriptViewerModal.tsx` - New reusable component; fetches version content, copy button, diff toggle with lazy ReactDiffViewer
- `puppeteer/dashboard/src/views/JobDefinitions.tsx` - DefinitionHistoryPanel now fetches versions, builds interleaved timeline, renders version change rows and version badges
- `puppeteer/dashboard/src/views/Jobs.tsx` - Job interface extended with versioning fields, ScriptViewerModal integrated, onViewScript prop added to JobDetailPanel
- `puppeteer/dashboard/package.json` - Added react-diff-viewer-continued ^4.2.0

## Decisions Made
- Used `React.lazy()` + `React.Suspense` for ReactDiffViewer to avoid loading the diff library until "Compare with previous" is clicked
- DefinitionHistoryPanel keeps the existing grouped execution logic (deduplication by job_run_id) unchanged; versions query is purely additive
- View script button in Jobs.tsx conditioned on `job.payload?.script_content || job.scheduled_job_id` to correctly handle both versioned and pre-phase-90 jobs

## Deviations from Plan

None — plan executed exactly as written, with one minor addition: the view script button condition was made explicit (`scheduled_job_id || payload.script_content`) to avoid showing the button on non-script jobs (Rule 2 - Missing Critical — handled automatically).

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** No scope creep. All implementations follow the plan spec exactly.

## Issues Encountered
None

## Next Phase Readiness
- Phase 90 is complete (all 2 plans done)
- Phase 91 (Output Validation) can begin
- Requires node-side changes to report structured results; coordinate with the Phase 87 output validation contract design

---
*Phase: 90-job-script-versioning*
*Completed: 2026-03-30*
