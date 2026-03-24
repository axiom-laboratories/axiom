---
phase: 56
slug: integration-bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + Playwright Python (E2E) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` |
| **Full suite command** | `cd puppeteer && pytest && python3 mop_validation/scripts/test_phase56_integration.py` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest && cd dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green + `python3 mop_validation/scripts/test_phase56_integration.py` all-pass
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 56-01-01 | 01 | 0 | JOB-01, RT-01, RT-02, VIS-02, SRCH-10, JOB-04, JOB-05 | E2E Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ W0 | ⬜ pending |
| 56-01-02 | 01 | 1 | JOB-01, RT-01, RT-02 | E2E Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ W0 | ⬜ pending |
| 56-01-03 | 01 | 1 | VIS-02 | E2E Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ W0 | ⬜ pending |
| 56-01-04 | 01 | 1 | SRCH-10 | E2E Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ W0 | ⬜ pending |
| 56-01-05 | 01 | 1 | JOB-04, JOB-05 | unit + E2E | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` | ✅ existing | ⬜ pending |
| 56-01-06 | 01 | 2 | All | manual | Human checkpoint sign-off | N/A | ⬜ pending |
| 56-01-07 | 01 | 2 | JOB-01, RT-01, RT-02, VIS-02, SRCH-10, JOB-04, JOB-05 | none | REQUIREMENTS.md update (post-checkpoint) | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/test_phase56_integration.py` — E2E Playwright test covering all 4 INT scenarios (JOB-01, RT-01, RT-02, VIS-02, SRCH-10, JOB-04, JOB-05)
- [ ] Live Docker stack running (`puppeteer/compose.server.yaml up`) with enrolled node and signing key in `secrets/`

*Wave 0 must create the test file before Wave 1 E2E verification tasks can pass.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Guided form execution visible in browser | JOB-01 | Browser-level confirmation that form submits and job appears in Jobs list | Open dashboard, submit guided form with Python script, watch job reach COMPLETED |
| Queue live data renders correctly | VIS-02 | Visual confirmation no 404 errors, data appears | Open Queue view, confirm PENDING/RUNNING jobs show without errors |
| CSV export download in browser | SRCH-10 | Actual file download requires browser interaction | Open job detail drawer, click CSV export, confirm file downloads with content |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
