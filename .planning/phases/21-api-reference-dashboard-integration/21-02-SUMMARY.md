---
phase: 21-api-reference-dashboard-integration
plan: "02"
subsystem: ui
tags: [react, react-router, lucide-react, sidebar, navigation]

# Dependency graph
requires:
  - phase: 21-api-reference-dashboard-integration
    provides: Plan 21-01 MkDocs site at /docs/ via nginx container
provides:
  - External sidebar link opening /docs/ in new tab (plain <a> tag, href="/docs/", target=_blank)
  - Catch-all React Router redirect (path="*" -> Navigate to="/")
  - Docs.tsx and UserGuide.md removed from codebase
affects: [any future phase touching AppRoutes.tsx or MainLayout.tsx sidebar nav]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "External links in React sidebar use plain <a> tags (not NavLink) with target=_blank and CSS matching inactive NavItem"
    - "Catch-all route inside PrivateRoute wrapper so unknown paths still trigger auth redirect"

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/AppRoutes.tsx
    - puppeteer/dashboard/src/layouts/MainLayout.tsx
  deleted:
    - puppeteer/dashboard/src/views/Docs.tsx
    - puppeteer/dashboard/src/assets/UserGuide.md

key-decisions:
  - "Catch-all route placed inside PrivateRoute parent so unauthenticated users hitting /docs still see Login, not bare redirect to /"
  - "External Docs link uses plain <a> (not NavLink) because NavLink cannot open external URLs and would never have an active state"
  - "Documentation section header added above Docs link to distinguish it from system nav items"

patterns-established:
  - "External sidebar nav items: plain <a> tag with href, target=_blank, rel=noopener noreferrer, CSS class matching inactive NavItem"

requirements-completed: [DASH-01, DASH-02]

# Metrics
duration: 2min
completed: 2026-03-16
---

# Phase 21 Plan 02: Remove In-App Docs View, Add External Sidebar Link Summary

**Docs.tsx and UserGuide.md deleted; sidebar gains external /docs/ link opening in new tab; unknown React routes catch-all redirect to /**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-16T22:28:29Z
- **Completed:** 2026-03-16T22:30:08Z
- **Tasks:** 2 of 2 (+ checkpoint awaiting human verify)
- **Files modified:** 2 modified, 2 deleted

## Accomplishments
- Removed lazy Docs import and `/docs` route from AppRoutes.tsx; added catch-all `<Route path="*">` with Navigate redirect to `/`
- Added BookOpen icon import and Documentation section in MainLayout.tsx sidebar with plain `<a href="/docs/">` opening in new tab
- Deleted Docs.tsx (in-app markdown renderer) and UserGuide.md (only consumed by Docs.tsx)
- Build passes clean with zero TypeScript errors both before and after deletions

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove Docs route from AppRoutes and add catch-all redirect** - `67660eb` (feat)
2. **Task 2: Add external Docs sidebar link, delete Docs.tsx and UserGuide.md** - `0b6a284` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified
- `puppeteer/dashboard/src/AppRoutes.tsx` - Removed Docs lazy import and route; added Navigate import and catch-all route
- `puppeteer/dashboard/src/layouts/MainLayout.tsx` - Added BookOpen import; added Documentation section + external Docs link after Audit Log
- `puppeteer/dashboard/src/views/Docs.tsx` - DELETED
- `puppeteer/dashboard/src/assets/UserGuide.md` - DELETED

## Decisions Made
- Catch-all route placed inside the PrivateRoute-wrapped `<Route path="/">` so unauthenticated users hitting unknown paths still see the Login redirect rather than a bare redirect to `/`
- External Docs link uses a plain `<a>` tag with matching inactive NavItem CSS because NavLink cannot open external URLs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Dashboard cleanup complete; sidebar shows Docs link pointing to the MkDocs site at /docs/
- Checkpoint awaiting human verification before state is finalized
- Phase 21 Plans 03+ (API reference content, MkDocs nav structure) can proceed after checkpoint approval

---
*Phase: 21-api-reference-dashboard-integration*
*Completed: 2026-03-16*
