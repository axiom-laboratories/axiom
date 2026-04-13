"""Unit tests for gen_wheel_key.py keypair generation script."""

import pytest
from pathlib import Path
from cryptography.hazmat.primitives import serialization


def test_generate_keypair(temp_wheel_dir, test_keypair):
    """gen_wheel_key.py generates a fresh Ed25519 keypair and writes private key to file."""
    assert False, "TODO: implement keypair generation test"


def test_no_overwrite_without_force(temp_wheel_dir):
    """gen_wheel_key.py refuses to overwrite existing key without --force flag."""
    assert False, "TODO: implement no-overwrite test"


def test_public_key_bytes_literal(temp_wheel_dir):
    """gen_wheel_key.py prints public key as Python bytes literal to stdout."""
    assert False, "TODO: implement public key format test"


def test_force_flag_overwrites(temp_wheel_dir):
    """gen_wheel_key.py overwrites existing key when --force is passed."""
    assert False, "TODO: implement force flag test"


def test_file_permissions_0600(temp_wheel_dir):
    """gen_wheel_key.py writes private key with mode 0600 (secure permissions)."""
    assert False, "TODO: implement permissions test"
