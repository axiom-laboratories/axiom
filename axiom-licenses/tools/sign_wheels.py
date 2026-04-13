#!/usr/bin/env python3
"""sign_wheels.py — Sign EE wheels and verify wheel+manifest pairs.

Release-time tool that signs all .whl files in a directory, producing
per-wheel manifest files compatible with Phase 137's _verify_wheel_manifest().

Usage:
    # Sign all wheels in dist/ directory
    python tools/sign_wheels.py --wheels-dir dist/ --key keys/wheel_signing.key

    # Sign and create deploy-name copy for container /tmp/ deployment
    python tools/sign_wheels.py --wheels-dir dist/ --key keys/wheel_signing.key --deploy-name

    # Verify all wheel+manifest pairs
    python tools/sign_wheels.py --verify --wheels-dir dist/ --key keys/wheel_signing.public.pem

    # Quiet mode (suppress per-wheel summary output)
    python tools/sign_wheels.py --wheels-dir dist/ --key keys/wheel_signing.key --quiet

Key resolution (in priority order):
    1. --key <path>
    2. AXIOM_WHEEL_SIGNING_KEY env var
"""

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def hash_wheel(wheel_path: str) -> str:
    """Compute SHA256 of wheel file in 64KB chunks (matching Phase 137 pattern).

    Args:
        wheel_path: Path to .whl file

    Returns:
        str: Lowercase hexadecimal digest

    Exits:
        With error message if file cannot be read.
    """
    try:
        sha256_hash = hashlib.sha256()
        with open(wheel_path, 'rb') as f:
            while chunk := f.read(65536):  # 64KB chunks
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except OSError as e:
        sys.exit(f"Error: failed to hash wheel {wheel_path}: {e}")


def resolve_key(args, mode: str = "private"):
    """Resolve signing/verification key from --key arg or env var.

    Args:
        args: Parsed arguments (must have .key attribute)
        mode: "private" to load private key for signing, "public" for verification

    Returns:
        Ed25519PrivateKey or Ed25519PublicKey instance

    Exits:
        With error message if no key provided or file not found/invalid.
    """
    key_source = args.key or os.getenv("AXIOM_WHEEL_SIGNING_KEY")
    if not key_source:
        sys.exit(
            "Error: no signing key provided.\n"
            "Set AXIOM_WHEEL_SIGNING_KEY env var or pass --key <path>."
        )

    path = Path(key_source)
    if not path.exists():
        sys.exit(f"Error: key file not found: {path}")

    try:
        key_bytes = path.read_bytes()

        # If mode is "public", try private first (to be flexible), then public
        if mode == "public":
            try:
                return serialization.load_pem_private_key(key_bytes, password=None)
            except Exception:
                return serialization.load_pem_public_key(key_bytes)
        else:
            # mode == "private"
            return serialization.load_pem_private_key(key_bytes, password=None)

    except Exception as e:
        sys.exit(f"Error: failed to load key from {path}: {e}")


def sign_wheels(
    wheels_dir: Path,
    private_key,
    deploy_name: bool = False,
    quiet: bool = False
) -> None:
    """Sign all .whl files in directory, producing per-wheel manifest files.

    Args:
        wheels_dir: Directory containing .whl files
        private_key: Ed25519PrivateKey instance
        deploy_name: If True, also write axiom_ee.manifest.json (fixed name for container)
        quiet: If True, suppress per-wheel summary output

    Exits:
        With error code 1 if no wheels found.
    """
    wheels = sorted(wheels_dir.glob("*.whl"))

    if not wheels:
        sys.exit(f"Error: no .whl files found in {wheels_dir}")

    for wheel_path in wheels:
        # Compute SHA256 of wheel
        sha256_hex = hash_wheel(str(wheel_path))

        # Sign the UTF-8 hex string (not raw bytes)
        message = sha256_hex.encode('utf-8')
        signature_bytes = private_key.sign(message)
        signature_b64 = base64.b64encode(signature_bytes).decode('ascii')

        # Build manifest dict
        manifest = {
            "sha256": sha256_hex,
            "signature": signature_b64
        }

        # Write versioned manifest (matching wheel filename)
        manifest_path = wheel_path.with_suffix(".manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2))

        if not quiet:
            print(f"Signed: {manifest_path.name} (sha256: {sha256_hex[:16]}...)", file=sys.stderr)

        # If --deploy-name: also write axiom_ee.manifest.json
        if deploy_name:
            deploy_path = wheels_dir / "axiom_ee.manifest.json"
            deploy_path.write_text(manifest_path.read_text())


def verify_manifests(wheels_dir: Path, public_key) -> bool:
    """Verify all wheel+manifest pairs in a directory.

    Args:
        wheels_dir: Directory containing .whl files and .manifest.json files
        public_key: Ed25519PublicKey instance

    Returns:
        bool: True if all wheels verified successfully, False if any failed.
    """
    wheels = sorted(wheels_dir.glob("*.whl"))
    all_passed = True

    for wheel_path in wheels:
        manifest_path = wheel_path.with_suffix(".manifest.json")

        # Check if manifest exists
        if not manifest_path.exists():
            print(f"FAIL: {manifest_path.name} — manifest file not found")
            all_passed = False
            continue

        try:
            # Load manifest JSON
            manifest = json.loads(manifest_path.read_text())

            # Verify required fields
            if "sha256" not in manifest or "signature" not in manifest:
                print(f"FAIL: {manifest_path.name} — missing sha256 or signature field")
                all_passed = False
                continue

            # Compute SHA256 of wheel
            sha256_hex = hash_wheel(str(wheel_path))

            # Check SHA256 matches
            if sha256_hex != manifest["sha256"]:
                print(f"FAIL: {manifest_path.name} — SHA256 mismatch")
                all_passed = False
                continue

            # Decode signature from base64
            try:
                signature_bytes = base64.b64decode(manifest["signature"])
            except Exception as e:
                print(f"FAIL: {manifest_path.name} — failed to decode signature: {e}")
                all_passed = False
                continue

            # Verify Ed25519 signature
            try:
                message = sha256_hex.encode('utf-8')
                public_key.verify(signature_bytes, message)
                print(f"OK: {manifest_path.name}")
            except Exception as e:
                print(f"FAIL: {manifest_path.name} — signature verification failed: {e}")
                all_passed = False

        except json.JSONDecodeError as e:
            print(f"FAIL: {manifest_path.name} — invalid JSON: {e}")
            all_passed = False
        except Exception as e:
            print(f"FAIL: {manifest_path.name} — unexpected error: {e}")
            all_passed = False

    return all_passed


def _build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        description="Sign EE wheel manifests with Ed25519 key"
    )
    parser.add_argument(
        "--wheels-dir",
        required=True,
        dest="wheels_dir",
        help="Directory containing .whl files to sign"
    )
    parser.add_argument(
        "--key",
        default=None,
        help="Path to private key PEM file (or set AXIOM_WHEEL_SIGNING_KEY)"
    )
    parser.add_argument(
        "--deploy-name",
        action="store_true",
        dest="deploy_name",
        help="Also write axiom_ee.manifest.json (fixed name for /tmp/ deployment)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify all wheel+manifest pairs (requires --key to be public PEM)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-wheel summary output"
    )
    return parser


def main():
    """Main entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    wheels_dir = Path(args.wheels_dir)

    if args.verify:
        # Verification mode: resolve public key and verify all manifests
        public_key = resolve_key(args, mode="public")
        all_passed = verify_manifests(wheels_dir, public_key)
        sys.exit(0 if all_passed else 1)
    else:
        # Signing mode: resolve private key and sign all wheels
        private_key = resolve_key(args, mode="private")
        sign_wheels(wheels_dir, private_key, args.deploy_name, args.quiet)
        sys.exit(0)


if __name__ == "__main__":
    main()
