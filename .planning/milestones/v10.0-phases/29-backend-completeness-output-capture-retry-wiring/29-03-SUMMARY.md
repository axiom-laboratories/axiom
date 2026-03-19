---
phase: 29-backend-completeness-output-capture-retry-wiring
plan: "03"
subsystem: node-execution
tags:
  - output-capture
  - script-hash
  - direct-mode-removal
  - timeout-wiring
dependency_graph:
  requires:
    - 29-01
    - 29-02
  provides:
    - runtime-without-direct-mode
    - node-script-hash
    - node-timeout-minutes
  affects:
    - mop_validation/local_nodes
tech_stack:
  added: []
  patterns:
    - AST source inspection for testing module-level guard functions
    - asyncio.wait_for for subprocess timeout enforcement
key_files:
  created:
    - puppeteer/tests/test_direct_mode_removal.py (implemented from stub)
  modified:
    - puppets/environment_service/runtime.py
    - puppets/environment_service/node.py
    - puppeteer/tests/test_output_capture.py
    - mop_validation/local_nodes/node_alpha/node-compose.yaml
    - mop_validation/local_nodes/node_beta/node-compose.yaml
    - mop_validation/local_nodes/node_gamma/node-compose.yaml
decisions:
  - AST-based source extraction used to test _check_execution_mode() without triggering full module import side effects
  - timeout parameter added to ContainerRuntime.run() with asyncio.wait_for wrapping proc.communicate()
  - script_hash computed after signature verification passes, before runtime.run() — attestation invariant preserved
metrics:
  duration: 4 minutes
  completed: "2026-03-18"
  tasks_completed: 2
  files_changed: 7
  requirements_closed:
    - OUTPUT-01
---

# Phase 29 Plan 03: Direct Mode Removal + Output Wiring Summary

Remove direct execution mode completely, add startup guard, wire script_hash computation into node.py execute_task(), respect timeout_minutes from WorkResponse, update mop_validation compose files.

## Tasks Completed

### Task 1: Remove direct mode from runtime.py and add node.py startup guard
**Commit:** a9c9282

- Deleted `EXECUTION_MODE=direct` branch from `ContainerRuntime.detect_runtime()` in runtime.py
- Deleted the entire direct-mode subprocess block from `ContainerRuntime.run()` in runtime.py
- Added `_check_execution_mode()` function to node.py called at module level (after load_dotenv, before class definitions)
- RuntimeError raised immediately: "EXECUTION_MODE=direct is no longer supported. Use EXECUTION_MODE=docker, podman, or auto."
- Implemented `test_direct_mode_raises_on_startup` using AST source extraction + subprocess (safe from module side effects)
- Added `test_runtime_py_has_no_direct_execution_path` for string-level verification

### Task 2: Wire script_hash and timeout_minutes into node execute_task()
**Commits:** fcebcb4 (main repo), 64a24ab (mop_validation)

- Added `import hashlib` to node.py
- Added `timeout_minutes` extraction from job dict + `timeout_secs = (timeout_minutes * 60) if timeout_minutes else 30`
- Computed `script_hash = hashlib.sha256(script.encode('utf-8')).hexdigest()` after signature verification, before runtime call
- Passed `timeout=timeout_secs` to `runtime_engine.run()`
- Added `timeout: Optional[int] = 30` parameter to `ContainerRuntime.run()` signature
- Wrapped `proc.communicate()` with `asyncio.wait_for(..., timeout=timeout)` — kills container on timeout
- Passed `script_hash=script_hash` to `report_result()`, added it to JSON payload as `"script_hash": script_hash`
- Updated `report_result()` signature to accept `script_hash=None`
- Changed `EXECUTION_MODE=direct` to `EXECUTION_MODE=docker` in all three mop_validation compose files
- Implemented `test_node_computes_script_hash` via source inspection (confirms import, sha256 call, ordering, forwarding)

## Test Results

All 18 phase-29 tests pass:
- `test_output_capture.py` — 7 tests (including test_node_computes_script_hash now live)
- `test_retry_wiring.py` — 9 tests
- `test_direct_mode_removal.py` — 2 tests

6 pre-existing collection errors in unrelated test files (test_bootstrap_admin, test_intent_scanner, test_lifecycle_enforcement, test_smelter, test_staging, test_tools) — out of scope, pre-existing baseline.

## Deviations from Plan

None — plan executed exactly as written.

The plan suggested using subprocess + exec of extracted source for the startup guard test. The implemented approach uses Python's `ast` module to find the function definition in source and extract it cleanly, then runs it in a subprocess with EXECUTION_MODE=direct — this is robust and avoids any import side effects.

## Self-Check

Files exist:
- `puppets/environment_service/runtime.py` — FOUND
- `puppets/environment_service/node.py` — FOUND
- `puppeteer/tests/test_direct_mode_removal.py` — FOUND
- `puppeteer/tests/test_output_capture.py` — FOUND

Commits exist:
- `a9c9282` — Task 1 (direct mode removal + startup guard)
- `fcebcb4` — Task 2 (script_hash + timeout wiring)
- `64a24ab` — Task 2 (mop_validation compose files, separate repo)

## Self-Check: PASSED
