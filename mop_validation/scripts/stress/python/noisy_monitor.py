#!/usr/bin/env python3
"""
stress/python/noisy_monitor.py
Phase 128: Sleep Drift Monitoring (Python)

Measures sleep(1) accuracy over 60 iterations using nanosecond-precision timestamps.
On a system with noisy neighbors, sleep times will exceed the threshold.
Provides latency isolation measurement for concurrent job detection.

No capability gating — monitor runs unconstrained to detect if neighbours disrupt it.

Environment variables:
  DRIFT_THRESHOLD_S    Maximum acceptable per-iteration drift in seconds (default "1.1")

Output:
  Line 1: JSON object with type, language, max_drift_s, mean_drift_s, measurements, pass
  Line 2+: Human-readable summary

Exit codes:
  0  Pass (all measurements below threshold).
  2  Fail (any measurement exceeds threshold).
"""

import json
import os
import time
import sys


def main():
    # Parse drift threshold from environment variable
    drift_threshold_s_str = os.environ.get("DRIFT_THRESHOLD_S", "1.1")
    try:
        drift_threshold_s = float(drift_threshold_s_str)
    except ValueError:
        drift_threshold_s = 1.1

    # Initialize measurements list
    measurements = []

    # Run 60 iterations of sleep(1) with nanosecond timestamp tracking
    for i in range(60):
        # Capture start nanosecond timestamp
        start_ns = int(time.time() * 1e9)

        # Sleep for 1 second
        time.sleep(1.0)

        # Capture end nanosecond timestamp
        end_ns = int(time.time() * 1e9)

        # Calculate elapsed time in seconds
        elapsed_ns = end_ns - start_ns
        elapsed_s = elapsed_ns / 1e9

        # Append to measurements list
        measurements.append(elapsed_s)

    # Calculate statistics
    max_drift_s = max(measurements)
    mean_drift_s = sum(measurements) / len(measurements)

    # Determine pass: all measurements must be below threshold
    pass_result = all(m < drift_threshold_s for m in measurements)

    # Build measurements array with 3-decimal precision
    measurements_rounded = [round(m, 3) for m in measurements]

    # Output JSON on first line
    result = {
        "type": "noisy_monitor",
        "language": "python",
        "max_drift_s": round(max_drift_s, 3),
        "mean_drift_s": round(mean_drift_s, 3),
        "threshold_s": drift_threshold_s,
        "measurements": measurements_rounded,
        "pass": pass_result
    }
    print(json.dumps(result))

    # Output human-readable summary on subsequent lines
    if pass_result:
        print(f"PASS: Sleep drift within tolerance (max={max_drift_s:.3f}s, mean={mean_drift_s:.3f}s < {drift_threshold_s:.1f}s threshold)")
        sys.exit(0)
    else:
        print(f"FAIL: Sleep drift exceeded threshold (max={max_drift_s:.3f}s > {drift_threshold_s:.1f}s) — noisy neighbours detected")
        sys.exit(2)


if __name__ == "__main__":
    main()
