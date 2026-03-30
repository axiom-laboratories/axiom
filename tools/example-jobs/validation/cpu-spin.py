#!/usr/bin/env python3
# validation/cpu-spin.py
# JOB-07 — CPU Throttle Validation
#
# Spins a CPU-bound loop for 5 seconds and compares wall time to CPU time.
# On a node with cpu_limit=0.5, the CPU/wall ratio will be ~0.5; without
# throttling it approaches 1.0.
#
# Required env:
#   AXIOM_CAPABILITIES   Comma- or space-separated capability string.
#                        Must contain "resource_limits_supported".
#
# Exit codes:
#   0  Measurement complete (throttling detected or not — both are valid exits).
#   1  resource_limits_supported capability is missing — abort safely.

import os
import sys
import time

caps_raw = os.environ.get("AXIOM_CAPABILITIES", "")
if "resource_limits_supported" not in caps_raw:
    print(
        "FAIL: resource limits are not supported on this node "
        "(resource_limits_supported capability missing)",
        flush=True,
    )
    sys.exit(1)

print("resource_limits_supported: present — proceeding with CPU spin test")

DURATION = 5
start_wall = time.monotonic()
start_cpu = time.process_time()

deadline = start_wall + DURATION
while time.monotonic() < deadline:
    _ = 2 ** 31

wall = time.monotonic() - start_wall
cpu = time.process_time() - start_cpu
ratio = cpu / wall if wall > 0 else 0

print(f"Wall time: {wall:.2f}s  CPU time: {cpu:.2f}s  Ratio: {ratio:.2f}")

if ratio < 0.8:
    print(
        f"PASS: CPU throttling confirmed (ratio={ratio:.2f} < 0.80 threshold) — "
        "cpu_limit is being enforced by the container runtime"
    )
else:
    print(
        f"INFO: No throttling detected (ratio={ratio:.2f} >= 0.80) — "
        "either cpu_limit is not set or this node has spare capacity"
    )

print("=== cpu-spin validation complete ===")
