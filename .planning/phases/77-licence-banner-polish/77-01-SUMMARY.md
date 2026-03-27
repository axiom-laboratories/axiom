---
phase: 77-licence-banner-polish
plan: 01
subsystem: ui
tags: [react, lucide-react, vitest, testing-library, sessionstorage, rbac]

# Dependency graph
requires:
  - phase: 74-licence-banner
    provides: Initial grace/expired banner at lines 211-223 of MainLayout.tsx
provides:
  - Role-gated licence banner (admin-only visibility) with sessionStorage dismiss for GRACE state
  - Non-dismissible DEGRADED_CE banner for admin only
  - 4 new tests covering BNR-01 through BNR-05

affects: [78-cli-signing-ux, 79-install-docs-cleanup, 80-github-pages-homepage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "isAdmin derived from existing user constant — no second getUser() call"
    - "sessionStorage dismiss with lazy useState initialiser (key: axiom_licence_grace_dismissed)"
    - "Two independent banner branches rather than combined ternary — satisfies non-coupling requirement"
    - "TDD RED→GREEN flow for UI behaviour testing with mockGetUser vi.fn() per-test override"

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/layouts/MainLayout.tsx
    - puppeteer/dashboard/src/layouts/__tests__/MainLayout.test.tsx

key-decisions:
  - "Use two independent conditional branches for GRACE and DEGRADED_CE banners — prevents graceDismissed state from accidentally suppressing the red expired banner"
  - "Derive isAdmin from already-resolved user constant at line 149 — avoids calling getUser() twice per render"
  - "sessionStorage key constant GRACE_DISMISSED_KEY declared in component body to prevent typos and centralise the string"
  - "getUser mock refactored to vi.fn() with mockReturnValue for per-test role control — plain arrow function cannot be overridden per test"

patterns-established:
  - "Role guard pattern: derive isAdmin from getUser() result, gate banner renders behind isAdmin"
  - "Session-scoped dismiss: lazy useState initialiser reads sessionStorage; setter writes it synchronously"

requirements-completed: [BNR-01, BNR-02, BNR-03, BNR-04, BNR-05]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 77 Plan 01: Licence Banner Polish Summary

**Admin-only amber/red licence banners in MainLayout: GRACE is dismissible via X button (sessionStorage-scoped), DEGRADED_CE is persistent, operators and viewers see nothing**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-27T16:23:25Z
- **Completed:** 2026-03-27T16:25:03Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Role guard added: banners only render when `isAdmin` (operator and viewer users see no banner regardless of licence state)
- GRACE banner split from DEGRADED_CE — each branch independent, preventing state cross-contamination
- Dismiss button (X icon, aria-label "Dismiss licence warning") on GRACE banner writes to sessionStorage key `axiom_licence_grace_dismissed` and hides banner without reload
- DEGRADED_CE banner has no dismiss control — persists until licence state changes
- 4 new tests (Tests 16-19) cover all BNR requirements; full suite 60/60 pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failing test stubs (RED)** - `375003d` (test)
2. **Task 2: Implement role guard and split banner branches (GREEN)** - `b160ae0` (feat)

_Note: TDD tasks — RED commit then GREEN commit._

## Files Created/Modified
- `puppeteer/dashboard/src/layouts/MainLayout.tsx` - Added X import, isAdmin constant, graceDismissed state with sessionStorage lazy init, two independent banner branches replacing the combined ternary
- `puppeteer/dashboard/src/layouts/__tests__/MainLayout.test.tsx` - Refactored getUser mock to vi.fn(), added sessionStorage.clear() to beforeEach, added Tests 16-19

## Decisions Made
- Two independent conditional branches for GRACE and DEGRADED_CE banners rather than a combined ternary — prevents graceDismissed state from accidentally suppressing the red expired banner (Pitfall 3 from RESEARCH.md)
- isAdmin derived from already-resolved user constant at line 149 — avoids calling getUser() twice per render
- sessionStorage key stored in a named constant (GRACE_DISMISSED_KEY) in component body to centralise the string

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- Phase 77 Plan 01 complete — all 5 BNR requirements met
- Phase 78 (CLI Signing UX) can proceed independently
- No blockers

---
*Phase: 77-licence-banner-polish*
*Completed: 2026-03-27*
