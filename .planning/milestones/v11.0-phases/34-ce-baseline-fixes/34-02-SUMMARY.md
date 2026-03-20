---
phase: 34-ce-baseline-fixes
plan: "02"
subsystem: testing
tags: [pytest, markers, ee-isolation, conftest, fixtures]

# Dependency graph
requires: []
provides:
  - ee_only marker registered in pyproject.toml with pytest_collection_modifyitems hook for auto-skip in CE
  - 4 EE-only placeholder test files (lifecycle_enforcement, foundry_mirror, smelter, staging)
  - CE User model constructors free of role= keyword argument in all fixtures, tests, and bootstrap
affects:
  - 34-ce-baseline-fixes (remaining plans)
  - 35-private-ee-repo-plugin-wiring

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ee_only pytest marker: any test that requires axiom-ee decorated with @pytest.mark.ee_only; auto-skipped in CE by conftest.py hook"
    - "importlib.metadata.version('axiom-ee') pattern for EE presence detection — no pkg_resources"

key-files:
  created:
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_lifecycle_enforcement.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_foundry_mirror.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_smelter.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_staging.py
  modified:
    - .worktrees/axiom-split/pyproject.toml
    - .worktrees/axiom-split/puppeteer/agent_service/tests/conftest.py
    - .worktrees/axiom-split/puppeteer/bootstrap_admin.py
    - .worktrees/axiom-split/puppeteer/tests/test_bootstrap_admin.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_db.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_scheduler_service.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_signature_service.py

key-decisions:
  - "Active pytest config is root pyproject.toml (not puppeteer/pyproject.toml) — markers added to root file where [tool.pytest.ini_options] lives"
  - "test_bootstrap_admin.py had puppeteer.* import paths that were wrong for the pythonpath=[puppeteer] setup — fixed to agent_service.* and bootstrap_admin.*"

patterns-established:
  - "EE placeholder test pattern: single @pytest.mark.ee_only decorated function in agent_service/tests/ that passes trivially"
  - "CE User fixture pattern: User(username=..., password_hash=...) with no role= kwarg"

requirements-completed: [GAP-03, GAP-04]

# Metrics
duration: 20min
completed: 2026-03-19
---

# Phase 34 Plan 02: CE Test Isolation (GAP-03 + GAP-04) Summary

**ee_only pytest marker with auto-skip hook isolates EE tests from CE suite; all User.role= references removed from CE fixtures, tests, and bootstrap**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-19T20:00:00Z
- **Completed:** 2026-03-19T20:20:00Z
- **Tasks:** 2 of 2
- **Files modified:** 11

## Accomplishments
- Registered `ee_only` pytest marker in root `pyproject.toml` with auto-skip hook in `conftest.py` using `importlib.metadata` for EE presence detection
- Created 4 EE-only placeholder test files in `puppeteer/agent_service/tests/` — all 4 show as SKIPPED on CE
- Removed `role=` keyword argument from all 5 CE-facing files (bootstrap_admin.py, test_bootstrap_admin.py, test_db.py, test_scheduler_service.py, test_signature_service.py)

## Task Commits

Each task was committed atomically:

1. **Task 1: EE test isolation — marker config + conftest hook + placeholder files** - `6e555cc` (feat)
2. **Task 2: Remove User.role references from CE test suite and bootstrap_admin.py** - `596e094` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `.worktrees/axiom-split/pyproject.toml` - Added `markers` list with `ee_only` under `[tool.pytest.ini_options]`
- `.worktrees/axiom-split/puppeteer/agent_service/tests/conftest.py` - Added `importlib.metadata` import + `pytest_collection_modifyitems` hook
- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_lifecycle_enforcement.py` - Created: EE-only placeholder
- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_foundry_mirror.py` - Created: EE-only placeholder
- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_smelter.py` - Created: EE-only placeholder
- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_staging.py` - Created: EE-only placeholder
- `.worktrees/axiom-split/puppeteer/bootstrap_admin.py` - Removed `role="admin"` from User() constructor
- `.worktrees/axiom-split/puppeteer/tests/test_bootstrap_admin.py` - Fixed imports + removed role= assertions
- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_db.py` - Removed role= constructor arg + replaced role assertion
- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_scheduler_service.py` - Removed role= from test_user fixture
- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_signature_service.py` - Removed role= from test_user fixture

## Decisions Made
- Active pytest config is the root `pyproject.toml` (not `puppeteer/pyproject.toml` which has no pytest config), so `markers` were added there.
- `test_bootstrap_admin.py` had wrong import paths (`puppeteer.agent_service.*` instead of `agent_service.*`) — corrected as Rule 1 auto-fix since the test could never run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed wrong import paths in test_bootstrap_admin.py**
- **Found during:** Task 2 (Remove User.role references)
- **Issue:** `from puppeteer.agent_service.db import ...` and `patch("puppeteer.bootstrap_admin.sessionmaker")` used `puppeteer.*` prefix which is wrong for `pythonpath = ["puppeteer"]` pytest config — caused `ModuleNotFoundError` collection error
- **Fix:** Changed all `puppeteer.agent_service.*` to `agent_service.*`, `puppeteer.bootstrap_admin` to `bootstrap_admin`, and updated patch targets to match
- **Files modified:** `puppeteer/tests/test_bootstrap_admin.py`
- **Verification:** Both test_bootstrap_admin.py tests now pass (2 passed)
- **Committed in:** `596e094` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Necessary correctness fix — test file was already broken due to wrong import prefix. No scope creep.

## Issues Encountered

Pre-existing failures in `puppeteer/tests/` (EE integration tests) and 3 tests in `puppeteer/agent_service/tests/` (test_report_result, test_get_job_stats, test_flight_recorder_on_failure) were present before this plan. These are unrelated to GAP-03/GAP-04 and are logged for deferred follow-up:

- `puppeteer/tests/test_foundry_mirror.py` (and 7 others in `puppeteer/tests/`) — EE integration tests that import missing CE modules (Blueprint, etc.). These need `@pytest.mark.ee_only` decoration in a future plan.
- `test_report_result` — result format assertion mismatch (pre-existing)
- `test_get_job_stats`, `test_flight_recorder_on_failure` — 401/422 response code mismatches (pre-existing)

## Next Phase Readiness
- GAP-03 and GAP-04 are closed: CE test suite can run `pytest -m "not ee_only"` without User.role AttributeErrors or PytestUnknownMarkWarning
- The `puppeteer/tests/` EE integration files (test_foundry_mirror.py etc.) still fail with ImportError — these need ee_only markers or exclusion in a follow-up plan (not blocking Phase 35)
- Phase 35 (Private EE Repo + Plugin Wiring) can proceed — CE test isolation foundation is in place

---
*Phase: 34-ce-baseline-fixes*
*Completed: 2026-03-19*
