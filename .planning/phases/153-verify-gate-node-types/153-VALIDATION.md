---
phase: 153
slug: verify-gate-node-types
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-16
---

# Phase 153 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_gate_evaluation.py tests/test_workflow_execution.py -xvs` |
| **Full suite command** | `cd puppeteer && pytest tests/test_workflow*.py -xvs` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_gate_evaluation.py tests/test_workflow_execution.py -xvs`
- **After every plan wave:** Run `cd puppeteer && pytest tests/test_workflow*.py -xvs`
- **Before `/gsd:verify-work`:** Full suite must be green + VERIFICATION.md created
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 153-01-01 | 01 | 1 | GATE-01 | unit | `cd puppeteer && pytest tests/test_gate_evaluation.py::TestEvaluateCondition -xvs` | ✅ | ⬜ pending |
| 153-01-02 | 01 | 1 | GATE-02 | unit | `cd puppeteer && pytest tests/test_gate_evaluation.py::TestEvaluateIfGate -xvs` | ✅ | ⬜ pending |
| 153-01-03 | 01 | 1 | GATE-03 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_concurrent_dispatch_idempotent -xvs` | ✅ | ⬜ pending |
| 153-01-04 | 01 | 1 | GATE-04 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py -k "or_gate" -xvs` | ✅ | ⬜ pending |
| 153-01-05 | 01 | 1 | GATE-05 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_dispatch_bfs_order -xvs` | ✅ | ⬜ pending |
| 153-01-06 | 01 | 1 | GATE-06 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_signal_wait_wakeup -xvs` | ✅ | ⬜ pending |
| 153-02-01 | 02 | 2 | ENGINE-01..07 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py -xvs` | ✅ | ⬜ pending |
| 153-02-02 | 02 | 2 | TRIGGER-01/03/05 | integration | `cd puppeteer && pytest tests/test_workflow*.py -xvs` | ✅ | ⬜ pending |
| 153-02-03 | 02 | 2 | PARAMS-01 | unit | `cd puppeteer && pytest tests/test_workflow_params.py -xvs` | ✅ | ⬜ pending |
| 153-02-04 | 02 | 2 | UI-01..04 | Playwright | `cd ~/Development/mop_validation && python scripts/test_playwright.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 setup needed.

- ✅ `tests/test_gate_evaluation.py` — 22 unit tests, all passing
- ✅ `tests/test_workflow_execution.py` — 11 integration tests, all passing
- ✅ `tests/conftest.py` — fixtures for workflow creation present
- ✅ Database schema — WorkflowStep.node_type, config_json, result_json all present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| IF_GATE evaluates result.json from predecessor job and routes branch correctly | GATE-02 | Requires live Docker stack with job execution + file output | Deploy stack, run workflow with IF_GATE, inspect WorkflowStepRun status and selected branch |
| SIGNAL_WAIT blocks until signal posted then unblocks downstream | GATE-06 | Requires live signal posting via API | Deploy stack, trigger workflow, verify WAITING status, POST signal, verify downstream step transitions to RUNNING |
| OR_GATE skips non-triggering branches | GATE-04 | Integration test verifies dispatch but branch skip marking needs Docker trace | Run workflow, confirm non-triggered branch steps end in SKIPPED status |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
