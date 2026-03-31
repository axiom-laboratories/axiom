---
phase: 99
plan: "99-01"
subsystem: scheduler
tags: [scheduler, apscheduler, diff-based-sync, create_task, event-loop, fire-log]
dependency_graph:
  requires: [phase-96-01, phase-97-01, phase-98-01]
  provides: [SCHED-01, SCHED-02, SCHED-03]
  affects: [scheduler_service, get_scheduling_health, ScheduledFireLog]
tech_stack:
  added: []
  patterns:
    - diff-based scheduler sync (add/remove vs. remove_all/re-add)
    - synchronous APScheduler callback wrapping asyncio.create_task
    - done-callback for fire_log failure tracking
key_files:
  created:
    - puppeteer/tests/test_scheduler_phase99.py
  modified:
    - puppeteer/agent_service/services/scheduler_service.py
decisions:
  - "_make_cron_callback returns a plain synchronous closure — APScheduler does not need to await it, and it schedules the coroutine as a non-blocking asyncio task, solving the cron burst event-loop delay"
  - "Internal jobs identified by id.startswith('__') — simple, self-documenting convention consistent with existing naming (__prune_node_stats__, etc.)"
  - "get_scheduling_health() 'failed' fire_log rows count as both fired and failed — a failed attempt is an attempted fire, maintaining the fired total for accuracy"
  - "test_foundry_mirror.py and 5 other test files have pre-existing import errors (Blueprint, intent_scanner, etc.) unrelated to Phase 99 — excluded from this plan's test run and logged to deferred items"
metrics:
  duration: "3 minutes"
  completed_date: "2026-03-31"
  tasks_completed: 5
  files_modified: 2
  tests_added: 9
  tests_passing: 9
---

# Phase 99 Plan 01: Diff-based sync and create_task() dispatcher Summary

Diff-based sync_scheduler() protecting internal jobs + synchronous create_task() cron callback with done-callback fire_log failure tracking.

## What Was Built

**scheduler_service.py** received three connected improvements:

1. **Diff-based `sync_scheduler()`** (SCHED-01 + SCHED-02): The old `remove_all_jobs()` / re-add pattern was replaced with a diff algorithm. The method now builds a desired set from DB (active jobs with valid 5-part cron), builds a current set from APScheduler excluding `__`-prefixed IDs, computes to_remove and to_add_or_update sets, then applies the minimal changes with `replace_existing=True`. Internal maintenance jobs (`__prune_node_stats__`, `__prune_execution_history__`, `__dispatch_timeout_sweeper__`) survive any number of sync calls.

2. **Synchronous `_make_cron_callback()` + done-callback** (SCHED-03): APScheduler cron fires now call a synchronous closure that calls `asyncio.get_event_loop().create_task(execute_scheduled_job(...))` and returns immediately. The task gets a done-callback (`_on_cron_task_done`) that, on exception, schedules `_mark_latest_fire_failed()` to update the most recent `ScheduledFireLog` row to `status='failed'`. The `execute_scheduled_job()` coroutine body is unchanged.

3. **`get_scheduling_health()` updated** (SCHED-03): `'failed'` fire_log rows now count in both `fired` (attempted) and `failed` aggregates. Previously this status was a TODO comment.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 99-01-W0-01 | Create test stubs (9 failing tests) | eeac89c |
| 99-01-01 | Replace sync_scheduler() with diff-based algorithm | 74044c8 |
| 99-01-02 | Add _make_cron_callback(), _on_cron_task_done(), _mark_latest_fire_failed() | 74044c8 |
| 99-01-03 | Update get_scheduling_health() to count 'failed' fire_log rows | 74044c8 |
| 99-01-04 | Implement all 9 test bodies — all pass | 3402ef4 |
| 99-01-05 | Full regression test run — 30 passed, 1 skipped (Postgres-only) | verified |

## Verification Results

1. `grep remove_all_jobs scheduler_service.py` — no output (PASS)
2. `grep replace_existing=True scheduler_service.py` — line 169 in sync_scheduler body (PASS)
3. `grep create_task scheduler_service.py` — lines 182, 199 (PASS)
4. `grep startswith scheduler_service.py` — line 147 in sync_scheduler (PASS)
5. `pytest tests/test_scheduler_phase99.py -v` — 9 passed (PASS)
6. `pytest tests/test_foundation_phase96.py tests/test_pool_phase97.py tests/test_dispatch_correctness_phase98.py` — 21 passed, 1 skipped (PASS)

## Deviations from Plan

### Pre-existing Out-of-Scope Issues (Not Fixed)

6 test files have pre-existing import errors that were present before Phase 99 began:
- `test_foundry_mirror.py` — `ImportError: cannot import name 'Blueprint' from agent_service.db`
- `test_intent_scanner.py` — `ModuleNotFoundError: No module named 'intent_scanner'`
- `test_lifecycle_enforcement.py`, `test_smelter.py`, `test_staging.py`, `test_tools.py` — various pre-existing import failures

All confirmed to exist before this plan's changes via `git stash` verification. Per scope boundary rules, these were not touched and are logged here for deferred resolution.

None of the 3 implementation tasks required any deviation from the plan spec.

## Self-Check: PASSED

- FOUND: puppeteer/tests/test_scheduler_phase99.py
- FOUND: puppeteer/agent_service/services/scheduler_service.py
- FOUND: .planning/phases/99-scheduler-hardening/99-01-SUMMARY.md
- FOUND commit eeac89c (Wave 0 stubs)
- FOUND commit 74044c8 (implementation)
- FOUND commit 3402ef4 (test implementations)
