---
phase: 53
slug: scheduling-health-and-data-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 53 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` (implicit) + `puppeteer/dashboard/vite.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/test_scheduling_health.py tests/test_job_templates.py tests/test_retention.py tests/test_execution_export.py -x` |
| **Full suite command** | `cd puppeteer && pytest` / `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~30 seconds (backend quick) / ~90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_scheduling_health.py tests/test_job_templates.py tests/test_retention.py tests/test_execution_export.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 53-01-01 | 01 | 0 | VIS-05, VIS-06 | unit stub | `pytest tests/test_scheduling_health.py -x` | ❌ W0 | ⬜ pending |
| 53-01-02 | 01 | 0 | SRCH-06, SRCH-07 | unit stub | `pytest tests/test_job_templates.py -x` | ❌ W0 | ⬜ pending |
| 53-01-03 | 01 | 0 | SRCH-08, SRCH-09 | unit stub | `pytest tests/test_retention.py -x` | ❌ W0 | ⬜ pending |
| 53-01-04 | 01 | 0 | SRCH-10 | unit stub | `pytest tests/test_execution_export.py -x` | ❌ W0 | ⬜ pending |
| 53-02-01 | 02 | 1 | VIS-05 | unit | `pytest tests/test_scheduling_health.py::test_health_aggregate -x` | ❌ W0 | ⬜ pending |
| 53-02-02 | 02 | 1 | VIS-06 | unit | `pytest tests/test_scheduling_health.py::test_missed_fire_detection -x` | ❌ W0 | ⬜ pending |
| 53-03-01 | 03 | 1 | SRCH-06 | unit | `pytest tests/test_job_templates.py::test_create_template -x` | ❌ W0 | ⬜ pending |
| 53-03-02 | 03 | 1 | SRCH-07 | unit | `pytest tests/test_job_templates.py::test_template_visibility -x` | ❌ W0 | ⬜ pending |
| 53-03-03 | 03 | 1 | SRCH-08 | unit | `pytest tests/test_retention.py::test_pruner_respects_pinned -x` | ❌ W0 | ⬜ pending |
| 53-03-04 | 03 | 1 | SRCH-09 | unit | `pytest tests/test_retention.py::test_pin_unpin -x` | ❌ W0 | ⬜ pending |
| 53-03-05 | 03 | 1 | SRCH-10 | unit | `pytest tests/test_execution_export.py::test_csv_export -x` | ❌ W0 | ⬜ pending |
| 53-04-01 | 04 | 2 | VIS-05, VIS-06 | manual | Playwright: verify Health tab renders with correct counts | N/A | ⬜ pending |
| 53-05-01 | 05 | 2 | SRCH-06, SRCH-07 | manual | Playwright: save template, load template pre-populates form | N/A | ⬜ pending |
| 53-05-02 | 05 | 2 | SRCH-08, SRCH-09 | manual | Playwright: pin record, verify not pruned by pruner | N/A | ⬜ pending |
| 53-05-03 | 05 | 2 | SRCH-10 | manual | Playwright: download CSV, verify headers and content | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_scheduling_health.py` — stubs for VIS-05, VIS-06
- [ ] `puppeteer/tests/test_job_templates.py` — stubs for SRCH-06, SRCH-07
- [ ] `puppeteer/tests/test_retention.py` — stubs for SRCH-08, SRCH-09
- [ ] `puppeteer/tests/test_execution_export.py` — stubs for SRCH-10

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Health panel time window switcher renders correctly | VIS-05 | UI rendering requires browser | Navigate to /job-definitions → Health tab; verify 24h/7d/30d toggle works |
| Red health indicator shows for missed fires | VIS-06 | Requires scheduled job execution data | Create a job definition, let it fire, verify missed fire shows red indicator |
| Save as Template button pre-populates guided form | SRCH-06, SRCH-07 | React state crossing requires browser | Fill guided form, save as template, load template, verify all fields populated |
| CSV export downloads correctly | SRCH-10 | File download requires browser | Open job detail drawer, click Export CSV, verify download with correct columns |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
