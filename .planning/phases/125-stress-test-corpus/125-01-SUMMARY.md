---
phase: 125-stress-test-corpus
plan: 01
subsystem: stress-test-corpus
tags:
  - python
  - stress-testing
  - resource-limits
  - validation
dependency_graph:
  requires: []
  provides:
    - python/cpu_burn.py — CPU throttling measurement via wall/CPU time ratio
    - python/memory_hog.py — Memory OOM validation via bytearray page-touching
    - python/noisy_monitor.py — Sleep drift measurement for concurrent isolation testing
  affects:
    - Plan 04 (orchestrator dispatch)
    - Phase 126 (limit enforcement validation)
    - Phase 128 (concurrent isolation testing)
tech_stack:
  added:
    - Python stdlib: time.perf_counter(), time.process_time()
    - Python stdlib: json for structured output
    - Bytearray page-touching pattern (stride slice access)
  patterns:
    - Dual output (JSON + human summary)
    - AXIOM_CAPABILITIES gating for CPU/memory tests
    - Exit code semantics (0=pass, 1=capability missing, 2=enforcement not detected)
key_files:
  created:
    - mop_validation/scripts/stress/python/cpu_burn.py (71 lines)
    - mop_validation/scripts/stress/python/memory_hog.py (98 lines)
    - mop_validation/scripts/stress/python/noisy_monitor.py (71 lines)
  modified: []
decisions:
  - JSON output includes spaces after colons (valid JSON, human-readable)
  - CPU duration defaults to 5 seconds, configurable via CPU_DURATION_S env var
  - Memory allocation defaults to 256 MB, configurable via MEMORY_SIZE_MB env var
  - Noisy monitor runs 60 iterations (60 seconds), threshold defaults to 1.1s
  - All scripts use time.perf_counter() for wall-clock measurements (preferred over monotonic)
metrics:
  duration_minutes: 10
  start_time: 2026-04-08T21:09:59Z
  completed_date: 2026-04-08
  tasks_completed: 3
  commits: 1

---

# Phase 125 Plan 01: Python Stress Test Scripts Summary

**One-liner:** Created three Python stress test scripts (CPU burner, memory hog, noisy-neighbour monitor) with dual JSON+human output and env var configurability.

## Work Summary

### Task 1: CPU Burner (cpu_burn.py)
- Implements CPU throttling measurement using wall-clock vs CPU time ratio
- Pattern: 5-second spin loop of `2 ** 31` (CPU-bound operation)
- Uses `time.perf_counter()` for wall time and `time.process_time()` for CPU time
- Threshold: ratio < 0.8 indicates throttling is active
- Exit code: 0 (always — measurement is valid either way)
- Gating: Requires `resource_limits_supported` capability (exit 1 if missing)
- Configuration: `CPU_DURATION_S` env var (default "5")

### Task 2: Memory Hog (memory_hog.py)
- Implements memory OOM validation via page-touched bytearray allocation
- Pattern: Allocate bytearray, touch every 4096-byte page, hold for 30 seconds
- Page-touching uses stride slice access: `chunk[0::4096] = b"\x00" * (len(chunk) // 4096)`
- Defeats Linux memory overcommit by forcing RSS commitment
- Normal exit: code 2 (process should be OOM-killed before returning)
- Exit code: 1 (capability missing), 2 (enforcement not detected)
- Gating: Requires `resource_limits_supported` capability (exit 1 if missing)
- Configuration: `MEMORY_SIZE_MB` env var (default "256")

### Task 3: Noisy Monitor (noisy_monitor.py)
- Implements latency drift detection for concurrent isolation testing
- Pattern: 60 iterations of `sleep(1)` with per-iteration elapsed time measurement
- Tracks individual latencies and computes max_drift and mean_drift
- Useful for detecting noisy neighbours interfering with scheduling
- Exit code: 0 (pass — max drift < threshold), 2 (fail — drift exceeded)
- No capability gating (monitor runs without resource_limits_supported)
- Configuration: `DRIFT_THRESHOLD_S` env var (default "1.1")

## Output Format

All three scripts follow identical output contract:

**Line 1: JSON object** (machine-parseable)
```json
{
  "type": "cpu_burn|memory_hog|noisy_monitor",
  "language": "python",
  ... (type-specific fields)
}
```

**Line 2+: Human-readable summary** (operator-friendly)
```
PASS: CPU throttling confirmed (ratio=0.50 < 0.80 threshold)
```
or
```
FAIL: Latency drift detected (max=1.25s >= 1.1s threshold)
```

## Verification Results

### Test Coverage
- ✓ Directory structure verified: all three scripts in `mop_validation/scripts/stress/python/`
- ✓ Executability verified: all scripts have execute bit set
- ✓ JSON output format: valid JSON on first line (python3 -m json.tool validates)
- ✓ Exit code 0: cpu_burn and noisy_monitor on success
- ✓ Exit code 1: cpu_burn and memory_hog when AXIOM_CAPABILITIES missing
- ✓ Exit code 2: memory_hog and noisy_monitor on failure
- ✓ Environment variable overrides: CPU_DURATION_S, MEMORY_SIZE_MB, DRIFT_THRESHOLD_S all respected

### Sample Output

**CPU Burner (no throttling):**
```
{"type": "cpu_burn", "language": "python", "wall_s": 5.0, "cpu_s": 4.99, "ratio": 1.0, "threshold": 0.8, "pass": false}
INFO: No throttling detected (ratio=1.00 >= 0.80) — check node capacity
```

**Noisy Monitor (pass):**
```
{"type": "noisy_monitor", "language": "python", "duration_s": 60, "measurements_count": 60, "max_drift_s": 1.05, "mean_drift_s": 1.001, "threshold_s": 1.1, "pass": true, "measurements": [1.0, 1.01, ..., 1.05]}
PASS: No latency drift detected (max=1.05s < 1.1s threshold)
```

## Integration Points

### For Plan 04 (Orchestrator)
- Scripts are ready to be loaded from disk and dispatched via `POST /dispatch`
- Each script must be signed with Ed25519 before submission
- All scripts respect `AXIOM_CAPABILITIES` and environment variable configuration
- JSON output is machine-parseable for automated result reporting

### For Phase 126 (Enforcement Validation)
- CPU burner and memory hog provide resource limit validation
- Can be dispatched with cpu_limit and memory_limit parameters
- Expected behaviors:
  - CPU burner: ratio < 0.8 when cpu_limit is active
  - Memory hog: exit code 2 (should be OOM-killed)

### For Phase 128 (Concurrent Isolation)
- Noisy monitor provides latency drift measurement under concurrent load
- Can be dispatched alongside CPU burner + memory hog to measure interference
- Threshold (default 1.1s) allows ~100ms jitter while detecting significant scheduling drift

## Deviations from Plan

None — plan executed exactly as written. All three scripts implement the specified contracts with dual output, capability gating, environment variable support, and proper exit codes.

## Self-Check: PASSED

- ✓ cpu_burn.py exists at `/home/thomas/Development/mop_validation/scripts/stress/python/cpu_burn.py`
- ✓ memory_hog.py exists at `/home/thomas/Development/mop_validation/scripts/stress/python/memory_hog.py`
- ✓ noisy_monitor.py exists at `/home/thomas/Development/mop_validation/scripts/stress/python/noisy_monitor.py`
- ✓ All files are executable (755 permissions)
- ✓ Commit `20f741d` verified in mop_validation repo
- ✓ All JSON output samples parse as valid JSON
- ✓ Exit codes match specification (0, 1, 2)
- ✓ AXIOM_CAPABILITIES gating works correctly
- ✓ Environment variable overrides function as expected

