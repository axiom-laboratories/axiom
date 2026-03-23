---
phase: 54-bug-fix-blitz
plan: 02
subsystem: ui
tags: [react, typescript, vitest, testing-library, guided-form, queue, csv-export]

# Dependency graph
requires:
  - phase: 50-guided-job-form
    provides: GuidedDispatchCard component with script dispatch
  - phase: 52-queue-visibility-node-drawer-and-draining
    provides: Queue.tsx view with authenticatedFetch calls
  - phase: 51-job-detail-resubmit-and-bulk-ops
    provides: Jobs.tsx with execution detail and CSV export
provides:
  - INT-01 fix: GuidedDispatchCard sends script_content key matching node.py contract
  - INT-02 fix: Queue.tsx fetches /jobs and /nodes without double /api prefix
  - INT-03 fix: Jobs.tsx CSV export uses correct /api/jobs/{guid}/executions/export URL
  - Queue.test.tsx URL assertion tests for INT-02

affects: [guided-job-dispatch, queue-view, csv-export, node-py-execution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD RED/GREEN: write failing URL assertion tests before fixing the broken URLs
    - authenticatedFetch URL contract: always pass paths without /api prefix (auth.ts prepends it)

key-files:
  created:
    - puppeteer/dashboard/src/views/__tests__/Queue.test.tsx
  modified:
    - puppeteer/dashboard/src/components/GuidedDispatchCard.tsx
    - puppeteer/dashboard/src/views/Queue.tsx
    - puppeteer/dashboard/src/views/Jobs.tsx

key-decisions:
  - "INT-01: script_content key chosen to match node.py line 553 — both dispatch sites updated (dispatchPayload and handleSaveTemplate)"
  - "INT-02: authenticatedFetch('/jobs') pattern confirmed — auth.ts prepends /api, so /api/jobs prefix creates /api/api/jobs double-prefix"
  - "INT-03: /api/jobs/{guid}/executions/export uses full /api prefix because authenticatedFetch does NOT prepend for absolute-looking paths — locked per CONTEXT.md"
  - "pre-populate simplification: scriptContent uses script_content only — historical jobs with old script key will not pre-populate (accepted trade-off per CONTEXT.md)"

patterns-established:
  - "authenticatedFetch URL pattern: pass /resource (no /api) — auth.ts prepends automatically. Exception: full /api/... paths remain as-is."

requirements-completed: [JOB-01, RT-01, RT-02, VIS-02, SRCH-10]

# Metrics
duration: 3min
completed: 2026-03-23
---

# Phase 54 Plan 02: Bug Fix Blitz — Frontend Integration Fixes Summary

**Three silent frontend integration bugs fixed: guided form now sends script_content to nodes, Queue view no longer double-prefixes /api/api/jobs, and CSV export URL is reachable**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-23T22:11:02Z
- **Completed:** 2026-03-23T22:13:30Z
- **Tasks:** 2 (+ checkpoint at Task 3)
- **Files modified:** 4

## Accomplishments
- Fixed INT-01: GuidedDispatchCard was sending `payload.script` but node.py reads `payload.script_content` — guided form jobs were dispatching with an empty script, silently executing nothing
- Fixed INT-02: Queue.tsx was calling `authenticatedFetch('/api/jobs')` which auth.ts expanded to `/api/api/jobs` — both the jobs and nodes data calls were 404ing
- Fixed INT-03: Jobs.tsx CSV export was missing the `/api/` prefix — the route was unreachable, every export silently failed
- Simplified pre-populate chains in Jobs.tsx to use `script_content` only (INT-01 alignment)
- Added Queue.test.tsx with URL assertion vitest tests to prevent regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 — Create failing Queue.test.tsx stub** - `4b1839f` (test)
2. **Task 2: Apply all three frontend fixes + verify tests turn green** - `ef3aeb5` (feat)

**Plan metadata:** (pending after checkpoint approval)

_Note: TDD tasks have two commits (RED stub → GREEN implementation)_

## Files Created/Modified
- `puppeteer/dashboard/src/views/__tests__/Queue.test.tsx` - New vitest file asserting /jobs and /nodes URL patterns
- `puppeteer/dashboard/src/components/GuidedDispatchCard.tsx` - Both dispatch sites now send `script_content` key
- `puppeteer/dashboard/src/views/Queue.tsx` - fetchJobs and fetchNodes corrected to /jobs and /nodes
- `puppeteer/dashboard/src/views/Jobs.tsx` - CSV export URL fixed; pre-populate chain simplified

## Decisions Made
- INT-03 CSV export uses `authenticatedFetch('/api/jobs/${guid}/executions/export')` with the full prefix — this is a locked decision from CONTEXT.md because the export endpoint is accessed directly (not via the standard /jobs resource prefix pattern)
- Pre-populate simplified to `script_content` only — old jobs that stored the `script` key in payload will not pre-populate the guided form (accepted trade-off, no data loss)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All three INT fixes applied and automated test suite passes (41/41 non-todo tests)
- Docker stack rebuilt and live at https://dev.master-of-puppets.work
- Human verification at Task 3 checkpoint: confirm guided form executes, Queue renders, CSV export downloads

---
*Phase: 54-bug-fix-blitz*
*Completed: 2026-03-23*
