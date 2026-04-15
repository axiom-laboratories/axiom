---
phase: 146
slug: workflow-data-model
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 146 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing in puppeteer/tests/) |
| **Config file** | puppeteer/pyproject.toml |
| **Quick run command** | `cd puppeteer && pytest tests/test_workflow.py -x -v` |
| **Full suite command** | `cd puppeteer && pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_workflow.py -x -v`
- **After every plan wave:** Run `cd puppeteer && pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 146-01-01 | 01 | 0 | WORKFLOW-01 | unit+integration | `pytest tests/test_workflow.py -x` | ❌ W0 | ⬜ pending |
| 146-01-02 | 01 | 1 | WORKFLOW-01 | unit | `pytest tests/test_workflow.py::test_create_workflow_success -x` | ❌ W0 | ⬜ pending |
| 146-01-03 | 01 | 1 | WORKFLOW-01 | unit | `pytest tests/test_workflow.py::test_create_workflow_invalid_edges -x` | ❌ W0 | ⬜ pending |
| 146-02-01 | 02 | 1 | WORKFLOW-02 | integration | `pytest tests/test_workflow.py::test_list_workflows -x` | ❌ W0 | ⬜ pending |
| 146-02-02 | 02 | 1 | WORKFLOW-03 | integration | `pytest tests/test_workflow.py::test_update_workflow -x` | ❌ W0 | ⬜ pending |
| 146-02-03 | 02 | 1 | WORKFLOW-03 | unit | `pytest tests/test_workflow.py::test_validate_cycle_detection -x` | ❌ W0 | ⬜ pending |
| 146-02-04 | 02 | 1 | WORKFLOW-03 | unit | `pytest tests/test_workflow.py::test_validate_depth_limit -x` | ❌ W0 | ⬜ pending |
| 146-02-05 | 02 | 1 | WORKFLOW-04 | integration | `pytest tests/test_workflow.py::test_delete_workflow_with_active_runs -x` | ❌ W0 | ⬜ pending |
| 146-02-06 | 02 | 2 | WORKFLOW-05 | integration | `pytest tests/test_workflow.py::test_fork_workflow -x` | ❌ W0 | ⬜ pending |
| 146-02-07 | 02 | 2 | WORKFLOW-05 | unit | `pytest tests/test_workflow.py::test_fork_pauses_source -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_workflow.py` — test stubs covering all WORKFLOW-01..05 test cases
- [ ] `puppeteer/tests/conftest.py` — add `workflow_fixture` (pre-created workflow with valid steps/edges) and async DB session fixture for transaction rollback
- [ ] `networkx` added to `puppeteer/requirements.txt`
- [ ] `puppeteer/migration_v53.sql` — new tables: workflows, workflow_steps, workflow_edges, workflow_parameters

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Structured error body fields in API responses | WORKFLOW-03 | Response body shape validation beyond status code | Submit cyclic graph, verify `cycle_path` field present in 422 response body |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
