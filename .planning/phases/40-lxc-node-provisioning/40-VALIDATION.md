---
phase: 40
slug: lxc-node-provisioning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Custom integration script (matching verify_ce_install.py / verify_ee_install.py pattern) |
| **Config file** | none — standalone script |
| **Quick run command** | `python3 ~/Development/mop_validation/scripts/verify_lxc_nodes.py` |
| **Full suite command** | `python3 ~/Development/mop_validation/scripts/verify_lxc_nodes.py` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Not applicable — no unit tests; integration tests require running stack
- **After every plan wave:** Run `python3 ~/Development/mop_validation/scripts/verify_lxc_nodes.py`
- **Before `/gsd:verify-work`:** Full suite must be green (all 5 `[PASS]` lines)
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 40-01-01 | 01 | 1 | NODE-01 | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 | ⬜ pending |
| 40-01-02 | 01 | 1 | NODE-02 | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 | ⬜ pending |
| 40-01-03 | 01 | 1 | NODE-03 | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 | ⬜ pending |
| 40-01-04 | 01 | 1 | NODE-04 | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 | ⬜ pending |
| 40-01-05 | 01 | 1 | NODE-05 | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/provision_lxc_nodes.py` — provisioner script (Wave 1 deliverable)
- [ ] `mop_validation/scripts/verify_lxc_nodes.py` — verification script covering NODE-01 through NODE-05 (Wave 1 deliverable)
- [ ] `mop_validation/local_nodes/lxc-node-compose.yaml` — Docker Compose template for LXC nodes (Wave 1 deliverable)
- [ ] `mop_validation/secrets/nodes/` directory — created by provisioner at runtime

*All verification files are Wave 1 deliverables (they are the phase output, not pre-existing infrastructure).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Revoke → 403 → reinstate → re-enroll → HEALTHY | NODE-05 | Requires operator action to reinstate revoked node | Run `python3 .../verify_lxc_nodes.py` — script automates revoke, checks 403, calls reinstate, re-issues token, restarts container, checks HEALTHY |

*The verify script automates the full NODE-05 lifecycle including reinstate; no manual steps needed.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
