---
phase: 49
slug: pagination-filtering-and-search
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_pagination.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds (quick) / ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_pagination.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 0 | SRCH-01 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_cursor_pagination -x` | ❌ W0 | ⬜ pending |
| 49-01-02 | 01 | 0 | SRCH-01 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_total_count_stable -x` | ❌ W0 | ⬜ pending |
| 49-01-03 | 01 | 0 | SRCH-01 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_no_duplicates -x` | ❌ W0 | ⬜ pending |
| 49-01-04 | 01 | 0 | SRCH-02 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_nodes_pagination -x` | ❌ W0 | ⬜ pending |
| 49-01-05 | 01 | 0 | SRCH-03 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_filter_status -x` | ❌ W0 | ⬜ pending |
| 49-01-06 | 01 | 0 | SRCH-03 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_filter_tags_or -x` | ❌ W0 | ⬜ pending |
| 49-01-07 | 01 | 0 | SRCH-03 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_filter_compose_and -x` | ❌ W0 | ⬜ pending |
| 49-01-08 | 01 | 0 | SRCH-04 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_scheduled_job_name_auto_populate -x` | ❌ W0 | ⬜ pending |
| 49-01-09 | 01 | 0 | SRCH-04 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_search_by_name -x` | ❌ W0 | ⬜ pending |
| 49-01-10 | 01 | 0 | SRCH-04 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_search_by_guid -x` | ❌ W0 | ⬜ pending |
| 49-01-11 | 01 | 0 | SRCH-05 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_export_csv_headers -x` | ❌ W0 | ⬜ pending |
| 49-01-12 | 01 | 0 | SRCH-05 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_export_respects_filters -x` | ❌ W0 | ⬜ pending |
| 49-01-13 | 01 | 0 | SRCH-05 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_export_max_rows -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_pagination.py` — stubs for SRCH-01 through SRCH-05 (cursor pagination, nodes pagination, filter composition, name search, GUID search, CSV export)
- [ ] No new conftest needed — existing async DB fixture pattern in `tests/test_tools.py` and `tests/test_runtime_expansion.py` can be reused

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Filter bar "More filters" expand/collapse UI | SRCH-03 | React UI interaction; Playwright would be needed | Open Jobs view, click "More filters", confirm date range/node/tags/created-by inputs appear |
| Active filter chips dismiss correctly | SRCH-03 | UI state management | Apply 2+ filters, click ✕ on a chip, confirm filter is removed and list refreshes |
| "N new jobs" banner on WebSocket job:created while paged | SRCH-01 | Requires live WebSocket event + paginated state | Load 50+ jobs, navigate to page 2, trigger a new job, confirm banner appears |
| CSV file downloads correctly in browser | SRCH-05 | File download requires browser | Click Export button with filters applied, confirm .csv file downloads with correct filename |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
