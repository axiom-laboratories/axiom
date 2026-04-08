#!/bin/bash
# stress/bash/noisy_monitor.sh
# Phase 125: Sleep Drift Monitoring
#
# Measures sleep(1) accuracy over 60 iterations using nanosecond-precision timestamps.
# On a system with noisy neighbors, sleep times will exceed the threshold.
# Provides latency isolation measurement for concurrent job detection.
#
# Environment variables:
#   DRIFT_THRESHOLD_S    Maximum acceptable per-iteration drift in seconds (default "1.1")
#
# Output:
#   Line 1: JSON object with type, language, max_drift_s, mean_drift_s, measurements, pass
#   Line 2+: Human-readable summary
#
# Exit codes:
#   0  Pass (all measurements below threshold).
#   2  Fail (any measurement exceeds threshold).

set -e
set -u

# Parse drift threshold from env var
DRIFT_THRESHOLD_S="${DRIFT_THRESHOLD_S:-1.1}"
if ! [[ "$DRIFT_THRESHOLD_S" =~ ^[0-9]+\.[0-9]+$|^[0-9]+$ ]]; then
    DRIFT_THRESHOLD_S="1.1"
fi

# Create temp files for measurements
MEASUREMENTS_FILE=$(mktemp)
trap "rm -f $MEASUREMENTS_FILE" EXIT

# Run 60 iterations of sleep(1) with nanosecond timestamp tracking
for i in {1..60}; do
    START_NS=$(date +%s%N)
    sleep 1.0
    END_NS=$(date +%s%N)

    # Calculate elapsed time in seconds (nanosecond difference / 1e9)
    ELAPSED_NS=$((END_NS - START_NS))
    ELAPSED_S=$(echo "scale=3; $ELAPSED_NS / 1000000000" | bc)

    echo "$ELAPSED_S" >> "$MEASUREMENTS_FILE"
done

# Calculate max and mean drift
MAX_DRIFT=$(sort -rn "$MEASUREMENTS_FILE" | head -1)
MEAN_DRIFT=$(awk '{sum+=$1} END {printf "%.3f", sum/NR}' "$MEASUREMENTS_FILE")

# Build measurements array as JSON-compatible string
MEASUREMENTS_JSON=$(awk '{printf "%.3f", $1; if (NR < 60) printf ","}' "$MEASUREMENTS_FILE")

# Check if pass (all < threshold)
PASS="true"
while IFS= read -r MEAS; do
    if (( $(echo "$MEAS > $DRIFT_THRESHOLD_S" | bc -l) )); then
        PASS="false"
        break
    fi
done < "$MEASUREMENTS_FILE"

# Output JSON on first line
printf '{"type": "noisy_monitor", "language": "bash", "max_drift_s": %.3f, "mean_drift_s": %.3f, "threshold_s": %.1f, "measurements": [%s], "pass": %s}\n' \
    "$MAX_DRIFT" "$MEAN_DRIFT" "$DRIFT_THRESHOLD_S" "$MEASUREMENTS_JSON" "$PASS"

# Human summary on second line
if [[ "$PASS" == "true" ]]; then
    printf "PASS: Sleep drift within tolerance (max=%.3fs, mean=%.3fs < %.1fs threshold)\n" \
        "$MAX_DRIFT" "$MEAN_DRIFT" "$DRIFT_THRESHOLD_S"
    exit 0
else
    printf "FAIL: Sleep drift exceeded threshold (max=%.3fs > %.1fs) — noisy neighbors detected\n" \
        "$MAX_DRIFT" "$DRIFT_THRESHOLD_S"
    exit 2
fi
