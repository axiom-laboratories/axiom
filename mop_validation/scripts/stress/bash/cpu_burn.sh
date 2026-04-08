#!/bin/bash
# stress/bash/cpu_burn.sh
# Phase 125: CPU Throttling Measurement
#
# Spins a CPU-bound loop for a configurable duration (default 5 seconds) and compares
# wall time to CPU time. On a node with cpu_limit enforcement, the CPU/wall ratio will
# be < 0.8; without throttling it approaches 1.0.
#
# Environment variables:
#   AXIOM_CAPABILITIES   Space/comma-separated capability string.
#                        Must contain "resource_limits_supported" for CPU test.
#   CPU_DURATION_S       Duration of CPU burn in seconds (default "5")
#
# Output:
#   Line 1: JSON object with type, language, wall_s, cpu_s, ratio, threshold, pass
#   Line 2+: Human-readable summary
#
# Exit codes:
#   0  Measurement complete (throttling detected or not — both are valid).
#   1  resource_limits_supported capability is missing — abort safely.

set -e
set -u

# Check capability gating
AXIOM_CAPABILITIES="${AXIOM_CAPABILITIES:-}"
if [[ ! "$AXIOM_CAPABILITIES" =~ resource_limits_supported ]]; then
    cat <<EOF
{"type": "cpu_burn", "language": "bash", "pass": false, "error": "resource_limits_supported capability missing"}
FAIL: resource_limits_supported capability missing — cannot validate CPU limits
EOF
    exit 1
fi

# Parse CPU duration from env var
CPU_DURATION_S="${CPU_DURATION_S:-5}"
if ! [[ "$CPU_DURATION_S" =~ ^[0-9]+$ ]]; then
    CPU_DURATION_S=5
fi

# Use /usr/bin/time to measure wall and CPU time
# We'll wrap a simple CPU-bound loop (dd piped to md5sum)
TIME_OUTPUT=$(mktemp)
trap "rm -f $TIME_OUTPUT" EXIT

/usr/bin/time -f "%e %U" -o "$TIME_OUTPUT" timeout "$CPU_DURATION_S" dd if=/dev/zero bs=1M 2>/dev/null | md5sum > /dev/null 2>&1 || true

# Read timing results
read WALL_STR CPU_STR < "$TIME_OUTPUT"

# Convert to floating point and calculate ratio
WALL_S=$(echo "$WALL_STR" | awk '{printf "%.2f", $1}')
CPU_S=$(echo "$CPU_STR" | awk '{printf "%.2f", $1}')

# Calculate ratio with bc
if (( $(echo "$WALL_S > 0" | bc -l) )); then
    RATIO=$(echo "scale=2; $CPU_S / $WALL_S" | bc -l)
else
    RATIO="0.00"
fi

# Throttling threshold: ratio < 0.8 = pass (throttled)
THRESHOLD="0.8"
PASS="false"
if (( $(echo "$RATIO < $THRESHOLD" | bc -l) )); then
    PASS="true"
fi

# Output JSON on first line
printf '{"type": "cpu_burn", "language": "bash", "wall_s": %.2f, "cpu_s": %.2f, "ratio": %.2f, "threshold": %.1f, "pass": %s}\n' \
    "$WALL_S" "$CPU_S" "$RATIO" "$THRESHOLD" "$PASS"

# Human summary on second line
if [[ "$PASS" == "true" ]]; then
    printf "PASS: CPU throttling confirmed (ratio=%.2f < %.1f threshold)\n" "$RATIO" "$THRESHOLD"
else
    printf "INFO: No throttling detected (ratio=%.2f >= %.1f) — check node capacity\n" "$RATIO" "$THRESHOLD"
fi

exit 0
