---
phase: 72-security-fixes
verified: 2026-03-26T23:30:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 72: Security Fixes Verification Report

**Phase Goal:** Harden the backend against 6 identified security vulnerabilities: device-name XSS, path traversal in vault and docs endpoints, ReDoS in PII masking regex, API_KEY crash vector and legacy exposure in compose, and missing X-Content-Type-Options header on CSV exports.
**Verified:** 2026-03-26T23:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | GET /auth/device/approve?user_code=`<script>alert(1)</script>` returns HTML with escaped payload | VERIFIED | `_html.escape(user_code or "")` at main.py:581; all 3 injection points use `escaped_code`; test_device_xss.py 2 tests PASS |
| 2   | Vault delete with `../../../etc/passwd` artifact_id raises HTTP 400 | VERIFIED | `validate_path_within()` called in both `store_artifact()` and `delete_artifact()` in vault_service.py:24,75; test_vault_traversal.py 4 tests PASS |
| 3   | GET /api/docs/../../../etc/passwd does not return 200 | VERIFIED | `validate_path_within(Path(docs_dir), Path(docs_dir) / filename)` at main.py:1813; Starlette normalises path traversal URLs (returns 404/307, never 200); test_docs_traversal.py 4 tests PASS |
| 4   | mask_pii() on adversarial 10k-char string with multiple @ completes in under 2 seconds | VERIFIED | Bounded EMAIL_REGEX `{1,64}` / `{1,63}` quantifiers in security.py:83; test_pii.py::test_mask_pii_redos_safety PASSES in <2s |
| 5   | Server boots cleanly with no API_KEY in environment | VERIFIED | API_KEY crash block (`try: API_KEY = os.environ["API_KEY"]...sys.exit(1)`) removed from security.py; `verify_api_key` function removed; `API_KEY` removed from main.py imports; `api_key: str = Depends(verify_api_key)` removed from pull_work, receive_heartbeat, report_result; API_KEY removed from compose.server.yaml |
| 6   | GET /api/jobs/export response contains X-Content-Type-Options: nosniff | VERIFIED | `"X-Content-Type-Options": "nosniff"` in StreamingResponse headers at main.py:882; test_csv_nosniff.py 2 tests PASS |
| 7   | Full pytest suite (agent_service tests) passes with no new failures | VERIFIED | 72 passed, 9 skipped; 9 pre-existing failures confirmed in SUMMARY (deprecated `task_type='python_script'` Pydantic validation in test data, unrelated to phase 72) |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `puppeteer/agent_service/security.py` | validate_path_within() helper, bounded email regex, API_KEY crash removed | VERIFIED | validate_path_within at line 98; EMAIL_REGEX bounded at line 83; no API_KEY or sys.exit anywhere in file |
| `puppeteer/agent_service/main.py` | XSS-escaped device approve page, path guard on docs route, nosniff header on CSV export, API_KEY import removed | VERIFIED | `import html as _html` at line 8; `escaped_code` used at lines 605, 607, 612; `validate_path_within` at line 1813; nosniff at line 882; no API_KEY or verify_api_key in imports |
| `puppeteer/agent_service/services/vault_service.py` | Path traversal guard on store_artifact and delete_artifact | VERIFIED | `from ..security import validate_path_within` at line 11; guard in store_artifact at line 24; guard in delete_artifact at line 75 |
| `puppeteer/agent_service/tests/test_device_xss.py` | SEC-01 XSS test | VERIFIED | 2 tests, both PASS |
| `puppeteer/agent_service/tests/test_vault_traversal.py` | SEC-02 path traversal test | VERIFIED | 4 tests, all PASS |
| `puppeteer/agent_service/tests/test_docs_traversal.py` | SEC-03 docs path traversal test | VERIFIED | 4 tests, all PASS |
| `puppeteer/agent_service/tests/test_pii.py` | SEC-04 ReDoS timing test added | VERIFIED | 4 tests (3 original + 1 new), all PASS |
| `puppeteer/agent_service/tests/test_security.py` | SEC-05 API_KEY import removed, existing tests pass | VERIFIED | 2 tests PASS; no API_KEY import |
| `puppeteer/agent_service/tests/test_csv_nosniff.py` | SEC-06 nosniff header test | VERIFIED | 2 tests, both PASS |
| `puppeteer/compose.server.yaml` | API_KEY line removed | VERIFIED | grep for API_KEY returns no output |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| main.py device_approve_page | html.escape() | `escaped_code = _html.escape(user_code or "")` | WIRED | Line 581; all 3 injection points use escaped_code (lines 605, 607, 612) |
| vault_service.py delete_artifact | security.validate_path_within | `from ..security import validate_path_within` | WIRED | Import at line 11; called at lines 24 and 75 |
| main.py get_doc_content | security.validate_path_within | `validate_path_within(Path(docs_dir), Path(docs_dir) / filename)` | WIRED | Line 1813; validate_path_within in security import tuple at main.py:47 |
| main.py export route | StreamingResponse headers | `"X-Content-Type-Options": "nosniff"` in headers dict | WIRED | Line 882 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| SEC-01 | 72-01, 72-02 | device-approve page HTML-escapes user_code | SATISFIED | html.escape() applied; 2 XSS tests PASS |
| SEC-02 | 72-01, 72-02 | vault_service path traversal guard | SATISFIED | validate_path_within in store_artifact + delete_artifact; 4 vault traversal tests PASS |
| SEC-03 | 72-01, 72-02 | docs route path traversal guard | SATISFIED | validate_path_within replaces abspath+startswith in get_doc_content; docs traversal tests PASS |
| SEC-04 | 72-01, 72-02 | mask_pii email regex bounded to prevent ReDoS | SATISFIED | Bounded EMAIL_REGEX `{1,64}`/`{1,63}` quantifiers; ReDoS timing test PASS |
| SEC-05 | 72-01, 72-02 | API_KEY crash removed, verify_api_key removed from all node routes | SATISFIED | sys.exit crash block gone; verify_api_key function gone; api_key param gone from 3 node routes; API_KEY removed from compose.server.yaml |
| SEC-06 | 72-01, 72-02 | X-Content-Type-Options: nosniff on CSV export | SATISFIED | Header present at main.py:882; nosniff tests PASS |

All 6 requirements marked complete in REQUIREMENTS.md. No orphaned requirements detected.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| None | — | — | — | — |

No TODO, FIXME, placeholder, or stub patterns found in phase 72 modified files.

### Human Verification Required

None — all security fixes are verifiable programmatically via automated tests. The 18 security tests cover the exact behaviours described in SEC-01 through SEC-06.

### Pre-existing Test Failures (Not Introduced by Phase 72)

9 tests in the full suite fail due to deprecated `task_type='python_script'` Pydantic validation in test fixture data. These failures predate phase 72 — the relevant test files (`test_job_service.py`, `test_models.py`, `test_sec01_audit.py`, `test_sec02_hmac.py`) were last modified in prior phases (confirmed via git log). They are not caused by or related to any change made in phase 72.

### Test Run Evidence

Security tests run: 18 total across 6 files — all PASS
```
test_device_xss.py: 2 passed
test_vault_traversal.py: 4 passed
test_docs_traversal.py: 4 passed (including unit test for validate_path_within)
test_pii.py: 4 passed (including ReDoS timing test)
test_security.py: 2 passed
test_csv_nosniff.py: 2 passed
```

Full suite (agent_service, excluding pre-existing broken tests/test_foundry_mirror.py collection error): 72 passed, 9 pre-existing failures, 9 skipped.

### Commits Verified

All 5 commits documented in SUMMARYs confirmed to exist in git history:
- `ed7ea20` — test(72-01): add failing RED tests for SEC-01, SEC-02, SEC-03, SEC-06
- `732329a` — test(72-01): update test_pii.py and test_security.py for SEC-04/05
- `ce1a43a` — fix(72-02): remove API_KEY crash, add validate_path_within(), fix email regex
- `de79839` — fix(72-02): SEC-01/03/05/06 — XSS escape, path guard, API_KEY cleanup, nosniff
- `5ca0756` — fix(72-02): SEC-02/05 — vault path guard, remove API_KEY from compose

---

_Verified: 2026-03-26T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
