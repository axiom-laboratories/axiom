---
phase: 37-licence-validation-docs-docker-hub
plan: "02"
subsystem: ui
tags: [react, typescript, tanstack-query, licence, edition-badge]

# Dependency graph
requires:
  - phase: 37-01
    provides: GET /api/licence endpoint returning LicenceInfo JSON
provides:
  - useLicence hook with LicenceInfo interface and 5-min cache
  - CE/EE edition badge in sidebar footer derived from /api/licence
  - LicenceSection component in Admin panel (admin-only) showing full licence details
affects:
  - MainLayout.tsx sidebar footer appearance
  - Admin.tsx panel content for admin users

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useLicence mirrors useFeatures exactly: staleTime 5min, retry false, CE fallback"
    - "Edition badge derived from hook — no hardcoding of edition strings in JSX"

key-files:
  created:
    - .worktrees/axiom-split/puppeteer/dashboard/src/hooks/useLicence.ts
  modified:
    - .worktrees/axiom-split/puppeteer/dashboard/src/layouts/MainLayout.tsx
    - .worktrees/axiom-split/puppeteer/dashboard/src/views/Admin.tsx

key-decisions:
  - "useLicence lives alongside useFeatures — same pattern, same cache duration, same error fallback"
  - "licence const added at MainLayout level (alongside features const) so it is available in SidebarContent closure"
  - "LicenceSection placed before Tabs in Admin return — visible to admin users at page top"

patterns-established:
  - "useLicence pattern: mirror useFeatures — queryKey, staleTime, retry:false, CE fallback object"

requirements-completed:
  - DIST-03

# Metrics
duration: 12min
completed: 2026-03-20
---

# Phase 37 Plan 02: Dashboard Edition Badge + Licence Panel Summary

**CE/EE edition badge in sidebar footer and full licence detail panel in Admin, both derived from useLicence() hook calling GET /api/licence**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-20T16:05:00Z
- **Completed:** 2026-03-20T16:17:50Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Created `useLicence.ts` hook: `LicenceInfo` interface, 5-min stale cache, no retry, `{edition: 'community'}` fallback
- Added CE/EE badge to sidebar footer in `MainLayout.tsx` — zinc neutral for CE, indigo for EE
- Added `LicenceSection` component to `Admin.tsx`: shows edition, customer ID, expiry date, enabled features; rendered admin-only

## Task Commits

Each task was committed atomically (worktree: `feature/axiom-oss-ee-split`):

1. **Task 1: Create useLicence hook** - `e4a2344` (feat)
2. **Task 2: Edition badge + LicenceSection** - `6879905` (feat)

**Plan metadata:** committed below (docs: complete plan)

## Files Created/Modified
- `.worktrees/axiom-split/puppeteer/dashboard/src/hooks/useLicence.ts` - useLicence hook + LicenceInfo interface
- `.worktrees/axiom-split/puppeteer/dashboard/src/layouts/MainLayout.tsx` - CE/EE badge in sidebar footer
- `.worktrees/axiom-split/puppeteer/dashboard/src/views/Admin.tsx` - LicenceSection component, admin-only

## Decisions Made
- `licence` const added at `MainLayout` component level alongside `features` — the plan referenced "alongside useFeatures()" which sits at `MainLayout` scope, not inside `SidebarContent`
- `getUser` imported from `../auth` in Admin.tsx (not previously imported) — added alongside `authenticatedFetch` import to enable admin-only gating
- LicenceSection placed as first content block before the Tabs component in Admin's JSX return

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The `.worktrees` directory is in `.gitignore` of the main repo; all commits were made using `git -C .worktrees/axiom-split` to target the worktree's branch `feature/axiom-oss-ee-split` directly. This is the expected pattern for worktree commits.

## Next Phase Readiness
- Dashboard edition badge is live; will show "EE" once `/api/licence` returns enterprise data from plan 37-01
- Admin Licence panel ready; pending the backend endpoint from plan 37-01
- Plan 37-03 (Docker Hub / docs) can proceed independently

---
*Phase: 37-licence-validation-docs-docker-hub*
*Completed: 2026-03-20*

## Self-Check: PASSED

- useLicence.ts: FOUND
- MainLayout.tsx: FOUND
- Admin.tsx: FOUND
- SUMMARY.md: FOUND
- Commit e4a2344: FOUND
- Commit 6879905: FOUND
