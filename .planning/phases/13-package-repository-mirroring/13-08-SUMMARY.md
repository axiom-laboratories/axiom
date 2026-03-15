---
phase: 13-package-repository-mirroring
plan: 08
subsystem: testing
tags: [pytest, mirror, foundry, mocking, asyncio, async-mock]

requires:
  - phase: 13-06
    provides: mirror_log column, is_active filter, MirrorService log capture, foundry fail-fast fix

provides:
  - "6 passing tests in test_mirror.py with correct agent_service imports"
  - "2 passing tests in test_foundry_mirror.py with real Dockerfile inspection and sequential mock"
  - "pyproject.toml pythonpath config so agent_service resolves when running pytest from puppeteer/"

affects:
  - 13-package-repository-mirroring
  - future test authoring patterns for foundry/mirror services

tech-stack:
  added: []
  patterns:
    - "_make_mock_db with sequential side_effect list for multi-query service tests"
    - "Patch shutil.rmtree in finally-block cleanup to keep build artifacts for assertion"
    - "Separate _make_scalar_one_result and _make_scalars_all_result helpers for different SQLAlchemy query patterns"
    - "pyproject.toml [tool.pytest.ini_options] pythonpath = ['puppeteer'] for correct import resolution"

key-files:
  created:
    - puppeteer/tests/test_mirror.py
    - puppeteer/tests/test_foundry_mirror.py
  modified:
    - pyproject.toml

key-decisions:
  - "Sequential side_effect list in _make_mock_db instead of SQL-repr string-matching: more robust and readable"
  - "shutil.rmtree patched alongside copytree/copy2 because finally block deletes build_dir before test assertions run"
  - "pythonpath added to pyproject.toml [tool.pytest.ini_options] to fix agent_service import resolution without PYTHONPATH env var"
  - "_make_scalars_all_result helper needed for validate_blueprint query which uses scalars().all() rather than scalar_one_or_none()"

requirements-completed: [PKG-01, PKG-02, REPO-02, REPO-03, REPO-04]

duration: 6min
completed: 2026-03-15
---

# Phase 13 Plan 08: Mirror Test Suite Repair Summary

**8 passing tests (6 mirror + 2 foundry) confirming PKG log capture, fail-fast 403, and Dockerfile COPY injection via real filesystem inspection**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-15T20:34:17Z
- **Completed:** 2026-03-15T20:40:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Rewrote `test_mirror.py` from 3 broken tests to 6 passing tests with correct `from agent_service...` imports
- Added `test_mirror_pypi_log_capture` verifying `ingredient.mirror_log` is set after `_mirror_pypi` call
- Added `test_mirror_ingredient_failure` verifying `mirror_status="FAILED"` when `_mirror_pypi` raises
- Added `test_sources_list_generation` verifying `deb [trusted=yes]` in `get_sources_list_content()` output
- Rewrote `test_foundry_mirror.py` replacing SQL-string-matching mock with `_make_mock_db` sequential side_effect list
- `test_foundry_mirror_injection` now opens Dockerfile from disk and asserts both `COPY pip.conf` and `COPY sources.list` lines present
- Fixed `pyproject.toml` to add `pythonpath = ["puppeteer"]` so `cd puppeteer && pytest` works without PYTHONPATH env var

## Task Commits

1. **Task 1: Rewrite test_mirror.py with 6 tests and correct imports** - `03cae11` (test)
2. **Task 2: Rewrite test_foundry_mirror.py with real assertions and sequential mock** - `4e17aa9` (test)

**Plan metadata:** `[docs commit hash]` (docs: complete plan)

## Files Created/Modified

- `puppeteer/tests/test_mirror.py` - 6 tests for MirrorService: command construction, orchestration, pip.conf generation, log capture, failure handling, sources.list generation
- `puppeteer/tests/test_foundry_mirror.py` - 2 tests for FoundryService mirror integration: fail-fast 403 on PENDING ingredient, Dockerfile COPY injection verified on disk
- `pyproject.toml` - Added `[tool.pytest.ini_options]` with `pythonpath = ["puppeteer"]` and `asyncio_mode = "auto"`

## Decisions Made

- **Sequential side_effect list in `_make_mock_db`**: Avoids fragile SQL repr string-matching. The list order matches the actual DB query sequence in `build_template` (tmpl → rt_bp → nw_bp → cfg → validate_blueprint scalars → mirror check scalar_one_or_none).
- **`shutil.rmtree` must be patched**: The `finally` block in `build_template` calls `asyncio.to_thread(shutil.rmtree, build_dir)` which deletes the build_dir before the test's assertions run. Patching `shutil.rmtree` prevents premature cleanup.
- **Two result helper functions**: `_make_scalar_one_result` for queries using `scalar_one_or_none()` and `_make_scalars_all_result` for `SmelterService.validate_blueprint` which uses `scalars().all()`.
- **pyproject.toml pythonpath**: Added `pythonpath = ["puppeteer"]` to allow running `cd puppeteer && pytest` as documented in CLAUDE.md without needing to set PYTHONPATH manually.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added pythonpath to pyproject.toml**
- **Found during:** Task 1 (initial test run)
- **Issue:** `from agent_service...` imports failed with `ModuleNotFoundError: No module named 'agent_service'` because pytest rootdir is the repo root, not `puppeteer/`
- **Fix:** Added `[tool.pytest.ini_options]` section to pyproject.toml with `pythonpath = ["puppeteer"]` and `asyncio_mode = "auto"`
- **Files modified:** pyproject.toml
- **Verification:** All 6 tests pass without PYTHONPATH env var
- **Committed in:** 03cae11 (Task 1 commit)

**2. [Rule 1 - Bug] Added shutil.rmtree mock to test_foundry_mirror_injection**
- **Found during:** Task 2 (test_foundry_mirror_injection)
- **Issue:** `assert os.path.isfile(dockerfile_path)` failed because the `finally` block in `build_template` deleted the build_dir via `asyncio.to_thread(shutil.rmtree, build_dir)` before test assertions ran
- **Fix:** Added `patch("shutil.rmtree")` to the `with patch(...)` context manager block in the test
- **Files modified:** puppeteer/tests/test_foundry_mirror.py
- **Verification:** Both foundry tests pass; Dockerfile on disk confirmed
- **Committed in:** 4e17aa9 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking import fix, 1 test logic bug fix)
**Impact on plan:** Both auto-fixes required for tests to run and pass. No scope creep.

## Issues Encountered

- `asyncio.to_thread(os.makedirs, ...)` vs direct `os.makedirs`: The `fake_makedirs` capture worked correctly because patching `os.makedirs` intercepts calls made through `asyncio.to_thread`. The directory IS created; the failure was purely the rmtree cleanup.
- `validate_blueprint` uses `scalars().all()` while all other queries use `scalar_one_or_none()` — required a separate mock result helper to avoid AttributeError.

## Next Phase Readiness

- All 8 tests pass: `cd puppeteer && pytest tests/test_mirror.py tests/test_foundry_mirror.py -v` → 8 passed
- Phase 13 gap closure complete (plans 06, 07, 08 all delivered)
- No blockers for Phase 19 continuation

---
*Phase: 13-package-repository-mirroring*
*Completed: 2026-03-15*
