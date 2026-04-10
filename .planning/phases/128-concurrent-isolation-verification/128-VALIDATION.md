---
phase: 128
slug: concurrent-isolation-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 128 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (unit tests) + manual orchestrator integration tests |
| **Config file** | `puppeteer/tests/conftest.py` (existing) |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -k "not (slow or integration)" --tb=short` |
| **Full suite command** | `cd puppeteer && pytest tests/` |
| **Estimated runtime** | ~30 seconds (unit tests) / ~6 minutes (full 5-run orchestrator) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x --tb=short`
- **After every plan wave:** Run `cd puppeteer && pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (unit tests)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 128-01-01 | 01 | 1 | ISOL-01/02 | unit | `python mop_validation/scripts/stress/python/noisy_monitor.py` | ❌ W0 | ⬜ pending |
| 128-01-02 | 01 | 1 | ISOL-01/02 | integration | Orchestrator 5-run test via `python mop_validation/scripts/stress/orchestrate_stress_tests.py` | ✅ | ⬜ pending |
| 128-02-01 | 02 | 2 | ISOL-01/02 | integration | Full orchestrator concurrent isolation scenario | ✅ | ⬜ pending |
| 128-02-02 | 02 | 2 | ISOL-01/02 | manual | Review generated report in `mop_validation/reports/isolation_verification.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/stress/python/noisy_monitor.py` — Python mirror of bash/pwsh noisy monitor
- [ ] Orchestrator enhancements (target_node_id, 5-run loop) — extend existing orchestrate_stress_tests.py

*Existing test infrastructure (conftest.py, pytest) covers unit test needs. Phase 128 primarily adds integration validation via orchestrator execution on live Docker nodes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Memory hog OOM doesn't starve monitor | ISOL-01 | Requires live Docker node with cgroup limits | Run orchestrator scenario 3; verify monitor completes 60 iterations on 4/5 runs |
| Latency drift < 1.1s under load | ISOL-02 | Requires concurrent job execution on real node | Run orchestrator scenario 3; check max_drift_s < 1.1 in monitor JSON output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
