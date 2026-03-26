---
phase: 68
slug: ee-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 68 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | MkDocs `mkdocs build --strict` + grep smoke tests |
| **Config file** | `docs/mkdocs.yml` |
| **Quick run command** | `grep -r "api/admin/features" docs/docs/ && echo FAIL || echo PASS` |
| **Full suite command** | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict 2>&1 | tail -20` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `grep -r "api/admin/features" docs/docs/ && echo FAIL || echo PASS`
- **After every plan wave:** Run `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict 2>&1 | tail -20`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 68-01-01 | 01 | 1 | EEDOC-01 | grep smoke | `grep "api/features" docs/docs/getting-started/install.md` | ✅ (after edit) | ⬜ pending |
| 68-01-02 | 01 | 1 | EEDOC-01 | grep smoke | `grep -r "api/admin/features" docs/docs/ && echo FAIL \|\| echo PASS` | ✅ | ⬜ pending |
| 68-02-01 | 02 | 1 | EEDOC-02 | grep smoke | `grep "AXIOM_LICENCE_KEY" docs/docs/licensing.md` | ✅ | ⬜ pending |
| 68-02-02 | 02 | 1 | EEDOC-02 | grep smoke | `grep -r "AXIOM_EE_LICENCE_KEY" docs/docs/ && echo FAIL \|\| echo PASS` | ✅ | ⬜ pending |
| 68-xx-build | 01+02 | 1 | EEDOC-01, EEDOC-02 | build | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict 2>&1 \| tail -20` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. No new test files needed — grep + mkdocs build covers EEDOC-01 and EEDOC-02 fully.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| EE badge visible in dashboard sidebar when key is valid | EEDOC-01 | UI visual check — requires live stack with valid licence key | Start stack with `AXIOM_LICENCE_KEY` set, log in, check sidebar shows **EE** badge |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
