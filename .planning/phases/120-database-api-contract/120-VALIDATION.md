---
phase: 120
slug: database-api-contract
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 120 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend) |
| **Config file** | `puppeteer/tests/conftest.py` + `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/test_job_limits.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_job_limits.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 120-01-01 | 01 | 0 | ENFC-03 | unit | `pytest tests/test_job_limits.py -x` | ❌ W0 | ⬜ pending |
| 120-01-02 | 01 | 1 | ENFC-03 | unit | `pytest tests/test_job_limits.py::test_job_limits_persist -x` | ❌ W0 | ⬜ pending |
| 120-01-03 | 01 | 1 | ENFC-03 | unit | `pytest tests/test_job_limits.py::test_work_response_has_limits -x` | ❌ W0 | ⬜ pending |
| 120-01-04 | 01 | 1 | ENFC-03 | unit | `pytest tests/test_job_limits.py::test_limit_format_validation -x` | ❌ W0 | ⬜ pending |
| 120-01-05 | 01 | 1 | ENFC-03 | unit | `pytest tests/test_job_limits.py::test_nullable_limits -x` | ❌ W0 | ⬜ pending |
| 120-02-01 | 02 | 1 | ENFC-03 | integration | `pytest tests/test_migration_v49.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_job_limits.py` — unit tests for JobCreate/JobResponse/WorkResponse model validation, DB column persistence, nullable backward compatibility
- [ ] `tests/test_migration_v49.py` — integration test for migration idempotency on Postgres, fresh SQLite schema verification
- [ ] `tests/conftest.py` — existing fixtures cover async_client, event_loop; may need DB setup for migration testing

*Existing infrastructure covers conftest.py; Wave 0 adds two new test files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dispatch UI limit inputs render correctly | ENFC-03 | Visual layout/styling | Open Jobs.tsx dispatch form, verify Memory Limit and CPU Limit inputs appear and accept text |
| Job detail view shows limits | ENFC-03 | Visual display | Dispatch job with limits, expand job row, verify limits visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
