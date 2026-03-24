---
phase: 49-pagination-filtering-and-search
plan: "04"
subsystem: api-routes
tags: [pagination, cursor, filtering, csv-export, nodes, tdd]
dependency_graph:
  requires: ["49-03"]
  provides: ["GET /jobs cursor+filters", "GET /jobs/export streaming CSV", "GET /nodes paginated", "JobService.list_nodes"]
  affects:
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/tests/test_pagination.py
tech_stack:
  added: []
  patterns: ["StreamingResponse CSV generator", "page-based pagination", "require_permission dependency", "TDD red-green"]
key_files:
  created: []
  modified:
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/tests/test_pagination.py
decisions:
  - "GET /jobs uses require_permission('jobs:read') instead of require_auth — consistent with EE RBAC; CE falls back gracefully via deps.py"
  - "GET /nodes returns {items,total,page,pages} envelope wrapping resp list — backward-compatible shape change (frontend reads items key)"
  - "JobService.list_nodes added to service layer rather than inline in route — enables the test_nodes_pagination stub to test directly without HTTP stack"
  - "Stats batch query scoped to page_node_ids only — avoids loading all-nodes stats when paginating large deployments (pitfall 6 from plan)"
  - "GET /jobs/export placed before GET /jobs/count to keep all static /jobs/* routes before parameterised /jobs/{guid}/* routes"
metrics:
  duration: "3 min"
  completed: "2026-03-22"
  tasks_completed: 2
  files_modified: 3
---

# Phase 49 Plan 04: API Route Layer — Cursor Pagination, 9-Axis Filters, CSV Export Summary

**One-liner:** Updated GET /jobs with 9-axis cursor filtering, new GET /jobs/export streaming CSV endpoint, and paginated GET /nodes returning {items,total,page,pages} envelope — all 13 test stubs now pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | TDD: Fill 5 remaining test stubs with real assertions | 731e71e | tests/test_pagination.py |
| 1 (GREEN) | Wire routes and add JobService.list_nodes | f3a854d | main.py, services/job_service.py |

## What Was Built

### GET /jobs (updated)
Replaced `skip` + bare `status` with full cursor-based pagination signature:
- `cursor`, `limit`, `status`, `runtime`, `task_type`, `node_id`, `tags` (comma-separated string → list), `created_by`, `date_from`, `date_to`, `search`
- Calls `JobService.list_jobs()` (implemented in Plan 03) and returns the `{items, total, next_cursor}` envelope directly
- Auth upgraded from `require_auth` to `require_permission("jobs:read")`

### GET /jobs/export (new)
Streaming CSV endpoint using FastAPI `StreamingResponse`:
- Same 9-axis filter params as GET /jobs
- Delegates to `JobService.list_jobs_for_export()` (Plan 03) with 10,000 row cap
- CSV generator yields header row then one row per job — memory-efficient for large exports
- `Content-Disposition: attachment; filename=jobs-export.csv` header

### GET /nodes (updated)
Added `page: int = 1` and `page_size: int = 25` query params:
- Total count query runs first (before pagination offset)
- Paginated node select with `.offset((page-1)*page_size).limit(page_size)`
- Stats batch query scoped to current page's node IDs only
- Returns `{items: resp, total, page, pages}` envelope

### JobService.list_nodes (new)
New `@staticmethod` in `job_service.py` that implements the pure service-layer paginated node list. Used by `test_nodes_pagination` directly without needing the HTTP stack.

### Imports added to main.py
- `csv`, `io`, `math` (stdlib)
- `StreamingResponse` from fastapi.responses
- `require_permission` from `.deps`

## Test Results

All 13 pagination test stubs pass:
- `test_cursor_pagination` — envelope shape
- `test_total_count_stable` — stable totals across 3 pages
- `test_no_duplicates` — 105 GUIDs, no repeats
- `test_nodes_pagination` — {items,total,page,pages} with 30 nodes, page_size=10
- `test_filter_status` — COMPLETED filter
- `test_filter_tags_or` — OR tag logic
- `test_filter_compose_and` — AND across axes
- `test_scheduled_job_name_auto_populate` — Job.name stamped from ScheduledJob.name
- `test_search_by_name` — ILIKE name search
- `test_search_by_guid` — partial GUID prefix
- `test_export_csv_headers` — all 12 required keys in export row
- `test_export_respects_filters` — COMPLETED filter excludes FAILED rows
- `test_export_max_rows` — limit=10 caps at 10 rows

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `puppeteer/agent_service/main.py` updated with GET /jobs, GET /jobs/export, GET /nodes
- [x] `puppeteer/agent_service/services/job_service.py` updated with list_nodes
- [x] `puppeteer/tests/test_pagination.py` all 5 stubs filled with real assertions
- [x] Commit 731e71e exists (RED: test stubs)
- [x] Commit f3a854d exists (GREEN: implementation)
- [x] All 13 pagination tests pass

## Self-Check: PASSED
