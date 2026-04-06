---
phase: 121
slug: job-service-admission-control
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 121 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vitest.config.ts` (frontend) |
| **Quick run command** | `cd puppeteer && pytest tests/test_job_service.py -x -v` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_job_service.py -x -v`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 121-01-01 | 01 | 0 | parse_bytes() | unit | `pytest tests/test_job_service.py::test_parse_bytes -v` | ❌ W0 | ⬜ pending |
| 121-01-02 | 01 | 0 | admission reject 422 | unit | `pytest tests/test_job_service.py::test_create_job_admission_exceeded -v` | ❌ W0 | ⬜ pending |
| 121-01-03 | 01 | 0 | admission accept | unit | `pytest tests/test_job_service.py::test_create_job_admission_accepted -v` | ❌ W0 | ⬜ pending |
| 121-01-04 | 01 | 0 | null memory compat | unit | `pytest tests/test_job_service.py::test_create_job_null_memory -v` | ❌ W0 | ⬜ pending |
| 121-01-05 | 01 | 0 | default limit config | unit | `pytest tests/test_job_service.py::test_create_job_default_limit -v` | ❌ W0 | ⬜ pending |
| 121-01-06 | 01 | 0 | pull_work capacity | unit | `pytest tests/test_job_service.py::test_pull_work_capacity_check -v` | ❌ W0 | ⬜ pending |
| 121-01-07 | 01 | 0 | diagnosis memory | unit | `pytest tests/test_job_service.py::test_diagnosis_memory_blocking -v` | ❌ W0 | ⬜ pending |
| 121-01-08 | 01 | 0 | diagnosis breakdown | unit | `pytest tests/test_job_service.py::test_diagnosis_nodes_breakdown -v` | ❌ W0 | ⬜ pending |
| 121-02-01 | 02 | 1 | API oversized job | integration | `pytest tests/test_main.py::test_create_job_oversized -v` | ❌ W0 | ⬜ pending |
| 121-02-02 | 02 | 1 | diagnosis API | integration | `pytest tests/test_main.py::test_diagnosis_memory_api -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_job_service.py` — stubs for parse_bytes, admission, capacity, diagnosis tests
- [ ] `tests/test_main.py` — stubs for API integration tests (oversized job, diagnosis endpoint)
- [ ] Fixtures: mock Node records with `job_memory_limit`, ASSIGNED/RUNNING jobs for capacity sum testing
- [ ] Verify pytest asyncio plugin configured for async test functions

*Existing infrastructure covers framework setup — Wave 0 adds test stubs only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Jobs.tsx PENDING diagnosis inline | UI diagnosis display | React component rendering | Expand a PENDING job in Jobs view, verify diagnosis panel shows per-node breakdown |
| JobDefinitions.tsx limit fields | Scheduled job limits | Form interaction | Create/edit a scheduled job, verify memory_limit and cpu_limit fields appear and persist |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
