---
phase: 52-queue-visibility-node-drawer-and-draining
plan: "04"
subsystem: ui
tags: [react, react-query, websocket, queue-monitoring, lucide-react]

# Dependency graph
requires:
  - phase: 52-queue-visibility-node-drawer-and-draining
    provides: DRAINING node lifecycle (PATCH /nodes/{id}/status), dispatch diagnosis endpoint

provides:
  - Queue.tsx: read-only live monitoring view with WebSocket-driven updates
  - /queue route registered in AppRoutes.tsx
  - Queue nav item in MainLayout.tsx sidebar (Monitoring section, between Jobs and History)

affects: [phase-53-scheduling-health-data-mgmt]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Two-query React Query pattern for active + terminal job sections
    - WebSocket invalidation with queryKey prefix targeting both sub-keys
    - DRAINING badge computed from cross-referenced node status query

key-files:
  created:
    - puppeteer/dashboard/src/views/Queue.tsx
  modified:
    - puppeteer/dashboard/src/AppRoutes.tsx
    - puppeteer/dashboard/src/layouts/MainLayout.tsx
    - puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx

key-decisions:
  - "Queue.tsx uses two parallel React Query fetches (['queue','active'] and ['queue','terminal',recencyWindow]) — invalidate({ queryKey: ['queue'] }) refreshes both at once via prefix matching"
  - "DRAINING badge is best-effort: computed by cross-referencing PENDING job target_tags against drainingNodeIds Set from a separate /api/nodes fetch"
  - "No setInterval or refetchInterval — WebSocket events (job:created, job:updated, node:updated, node:heartbeat) are the sole refresh mechanism"

patterns-established:
  - "Read-only monitoring view: no action buttons, subtle Manage jobs link pointing to /jobs"
  - "Recency window state as literal union type (1 | 6 | 24) — Select value converts via Number()"

requirements-completed: [VIS-02]

# Metrics
duration: 8min
completed: 2026-03-23
---

# Phase 52 Plan 04: Queue View Summary

**Read-only Queue.tsx live monitoring view with WebSocket-driven two-section table (Active + Recent), adjustable terminal recency window (1h/6h/24h), and DRAINING node badges on affected PENDING jobs**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-23T16:34:06Z
- **Completed:** 2026-03-23T16:42:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Queue.tsx built with two parallel React Query fetches (active jobs: PENDING/ASSIGNED/RUNNING; terminal jobs filtered by recency window)
- WebSocket integration invalidates `['queue']` prefix on job:created, job:updated, node:updated, node:heartbeat events — no polling
- DRAINING node badge shown on PENDING jobs whose target_tags include a draining node_id
- /queue route added to AppRoutes.tsx after /jobs; Queue nav item added to MainLayout.tsx Monitoring section between Jobs and History

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Queue.tsx view with WebSocket live updates** - `6ea806d` (feat)
2. **Task 2: Wire /queue route and sidebar nav entry** - `dfc9dc0` (feat)

**Plan metadata:** (docs commit — see final commit)

## Files Created/Modified
- `puppeteer/dashboard/src/views/Queue.tsx` - Read-only job queue monitoring view (406 lines)
- `puppeteer/dashboard/src/AppRoutes.tsx` - Added lazy Queue import and /queue route
- `puppeteer/dashboard/src/layouts/MainLayout.tsx` - Added ListOrdered import and Queue nav item
- `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx` - Fixed missing getUser mock export

## Decisions Made
- Two-query React Query pattern: `['queue','active']` + `['queue','terminal',recencyWindow]` — invalidating `['queue']` prefix refreshes both with a single call
- DRAINING badge is cross-referenced from a third `/api/nodes` fetch — displayed as "best-effort" since the diagnosis endpoint provides authoritative info per the plan spec
- Recency window uses literal union type `1 | 6 | 24` with `Number()` coercion from Select string value

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed Nodes.test.tsx auth mock missing getUser export**
- **Found during:** Task 2 (building + running tests)
- **Issue:** `Nodes.tsx` calls `getUser()` from `../auth` (added in Phase 52-02/03), but the test's `vi.mock('../../auth')` only exported `authenticatedFetch`. All 5 ENVTAG-03 tests failed with "No getUser export is defined on the auth mock".
- **Fix:** Added `getUser: () => ({ username: 'testuser', role: 'admin' })` to the mock factory in `Nodes.test.tsx`
- **Files modified:** `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx`
- **Verification:** All 8 test files pass (39 passed, 3 todo)
- **Committed in:** `dfc9dc0` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing test mock)
**Impact on plan:** Pre-existing test gap from Phase 52-02/03 Nodes.tsx changes. Fix restores all tests to passing.

## Issues Encountered
None — build passed on first attempt for both tasks.

## Self-Check: PASSED

## Next Phase Readiness
- Queue.tsx is complete and functional; ready for Phase 53 scheduling health integration
- All frontend tests passing (39/39 + 3 todo)
- No blockers

---
*Phase: 52-queue-visibility-node-drawer-and-draining*
*Completed: 2026-03-23*
