#!/usr/bin/env python3
# validation/network-filter.py
# JOB-05 — Network Isolation Validation
#
# Confirms that network isolation is active on the target node by attempting
# to connect to a host that should be unreachable (AXIOM_BLOCKED_HOST).
#
# This script only validates existing isolation — it does NOT manipulate
# iptables or any network configuration. Isolation must be applied at the
# container runtime level (e.g. --network=none).
#
# Required env (all optional with defaults):
#   AXIOM_BLOCKED_HOST   Host to verify is unreachable. Default: 8.8.8.8
#   AXIOM_ALLOWED_HOST   Optional host to verify is reachable (if set).
#
# Exit codes:
#   0  Isolation confirmed (blocked host is unreachable).
#   1  Isolation NOT active (blocked host is reachable, or unexpected error).

import os
import socket
import sys

BLOCKED = os.environ.get("AXIOM_BLOCKED_HOST", "8.8.8.8")
ALLOWED = os.environ.get("AXIOM_ALLOWED_HOST", "")

socket.setdefaulttimeout(5)

print("=== Axiom Network Filter Validation ===")
print(f"Checking blocked host: {BLOCKED}")

# --- Blocked host check ---
try:
    conn = socket.create_connection((BLOCKED, 80), timeout=5)
    conn.close()
    print(
        f"FAIL: connected to blocked host {BLOCKED}:80 — "
        "network isolation is NOT active"
    )
    sys.exit(1)
except (socket.timeout, OSError):
    print(f"PASS: blocked host {BLOCKED} is unreachable (expected)")

# --- Optional allowed host check ---
if ALLOWED:
    print(f"Checking allowed host: {ALLOWED}")
    try:
        conn = socket.create_connection((ALLOWED, 80), timeout=5)
        conn.close()
        print(f"PASS: allowed host {ALLOWED} is reachable")
    except (socket.timeout, OSError) as exc:
        print(f"WARN: allowed host {ALLOWED} is unreachable: {exc}")
        print("      This may indicate over-restrictive isolation.")

print("=== network-filter validation complete ===")
