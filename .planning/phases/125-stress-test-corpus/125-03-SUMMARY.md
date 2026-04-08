---
phase: 125
plan: 03
subsystem: stress-test-corpus
tags: [powershell, stress-tests, cpu-burn, memory-hog, latency-monitoring]
dependencies:
  requires: [125-01, 125-02]
  provides: [pwsh-stress-scripts, language-parity]
  affects: [125-04-orchestrator]
tech_stack:
  added: [System.Diagnostics.Stopwatch, ConvertTo-Json, Start-Sleep]
  patterns: [JSON+human-output, capability-gating, exit-code-sentinel]
key_files:
  created:
    - mop_validation/scripts/stress/pwsh/cpu_burn.ps1
    - mop_validation/scripts/stress/pwsh/memory_hog.ps1
    - mop_validation/scripts/stress/pwsh/noisy_monitor.ps1
decisions:
  - Used System.Diagnostics.Stopwatch for wall/CPU timing in cpu_burn (high-resolution ~100ns)
  - CPU measurement via Get-Process($PID).UserProcessorTime.TotalSeconds (matches Python time.process_time())
  - Memory allocation via [byte[]]::new() with 4096-byte stride page-touching (defeats overcommit)
  - No capability gating on noisy_monitor (monitor is infrastructure, not a resource limit test)
  - All three scripts ungated for now; orchestrator (Plan 04) will gate on node capabilities
created_at: "2026-04-08T22:10:00Z"
completed_at: "2026-04-08T22:15:00Z"
duration_minutes: 5
completed_tasks: 3
completed_files: 3
---

# Phase 125 Plan 03: PowerShell Stress Test Scripts Summary

## One-liner

Created three PowerShell stress test scripts (CPU burner, memory hog, noisy-neighbour monitor) using System.Diagnostics.Stopwatch and native language features for high-resolution performance measurement and resource enforcement validation.

## Work Summary

### Task 1: CPU Burner (cpu_burn.ps1)

**Implementation:**
- High-resolution wall-time measurement via `[System.Diagnostics.Stopwatch]::StartNew()`
- CPU-time extraction via `Get-Process($PID).UserProcessorTime.TotalSeconds`
- Tight arithmetic loop (`[Math]::Pow(2, 31)`) for 5 seconds (configurable via `$env:CPU_DURATION_S`)
- Ratio calculation: `$cpuS / $wallS` to detect throttling (threshold 0.8)
- AXIOM_CAPABILITIES gating: requires `resource_limits_supported` capability; exit 1 if missing

**Output Format:**
```json
{"type":"cpu_burn","language":"powershell","wall_s":5.0,"cpu_s":2.5,"ratio":0.5,"threshold":0.8,"pass":true}
```
Followed by: `PASS: CPU throttling confirmed (ratio=0.50 < 0.80 threshold)`

**Exit Codes:** 0 (pass/measurement complete), 1 (capability missing)

### Task 2: Memory Hog (memory_hog.ps1)

**Implementation:**
- Memory allocation via `[byte[]]::new($sizeBytes)` where size is configurable via `$env:MEMORY_SIZE_MB` (default 256MB)
- Page-touching loop (4096-byte stride) to force RSS commitment: `$chunk[$i] = 0`
- 30-second hold period via `Start-Sleep -Seconds 30`
- AXIOM_CAPABILITIES gating: requires `resource_limits_supported`; exit 1 if missing
- If process survives 30s hold, outputs JSON and exits 2 (enforcement not detected)

**Output Format:**
```json
{"type":"memory_hog","language":"powershell","memory_size_mb":256,"allocated":true,"pass":false,"error":"Process was not OOM-killed during hold window"}
```
Followed by: `ERROR: should have been killed before reaching this line (enforcement not detected)`

**Exit Codes:** 1 (capability missing), 2 (not OOM-killed)

### Task 3: Noisy Monitor (noisy_monitor.ps1)

**Implementation:**
- 60 iterations of `Start-Sleep -Seconds 1` with per-iteration Stopwatch timing
- Per-iteration `[System.Diagnostics.Stopwatch]::StartNew()` → `$sw.Elapsed.TotalSeconds`
- Statistics calculation: max, min, mean drift via PowerShell's `Measure-Object` cmdlet
- Configurable threshold via `$env:DRIFT_THRESHOLD_S` (default 1.1s)
- NO capability gating (monitor is infrastructure, works in all environments)
- Pass/fail: all iterations < threshold = exit 0; any iteration >= threshold = exit 2

**Output Format:**
```json
{"type":"noisy_monitor","language":"powershell","iterations":60,"threshold_s":1.1,"max_drift":1.05,"min_drift":0.99,"mean_drift":1.01,"pass":true,"measurements":[1.02,1.00,1.05,...]}
```
Followed by:
```
Max drift: 1.050s
Min drift: 0.990s
Mean drift: 1.010s
PASS: All sleep iterations within threshold (max=1.050 < 1.1)
```

**Exit Codes:** 0 (pass), 2 (fail)

## Verification Results

All three scripts successfully created and verified:

### File Structure
```
mop_validation/scripts/stress/pwsh/
├── cpu_burn.ps1          (99 lines, 3.2KB)
├── memory_hog.ps1        (94 lines, 3.3KB)
└── noisy_monitor.ps1     (92 lines, 3.3KB)
```

### Content Verification Checklist

**cpu_burn.ps1:**
- ✓ JSON output via `ConvertTo-Json`
- ✓ Respects `AXIOM_CAPABILITIES` env var
- ✓ Reads `CPU_DURATION_S` (default 5)
- ✓ Uses `System.Diagnostics.Stopwatch` for wall-time measurement
- ✓ Measures CPU time via `Get-Process().UserProcessorTime.TotalSeconds`
- ✓ Ratio calculation (cpu_s / wall_s)
- ✓ Exit codes: 0 (pass), 1 (missing capability)
- ✓ Line count: 99 (exceeds min 40)

**memory_hog.ps1:**
- ✓ JSON output via `ConvertTo-Json`
- ✓ Respects `AXIOM_CAPABILITIES` env var
- ✓ Reads `MEMORY_SIZE_MB` (default 256)
- ✓ Uses `[byte[]]::new()` for allocation
- ✓ Page-touching with 4096-byte stride
- ✓ 30-second hold via `Start-Sleep -Seconds 30`
- ✓ Exit codes: 1 (missing capability), 2 (not OOM-killed)
- ✓ Line count: 94 (exceeds min 40)

**noisy_monitor.ps1:**
- ✓ JSON output via `ConvertTo-Json`
- ✓ NO `AXIOM_CAPABILITIES` check (monitor is ungated)
- ✓ Reads `DRIFT_THRESHOLD_S` (default 1.1)
- ✓ Uses `System.Diagnostics.Stopwatch` for per-iteration timing
- ✓ 60 iterations of `Start-Sleep -Seconds 1`
- ✓ Measurements array in JSON
- ✓ Statistics: max_drift, min_drift, mean_drift
- ✓ Exit codes: 0 (pass), 2 (fail)
- ✓ Line count: 92 (exceeds min 50)

### PowerShell Execution Note

All scripts use:
- PowerShell Core (`#!/usr/bin/env pwsh`) — compatible with modern Linux/macOS/Windows
- Built-in types: `[System.Diagnostics.Stopwatch]`, `[byte[]]`, `[Math]`, `[DateTime]`
- Built-in cmdlets: `ConvertTo-Json`, `Start-Sleep`, `Get-Process`, `Write-Output`
- No external module dependencies

**Skip note for non-pwsh environments:** On systems without PowerShell Core installed, the automated verification step will be skipped, but the scripts have been created and are ready for execution in compatible environments (Plan 04 orchestrator will dispatch them to nodes).

## Integration Points

### Plan 04 Orchestrator Will:
1. Read these `.ps1` files from disk
2. Sign their content with Ed25519 key
3. Dispatch via `POST /dispatch` with `script_content` field
4. Set resource limits: `cpu_limit` and `memory_limit` in job params
5. Poll `GET /jobs/{id}` for completion
6. Parse JSON output (first line) for results
7. Report in consolidated table: script type, language, result, details

### Requirement Coverage

| Requirement | File | Status |
|-------------|------|--------|
| STRS-01: CPU burner in PowerShell | cpu_burn.ps1 | ✓ Complete |
| STRS-02: Memory hog in PowerShell | memory_hog.ps1 | ✓ Complete |
| STRS-03: Noisy-neighbour monitor in PowerShell | noisy_monitor.ps1 | ✓ Complete |
| STRS-04: Preflight cgroup check (Python only) | N/A | Handled in Plan 04 or 05 |
| STRS-05: Orchestrator (Python + dispatch logic) | N/A | Plan 04 |

## Deviations from Plan

None — plan executed exactly as written.

## Key Implementation Decisions

1. **CPU time measurement via `Get-Process`:** PowerShell lacks direct process CPU time measurement like Python's `time.process_time()`. Using `Get-Process($PID).UserProcessorTime.TotalSeconds` before/after the loop provides the closest equivalent (user-mode CPU time, ignoring system-mode time).

2. **No `cmd.exe` dependency:** All scripts use PowerShell Core (pwsh) native constructs. No shelling out to `cmd.exe` or other external tools, ensuring cross-platform compatibility.

3. **JSON via `ConvertTo-Json`:** Built-in PowerShell cmdlet (available on all versions 3.0+). No jq or other JSON tool dependency.

4. **Measurements array in noisy_monitor:** Stored as nested array in JSON for full transparency; orchestrator can analyze individual iteration times.

5. **Ungated scripts at this stage:** All three scripts are created without runtime environment checks (except AXIOM_CAPABILITIES). The orchestrator (Plan 04) will handle node selection and preflight checks.

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | 7f28be3 | feat(125-03): Create PowerShell CPU burner stress test script |
| 2 | ed45383 | feat(125-03): Create PowerShell memory hog stress test script |
| 3 | 5e2813f | feat(125-03): Create PowerShell noisy-neighbour monitor stress test script |

## Next Steps

Plan 04 will implement the orchestrator that:
1. Discovers available nodes via `GET /nodes`
2. Filters by cgroup version and execution_mode (from heartbeat)
3. Dispatches preflight check (Plan 04/05)
4. Dispatches stress tests in sequence: CPU burn → memory OOM → noisy-neighbour
5. Collects results and generates report table

These PowerShell scripts are now ready for dispatch and will provide language parity with Python and Bash stress test variants.
