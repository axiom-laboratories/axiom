#!/bin/bash
# stress/bash/memory_hog.sh
# Phase 125: Memory OOM Measurement
#
# Allocates a configurable amount of memory (default 256MB) via dd into tmpfs,
# holds it for 30 seconds, and detects if it gets killed by OOMKill (exit code 137).
# On a node with memory_limit enforcement, the allocation should be killed.
#
# Environment variables:
#   AXIOM_CAPABILITIES   Space/comma-separated capability string.
#                        Must contain "resource_limits_supported" for memory test.
#   MEMORY_SIZE_MB       Size to allocate in MB (default "256")
#
# Output:
#   Line 1: JSON object with type, language, allocated_mb, held_s, pass
#   Line 2+: Human-readable summary
#
# Exit codes:
#   2  Process survived (enforcement not detected).
#   (normally process is killed by OOM before this script exits)

set -e
set -u

# Check capability gating
AXIOM_CAPABILITIES="${AXIOM_CAPABILITIES:-}"
if [[ ! "$AXIOM_CAPABILITIES" =~ resource_limits_supported ]]; then
    cat <<EOF
{"type": "memory_hog", "language": "bash", "pass": false, "error": "resource_limits_supported capability missing"}
FAIL: resource_limits_supported capability missing — cannot validate memory limits
EOF
    exit 1
fi

# Parse memory size from env var
MEMORY_SIZE_MB="${MEMORY_SIZE_MB:-256}"
if ! [[ "$MEMORY_SIZE_MB" =~ ^[0-9]+$ ]]; then
    MEMORY_SIZE_MB=256
fi

# Create a temp file for memory allocation
MEM_FILE="/dev/shm/mop_memtest_$$"
trap "rm -f $MEM_FILE" EXIT

# Allocate memory via dd (uses tmpfs if available)
# This ensures the memory is actually committed (not just sparse)
dd if=/dev/zero bs=1M count="$MEMORY_SIZE_MB" of="$MEM_FILE" 2>/dev/null

# Hold for 30 seconds
HOLD_SECONDS=30
sleep "$HOLD_SECONDS"

# If we reach here, the process survived (enforcement not detected)
# Output JSON indicating failure
printf '{"type": "memory_hog", "language": "bash", "allocated_mb": %d, "held_s": %d, "pass": false, "reason": "process survived OOM — enforcement not detected"}\n' \
    "$MEMORY_SIZE_MB" "$HOLD_SECONDS"

printf "FAIL: Memory limit enforcement not detected (process survived after allocating %dMB)\n" "$MEMORY_SIZE_MB"

exit 2
