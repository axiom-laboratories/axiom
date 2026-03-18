"""
TDD tests for Phase 29 direct mode startup guard requirement.
The 'direct' execution mode bypass has been removed; nodes raise
a clear RuntimeError at startup if EXECUTION_MODE=direct is set.
"""
import sys
import os
import subprocess
import pytest


_NODE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "puppets", "environment_service")
)
_RUNTIME_PATH = os.path.join(_NODE_DIR, "runtime.py")
_NODE_PATH = os.path.join(_NODE_DIR, "node.py")


def test_direct_mode_raises_on_startup():
    """EXECUTION_MODE=direct must cause a RuntimeError when node.py is imported.
    The _check_execution_mode() function is called at module level and raises
    before any network or filesystem operations occur."""
    # Run a minimal Python process that sets EXECUTION_MODE=direct and calls
    # _check_execution_mode() directly from node.py source (safe extraction).
    script = f"""
import sys
sys.path.insert(0, {_NODE_DIR!r})
import os
os.environ['EXECUTION_MODE'] = 'direct'

# Extract and exec only the _check_execution_mode definition + call
import ast, textwrap

with open({_NODE_PATH!r}) as f:
    src = f.read()

tree = ast.parse(src)
# Find the _check_execution_mode function definition
fn_src = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == '_check_execution_mode':
        fn_src = ast.get_source_segment(src, node)
        break

assert fn_src is not None, "_check_execution_mode not found in node.py"
exec(fn_src)
_check_execution_mode()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0, (
        f"Expected RuntimeError when EXECUTION_MODE=direct, but process exited 0. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "no longer supported" in result.stderr, (
        f"Expected 'no longer supported' in stderr, got: {result.stderr!r}"
    )


def test_runtime_py_has_no_direct_execution_path():
    """runtime.py must contain no 'direct' string in execution logic."""
    with open(_RUNTIME_PATH) as f:
        source = f.read()
    assert '"direct"' not in source and "'direct'" not in source, (
        "runtime.py still contains a 'direct' mode reference in execution code"
    )
