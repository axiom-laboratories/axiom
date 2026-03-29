#!/usr/bin/env python3
"""
Axiom OpenAPI Snapshot Generator

Fetches the OpenAPI spec from a running Docker stack and commits it to
docs/docs/api-reference/openapi.json as the source-of-truth snapshot
for docs accuracy validation.

Usage:
    python tools/generate_openapi.py [--url URL]

Options:
    --url URL    Base URL of the running stack (default: http://localhost:8080)
"""
import argparse
import json
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(
        description="Fetch OpenAPI spec from running stack and save snapshot."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of the running stack (default: http://localhost:8080)",
    )
    args = parser.parse_args()

    print(f"Fetching OpenAPI spec from {args.url}/openapi.json ...")
    try:
        r = requests.get(f"{args.url}/openapi.json", timeout=10)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to {args.url} — is the stack running?")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP error: {e}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"[ERROR] Connection timed out to {args.url}")
        sys.exit(1)

    try:
        spec = r.json()
    except Exception:
        print("[ERROR] Response is not valid JSON")
        sys.exit(1)

    out_path = REPO_ROOT / "docs" / "docs" / "api-reference" / "openapi.json"
    out_path.write_text(json.dumps(spec, indent=2))

    route_count = len(spec.get("paths", {}))
    print(f"Written to {out_path}")
    print(f"Routes: {route_count}")

    if route_count == 0:
        print("[WARN] Snapshot has no routes — is this a stub?")


if __name__ == "__main__":
    main()
