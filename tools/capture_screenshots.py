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
    --url URL    Base URL of the running stack (default: http://localhost:80)
    --check      Run pre-flight check only (no screenshots), then exit

Prerequisites:
    - Puppeteer stack running (port 80 accessible)
    - At least one node enrolled and online
    - pip install playwright requests && playwright install chromium
"""

import argparse
import base64
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
    """Read puppeteer/secrets.env (or puppeteer/.env as fallback) and return a dict of key=value pairs."""
    secrets_path = REPO_ROOT / "puppeteer" / "secrets.env"
    fallback_path = REPO_ROOT / "puppeteer" / ".env"
    if not secrets_path.exists():
        if fallback_path.exists():
            secrets_path = fallback_path
        else:
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
            f"{base_url}/auth/login",
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
        data = r.json()
        nodes = data.get("items", data) if isinstance(data, dict) else data
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
# Demo data seeding
# ---------------------------------------------------------------------------

def seed_demo_data(base_url: str, jwt: str) -> dict:
    """
    Seed demo data against the live stack:
      - Generate an ephemeral Ed25519 keypair (no file I/O)
      - Register the public key as 'screenshot-seed-key'
      - Dispatch 4 signed jobs with a mix of outcomes
      - Wait up to 30s for at least 2 jobs to reach a terminal state

    Returns {"sig_id": <signature_id>}.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    print("\nSeeding demo data...")

    # Generate ephemeral keypair
    priv = Ed25519PrivateKey.generate()
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    auth_headers = {"Authorization": f"Bearer {jwt}"}

    # Register public key — handle existing key gracefully
    sig_id = None
    r = requests.post(
        f"{base_url}/api/signatures",
        json={"name": "screenshot-seed-key", "public_key": pub_pem},
        headers=auth_headers,
        timeout=10,
    )
    if r.status_code in (200, 201):
        sig_id = r.json().get("id")
        print(f"  [OK] Registered signing key (id={sig_id})")
    elif r.status_code in (400, 409):
        # Key already exists — find its ID
        r2 = requests.get(f"{base_url}/api/signatures", headers=auth_headers, timeout=10)
        if r2.status_code == 200:
            for sig in r2.json():
                if sig.get("name") == "screenshot-seed-key":
                    sig_id = sig.get("id")
                    break
        if sig_id:
            print(f"  [OK] Found existing signing key (id={sig_id})")
            # Re-register to get the correct public key into the DB for this ephemeral priv
            # Since the key already exists we cannot verify — register under a unique name
            import datetime
            unique_name = f"screenshot-seed-key-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')}"
            r3 = requests.post(
                f"{base_url}/api/signatures",
                json={"name": unique_name, "public_key": pub_pem},
                headers=auth_headers,
                timeout=10,
            )
            if r3.status_code in (200, 201):
                sig_id = r3.json().get("id")
                print(f"  [OK] Registered fresh signing key as '{unique_name}' (id={sig_id})")
            else:
                print(f"  [WARN] Could not register fresh key: {r3.status_code} — jobs may fail signature check")
        else:
            print("  [WARN] Could not find existing signing key ID — jobs may fail signature check")
    else:
        print(f"  [WARN] Unexpected response registering key: {r.status_code} — continuing anyway")

    def sign_and_dispatch(script: str, label: str):
        sig_bytes = priv.sign(script.encode("utf-8"))
        sig_b64 = base64.b64encode(sig_bytes).decode()
        payload = {
            "task_type": "script",
            "runtime": "python",
            "payload": {
                "script_content": script,
                "signature": sig_b64,
            },
            "signature_id": sig_id,
        }
        r = requests.post(
            f"{base_url}/api/jobs",
            json=payload,
            headers=auth_headers,
            timeout=10,
        )
        if r.status_code in (200, 201):
            job_id = r.json().get("guid", r.json().get("id", "?"))
            print(f"  [OK] Dispatched job '{label}' (id={job_id})")
        else:
            print(f"  [WARN] Job '{label}' dispatch returned {r.status_code}: {r.text[:120]}")

    # Dispatch 4 jobs with a mix of outcomes
    sign_and_dispatch('print("hello from axiom")', "hello")
    sign_and_dispatch(
        'import platform; print(f"node: {platform.node()}")',
        "platform-info",
    )
    sign_and_dispatch(
        'raise RuntimeError("intentional failure for demo")',
        "intentional-failure",
    )
    sign_and_dispatch(
        'import time; time.sleep(2); print("done")',
        "sleep-done",
    )

    # Wait for at least 2 jobs to reach a terminal state
    print("  Waiting for jobs to complete", end="", flush=True)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/api/jobs", headers=auth_headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                jobs = data.get("items", data) if isinstance(data, dict) else data
                terminal = [
                    j for j in jobs
                    if j.get("status", "").upper() in ("COMPLETED", "FAILED")
                ]
                if len(terminal) >= 2:
                    print(f" done ({len(terminal)} terminal jobs)")
                    break
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(1)
    else:
        print(" (timeout — proceeding with partial data)")

    return {"sig_id": sig_id}


# ---------------------------------------------------------------------------
# Screenshot capture — 11 views
# ---------------------------------------------------------------------------

def capture_screenshots(base_url: str, jwt: str, out_dirs: list) -> int:
    """
    Capture 11 named PNG screenshots at 1440x900 and write them to all out_dirs.

    Returns the number of successfully captured screenshots.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "[ERROR] Playwright not installed.\n"
            "  Run: pip install playwright && playwright install chromium"
        )
        return 0

    def save_screenshot(page, name: str, captured: list):
        """Write page screenshot to all output directories."""
        try:
            data = page.screenshot()
            for d in out_dirs:
                (d / name).write_bytes(data)
            print(f"  [OK] {name}")
            captured.append(name)
        except Exception as e:
            print(f"  [WARN] Failed to save {name}: {e}")

    def auth_page(page, route: str):
        """Navigate to /login, inject JWT, then navigate to the target route."""
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.evaluate(f"localStorage.setItem('mop_auth_token', '{jwt}')")
        page.goto(f"{base_url}{route}")
        page.wait_for_load_state("networkidle")

    print("\nCapturing screenshots...")

    captured = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # 1. Login page — no auth needed
        try:
            page.goto(f"{base_url}/login")
            page.wait_for_load_state("networkidle")
            save_screenshot(page, "login.png", captured)
        except Exception as e:
            print(f"  [WARN] login.png failed: {e}")

        # 2. Dashboard
        try:
            auth_page(page, "/")
            save_screenshot(page, "dashboard.png", captured)
        except Exception as e:
            print(f"  [WARN] dashboard.png failed: {e}")

        # 3. Nodes list
        try:
            auth_page(page, "/nodes")
            save_screenshot(page, "nodes.png", captured)
        except Exception as e:
            print(f"  [WARN] nodes.png failed: {e}")

        # 4. Node detail — click first node card
        try:
            auth_page(page, "/nodes")
            # Nodes page uses card layout, not a table — click the first cursor-pointer card
            page.wait_for_selector(".cursor-pointer", timeout=10000)
            first_card = page.locator(".cursor-pointer").first
            first_card.click()
            page.wait_for_timeout(1200)
            save_screenshot(page, "node_detail.png", captured)
        except Exception as e:
            print(f"  [WARN] node_detail.png failed: {e}")

        # 5. Jobs page
        try:
            auth_page(page, "/jobs")
            save_screenshot(page, "jobs.png", captured)
        except Exception as e:
            print(f"  [WARN] jobs.png failed: {e}")

        # 6. Job detail — click a completed job row
        try:
            # Reuse already-loaded jobs page if still there
            if "/jobs" not in page.url:
                auth_page(page, "/jobs")
            completed_row = page.locator("tr").filter(has_text="COMPLETED").first
            completed_row.click()
            page.wait_for_timeout(800)
            save_screenshot(page, "job_detail.png", captured)
        except Exception as e:
            print(f"  [WARN] job_detail.png failed: {e}")

        # 7. Queue page
        try:
            auth_page(page, "/queue")
            save_screenshot(page, "queue.png", captured)
        except Exception as e:
            print(f"  [WARN] queue.png failed: {e}")

        # 8. History page
        try:
            auth_page(page, "/history")
            save_screenshot(page, "history.png", captured)
        except Exception as e:
            print(f"  [WARN] history.png failed: {e}")

        # 9. Scheduled jobs page
        try:
            auth_page(page, "/scheduled-jobs")
            save_screenshot(page, "scheduled_jobs.png", captured)
        except Exception as e:
            print(f"  [WARN] scheduled_jobs.png failed: {e}")

        # 10. Foundry templates page
        try:
            auth_page(page, "/templates")
            save_screenshot(page, "foundry.png", captured)
        except Exception as e:
            print(f"  [WARN] foundry.png failed: {e}")

        # 11. Audit log
        try:
            auth_page(page, "/audit")
            save_screenshot(page, "audit.png", captured)
        except Exception as e:
            print(f"  [WARN] audit.png failed: {e}")

        browser.close()

    print(f"\nCaptured {len(captured)}/11 screenshots.")
    print("Written to:")
    for d in out_dirs:
        print(f"  {d}  ({len(list(d.glob('*.png')))} PNG files)")

    return len(captured)


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
        default="http://localhost:80",
        help="Base URL of the running stack (default: http://localhost:80)",
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

    # Seed demo data then capture screenshots
    seed_demo_data(args.url, jwt)
    capture_screenshots(args.url, jwt, out_dirs)


if __name__ == "__main__":
    main()
