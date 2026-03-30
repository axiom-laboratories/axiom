---
phase: 98
slug: dispatch-correctness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 98 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — `puppeteer/tests/`) |
| **Config file** | `puppeteer/pytest.ini` or `puppeteer/pyproject.toml` |
| **Quick run command** | `cd puppeteer && pytest tests/test_dispatch_correctness_phase98.py -v` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~15 seconds (unit tests only; integration tests skip on SQLite) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_dispatch_correctness_phase98.py -v`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 98-01-01 | 01 | 1 | DISP-01 | unit (code inspection) | `cd puppeteer && pytest tests/test_dispatch_correctness_phase98.py::test_index_declared_in_job_model -v` | ❌ W0 | ⬜ pending |
| 98-01-02 | 01 | 1 | DISP-02 | unit (file check) | `cd puppeteer && pytest tests/test_dispatch_correctness_phase98.py::test_migration_v44_exists_and_contains_index -v` | ❌ W0 | ⬜ pending |
| 98-01-03 | 01 | 1 | DISP-03 | unit (code inspection) | `cd puppeteer && pytest tests/test_dispatch_correctness_phase98.py::test_skip_locked_in_job_service -v` | ❌ W0 | ⬜ pending |
| 98-01-04 | 01 | 1 | DISP-04 | unit (IS_POSTGRES guard) | `cd puppeteer && pytest tests/test_dispatch_correctness_phase98.py::test_sqlite_path_unguarded -v` | ❌ W0 | ⬜ pending |
| 98-01-05 | 01 | 1 | OBS-03 | integration (Postgres skip-guarded) | `cd puppeteer && pytest tests/test_dispatch_correctness_phase98.py::test_no_double_assignment_concurrent_pull_work -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_dispatch_correctness_phase98.py` — new test file with stubs for DISP-01, DISP-02, DISP-03, DISP-04, OBS-03

*All tests go in a single new file. No conftest changes needed — existing fixtures are sufficient.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

The OBS-03 integration test runs only against Postgres. In a SQLite-only CI environment it is automatically skipped (not failed). The integration test should be run manually or in a Postgres-backed CI environment to exercise the zero double-assignment claim.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
