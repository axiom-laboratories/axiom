#!/usr/bin/env python3
"""issue_licence.py — Axiom EE licence issuance CLI.

Issues a signed JWT licence, writes a YAML audit record to the
axiom-laboratories/axiom-licenses GitHub repository, and prints the JWT to stdout.

Usage:
    python tools/issue_licence.py \\
        --key keys/licence.key \\
        --customer acme-corp \\
        --tier ee \\
        --nodes 10 \\
        --expiry 2027-01-01 \\
        --issued-to "Acme Corp" \\
        --contact-email admin@acme.com \\
        --features sso,webhooks \\
        [--no-remote]

Key resolution (in priority order):
    1. --key <path>
    2. AXIOM_LICENCE_SIGNING_KEY env var (path to PEM file)

Remote commit:
    AXIOM_GITHUB_TOKEN must be set with contents:write scope unless --no-remote is used.
"""

import argparse
import base64
import datetime
import getpass
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import jwt
import yaml
import requests
from cryptography.hazmat.primitives import serialization


# ---------------------------------------------------------------------------
# Key resolution
# ---------------------------------------------------------------------------

def resolve_key(args):
    """Resolve the signing key from --key arg or AXIOM_LICENCE_SIGNING_KEY env var.

    Exits with a clear error message if neither is provided or the file is missing.
    Returns a loaded Ed25519PrivateKey instance.
    """
    key_source = args.key or os.getenv("AXIOM_LICENCE_SIGNING_KEY")
    if not key_source:
        sys.exit(
            "Error: no signing key provided.\n"
            "Set AXIOM_LICENCE_SIGNING_KEY env var or pass --key <path>."
        )
    path = Path(key_source)
    if not path.exists():
        sys.exit(f"Error: key file not found: {path}")
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


# ---------------------------------------------------------------------------
# Issued-by resolution
# ---------------------------------------------------------------------------

def resolve_issued_by(args):
    """Return the issuer name: args.issued_by, git config user.name, or getpass.getuser()."""
    if args.issued_by:
        return args.issued_by
    try:
        return subprocess.check_output(
            ["git", "config", "user.name"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return getpass.getuser()


# ---------------------------------------------------------------------------
# Audit record
# ---------------------------------------------------------------------------

def build_audit_record(payload, token, issued_by):
    """Build the YAML audit record dict from a signed JWT payload.

    The jti field in the record comes from payload["licence_id"] — the JWT
    payload uses "licence_id" as the key (not "jti").

    Required fields (12):
        jti, customer_id, issued_to, contact_email, tier, node_limit,
        features, grace_days, issued_at, expiry, issued_by, licence_blob
    """
    return {
        "jti": payload["licence_id"],
        "customer_id": payload["customer_id"],
        "issued_to": payload["issued_to"],
        "contact_email": payload.get("contact_email", ""),
        "tier": payload["tier"],
        "node_limit": payload["node_limit"],
        "features": payload.get("features", []),
        "grace_days": payload.get("grace_days", 30),
        "issued_at": datetime.datetime.utcfromtimestamp(payload["iat"]).date().isoformat(),
        "expiry": datetime.datetime.utcfromtimestamp(payload["exp"]).date().isoformat(),
        "issued_by": issued_by,
        "licence_blob": token,
    }


# ---------------------------------------------------------------------------
# GitHub API commit
# ---------------------------------------------------------------------------

def commit_yaml_to_github(customer_id, jti, yaml_text, tier, expiry, github_token):
    """Commit the YAML audit record to the axiom-laboratories/axiom-licenses repo.

    Raises SystemExit if AXIOM_GITHUB_TOKEN is not provided.
    Raises requests.HTTPError on API failure.
    """
    if not github_token:
        sys.exit(
            "Error: AXIOM_GITHUB_TOKEN env var not set.\n"
            "Use --no-remote for local-only operation."
        )
    path = f"licenses/issued/{customer_id}-{jti}.yml"
    url = f"https://api.github.com/repos/axiom-laboratories/axiom-licenses/contents/{path}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = {
        "message": f"feat(licenses): issue {customer_id} {tier} exp {expiry}",
        "content": base64.b64encode(yaml_text.encode()).decode(),
    }
    resp = requests.put(url, headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser():
    p = argparse.ArgumentParser(
        description="Issue an Axiom EE licence JWT and write a YAML audit record."
    )
    p.add_argument("--customer", required=True, help="Customer identifier, e.g. acme-corp")
    p.add_argument("--tier", required=True, choices=["ce", "ee"], help="Licence tier")
    p.add_argument("--nodes", required=True, type=int, help="Max active nodes (0 = unlimited)")
    p.add_argument("--expiry", required=True, help="Expiry date in YYYY-MM-DD format")
    p.add_argument("--issued-to", required=True, dest="issued_to", help="Human-readable licensee name")
    p.add_argument("--features", default="", help="Comma-separated feature flags, e.g. sso,webhooks")
    p.add_argument("--contact-email", default="", dest="contact_email", help="Contact email address")
    p.add_argument("--grace-days", type=int, default=30, dest="grace_days", help="Grace period in days")
    p.add_argument("--key", default=None, help="Path to private key PEM file")
    p.add_argument("--issued-by", default=None, dest="issued_by", help="Issuer name (defaults to git user or login)")
    p.add_argument("--no-remote", action="store_true", dest="no_remote",
                   help="Write YAML locally and print JWT; skip GitHub API commit")
    return p


def main():
    parser = _build_parser()
    args = parser.parse_args()

    # Resolve key
    private_key = resolve_key(args)

    # Resolve issuer
    issued_by = resolve_issued_by(args)

    # Parse features
    features = [f.strip() for f in args.features.split(",") if f.strip()] if args.features else []

    # Parse expiry to epoch
    expiry_dt = datetime.datetime.strptime(args.expiry, "%Y-%m-%d")
    exp_ts = int(expiry_dt.timestamp())

    # Build payload
    licence_id = str(uuid.uuid4())
    now_ts = int(time.time())
    payload = {
        "version": 1,
        "licence_id": licence_id,
        "customer_id": args.customer,
        "issued_to": args.issued_to,
        "contact_email": args.contact_email,
        "tier": args.tier,
        "node_limit": args.nodes,
        "features": features,
        "grace_days": args.grace_days,
        "iat": now_ts,
        "exp": exp_ts,
    }

    # Sign JWT
    token = jwt.encode(payload, private_key, algorithm="EdDSA")

    # Build audit record
    record = build_audit_record(payload, token, issued_by)
    yaml_text = yaml.dump(record, default_flow_style=False, sort_keys=False)

    # Human-readable summary to stderr
    print("", file=sys.stderr)
    print("=== Licence Summary ===", file=sys.stderr)
    for field in ["jti", "customer_id", "issued_to", "tier", "node_limit",
                  "features", "grace_days", "issued_at", "expiry", "issued_by"]:
        print(f"  {field}: {record[field]}", file=sys.stderr)
    print("", file=sys.stderr)

    if args.no_remote:
        # Write YAML locally
        local_filename = f"{args.customer}-{licence_id}.yml"
        Path(local_filename).write_text(yaml_text)
        print(f"[no-remote] YAML written to: {local_filename}", file=sys.stderr)
        print(yaml_text, file=sys.stderr)
        # JWT to stdout
        print(token)
    else:
        github_token = os.getenv("AXIOM_GITHUB_TOKEN")
        commit_yaml_to_github(
            customer_id=args.customer,
            jti=licence_id,
            yaml_text=yaml_text,
            tier=args.tier,
            expiry=record["expiry"],
            github_token=github_token,
        )
        commit_path = f"licenses/issued/{args.customer}-{licence_id}.yml"
        print(f"[remote] YAML committed to: {commit_path}", file=sys.stderr)
        print(token)


if __name__ == "__main__":
    main()
