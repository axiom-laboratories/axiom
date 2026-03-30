---
phase: 97
slug: db-pool-tuning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 97 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or implicit discovery) |
| **Quick run command** | `cd puppeteer && pytest tests/test_pool_phase97.py -v` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~5 seconds (unit tests, no DB connection needed) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_pool_phase97.py -v`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 97-01-01 | 01 | 1 | POOL-01, POOL-02, POOL-04 | unit | `cd puppeteer && pytest tests/test_pool_phase97.py::test_pool_kwargs_structure tests/test_pool_phase97.py::test_pool_pre_ping_included tests/test_pool_phase97.py::test_no_pool_kwargs_for_sqlite -v` | ❌ W0 | ⬜ pending |
| 97-01-02 | 01 | 1 | POOL-03 | unit | `cd puppeteer && pytest tests/test_pool_phase97.py::test_asyncpg_pool_size_env_var tests/test_pool_phase97.py::test_env_example_contains_pool_size tests/test_pool_phase97.py::test_compose_yaml_contains_pool_size -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_pool_phase97.py` — stubs for POOL-01, POOL-02, POOL-03, POOL-04

*Existing pytest infrastructure covers all other needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pool exhaustion absent under 20-node load | POOL-01 | Requires 20 enrolled nodes + Postgres — impractical in unit test suite | Start stack with Postgres URL, enroll 20 nodes, monitor `/work/pull` for pool timeout errors over 60s polling interval |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
