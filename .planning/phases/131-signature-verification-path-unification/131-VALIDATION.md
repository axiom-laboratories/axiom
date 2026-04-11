---
phase: 131
slug: signature-verification-path-unification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 131 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_signature_unification.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_signature_unification.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 131-01-01 | 01 | 0 | countersign-stub | unit stub | `cd puppeteer && pytest tests/test_signature_unification.py -x -q` | ❌ W0 | ⬜ pending |
| 131-01-02 | 01 | 1 | countersign-impl | unit | `cd puppeteer && pytest tests/test_signature_unification.py::test_countersign_returns_base64 -x -q` | ❌ W0 | ⬜ pending |
| 131-01-03 | 01 | 1 | missing-key-hard-fail | unit | `cd puppeteer && pytest tests/test_signature_unification.py::test_countersign_missing_key_raises -x -q` | ❌ W0 | ⬜ pending |
| 131-01-04 | 01 | 1 | crlf-normalization | unit | `cd puppeteer && pytest tests/test_signature_unification.py::test_countersign_normalizes_crlf -x -q` | ❌ W0 | ⬜ pending |
| 131-02-01 | 02 | 2 | create-job-uses-service | integration | `cd puppeteer && pytest tests/test_signature_unification.py::test_create_job_calls_countersign -x -q` | ❌ W0 | ⬜ pending |
| 131-02-02 | 02 | 2 | create-job-500-on-missing-key | integration | `cd puppeteer && pytest tests/test_signature_unification.py::test_create_job_500_no_key -x -q` | ❌ W0 | ⬜ pending |
| 131-03-01 | 03 | 2 | fire-job-countersigns | integration | `cd puppeteer && pytest tests/test_signature_unification.py::test_fire_job_countersigns -x -q` | ❌ W0 | ⬜ pending |
| 131-03-02 | 03 | 2 | fire-job-hmac-stamped | integration | `cd puppeteer && pytest tests/test_signature_unification.py::test_fire_job_hmac_stamped -x -q` | ❌ W0 | ⬜ pending |
| 131-03-03 | 03 | 2 | fire-job-signing-error | integration | `cd puppeteer && pytest tests/test_signature_unification.py::test_fire_job_signing_error_status -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_signature_unification.py` — stubs for all 9 test cases above
- [ ] Stubs use `pytest.mark.skip` or `assert False, "not implemented"` initially

*Existing `puppeteer/pytest.ini` and conftest.py infrastructure covers all phase requirements — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Signed scheduled job dispatched to live node verifies correctly | SEC-02 | Requires running Docker stack + enrolled node + real signing key | 1. Start stack; 2. Enroll node; 3. Trigger scheduled job; 4. Check node accepts job and `work/pull` signature verification passes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
