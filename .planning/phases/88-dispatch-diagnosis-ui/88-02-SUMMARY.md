---
phase: 88-dispatch-diagnosis-ui
plan: 02
subsystem: ui
tags: [react, jobs, diagnosis, polling, typescript]

requires:
  - phase: 88-dispatch-diagnosis-ui plan 01
    provides: "POST /jobs/dispatch-diagnosis/bulk endpoint aggregating diagnoses for multiple job GUIDs"

provides:
  - "diagnosisCache state in Jobs component populated from bulk diagnosis endpoint"
  - "10s auto-poll for PENDING/ASSIGNED job diagnoses while Jobs view is mounted"
  - "Inline diagnosis sub-text under status badge in job list table rows"
  - "Amber left-border accent on PENDING and stuck_assigned rows"
  - "Manual refresh button (RefreshCw) in Queue Monitor header"
  - "Drawer diagnosis auto-refresh at 10s interval for PENDING and ASSIGNED jobs"

affects:
  - Users viewing the Jobs page with pending/stuck jobs

tech-stack:
  added: []
  patterns:
    - "diagnosisCache: Record<string, DispatchDiagnosis> keyed by job GUID, merged with spread on each poll"
    - "Poll useEffect uses stringified GUID join as dependency to avoid array identity instability"
    - "Benign reason codes (pending_dispatch, not_pending) filtered from inline display — only actionable diagnoses shown"

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/Jobs.tsx

key-decisions:
  - "Poll dependency is jobs.filter(...).map(j=>j.guid).join(',') string — prevents infinite re-render from array identity"
  - "pending_dispatch and not_pending reasons suppressed from inline display — keeps UI clean for healthy queues"
  - "Drawer auto-refresh reuses same 10s interval pattern, with setDiagnosisLoading only on first fetch (not interval ticks)"

requirements-completed: [DIAG-01, DIAG-03]

duration: 5min
completed: 2026-03-29
---

# Phase 88 Plan 02: Inline Diagnosis Display, Bulk Poll, and Manual Refresh Summary

**Wired the bulk dispatch diagnosis endpoint into the Jobs view with inline sub-text under status badges, 10s background polling, and a manual refresh button — completing the PENDING/stuck-ASSIGNED diagnostic UX.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-29T21:05:00Z
- **Completed:** 2026-03-29T21:10:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- `diagnosisCache` state populated via `fetchDiagnoses` (POSTs to `/jobs/dispatch-diagnosis/bulk`), auto-polls every 10s while PENDING/ASSIGNED jobs exist
- Status cell in job table updated: amber left-border for PENDING/stuck rows, diagnosis sub-line beneath badge (filtered for actionable reasons only)
- `RefreshCw` button in Queue Monitor header triggers immediate `fetchDiagnoses` call
- `JobDetailPanel` drawer upgraded: handles ASSIGNED jobs, 10s auto-refresh interval with cleanup on close

## Task Commits

Each task was committed atomically:

1. **Task 1: diagnosisCache state, fetchDiagnoses callback, 10s poll** - `a376663` (feat)
2. **Task 2: Inline diagnosis display and amber border in status cell** - `aebb074` (feat)
3. **Task 3: Manual refresh button and extended drawer auto-refresh** - `ced9511` (feat)

## Files Created/Modified

- `puppeteer/dashboard/src/views/Jobs.tsx` — All three UX changes: diagnosisCache, inline display, manual refresh, drawer upgrade (1584 lines)

## Decisions Made

- Poll useEffect dependency is the stringified GUID join (not the array) to avoid infinite re-render loops from array identity instability — ESLint disable comment included per plan spec
- Benign reason codes (`pending_dispatch`, `not_pending`) are suppressed from the inline sub-text to keep the UI clean for normal healthy queues
- Drawer's initial fetch still sets `diagnosisLoading` while interval ticks do not — avoids loading flicker on auto-refresh

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three DIAG requirements now complete: DIAG-01 (inline in list), DIAG-02 (backend, phase 01), DIAG-03 (updates without page reload)
- Phase 88 is complete; ready to proceed to Phase 89 (CE Alerting) or any other v16.0 implementation phase

---
*Phase: 88-dispatch-diagnosis-ui*
*Completed: 2026-03-29*
