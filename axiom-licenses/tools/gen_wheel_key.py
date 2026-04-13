#!/usr/bin/env python3
"""gen_wheel_key.py — Generate Ed25519 keypair for wheel manifest signing.

One-time keypair generation for EE wheel signing. Generates a fresh Ed25519
keypair, writes the private key to a file with secure permissions (0600), and
prints the public key PEM as a Python bytes literal to stdout for copy-paste
into the backend (ee/__init__.py).

Usage:
    python tools/gen_wheel_key.py [--out wheel_signing.key] [--force]

The private key file will be created with mode 0600 (readable only by owner).
The public key is printed to stdout formatted as a Python bytes literal.
"""

import argparse
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def generate_keypair(out_path: Path, force: bool = False) -> tuple[bytes, bytes]:
    """Generate Ed25519 keypair and write private key to file.

    Args:
        out_path: Path where private key should be written
        force: If True, overwrite existing key file. If False, error if exists.

    Returns:
        tuple[bytes, bytes]: (private_pem, public_pem)

    Exits:
        With error message if out_path exists and force=False.
        With error message if key generation or serialization fails.
    """
    if out_path.exists() and not force:
        sys.exit(f"Error: {out_path} already exists. Use --force to overwrite.")

    try:
        # Generate fresh Ed25519 keypair
        private_key = ed25519.Ed25519PrivateKey.generate()

        # Serialize private key to PEM (PKCS8, unencrypted)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Extract and serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Write private key to file with secure permissions
        out_path.write_bytes(private_pem)
        out_path.chmod(0o600)

        return (private_pem, public_pem)

    except Exception as e:
        sys.exit(f"Error: failed to generate keypair: {e}")


def _build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate Ed25519 keypair for wheel manifest signing"
    )
    parser.add_argument(
        "--out",
        default="./wheel_signing.key",
        help="Output path for private key (default: ./wheel_signing.key)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing key file"
    )
    return parser


def main():
    """Main entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    # Generate keypair
    out_path = Path(args.out)
    private_pem, public_pem = generate_keypair(out_path, args.force)

    # Print status to stderr
    print(f"[keygen] Private key written to: {out_path} with mode 0600", file=sys.stderr)
    print(
        "[keygen] Public key (copy below into ee/__init__.py as _MANIFEST_PUBLIC_KEY_PEM):",
        file=sys.stderr
    )

    # Print public key as Python bytes literal to stdout
    public_pem_str = public_pem.decode()
    print(f'b"""{public_pem_str}"""')


if __name__ == "__main__":
    main()
