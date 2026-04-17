---
phase: 163
slug: v23-0-tech-debt-closure
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-17
verified: 2026-04-17
---

# Phase 163 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Documentation phase — no new tests (regression tests verified) |
| **Config file** | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vitest.config.ts` (frontend) |
| **Quick run command** | `cd puppeteer && pytest tests/test_regression_phase157_deferred_gaps.py -v` |
| **Full suite command** | `cd puppeteer && pytest tests/test_regression_phase157_deferred_gaps.py tests/test_workflow.py tests/test_compatibility_engine.py -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_regression_phase157_deferred_gaps.py -v`
- **After every plan wave:** Run full suite command above
- **Before `/gsd:verify-work`:** Full suite must be green + VALIDATION.md files written
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 163-01-01 | 01 | 1 | Nyquist-158 | doc | `ls .planning/phases/158-*/163-VALIDATION.md` | ❌ W0 | ⬜ pending |
| 163-01-02 | 01 | 1 | Nyquist-159 | doc | `ls .planning/phases/159-*/163-VALIDATION.md` | ❌ W0 | ⬜ pending |
| 163-01-03 | 01 | 1 | Nyquist-160 | doc | `ls .planning/phases/160-*/163-VALIDATION.md` | ❌ W0 | ⬜ pending |
| 163-01-04 | 01 | 1 | Nyquist-161 | doc | `ls .planning/phases/161-*/163-VALIDATION.md` | ❌ W0 | ⬜ pending |
| 163-01-05 | 01 | 1 | Nyquist-162 | doc | `ls .planning/phases/162-*/163-VALIDATION.md` | ❌ W0 | ⬜ pending |
| 163-02-01 | 02 | 2 | MIN-6 | regression | `cd puppeteer && pytest tests/test_regression_phase157_deferred_gaps.py::test_node_stats_pruning_sqlite_compatible -v` | ✅ | ⬜ pending |
| 163-02-02 | 02 | 2 | MIN-7 | regression | `cd puppeteer && pytest tests/test_regression_phase157_deferred_gaps.py::test_foundry_build_dir_cleanup_on_failure -v` | ✅ | ⬜ pending |
| 163-02-03 | 02 | 2 | MIN-8 | regression | `cd puppeteer && pytest tests/test_regression_phase157_deferred_gaps.py::test_require_permission_uses_cache -v` | ✅ | ⬜ pending |
| 163-02-04 | 02 | 2 | WARN-8 | regression | `cd puppeteer && pytest tests/test_regression_phase157_deferred_gaps.py::test_node_id_scan_deterministic -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Regression tests for MIN-6/7/8, WARN-8 already exist in `test_regression_phase157_deferred_gaps.py` (written in Phase 157, all passing).

*No new test stubs or framework installs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VALIDATION.md files accepted as Nyquist-compliant | Nyquist-158..162 | Content review needed | Read each VALIDATION.md, confirm frontmatter has `nyquist_compliant: true`, task map covers phase scope |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
