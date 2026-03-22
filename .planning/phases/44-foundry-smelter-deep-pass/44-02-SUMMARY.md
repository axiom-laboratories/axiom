---
phase: 44-foundry-smelter-deep-pass
plan: 02
subsystem: testing
tags: [foundry, smelter, validation, docker, python, requests, subprocess]

# Dependency graph
requires:
  - phase: 42-ee-validation-pass
    provides: confirmed EE stack with foundry and smelter services active
provides:
  - FOUNDRY-04 MIN-7 build directory cleanup gap documentation script
  - FOUNDRY-06 WARNING mode enforcement path verification script
affects:
  - 44-foundry-smelter-deep-pass (run_foundry_matrix.py runner — plan 05)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - EE pre-flight guard via GET /api/features — [SKIP] exit 0 on CE builds
    - Dynamic agent container discovery via docker ps --filter name=agent
    - Dual-outcome gap documentation — both "confirmed" and "fixed" outcomes produce [PASS]
    - try/finally enforcement mode restore pattern for smelter config changes
    - GET /api/templates (list) + filter by ID to read is_compliant field (no GET /api/templates/{id} endpoint)

key-files:
  created:
    - mop_validation/scripts/verify_foundry_04_build_dir.py
    - mop_validation/scripts/verify_foundry_06_warning.py
  modified: []

key-decisions:
  - "FOUNDRY-04: Both GAP CONFIRMED and GAP FIXED outcomes are [PASS] — this is a gap documentation test, not an assertion that the gap exists"
  - "FOUNDRY-04: foundry_service.py lines 241-243 show build dir IS cleaned in finally block — script may report FIXED on the live stack"
  - "FOUNDRY-06: No GET /api/templates/{id} endpoint exists — must use GET /api/templates (list) and filter by ID to read is_compliant"
  - "FOUNDRY-06: Audit log entry for template:build does not carry an explicit WARNING tag — is_compliant=False is the primary documented WARNING signal; gap noted as [INFO]"
  - "FOUNDRY-06: Exit 1 only if build was blocked (non-200) or is_compliant remains True — audit log absence is [INFO] not [FAIL]"

patterns-established:
  - "Foundry script pattern: EE pre-flight → dynamic container discovery → test logic → finally restore → dual outcome"
  - "Gap documentation pattern: both expected and fixed outcomes produce [PASS] with clear labelling"

requirements-completed:
  - FOUNDRY-04
  - FOUNDRY-06

# Metrics
duration: 3min
completed: 2026-03-22
---

# Phase 44 Plan 02: Foundry Validation Scripts (FOUNDRY-04 + FOUNDRY-06) Summary

**Two standalone Foundry validation scripts: MIN-7 build-dir cleanup gap documentation (dual-[PASS]) and WARNING mode enforcement path (is_compliant=False assertion with finally-restore)**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-22T09:09:04Z
- **Completed:** 2026-03-22T09:11:38Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `verify_foundry_04_build_dir.py`: globs /tmp/puppet_build_* before/after a successful build; reports whether MIN-7 gap is confirmed or fixed — both outcomes are [PASS]; exits 1 only on stack/build failure
- `verify_foundry_06_warning.py`: sets smelter mode to WARNING, builds with an unapproved package, asserts HTTP 200 (not blocked) and is_compliant=False on template; restores mode in finally
- Both scripts use the canonical Phase 43 pattern: EE pre-flight ([SKIP] on CE), load_env, wait_for_stack, get_admin_token, _print_summary

## Task Commits

Each task was committed atomically (in mop_validation repo):

1. **Task 1: verify_foundry_04_build_dir.py** - `3f85ac2` (feat)
2. **Task 2: verify_foundry_06_warning.py** - `346f7b2` (feat)

## Files Created/Modified

- `mop_validation/scripts/verify_foundry_04_build_dir.py` - FOUNDRY-04 MIN-7 gap documentation; dual-outcome [PASS]; docker exec glob pattern
- `mop_validation/scripts/verify_foundry_06_warning.py` - FOUNDRY-06 WARNING mode; try/finally enforcement mode restore; is_compliant=False assertion

## Decisions Made

- No `GET /api/templates/{id}` endpoint exists in the EE foundry router — used `GET /api/templates` list and filtered by ID to read `is_compliant`.
- `foundry_service.py` already cleans up build dirs in its `finally` block (lines 241-243 via `shutil.rmtree`). FOUNDRY-04 will likely report "MIN-7 appears FIXED" on the live EE stack. The dual-outcome design handles this correctly.
- FOUNDRY-06 audit log does not distinguish WARNING builds from clean builds — `is_compliant=False` is the primary documented signal. Audit gap noted as `[INFO]`, not `[FAIL]`.

## Deviations from Plan

None — plan executed exactly as written. One implementation note: the plan's interface snippet referenced `GET /api/templates/{tmpl_id}` but no such single-resource endpoint exists; adapted to use the list endpoint (Rule 1 auto-fix, minor).

## Issues Encountered

None — both scripts produced clean [SKIP] exit 0 on the CE stack (correct pre-flight behaviour). EE stack required to exercise the full test paths.

## User Setup Required

None - scripts are standalone validation tools. EE stack required for full execution (scripts [SKIP] gracefully on CE).

## Next Phase Readiness

- FOUNDRY-04 and FOUNDRY-06 scripts complete the simpler half of the 6-script suite
- Plans 44-03 (FOUNDRY-01 wizard), 44-04 (FOUNDRY-02 STRICT + FOUNDRY-03 failure), 44-05 (FOUNDRY-05 air-gap + runner) remain
- All scripts follow the same EE pre-flight + [SKIP] pattern — runner (plan 44-05) can call them safely on mixed CE/EE environments

---
*Phase: 44-foundry-smelter-deep-pass*
*Completed: 2026-03-22*
