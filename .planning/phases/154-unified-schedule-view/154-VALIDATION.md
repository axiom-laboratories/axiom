---
phase: 154
slug: unified-schedule-view
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 154 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` + `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/test_scheduler.py::test_get_unified_schedule -xvs` (backend) / `cd puppeteer/dashboard && npm run test -- src/__tests__/Schedule.test.tsx` (frontend) |
| **Full suite command** | `cd puppeteer && pytest && cd ../puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick backend + frontend smoke tests
- **After every plan wave:** Run `cd puppeteer && pytest && cd ../puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 154-01-01 | 01 | 1 | UI-05 | unit + integration | `pytest tests/test_scheduler.py::test_get_unified_schedule_merges_jobs_workflows -xvs` | ❌ W0 | ⬜ pending |
| 154-01-02 | 01 | 1 | UI-05 | unit | `pytest tests/test_scheduler.py::test_get_unified_schedule_filters_inactive -xvs` | ❌ W0 | ⬜ pending |
| 154-01-03 | 01 | 1 | UI-05 | unit | `pytest tests/test_scheduler.py::test_get_unified_schedule_invalid_cron_skip -xvs` | ❌ W0 | ⬜ pending |
| 154-01-04 | 01 | 1 | UI-05 | integration | `pytest tests/test_main.py::test_schedule_endpoint_requires_permission -xvs` | ❌ W0 | ⬜ pending |
| 154-02-01 | 02 | 2 | UI-05 | component | `cd puppeteer/dashboard && npm run test -- src/__tests__/Schedule.test.tsx` | ❌ W0 | ⬜ pending |
| 154-02-02 | 02 | 2 | UI-05 | component + E2E | `cd puppeteer/dashboard && npm run test -- src/__tests__/Schedule.test.tsx` | ❌ W0 | ⬜ pending |
| 154-02-03 | 02 | 2 | UI-05 | unit | `cd puppeteer/dashboard && npm run test -- src/__tests__/Schedule.test.tsx` | ❌ W0 | ⬜ pending |
| 154-02-04 | 02 | 2 | UI-05 | component + E2E | `cd puppeteer/dashboard && npm run test -- src/__tests__/MainLayout.test.tsx` | ❌ W0 | ⬜ pending |
| 154-02-05 | 02 | 2 | UI-05 | component | `cd puppeteer/dashboard && npm run test -- src/__tests__/Schedule.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_scheduler.py` — stubs for `test_get_unified_schedule*` (3 tests: merging, filtering, cron parsing)
- [ ] `puppeteer/tests/test_main.py` — stub for `test_schedule_endpoint_requires_permission`
- [ ] `puppeteer/dashboard/src/__tests__/Schedule.test.tsx` — frontend component tests (5 tests: render, navigation, refetch, empty state)
- [ ] `puppeteer/dashboard/src/__tests__/MainLayout.test.tsx` — sidebar nav tests (rename, new entry)

*Framework install: None required — pytest + vitest already in place.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Schedule page accessible from sidebar nav | UI-05 | Requires browser navigation in Docker stack | Load dashboard, verify "Schedule" link in sidebar navigates to /schedule |
| JOB and FLOW badges visually distinct | UI-05 | Visual color distinction hard to assert in unit tests | Load Schedule page, verify JOB badge (blue) and FLOW badge (purple/indigo) are visually distinct |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
