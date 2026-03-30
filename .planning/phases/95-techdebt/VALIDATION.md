---
phase: 95
slug: techdebt
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-03-30
---

# Phase 95 — Validation Strategy

> Tech debt closure phase. Verification is a mix of automated tests, file-existence checks, and
> content inspection. All items are low-risk housekeeping edits.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + bash file-existence checks |
| **Config file** | puppeteer/pyproject.toml |
| **Quick run command** | `cd /home/thomas/Development/master_of_puppets/puppeteer && python -m pytest agent_service/tests/test_signing_ux.py -v` |
| **Full suite command** | `cd /home/thomas/Development/master_of_puppets/puppeteer && python -m pytest agent_service/tests/` |
| **Estimated runtime** | ~5 seconds (signing UX tests), ~60 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `pytest test_signing_ux.py -v`
- **After every plan wave:** Run full suite + file-existence checks for all VALIDATION.md files
- **Before `/gsd:verify-work`:** Full suite green + all must_haves satisfied
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 95-01-T1 | 95-01 | 1 | — | integration | `pytest test_signing_ux.py -v` | ✅ | ⬜ pending |
| 95-01-T2 | 95-01 | 1 | — | content | `grep -n "YOUR_SCRIPT" puppeteer/dashboard/src/views/Signatures.tsx` | ✅ | ⬜ pending |
| 95-01-T3 | 95-01 | 1 | — | content | `grep "DOC-01\|DOC-03" .planning/REQUIREMENTS.md` | ✅ | ⬜ pending |
| 95-01-T4 | 95-01 | 1 | — | content | `grep "requirements:" -A 2 .planning/phases/94-research-planning-closure/94-01-PLAN.md` | ✅ | ⬜ pending |
| 95-01-T5 | 95-01 | 1 | — | content | `grep "requirements:" -A 2 .planning/phases/94-research-planning-closure/94-02-PLAN.md` | ✅ | ⬜ pending |
| 95-02-T1 | 95-02 | 1 | — | existence | `test -f .planning/phases/92-usp-signing-ux/VALIDATION.md` | ⬜ | ⬜ pending |
| 95-02-T2 | 95-02 | 1 | — | existence | `test -f .planning/phases/93-documentation-prs/VALIDATION.md` | ⬜ | ⬜ pending |
| 95-02-T3 | 95-02 | 1 | — | existence | `test -f .planning/phases/94-research-planning-closure/VALIDATION.md` | ⬜ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files or frameworks needed —
all verification uses existing pytest suite and shell file checks.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Signatures page renders SIGN_CMD with YOUR_SCRIPT.py | — | UI render | Load the Signatures view in the dashboard; verify the signing script block shows YOUR_SCRIPT.py |
| REQUIREMENTS.md DOC strikethroughs render correctly | — | Markdown render | Open REQUIREMENTS.md in a markdown viewer; confirm DOC-01 and DOC-03 render as struck-through text |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
