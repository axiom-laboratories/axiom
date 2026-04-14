---
phase: 134
slug: socket-mount-podman-support
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 134 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or `pyproject.toml`) |
| **Quick run command** | `cd puppeteer && pytest tests/test_runtime.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_runtime.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 134-01-01 | 01 | 0 | CONT-10 | unit | `cd puppeteer && pytest tests/test_runtime_socket.py -x -q` | ❌ W0 | ⬜ pending |
| 134-01-02 | 01 | 1 | CONT-10 | unit | `cd puppeteer && pytest tests/test_runtime_socket.py -x -q` | ❌ W0 | ⬜ pending |
| 134-01-03 | 01 | 1 | CONT-02 | unit | `cd puppeteer && pytest tests/test_runtime_network.py -x -q` | ❌ W0 | ⬜ pending |
| 134-02-01 | 02 | 1 | CONT-02 | integration | `docker compose -f puppets/node-compose.yaml config --quiet` | ✅ | ⬜ pending |
| 134-02-02 | 02 | 1 | CONT-09 | integration | `docker compose -f puppets/node-compose.podman.yaml config --quiet` | ❌ W0 | ⬜ pending |
| 134-02-03 | 02 | 2 | CONT-02, CONT-09 | e2e | `cd puppeteer && pytest tests/test_node_compose.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_runtime_socket.py` — stubs for CONT-10 (socket detection unit tests: docker sock, podman sock, binary fallback, env override)
- [ ] `puppeteer/tests/test_runtime_network.py` — stubs for CONT-02 network isolation (jobs_network wiring in run())
- [ ] `puppeteer/tests/test_node_compose.py` — stubs for CONT-02/CONT-09 compose validation (no privileged, socket mount present, cap_drop ALL)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Job executes without privileged mode via socket | CONT-02 | Requires live Docker daemon + node container running | Start stack with `docker compose -f puppets/node-compose.yaml up -d`, dispatch a job, confirm execution succeeds in node logs |
| Podman rootless socket detection works | CONT-09 | Requires Podman daemon running on host | `systemctl --user enable podman.socket && docker compose -f puppets/node-compose.podman.yaml up -d`, dispatch job, confirm runtime=podman in logs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
