---
phase: 49-pagination-filtering-and-search
plan: "03"
subsystem: job-service
tags: [pagination, cursor, filtering, search, export]
dependency_graph:
  requires: ["49-02"]
  provides: ["list_jobs-cursor-envelope", "list_jobs_for_export", "9-axis-filter-helper"]
  affects: ["puppeteer/agent_service/services/job_service.py"]
tech_stack:
  added: []
  patterns: ["cursor pagination", "filter composition via SQLAlchemy .where() chaining", "TDD red-green"]
key_files:
  created: []
  modified:
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/tests/test_pagination.py
decisions:
  - "Cursor direction: ORDER BY created_at DESC, guid DESC — cursor WHERE uses < not >, matching descending direction"
  - "Total count query runs BEFORE cursor filter — prevents total drifting between pages"
  - "Tags filter uses LIKE '%\"tag\"%' with JSON-quoted match — avoids substring collisions (e.g. 'gpu' in 'gpu-large')"
  - "_build_job_filter_queries is a @staticmethod that takes both queries — returns tuple to avoid duplication between list_jobs and list_jobs_for_export"
  - "73 pre-existing test failures confirmed unrelated to this plan's changes (EE modules, trigger service)"
metrics:
  duration: "3 min"
  completed: "2026-03-22"
  tasks_completed: 1
  files_modified: 2
---

# Phase 49 Plan 03: Job Service Cursor Pagination + 9-Axis Filters Summary

**One-liner:** Cursor-paginated list_jobs returning {items, total, next_cursor} with 9 composable filter axes and metadata-only list_jobs_for_export.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | TDD: Add failing tests for cursor pagination and filters | 8dc809b | tests/test_pagination.py |
| 1 (GREEN) | Implement list_jobs cursor pagination + list_jobs_for_export | 5c8b929 | services/job_service.py |

## What Was Built

### Module-level helpers
- `_encode_cursor(created_at, guid) -> str` — base64 urlsafe JSON encode of `{ts, guid}`
- `_decode_cursor(cursor) -> (datetime, str)` — decode cursor back to sortable values

### JobService._build_job_filter_queries
A shared private static method that applies all 9 filter axes (status, runtime, task_type, node_id, tags, created_by, date_from, date_to, search) to both the items query and the count query. All axes compose with AND; the tags axis uses OR within itself. Returns `(query, count_query)`.

### JobService.list_jobs (rewritten)
New signature adds cursor and 8 new filter parameters. Returns `{"items": List[dict], "total": int, "next_cursor": Optional[str]}`. Key implementation details:
- Count query runs BEFORE cursor filter — total is stable across "load more" interactions
- Cursor WHERE: `OR(created_at < ts, AND(created_at == ts, guid < guid_val))` — correct for DESC ordering
- next_cursor is only set when exactly `limit` rows returned
- Response dicts now include `name`, `created_by`, `created_at`, `runtime`

### JobService.list_jobs_for_export (new)
Flat metadata-only list capped at 10,000 rows by default. Uses the same `_build_job_filter_queries` helper. Returns dicts with: guid, name, status, task_type, display_type, runtime, node_id, created_at, started_at, completed_at, duration_seconds, target_tags. No payload content or secrets exposed.

## Test Results

8 of 13 pagination test stubs converted to real assertions and passing:
- `test_cursor_pagination` — {items, total, next_cursor} envelope shape
- `test_total_count_stable` — total stays consistent across 3 pages of 105 jobs
- `test_no_duplicates` — 105 GUIDs, no repeats across pages
- `test_filter_status` — status=COMPLETED excludes FAILED/PENDING
- `test_filter_tags_or` — tags=["gpu","linux"] returns 2 jobs (OR logic)
- `test_filter_compose_and` — status+runtime filters return 1 of 4 jobs
- `test_search_by_name` — ILIKE match on job.name
- `test_search_by_guid` — partial GUID prefix match

Remaining 5 stubs (`test_nodes_pagination`, `test_scheduled_job_name_auto_populate`, `test_export_csv_headers`, `test_export_respects_filters`, `test_export_max_rows`) kept as `pytest.fail("not implemented")` for Plans 04 and 05.

## Deviations from Plan

None — plan executed exactly as written. The 73 pre-existing test failures in the broader suite (EE-only modules, trigger service) were confirmed pre-existing via git stash comparison and are out of scope for this plan.

## Self-Check

- [x] `puppeteer/agent_service/services/job_service.py` modified with new list_jobs and list_jobs_for_export
- [x] `puppeteer/tests/test_pagination.py` updated with real assertions
- [x] Commit 8dc809b exists (RED: failing tests)
- [x] Commit 5c8b929 exists (GREEN: implementation)
- [x] 8 target tests pass
- [x] No regressions in passing test suite

## Self-Check: PASSED
