---
phase: 116-fix-smelter-db-migration-and-add-ee-licence-hot-reload
plan: 02
subsystem: ui, frontend, backend
tags: [WebSocket, React, FastAPI, licence, admin]

# Dependency graph
requires:
  - phase: 116-01
    provides: reload_licence endpoint, background timer, expiry guard middleware, licence_service functions
provides:
  - WebSocket broadcast for licence status changes
  - Admin UI for licence management
  - Real-time licence status updates
  - Grace period notification banner
  - E2E tests for admin licence workflow

affects: [future admin enhancements, dashboard maintenance, licence lifecycle]

# Tech tracking
tech-stack:
  added:
    - React hooks for WebSocket integration
    - Radix UI Card/Badge/Button components
    - TypeScript interfaces for licence events
  patterns:
    - WebSocket event broadcasting to all connected clients
    - Admin section with tab-based navigation
    - Grace period dismissible banner (localStorage-based)
    - Real-time state refresh via query invalidation

key-files:
  created:
    - puppeteer/dashboard/src/components/LicenceStatus.tsx
    - puppeteer/dashboard/src/components/LicenceReloadButton.tsx
    - puppeteer/dashboard/src/components/GracePeriodBanner.tsx
  modified:
    - puppeteer/agent_service/main.py (WebSocket broadcast)
    - puppeteer/dashboard/src/hooks/useWebSocket.ts (licence handler)
    - puppeteer/dashboard/src/views/Admin.tsx (licence tab)

key-decisions:
  - "WebSocket broadcasts sent immediately after state swap in reload endpoint"
  - "Grace period banner placed in Admin tab only (Option A), not global"
  - "Query invalidation used to refresh licence data on WebSocket events"
  - "LicenceReloadButton hidden for non-admin users"

requirements-completed: []

# Metrics
duration: 35min
completed: 2026-04-02
---

# Phase 116 Plan 02: Dashboard UI & WebSocket Broadcast for Licence Management Summary

**Real-time admin licence management UI with WebSocket-driven updates, grace period notifications, and reload controls integrated into admin dashboard**

## Performance

- **Duration:** 35 min
- **Started:** 2026-04-02T20:55:00Z
- **Completed:** 2026-04-02T21:30:00Z
- **Tasks:** 7 completed
- **Files created:** 3 components
- **Files modified:** 3

## Accomplishments

- **WebSocket broadcast integration:** Licence status changes now broadcast to all connected dashboard clients immediately after reload or expiry transition
- **Three reusable UI components:** LicenceStatus (metadata display), LicenceReloadButton (admin action), GracePeriodBanner (dismissible alert)
- **Real-time admin tab:** New "Licence" tab in admin page with live updates via WebSocket
- **Grace period notifications:** Amber dismissible banner displays when licence in grace period, localStorage-persisted dismissal
- **E2E Playwright tests:** Full workflow test covering admin access, reload button visibility, status display, and grace period banner
- **Type-safe event handling:** LicenceStatusChangeData interface ensures type safety for WebSocket payloads

## Task Commits

Each task was committed atomically:

1. **Task 1: Add WebSocket Licence Status Broadcast** - `3a64671` (feat)
   - Added broadcast in reload_licence_endpoint after state swap
   - Added broadcast in background expiry checker on transitions
   - Includes metadata: organization, tier, expires_at

2. **Task 2: Extend useWebSocket Hook for Licence Events** - `6f9d70c` (feat)
   - Added LicenceStatusChangeData interface
   - Added optional onLicenceStatusChanged callback
   - Dispatch licence_status_changed events with proper typing

3. **Task 3: Create Licence Status Components** - `53ab0e1` (feat)
   - LicenceStatus.tsx: Card-based licence metadata display
   - LicenceReloadButton.tsx: Admin-only reload with modal
   - GracePeriodBanner.tsx: Dismissible amber grace period alert

4. **Task 4: Add Licence Section to Admin Page** - `1837b68` (feat)
   - Added Licence tab to admin tabs bar
   - Created LicenceTabContent component with WebSocket integration
   - Imported licence components and integrated into admin

5. **Task 5: Add Global GRACE Period Banner** - (Included in Task 4)
   - Implemented Option A (Admin section only) per plan recommendation
   - GracePeriodBanner displays in Licence tab when status == grace

6. **Task 6: E2E Test — Playwright Dashboard Suite** - `15e9832` (test, in mop_validation repo)
   - Test 8: Admin Licence Management
   - Verifies tab access, status display, reload button, grace banner
   - Screenshot capture for manual verification

7. **Task 7: Update Admin Page Routing & Navigation** - (verified complete)
   - /admin route already exists in AppRoutes.tsx
   - Licence tab accessible via Admin page
   - No routing changes required

**Plan metadata:** docs(116-02): complete admin licence UI & WebSocket plan (will be committed as final step)

## Files Created/Modified

**Created:**
- `puppeteer/dashboard/src/components/LicenceStatus.tsx` - Licence metadata display card with status badge, organization, tier, node limit with utilization %, expiry date countdown
- `puppeteer/dashboard/src/components/LicenceReloadButton.tsx` - Admin-only reload button with optional licence key override modal, loading state, error handling
- `puppeteer/dashboard/src/components/GracePeriodBanner.tsx` - Amber dismissible banner for grace period notifications, localStorage-persisted dismissal, countdown in days

**Modified:**
- `puppeteer/agent_service/main.py` - Added WebSocket broadcast calls in reload_licence_endpoint and background licence expiry checker
- `puppeteer/dashboard/src/hooks/useWebSocket.ts` - Extended with licence event handler, LicenceStatusChangeData interface, onLicenceStatusChanged callback
- `puppeteer/dashboard/src/views/Admin.tsx` - Added Licence tab, LicenceTabContent component, WebSocket subscription, licence components import

## Decisions Made

1. **WebSocket broadcast timing:** Broadcast immediately after state swap (atomic operation) rather than queuing for next cycle — ensures all clients see consistent state
2. **Grace period banner placement:** Placed only in Admin → Licence tab (Option A) per plan recommendation; future enhancement to add global MainLayout banner if needed
3. **State refresh strategy:** Using React Query's queryClient.invalidateQueries to refresh licence data on WebSocket broadcast rather than updating local state directly — ensures single source of truth from API
4. **Component visibility:** LicenceReloadButton returns null for non-admin users rather than showing disabled button — cleaner UX per admin-only permission pattern
5. **Event handler pattern:** Optional onLicenceStatusChanged parameter on useWebSocket hook allows components to opt-in to licence events without forcing all listeners to subscribe

## Deviations from Plan

None - plan executed exactly as written. All 7 tasks completed successfully with no blocking issues.

## Issues Encountered

None - no problems during execution. Build passed successfully, all components render correctly, backend broadcasts function as designed.

## Next Phase Readiness

**Phase 116 now complete:**
- Plan 01: Backend licence service, reload endpoint, background timer, expiry guard ✓
- Plan 02: Admin UI, WebSocket broadcast, real-time updates ✓

All licence management features fully functional and tested. System ready for:
- Production deployment of hot-reload licence feature
- Operator documentation (how to reload licence from admin page)
- Further EE enhancement work in Phase 117+

---
*Phase: 116-fix-smelter-db-migration-and-add-ee-licence-hot-reload*
*Plan: 02-dashboard-ui-websocket-broadcast*
*Completed: 2026-04-02*
