---
phase: 45
slug: gap-report-synthesis-critical-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `puppeteer/pytest.ini` (inferred; tests run from `cd puppeteer && pytest`) |
| **Quick run command** | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_foundry_build_cleanup.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green + `mop_validation/reports/v11.1-gap-report.md` exists + `verify_foundry_04_build_dir.py` exits 0
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 45-01-01 | 01 | 1 | GAP-01 | manual/output | `ls mop_validation/reports/v11.1-gap-report.md` | ❌ W0 | ⬜ pending |
| 45-01-02 | 01 | 1 | GAP-03 | manual/output | inspect backlog section in gap report | ❌ W0 | ⬜ pending |
| 45-02-01 | 02 | 2 | GAP-02 | unit | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py::test_build_dir_cleaned_up_on_success -x` | ❌ W0 | ⬜ pending |
| 45-02-02 | 02 | 2 | GAP-02 | unit | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py::test_build_dir_cleaned_up_on_failure -x` | ❌ W0 | ⬜ pending |
| 45-02-03 | 02 | 2 | GAP-02 | integration | `python mop_validation/scripts/verify_foundry_04_build_dir.py` | ✅ (needs mod) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_foundry_build_cleanup.py` — MIN-07 regression tests (GAP-02)
- [ ] `mop_validation/reports/v11.1-gap-report.md` — primary output artefact (GAP-01, GAP-03)

*`mop_validation/scripts/verify_foundry_04_build_dir.py` exists but needs assertion inversion — not a new file gap.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gap report contains all findings with severity/area/repro/fix | GAP-01 | Document inspection — no automated parser | Open `mop_validation/reports/v11.1-gap-report.md`, verify every SUMMARY.md finding appears with ID, severity, area, reproduction steps, and v12.0+ fix candidate |
| Backlog section cross-references MIN-06, MIN-07, MIN-08, WARN-08 | GAP-03 | Document inspection | Check backlog section of gap report — all four deferred IDs must appear with their original designations |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
