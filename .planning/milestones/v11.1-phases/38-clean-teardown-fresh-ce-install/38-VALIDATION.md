---
phase: 38
slug: clean-teardown-fresh-ce-install
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | standalone Python script (no pytest runner needed) |
| **Config file** | none — `verify_ce_install.py` is a standalone executable |
| **Quick run command** | `python3 ~/Development/mop_validation/scripts/verify_ce_install.py` |
| **Full suite command** | same — single script covers INST-01 through INST-04 |
| **Estimated runtime** | ~30 seconds (includes stack readiness wait) |

---

## Sampling Rate

- **After every task commit:** Manual inspection of script output / `docker volume ls` / `docker ps`
- **After every plan wave:** Run `python3 ~/Development/mop_validation/scripts/verify_ce_install.py` against a fresh CE cold start
- **Before `/gsd:verify-work`:** All `verify_ce_install.py` checks must print `[PASS]`
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 1 | INST-01 | smoke | `bash teardown_soft.sh && docker volume ls` | ❌ W0 | ⬜ pending |
| 38-01-02 | 01 | 1 | INST-02 | smoke | `bash teardown_hard.sh` | ❌ W0 | ⬜ pending |
| 38-02-01 | 02 | 2 | INST-03 | integration | `python3 verify_ce_install.py` | ❌ W0 | ⬜ pending |
| 38-02-02 | 02 | 2 | INST-04 | manual | see script comments in `verify_ce_install.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/teardown_soft.sh` — bash script covering INST-01 (stop containers, rm pgdata only)
- [ ] `mop_validation/scripts/teardown_hard.sh` — bash script covering INST-02 (all volumes + LXC node secrets)
- [ ] `mop_validation/scripts/verify_ce_install.py` — Python verification covering INST-03 and INST-04

*All three files are the deliverables of this phase — Wave 0 IS the phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin re-seed safety | INST-04 | Requires deliberate env-var change + restart cycle | 1. Start CE stack fresh. 2. Log in as admin (password A). 3. Stop stack. 4. Change ADMIN_PASSWORD to B. 5. Start stack. 6. Log in with password A — must succeed. Log in with B — must fail. Document in `verify_ce_install.py` comments. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
