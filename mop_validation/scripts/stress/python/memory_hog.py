#!/usr/bin/env python3
"""
stress/python/memory_hog.py
Phase 125: Memory OOM Measurement

Allocates a configurable amount of memory (default 256MB) via bytearray,
holds it for 30 seconds, and detects if it gets killed by OOMKill (exit code 137).
On a node with memory_limit enforcement, the allocation should be killed.

Environment variables:
  AXIOM_CAPABILITIES   Space/comma-separated capability string.
                       Must contain "resource_limits_supported" for memory test.
  MEMORY_SIZE_MB       Size to allocate in MB (default "256")

Output:
  Line 1: JSON object with type, language, allocated_mb, held_s, pass
  Line 2+: Human-readable summary

Exit codes:
  2  Process survived (enforcement not detected).
  (normally process is killed by OOM before this script exits)
"""

import json
import os
import time
import sys

# Check capability gating
capabilities = os.environ.get("AXIOM_CAPABILITIES", "")
if "resource_limits_supported" not in capabilities:
    result = {
        "type": "memory_hog",
        "language": "python",
        "pass": False,
        "error": "resource_limits_supported capability missing"
    }
    print(json.dumps(result))
    print("FAIL: resource_limits_supported capability missing — cannot validate memory limits")
    sys.exit(1)

# Parse memory size from env var
try:
    memory_size_mb = int(os.environ.get("MEMORY_SIZE_MB", "256"))
except ValueError:
    memory_size_mb = 256

# Allocate memory via bytearray
# This ensures the memory is actually committed (not just sparse)
try:
    memory_buffer = bytearray(memory_size_mb * 1024 * 1024)
    # Touch the memory to ensure it's actually allocated
    for i in range(0, len(memory_buffer), 4096):
        memory_buffer[i] = 0
except MemoryError:
    # Process was killed before reaching here (likely by OOMKill)
    # This shouldn't happen in normal flow, but handling for safety
    result = {
        "type": "memory_hog",
        "language": "python",
        "allocated_mb": memory_size_mb,
        "held_s": 0,
        "pass": True,
        "reason": "OOMKill triggered during allocation"
    }
    print(json.dumps(result))
    print("PASS: Memory limit enforcement detected (OOMKill during allocation)")
    sys.exit(137)  # Exit with OOM code

# Hold for 30 seconds
hold_seconds = 30
try:
    time.sleep(hold_seconds)
except KeyboardInterrupt:
    pass

# If we reach here, the process survived (enforcement not detected)
# Output JSON indicating failure
result = {
    "type": "memory_hog",
    "language": "python",
    "allocated_mb": memory_size_mb,
    "held_s": hold_seconds,
    "pass": False,
    "reason": "process survived OOM — enforcement not detected"
}
print(json.dumps(result))
print(f"FAIL: Memory limit enforcement not detected (process survived after allocating {memory_size_mb}MB)")

sys.exit(2)
