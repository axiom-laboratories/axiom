---
phase: 17
slug: backend-oauth-device-flow-and-job-staging
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none — run from `puppeteer/` directory |
| **Quick run command** | `cd puppeteer && pytest tests/test_device_flow.py tests/test_job_staging.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_device_flow.py tests/test_job_staging.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 0 | STAGE-01 | unit | `pytest tests/test_job_staging.py::test_scheduled_job_status_field -x` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 0 | AUTH-CLI-01 | unit | `pytest tests/test_device_flow.py::test_device_authorization_response -x` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 0 | AUTH-CLI-01 | unit | `pytest tests/test_device_flow.py::test_user_code_format -x` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | AUTH-CLI-01 | unit | `pytest tests/test_device_flow.py::test_device_authorization_response -x` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 1 | AUTH-CLI-02 | unit | `pytest tests/test_device_flow.py::test_token_exchange_pending -x` | ❌ W0 | ⬜ pending |
| 17-02-03 | 02 | 1 | AUTH-CLI-02 | unit | `pytest tests/test_device_flow.py::test_token_exchange_denied -x` | ❌ W0 | ⬜ pending |
| 17-02-04 | 02 | 1 | AUTH-CLI-02 | unit | `pytest tests/test_device_flow.py::test_token_exchange_expired -x` | ❌ W0 | ⬜ pending |
| 17-02-05 | 02 | 1 | AUTH-CLI-02 | unit | `pytest tests/test_device_flow.py::test_token_exchange_approved -x` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 1 | STAGE-02 | unit | `pytest tests/test_job_staging.py::test_push_creates_draft -x` | ❌ W0 | ⬜ pending |
| 17-03-02 | 03 | 1 | STAGE-02 | unit | `pytest tests/test_job_staging.py::test_push_duplicate_name_conflict -x` | ❌ W0 | ⬜ pending |
| 17-03-03 | 03 | 1 | STAGE-02 | unit | `pytest tests/test_job_staging.py::test_push_revoked_job_blocked -x` | ❌ W0 | ⬜ pending |
| 17-03-04 | 03 | 1 | STAGE-03 | unit | `pytest tests/test_job_staging.py::test_push_requires_auth -x` | ❌ W0 | ⬜ pending |
| 17-03-05 | 03 | 1 | STAGE-03 | unit | `pytest tests/test_job_staging.py::test_push_invalid_signature -x` | ❌ W0 | ⬜ pending |
| 17-03-06 | 03 | 1 | STAGE-04 | unit | `pytest tests/test_job_staging.py::test_push_records_pushed_by -x` | ❌ W0 | ⬜ pending |
| 17-04-01 | 04 | 1 | GOV-CLI-01 | unit | `pytest tests/test_job_staging.py::test_scheduler_skips_revoked -x` | ❌ W0 | ⬜ pending |
| 17-04-02 | 04 | 1 | GOV-CLI-01 | unit | `pytest tests/test_job_staging.py::test_scheduler_skips_deprecated -x` | ❌ W0 | ⬜ pending |
| 17-04-03 | 04 | 1 | GOV-CLI-01 | unit | `pytest tests/test_job_staging.py::test_scheduler_skips_draft -x` | ❌ W0 | ⬜ pending |
| 17-04-04 | 04 | 1 | GOV-CLI-01 | unit | `pytest tests/test_job_staging.py::test_revoke_requires_admin -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_device_flow.py` — stubs for AUTH-CLI-01, AUTH-CLI-02
- [ ] `puppeteer/tests/test_job_staging.py` — stubs for STAGE-01, STAGE-02, STAGE-03, STAGE-04, GOV-CLI-01

*Use the existing `unittest.mock.patch` / `MagicMock` pattern from `test_tools.py` and `test_compatibility_engine.py`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser approval page displays user code and has Approve/Deny form | AUTH-CLI-01 | UI rendering requires browser | Navigate to `/auth/device/activate?user_code=XXXX-XXXX`, verify code shown and buttons present |
| Approval page reads JWT from localStorage and redirects to /login when absent | AUTH-CLI-01 | JS DOM interaction | Open approval page in private window, verify redirect |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
