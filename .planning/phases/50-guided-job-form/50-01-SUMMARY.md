---
phase: 50-guided-job-form
plan: 01
subsystem: testing
tags: [vitest, react-testing-library, tdd, wave-0]

# Dependency graph
requires: []
provides:
  - "11 failing test stubs covering GuidedDispatchCard behaviours (JOB-01, JOB-02, JOB-03)"
  - "Wave 0 TDD scaffold ready for Plan 02 implementation"
affects: [50-02, 50-03]

# Tech tracking
tech-stack:
  added: []
  patterns: [Wave 0 stub convention: throw Error('not implemented') so tests fail with clear message rather than skip]

key-files:
  created:
    - puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx
  modified: []

key-decisions:
  - "Wave 0 stub pattern: throw new Error('not implemented') used consistently — runner reports failure not skip, matching Phase 49 decision"
  - "GuidedDispatchCard imported from '../../components/GuidedDispatchCard' (does not exist yet) — intentional to confirm red phase"

patterns-established:
  - "Wave 0 TDD: test file created before component exists; import failure is acceptable for Wave 0 red confirmation"

requirements-completed: [JOB-01, JOB-02, JOB-03]

# Metrics
duration: 3min
completed: 2026-03-23
---

# Phase 50 Plan 01: Guided Job Form Wave 0 Summary

**11 failing vitest stubs for GuidedDispatchCard covering guided form render, JSON preview, and advanced mode — Wave 0 red phase confirmed**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-23T12:36:55Z
- **Completed:** 2026-03-23T12:39:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created Jobs.test.tsx with 11 stubs grouped under `describe('GuidedDispatchCard')`
- All 11 tests confirmed failing (exit non-zero) — red phase established
- Mock for `../../auth` prevents network calls during test execution
- Stubs cover all three requirements: JOB-01 (5 stubs), JOB-02 (2 stubs), JOB-03 (4 stubs)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write 11 failing test stubs for GuidedDispatchCard** - `20b43c9` (test)

**Plan metadata:** (docs: complete plan — committed with state update)

## Files Created/Modified
- `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx` - 11 failing stubs for GuidedDispatchCard; Wave 0 TDD scaffold

## Decisions Made
- Wave 0 stub pattern: `throw new Error('not implemented')` used for all stubs — consistent with Phase 49 decision; runner reports failure rather than skip, giving clear red signal
- Import of `GuidedDispatchCard` from a path that does not yet exist is intentional — confirms the red phase before Plan 02 creates the component

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 0 scaffold complete. Plan 02 can now implement GuidedDispatchCard to turn stubs green.
- Plan 03 handles advanced mode (JOB-03) stubs.

## Self-Check: PASSED

- File `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx`: FOUND
- Commit `20b43c9`: FOUND
- 11 tests failing: CONFIRMED (vitest output: `Tests  11 failed (11)`)

---
*Phase: 50-guided-job-form*
*Completed: 2026-03-23*
