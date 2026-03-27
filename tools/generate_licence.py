#!/usr/bin/env python3
"""
Axiom Licence Key Generator — offline CLI tool.

Usage:
  # Generate a fresh keypair (one-time setup):
  python tools/generate_licence.py --generate-keypair

  # Issue a licence JWT:
  python tools/generate_licence.py \\
    --key tools/licence_signing.key \\
    --customer-id ACME \\
    --tier ee \\
    --node-limit 10 \\
    --expiry 2027-01-01 \\
    --issued-to "ACME Corp" \\
    --contact-email admin@acme.example \\
    --feature sso --feature webhooks

The generated JWT is printed to stdout (one line).
A human-readable summary is printed to stderr.

No imports from agent_service — pure stdlib + PyJWT + cryptography.
This tool is designed for offline operation in air-gapped environments.
"""
import argparse
import datetime
import sys
import time
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import jwt


# ---------------------------------------------------------------------------
# Keypair generation
# ---------------------------------------------------------------------------

def generate_keypair(out_path: Path) -> None:
    """
    Generate a new Ed25519 keypair.

    Writes the private key PEM to `out_path`.
    Prints the public key PEM to stdout with instructions.
    """
    private_key = Ed25519PrivateKey.generate()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Write private key to file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(private_pem)
    out_path.chmod(0o600)

    # Print public key to stdout with instructions
    print(public_pem.decode(), end="")
    print("", file=sys.stderr)
    print("Keypair generated.", file=sys.stderr)
    print(f"  Private key written to: {out_path}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Paste the public PEM above into _LICENCE_PUBLIC_KEY_PEM in:", file=sys.stderr)
    print("  puppeteer/agent_service/services/licence_service.py", file=sys.stderr)


# ---------------------------------------------------------------------------
# Licence JWT signing
# ---------------------------------------------------------------------------

def sign_licence(args: argparse.Namespace) -> str:
    """
    Read the private key from args.key and sign a licence JWT.

    Returns the encoded JWT string.
    """
    key_path = Path(args.key)
    if not key_path.exists():
        print(f"Error: key file not found: {key_path}", file=sys.stderr)
        sys.exit(1)

    private_key_pem = key_path.read_bytes()
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    # Parse expiry
    expiry_date = datetime.date.fromisoformat(args.expiry)
    expiry_dt = datetime.datetime(
        expiry_date.year, expiry_date.month, expiry_date.day,
        23, 59, 59, tzinfo=datetime.timezone.utc,
    )
    exp_ts = int(expiry_dt.timestamp())

    features = args.features if args.features else []

    payload = {
        "version": 1,
        "licence_id": str(uuid.uuid4()),
        "customer_id": args.customer_id,
        "issued_to": args.issued_to,
        "contact_email": args.contact_email or "",
        "tier": args.tier,
        "node_limit": args.node_limit,
        "features": features,
        "grace_days": args.grace_days,
        "iat": int(time.time()),
        "exp": exp_ts,
    }

    token = jwt.encode(payload, private_key, algorithm="EdDSA")

    # Summary to stderr
    print("", file=sys.stderr)
    print("Licence generated:", file=sys.stderr)
    print(f"  licence_id  : {payload['licence_id']}", file=sys.stderr)
    print(f"  customer_id : {payload['customer_id']}", file=sys.stderr)
    print(f"  issued_to   : {payload['issued_to']}", file=sys.stderr)
    print(f"  tier        : {payload['tier']}", file=sys.stderr)
    print(f"  node_limit  : {payload['node_limit']} (0 = unlimited)", file=sys.stderr)
    print(f"  features    : {features}", file=sys.stderr)
    print(f"  expires     : {expiry_date.isoformat()}", file=sys.stderr)
    print(f"  grace_days  : {payload['grace_days']}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Set AXIOM_LICENCE_KEY=<token> or write token to secrets/licence.key", file=sys.stderr)

    return token


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Axiom Licence Key Generator — offline EdDSA JWT tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Mode: keypair generation
    parser.add_argument(
        "--generate-keypair",
        action="store_true",
        help="Generate a new Ed25519 keypair (write private key, print public PEM)",
    )
    parser.add_argument(
        "--out",
        default="tools/licence_signing.key",
        help="Output path for private key when using --generate-keypair (default: tools/licence_signing.key)",
    )

    # Mode: licence signing
    parser.add_argument(
        "--key",
        default=None,
        help="Path to private key PEM file (or set AXIOM_LICENCE_SIGNING_KEY env var)",
    )
    parser.add_argument("--customer-id", help="Customer identifier (e.g. ACME)")
    parser.add_argument("--tier", choices=["ce", "ee"], default="ee", help="Licence tier")
    parser.add_argument("--node-limit", type=int, default=0, help="Max active nodes (0 = unlimited)")
    parser.add_argument(
        "--feature",
        action="append",
        dest="features",
        default=[],
        help="Feature flag to enable (repeatable: --feature sso --feature webhooks)",
    )
    parser.add_argument("--expiry", help="Expiry date ISO format e.g. 2027-01-01")
    parser.add_argument("--grace-days", type=int, default=30, help="Grace period in days (default: 30)")
    parser.add_argument("--issued-to", help="Human-readable licensee name e.g. 'ACME Corp'")
    parser.add_argument("--contact-email", default="", help="Contact email for licence")

    args = parser.parse_args()

    if args.generate_keypair:
        out_path = Path(args.out)
        generate_keypair(out_path)
        return

    # Signing mode — validate required arguments
    import os
    if not args.key:
        args.key = os.getenv("AXIOM_LICENCE_SIGNING_KEY", "")
    if not args.key:
        parser.error("--key is required (or set AXIOM_LICENCE_SIGNING_KEY env var)")
    if not args.customer_id:
        parser.error("--customer-id is required")
    if not args.issued_to:
        parser.error("--issued-to is required")
    if not args.expiry:
        parser.error("--expiry is required (e.g. 2027-01-01)")

    token = sign_licence(args)
    print(token)


if __name__ == "__main__":
    main()
