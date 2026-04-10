---
phase: 128-concurrent-isolation-verification
plan: 01
subsystem: stress-test-corpus
tags: [concurrent-isolation, latency-drift, sleep-monitoring, nanosecond-precision]
dependency_graph:
  requires: [STRS-03, STRS-04]
  provides: [ISOL-01-monitor]
  affects: [128-02, orchestrate_stress_tests.py]
tech_stack:
  added: []
  patterns: [nanosecond-precision-timing, json-first-output, unix-exit-codes]
key_files:
  created:
    - mop_validation/scripts/stress/python/noisy_monitor.py
  modified: []
decisions:
  - Time precision: Using `time.time() * 1e9` for nanosecond-level accuracy; matches bash `date +%s%N` pattern
  - Threshold as float: Parsed from DRIFT_THRESHOLD_S env var with safe float() conversion; defaults to 1.1
  - No capability gating: Unlike memory_hog.py, monitor runs unconstrained to detect neighbor disruption
  - JSON schema: Matches orchestrator expectations from line 654-704 of orchestrate_stress_tests.py
duration_minutes: 5
completed_date: "2026-04-10"
---

# Phase 128 Plan 01: Python Noisy Monitor Summary

Python latency drift monitor for concurrent isolation testing — part of three-language stress test suite (Python/Bash/PowerShell).

## Objective

Create noisy_monitor.py to measure sleep(1) drift over 60 iterations with nanosecond precision, enabling Phase 128's concurrent isolation verification to detect if co-located jobs suffer latency disruption from noisy neighbours.

## One-Liner

Nanosecond-precision sleep drift monitor (60 iterations) with pass/fail determination based on per-iteration latency against configurable threshold.

## Execution Summary

### Task 1: Create noisy_monitor.py (COMPLETE)

**Implementation details:**
- File: `/home/thomas/Development/master_of_puppets/mop_validation/scripts/stress/python/noisy_monitor.py`
- 91 lines (exceeds 80-line minimum)
- Executable (`chmod +x` applied)

**Algorithm:**
1. Parse `DRIFT_THRESHOLD_S` env var (default 1.1s, safe float conversion)
2. Initialize empty measurements list
3. Loop 60 times:
   - Capture start nanosecond timestamp: `int(time.time() * 1e9)`
   - Call `time.sleep(1.0)`
   - Capture end nanosecond timestamp: `int(time.time() * 1e9)`
   - Calculate elapsed_s = (end_ns - start_ns) / 1e9
   - Append to measurements
4. Calculate max_drift_s = max(measurements)
5. Calculate mean_drift_s = sum(measurements) / len(measurements)
6. Determine pass = all(m < threshold for m in measurements)
7. Build measurements array with 3-decimal precision rounding
8. Output JSON on first line (schema matches bash/pwsh implementations)
9. Output human-readable summary on second line
10. Exit 0 on pass, 2 on fail

**Verification results:**
- Syntax check: PASSED (python3 -m py_compile)
- File executable: PASSED (chmod +x verified)
- JSON output format: PASSED (first stdout line matches orchestrator expectations)
- Environment variable parsing: PASSED (DRIFT_THRESHOLD_S override tested)
- Exit codes: PASSED (0 on pass, 2 on fail)
- Line count: PASSED (91 lines > 80 minimum)

**Example output (pass case):**
```
{"type": "noisy_monitor", "language": "python", "max_drift_s": 1.001, "mean_drift_s": 1.0, "threshold_s": 1.1, "measurements": [1.0, ...60 items...], "pass": true}
PASS: Sleep drift within tolerance (max=1.001s, mean=1.000s < 1.1s threshold)
```

**Example output (fail case with DRIFT_THRESHOLD_S=0.99):**
```
{"type": "noisy_monitor", "language": "python", "max_drift_s": 1.001, "mean_drift_s": 1.0, "threshold_s": 0.99, "measurements": [1.0, ...60 items...], "pass": false}
FAIL: Sleep drift exceeded threshold (max=1.001s > 1.0s) — noisy neighbours detected
```

**Commit:** 0fdad86 — feat(128-01): implement Python noisy_monitor for concurrent isolation testing

## Verification Status

All success criteria met:

- [x] File created at `mop_validation/scripts/stress/python/noisy_monitor.py`
- [x] Executable and parseable (syntax valid)
- [x] Implements exact 60-iteration sleep drift algorithm with nanosecond precision
- [x] Outputs JSON on first line with max_drift_s, mean_drift_s, threshold_s, measurements, pass
- [x] Respects DRIFT_THRESHOLD_S env var (default 1.1s)
- [x] Exits 0 on pass, 2 on fail
- [x] Human-readable summary on subsequent lines
- [x] No capability gating (unlike memory_hog.py)
- [x] Three-language parity achieved (Python now joins Bash + PowerShell)

## Deviations from Plan

None — plan executed exactly as written. All requirements met, no auto-fixes needed, no architectural decisions required.

## Next Steps

Plan 128-02 will use `load_script("python", "noisy_monitor.py")` to dispatch this script as part of the concurrent isolation stress test scenario.

## Self-Check Results

- File exists: `/home/thomas/Development/master_of_puppets/mop_validation/scripts/stress/python/noisy_monitor.py` ✓
- Commit exists: `0fdad86` ✓
- All assertions verified in testing ✓

**Self-Check: PASSED**
