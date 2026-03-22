"""
DEBT-04: Node ID selection from secrets/ must be deterministic.

The _load_or_generate_node_id() function in node.py uses sorted() when
iterating over the secrets directory listing, ensuring that filesystem
readdir order (which varies by OS/filesystem) does not affect which
certificate identity is reused after a container restart.

These tests verify the function behavior by extracting and running the function
body directly with mocked I/O (to avoid importing node.py's many side-effect
dependencies like aiohttp, psutil, etc.).
"""
import os
import sys
import uuid
import types
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Extract the function under test without importing the full module
# ---------------------------------------------------------------------------

def _extract_function() -> callable:
    """
    Extract _load_or_generate_node_id from node.py by parsing its source
    and executing only the relevant function definition in a minimal namespace.
    """
    node_py = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "puppets",
            "environment_service", "node.py"
        )
    )
    with open(node_py, "r") as f:
        source = f.read()

    # Find the function definition
    fn_start = source.find("def _load_or_generate_node_id")
    assert fn_start != -1, "_load_or_generate_node_id not found in node.py"

    # Extract lines until the next top-level definition or end of file
    lines = source[fn_start:].splitlines()
    fn_lines = [lines[0]]  # Start with the def line
    for line in lines[1:]:
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        fn_lines.append(line)
    fn_source = "\n".join(fn_lines)

    # Execute in a minimal namespace with only what the function needs
    namespace = {
        "os": os,
        "uuid": uuid,
    }
    exec(fn_source, namespace)
    return namespace["_load_or_generate_node_id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_deterministic_selection_returns_alphabetically_first():
    """When multiple node-*.crt files exist, returns alphabetically first node ID."""
    fn = _extract_function()

    # Files returned in a non-alphabetical order (simulating filesystem entropy)
    mock_files = ["node-zzz.crt", "node-aaa.crt", "node-mmm.crt", "other.txt", "node-bbb.key"]

    with patch("os.makedirs"), \
         patch("os.listdir", return_value=mock_files):
        result = fn()

    assert result == "node-aaa", (
        f"Expected 'node-aaa' (alphabetically first), got '{result}'"
    )


def test_only_node_crt_files_are_considered():
    """Files not matching 'node-*.crt' pattern are ignored."""
    fn = _extract_function()

    mock_files = [
        "node-xyz.crt",      # valid
        "node-abc.key",      # wrong extension
        "other-node.crt",    # wrong prefix
        "README.txt",        # irrelevant
        "node-def.crt.bak",  # not .crt
    ]

    with patch("os.makedirs"), \
         patch("os.listdir", return_value=mock_files):
        result = fn()

    assert result == "node-xyz", (
        f"Expected 'node-xyz' (only valid .crt file), got '{result}'"
    )


def test_generates_new_id_when_no_certs_exist():
    """When no node-*.crt files exist, a fresh UUID-based ID is generated."""
    fn = _extract_function()

    mock_files = ["some_other_file.txt", "cert.pem"]

    with patch("os.makedirs"), \
         patch("os.listdir", return_value=mock_files):
        result = fn()

    assert result.startswith("node-"), (
        f"Generated ID should start with 'node-', got '{result}'"
    )
    suffix = result[len("node-"):]
    assert len(suffix) == 8, f"Expected 8-char hex suffix, got '{suffix}'"
    assert all(c in "0123456789abcdef" for c in suffix), (
        f"Suffix should be hex, got '{suffix}'"
    )


def test_reverse_filesystem_order_still_returns_first_alphabetically():
    """Reverse-sorted filesystem listing still yields the alphabetically first cert."""
    fn = _extract_function()

    # Reverse alphabetical order from the filesystem
    mock_files = ["node-zzz.crt", "node-mmm.crt", "node-bbb.crt", "node-aaa.crt"]

    with patch("os.makedirs"), \
         patch("os.listdir", return_value=mock_files):
        result = fn()

    assert result == "node-aaa", (
        f"Expected 'node-aaa' regardless of listdir order, got '{result}'"
    )


def test_sorted_call_is_used_in_source():
    """Verify the source code of node.py contains sorted() in _load_or_generate_node_id.

    This is a code-level assertion confirming DEBT-04 is fixed at the source level.
    """
    node_py = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "puppets",
            "environment_service", "node.py"
        )
    )
    assert os.path.exists(node_py), f"node.py not found at {node_py}"

    with open(node_py, "r") as f:
        source = f.read()

    fn_start = source.find("def _load_or_generate_node_id")
    assert fn_start != -1, "_load_or_generate_node_id not found in node.py"

    fn_slice = source[fn_start:fn_start + 400]
    assert "sorted(" in fn_slice, (
        "sorted() must be called within _load_or_generate_node_id to ensure "
        "deterministic node ID selection (DEBT-04)"
    )
