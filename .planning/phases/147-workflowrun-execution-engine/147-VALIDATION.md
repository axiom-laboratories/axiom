---
phase: 147
slug: workflowrun-execution-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 147 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or pyproject.toml) |
| **Quick run command** | `cd puppeteer && pytest tests/test_workflow_execution.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_workflow_execution.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 147-01-01 | 01 | 1 | ENGINE-01 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_workflowsteprun_model -xq` | ❌ W0 | ⬜ pending |
| 147-01-02 | 01 | 1 | ENGINE-01 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_job_workflow_fk -xq` | ❌ W0 | ⬜ pending |
| 147-02-01 | 02 | 2 | ENGINE-02 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_start_run -xq` | ❌ W0 | ⬜ pending |
| 147-02-02 | 02 | 2 | ENGINE-03 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_advance_workflow_bfs -xq` | ❌ W0 | ⬜ pending |
| 147-02-03 | 02 | 2 | ENGINE-04 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_concurrency_guard -xq` | ❌ W0 | ⬜ pending |
| 147-03-01 | 03 | 3 | ENGINE-05 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_state_machine_completed -xq` | ❌ W0 | ⬜ pending |
| 147-03-02 | 03 | 3 | ENGINE-05 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_state_machine_partial -xq` | ❌ W0 | ⬜ pending |
| 147-03-03 | 03 | 3 | ENGINE-05 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_state_machine_failed -xq` | ❌ W0 | ⬜ pending |
| 147-04-01 | 04 | 3 | ENGINE-06 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_cancel_run -xq` | ❌ W0 | ⬜ pending |
| 147-04-02 | 04 | 3 | ENGINE-06 | unit | `cd puppeteer && pytest tests/test_workflow_execution.py::test_cascade_cancellation -xq` | ❌ W0 | ⬜ pending |
| 147-05-01 | 05 | 4 | ENGINE-07 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_api_create_run -xq` | ❌ W0 | ⬜ pending |
| 147-05-02 | 05 | 4 | ENGINE-07 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_api_cancel_run -xq` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_workflow_execution.py` — stubs for ENGINE-01..07 (BFS, concurrency, state machine, cancel, API)
- [ ] `tests/conftest.py` — shared fixtures for workflow/step/edge/run setup

*Existing pytest infrastructure covers framework — only test file stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Jobs dispatched to actual nodes execute and advance workflow | ENGINE-02, ENGINE-03 | Requires live Docker stack with enrolled nodes | Submit a 2-step linear workflow run via POST /api/workflow-runs; verify both steps dispatch and WorkflowRun reaches COMPLETED |
| Partial completion visible in run status after step failure | ENGINE-05 | Requires node that intentionally fails a job | Submit a 2-branch workflow where one branch's job always exits 1; verify WorkflowRun.status = PARTIAL |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
