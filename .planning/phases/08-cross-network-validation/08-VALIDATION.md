---
phase: 8
slug: cross-network-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | mop_validation/scripts/test_cross_network.py |
| **Quick run command** | `python mop_validation/scripts/test_cross_network.py --keep` |
| **Full suite command** | `python mop_validation/scripts/test_cross_network.py` |
| **Estimated runtime** | ~300 seconds (LXC provisioning + full stack validation) |

---

## Sampling Rate

- **After every task commit:** Verify the specific component implemented (API call, LXC command, or helper function) compiles and is importable
- **After every plan wave:** Run `python mop_validation/scripts/test_cross_network.py --keep` to check progress against actual LXCs
- **Before `/gsd:verify-work`:** Full suite must pass (both Docker and Podman stacks)
- **Max feedback latency:** ~300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | Script skeleton | unit | `python -c "import mop_validation.scripts.test_cross_network"` | ❌ W0 | ⬜ pending |
| 8-01-02 | 01 | 1 | LXC provisioning | integration | `python mop_validation/scripts/test_cross_network.py --dry-run` | ❌ W0 | ⬜ pending |
| 8-02-01 | 02 | 1 | Docker stack enroll+heartbeat | e2e | `python mop_validation/scripts/test_cross_network.py --stack docker --keep` | ❌ W0 | ⬜ pending |
| 8-02-02 | 02 | 1 | Docker job dispatch+execute | e2e | `python mop_validation/scripts/test_cross_network.py --stack docker --keep` | ❌ W0 | ⬜ pending |
| 8-02-03 | 02 | 1 | Docker revocation | e2e | `python mop_validation/scripts/test_cross_network.py --stack docker --keep` | ❌ W0 | ⬜ pending |
| 8-03-01 | 03 | 2 | Podman stack enroll+heartbeat | e2e | `python mop_validation/scripts/test_cross_network.py --stack podman --keep` | ❌ W0 | ⬜ pending |
| 8-03-02 | 03 | 2 | Podman job dispatch+execute | e2e | `python mop_validation/scripts/test_cross_network.py --stack podman --keep` | ❌ W0 | ⬜ pending |
| 8-03-03 | 03 | 2 | Full suite both stacks | e2e | `python mop_validation/scripts/test_cross_network.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/test_cross_network.py` — main test harness (created in Wave 1 Plan 01)
- [ ] `mop_validation/scripts/sign_job.py` or reuse existing signing tool — for test job signing

*The test script IS the test infrastructure for this phase — Wave 0 and Wave 1 overlap since the deliverable is the script itself.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Podman-compose gap documentation | Podman stack compat | Subjective assessment of what "documented" means | Read output file after Podman stack test; confirm gap list is accurate |
| Node revocation cross-network (403) | Revocation check | Cannot call /work/pull with node's mTLS cert from test harness | Verify via `GET /nodes` status=REVOKED and remaining nodes continue heartbeating |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
