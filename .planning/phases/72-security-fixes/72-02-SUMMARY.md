---
phase: 72-security-fixes
plan: 02
subsystem: security
tags: [security, xss, path-traversal, redos, api-key, nosniff, codeql]

# Dependency graph
requires:
  - "72-01 (failing test scaffolds for all 6 security fixes)"
provides:
  - "All 6 CodeQL security fixes implemented and GREEN: SEC-01 through SEC-06"
  - "validate_path_within() helper in security.py (used by main.py and vault_service.py)"
  - "API_KEY crash removed — server boots with no API_KEY env var"
affects:
  - "72-03 (EE Licence System — if added)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "html.escape() for XSS prevention in inline HTML templates"
    - "pathlib.Path.is_relative_to() for safe path containment checks (Python 3.9+)"
    - "validate_path_within(base, candidate) — reusable security helper in security.py"
    - "Bounded email regex {1,64} / {1,63} quantifiers to prevent ReDoS backtracking"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/security.py
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/services/vault_service.py
    - puppeteer/compose.server.yaml
    - puppeteer/agent_service/tests/test_device_xss.py
    - puppeteer/agent_service/tests/test_docs_traversal.py

key-decisions:
  - "validate_path_within raises HTTP 400 (not 403) — consistent with 'bad request' for malformed input"
  - "XSS test assertion changed from 'no <script> tag' to 'payload not in text' — page has its own JS block"
  - "Traversal URL tests check != 200 (not == 400) — Starlette normalizes path traversal URLs at routing level before they reach handler; security property holds (file never served)"
  - "Unit test added to test_docs_traversal.py verifying validate_path_within raises 400 on dotdot filename"
  - "vault_service.py validate_path_within is defense-in-depth — artifact_id is always uuid4() but guard added anyway"
  - ".env not committed (gitignored) — API_KEY removed from local .env only"

# Metrics
duration: 7min
completed: 2026-03-26
---

# Phase 72 Plan 02: Security Fixes Implementation Summary

**All 6 CodeQL security fixes implemented: XSS escaping, path traversal guards, bounded email regex, API_KEY removal, nosniff header — 18 security tests GREEN**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-26T23:01:30Z
- **Completed:** 2026-03-26T23:08:46Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- **SEC-01 (XSS):** `html.escape()` applied to `user_code` in `device_approve_page()` before inserting into 3 HTML injection points (display div + 2 hidden inputs)
- **SEC-02 (Path traversal, vault):** `validate_path_within()` guard added to `store_artifact()` and `delete_artifact()` in vault_service.py
- **SEC-03 (Path traversal, docs):** Replaced `os.path.abspath + startswith` guard with `validate_path_within()` in `get_doc_content()` route
- **SEC-04 (ReDoS):** Replaced unbounded email regex with bounded `{1,64}` / `{1,63}` quantifiers in `mask_pii()`
- **SEC-05 (API_KEY crash):** Removed `try: API_KEY = os.environ["API_KEY"] ... sys.exit(1)` block, removed `verify_api_key()` function, removed all usages from main.py and node-facing routes
- **SEC-06 (nosniff):** Added `"X-Content-Type-Options": "nosniff"` to `StreamingResponse` headers on CSV export endpoint
- All 18 security tests GREEN (6 test files, 18 tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix security.py** - `ce1a43a` (fix)
2. **Task 2: Fix main.py** - `de79839` (fix)
3. **Task 3: Fix vault_service.py + config cleanup** - `5ca0756` (fix)

## Files Created/Modified

- `puppeteer/agent_service/security.py` — removed API_KEY crash block and verify_api_key(); added validate_path_within() helper; bounded EMAIL_REGEX; added Path import; removed sys import
- `puppeteer/agent_service/main.py` — added html.escape() for XSS; replaced docs path guard with validate_path_within(); removed verify_api_key/API_KEY from imports; removed api_key param from 3 routes; added nosniff header
- `puppeteer/agent_service/services/vault_service.py` — added validate_path_within() to store_artifact() and delete_artifact()
- `puppeteer/compose.server.yaml` — removed API_KEY env var from agent and model service sections
- `puppeteer/agent_service/tests/test_device_xss.py` — fixed test assertion (payload not in text, not no-script-tag)
- `puppeteer/agent_service/tests/test_docs_traversal.py` — updated traversal assertions to != 200; added unit test for validate_path_within dotdot case

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] XSS test assertion too broad — page has own JavaScript**
- **Found during:** Task 2 (running test_device_xss.py after fixing main.py)
- **Issue:** `assert "<script>" not in resp.text` always fails because the approval page includes its own `<script>` block for the token injection JS. The escaping WAS working but the test couldn't see it.
- **Fix:** Changed assertion to `assert payload not in resp.text` — directly checks that the user-supplied injection string doesn't appear verbatim.
- **Files modified:** `puppeteer/agent_service/tests/test_device_xss.py`
- **Commit:** `de79839` (Task 2)

**2. [Rule 1 - Bug] Docs traversal test expected 400 but URL is normalized at routing layer**
- **Found during:** Task 2 (running test_docs_traversal.py after fixing main.py)
- **Issue:** `..%2F..%2Fetc%2Fpasswd` — Starlette URL-decodes `%2F` to `/` and normalizes the path before routing. The request never reaches our `/api/docs/{filename}` handler. Returns 404 (route not found), not 400 (our guard).
- **Fix:** Changed assertions from `== 400` to `!= 200` (traversal is blocked regardless — file is never served). Added a synchronous unit test `test_validate_path_within_rejects_dotdot_filename` that directly calls the function with `../../etc/passwd` as the candidate path (confirming HTTP 400).
- **Files modified:** `puppeteer/agent_service/tests/test_docs_traversal.py`
- **Commit:** `de79839` (Task 2)

**3. [Rule 3 - Blocking] test_openapi_export.py does not exist**
- **Found during:** Task 3 (checking for test_openapi_export.py)
- **Issue:** Plan referenced removing `"API_KEY": "dummy-build-key"` from DUMMY_ENV in test_openapi_export.py. File does not exist in the test directory.
- **Fix:** Skipped that sub-task — no action needed. The export script no longer references API_KEY after security.py cleanup.
- **Files modified:** None

**4. [Rule 3 - Blocking] .env is gitignored**
- **Found during:** Task 3 commit
- **Issue:** `puppeteer/.env` is in `.gitignore`. API_KEY removed locally but cannot be committed.
- **Fix:** Committed compose.server.yaml (removing API_KEY) without the .env file. Noted in commit message.
- **Files modified:** N/A (local .env still updated)

---

**Total deviations:** 4 (all auto-fixed)
**Impact on plan:** All fixes required for correct test behavior or environment constraints. Security properties are correctly verified.

## Issues Encountered

- 9 pre-existing test failures in full suite (unrelated to these changes): `test_job_service.py`, `test_models.py`, `test_sec01_audit.py`, `test_sec02_hmac.py` — all fail due to deprecated `task_type='python_script'` Pydantic validation in test data. Pre-existing before this plan, out of scope.

## User Setup Required

None — server boots cleanly without API_KEY in environment.

## Next Phase Readiness

- All 6 SEC requirements (SEC-01 through SEC-06) implemented and verified
- Phase 72 security fixes complete — ready for Phase 73 (EE Licence System)

## Self-Check: PASSED

- FOUND: puppeteer/agent_service/security.py
- FOUND: puppeteer/agent_service/main.py
- FOUND: puppeteer/agent_service/services/vault_service.py
- FOUND: .planning/phases/72-security-fixes/72-02-SUMMARY.md
- FOUND commit: ce1a43a (Task 1 — security.py)
- FOUND commit: de79839 (Task 2 — main.py + test fixes)
- FOUND commit: 5ca0756 (Task 3 — vault_service.py + config)
