#!/usr/bin/env python3
# validation/verify_pypi_mirror.py
# PKG-04 — PyPI Mirror Validation
#
# Confirms pip resolves packages from the internal mirror rather than pypi.org.
# Runs a dry-run pip install of the 'requests' package and inspects the verbose
# output for "Downloading" lines. The PYPI_MIRROR_HOST hostname must appear in
# at least one Downloading line for the validation to PASS.
#
# Required env:
#   PYPI_MIRROR_HOST   Hostname (and optional port) of the internal mirror.
#                      Example: devpi:3141  or  pypi.internal.example.com
#
# Exit codes:
#   0  PASS — pip resolved requests from the configured mirror.
#   1  FAIL — mirror hostname not found in Downloading lines, pypi.org detected,
#              PYPI_MIRROR_HOST env var is absent, or no Downloading lines found.

import os
import subprocess
import sys

MIRROR_HOST = os.environ.get("PYPI_MIRROR_HOST", "")
TEST_PACKAGE = "requests"

print("=== Axiom PyPI Mirror Validation ===")

if not MIRROR_HOST:
    print("FAIL: PYPI_MIRROR_HOST env var is not set.")
    print("      Set it to the hostname (and port) of your internal pip mirror,")
    print("      e.g. PYPI_MIRROR_HOST=devpi:3141")
    sys.exit(1)

print(f"Testing mirror: {MIRROR_HOST}")
print(f"Package probe: {TEST_PACKAGE}")

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", TEST_PACKAGE, "--dry-run", "-v"],
    capture_output=True,
    text=True,
)
combined = result.stdout + result.stderr

download_lines = [
    line for line in combined.splitlines()
    if "Downloading" in line or "downloading" in line
]

if not download_lines:
    print("WARN: No 'Downloading' lines found in pip output.")
    print("      The package may already be cached. Rerun with:")
    print(f"      pip install {TEST_PACKAGE} --dry-run -v --no-cache-dir")
    print("--- Last 500 chars of pip output ---")
    print(combined[-500:])
    sys.exit(1)

for line in download_lines:
    if MIRROR_HOST in line:
        print(f"PASS: pip resolved {TEST_PACKAGE} from mirror ({MIRROR_HOST})")
        print(f"      {line.strip()}")
        sys.exit(0)
    if "pypi.org" in line:
        print(f"FAIL: pip resolved {TEST_PACKAGE} from pypi.org instead of mirror.")
        print(f"      {line.strip()}")
        print("      Check PYPI_MIRROR_URL config and that devpi is seeded.")
        sys.exit(1)

# Download lines found but neither mirror nor pypi.org matched — unknown source
print("FAIL: Downloading lines found but mirror hostname not present.")
for line in download_lines:
    print(f"      {line.strip()}")
print(f"      Expected '{MIRROR_HOST}' in at least one Downloading line.")
sys.exit(1)
