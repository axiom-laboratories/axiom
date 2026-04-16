---
phase: 148
slug: gate-node-types
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 148 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_workflow.py tests/test_gate_evaluation.py -xvs` |
| **Full suite command** | `cd puppeteer && pytest tests/test_workflow*.py tests/test_gate_evaluation.py -xvs` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_workflow.py tests/test_gate_evaluation.py -xvs`
- **After every plan wave:** Run `cd puppeteer && pytest tests/test_workflow*.py tests/test_gate_evaluation.py -xvs`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 148-W0-01 | 01 | 0 | GATE-01/02 | unit | `cd puppeteer && pytest tests/test_gate_evaluation.py -xvs` | ❌ W0 | ⬜ pending |
| 148-W0-02 | 01 | 0 | GATE-03/04/05/06 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py -xvs` | ✅ (stub) | ⬜ pending |
| 148-W0-03 | 01 | 0 | migration | manual | verify `ALTER TABLE` SQL in migration_v55.sql | ❌ W0 | ⬜ pending |
| 148-01-01 | 01 | 1 | schema | unit | `cd puppeteer && pytest tests/test_workflow.py -xvs` | ✅ | ⬜ pending |
| 148-01-02 | 01 | 1 | GATE-01 | unit | `cd puppeteer && pytest tests/test_gate_evaluation.py::test_if_gate_operators -xvs` | ❌ W0 | ⬜ pending |
| 148-01-03 | 01 | 1 | GATE-02 | unit | `cd puppeteer && pytest tests/test_gate_evaluation.py::test_if_gate_no_match_cascades -xvs` | ❌ W0 | ⬜ pending |
| 148-02-01 | 02 | 2 | GATE-03 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_and_join_synchronization -xvs` | ✅ | ⬜ pending |
| 148-02-02 | 02 | 2 | GATE-04 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_or_gate_branch_skip -xvs` | ❌ W0 | ⬜ pending |
| 148-02-03 | 02 | 2 | GATE-05 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_parallel_fan_out -xvs` | ❌ W0 | ⬜ pending |
| 148-03-01 | 03 | 3 | GATE-06 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_signal_wait_wakeup -xvs` | ❌ W0 | ⬜ pending |
| 148-03-02 | 03 | 3 | GATE-06 | integration | `cd puppeteer && pytest tests/test_workflow_execution.py::test_signal_wakes_blocked_run -xvs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_gate_evaluation.py` — unit tests for GateEvaluationService (resolve_field, evaluate_condition, evaluate_if_gate) — GATE-01/02
- [ ] `tests/test_workflow_execution.py` — extended with OR_GATE, PARALLEL, SIGNAL_WAIT integration test stubs — GATE-04/05/06
- [ ] `tests/conftest.py` — helper fixtures to create gate node workflows (templates for IF, AND, OR, PARALLEL, SIGNAL_WAIT)
- [ ] `migration_v55.sql` — `ALTER TABLE workflow_steps ALTER COLUMN scheduled_job_id DROP NOT NULL` + `ALTER TABLE workflow_step_runs ADD COLUMN result_json TEXT`

*All four are required before Wave 1 implementation tasks can verify correctly.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gate node E2E against Docker stack | GATE-01..06 | Requires running node + agent + job execution pipeline | Submit workflow with IF gate via API; observe WorkflowStepRun status transitions in DB; verify correct branch taken |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
