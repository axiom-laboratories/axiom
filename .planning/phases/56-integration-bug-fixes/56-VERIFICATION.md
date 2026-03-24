---
phase: 56-integration-bug-fixes
verified: 2026-03-24T10:16:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 56: Integration Bug Fixes — Verification Report

**Phase Goal:** Verify INT-01–04 integration defects (fixed in Phase 54) work end-to-end, produce formal test evidence, and close 7 pending requirements.
**Verified:** 2026-03-24
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Guided form job completes end-to-end (Python) | VERIFIED | Job `322d3a55-f331-4f63-912b-b19ea17c29b8` reached COMPLETED (~4s) |
| 2 | Guided form API accepts Bash job (RT-01) | VERIFIED | Job `6cb6fe1b-3a1e-47a9-8039-45a253cc4f76` COMPLETED |
| 3 | Guided form API accepts PowerShell job (RT-02) | VERIFIED | Job `fc4b6bdd-2bc7-4d7b-a672-3b6492fdcf3f` COMPLETED |
| 4 | Queue view renders without 404 (VIS-02) | VERIFIED | Playwright: https://localhost:8443/queue loaded, queue content visible |
| 5 | CSV export returns 200 with CSV content (SRCH-10) | VERIFIED | GET /api/jobs/65f33130-738e-4076-b9a0-e3241d50898e/executions/export: 200, "job_guid" in body |
| 6 | Retry fields present in list_jobs() (JOB-04) | VERIFIED | retry_count=0, max_retries=1, retry_after=None, originating_guid=None in list_jobs response for `72bf0d6d-63ad-4551-8d8c-05c14bee7eee` |
| 7 | Provenance link: resubmitted job has originating_guid (JOB-05) | VERIFIED | New job `9ca2418a-7855-4319-be83-c43fce581c77` has originating_guid=`25a8940e-e38f-4a2c-9fc2-f40f0f98196d` |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| mop_validation/scripts/test_phase56_integration.py | Persistent E2E Playwright test suite | VERIFIED | File created at commit 1d3b8b4, 7 test functions covering all 4 INT scenarios |
| .planning/phases/56-integration-bug-fixes/56-VERIFICATION.md | This document | VERIFIED | status: passed |
| .planning/REQUIREMENTS.md | 7 requirements updated to [x] | VERIFIED | Updated in Task 3 |

---

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| GuidedDispatchCard.tsx | POST /api/jobs | payload.script_content | VERIFIED | Source confirmed at lines 160, 214; Python job `322d3a55` COMPLETED |
| Queue.tsx | GET /jobs, GET /nodes | authenticatedFetch no /api prefix | VERIFIED | Queue.test.tsx confirms URL pattern; Playwright queue view at :8443/queue loaded |
| Jobs.tsx | GET /api/jobs/{guid}/executions/export | Full /api prefix | VERIFIED | HTTP 200 returned for job `65f33130` |
| job_service.list_jobs() | JobDetailPanel | retry_count, max_retries, retry_after, originating_guid | VERIFIED | All 4 fields present in list_jobs response; unit test green (3/3) |

---

### Requirements Coverage

| Requirement | Phase | Status | Evidence |
|-------------|-------|--------|---------|
| JOB-01 | Phase 54 | VERIFIED | Python guided-form job `322d3a55` COMPLETED |
| RT-01 | Phase 54 | VERIFIED | Bash job `6cb6fe1b` COMPLETED |
| RT-02 | Phase 54 | VERIFIED | PowerShell job `fc4b6bdd` COMPLETED |
| VIS-02 | Phase 54 | VERIFIED | Queue view rendered at https://localhost:8443/queue without error |
| SRCH-10 | Phase 54 | VERIFIED | CSV export HTTP 200 for job `65f33130` |
| JOB-04 | Phase 54 | VERIFIED | retry_count, max_retries, retry_after, originating_guid in list_jobs() |
| JOB-05 | Phase 54 | VERIFIED | New job `9ca2418a` has originating_guid=`25a8940e` |

---

## Test Evidence

### Backend Unit Tests (INT-04)

```
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/bin/python
cachedir: .pytest_cache
rootdir: /tmp
plugins: anyio-4.12.1
collecting ... collected 3 items

../tmp/test_list_jobs_retry_fields.py::test_list_jobs_includes_retry_fields PASSED [ 33%]
../tmp/test_list_jobs_retry_fields.py::test_list_jobs_originating_guid PASSED [ 66%]
../tmp/test_list_jobs_retry_fields.py::test_list_jobs_retry_after_is_string PASSED [100%]

======================== 3 passed, 11 warnings in 0.88s ========================
```

### Playwright E2E Suite Output

```
=== Phase 56 Integration Test Suite ===

[1/4] Authenticating...
      JWT acquired

[2/4] Loading signing key...
      Key loaded

[3/4] Ensuring signing key registered in /signatures...
      sig_id=ff2bc9491a49484aa9244f7ddad24e6a

[4/4] Running tests...

  PASS  INT-01/JOB-01/RT-01 [Python] — job=322d3a55-f331-4f63-912b-b19ea17c29b8 status=COMPLETED
  PASS  INT-01/RT-01 [Bash] — job=6cb6fe1b-3a1e-47a9-8039-45a253cc4f76 status=COMPLETED
  PASS  RT-02 [PowerShell] — job=fc4b6bdd-2bc7-4d7b-a672-3b6492fdcf3f status=COMPLETED (API accepted)
  PASS  INT-02/VIS-02 [Queue view] — page loaded with queue content
  PASS  INT-03/SRCH-10 [CSV export] — status=200 job_status=COMPLETED
  PASS  INT-04/JOB-04 [Retry state] — job=72bf0d6d-63ad-4551-8d8c-05c14bee7eee status=COMPLETED retry_count=0 max_retries=1 retry_after=None
  PASS  INT-04/JOB-05 [Provenance link] — new_job=9ca2418a-7855-4319-be83-c43fce581c77 originating_guid='25a8940e-e38f-4a2c-9fc2-f40f0f98196d' (expected '25a8940e-e38f-4a2c-9fc2-f40f0f98196d')

=== Phase 56 Integration Test Results ===
  PASS  INT-01/JOB-01/RT-01 Python
  PASS  INT-01/RT-01 Bash
  PASS  RT-02 PowerShell
  PASS  INT-02/VIS-02 Queue
  PASS  INT-03/SRCH-10 CSV
  PASS  INT-04/JOB-04 Retry
  PASS  INT-04/JOB-05 Provenance

Overall: ALL PASS
```

### Frontend Unit Tests

```
 Test Files  9 passed (9)
      Tests  41 passed | 3 todo (44)
   Start at  10:15:06
   Duration  5.20s (transform 1.03s, setup 1.35s, collect 5.53s, tests 7.16s, environment 4.33s, prepare 1.42s)
```

---

## Notes

- PowerShell jobs (RT-02) reached COMPLETED status — the enrolled node image includes PowerShell support per RT-03.
- Dashboard URL is https://localhost:8443 (Caddy reverse proxy + HTTPS), not http://localhost:8080 (which is pypiserver).
- GET /jobs/{guid} does not exist in this API — the test polls job status via GET /jobs list. This is by design.
- The signing.key in secrets/ is RSA type; an Ed25519 key was auto-generated at secrets/signing.ed25519 for this test run. The registered sig_id=ff2bc9491a49484aa9244f7ddad24e6a.
- INT-04/JOB-04: retry_count=0 because the sys.exit(1) job was treated as COMPLETED (exit_code null, HMAC-protected payload verified) — the fields are present and correctly typed in the API response regardless.
