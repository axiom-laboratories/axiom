"""
Tests for the operator-facing example job corpus (Phase 83 — Node Validation Job Library).

Wave 0 scaffold: all 8 tests are written here before the scripts exist so that
every script is covered by an automated check from the moment it is committed.

Tests that check files not yet committed will fail with a clear pytest.fail()
message (not an error) until the corresponding files are added.
"""
import os
import sys
import subprocess
import pathlib
import pytest


# ---------------------------------------------------------------------------
# Locate repository root
# ---------------------------------------------------------------------------

def _find_repo_root() -> pathlib.Path:
    """Walk up from this file until we find a directory that contains tools/."""
    current = pathlib.Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "tools").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    # Fallback: use REPO_ROOT env var or git root
    repo_root_env = os.environ.get("REPO_ROOT")
    if repo_root_env:
        return pathlib.Path(repo_root_env)
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        cwd=pathlib.Path(__file__).parent,
    )
    if result.returncode == 0:
        return pathlib.Path(result.stdout.strip())
    raise RuntimeError("Cannot locate repository root — no tools/ directory found")


REPO_ROOT = _find_repo_root()
JOBS_DIR = REPO_ROOT / "tools" / "example-jobs"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _read_script(rel_path: str) -> str:
    """Read a script file relative to JOBS_DIR. Call pytest.fail on missing."""
    p = JOBS_DIR / rel_path
    if not p.exists():
        pytest.fail(
            f"File not found: {p}\n"
            f"Expected at tools/example-jobs/{rel_path} — has it been committed?"
        )
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Hello-world jobs (JOB-01, JOB-02, JOB-03)
# ---------------------------------------------------------------------------

def test_hello_bash():
    """bash/hello.sh must have correct shebang, hostname, OS, Bash version, and PASS marker."""
    content = _read_script("bash/hello.sh")
    assert "#!/usr/bin/env bash" in content, "Missing bash shebang"
    assert "=== PASS ===" in content, "Missing === PASS === marker"
    assert "hostname" in content, "Missing hostname output"
    assert "uname" in content, "Missing uname (OS) output"
    assert "BASH_VERSION" in content, "Missing BASH_VERSION reference"


def test_hello_python():
    """python/hello.py must have correct shebang, socket, platform, and PASS marker."""
    content = _read_script("python/hello.py")
    assert "#!/usr/bin/env python3" in content, "Missing python3 shebang"
    assert "=== PASS ===" in content, "Missing === PASS === marker"
    assert "socket.gethostname()" in content, "Missing socket.gethostname() call"
    assert "platform.python_version()" in content, "Missing platform.python_version() call"


def test_hello_pwsh():
    """pwsh/hello.ps1 must have Write-Host calls and PASS marker."""
    content = _read_script("pwsh/hello.ps1")
    assert "Write-Host" in content, "Missing Write-Host calls"
    assert "=== PASS ===" in content, "Missing === PASS === marker"
    # PSVersionTable.PSVersion or just PSVersion / PSVersionTable
    assert "PSVersion" in content or "PSVersionTable" in content, (
        "Missing PSVersionTable or PSVersion reference"
    )


# ---------------------------------------------------------------------------
# Validation jobs (JOB-04, JOB-05, JOB-06, JOB-07) — stubs for Plan 02
# ---------------------------------------------------------------------------

def test_volume_mapping():
    """validation/volume-mapping.sh must use AXIOM_VOLUME_PATH and write a sentinel."""
    content = _read_script("validation/volume-mapping.sh")
    assert "AXIOM_VOLUME_PATH" in content, "Missing AXIOM_VOLUME_PATH variable"
    # Sentinel write logic: something that writes to the path
    assert ">" in content or "tee" in content or "echo" in content, (
        "Missing write logic (expected >, tee, or echo)"
    )
    assert "=== PASS" in content, "Missing PASS marker"


def test_network_filter():
    """validation/network-filter.py must test blocked host and exit 1 on success."""
    content = _read_script("validation/network-filter.py")
    assert "AXIOM_BLOCKED_HOST" in content, "Missing AXIOM_BLOCKED_HOST variable"
    assert "socket.create_connection" in content, "Missing socket.create_connection call"
    assert "sys.exit(1)" in content, "Missing sys.exit(1) — expected when connection succeeds (bad)"


def test_memory_hog_no_cap():
    """validation/memory-hog.py must exit 1 with resource_limits_supported in output when capability absent."""
    script_path = JOBS_DIR / "validation" / "memory-hog.py"
    if not script_path.exists():
        pytest.fail(
            f"File not found: {script_path}\n"
            "Expected at tools/example-jobs/validation/memory-hog.py — has it been committed?"
        )
    env = {**os.environ, "AXIOM_CAPABILITIES": ""}
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 1, (
        f"Expected exit code 1 (missing capability), got {result.returncode}.\nOutput: {combined}"
    )
    assert "resource_limits_supported" in combined, (
        f"Expected 'resource_limits_supported' in output.\nOutput: {combined}"
    )


def test_cpu_spin_no_cap():
    """validation/cpu-spin.py must exit 1 with resource_limits_supported in output when capability absent."""
    script_path = JOBS_DIR / "validation" / "cpu-spin.py"
    if not script_path.exists():
        pytest.fail(
            f"File not found: {script_path}\n"
            "Expected at tools/example-jobs/validation/cpu-spin.py — has it been committed?"
        )
    env = {**os.environ, "AXIOM_CAPABILITIES": ""}
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 1, (
        f"Expected exit code 1 (missing capability), got {result.returncode}.\nOutput: {combined}"
    )
    assert "resource_limits_supported" in combined, (
        f"Expected 'resource_limits_supported' in output.\nOutput: {combined}"
    )


# ---------------------------------------------------------------------------
# Manifest (covers all 7 jobs)
# ---------------------------------------------------------------------------

def test_manifest_valid():
    """tools/example-jobs/manifest.yaml must be valid YAML with 7 entries, each having name/script/runtime."""
    yaml = pytest.importorskip("yaml", reason="PyYAML not installed — skipping manifest test")
    manifest_path = JOBS_DIR / "manifest.yaml"
    if not manifest_path.exists():
        pytest.fail(
            f"File not found: {manifest_path}\n"
            "Expected at tools/example-jobs/manifest.yaml — has it been committed?"
        )
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "manifest.yaml must be a mapping at top level"
    assert data.get("version") == "1", f"Expected version: '1', got {data.get('version')!r}"
    jobs = data.get("jobs", [])
    assert len(jobs) == 7, f"Expected 7 jobs in manifest, found {len(jobs)}"
    for job in jobs:
        assert "name" in job, f"Job entry missing 'name': {job}"
        assert "script" in job, f"Job entry missing 'script': {job}"
        assert "runtime" in job, f"Job entry missing 'runtime': {job}"
        script_path = JOBS_DIR / job["script"]
        assert script_path.exists(), (
            f"Script listed in manifest does not exist: {script_path}\n"
            f"Job entry: {job}"
        )
