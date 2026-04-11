#!/usr/bin/env python3
"""
Minimal test for scenario 3 concurrent isolation.
"""
import sys
import os
from pathlib import Path
current_dir = Path(__file__).resolve()
sys.path.insert(0, str(current_dir.parents[2]))

from orchestrate_stress_tests import (
    ensure_ed25519_keys,
    find_secrets_env,
    MopClient,
    Orchestrator,
    AGENT_URL,
)

def test_scenario_3():
    print("Testing Scenario 3 Concurrent Isolation...")

    # Setup
    try:
        private_key, public_key_pem = ensure_ed25519_keys()
        print("✓ Keys loaded")
    except Exception as e:
        print(f"✗ Key loading failed: {e}")
        return

    try:
        secrets = find_secrets_env()
        admin_password = secrets.get("ADMIN_PASSWORD", "")
        print("✓ Secrets loaded")
    except Exception as e:
        print(f"✗ Secrets loading failed: {e}")
        return

    # Create client
    client = MopClient(AGENT_URL, admin_password, public_key_pem=public_key_pem)
    print(f"✓ Client created for {AGENT_URL}")

    # Login
    if not client.login():
        print("✗ Login failed")
        return
    print("✓ Login successful")

    # Register signature
    if not client.register_signature():
        print("✗ Signature registration failed")
        return
    print("✓ Signature registered")

    # Create orchestrator
    orchestrator = Orchestrator(client, private_key, dry_run=False, runtime=None)
    print("✓ Orchestrator created")

    # Run scenario 3
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(orchestrator.run_scenario_3_concurrent_isolation())

    print("\nScenario 3 Results:")
    print(f"  Name: {result.get('name')}")
    print(f"  Runs: {result.get('runs')}")
    print(f"  Passed: {result.get('passed')}/{result.get('runs')}")
    print(f"  Overall Pass: {result.get('overall_pass')}")

    # Check reports
    from pathlib import Path
    reports_dir = Path("/home/thomas/Development/mop_validation/reports")
    md_report = reports_dir / "isolation_verification.md"
    json_report = reports_dir / "isolation_verification.json"

    if md_report.exists():
        print(f"✓ Markdown report: {md_report}")
        print(f"  Size: {md_report.stat().st_size} bytes")
    else:
        print(f"✗ Markdown report missing: {md_report}")

    if json_report.exists():
        print(f"✓ JSON report: {json_report}")
        print(f"  Size: {json_report.stat().st_size} bytes")
    else:
        print(f"✗ JSON report missing: {json_report}")

if __name__ == "__main__":
    test_scenario_3()
