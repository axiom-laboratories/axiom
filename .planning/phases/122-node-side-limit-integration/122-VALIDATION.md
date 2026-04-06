---
phase: 122
slug: node-side-limit-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 122 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (7.0+) with asyncio_mode=auto |
| **Config file** | `pyproject.toml` (existing: `testpaths=["puppeteer/agent_service/tests"], asyncio_mode="auto"`) |
| **Quick run command** | `pytest puppets/environment_service/tests/test_node.py -xvs` |
| **Full suite command** | `pytest puppets/environment_service/tests/ -xvs` |
| **Estimated runtime** | ~30 seconds (unit), ~2 min (full + integration) |

---

## Sampling Rate

- **After every task commit:** Run `pytest puppets/environment_service/tests/test_node.py -x`
- **After every plan wave:** Run `pytest puppets/environment_service/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 122-01-01 | 01 | 1 | ENFC-03 (part 1) | unit | `pytest puppets/environment_service/tests/test_node.py::test_parse_bytes_invalid -xvs` | ❌ W0 | ⬜ pending |
| 122-01-02 | 01 | 1 | ENFC-03 (part 2) | unit | `pytest puppets/environment_service/tests/test_node.py::test_parse_cpu_invalid -xvs` | ❌ W0 | ⬜ pending |
| 122-01-03 | 01 | 1 | Error handling | unit+integration | `pytest puppets/environment_service/tests/test_node.py::test_execute_task_invalid_memory_format -xvs` | ❌ W0 | ⬜ pending |
| 122-01-04 | 01 | 1 | Logging | unit | `pytest puppets/environment_service/tests/test_node.py::test_execute_task_logs_limits -xvs` | ❌ W0 | ⬜ pending |
| 122-01-05 | 01 | 1 | ENFC-03 (part 3) | integration | `pytest puppets/environment_service/tests/test_runtime.py::test_run_with_memory_limit -xvs` | ✅ | ⬜ pending |
| 122-01-06 | 01 | 1 | ENFC-03 (part 4) | integration | `pytest puppets/environment_service/tests/test_runtime.py::test_run_with_cpu_limit -xvs` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppets/environment_service/tests/test_node.py` — expand with test_parse_bytes_invalid(), test_parse_cpu_valid/invalid(), test_execute_task_invalid_memory_format(), test_execute_task_invalid_cpu_format()
- [ ] `puppets/environment_service/tests/test_runtime.py` — enhance existing tests to verify `--memory` and `--cpus` flags actually passed to subprocess
- [ ] `puppets/environment_service/tests/conftest.py` — shared fixtures for mock PuppetNode and work dicts with limit fields

*Existing infrastructure covers framework install — pytest already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end limit flow via Docker stack | ENFC-03 full | Requires running orchestrator + node containers | Submit job with limits via API, verify container started with correct `--memory`/`--cpus` flags |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
