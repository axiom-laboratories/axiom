---
phase: 11-compatibility-engine
plan: "04"
subsystem: ui
tags: [react, typescript, tanstack-query, blueprint, capability-matrix, os-family]

# Dependency graph
requires:
  - phase: 11-03
    provides: POST /api/blueprints accepts os_family + confirmed_deps, 422 deps_required response shape, GET /api/capability-matrix?os_family filter
provides:
  - CreateBlueprintDialog with OS family dropdown (DEBIAN / ALPINE)
  - Filtered capability-matrix query keyed on OS family selection
  - Placeholder text in tool list when no OS family selected
  - Two-pass 422 dep-confirmation overlay dialog
affects:
  - 11-05
  - any phase building on blueprint creation UX

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TanStack Query queryKey includes osFamily so query re-fires automatically on OS change
    - Two-pass mutation pattern: mutationFn returns null on soft 422, sets pendingDeps state, second call passes confirmed_deps

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/components/CreateBlueprintDialog.tsx

key-decisions:
  - "mutate(undefined) used at call site (not mutate()) to satisfy TypeScript when mutationFn accepts optional opts parameter"
  - "OS Family dropdown placed before Base OS select — it drives tool filtering so logical ordering requires it first"
  - "Tool chip selection cleared on OS family change — prevents stale tools from a different OS family persisting in state"

patterns-established:
  - "Filtered query pattern: queryKey: ['capability-matrix', osFamily], enabled: !!osFamily — query only fires when filter value is set"
  - "Two-pass mutation: return null on soft 422 (pause for confirmation), re-mutate with confirmed payload on user confirm"

requirements-completed:
  - COMP-04

# Metrics
duration: 2min
completed: 2026-03-11
---

# Phase 11 Plan 04: Blueprint Dialog OS-Aware Tool Filtering Summary

**OS family dropdown + filtered capability-matrix query + two-pass dep-confirmation overlay added to CreateBlueprintDialog for RUNTIME blueprints**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-11T10:28:48Z
- **Completed:** 2026-03-11T10:30:33Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `osFamily` state (`'DEBIAN' | 'ALPINE' | ''`) to `CreateBlueprintDialog`
- Replaced unfiltered capability-matrix query with OS-family-aware version (`queryKey: ['capability-matrix', osFamily]`, `enabled: !!osFamily`)
- Tool list shows placeholder "Select an OS family to see available tools" when no OS selected; chips only render for chosen OS
- Tool selection is cleared whenever OS family changes
- Updated `createMutation` to include `os_family` in POST body for RUNTIME type and accept optional `confirmed_deps`
- 422 `deps_required` response handled by setting `pendingDeps` state without throwing
- Dep-confirm overlay dialog lists each missing dep with amber monospace label and "Confirm & Add" button that re-submits with `confirmed_deps`
- TypeScript compiles cleanly; no new lint errors

## Task Commits

Each task was committed atomically:

1. **Task 1: OS family state + filtered capability-matrix query + updated createMutation** - `f76d68c` (feat)

**Plan metadata:** (docs commit — follows this summary)

## Files Created/Modified
- `puppeteer/dashboard/src/components/CreateBlueprintDialog.tsx` - OS family dropdown, filtered query, two-pass dep-confirm mutation, dep overlay dialog

## Decisions Made
- Used `mutate(undefined)` at the main "Create Blueprint" button call site to satisfy TypeScript strict mode (mutationFn now has typed `opts` param)
- OS Family dropdown placed before Base OS select since OS family drives available tools — logical ordering matches user mental model
- Chip selection cleared on OS family change to prevent stale cross-OS tool selections persisting

## Deviations from Plan

None - plan executed exactly as written.

One minor auto-fix applied during TypeScript verification:

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript error: Expected 1-2 arguments, but got 0 on createMutation.mutate()**
- **Found during:** Task 1 (TypeScript verification step)
- **Issue:** After updating mutationFn signature to `(opts?: {...})`, TanStack Query's `mutate()` call with no arguments fails TS strict check
- **Fix:** Changed `createMutation.mutate()` to `createMutation.mutate(undefined)` at the main button's onClick
- **Files modified:** `puppeteer/dashboard/src/components/CreateBlueprintDialog.tsx`
- **Verification:** `npx tsc --noEmit` shows zero errors from this file
- **Committed in:** f76d68c (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — TypeScript strict mode callsite fix)
**Impact on plan:** Trivial one-line fix required for type correctness. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CreateBlueprintDialog is fully OS-aware; COMP-04 complete
- Plan 11-05 can now build on the OS-filtered blueprint form (wizard or admin matrix editing)
- Backend already accepts `os_family` and `confirmed_deps` from Plan 11-03; frontend now sends both correctly

---
*Phase: 11-compatibility-engine*
*Completed: 2026-03-11*
