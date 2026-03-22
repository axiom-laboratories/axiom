---
phase: 45-gap-report-synthesis-critical-fixes
plan: 02
subsystem: testing
tags: [pytest, foundry, cleanup, regression-test, mop_validation, min-07]

requires:
  - phase: 45-01
    provides: "GAP-01 fix context; phase established test pattern"
provides:
  - "MIN-07 regression tests in pytest suite (2 async tests)"
  - "verify_foundry_04_build_dir.py with correct pass/fail assertion"
affects: [phase-44-foundry, foundry-service, mop_validation-scripts]

tech-stack:
  added: []
  patterns:
    - "sys.modules injection pattern for testing EE-only services in CE environment"
    - "asyncio.to_thread forwarding pattern for testing finally-block cleanup"

key-files:
  created:
    - puppeteer/tests/test_foundry_build_cleanup.py
  modified:
    - mop_validation/scripts/verify_foundry_04_build_dir.py

key-decisions:
  - "EE model stubs injected via sys.modules before foundry_service import — Blueprint/PuppetTemplate don't exist in CE db.py, so MagicMock() instances used as class stubs"
  - "asyncio.to_thread patched with fake_to_thread that calls fn(*args) synchronously — allows shutil.rmtree mock to be captured rather than passed to thread executor"
  - "select() in foundry_service.py patched to return MagicMock() — prevents SQLAlchemy ArgumentError when MagicMock class used as ORM model"
  - "subprocess.run patched with FileNotFoundError to simulate podman-not-found path — avoids real podman detection in CI"
  - "6 pre-existing test collection errors (test_foundry_mirror, test_smelter, etc.) confirmed as pre-existing EE-only failures — no new failures introduced by this plan"

patterns-established:
  - "EE-only service testing: inject sys.modules stubs before import; patch select(); patch subprocess.run for engine detection; use fake_to_thread for asyncio.to_thread"

requirements-completed: [GAP-02]

duration: 6min
completed: 2026-03-22
---

# Phase 45 Plan 02: MIN-07 Regression Tests + Verification Script Inversion Summary

**MIN-07 regression tests added to pytest suite; verify_foundry_04_build_dir.py assertion inverted so leftover build dirs produce [FAIL] instead of both outcomes producing [PASS]**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-22T12:32:04Z
- **Completed:** 2026-03-22T12:38:15Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `puppeteer/tests/test_foundry_build_cleanup.py` with 2 async pytest tests asserting `shutil.rmtree` is called in the `finally` block of `FoundryService.build_template()` on both success and failure paths
- Tests work in CE environment (EE models not installed) via `sys.modules` stub injection
- Updated `mop_validation/scripts/verify_foundry_04_build_dir.py` Step 8: leftover `puppet_build_*` dirs now produce `[FAIL]` + `results.append(False)`, no dirs produce `[PASS]` + `results.append(True)`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write MIN-07 regression tests** - `31e012d` (test) — in master_of_puppets repo
2. **Task 2: Invert verify_foundry_04_build_dir.py assertion** - `31bc95b` (fix) — in mop_validation repo

## Files Created/Modified

- `puppeteer/tests/test_foundry_build_cleanup.py` — Two async tests: `test_build_dir_cleaned_up_on_success` and `test_build_dir_cleaned_up_on_failure`. Uses sys.modules EE stub injection, patches select/subprocess/asyncio.to_thread/shutil.rmtree.
- `mop_validation/scripts/verify_foundry_04_build_dir.py` — Step 8 assertion inverted, docstring updated, `_print_summary` step name updated to "Build dir cleaned up (MIN-7 regression)".

## Decisions Made

- **EE model stubs via sys.modules:** `Blueprint`, `PuppetTemplate`, etc. exist only in the compiled Axiom EE `.so` package. The CE `agent_service.db` does not export them. Tests inject `MagicMock()` instances (not the class) as stubs before importing `foundry_service`. This allows the module import to succeed without EE installed.
- **Patching `select()`:** SQLAlchemy's `select()` was called with MagicMock stubs, causing `ArgumentError`. Patching `agent_service.services.foundry_service.select` with `return_value=MagicMock()` avoids this — the `db.execute.side_effect` list handles the actual response sequence.
- **`fake_to_thread` pattern:** `asyncio.to_thread` wraps the `shutil.rmtree` call. Patching with a synchronous forwarder (`fn(*args, **kwargs)`) ensures the test's `shutil.rmtree` mock is called, making the assertion traceable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] EE model classes not available in CE — could not import as plan specified**
- **Found during:** Task 1 (writing regression tests)
- **Issue:** Plan specified `from agent_service.db import Blueprint, PuppetTemplate, ...` — these classes do not exist in the CE `agent_service.db` module. Pre-existing test files (`test_foundry_mirror.py`, etc.) have the same import error and are excluded from the CE pytest run.
- **Fix:** Replaced direct ORM class imports with `sys.modules` injection of `MagicMock()` stubs before importing `foundry_service`. Added `select()` patch and `subprocess.run` patch (for podman engine detection). Used `MagicMock()` instances (not the `MagicMock` class) as stub values so attribute access (`PuppetTemplate.id`) returns another MagicMock instead of raising `AttributeError`.
- **Files modified:** `puppeteer/tests/test_foundry_build_cleanup.py`
- **Verification:** `pytest tests/test_foundry_build_cleanup.py -v` shows 2 passed
- **Committed in:** `31e012d` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — CE/EE model availability bug)
**Impact on plan:** Fix was necessary for correctness; tests run in the CE environment where the plan will be verified. No scope creep.

## Issues Encountered

The CE pytest baseline already has 6 collection errors (`test_foundry_mirror.py`, `test_intent_scanner.py`, `test_lifecycle_enforcement.py`, `test_smelter.py`, `test_staging.py`, `test_tools.py`) — all pre-existing EE-only import failures. Confirmed by running pytest without the new test file. My changes do not introduce any new failures.

## Next Phase Readiness

- MIN-07 regression gap is now closed: both unit-test coverage and full-stack verification script reflect the patched state
- Full-stack verification (`verify_foundry_04_build_dir.py`) will now [FAIL] and exit 1 if future changes regress the `finally: shutil.rmtree` cleanup
- Ready for remaining GAP plans in Phase 45

---
*Phase: 45-gap-report-synthesis-critical-fixes*
*Completed: 2026-03-22*
