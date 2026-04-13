"""Unit tests for sign_wheels.py wheel signing and verification script."""

import pytest
import json
import base64
import subprocess
from pathlib import Path


def test_wheel_discovery(temp_wheel_dir, sample_wheel):
    """sign_wheels.py discovers all .whl files in input directory."""
    assert False, "TODO: implement wheel discovery test"


def test_wheel_hash_chunked(temp_wheel_dir, sample_wheel):
    """sign_wheels.py computes SHA256 of wheel bytes in 64KB chunks."""
    assert False, "TODO: implement chunked hash test"


def test_signature_format(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py signs SHA256 hex (UTF-8) with Ed25519, produces base64 signature."""
    assert False, "TODO: implement signature format test"


def test_manifest_naming(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py creates manifest JSON files matching wheel filenames."""
    assert False, "TODO: implement manifest naming test"


def test_deploy_name_flag(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py --deploy-name also writes axiom_ee.manifest.json."""
    assert False, "TODO: implement deploy-name test"


def test_no_wheels_error(temp_wheel_dir, test_keypair):
    """sign_wheels.py exits 1 if no wheels found."""
    assert False, "TODO: implement no-wheels error test"


def test_verify_mode(temp_wheel_dir, sample_wheel, sample_manifest, test_keypair):
    """sign_wheels.py --verify loads public key and verifies all manifests."""
    assert False, "TODO: implement verify mode test"


def test_verify_exit_codes(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py --verify exits 0 if all manifests verify, 1 if any fail."""
    assert False, "TODO: implement verify exit codes test"


def test_key_resolution_arg(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py resolves key from --key argument."""
    assert False, "TODO: implement key resolution arg test"


def test_key_resolution_env(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py resolves key from AXIOM_WHEEL_SIGNING_KEY env var."""
    assert False, "TODO: implement key resolution env test"


def test_quiet_flag(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py --quiet suppresses per-wheel summary output."""
    assert False, "TODO: implement quiet flag test"


def test_verify_sha256_mismatch(temp_wheel_dir, sample_wheel, sample_manifest):
    """sign_wheels.py --verify reports FAIL when SHA256 doesn't match."""
    assert False, "TODO: implement SHA256 mismatch test"
