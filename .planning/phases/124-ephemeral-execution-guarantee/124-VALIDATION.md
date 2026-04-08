---
phase: 124
slug: ephemeral-execution-guarantee
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 124 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python backend) + vitest (React frontend) |
| **Config file** | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vitest.config.ts` (frontend) |
| **Quick run command** | `cd puppeteer && pytest tests/test_job_service.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_job_service.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 124-01-01 | 01 | 1 | EPHR-02 | integration | `pytest tests/test_compose_validation.py -x` | ❌ W0 | ⬜ pending |
| 124-01-02 | 01 | 1 | heartbeat | unit | `pytest tests/test_job_service.py -x` | ✅ | ⬜ pending |
| 124-01-03 | 01 | 1 | NodeResponse | integration | `pytest tests/test_job_service.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_compose_validation.py` — stubs for compose generator direct-mode rejection
- [ ] `puppeteer/tests/test_heartbeat_execution_mode.py` — stubs for heartbeat execution_mode persistence

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard execution_mode badge | Phase 127 | UI rendering deferred to Phase 127 | Visual check in Nodes.tsx after stack rebuild |
| Server NODE_EXECUTION_MODE=direct rejection | startup validation | Requires process restart with env var | `NODE_EXECUTION_MODE=direct python -m agent_service.main` should fail |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
