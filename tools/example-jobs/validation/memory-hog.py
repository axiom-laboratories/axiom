#!/usr/bin/env python3
# validation/memory-hog.py
# JOB-06 — Memory OOM Validation
#
# Allocates 256 MB of RSS memory (page-touching prevents overcommit from
# deferring the commit) and holds it for 30 seconds. On a node configured
# with a memory_limit < 256 MB, the container runtime should OOM-kill the
# process before the sleep completes.
#
# Required env:
#   AXIOM_CAPABILITIES   Comma- or space-separated capability string.
#                        Must contain "resource_limits_supported".
#
# Exit codes:
#   0  Unreachable under normal operation (job should be OOM-killed).
#   1  resource_limits_supported capability is missing — abort safely.
#   2  Sentinel: process was NOT killed during the 30-second hold window.
#      This indicates resource limits are not enforced on this node.

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

print("resource_limits_supported: present — proceeding with memory allocation test")
print("Allocating 256 MB ...", flush=True)

chunk = bytearray(256 * 1024 * 1024)
# Touch every page to force RSS commitment (defeats Linux overcommit).
chunk[0::4096] = b"\x00" * (len(chunk) // 4096)

print("Allocation complete — container should be OOM-killed or exceed memory limit")
time.sleep(30)

# If the process reaches this line the container runtime did not enforce limits.
print(
    "ERROR: should have been killed before reaching this line",
    flush=True,
)
sys.exit(2)
