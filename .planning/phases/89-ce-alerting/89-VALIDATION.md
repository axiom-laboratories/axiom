---
phase: 89
slug: ce-alerting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 89 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` or inline |
| **Quick run command** | `cd puppeteer && pytest tests/test_webhook_notification.py -v` |
| **Full suite command** | `cd puppeteer && pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_webhook_notification.py -v`
- **After every plan wave:** Run `cd puppeteer && pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 89-01-01 | 01 | 1 | ALRT-02 | unit | `pytest tests/test_webhook_notification.py::test_dispatch_sends_post` | ❌ W0 | ⬜ pending |
| 89-01-02 | 01 | 1 | ALRT-02 | unit | `pytest tests/test_webhook_notification.py::test_disabled_no_send` | ❌ W0 | ⬜ pending |
| 89-01-03 | 01 | 1 | ALRT-02 | unit | `pytest tests/test_webhook_notification.py::test_security_rejected_opt_in` | ❌ W0 | ⬜ pending |
| 89-01-04 | 01 | 1 | ALRT-02 | unit | `pytest tests/test_webhook_notification.py::test_delivery_status_written` | ❌ W0 | ⬜ pending |
| 89-01-05 | 01 | 1 | ALRT-01 | unit | `pytest tests/test_webhook_notification.py::test_config_endpoints` | ❌ W0 | ⬜ pending |
| 89-02-01 | 02 | 2 | ALRT-01 | manual | Playwright smoke: Notifications tab visible, form saves | N/A | ⬜ pending |
| 89-02-02 | 02 | 2 | ALRT-01 | manual | Playwright smoke: Send test button shows inline result | N/A | ⬜ pending |
| 89-02-03 | 02 | 2 | ALRT-03 | manual | Login as operator, verify Notifications card accessible | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_webhook_notification.py` — stubs for ALRT-01, ALRT-02, ALRT-03

*Existing test infrastructure (pytest) covers framework requirements. Only new test file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Notifications tab appears in Admin UI | ALRT-01 | Frontend rendering | Login as operator, navigate to Admin, verify Notifications tab visible |
| Send test button shows inline result | ALRT-01 | UI interaction | Enter webhook URL, click Send test, verify inline green/red feedback below button |
| Operator role can access Notifications | ALRT-03 | RBAC | Login as operator (not admin), navigate to Admin, verify card loads without 403 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
