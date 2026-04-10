---
phase: 126
slug: limit-enforcement-validation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-09
---

# Phase 126 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + standalone orchestrator script (end-to-end) |
| **Config file** | none — orchestrator is standalone |
| **Quick run command** | `python3 mop_validation/scripts/stress/orchestrate_stress_tests.py --dry-run` |
| **Full suite command** | `python3 mop_validation/scripts/stress/orchestrate_stress_tests.py` |
| **Estimated runtime** | ~120 seconds (full suite across both runtimes) |

---

## Sampling Rate

- **After every task commit:** Run `--dry-run` to verify orchestrator loads scripts and connects to API
- **After every plan wave:** Run full orchestrator on both Docker and Podman runtimes
- **Before `/gsd:verify-work`:** Full suite must be green on both runtimes
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 126-01-01 | 01 | 1 | ENFC-04 | integration | Deploy Podman node + verify heartbeat | ✅ node-compose.yaml | ⬜ pending |
| 126-01-02 | 01 | 1 | ENFC-04 | integration | Orchestrator `--runtime` filter works | ✅ orchestrate_stress_tests.py | ⬜ pending |
| 126-02-01 | 02 | 2 | ENFC-01 | e2e | `orchestrate_stress_tests.py --runtime docker` Scenario 2 (OOM) | ✅ | ⬜ pending |
| 126-02-02 | 02 | 2 | ENFC-02 | e2e | `orchestrate_stress_tests.py --runtime docker` Scenario 1 (CPU) | ✅ | ⬜ pending |
| 126-02-03 | 02 | 2 | ENFC-01 | e2e | `orchestrate_stress_tests.py --runtime podman` Scenario 2 (OOM) | ✅ | ⬜ pending |
| 126-02-04 | 02 | 2 | ENFC-02 | e2e | `orchestrate_stress_tests.py --runtime podman` Scenario 1 (CPU) | ✅ | ⬜ pending |
| 126-03-01 | 03 | 2 | — | report | Validation report written to `mop_validation/reports/` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Podman node compose configuration (new file in `mop_validation/local_nodes/`)
- [ ] Orchestrator `--runtime` CLI flag for execution_mode filtering
- [ ] Validation report template/format definition

*Existing infrastructure covers stress scripts, /dispatch endpoint, and heartbeat execution_mode reporting.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Podman node enrolls and heartbeats | ENFC-04 | Requires live Podman container | Deploy Podman node, check `/nodes` response shows execution_mode=podman |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
