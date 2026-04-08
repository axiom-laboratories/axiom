---
phase: 125
slug: stress-test-corpus
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 125 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing backend test infrastructure) |
| **Config file** | `puppeteer/pytest.ini` or none — Wave 0 installs |
| **Quick run command** | `pytest puppeteer/tests/test_stress_integration.py -x -v` |
| **Full suite command** | `pytest puppeteer/tests/ -x --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest puppeteer/tests/test_stress_integration.py -x -v`
- **After every plan wave:** Run `pytest puppeteer/tests/test_stress_integration.py puppeteer/tests/test_job_limits.py -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 125-01-01 | 01 | 1 | STRS-01 | integration | `pytest tests/test_stress_integration.py::test_cpu_burn_all_languages -xvs` | ❌ W0 | ⬜ pending |
| 125-01-02 | 01 | 1 | STRS-02 | integration | `pytest tests/test_stress_integration.py::test_memory_oom_exits_137 -xvs` | ❌ W0 | ⬜ pending |
| 125-01-03 | 01 | 1 | STRS-03 | integration | `pytest tests/test_stress_integration.py::test_noisy_monitor_drift -xvs` | ❌ W0 | ⬜ pending |
| 125-02-01 | 02 | 2 | STRS-04 | unit | `pytest tests/test_stress_integration.py::test_preflight_cgroup_detection -xvs` | ❌ W0 | ⬜ pending |
| 125-02-02 | 02 | 2 | STRS-05 | integration | `pytest tests/test_stress_integration.py::test_orchestrator_all_scenarios -xvs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_stress_integration.py` — stubs for STRS-01 through STRS-05
- [ ] Fixtures for mock node registration, signed job dispatch, result parsing
- [ ] Integration test for Bash and PowerShell versions (may skip if no shell in CI)
- [ ] Test for preflight cgroup detection (check /sys/fs/cgroup availability)
- [ ] Framework install: None — pytest already in `puppeteer/requirements.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Concurrent isolation on live node | STRS-05 scenario 3 | Requires real Docker host with cgroup limits | Deploy stress scripts to test node, run orchestrator scenario 3, verify monitor drift < 1.1s |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
