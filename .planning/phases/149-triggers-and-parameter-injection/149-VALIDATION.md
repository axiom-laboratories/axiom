---
phase: 149
slug: triggers-and-parameter-injection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 149 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_triggers.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_triggers.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 149-01-01 | 01 | 1 | Cron trigger | unit | `cd puppeteer && pytest tests/test_triggers.py::test_cron_trigger -x -q` | ❌ W0 | ⬜ pending |
| 149-01-02 | 01 | 1 | Webhook HMAC | unit | `cd puppeteer && pytest tests/test_triggers.py::test_webhook_hmac -x -q` | ❌ W0 | ⬜ pending |
| 149-01-03 | 01 | 1 | Manual trigger | unit | `cd puppeteer && pytest tests/test_triggers.py::test_manual_trigger -x -q` | ❌ W0 | ⬜ pending |
| 149-02-01 | 02 | 1 | Parameter injection | unit | `cd puppeteer && pytest tests/test_triggers.py::test_param_injection -x -q` | ❌ W0 | ⬜ pending |
| 149-02-02 | 02 | 1 | Parameter merging | unit | `cd puppeteer && pytest tests/test_triggers.py::test_param_merge -x -q` | ❌ W0 | ⬜ pending |
| 149-03-01 | 03 | 2 | Trigger API endpoints | integration | `cd puppeteer && pytest tests/test_triggers.py::test_trigger_endpoints -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_triggers.py` — stubs for all trigger and parameter injection tests
- [ ] `tests/conftest.py` — shared fixtures (already exists, extend as needed)

*Existing infrastructure covers core patterns; new test file needed for trigger-specific tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Webhook secret shown once at creation | Security requirement | Plaintext only returned once in API response | Create webhook via API, confirm secret in response; re-fetch to confirm secret not returned again |
| Cron job fires at scheduled time | Scheduler integration | Requires real time passage | Set a 1-minute cron, wait, confirm WorkflowRun created |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
