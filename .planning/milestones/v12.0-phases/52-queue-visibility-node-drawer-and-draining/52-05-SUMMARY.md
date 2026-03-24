---
phase: 52-queue-visibility-node-drawer-and-draining
plan: "05"
subsystem: ui
tags: [react, typescript, shadcn, sheet, websocket, draining, diagnosis]

# Dependency graph
requires:
  - phase: 52-02
    provides: PATCH /nodes/{id}/drain, PATCH /nodes/{id}/undrain, GET /jobs/{guid}/dispatch-diagnosis backend endpoints
  - phase: 52-03
    provides: GET /nodes/{node_id}/detail endpoint (running job, eligible pending, 24h history, capabilities)
  - phase: 52-04
    provides: Queue.tsx live view and /queue route (verified end-to-end in same human checkpoint)
provides:
  - Node detail Sheet drawer in Nodes.tsx (row-click opens right-side panel with running job, eligible pending jobs, 24h history, capabilities)
  - Drain/Un-drain action buttons in node drawer, gated to admin role
  - DRAINING amber status badge and status union type extension in Nodes.tsx
  - Dispatch diagnosis amber callout in JobDetailPanel (Jobs.tsx) for PENDING jobs, with WebSocket refresh
affects:
  - phase 53-scheduling-health-data-mgmt

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Sheet drawer pattern for node detail: row click -> setSelectedNode + setNodeDrawerOpen -> fetch /detail
    - Admin-gated UI: getUser() from auth.ts, user?.role === 'admin' guard on drain/undrain buttons
    - Diagnosis callout: useEffect on [open, job?.guid, job?.status] + useWebSocket refresh inside JobDetailPanel
    - Deviation fix: JWT missing role field fixed in main.py create_access_token before human verify

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/Nodes.tsx
    - puppeteer/dashboard/src/views/Jobs.tsx
    - puppeteer/agent_service/main.py

key-decisions:
  - "JWT payload was missing role field — fixed inline (deviation Rule 1) before human verification; all 12 UI tests confirmed passing after fix"
  - "useWebSocket hook used directly inside JobDetailPanel component (valid hooks usage) to refresh diagnosis on node:updated and job:updated events without lifting state to parent"
  - "Drain/undrain buttons only shown for ONLINE/BUSY/DRAINING nodes — not OFFLINE/REVOKED/TAMPERED; avoids spurious API calls on unreachable nodes"

patterns-established:
  - "Row-click drawer pattern: onClick on <tr> with e.stopPropagation() on action buttons prevents conflict"
  - "Admin role check: const currentUser = getUser(); then currentUser?.role === 'admin' inline in JSX"

requirements-completed:
  - VIS-01
  - VIS-03
  - VIS-04

# Metrics
duration: 50min
completed: 2026-03-23
---

# Phase 52 Plan 05: Queue Visibility Node Drawer and Draining — Frontend Summary

**Node detail Sheet drawer, admin drain/undrain controls, DRAINING status badge, and PENDING dispatch diagnosis callout — all four Phase 52 frontend features verified end-to-end by human**

## Performance

- **Duration:** ~50 min (including human verify checkpoint and JWT fix)
- **Started:** 2026-03-23T16:36:00Z
- **Completed:** 2026-03-23T17:20:14Z (post-fix commit)
- **Tasks:** 2 implementation tasks + 1 human verify checkpoint
- **Files modified:** 3

## Accomplishments

- Nodes.tsx: DRAINING added to Node status union, amber badge rendering, row-click handler opening right-side Sheet drawer with running job, eligible pending jobs, 24h history, and capabilities
- Nodes.tsx: Admin-gated Drain/Un-drain action buttons inside the drawer, calling PATCH /nodes/{id}/drain and /undrain with toast feedback and query invalidation
- Jobs.tsx: Amber dispatch diagnosis callout at top of JobDetailPanel when job.status === 'PENDING', fetching GET /jobs/{guid}/dispatch-diagnosis and refreshing on WebSocket node:updated / job:updated events
- All four Phase 52 features (Queue view from Plan 04 + three features from this plan) verified and approved via human checkpoint

## Task Commits

Each task was committed atomically:

1. **Task 1: Add DRAINING status display + node detail drawer to Nodes.tsx** - `987016a` (feat)
2. **Task 2: Add PENDING diagnosis callout to JobDetailPanel in Jobs.tsx** - `803586c` (feat)

**Deviation fix (outside plan):** `048ae0c` — fix(auth): include role in JWT payload (applied before human verify)

## Files Created/Modified

- `puppeteer/dashboard/src/views/Nodes.tsx` — Added DRAINING to Node status union, NodeDetail interface, row-click state, handleNodeClick/handleDrain/handleUndrain functions, Sheet drawer with running job / eligible pending / 24h history / capabilities sections, admin drain/undrain buttons
- `puppeteer/dashboard/src/views/Jobs.tsx` — Added DispatchDiagnosis interface, diagnosis state inside JobDetailPanel, useEffect fetch on PENDING open, useWebSocket refresh hook, amber callout JSX at top of detail panel
- `puppeteer/agent_service/main.py` — JWT create_access_token now includes role field in payload (deviation fix)

## Decisions Made

- JWT was missing the `role` field — the frontend getUser() parses it from the token, so admin-gated drain/undrain buttons would never render. Fixed inline before human verify (deviation Rule 1 — broken behavior).
- useWebSocket hook called directly inside JobDetailPanel (not just at parent Jobs level) so diagnosis re-fetches on relevant WS events without prop-drilling or lifting state.
- Drain/undrain buttons conditionally rendered: Drain shown for ONLINE or BUSY, Un-drain shown for DRAINING only. Other statuses (OFFLINE, REVOKED, TAMPERED) show neither.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JWT payload missing role field broke admin-gated UI**
- **Found during:** Task 1 verification / human verify checkpoint
- **Issue:** `create_access_token` in `main.py` did not include `role` in the JWT claims. `getUser()` in `auth.ts` parses role from the token, so `currentUser?.role === 'admin'` always evaluated to false. Admin drain/undrain buttons never rendered.
- **Fix:** Added `"role": user.role` to the JWT payload dict in `create_access_token`.
- **Files modified:** `puppeteer/agent_service/main.py`
- **Verification:** All 12 UI tests re-run and passed after fix.
- **Committed in:** `048ae0c`

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Required for admin-gated drain/undrain feature to work at all. No scope creep.

## Issues Encountered

None beyond the JWT role field bug documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All Phase 52 requirements (VIS-01, VIS-03, VIS-04) complete and human-verified
- Phase 53 (scheduling health + data management) can now proceed — it depends on both Phase 48 and Phase 52
- Queue view, node drawer, drain lifecycle, and dispatch diagnosis are all production-ready

---
*Phase: 52-queue-visibility-node-drawer-and-draining*
*Completed: 2026-03-23*
