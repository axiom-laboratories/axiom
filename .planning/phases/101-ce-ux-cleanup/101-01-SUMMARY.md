---
phase: 101-ce-ux-cleanup
plan: "01"
subsystem: ui
tags: [react, radix-tabs, feature-gating, licence, upgrade-placeholder]

# Dependency graph
requires: []
provides:
  - CE Admin page shows only Onboarding, Data, and + Enterprise tabs
  - EE Admin tabs (Smelter Registry, BOM Explorer, Tools, Artifact Vault, Rollouts, Automation) gated behind isEnterprise
  - + Enterprise tab renders UpgradePlaceholder grid for all six EE features
affects: [phase-102, phase-103]

# Tech tracking
tech-stack:
  added: []
  patterns: [isEnterprise gate on TabsTrigger + TabsContent pairs, UpgradePlaceholder grid for CE upgrade panels]

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/Admin.tsx

key-decisions:
  - "isEnterprise destructured at Admin component scope (not inside LicenceSection subcomponent) so it can be used in JSX render"
  - "EE TabsTrigger and TabsContent both gated so neither the tab button nor its content panel ever renders for CE users"
  - "+ Enterprise trigger placed after EE triggers and before Data to keep CE tab bar as: Onboarding | + Enterprise | Data"

patterns-established:
  - "EE tab gating pattern: {isEnterprise && (<TabsTrigger .../>)} + matching {isEnterprise && (<TabsContent .../>)}"
  - "CE upgrade panel pattern: {!isEnterprise && (<TabsContent value='enterprise'><grid of UpgradePlaceholder /></TabsContent>)}"

requirements-completed:
  - CEUX-01
  - CEUX-02
  - CEUX-03

# Metrics
duration: 15min
completed: 2026-03-31
---

# Plan 101-01: CE Tab Gating + Upgrade Panel in Admin.tsx Summary

**Six EE Admin tabs gated behind isEnterprise with a CE + Enterprise upgrade panel listing all gated features via UpgradePlaceholder**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-31T18:50:00Z
- **Completed:** 2026-03-31T18:55:00Z
- **Tasks:** 6 (tasks 1–5 implementation + task 6 verification)
- **Files modified:** 1

## Accomplishments
- Added `isEnterprise` destructure to the `Admin` component body (not just inside `LicenceSection`)
- Gated all six EE `TabsTrigger` and `TabsContent` blocks with `{isEnterprise && (...)}`
- Added `+ Enterprise` tab trigger and content panel (gated `{!isEnterprise && (...)}`) that renders an `UpgradePlaceholder` grid for all six EE features
- Imported `UpgradePlaceholder` into `Admin.tsx`
- Verified with Python Playwright: CE tab bar shows `[Onboarding] [+ Enterprise] [Data]`, six EE tabs absent, clicking `+ Enterprise` renders 6 upgrade placeholder headings

## Task Commits

1. **Tasks 2–5: Import, isEnterprise, tab gating, upgrade panel** - `0247a82` (feat)

## Files Created/Modified
- `puppeteer/dashboard/src/views/Admin.tsx` - Added isEnterprise destructure, gated 6 EE tabs, added + Enterprise upgrade panel

## Decisions Made
- Placed `+ Enterprise` trigger between the last EE trigger slot and the `Data` tab, keeping the CE bar clean as `Onboarding | + Enterprise | Data`
- Kept all six EE TabsContent components in the file tree wrapped by `{isEnterprise && (...)}` rather than deleting them, preserving EE functionality

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Initial Playwright test targeted the old dashboard container (not yet rebuilt). Rebuilding `dashboard` image resolved this immediately.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CE UX cleanup for Admin tabs is complete; no blank pages or EE-only views leak to CE users
- Phase 102 (Linux E2E) and Phase 103 (Windows E2E) can now proceed against a clean CE UI

---
*Phase: 101-ce-ux-cleanup*
*Completed: 2026-03-31*
