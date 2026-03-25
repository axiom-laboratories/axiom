---
phase: 65
slug: friction-report-synthesis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 65 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing in mop_validation) + inline smoke assertions |
| **Config file** | None — inline |
| **Quick run command** | `python ~/Development/mop_validation/scripts/synthesise_friction.py && grep -q "NOT READY" ~/Development/mop_validation/reports/cold_start_friction_report.md` |
| **Full suite command** | `python ~/Development/mop_validation/scripts/synthesise_friction.py && python -c "import pathlib; r = pathlib.Path('/home/thomas/Development/mop_validation/reports/cold_start_friction_report.md').read_text(); assert 'NOT READY' in r; assert 'Cross-Edition' in r; print('PASS')"` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command above
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 65-01-01 | 01 | 1 | RPT-01 | smoke | `python ~/Development/mop_validation/scripts/synthesise_friction.py` | ❌ W0 | ⬜ pending |
| 65-01-02 | 01 | 1 | RPT-01 | smoke | `grep -q "Cross-Edition" ~/Development/mop_validation/reports/cold_start_friction_report.md` | ❌ W0 | ⬜ pending |
| 65-01-03 | 01 | 1 | RPT-01 | smoke | `grep -q "NOT READY" ~/Development/mop_validation/reports/cold_start_friction_report.md` | ❌ W0 | ⬜ pending |
| 65-01-04 | 01 | 1 | RPT-01 | smoke | Check finding count > 0 in report | ❌ W0 | ⬜ pending |
| 65-01-05 | 01 | 1 | RPT-01 | unit | `python ~/Development/mop_validation/scripts/synthesise_friction.py --reports-dir /tmp/empty; [ $? -ne 0 ] && echo PASS` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/synthesise_friction.py` — the synthesis script (primary deliverable)

*Note: The FRICTION.md source files already exist in mop_validation/reports/ — no additional test fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-edition comparison table accuracy | RPT-01 | Requires human review of finding classification (CE-only vs EE-only vs shared) | Open `cold_start_friction_report.md`, verify each finding in the comparison table matches the source FRICTION.md files |
| Actionable recommendations completeness | RPT-01 | Requires human judgement on recommendation quality | Verify every BLOCKER/NOTABLE has a doc section or code path reference |
| First-user readiness verdict rationale | RPT-01 | Requires human review of verdict logic | Confirm NOT READY verdict lists all blocking criteria |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
