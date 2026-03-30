#!/usr/bin/env bash
# validation/volume-mapping.sh
# JOB-04 — Volume Mount Validation
#
# Confirms that the container volume mount at AXIOM_VOLUME_PATH is readable
# and writable. Writes a PID-unique sentinel file, reads it back, and cleans up.
#
# Required env:
#   AXIOM_VOLUME_PATH   Path to the volume mount inside the container.
#                       Defaults to /mnt/axiom-data if not set.
#
# Exit codes:
#   0  Volume is present, readable, and writable.
#   1  Volume path does not exist or is not accessible.

set -euo pipefail

MOUNT_PATH="${AXIOM_VOLUME_PATH:-/mnt/axiom-data}"
SENTINEL="${MOUNT_PATH}/axiom-validation-$$.txt"

echo "=== Axiom Volume Mapping Validation ==="
echo "Mount path: ${MOUNT_PATH}"

if [[ ! -d "${MOUNT_PATH}" ]]; then
    echo "FAIL: mount path ${MOUNT_PATH} does not exist inside container"
    echo "      Ensure the volume is mounted at AXIOM_VOLUME_PATH."
    exit 1
fi

# Write sentinel
CONTENT="axiom-validation-$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "${CONTENT}" > "${SENTINEL}"
echo "Wrote sentinel: ${SENTINEL}"

# Read back
READ_BACK=$(cat "${SENTINEL}")
if [[ "${READ_BACK}" != "${CONTENT}" ]]; then
    echo "FAIL: sentinel read-back mismatch"
    echo "  Written:  ${CONTENT}"
    echo "  Read:     ${READ_BACK}"
    rm -f "${SENTINEL}"
    exit 1
fi
echo "Read-back matches."

# Cleanup
rm -f "${SENTINEL}"
echo "Cleaned up sentinel."

echo "=== PASS: volume mount is readable and writable ==="
