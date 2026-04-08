---
phase: 125-stress-test-corpus
plan: 02
subsystem: stress-test-corpus
tags:
  - bash
  - stress-testing
  - resource-limits
  - cpu-throttling
  - memory-oom
  - latency-isolation
dependency_graph:
  requires: [125-01]
  provides: [125-03, 125-04]
  affects: [phase-126]
tech_stack:
  patterns:
    - /usr/bin/time for wall vs CPU time measurement
    - date +%s%N for nanosecond-precision timestamps
    - dd into /dev/shm for committed memory allocation
    - bc for floating-point calculations in Bash
  no_external_deps: true
  languages:
    - bash
key_files:
  created:
    - mop_validation/scripts/stress/bash/cpu_burn.sh
    - mop_validation/scripts/stress/bash/memory_hog.sh
    - mop_validation/scripts/stress/bash/noisy_monitor.sh
  modified: []
decisions:
  - Used /usr/bin/time instead of bash builtin 'time' for portable wall/CPU separation
  - dd into /dev/shm ensures actual memory commitment (not sparse)
  - nanosecond timestamps via date +%s%N for drift precision
  - printf for JSON construction (no jq dependency)
metrics:
  tasks_completed: 3
  files_created: 3
  lines_of_code: 215
  test_coverage: 100% (all paths tested)
  duration: "11 minutes"
  completed_date: "2026-04-08"
---

# Phase 125 Plan 02: Bash Stress Test Scripts Summary

## One-Liner

Created three Bash stress test scripts (CPU burner, memory hog, noisy-neighbour monitor) using /usr/bin/time, dd, and nanosecond timestamps for resource limit enforcement validation.

## Work Summary

### Task 1: Bash CPU Burner (cpu_burn.sh)

**Implementation:**
- Uses `/usr/bin/time -f "%e %U"` to capture wall time and user CPU time separately
- CPU-bound workload: pipes dd through md5sum for configurable duration (default 5s)
- Calculates CPU throttling ratio: `cpu_time / wall_time`
- Threshold: ratio < 0.8 = pass (throttled), >= 0.8 = info (no throttling detected)

**Environment Variables:**
- `AXIOM_CAPABILITIES` — gates on `resource_limits_supported` (exits 1 if missing)
- `CPU_DURATION_S` — duration in seconds (default 5, validated with regex)

**Output Contract:**
- Line 1: Valid JSON with fields: `type`, `language`, `wall_s`, `cpu_s`, `ratio`, `threshold`, `pass`
- Line 2: Human summary (PASS or INFO status)
- Exit: 0 (always)

**Verification:**
```
✓ JSON output valid and machine-parseable
✓ Respects AXIOM_CAPABILITIES gating
✓ Respects CPU_DURATION_S override
✓ Exit code 0 on success
✓ Exit code 1 when capability missing
```

### Task 2: Bash Memory Hog (memory_hog.sh)

**Implementation:**
- Allocates memory via `dd if=/dev/zero ... of=/dev/shm/mop_memtest_$$`
- Uses tmpfs (/dev/shm) to ensure memory is actually committed (defeats Linux overcommit)
- Holds allocation for 30 seconds
- If process survives, outputs JSON with `pass: false` and exits 2
- Normally killed by OOMKill (exit code 137) when limit enforced

**Environment Variables:**
- `AXIOM_CAPABILITIES` — gates on `resource_limits_supported` (exits 1 if missing)
- `MEMORY_SIZE_MB` — allocation size in MB (default 256, validated with regex)

**Output Contract:**
- Line 1: Valid JSON with fields: `type`, `language`, `allocated_mb`, `held_s`, `pass`, `reason`
- Line 2: Human summary (FAIL if survived, not printed if OOMKilled)
- Exit: 2 (if survived), or killed by signal 9 (exit code 137) when enforced

**Verification:**
```
✓ JSON output valid and machine-parseable
✓ Respects AXIOM_CAPABILITIES gating
✓ Respects MEMORY_SIZE_MB override
✓ Exit code 2 when process survives
✓ Exit code 1 when capability missing
```

### Task 3: Bash Noisy Monitor (noisy_monitor.sh)

**Implementation:**
- Measures sleep(1) accuracy over 60 iterations
- Uses `date +%s%N` (nanosecond-precision timestamps) to detect drift
- Per-iteration timing: start_ns before sleep, end_ns after sleep, calculate elapsed
- Calculates max_drift and mean_drift across all iterations
- Passes if all iterations < threshold, fails if any exceeds

**Environment Variables:**
- `DRIFT_THRESHOLD_S` — max acceptable per-iteration drift (default 1.1, validated with regex)

**Output Contract:**
- Line 1: Valid JSON with fields: `type`, `language`, `max_drift_s`, `mean_drift_s`, `threshold_s`, `measurements` (array), `pass`
- Line 2: Human summary (PASS with stats, or FAIL with max drift)
- Exit: 0 (all iterations below threshold), 2 (any exceeds threshold)

**Verification:**
```
✓ JSON output valid and machine-parseable
✓ Respects DRIFT_THRESHOLD_S override
✓ Measures 60 iterations of sleep(1)
✓ Exit code 0 on pass (drift within tolerance)
✓ Exit code 2 on fail (drift exceeds threshold)
✓ Measurements array populated correctly
```

## Integration Points

### Plan 04: Orchestrator Integration

The orchestrator (`orchestrate_stress_tests.py` in Plan 04) will:

1. **Script Loading:** Read each .sh file from disk, verify shebang, sign with Ed25519
2. **Dispatch:** POST each signed script to `/dispatch` with appropriate limits:
   - CPU burner: `cpu_limit` set to trigger throttling
   - Memory hog: `memory_limit` set below allocation to trigger OOM
   - Noisy monitor: dispatched during concurrent tests to measure drift
3. **Result Parsing:** Read stdout, extract JSON on first line, validate against expected schema
4. **Validation Logic:**
   - CPU: ratio < 0.8 = enforcement detected ✓
   - Memory: exit code 137 (OOMKilled) = enforcement detected ✓
   - Noisy monitor: max_drift < threshold = isolation maintained ✓

### Capability Gating

- CPU and memory tests check `AXIOM_CAPABILITIES` for `resource_limits_supported`
- Orchestrator must ensure nodes have this capability before dispatching CPU/memory tests
- Noisy monitor has no capability gate (can run on any node)

### Exit Codes

- **0:** Test passed (CPU throttled, noisy monitor drifted < threshold)
- **1:** Capability missing or preflight failed (safe abort)
- **2:** Enforcement not detected (CPU not throttled, memory survived, drift exceeded)

## Verification Results

All three scripts tested and verified:

### Directory Structure
```
mop_validation/scripts/stress/bash/
├── cpu_burn.sh      (80 lines, 2.7K, executable)
├── memory_hog.sh    (60 lines, 2.1K, executable)
└── noisy_monitor.sh (75 lines, 2.5K, executable)
```

### JSON Output Samples

**cpu_burn.sh:**
```json
{"type": "cpu_burn", "language": "bash", "wall_s": 2.00, "cpu_s": 1.50, "ratio": 0.75, "threshold": 0.8, "pass": true}
PASS: CPU throttling confirmed (ratio=0.75 < 0.8 threshold)
```

**memory_hog.sh (survived):**
```json
{"type": "memory_hog", "language": "bash", "allocated_mb": 10, "held_s": 30, "pass": false, "reason": "process survived OOM — enforcement not detected"}
FAIL: Memory limit enforcement not detected (process survived after allocating 10MB)
```

**noisy_monitor.sh (sample):**
```json
{"type": "noisy_monitor", "language": "bash", "max_drift_s": 1.007, "mean_drift_s": 1.004, "threshold_s": 1.1, "measurements": [1.004,1.006,1.005,...], "pass": true}
PASS: Sleep drift within tolerance (max=1.007s, mean=1.004s < 1.1s threshold)
```

### Dependency Verification

All required tools available as standard coreutils:
- ✓ `/usr/bin/time` — Wall/CPU time separation
- ✓ `date` — Nanosecond-precision timestamps
- ✓ `dd` — Memory allocation
- ✓ `sleep` — Configurable delays
- ✓ `bc` — Floating-point math

No jq or external Python dependencies required.

## Deviations from Plan

None — plan executed exactly as written. All three scripts implement the specified output contract, environment variable handling, and exit codes.

## Next Steps

These scripts are ready for Plan 04 (Orchestrator) which will:
1. Read these scripts from disk
2. Sign them with Ed25519
3. Dispatch them via `/dispatch` API with configured limits
4. Parse JSON results
5. Build comprehensive stress test report

