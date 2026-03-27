---
phase: 73-ee-licence-system
plan: 01
subsystem: testing
tags: [tdd, jwt, eddsa, ed25519, licence, ee]

# Dependency graph
requires: []
provides:
  - 7 failing RED tests covering all LIC-01 through LIC-07 requirements
  - Test contracts for licence_service.py public API (LicenceState, LicenceStatus, _compute_state, load_licence, check_and_record_boot, _decode_licence_jwt)
  - Test contracts for /api/licence endpoint shape and enroll_node 402 node-limit path
affects: [73-02, 73-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED phase: 7 unit tests import from function scope to produce ModuleNotFoundError as failure signal"
    - "EdDSA JWT round-trip test: generate inline keypair, encode with PyJWT, decode with test pub key"
    - "Clock rollback test: write future timestamp to tempfile boot.log, patch BOOT_LOG_PATH constant"
    - "FastAPI TestClient dependency override: app.dependency_overrides[require_auth] = lambda: mock_user"

key-files:
  created:
    - puppeteer/tests/test_licence_service.py
  modified: []

key-decisions:
  - "Import path for licence_service is puppeteer.agent_service.services.licence_service — consistent with existing service module pattern"
  - "Test for test_enroll_node_limit_enforced imports enroll_node from puppeteer.agent_service.main (not from licence_service) — the node limit guard lives in main.py"
  - "All 7 tests use function-scope imports so ModuleNotFoundError is the RED failure, not import-time crash at collection"

patterns-established:
  - "Pattern: TDD RED tests use function-scope imports from missing modules to cleanly signal missing implementation"

requirements-completed: [LIC-01, LIC-02, LIC-03, LIC-04, LIC-05, LIC-06, LIC-07]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 73 Plan 01: Licence System RED Tests Summary

**7 failing unit tests documenting the exact EdDSA licence service contract for all LIC requirements (Wave 0 TDD RED phase)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T08:14:08Z
- **Completed:** 2026-03-27T08:16:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `puppeteer/tests/test_licence_service.py` with exactly 7 test functions
- All 7 tests fail with `ModuleNotFoundError: No module named 'puppeteer.agent_service'` — RED phase confirmed
- Each test maps precisely to one LIC requirement (LIC-01 through LIC-07)
- Tests document the exact public API contract that plan 02/03 must implement

## Task Commits

1. **Task 1: Write RED test file for all 7 LIC requirements** - `abd12e4` (test)

## Files Created/Modified
- `puppeteer/tests/test_licence_service.py` - 7 failing unit tests for LIC-01 through LIC-07

## Decisions Made
- Import path `puppeteer.agent_service.services.licence_service` follows the plan's spec and matches existing service module pattern (`signature_service`, `job_service`, etc.)
- `test_enroll_node_limit_enforced` imports from `puppeteer.agent_service.main` not licence_service, because the node limit guard belongs in `enroll_node()` in main.py per the research spec
- Function-scope imports chosen over module-scope so test collection succeeds and each test fails individually rather than one import error blocking all 7

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RED tests committed and confirmed failing on all 7 LIC requirements
- Plan 02 (GREEN phase) can now implement `puppeteer/agent_service/services/licence_service.py` and turn all 7 tests green
- Plan 03 will integrate licence_service into main.py lifespan + enroll_node + /api/licence route

## Self-Check: PASSED

- `puppeteer/tests/test_licence_service.py` — FOUND
- commit `abd12e4` — FOUND
- `.planning/phases/73-ee-licence-system/73-01-SUMMARY.md` — FOUND

---
*Phase: 73-ee-licence-system*
*Completed: 2026-03-27*
