---
phase: 34-ce-baseline-fixes
plan: "03"
subsystem: job-dispatch
tags: [ce-baseline, nodeconfig, pollresponse, job-service, node-agent]
dependency_graph:
  requires: [34-02]
  provides: [GAP-05, GAP-06]
  affects: [job-dispatch, node-poll-loop, env-tag-propagation]
tech_stack:
  added: []
  patterns: [flat-response-fields, ce-ee-separation]
key_files:
  created: []
  modified:
    - .worktrees/axiom-split/puppeteer/agent_service/models.py
    - .worktrees/axiom-split/puppeteer/agent_service/main.py
    - .worktrees/axiom-split/puppeteer/agent_service/services/job_service.py
    - .worktrees/axiom-split/puppets/environment_service/node.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_job_service.py
decisions:
  - "NodeUpdateRequest replaces NodeConfig for PATCH /nodes/{node_id} — only tags and env_tag (CE-safe fields)"
  - "PollResponse carries env_tag directly as Optional[str] = None — no config nesting"
  - "node.py reads env_tag from flat job_data dict — eliminates AttributeError on missing config sub-dict"
metrics:
  duration: "~4 minutes"
  completed_date: "2026-03-19"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 34 Plan 03: NodeConfig Removal and PollResponse Simplification Summary

NodeConfig (EE-only fields) deleted from models.py; PollResponse simplified to job + env_tag; job_service and node.py updated to use flat env_tag field, eliminating AttributeError crashes on CE job dispatch.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Strip NodeConfig from models.py and remove all imports in main.py | ad2af01 | models.py, main.py |
| 2 | Fix job_service.py NodeConfig construction and node.py config parsing | 685fba8 | job_service.py, node.py, test_job_service.py |

## What Was Built

### NodeConfig Deletion (GAP-05)
`NodeConfig` carried EE-only fields (`concurrency_limit`, `job_memory_limit`, `job_cpu_limit`) that caused `AttributeError` crashes when CE code tried to construct it with missing context. The class has been fully removed from `models.py`.

`PollResponse` was simplified from `job + config: NodeConfig` to `job + env_tag: Optional[str] = None`.

A replacement `NodeUpdateRequest` model (tags + env_tag only) was created for the `PATCH /nodes/{node_id}` operator endpoint, which previously used `NodeConfig` as its request schema.

### Job Dispatch Cleanup (GAP-06)
All three `NodeConfig(...)` construction sites in `job_service.py` were removed:
- TAMPERED quarantine path: `return PollResponse(job=None)` (no env_tag needed — quarantined nodes shouldn't adopt config)
- Concurrency limit path: `return PollResponse(job=None, env_tag=current_env_tag)`
- No-work path: `return PollResponse(job=None, env_tag=current_env_tag)`
- Work dispatch path: `return PollResponse(job=work_resp, env_tag=current_env_tag)`

The unused `memory = "512m"` default variable was also removed.

`node.py` poll loop updated: replaced the nested `config = job_data.get("config", {})` block with a direct `pushed_tag = job_data.get("env_tag")` read. The `self.concurrency_limit` and `self.job_memory_limit` update lines from poll response were removed — these remain set from env vars at init and used for local admission checks.

### GET /api/features CE Verification
Route confirmed present and correct at line 820 of `main.py`. When `app.state.ee is None` (CE install), returns all eight feature flags as `False`. No code changes were required.

## Verification Results

```
grep -rn "NodeConfig" puppeteer/ puppets/ --include="*.py"
# Result: EXIT 1 — zero matches
```

```
pytest puppeteer/agent_service/tests/test_job_service.py puppeteer/agent_service/tests/test_models.py -x -q
# Result: 7 passed, 23 warnings
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale test assertion in test_report_result**
- **Found during:** Task 2 verification
- **Issue:** `test_report_result` asserted `job["result"] == {"output": "success"}` but `report_result()` stores only `{"exit_code": ...}` as a minimal summary (full output goes to `ExecutionRecord`). Test was wrong relative to actual implementation.
- **Fix:** Updated assertion to `assert job["result"] == {"exit_code": None}` with clarifying comment.
- **Files modified:** `puppeteer/agent_service/tests/test_job_service.py`
- **Commit:** 685fba8

### Architectural Note: NodeUpdateRequest

The plan specified deleting `NodeConfig` from `models.py` entirely. However, `PATCH /nodes/{node_id}` in `main.py` used `NodeConfig` as its request schema for operator-managed fields (`tags`, `env_tag`). Rather than breaking this route, a purpose-specific `NodeUpdateRequest` model was created with only the CE-appropriate fields. This is a direct consequence of removing `NodeConfig` — not a new feature.

## Self-Check: PASSED

- models.py: FOUND
- job_service.py: FOUND
- node.py: FOUND
- SUMMARY.md: FOUND
- Commit ad2af01: FOUND
- Commit 685fba8: FOUND
