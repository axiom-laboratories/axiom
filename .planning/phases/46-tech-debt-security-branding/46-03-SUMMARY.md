---
phase: 46-tech-debt-security-branding
plan: 03
subsystem: ui
tags: [react, vitest, branding, tsx, foundry]

requires: []
provides:
  - "BRAND-01: Foundry UI label rename — Blueprint->Image Recipe, Template->Node Image, Capability Matrix->Tools"
  - "Templates.test.tsx smoke test suite (5 tests) validating renamed labels"
affects:
  - "47-runtime-expansion"
  - "any future Foundry UI work"

tech-stack:
  added: []
  patterns:
    - "Frontend label rename pattern: only JSX string literals changed, TypeScript identifiers preserved"
    - "TDD applied to UI rename: RED test first, then GREEN after rename"

key-files:
  created:
    - puppeteer/dashboard/src/views/__tests__/Templates.test.tsx
  modified:
    - puppeteer/dashboard/src/views/Templates.tsx
    - puppeteer/dashboard/src/components/CreateBlueprintDialog.tsx
    - puppeteer/dashboard/src/components/CreateTemplateDialog.tsx
    - puppeteer/dashboard/src/components/foundry/BlueprintWizard.tsx
    - puppeteer/dashboard/src/views/Admin.tsx

key-decisions:
  - "Renamed 'Templates' tab to 'Node Images' in addition to the explicit rename map — tab was the primary entry point for template (node image) management"
  - "Test readiness signal changed from 'Templates (N)' to 'Node Images (N)' to match post-rename state"
  - "TypeScript identifiers (Blueprint, BlueprintWizard, BlueprintItem, etc.) intentionally preserved — only JSX string literals changed per plan constraint"

patterns-established:
  - "Foundry rename map: Blueprint=Image Recipe, Puppet Template/Template=Node Image, Capability Matrix=Tools — apply consistently to any new Foundry UI code"

requirements-completed: [BRAND-01]

duration: 5min
completed: 2026-03-22
---

# Phase 46 Plan 03: Foundry UI Label Rename Summary

**Renamed Blueprint->Image Recipe, Template->Node Image, Capability Matrix->Tools across five TSX files with a TDD smoke test; all 28 tests pass and build exits 0.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-22T14:54:57Z
- **Completed:** 2026-03-22T15:00:52Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Applied BRAND-01 rename map to all visible UI string literals in five Foundry TSX files — zero TypeScript interface or component names changed
- Created Templates.test.tsx with 5 smoke tests that confirmed RED before rename and GREEN after rename
- Full 28-test suite passes with no regressions; TypeScript build exits 0

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing BRAND-01 smoke test scaffold** - `0d6edc9` (test)
2. **Task 2: Apply BRAND-01 label rename across all five affected files** - `51a961c` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `puppeteer/dashboard/src/views/__tests__/Templates.test.tsx` - New BRAND-01 smoke test (5 assertions)
- `puppeteer/dashboard/src/views/Templates.tsx` - Tab labels, buttons, empty states, toast messages, dialog titles renamed
- `puppeteer/dashboard/src/components/CreateBlueprintDialog.tsx` - Dialog title, field label, button text renamed
- `puppeteer/dashboard/src/components/CreateTemplateDialog.tsx` - Dialog title, labels, button text renamed
- `puppeteer/dashboard/src/components/foundry/BlueprintWizard.tsx` - Step label, button text, toast message renamed
- `puppeteer/dashboard/src/views/Admin.tsx` - Capability Matrix tab trigger renamed to Tools

## Decisions Made
- Renamed the "Templates" tab to "Node Images" (the tab was the primary home for what the plan calls "Node Images") — this was the correct application of the "Puppet Template/Template -> Node Image" rename rule
- Test readiness signals updated to use "Node Images (N)" pattern after post-rename state was established

## Deviations from Plan

None - plan executed exactly as written. The test readiness assertion was adjusted during Task 2 (after rename) to use the post-rename tab label as the wait signal — this is normal TDD adaptation, not a deviation.

## Issues Encountered
- Initial test used "Templates (N)" as the readiness signal — after rename the tab became "Node Images (N)", causing test timeouts. Fixed immediately by updating the wait pattern.

## User Setup Required
None - frontend-only string changes, no environment variables or external configuration needed.

## Next Phase Readiness
- All Foundry UI now uses consistent product terminology; safe for operator-facing feature work in Phase 47+
- No blockers

## Self-Check: PASSED

- FOUND: `puppeteer/dashboard/src/views/__tests__/Templates.test.tsx`
- FOUND: `.planning/phases/46-tech-debt-security-branding/46-03-SUMMARY.md`
- FOUND commit `0d6edc9` (test: RED)
- FOUND commit `51a961c` (feat: GREEN)

---
*Phase: 46-tech-debt-security-branding*
*Completed: 2026-03-22*
