---
phase: 50-guided-job-form
plan: "03"
subsystem: ui
tags: [react, radix-ui, dialog, tooltip, vitest, tdd, guided-form]

requires:
  - phase: 50-guided-job-form/50-02
    provides: GuidedDispatchCard with placeholder ADV button and guided form

provides:
  - Advanced mode gate in GuidedDispatchCard (ADV button, two confirmation dialogs, JSON textarea, validation, tooltip, reset path)

affects:
  - Jobs.tsx (uses GuidedDispatchCard)

tech-stack:
  added: ["@radix-ui/react-tooltip (direct import, no ui/tooltip.tsx wrapper)"]
  patterns:
    - "Conditional UI branching: advancedMode flag gates between guided form and JSON textarea"
    - "Radix Dialog for confirmation gates (pendingAdvSwitch / pendingAdvReset state)"
    - "useMemo for client-side JSON schema validation (advancedJsonError)"
    - "Radix Tooltip wrapping span-wrapped disabled button for hover error display"

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/components/GuidedDispatchCard.tsx
    - puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx

key-decisions:
  - "Imported TooltipProvider/Tooltip/TooltipTrigger/TooltipContent directly from @radix-ui/react-tooltip (no ui/tooltip.tsx exists in this project)"
  - "Button label in Advanced mode uses 'Dispatch Payload' (not 'Dispatch Job') to distinguish from guided mode"
  - "aria-label='Return to guided mode' on Guided button enables getByRole query in tests"

patterns-established:
  - "pendingAdvSwitch / pendingAdvReset: two-stage confirm pattern for destructive mode transitions"
  - "advancedJsonError useMemo: real-time schema validation with null=valid, string=error message"

requirements-completed: [JOB-03]

duration: 3min
completed: 2026-03-23
---

# Phase 50 Plan 03: Advanced Mode Gate Summary

**One-way ADV escape hatch with Radix confirmation dialogs, live JSON validation, Tooltip-guarded dispatch, and reset-to-blank guided flow — all 11 tests green.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-23T12:46:23Z
- **Completed:** 2026-03-23T12:49:46Z
- **Tasks:** 1 (TDD: red → green)
- **Files modified:** 2

## Accomplishments
- ADV button (ghost, muted, hidden once in Advanced mode) triggers Radix confirmation Dialog before mode switch — cancel leaves guided form unchanged
- Confirming Advanced mode serialises `generatedPayload` via JSON.stringify into the textarea
- `advancedJsonError` useMemo validates task_type/payload/runtime in real time; inline red error text beneath textarea
- Dispatch button in Advanced mode wrapped in Radix Tooltip showing the error string on hover when disabled
- Reset (← Guided) button triggers second Radix Dialog; confirming resets advancedMode, advancedJson, and form to blank INITIAL_FORM_STATE
- Dispatch handler branches on advancedMode: POSTs raw JSON.parse(advancedJson) or guided generatedPayload
- All 4 JOB-03 stubs implemented and passing; full suite 39/39 green

## Task Commits

1. **Task 1: Add Advanced mode gate to GuidedDispatchCard** - `3e2520b` (feat)

**Plan metadata:** (see final commit)

## Files Created/Modified
- `puppeteer/dashboard/src/components/GuidedDispatchCard.tsx` - Full Advanced mode: state, handlers, dialogs, textarea, tooltip, validation
- `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx` - JOB-03 stubs implemented; unused React import removed

## Decisions Made
- Imported `@radix-ui/react-tooltip` directly (no `ui/tooltip.tsx` in project) — confirmed via directory scan before implementation
- `← Guided` button uses `aria-label="Return to guided mode"` to enable clean `getByRole` queries in tests without ambiguous text match
- Dialog 2 title "Return to guided mode?" matches test's `getByRole('heading')` query — prevents false multi-match against description text

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused React import from Jobs.test.tsx**
- **Found during:** Task 1 (TypeScript verification)
- **Issue:** `import React from 'react'` was present but unused — TS6133 error introduced in Plan 01 stub
- **Fix:** Removed the unused import line
- **Files modified:** `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx`
- **Verification:** `npx tsc --noEmit` no longer reports TS6133 for Jobs.test.tsx
- **Committed in:** 3e2520b (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - pre-existing unused import)
**Impact on plan:** Fix was necessary for TypeScript compliance. Zero scope creep.

## Issues Encountered
- First test run: "Reset" test failed with "Found multiple elements with text /return to guided mode\?/i" — dialog title and description both matched the regex. Fixed by switching to `getByRole('heading', ...)` to target the `<h2>` specifically.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GuidedDispatchCard is fully implemented: guided form (Plan 02) + Advanced mode gate (Plan 03)
- Phase 50 is complete — the guided job dispatch flow with ADV escape hatch is ready for production
- No blockers

## Self-Check: PASSED

All expected files exist and commit 3e2520b verified in git log.

---
*Phase: 50-guided-job-form*
*Completed: 2026-03-23*
