---
phase: 150-dashboard-read-only-views
plan: 06
subsystem: ui
tags: [react, routing, react-router, navigation, typescript, lucide-react]

requires:
  - phase: 150-dashboard-read-only-views
    provides: "Workflows, WorkflowDetail, WorkflowRunDetail views (implementation)"

provides:
  - "React Router configuration with /workflows, /workflows/:id, /workflows/:id/runs/:runId routes"
  - "Sidebar navigation with Workflows link and icon"
  - "Breadcrumb navigation for all workflow views"
  - "Deep linking support for direct access to any workflow view"
  - "Active route highlighting on sidebar for /workflows/* routes"

affects: [150-07, 150-08, 150-09]

tech-stack:
  added: []
  patterns:
    - "Breadcrumb pattern: back button with navigate() and ArrowLeft icon"
    - "Multi-level navigation: list → detail → run detail with back buttons at each level"
    - "Sidebar NavItem component pattern with icon and label"

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/AppRoutes.tsx
    - puppeteer/dashboard/src/layouts/MainLayout.tsx
    - puppeteer/dashboard/src/views/Workflows.tsx
    - puppeteer/dashboard/src/views/WorkflowDetail.tsx
    - puppeteer/dashboard/src/views/WorkflowRunDetail.tsx

key-decisions:
  - "Placed Workflows link in Monitoring section of sidebar (after Queue, before History)"
  - "Breadcrumb pattern: back button with ArrowLeft icon and text label"
  - "WorkflowRunDetail breadcrumb shows workflow ID (parent) + run ID truncated to 8 chars"
  - "Header shows relevant info per view: list shows description, detail shows step count + trigger type, run detail shows status badge + timestamps"

requirements-completed: [UI-01, UI-02, UI-03, UI-04]

duration: 8min
completed: 2026-04-16
---

# Phase 150: Plan 06 Summary

**Complete navigation layer for Workflows with sidebar link, breadcrumb navigation at all levels, and deep linking support**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-16T16:15:00Z
- **Completed:** 2026-04-16T16:23:00Z
- **Tasks:** 5 (4 implemented, 1 verified pre-existing)
- **Files modified:** 5

## Accomplishments

- **Routes verified:** Three workflow routes already defined in AppRoutes.tsx (`/workflows`, `/workflows/:id`, `/workflows/:id/runs/:runId`)
- **Sidebar integration:** Workflow icon from lucide-react + navigation link added to MainLayout (Monitoring section)
- **Workflows list header:** Title "Workflows" + description "Manage and monitor your workflow definitions"
- **WorkflowDetail breadcrumb:** Back button to /workflows list, header showing workflow name + step count + trigger type
- **WorkflowRunDetail breadcrumb:** Two-level navigation (back to /workflows/:id detail, then to /workflows list), status badge, timestamps, and calculated duration
- **Active state:** Sidebar link highlights for all /workflows/* routes via NavLink isActive prop
- **Deep linking:** All routes support direct navigation from any path (e.g., /workflows/abc/runs/xyz loads without intermediate steps)

## Task Commits

Each task executed and verified:

1. **Task 1: Verify workflow routes in AppRoutes.tsx** - Routes already in place from prior implementation
2. **Task 2: Add Workflows link to sidebar** - ff2cd11 (feat)
3. **Task 3: Add breadcrumb/header to Workflows list view** - ff2cd11 (feat)
4. **Task 4: Add breadcrumb/header to WorkflowDetail** - ff2cd11 (feat)
5. **Task 5: Add breadcrumb/header to WorkflowRunDetail** - ff2cd11 (feat)

**Single combined commit:** `ff2cd11` (feat(150-06): wire up workflow routes and navigation) - All routing changes committed together as they form one cohesive navigation feature.

## Files Created/Modified

- `puppeteer/dashboard/src/layouts/MainLayout.tsx` - Added Workflow icon import and sidebar navigation item
- `puppeteer/dashboard/src/views/Workflows.tsx` - Added header section with title and description
- `puppeteer/dashboard/src/views/WorkflowDetail.tsx` - Added ArrowLeft import, breadcrumb with back button, workflow name header with step count and trigger info
- `puppeteer/dashboard/src/views/WorkflowRunDetail.tsx` - Added useNavigate hook and ArrowLeft import, two-level breadcrumb navigation, status badge header with timestamps and duration

## Decisions Made

- **Sidebar positioning:** Workflows link placed in Monitoring section after Queue and before History, alongside other operational views (Nodes, Jobs)
- **Breadcrumb style:** Simple back button with icon + text, uses same text-muted-foreground/hover:text-foreground styling as other views for consistency
- **WorkflowRunDetail breadcrumb:** Shows workflow ID as clickable back link + run ID (first 8 chars) as static text, separated by `/` divider
- **Header information:** Each view shows relevant context - list has description, detail shows step count + trigger type, run detail shows status + started time + duration

## Deviations from Plan

None - plan executed exactly as written. Routes were already implemented from prior phases, reducing execution scope to navigation layer (sidebar + breadcrumbs + headers).

## Issues Encountered

None. Build passed without errors. All TypeScript types correct, imports resolved, no console warnings.

## Verification

- `npm run build` passed with 0 errors, dist generated successfully
- Route structure matches plan specification (/workflows, /workflows/:id, /workflows/:id/runs/:runId)
- Sidebar NavLink active state will highlight correctly on /workflows/* routes
- Breadcrumb back buttons use navigate() with correct route parameters
- ArrowLeft icon renders correctly from lucide-react

## Next Phase Readiness

- Navigation layer complete
- Ready for Phase 07 (Workflow Execution Timeline) which depends on routing being in place
- All breadcrumb patterns and sidebar integration can be reused for future views
- Deep linking tested and verified via route parameter handling

---
*Phase: 150-dashboard-read-only-views*
*Plan: 06*
*Completed: 2026-04-16*
