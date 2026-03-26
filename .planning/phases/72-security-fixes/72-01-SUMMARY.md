---
phase: 72-security-fixes
plan: 01
subsystem: testing
tags: [pytest, security, xss, path-traversal, redos, anyio, httpx]

# Dependency graph
requires: []
provides:
  - "Failing RED test suite for all 6 security fixes (SEC-01 through SEC-06)"
  - "validate_path_within helper contract defined via test_vault_traversal.py"
  - "auth dep-override pattern established for ASGI test clients"
affects: [72-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FastAPI dependency_overrides for auth bypass in ASGI tests (MagicMock user + DB override)"
    - "TDD RED phase: test asserts the fixed behaviour before implementation lands"
    - "validate_path_within contract tested against security.py import"

key-files:
  created:
    - puppeteer/agent_service/tests/test_device_xss.py
    - puppeteer/agent_service/tests/test_vault_traversal.py
    - puppeteer/agent_service/tests/test_docs_traversal.py
    - puppeteer/agent_service/tests/test_csv_nosniff.py
  modified:
    - puppeteer/agent_service/tests/test_pii.py
    - puppeteer/agent_service/tests/test_security.py

key-decisions:
  - "test_vault_traversal.py tests validate_path_within() directly (not VaultService) — vault_service.py has broken Artifact import that would cause ImportError if VaultService is imported"
  - "test_csv_nosniff.py uses /jobs/export not /api/jobs/export — route has no /api prefix"
  - "Dependency override pattern (MagicMock + override_get_current_user) used for auth-required endpoints instead of real JWT — avoids DB user creation in test"
  - "ReDoS timing test (test_pii_redos_safety) passes with current regex — acceptable per plan, fix lands in Plan 02"

patterns-established:
  - "TDD auth client fixture: async fixture using app.dependency_overrides + MagicMock user"
  - "validate_path_within contract: tests import the helper and call with Path objects, expect HTTPException(400)"

requirements-completed: []

# Metrics
duration: 22min
completed: 2026-03-26
---

# Phase 72 Plan 01: Security Test Scaffolds (Wave 0) Summary

**Wave 0 RED test suite: 4 new test files + 2 updated covering all 6 CodeQL security fixes, with failing assertions that will turn GREEN when Plan 02 fixes land**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-03-26T22:35:00Z
- **Completed:** 2026-03-26T22:57:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created 4 new test files covering SEC-01 (XSS), SEC-02 (vault traversal), SEC-03 (docs traversal), SEC-06 (nosniff header)
- Updated test_pii.py with ReDoS timing test for SEC-04
- Removed API_KEY import from test_security.py for SEC-05 readiness
- All 9 security assertion tests FAIL (RED), all 8 existing/sanity tests PASS (GREEN)
- No ImportError in any test file — all collect cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Create failing test files for SEC-01, SEC-02, SEC-03, SEC-06** - `ed7ea20` (test)
2. **Task 2: Update existing test_pii.py and test_security.py** - `732329a` (test)

## Files Created/Modified

- `puppeteer/agent_service/tests/test_device_xss.py` - XSS test: raw `<script>` and attribute-breaking payload in GET /auth/device/approve
- `puppeteer/agent_service/tests/test_vault_traversal.py` - Path traversal: validate_path_within() must raise HTTP 400 for `../../../etc/passwd`
- `puppeteer/agent_service/tests/test_docs_traversal.py` - Docs path traversal: /api/docs/{filename} must return 400 not 404 for traversal
- `puppeteer/agent_service/tests/test_csv_nosniff.py` - CSV export: X-Content-Type-Options: nosniff must be present
- `puppeteer/agent_service/tests/test_pii.py` - Added ReDoS timing test for mask_pii() adversarial input
- `puppeteer/agent_service/tests/test_security.py` - Removed API_KEY from import; existing tests still pass

## Decisions Made

- **vault_service.py has broken Artifact import** — `Artifact` DB model doesn't exist in `db.py`, so `VaultService` can't be imported. Designed `test_vault_traversal.py` to test `validate_path_within()` from `security.py` directly rather than going through `VaultService`. This tests the same security contract (the helper that Plan 02 will add).
- **Route prefix correction** — The CSV export is at `/jobs/export` not `/api/jobs/export`. Fixed in test after first test run returned 404.
- **Auth override pattern** — Used `app.dependency_overrides` with `MagicMock` user instead of real JWT tokens, following the pattern established in `test_job51_bulk.py`. This avoids needing a real user in the test DB.
- **ReDoS test outcome** — The current email regex completes fast enough (< 2s) on the adversarial input. The timing test passes even before the fix. This is acceptable per plan spec; the test documents the requirement that future regex changes must stay fast.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Redesigned test_vault_traversal.py to avoid broken VaultService import**
- **Found during:** Task 1 (creating test_vault_traversal.py)
- **Issue:** `vault_service.py` imports `Artifact` from `..db`, but the `Artifact` SQLAlchemy model is not defined in `db.py`. Importing `VaultService` triggers `ImportError` at collection time, giving ERROR not FAILED state.
- **Fix:** Rewrote test to import `validate_path_within` from `agent_service.security` directly (using a `_get_validate_fn()` helper that catches ImportError and returns None). Tests fail with `AssertionError: validate_path_within not found` instead of ImportError — a clean FAILED state.
- **Files modified:** `puppeteer/agent_service/tests/test_vault_traversal.py`
- **Committed in:** `ed7ea20` (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed CSV export URL from /api/jobs/export to /jobs/export**
- **Found during:** Task 1 (test_csv_nosniff.py)
- **Issue:** Initial test used `/api/jobs/export` but the route in `main.py` is registered at `/jobs/export` (no `/api` prefix), returning 404.
- **Fix:** Corrected URL in both test functions.
- **Files modified:** `puppeteer/agent_service/tests/test_csv_nosniff.py`
- **Committed in:** `ed7ea20` (Task 1 commit, fixed before commit)

**3. [Rule 3 - Blocking] Switched from real JWT auth to dependency_overrides for authenticated routes**
- **Found during:** Task 1 (test_docs_traversal.py, test_csv_nosniff.py)
- **Issue:** `require_auth` does a DB lookup for the user. A JWT with `sub: "admin"` returns 401 if no matching user row exists in the test DB. Test was returning 401 instead of the expected status.
- **Fix:** Adopted `app.dependency_overrides` + `MagicMock` user pattern (per `test_job51_bulk.py`).
- **Files modified:** `puppeteer/agent_service/tests/test_docs_traversal.py`, `puppeteer/agent_service/tests/test_csv_nosniff.py`
- **Committed in:** `ed7ea20` (Task 1 commit, fixed before commit)

---

**Total deviations:** 3 auto-fixed (all Rule 3 — blocking issues)
**Impact on plan:** All fixes required for correct RED test state. No scope creep.

## Issues Encountered

- `Artifact` DB model missing from `db.py` despite being referenced in `vault_service.py`. Deferred to implementation team — not in scope for Plan 01 (test scaffolds only). Plan 02 should note this when implementing SEC-02.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 6 test files ready to go GREEN when Plan 02 security fixes land
- Plan 02 should implement: html.escape() for SEC-01, validate_path_within() helper for SEC-02/03, bounded regex for SEC-04, API_KEY removal for SEC-05, nosniff header for SEC-06
- Blocker note: `validate_path_within` must be added to `security.py` (not just vault_service.py) — test_vault_traversal.py imports it from there

## Self-Check: PASSED

- FOUND: puppeteer/agent_service/tests/test_device_xss.py
- FOUND: puppeteer/agent_service/tests/test_vault_traversal.py
- FOUND: puppeteer/agent_service/tests/test_docs_traversal.py
- FOUND: puppeteer/agent_service/tests/test_csv_nosniff.py
- FOUND: .planning/phases/72-security-fixes/72-01-SUMMARY.md
- FOUND commit: ed7ea20 (Task 1)
- FOUND commit: 732329a (Task 2)

---
*Phase: 72-security-fixes*
*Completed: 2026-03-26*
