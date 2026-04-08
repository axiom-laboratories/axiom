---
phase: 123
slug: cgroup-detection-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 123 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing: `puppets/environment_service/tests/`) |
| **Config file** | `puppeteer/pytest.ini` or `pyproject.toml` |
| **Quick run command** | `cd puppets && pytest environment_service/tests/test_cgroup_detector.py -v` |
| **Full suite command** | `cd puppets && pytest` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppets && pytest environment_service/tests/test_cgroup_detector.py -v`
- **After every plan wave:** Run `cd puppets && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 123-01-01 | 01 | 1 | CGRP-01 | unit | `pytest environment_service/tests/test_cgroup_detector.py::test_detect_cgroup_v1 -xvs` | ❌ W0 | ⬜ pending |
| 123-01-02 | 01 | 1 | CGRP-01 | unit | `pytest environment_service/tests/test_cgroup_detector.py::test_detect_cgroup_v2 -xvs` | ❌ W0 | ⬜ pending |
| 123-01-03 | 01 | 1 | CGRP-01 | unit | `pytest environment_service/tests/test_cgroup_detector.py::test_detect_cgroup_unsupported_permission -xvs` | ❌ W0 | ⬜ pending |
| 123-01-04 | 01 | 1 | CGRP-01 | unit | `pytest environment_service/tests/test_cgroup_detector.py::test_detect_cgroup_hybrid -xvs` | ❌ W0 | ⬜ pending |
| 123-02-01 | 02 | 1 | CGRP-02 | integration | `cd puppeteer && pytest tests/test_heartbeat.py::test_heartbeat_includes_cgroup_version -xvs` | ❌ W0 | ⬜ pending |
| 123-02-02 | 02 | 1 | CGRP-02 | integration | `cd puppeteer && pytest tests/test_job_service.py::test_receive_heartbeat_stores_cgroup -xvs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppets/environment_service/tests/test_cgroup_detector.py` — stubs for CGRP-01 (v1, v2, hybrid, unsupported)
- [ ] `puppeteer/tests/test_heartbeat.py` — stubs for CGRP-02 (heartbeat payload + NodeResponse)
- [ ] `puppeteer/tests/test_job_service.py` — stubs for CGRP-02 (receive_heartbeat DB updates)

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker-in-Docker cgroup detection accuracy | CGRP-01 | Requires real DinD environment | Deploy node in DinD container, verify cgroup version matches host cgroup namespace |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
