import pytest
import json
import os
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from agent_service.services.foundry_service import FoundryService
from agent_service.db import PuppetTemplate, Blueprint, ApprovedIngredient, Config


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


def _make_mock_db(tmpl, rt_bp, nw_bp, ing, cfg_val="WARNING"):
    """
    Returns an AsyncMock db whose execute() returns responses in query order:
      1. Template lookup            — scalar_one_or_none
      2. Runtime blueprint lookup   — scalar_one_or_none
      3. Network blueprint lookup   — scalar_one_or_none
      4. Config/smelter_enforcement_mode — scalar_one_or_none
      5. SmelterService.validate_blueprint: ApprovedIngredient.name for os_family — scalars().all()
      6. Mirror check per package: ApprovedIngredient WHERE name ILIKE ? AND is_active=True — scalar_one_or_none

    Uses sequential side_effect list — avoids fragile SQL repr string-matching.
    """
    mock_db = AsyncMock()

    # For the scalars().all() query (validate_blueprint), return ing.name if ing is provided
    approved_names = [ing.name] if ing is not None else []

    mock_db.execute.side_effect = [
        _make_scalar_one_result(tmpl),           # 1. SELECT PuppetTemplate WHERE id = ?
        _make_scalar_one_result(rt_bp),          # 2. SELECT Blueprint WHERE id = runtime_blueprint_id
        _make_scalar_one_result(nw_bp),          # 3. SELECT Blueprint WHERE id = network_blueprint_id
        _make_scalar_one_result(cfg_val),        # 4. SELECT Config WHERE key = 'smelter_enforcement_mode'
        _make_scalars_all_result(approved_names),# 5. validate_blueprint: SELECT ApprovedIngredient.name
        _make_scalar_one_result(ing),            # 6. Mirror check: SELECT ApprovedIngredient WHERE name ILIKE ?
    ]
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    return mock_db


@pytest.mark.asyncio
async def test_foundry_fail_fast_unsynced_mirror():
    """Build is rejected with HTTP 403 if an active blueprint package is approved but not yet mirrored."""
    tmpl = PuppetTemplate(
        id="t1", friendly_name="test",
        runtime_blueprint_id="rt1", network_blueprint_id="nw1",
        is_compliant=True
    )
    rt_bp = Blueprint(
        id="rt1",
        definition=json.dumps({"base_os": "debian:12-slim", "packages": {"python": ["flask"]}}),
        os_family="DEBIAN"
    )
    nw_bp = Blueprint(id="nw1", definition=json.dumps({"egress_rules": []}))
    ing = ApprovedIngredient(name="flask", os_family="DEBIAN", mirror_status="PENDING", is_active=True)

    mock_db = _make_mock_db(tmpl, rt_bp, nw_bp, ing, cfg_val="WARNING")

    with pytest.raises(HTTPException) as exc_info:
        await FoundryService.build_template("t1", mock_db)

    assert exc_info.value.status_code == 403
    assert "not yet mirrored" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_foundry_mirror_injection():
    """When all packages are MIRRORED, Dockerfile contains pip.conf and sources.list COPY lines."""
    tmpl = PuppetTemplate(
        id="t1", friendly_name="test",
        runtime_blueprint_id="rt1", network_blueprint_id="nw1",
        is_compliant=True
    )
    rt_bp = Blueprint(
        id="rt1",
        definition=json.dumps({"base_os": "debian:12-slim", "packages": {"python": ["flask"]}, "tools": []}),
        os_family="DEBIAN"
    )
    nw_bp = Blueprint(id="nw1", definition=json.dumps({"egress_rules": []}))
    ing = ApprovedIngredient(name="flask", os_family="DEBIAN", mirror_status="MIRRORED", is_active=True)

    captured_build_dir = []
    original_makedirs = os.makedirs

    def fake_makedirs(path, exist_ok=False):
        if "puppet_build" in str(path):
            captured_build_dir.append(path)
        original_makedirs(path, exist_ok=exist_ok)

    mock_db = _make_mock_db(tmpl, rt_bp, nw_bp, ing)

    with patch("os.makedirs", side_effect=fake_makedirs), \
         patch("shutil.copytree"), \
         patch("shutil.copy2"), \
         patch("shutil.rmtree"), \
         patch("asyncio.create_subprocess_exec") as mock_proc:
        # Make the build subprocess fail quickly — we only care about Dockerfile content
        mock_proc.side_effect = Exception("build subprocess not needed for this test")
        try:
            await FoundryService.build_template("t1", mock_db)
        except Exception:
            pass

    assert captured_build_dir, "build_dir was never created — check makedirs mock or puppet_build path"
    build_dir = captured_build_dir[0]
    dockerfile_path = os.path.join(build_dir, "Dockerfile")
    pip_conf_path = os.path.join(build_dir, "pip.conf")

    assert os.path.isfile(dockerfile_path), f"Dockerfile not written to {build_dir}"
    assert os.path.isfile(pip_conf_path), f"pip.conf not written to {build_dir}"

    dockerfile_content = open(dockerfile_path).read()
    assert "COPY pip.conf /etc/pip.conf" in dockerfile_content, \
        f"COPY pip.conf line missing. Dockerfile:\n{dockerfile_content}"
    assert "COPY sources.list /etc/apt/sources.list" in dockerfile_content, \
        f"COPY sources.list line missing (DEBIAN build). Dockerfile:\n{dockerfile_content}"

    pip_conf_content = open(pip_conf_path).read()
    assert "index-url" in pip_conf_content
    assert "trusted-host" in pip_conf_content

    # Cleanup
    import shutil as _shutil
    _shutil.rmtree(build_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_alpine_build_injects_repos():
    """
    When Alpine base_os is used, Dockerfile contains COPY repositories line.
    This test is part of Phase 109 Wave 3 (Foundry Alpine injection).
    Placeholder test in RED state — implementation deferred.
    """
    pytest.skip("Deferred to Phase 109 Wave 3: Foundry Alpine injection not yet implemented")
