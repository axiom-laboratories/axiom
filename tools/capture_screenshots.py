#!/usr/bin/env python3
# Install: pip install playwright requests && playwright install chromium
"""
Master of Puppets — Screenshot Capture Script

Seeds demo data against a live Docker stack and captures 11 named PNG screenshots
at 1440x900, writing them to both docs/docs/assets/screenshots/ and
homepage/assets/screenshots/.

Usage:
    python tools/capture_screenshots.py [--url URL] [--check]

Options:
    --url URL    Base URL of the running stack (default: http://localhost:8080)
    --check      Run pre-flight check only (no screenshots), then exit

Prerequisites:
    - Puppeteer stack running (port 8080 accessible)
    - At least one node enrolled and online
    - pip install playwright requests && playwright install chromium
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests

# Repo root is one level above the tools/ directory
REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Secrets loader
# ---------------------------------------------------------------------------

def load_secrets() -> dict:
    """Read puppeteer/secrets.env and return a dict of key=value pairs."""
    secrets_path = REPO_ROOT / "puppeteer" / "secrets.env"
    if not secrets_path.exists():
        raise FileNotFoundError(
            f"secrets.env not found at {secrets_path}\n"
            "Ensure the Puppeteer stack has been configured with credentials."
        )
    result = {}
    for line in secrets_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


# ---------------------------------------------------------------------------
# Pre-flight check
# ---------------------------------------------------------------------------

def preflight_check(base_url: str, admin_password: str):
    """
    Verify the stack is reachable, credentials are valid, and at least one
    node is enrolled.

    Returns the JWT string on success, or False on failure.
    """
    print("\nRunning pre-flight checks...")

    # 1. Stack reachable
    try:
        r = requests.get(f"{base_url}/", timeout=10)
        if r.status_code == 200:
            print(f"  [OK] Stack reachable at {base_url}")
        else:
            print(f"  [FAIL] Stack returned HTTP {r.status_code} — expected 200")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] Cannot connect to {base_url} — is the stack running?")
        return False
    except requests.exceptions.Timeout:
        print(f"  [FAIL] Connection timed out to {base_url}")
        return False

    # 2. Admin credentials valid — obtain JWT
    try:
        r = requests.post(
            f"{base_url}/api/auth/login",
            data={"username": "admin", "password": admin_password},
            timeout=10,
        )
        if r.status_code == 200:
            jwt = r.json().get("access_token")
            if not jwt:
                print("  [FAIL] Login succeeded but no access_token in response")
                return False
            print("  [OK] Admin credentials valid — JWT obtained")
        else:
            print(f"  [FAIL] Login failed with HTTP {r.status_code} — check ADMIN_PASSWORD in secrets.env")
            return False
    except Exception as e:
        print(f"  [FAIL] Login request error: {e}")
        return False

    # 3. At least one enrolled node
    try:
        r = requests.get(
            f"{base_url}/api/nodes",
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  [FAIL] GET /api/nodes returned HTTP {r.status_code}")
            return False
        nodes = r.json()
        if not isinstance(nodes, list) or len(nodes) == 0:
            print("  [FAIL] No enrolled nodes found — enroll at least one node before capturing screenshots")
            return False
        online = [n for n in nodes if n.get("status", "").upper() == "ONLINE"]
        print(f"  [OK] {len(nodes)} node(s) enrolled, {len(online)} online")
    except Exception as e:
        print(f"  [FAIL] Nodes check error: {e}")
        return False

    print("\nPre-flight OK. Ready to capture.")
    return jwt


# ---------------------------------------------------------------------------
# Output directory setup
# ---------------------------------------------------------------------------

def setup_output_dirs() -> list:
    """Create screenshot output directories and return them as Path objects."""
    dirs = [
        REPO_ROOT / "docs" / "docs" / "assets" / "screenshots",
        REPO_ROOT / "homepage" / "assets" / "screenshots",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    return dirs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Capture screenshots of the Master of Puppets dashboard."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of the running stack (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run pre-flight check only (no screenshots), then exit",
    )
    args = parser.parse_args()

    # Load credentials
    try:
        secrets = load_secrets()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    admin_password = secrets.get("ADMIN_PASSWORD", "")
    if not admin_password:
        print("[ERROR] ADMIN_PASSWORD not found in puppeteer/secrets.env")
        sys.exit(1)

    # Pre-flight check
    jwt = preflight_check(args.url, admin_password)

    if args.check:
        sys.exit(0 if jwt else 1)

    if not jwt:
        print("[ERROR] Pre-flight check failed — aborting screenshot capture.")
        sys.exit(1)

    # Setup output directories
    out_dirs = setup_output_dirs()
    print(f"\nOutput directories:")
    for d in out_dirs:
        print(f"  {d}")

    # Seed demo data and capture screenshots (implemented in subsequent tasks)
    seed_demo_data(args.url, jwt)
    capture_screenshots(args.url, jwt, out_dirs)


if __name__ == "__main__":
    main()
