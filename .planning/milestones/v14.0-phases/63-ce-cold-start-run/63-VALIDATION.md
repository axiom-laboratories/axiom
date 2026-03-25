---
phase: 63
slug: ce-cold-start-run
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 63 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (mop_validation) + manual FRICTION file review |
| **Config file** | none — scripts are standalone (`python3 script.py`) |
| **Quick run command** | `incus exec axiom-coldstart -- bash -c "docker ps --format '{{.Names}}'"` |
| **Full suite command** | `cat ~/Development/mop_validation/reports/FRICTION-CE-*.md` |
| **Estimated runtime** | ~600 seconds (first-run Docker build) |

---

## Sampling Rate

- **After every task commit:** Verify FRICTION file exists in LXC before pulling
- **After every plan wave:** Both FRICTION files present in `mop_validation/reports/`
- **Before `/gsd:verify-work`:** FRICTION files pulled and CE-05 acceptance gate evaluated
- **Max feedback latency:** 600 seconds (first cold build budget)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 63-01-01 | 01 | 1 | CE-01 | manual | `incus exec axiom-coldstart -- bash -c "docker ps"` | ✅ | ⬜ pending |
| 63-01-02 | 01 | 1 | CE-01 | automated | Stack readiness poll (HTTP 200/301 on :8443) | ✅ | ⬜ pending |
| 63-02-01 | 02 | 2 | CE-01 | Gemini scenario | ce-install.md run → FRICTION-CE-INSTALL.md generated | ❌ W0 (generated) | ⬜ pending |
| 63-02-02 | 02 | 2 | CE-05 | manual | `cat mop_validation/reports/FRICTION-CE-INSTALL.md` | ❌ W0 (generated) | ⬜ pending |
| 63-03-01 | 03 | 3 | CE-02, CE-03, CE-04 | Gemini scenario | ce-operator.md run → FRICTION-CE-OPERATOR.md generated | ❌ W0 (generated) | ⬜ pending |
| 63-03-02 | 03 | 3 | CE-05 | manual | `cat mop_validation/reports/FRICTION-CE-OPERATOR.md` | ❌ W0 (generated) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The verification script `verify_phase62_scaf.py` already validates scaffolding. CE-specific verification (`verify_ce_install.py`, `verify_ce_job.py`) exists for post-run checks. No new test files need to be created — FRICTION.md files are outputs of the Gemini scenario runs themselves.

*No Wave 0 test stubs required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CE install: stack running, node enrolled, dashboard accessible | CE-01 | Verified by Gemini agent following docs + FRICTION-CE-INSTALL.md checklist | Read `mop_validation/reports/FRICTION-CE-INSTALL.md`; confirm PASS on enrolled-node and dashboard-reachable checklist items |
| Python job COMPLETED with stdout | CE-02 | Verified by Gemini agent in ce-operator.md; result in FRICTION-CE-OPERATOR.md | Read `mop_validation/reports/FRICTION-CE-OPERATOR.md`; confirm Python job PASS entry |
| Bash job COMPLETED with stdout | CE-03 | Verified by Gemini agent in ce-operator.md | Read FRICTION-CE-OPERATOR.md; confirm Bash job PASS entry |
| PowerShell job COMPLETED with stdout | CE-04 | Verified by Gemini agent in ce-operator.md | Read FRICTION-CE-OPERATOR.md; confirm PowerShell job PASS entry |
| FRICTION.md contains verbatim quotes, BLOCKER/NOTABLE/MINOR, checkpoint disclosure | CE-05 | Content quality judgment | Operator reviews both FRICTION files for format compliance and completeness |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 600s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
