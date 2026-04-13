"""Unit tests for key resolution pattern in wheel signing tools."""

import pytest
import os
from pathlib import Path


def test_key_resolution_from_arg(test_keypair):
    """Key resolution follows issue_licence.py pattern: --key arg takes priority."""
    assert False, "TODO: implement key arg resolution test"


def test_key_resolution_from_env(test_keypair):
    """Key resolution falls back to AXIOM_WHEEL_SIGNING_KEY env var if no --key."""
    assert False, "TODO: implement key env resolution test"


def test_key_resolution_missing(capsys):
    """Key resolution exits with clear error if neither --key nor env var provided."""
    assert False, "TODO: implement missing key error test"


def test_key_file_not_found(capsys):
    """Key resolution exits with clear error if key file doesn't exist."""
    assert False, "TODO: implement file not found error test"


def test_key_load_failure(temp_wheel_dir, capsys):
    """Key resolution exits with clear error if PEM is malformed."""
    assert False, "TODO: implement PEM load failure test"


def test_key_resolution_private_to_public_fallback(temp_wheel_dir, test_keypair):
    """Key resolution in public mode falls back to public key if private key fails."""
    assert False, "TODO: implement private-to-public fallback test"
