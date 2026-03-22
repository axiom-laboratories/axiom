"""
Phase 47 — CE Runtime Expansion: Test scaffold (Wave 0)
Uses source inspection to verify implementation correctness without live DB/runtime deps.
Tests RT-01 through RT-07 requirements.
"""
import sys
import pytest
from pathlib import Path

# Locate repo root relative to this test file (tests/ is inside puppeteer/)
PUPPETEER_DIR = Path(__file__).parents[1]
REPO_ROOT = PUPPETEER_DIR.parent
PUPPETS_DIR = REPO_ROOT / "puppets"
AGENT_SERVICE_DIR = PUPPETEER_DIR / "agent_service"


# ---------------------------------------------------------------------------
# RT-03: Containerfile.node ships PowerShell Core via Microsoft APT repo
# ---------------------------------------------------------------------------

def test_containerfile_has_powershell():
    """RT-03: Containerfile.node must install PowerShell Core via Microsoft APT repo."""
    containerfile = PUPPETS_DIR / "Containerfile.node"
    assert containerfile.exists(), f"Containerfile.node not found at {containerfile}"
    content = containerfile.read_text()
    assert "powershell" in content, (
        "Containerfile.node must install powershell package. "
        "Expected 'powershell' in apt-get install line."
    )
    assert "packages-microsoft-prod.deb" in content, (
        "Containerfile.node must register the Microsoft APT repository via "
        "packages-microsoft-prod.deb before installing powershell."
    )


# ---------------------------------------------------------------------------
# RT-01: node.py execute_task handles task_type == 'script' for bash runtime
# ---------------------------------------------------------------------------

def test_bash_job_accepted():
    """RT-01: node.py script branch must handle 'bash' runtime with .sh extension."""
    node_py = PUPPETS_DIR / "environment_service" / "node.py"
    assert node_py.exists(), f"node.py not found at {node_py}"
    source = node_py.read_text()

    assert 'task_type == "script"' in source, (
        "node.py must have a 'task_type == \"script\"' branch in execute_task. "
        "The unified script branch replaces the old python_script branch."
    )
    assert '"bash"' in source or "'bash'" in source, (
        "node.py script branch must include 'bash' in cmd_map or runtime handling."
    )
    assert '"sh"' in source or "'sh'" in source, (
        "node.py script branch must use .sh extension for bash runtime in ext_map."
    )


# ---------------------------------------------------------------------------
# RT-02: node.py execute_task handles task_type == 'script' for powershell runtime
# ---------------------------------------------------------------------------

def test_powershell_job_accepted():
    """RT-02: node.py script branch must handle 'powershell' runtime with .ps1 extension."""
    node_py = PUPPETS_DIR / "environment_service" / "node.py"
    source = node_py.read_text()

    assert "pwsh" in source, (
        "node.py script branch must use 'pwsh' as the PowerShell Core binary name."
    )
    assert '"ps1"' in source or "'ps1'" in source, (
        "node.py script branch must use .ps1 extension for powershell runtime in ext_map."
    )


# ---------------------------------------------------------------------------
# RT-01/RT-02: Temp-file execution with cleanup
# ---------------------------------------------------------------------------

def test_node_script_execution():
    """RT-01/RT-02: script branch must write to temp file, mount it, and clean up in finally."""
    node_py = PUPPETS_DIR / "environment_service" / "node.py"
    source = node_py.read_text()

    assert "tmp_path" in source, (
        "node.py script branch must use a tmp_path variable for the temp script file."
    )
    # Temp file should be mounted (not passed via stdin/input_data)
    assert "tmp_path}:{tmp_path}" in source or "tmp_path}:" in source, (
        "node.py must add tmp_path to mounts list as 'tmp_path:tmp_path:ro' for container access."
    )
    # Cleanup in finally block
    assert "os.path.exists(tmp_path)" in source, (
        "node.py must check os.path.exists(tmp_path) before removing it in the finally block."
    )
    assert "os.remove(tmp_path)" in source, (
        "node.py must call os.remove(tmp_path) in a finally block to clean up the temp script."
    )


# ---------------------------------------------------------------------------
# RT-05: Invalid runtime rejected before queue entry (model validation)
# ---------------------------------------------------------------------------

def test_invalid_runtime_rejected():
    """RT-05: JobPushRequest/JobDispatchRequest must enforce runtime enum via field validator."""
    models_py = AGENT_SERVICE_DIR / "models.py"
    assert models_py.exists(), f"models.py not found at {models_py}"
    source = models_py.read_text()

    # Must have a validator that restricts the runtime field
    has_validator = (
        "model_validator" in source or
        "field_validator" in source or
        "@validator" in source
    )
    assert has_validator, (
        "models.py must use a pydantic validator (model_validator, field_validator, or @validator) "
        "to enforce the runtime field enum."
    )
    # The runtime field must only allow known values
    assert "runtime" in source, (
        "models.py must include a 'runtime' field on job request/dispatch models."
    )
    # Must reference the valid runtimes (python, bash, powershell)
    assert "powershell" in source or "POWERSHELL" in source, (
        "models.py runtime validator must reference 'powershell' as a valid runtime value."
    )


# ---------------------------------------------------------------------------
# RT-04: display_type computed server-side (job_service)
# ---------------------------------------------------------------------------

def test_display_type_computed_serverside():
    """RT-04: job_service must compute display_type from (task_type, runtime) server-side."""
    job_service_py = AGENT_SERVICE_DIR / "services" / "job_service.py"
    assert job_service_py.exists(), f"job_service.py not found at {job_service_py}"
    source = job_service_py.read_text()

    assert "_compute_display_type" in source or "compute_display_type" in source, (
        "job_service.py must define a '_compute_display_type' (or similar) function "
        "that derives the UI display label from task_type and runtime."
    )
    assert "display_type" in source, (
        "job_service.py must include 'display_type' key in the job list/detail response dict."
    )


# ---------------------------------------------------------------------------
# RT-07: ScheduledJob has runtime column; scheduler fires script task_type
# ---------------------------------------------------------------------------

def test_scheduled_job_runtime_field():
    """RT-07: ScheduledJob DB model must have a 'runtime' column; scheduler must use task_type='script'."""
    db_py = AGENT_SERVICE_DIR / "db.py"
    assert db_py.exists(), f"db.py not found at {db_py}"
    db_source = db_py.read_text()

    # Find the ScheduledJob class definition and check for runtime column
    # We look for 'runtime' appearing after the class ScheduledJob line
    sched_job_idx = db_source.find("class ScheduledJob")
    assert sched_job_idx != -1, "ScheduledJob class not found in db.py"
    # Check runtime column appears in the class body (next class starts after)
    next_class_idx = db_source.find("\nclass ", sched_job_idx + 1)
    sched_job_body = db_source[sched_job_idx:next_class_idx] if next_class_idx != -1 else db_source[sched_job_idx:]
    assert "runtime" in sched_job_body, (
        "ScheduledJob DB model in db.py must have a 'runtime' column "
        "(e.g., 'runtime: Mapped[str] = mapped_column(String, default=\"python\")')."
    )

    scheduler_py = AGENT_SERVICE_DIR / "services" / "scheduler_service.py"
    assert scheduler_py.exists(), f"scheduler_service.py not found at {scheduler_py}"
    sched_source = scheduler_py.read_text()

    assert 'task_type="script"' in sched_source or "task_type='script'" in sched_source, (
        "scheduler_service.py must dispatch scheduled jobs with task_type='script' "
        "(replacing the old 'python_script' task_type)."
    )
