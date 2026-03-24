---
phase: 47
slug: ce-runtime-expansion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` (or inferred from project root) |
| **Quick run command** | `cd puppeteer && pytest tests/test_runtime_expansion.py -x` |
| **Full suite command** | `cd puppeteer && pytest && cd dashboard && npm run test` |
| **Estimated runtime** | ~30 seconds (backend unit), ~15 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_runtime_expansion.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 47-01-01 | 01 | 0 | RT-01,RT-02,RT-03,RT-04,RT-05,RT-07 | unit stubs | `cd puppeteer && pytest tests/test_runtime_expansion.py -x` | ❌ W0 | ⬜ pending |
| 47-01-02 | 01 | 1 | RT-03 | unit | `cd puppeteer && pytest tests/test_runtime_expansion.py::test_containerfile_has_powershell -x` | ❌ W0 | ⬜ pending |
| 47-01-03 | 01 | 1 | RT-01,RT-02 | unit | `cd puppeteer && pytest tests/test_runtime_expansion.py::test_node_script_execution -x` | ❌ W0 | ⬜ pending |
| 47-02-01 | 02 | 2 | RT-04 | unit | `cd puppeteer && pytest tests/test_runtime_expansion.py::test_invalid_runtime_rejected -x` | ❌ W0 | ⬜ pending |
| 47-02-02 | 02 | 2 | RT-05 | unit | `cd puppeteer && pytest tests/test_runtime_expansion.py::test_display_type_computed_serverside -x` | ❌ W0 | ⬜ pending |
| 47-02-03 | 02 | 2 | RT-07 | unit | `cd puppeteer && pytest tests/test_runtime_expansion.py::test_scheduled_job_runtime_field -x` | ❌ W0 | ⬜ pending |
| 47-03-01 | 03 | 3 | RT-05 | unit | `cd puppeteer/dashboard && npm run test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_runtime_expansion.py` — stubs covering RT-01 through RT-07 (source inspection approach, same as `test_job_staging.py`)
- [ ] No framework install needed — pytest already present in the project

*Pattern: use `inspect.getsource()` for validating models, DB schema, and service logic without requiring a live DB.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bash job executes on a real node and returns output | RT-01 | Requires running Docker stack + enrolled node | Submit `task_type: script, runtime: bash` via Jobs UI; verify output in Jobs list |
| PowerShell job executes on a real node and returns output | RT-02 | Requires running Docker stack + enrolled node with pwsh installed | Submit `task_type: script, runtime: powershell` via Jobs UI; verify output in Jobs list |
| Runtime dropdown appears in submission form when task_type is `script` | RT-05 | UI interaction | Open Jobs view, select `script` task type, verify runtime dropdown appears |
| Scheduled bash/ps job fires on cron schedule | RT-07 | Requires live APScheduler + enrolled node | Create job definition with runtime: bash, short cron; verify execution in jobs list |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
