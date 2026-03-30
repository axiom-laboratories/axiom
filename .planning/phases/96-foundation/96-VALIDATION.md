---
phase: 96
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 96 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `puppeteer/pytest.ini` (none — inline markers) |
| **Quick run command** | `cd puppeteer && pytest tests/test_foundation_phase96.py -v` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~5 seconds (unit tests, in-memory SQLite) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_foundation_phase96.py -v`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 96-01-01 | 01 | 1 | FOUND-01 | unit | `pytest tests/test_foundation_phase96.py::test_requirements_pin -v` | ❌ W0 | ⬜ pending |
| 96-01-02 | 01 | 1 | FOUND-02 | unit | `pytest tests/test_foundation_phase96.py::test_is_postgres_flag -v` | ❌ W0 | ⬜ pending |
| 96-01-03 | 01 | 1 | FOUND-03 | unit | `pytest tests/test_foundation_phase96.py::test_scheduler_job_defaults -v` | ❌ W0 | ⬜ pending |
| 96-01-04 | 01 | 1 | FOUND-01 | unit | `pytest tests/test_foundation_phase96.py::test_apscheduler_version_assertion -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_foundation_phase96.py` — stubs/implementations for FOUND-01, FOUND-02, FOUND-03
