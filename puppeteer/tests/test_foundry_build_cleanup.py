"""
MIN-07 Regression Tests — Build Directory Cleanup.

Verifies that FoundryService.build_template() always calls shutil.rmtree on the
build directory, whether the build succeeds or raises an exception.

These tests work in both CE and EE environments by mocking the EE-only DB
models (Blueprint, PuppetTemplate, etc.) via sys.modules before importing
foundry_service. The pattern is necessary because the EE model classes only
exist when the Axiom EE package is installed.
"""
import json
import sys
import shutil
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, mock_open

import pytest


# ── EE Model Stubs (inject before any agent_service import) ───────────────────
#
# foundry_service.py does: from ..db import Blueprint, PuppetTemplate, ...
# These models only exist in the compiled EE .so.  We inject lightweight stubs
# so the module can be imported and tested without the EE package.

def _make_ee_model_class():
    """Return a MagicMock that behaves like a SQLAlchemy ORM class stub.

    When foundry_service does ``PuppetTemplate.id == template_id`` the class
    attribute ``id`` must be accessible.  A plain ``MagicMock()`` instance
    supports arbitrary attribute access, so we return one here instead of the
    raw ``MagicMock`` class.
    """
    return MagicMock()


def _make_ee_db_stub():
    """Return a MagicMock module that satisfies foundry_service's db imports."""
    stub = MagicMock()
    stub.Blueprint = _make_ee_model_class()
    stub.PuppetTemplate = _make_ee_model_class()
    stub.CapabilityMatrix = _make_ee_model_class()
    stub.ApprovedIngredient = _make_ee_model_class()
    stub.Config = _make_ee_model_class()
    stub.AsyncSession = MagicMock()
    stub.ImageBOM = _make_ee_model_class()
    stub.PackageIndex = _make_ee_model_class()
    stub.ApprovedOS = _make_ee_model_class()
    return stub


def _make_ee_models_stub():
    """Return a MagicMock that satisfies foundry_service's models imports."""
    stub = MagicMock()
    stub.ImageBuildRequest = MagicMock
    stub.ImageResponse = MagicMock
    return stub


# Inject stubs if the EE classes are not present
import agent_service.db as _real_db
if not hasattr(_real_db, "Blueprint"):
    sys.modules["agent_service.db"] = _make_ee_db_stub()  # type: ignore[assignment]

import agent_service.models as _real_models
if not hasattr(_real_models, "ImageBuildRequest"):
    sys.modules["agent_service.models"] = _make_ee_models_stub()  # type: ignore[assignment]

# Now the import will succeed in both CE and EE
from agent_service.services.foundry_service import FoundryService  # noqa: E402


# ── DB Mock Helpers ────────────────────────────────────────────────────────────


def _make_scalar_one_result(val):
    """Result for queries using scalar_one_or_none()."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = val
    return m


def _make_scalars_all_result(vals):
    """Result for queries using scalars().all()."""
    m = MagicMock()
    m.scalars.return_value.all.return_value = vals
    return m


def _make_mock_db(tmpl, rt_bp, nw_bp):
    """
    Returns an AsyncMock db for a build with no python packages.

    Query order in build_template:
      1. SELECT PuppetTemplate            — scalar_one_or_none
      2. SELECT Blueprint (runtime)       — scalar_one_or_none
      3. SELECT Blueprint (network)       — scalar_one_or_none
      4. SELECT Config smelter_mode       — scalar_one_or_none
      5. validate_blueprint approved list — scalars().all()
    """
    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        _make_scalar_one_result(tmpl),       # 1. SELECT PuppetTemplate
        _make_scalar_one_result(rt_bp),      # 2. SELECT Blueprint (runtime)
        _make_scalar_one_result(nw_bp),      # 3. SELECT Blueprint (network)
        _make_scalar_one_result("WARNING"),  # 4. SELECT Config smelter_enforcement_mode
        _make_scalars_all_result([]),        # 5. validate_blueprint: no packages to validate
    ]
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    return mock_db


# ── Fixtures ───────────────────────────────────────────────────────────────────


def _make_fixtures():
    """Return minimal template + blueprints with empty python packages."""
    tmpl = MagicMock()
    tmpl.id = "t1"
    tmpl.friendly_name = "cleanup-test"
    tmpl.runtime_blueprint_id = "rt1"
    tmpl.network_blueprint_id = "nw1"
    tmpl.is_compliant = True
    tmpl.current_image_uri = None
    tmpl.last_built_at = None
    tmpl.status = "PENDING"

    rt_bp = MagicMock()
    rt_bp.id = "rt1"
    rt_bp.definition = json.dumps({
        "base_os": "python:3.12-slim",
        "tools": [],
        "packages": {"python": []},
    })
    rt_bp.os_family = "DEBIAN"

    nw_bp = MagicMock()
    nw_bp.id = "nw1"
    nw_bp.definition = json.dumps({"egress_rules": []})

    return tmpl, rt_bp, nw_bp


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_dir_cleaned_up_on_success():
    """
    MIN-07: shutil.rmtree must be called on the build dir after a successful build.

    Patches all filesystem and subprocess calls so no real I/O occurs.
    Asserts that rmtree was called and that its path argument contains 'puppet_build'.
    """
    tmpl, rt_bp, nw_bp = _make_fixtures()
    mock_db = _make_mock_db(tmpl, rt_bp, nw_bp)

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"Build complete", None)
    mock_proc.returncode = 0

    mock_push_proc = AsyncMock()
    mock_push_proc.communicate.return_value = (b"", None)

    # create_subprocess_exec is called twice: docker build + docker push
    subprocess_calls = [mock_proc, mock_push_proc]

    with patch("shutil.rmtree") as mock_rmtree, \
         patch("agent_service.services.foundry_service.select",
               return_value=MagicMock()), \
         patch("agent_service.services.foundry_service.subprocess.run",
               side_effect=FileNotFoundError("podman not found")), \
         patch("agent_service.services.foundry_service.os.path.exists",
               return_value=True), \
         patch("agent_service.services.foundry_service.os.path.isdir",
               return_value=True), \
         patch("agent_service.services.foundry_service.os.path.isfile",
               return_value=True), \
         patch("agent_service.services.foundry_service.os.makedirs"), \
         patch("agent_service.services.foundry_service.shutil.copytree"), \
         patch("agent_service.services.foundry_service.shutil.copy2"), \
         patch("builtins.open", mock_open()), \
         patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread, \
         patch("asyncio.create_subprocess_exec",
               side_effect=subprocess_calls), \
         patch("agent_service.services.foundry_service.StagingService.run_smelt_check",
               new_callable=AsyncMock,
               return_value={"status": "SUCCESS"}), \
         patch("agent_service.services.foundry_service.StagingService.capture_bom",
               new_callable=AsyncMock):

        # asyncio.to_thread wraps blocking calls (makedirs, copytree, copy2, rmtree).
        # Forward each call so shutil.rmtree mock is invoked correctly.
        async def fake_to_thread(fn, *args, **kwargs):
            fn(*args, **kwargs)

        mock_to_thread.side_effect = fake_to_thread

        await FoundryService.build_template("t1", mock_db)

    assert mock_rmtree.called, (
        "shutil.rmtree must be called after a successful build (MIN-07)"
    )
    rmtree_path = str(mock_rmtree.call_args[0][0])
    assert "puppet_build" in rmtree_path, (
        f"rmtree path must contain 'puppet_build', got: {rmtree_path!r}"
    )


@pytest.mark.asyncio
async def test_build_dir_cleaned_up_on_failure():
    """
    MIN-07: shutil.rmtree must be called on the build dir even when the build raises.

    Simulates a subprocess failure (RuntimeError) and verifies the finally block
    still invokes cleanup.
    """
    tmpl, rt_bp, nw_bp = _make_fixtures()
    mock_db = _make_mock_db(tmpl, rt_bp, nw_bp)

    with patch("shutil.rmtree") as mock_rmtree, \
         patch("agent_service.services.foundry_service.select",
               return_value=MagicMock()), \
         patch("agent_service.services.foundry_service.subprocess.run",
               side_effect=FileNotFoundError("podman not found")), \
         patch("agent_service.services.foundry_service.os.path.exists",
               return_value=True), \
         patch("agent_service.services.foundry_service.os.path.isdir",
               return_value=True), \
         patch("agent_service.services.foundry_service.os.path.isfile",
               return_value=True), \
         patch("agent_service.services.foundry_service.os.makedirs"), \
         patch("agent_service.services.foundry_service.shutil.copytree"), \
         patch("agent_service.services.foundry_service.shutil.copy2"), \
         patch("builtins.open", mock_open()), \
         patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread, \
         patch("asyncio.create_subprocess_exec",
               side_effect=RuntimeError("simulated docker failure")):

        async def fake_to_thread(fn, *args, **kwargs):
            fn(*args, **kwargs)

        mock_to_thread.side_effect = fake_to_thread

        try:
            await FoundryService.build_template("t1", mock_db)
        except Exception:
            pass  # Expected — we triggered a RuntimeError

    assert mock_rmtree.called, (
        "shutil.rmtree must be called in the finally block even when build raises (MIN-07)"
    )
