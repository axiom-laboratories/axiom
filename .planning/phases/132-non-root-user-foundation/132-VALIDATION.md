---
phase: 132
slug: non-root-user-foundation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 132 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or `pyproject.toml`) |
| **Quick run command** | `cd puppeteer && pytest tests/test_nonroot.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_nonroot.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 132-01-01 | 01 | 1 | CONT-01 | integration | `docker run --rm master-of-puppets-agent stat -c '%U:%G' /app` | ❌ W0 | ⬜ pending |
| 132-01-02 | 01 | 1 | CONT-01 | integration | `docker run --rm master-of-puppets-agent id` | ❌ W0 | ⬜ pending |
| 132-01-03 | 01 | 1 | CONT-06 | integration | `docker run --rm master-of-puppets-node stat -c '%U:%G' /app` | ❌ W0 | ⬜ pending |
| 132-02-01 | 02 | 2 | CONT-01 | integration | `cd puppeteer && pytest tests/test_nonroot.py::test_agent_runs_as_nonroot -x` | ❌ W0 | ⬜ pending |
| 132-02-02 | 02 | 2 | CONT-06 | integration | `cd puppeteer && pytest tests/test_nonroot.py::test_node_runs_as_nonroot -x` | ❌ W0 | ⬜ pending |
| 132-02-03 | 02 | 2 | CONT-01 | integration | `cd puppeteer && pytest tests/test_nonroot.py::test_volumes_owned_by_appuser -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_nonroot.py` — stubs for CONT-01, CONT-06 (image-level and compose-level checks)
- [ ] `mop_validation/scripts/verify_nonroot.sh` — shell script for integration verification against running stack

*Existing pytest infrastructure covers the framework; new test file needed for phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Volume ownership migrates on upgrade | CONT-01 | Requires starting old (root) container then upgrading | 1. Start stack with old image, 2. Recreate with new image, 3. Run `docker exec agent stat -c '%U:%G' /app/secrets` |
| Non-root user can write to logs/tmp/config | CONT-01 | Full write test requires live stack | `docker exec agent touch /app/secrets/test_write && echo "Write OK"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
