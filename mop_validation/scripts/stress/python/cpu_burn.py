#!/usr/bin/env python3
"""
stress/python/cpu_burn.py
Phase 125: CPU Throttling Measurement

Spins a CPU-bound loop for a configurable duration (default 5 seconds) and compares
wall time to CPU time. On a node with cpu_limit enforcement, the CPU/wall ratio will
be < 0.8; without throttling it approaches 1.0.

Environment variables:
  AXIOM_CAPABILITIES   Space/comma-separated capability string.
                       Must contain "resource_limits_supported" for CPU test.
  CPU_DURATION_S       Duration of CPU burn in seconds (default "5")

Output:
  Line 1: JSON object with type, language, wall_s, cpu_s, ratio, threshold, pass
  Line 2+: Human-readable summary

Exit codes:
  0  Measurement complete (throttling detected or not — both are valid).
  1  resource_limits_supported capability is missing — abort safely.
"""

import json
import os
import time
import sys

# Check capability gating
capabilities = os.environ.get("AXIOM_CAPABILITIES", "")
if "resource_limits_supported" not in capabilities:
    result = {
        "type": "cpu_burn",
        "language": "python",
        "pass": False,
        "error": "resource_limits_supported capability missing"
    }
    print(json.dumps(result))
    print("FAIL: resource_limits_supported capability missing — cannot validate CPU limits")
    sys.exit(1)

# Parse CPU duration from env var
cpu_duration_s = int(os.environ.get("CPU_DURATION_S", "5"))

# Measure wall and CPU time for a CPU-bound loop
wall_start = time.time()
cpu_start = time.process_time()

# CPU-bound loop: compute hashes
deadline = wall_start + cpu_duration_s
data = b"x" * 1024
while time.time() < deadline:
    hash(data)

wall_elapsed = time.time() - wall_start
cpu_elapsed = time.process_time() - cpu_start

# Avoid division by zero
if wall_elapsed > 0:
    ratio = cpu_elapsed / wall_elapsed
else:
    ratio = 0.0

# Throttling threshold: ratio < 0.8 = pass (throttled)
threshold = 0.8
passed = ratio < threshold

# Output JSON on first line
result = {
    "type": "cpu_burn",
    "language": "python",
    "wall_s": round(wall_elapsed, 2),
    "cpu_s": round(cpu_elapsed, 2),
    "ratio": round(ratio, 2),
    "threshold": threshold,
    "pass": passed
}
print(json.dumps(result))

# Human summary on second line
if passed:
    print(f"PASS: CPU throttling confirmed (ratio={ratio:.2f} < {threshold} threshold)")
else:
    print(f"INFO: No throttling detected (ratio={ratio:.2f} >= {threshold}) — check node capacity")

sys.exit(0)
