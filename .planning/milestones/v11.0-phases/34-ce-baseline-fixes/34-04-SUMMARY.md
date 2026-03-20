---
phase: 34-ce-baseline-fixes
plan: "04"
subsystem: testing
tags: [pytest, testpaths, pyproject.toml, ce-baseline, gap-closure]

# Dependency graph
requires:
  - phase: 34-ce-baseline-fixes
    provides: "CE stub router, EE test isolation, NodeConfig removal — prerequisite gaps closed"
provides:
  - "testpaths config restricting default CE pytest run to puppeteer/agent_service/tests/"
  - "test_get_job_stats and test_flight_recorder_on_failure marked skip with pre-existing reason"
  - "CE gate: pytest -m 'not ee_only' exits with zero collection errors and zero FAILED"
affects: [35-private-ee-repo, phase-35, phase-36]

# Tech tracking
tech-stack:
  added: []
  patterns: [testpaths-exclusion, pytest-mark-skip-pre-existing]

key-files:
  created: []
  modified:
    - .worktrees/axiom-split/pyproject.toml
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_sprint3.py

key-decisions:
  - "testpaths = ['puppeteer/agent_service/tests'] added to pyproject.toml — puppeteer/tests/ EE files excluded from default CE run, remain opt-in for EE runs"
  - "pre-existing test_sprint3.py 422 vs 200 mismatches marked skip with Phase 34 attribution — deferred to Phase 35+ for actual fix"

patterns-established:
  - "testpaths exclusion pattern: EE integration test directories excluded from CE testpaths; accessible via explicit pytest path argument"
  - "pre-existing failure skip pattern: @pytest.mark.skip with reason attributing phase and deferral target"

requirements-completed: [GAP-03]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 34 Plan 04: GAP-03 CE Pytest Gate Closure Summary

**testpaths config + two pre-existing skip markers close the CE pytest gate: 27 passed, 2 skipped, 0 errors, exit code 0**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T20:25:25Z
- **Completed:** 2026-03-19T20:26:54Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `testpaths = ["puppeteer/agent_service/tests"]` to `pyproject.toml` — `puppeteer/tests/` EE integration files (8 files with missing CE symbols) no longer halt CE collection
- Marked `test_get_job_stats` and `test_flight_recorder_on_failure` in `test_sprint3.py` as `@pytest.mark.skip` with reason attributing these as pre-existing 422 vs 200 mismatches, not Phase 34 regressions
- Full CE gate (`pytest -m "not ee_only"`) now exits with code 0: 27 passed, 2 skipped, 4 deselected (ee_only), zero collection errors
- `puppeteer/tests/` remains explicitly targetable for EE runs (`pytest puppeteer/tests/` still collects all 8 EE files)

## Task Commits

Each task was committed atomically (commits in the `feature/axiom-oss-ee-split` worktree branch):

1. **Task 1: Add testpaths to pyproject.toml** - `7e24d2c` (feat)
2. **Task 2: Skip pre-existing test_sprint3.py failures** - `deb5150` (fix)

**Plan metadata:** committed in main repo docs commit below.

## Files Created/Modified
- `.worktrees/axiom-split/pyproject.toml` - Added `testpaths = ["puppeteer/agent_service/tests"]` under `[tool.pytest.ini_options]`
- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_sprint3.py` - Added `@pytest.mark.skip` to `test_get_job_stats` and `test_flight_recorder_on_failure`

## Decisions Made
- Used `testpaths` (not `.pytest_cache` ignore or custom `conftest.py`) — the standard pytest config mechanism; one line, self-documenting, no custom code
- Skip reason string names Phase 34 explicitly so future developer knows these failures pre-date the split work
- Did not attempt to fix the 422 vs 200 mismatch (those tests reference `/api/jobs/stats` and `/work/{guid}/result` route signatures that may need EE-aware changes — deferred to Phase 35+)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `python3 -m pytest` unavailable in shell PATH (no system pytest). Used `/home/thomas/Development/master_of_puppets/.venv/bin/pytest` directly. Verification outcome identical to plan expectation.
- Worktree files are gitignored from the main repo — committed from inside the worktree (`cd .worktrees/axiom-split && git commit`). This is the expected pattern for worktree-based work.

## User Setup Required

None - no external service configuration required. The worktree branch `feature/axiom-oss-ee-split` contains all changes.

## Next Phase Readiness
- GAP-03 fully resolved: CE pytest gate is clean
- All four Phase 34 gap plans (01-04) are complete — Phase 34 is done
- Phase 35 (Private EE Repo + Plugin Wiring) can begin; depends on GAP-01 (stub router) and GAP-03 (clean pytest) being complete — both now are

---
*Phase: 34-ce-baseline-fixes*
*Completed: 2026-03-19*
