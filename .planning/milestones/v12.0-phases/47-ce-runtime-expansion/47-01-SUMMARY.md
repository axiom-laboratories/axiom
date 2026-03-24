---
phase: 47-ce-runtime-expansion
plan: "01"
subsystem: node-execution
tags: [runtime, node, powershell, bash, tdd, containerfile]
dependency_graph:
  requires: []
  provides: [script-task-type, powershell-node-image, rt-test-scaffold]
  affects: [puppets/Containerfile.node, puppets/environment_service/node.py]
tech_stack:
  added: [PowerShell Core via Microsoft APT repo]
  patterns: [temp-file mount execution, runtime dispatch map, source inspection tests]
key_files:
  created:
    - puppeteer/tests/test_runtime_expansion.py
  modified:
    - puppets/Containerfile.node
    - puppets/environment_service/node.py
decisions:
  - "Temp-file mount pattern chosen over stdin (input_data) to support all three runtimes uniformly — bash and pwsh do not support stdin script execution as cleanly as Python"
  - "RUNTIME_EXT and RUNTIME_CMD dispatch maps defined inline in execute_task — keeps all runtime logic co-located, easy to extend in plan 02"
  - "python_script task_type branch removed entirely — no existing deployments per CONTEXT.md, clean break avoids dual-branch confusion"
  - "finally: block for tmp_path cleanup placed outside the try: so it runs even on RuntimeError from runtime_engine.run()"
metrics:
  duration: "~3 minutes"
  completed: "2026-03-22T16:51:14Z"
  tasks_completed: 3
  files_changed: 3
---

# Phase 47 Plan 01: CE Runtime Expansion — Node Foundation Summary

Node image ships PowerShell Core and the agent executes Python, Bash, and PowerShell scripts via a unified `script` task_type using temp-file container mounts with Ed25519 signature verification.

## What Was Built

### Task 1: Test scaffold (Wave 0, RED phase)

Created `puppeteer/tests/test_runtime_expansion.py` with 7 source-inspection tests covering all CE runtime expansion requirements (RT-01 through RT-07). Tests are intentionally RED for RT-04, RT-05, RT-07 (backend implementation deferred to plan 02).

**Test functions:**
- `test_containerfile_has_powershell` — asserts Microsoft APT repo method
- `test_bash_job_accepted` — asserts script branch handles bash with .sh extension
- `test_powershell_job_accepted` — asserts script branch handles powershell/pwsh with .ps1
- `test_node_script_execution` — asserts tmp_path, mount pattern, and finally cleanup
- `test_invalid_runtime_rejected` — RED (models.py runtime validator not yet added)
- `test_display_type_computed_serverside` — RED (job_service display_type not yet added)
- `test_scheduled_job_runtime_field` — RED (ScheduledJob.runtime column not yet added)

### Task 2: Containerfile.node — PowerShell Core (RT-03)

Extended the single `apt-get` RUN layer in `puppets/Containerfile.node` to:
1. Add `wget apt-transport-https gnupg` to initial package list
2. Download and register `packages-microsoft-prod.deb` for Debian 12
3. Run a second `apt-get update` to pick up the Microsoft repo
4. Install `powershell` (provides `pwsh` binary)
5. Remove `.deb` file in same layer to keep image size minimal

### Task 3: node.py unified script branch (RT-01, RT-02)

Replaced the `python_script` task_type block in `execute_task` with a unified `script` branch:

- `RUNTIME_EXT = {"python": "py", "bash": "sh", "powershell": "ps1"}`
- `RUNTIME_CMD = {python: lambda p: ["python", p], bash: ["bash", p], powershell: ["pwsh", p]}`
- Script written to `tmp_path = f"/tmp/job_{guid}.{ext}"`
- Mounted as `f"{tmp_path}:{tmp_path}:ro"` into the container
- `runtime_engine.run()` called with `command=cmd` (no `input_data`)
- Signature verification path unchanged (`public_key.verify(sig_bytes, script.encode())`)
- `finally:` block removes `tmp_path` if it exists

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| test_containerfile_has_powershell | GREEN | RT-03 satisfied |
| test_bash_job_accepted | GREEN | RT-01 satisfied |
| test_powershell_job_accepted | GREEN | RT-02 satisfied |
| test_node_script_execution | GREEN | RT-01/02 temp-file pattern |
| test_invalid_runtime_rejected | RED | RT-05, plan 02 |
| test_display_type_computed_serverside | RED | RT-04, plan 02 |
| test_scheduled_job_runtime_field | RED | RT-07, plan 02 |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
