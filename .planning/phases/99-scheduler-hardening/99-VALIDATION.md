---
phase: 99
slug: scheduler-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 99 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or `pyproject.toml`) |
| **Quick run command** | `cd puppeteer && pytest tests/test_scheduler_phase99.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_scheduler_phase99.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 99-01-01 | 01 | 0 | SCHED-01/02/03 | infra | `cd puppeteer && pytest tests/test_scheduler_phase99.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 99-01-02 | 01 | 1 | SCHED-01 | unit | `cd puppeteer && pytest tests/test_scheduler_phase99.py::test_sync_scheduler_does_not_call_remove_all_jobs -xvs` | ❌ W0 | ⬜ pending |
| 99-01-03 | 01 | 1 | SCHED-01 | unit | `cd puppeteer && pytest tests/test_scheduler_phase99.py::test_sync_scheduler_uses_replace_existing -xvs` | ❌ W0 | ⬜ pending |
| 99-01-04 | 01 | 1 | SCHED-02 | functional | `cd puppeteer && pytest tests/test_scheduler_phase99.py::test_internal_jobs_survive_sync -xvs` | ❌ W0 | ⬜ pending |
| 99-01-05 | 01 | 1 | SCHED-01 | functional | `cd puppeteer && pytest tests/test_scheduler_phase99.py::test_sync_adds_new_active_job -xvs` | ❌ W0 | ⬜ pending |
| 99-01-06 | 01 | 1 | SCHED-01 | functional | `cd puppeteer && pytest tests/test_scheduler_phase99.py::test_sync_removes_inactive_job -xvs` | ❌ W0 | ⬜ pending |
| 99-01-07 | 01 | 1 | SCHED-03 | unit | `cd puppeteer && pytest tests/test_scheduler_phase99.py::test_cron_callback_is_sync_wrapper -xvs` | ❌ W0 | ⬜ pending |
| 99-01-08 | 01 | 1 | SCHED-03 | timing | `cd puppeteer && pytest tests/test_scheduler_phase99.py::test_cron_callback_returns_immediately -xvs` | ❌ W0 | ⬜ pending |
| 99-01-09 | 01 | 1 | SCHED-03 | unit | `cd puppeteer && pytest tests/test_scheduler_phase99.py::test_failed_fire_log_counted_in_health -xvs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_scheduler_phase99.py` — test stubs for SCHED-01, SCHED-02, SCHED-03

*Existing test infrastructure (conftest, fixtures, IS_POSTGRES pattern) covers all phase requirements — no new framework installs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Internal jobs still fire after a CRUD operation in live Docker stack | SCHED-02 | Requires running scheduler + real timing | Create a job def via API, confirm `__prune_node_stats__` still in APScheduler job list via logs |
| No event loop stall under cron burst (heartbeats keep flowing) | SCHED-03 | Requires real load + timing measurement | Fire 5 cron jobs simultaneously, verify `/heartbeat` responds < 200ms during burst |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
