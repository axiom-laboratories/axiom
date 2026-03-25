---
phase: 62
slug: agent-scaffolding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 62 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python 3 scripts (no pytest — infrastructure-level checks) |
| **Config file** | none — scripts are self-contained |
| **Quick run command** | `python3 mop_validation/scripts/verify_phase62_scaf.py` |
| **Full suite command** | `python3 mop_validation/scripts/verify_phase62_scaf.py --full` |
| **Estimated runtime** | ~30 seconds (quick); ~90 seconds (full with round-trip) |

---

## Sampling Rate

- **After every task commit:** Run `python3 mop_validation/scripts/verify_phase62_scaf.py`
- **After every plan wave:** Run `python3 mop_validation/scripts/verify_phase62_scaf.py --full`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 62-01-01 | 01 | 0 | SCAF-01 | smoke | `incus exec axiom-coldstart -- test -f /workspace/gemini-context/GEMINI.md && echo PASS` | ❌ W0 | ⬜ pending |
| 62-01-02 | 01 | 0 | SCAF-02 | smoke | `python3 mop_validation/scripts/verify_phase62_scaf.py --checkpoint-roundtrip` | ❌ W0 | ⬜ pending |
| 62-01-03 | 01 | 0 | SCAF-03 | smoke | `python3 mop_validation/scripts/verify_phase62_scaf.py --isolation` | ❌ W0 | ⬜ pending |
| 62-01-04 | 01 | 0 | SCAF-04 | smoke | `python3 mop_validation/scripts/verify_phase62_scaf.py --scenarios` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/verify_phase62_scaf.py` — SCAF-01 through SCAF-04 smoke verifier
- [ ] `mop_validation/scenarios/` — directory for scenario `.md` files
- [ ] `mop_validation/scenarios/tester-gemini.md` — tester persona GEMINI.md content
- [ ] `mop_validation/scripts/setup_agent_scaffolding.py` — LXC workspace setup script
- [ ] `mop_validation/scripts/monitor_checkpoint.py` — host-side checkpoint watcher

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SCAF-02 round-trip with real Gemini API | SCAF-02 | Requires Tier 1 paid API key (free tier quota exhausted, returns 429) | Run `verify_phase62_scaf.py --full` after confirming API key is Tier 1 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
