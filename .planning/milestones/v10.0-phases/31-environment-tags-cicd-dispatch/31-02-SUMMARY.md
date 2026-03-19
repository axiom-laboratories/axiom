---
phase: 31-environment-tags-cicd-dispatch
plan: "02"
subsystem: job-dispatch
tags: [env-tag, job-routing, heartbeat, scheduler, node]
dependency_graph:
  requires: [31-01]
  provides: [ENVTAG-02-runtime]
  affects: [job_service, scheduler_service, node]
tech_stack:
  added: []
  patterns:
    - env_tag column check in candidate loop after env: prefix guard
    - env_tag storage in receive_heartbeat() via dedicated column (not SEC-02 tag stripping path)
    - env_tag propagation from ScheduledJob to Job in execute_scheduled_job()
    - ENV_TAG env var read per heartbeat iteration for live reload without container restart
key_files:
  created: []
  modified:
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/services/scheduler_service.py
    - puppets/environment_service/node.py
decisions:
  - pull_work env_tag guard placed AFTER existing env: prefix isolation block — backward compat preserved; new column check is additive
  - node.env_tag overwritten on every heartbeat — node.py is source of truth; operator override deferred to Phase 32 (ENVTAG-03)
  - ENV_TAG read inside heartbeat_loop() per-iteration — live reload without container restart
  - SEC-02 comment updated but stripping logic untouched — env_tag column is a separate concern from free-text tag list
metrics:
  duration_seconds: 133
  completed_date: "2026-03-18"
  tasks_completed: 2
  files_modified: 3
---

# Phase 31 Plan 02: env_tag Wiring — job_service, scheduler_service, node.py Summary

**One-liner:** ENV_TAG env var flows from node.py heartbeat through receive_heartbeat() storage into pull_work() case-insensitive column filter, with cron job inheritance via execute_scheduled_job().

## What Was Built

Three targeted changes completing the ENVTAG-02 runtime behaviour:

1. **`job_service.py` — `pull_work()` candidate loop:** Added conditional env_tag column check after the existing `env:` prefix isolation block. If `candidate.env_tag` is set, the node's `env_tag` is compared case-insensitively via `.upper()`. `None` job env_tag bypasses the filter entirely (env-untagged jobs remain dispatchable to any node).

2. **`job_service.py` — `receive_heartbeat()`:** Added `node.env_tag = hb.env_tag` after the SEC-02 tag sanitisation line. The value is already normalised to uppercase by the `HeartbeatPayload` validator (from Plan 31-01). Stored in the dedicated `Node.env_tag` column — not subject to SEC-02 free-text stripping.

3. **`scheduler_service.py` — `execute_scheduled_job()`:** Added `env_tag=s_job.env_tag` to the `Job(...)` constructor call so cron-fired jobs inherit the env_tag from their `ScheduledJob` definition.

4. **`node.py` — `heartbeat_loop()`:** Added `env_tag = os.getenv("ENV_TAG")` inside the loop body (per-iteration read for live reload) and included `"env_tag": env_tag` in the heartbeat payload dict.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Wire env_tag filter into pull_work() and storage into receive_heartbeat() | 2209a6e | job_service.py |
| 2 | Propagate env_tag in scheduler_service and add ENV_TAG to node.py | e780fa1 | scheduler_service.py, node.py |

## Verification

All 11 `test_env_tag.py` tests pass:
- 3 DB column tests (ENVTAG-01, carried from Plan 31-01)
- 2 Pydantic normalisation tests (ENVTAG-01, carried)
- 3 pull_work source-inspection tests (ENVTAG-02, newly GREEN in this plan)
- 3 dispatch model tests (ENVTAG-04, carried)

Full test suite (tests that can be collected) — 49 passed, 0 failed. The 6 collection errors (`test_bootstrap_admin`, `test_intent_scanner`, `test_lifecycle_enforcement`, `test_smelter`, `test_staging`, `test_tools`) are pre-existing and unrelated to this plan.

`grep -n "env_tag" puppeteer/agent_service/services/job_service.py` confirms env_tag lines in both `pull_work()` (lines 326-331) and `receive_heartbeat()` (lines 408, 431).

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- job_service.py: FOUND
- scheduler_service.py: FOUND
- node.py: FOUND
- commit 2209a6e: FOUND
- commit e780fa1: FOUND
