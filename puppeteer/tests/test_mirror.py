import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from agent_service.services.mirror_service import MirrorService
from agent_service.db import ApprovedIngredient


@pytest.mark.asyncio
async def test_mirror_pypi_command_construction():
    """Verify pip download command is correctly constructed."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="test-id",
        name="requests",
        version_constraint="==2.20.0",
        os_family="DEBIAN"
    )

    with patch("subprocess.run") as mock_run, patch("os.makedirs"):
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

        await MirrorService._mirror_pypi(mock_db, ingredient)

        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "pip" in cmd
        assert "download" in cmd
        assert "requests==2.20.0" in cmd
        assert "--dest" in cmd
        assert "--no-deps" in cmd


@pytest.mark.asyncio
async def test_mirror_ingredient_orchestration():
    """Verify mirror_ingredient updates DB status to MIRRORED on success."""
    ingredient = ApprovedIngredient(
        id="test-id",
        name="flask",
        version_constraint="==2.0.0",
        os_family="DEBIAN",
        mirror_status="PENDING"
    )

    with patch("agent_service.services.mirror_service.AsyncSessionLocal") as mock_session_factory:
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = ingredient
        mock_db.execute.return_value = mock_res

        with patch.object(MirrorService, "_mirror_pypi", new_callable=AsyncMock):
            await MirrorService.mirror_ingredient("test-id")

            assert ingredient.mirror_status == "MIRRORED"
            mock_db.commit.assert_called()


def test_pip_conf_generation():
    """Verify pip.conf content points to correct host."""
    with patch.dict("os.environ", {"PYPI_MIRROR_URL": "http://my-pypi:8080/simple"}):
        content = MirrorService.get_pip_conf_content()
        assert "http://my-pypi:8080/simple" in content
        assert "trusted-host = my-pypi" in content


@pytest.mark.asyncio
async def test_mirror_pypi_log_capture():
    """Verify ingredient.mirror_log is set to combined stdout+stderr after _mirror_pypi."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="test-id",
        name="numpy",
        version_constraint="==1.24.0",
        os_family="DEBIAN",
        mirror_status="PENDING"
    )

    with patch("subprocess.run") as mock_run, patch("os.makedirs"):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Successfully downloaded numpy-1.24.0\n",
            stderr="WARNING: some warning\n"
        )

        await MirrorService._mirror_pypi(mock_db, ingredient)

        assert ingredient.mirror_log is not None, "mirror_log was not set"
        assert "numpy" in ingredient.mirror_log or "stdout" in ingredient.mirror_log.lower()
        assert "stderr" in ingredient.mirror_log.lower() or "WARNING" in ingredient.mirror_log


@pytest.mark.asyncio
async def test_mirror_ingredient_failure():
    """Verify mirror_ingredient sets mirror_status=FAILED when _mirror_pypi raises."""
    ingredient = ApprovedIngredient(
        id="fail-id",
        name="nonexistent-pkg",
        version_constraint="==99.99.99",
        os_family="DEBIAN",
        mirror_status="PENDING"
    )

    with patch("agent_service.services.mirror_service.AsyncSessionLocal") as mock_session_factory:
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = ingredient
        mock_db.execute.return_value = mock_res

        with patch.object(MirrorService, "_mirror_pypi", new_callable=AsyncMock) as mock_pypi:
            mock_pypi.side_effect = Exception("pip download failed: no matching distribution")
            await MirrorService.mirror_ingredient("fail-id")

            assert ingredient.mirror_status == "FAILED", f"Expected FAILED, got {ingredient.mirror_status}"
            mock_db.commit.assert_called()


def test_sources_list_generation():
    """Verify get_sources_list_content returns a valid deb line with trusted=yes."""
    with patch.dict("os.environ", {"APT_MIRROR_URL": "http://my-mirror/apt"}):
        content = MirrorService.get_sources_list_content()
        assert "deb [trusted=yes]" in content
        assert "http://my-mirror/apt" in content


@pytest.mark.asyncio
async def test_pure_python_wheel_downloaded_once(monkeypatch):
    """Test that pure-python wheels are downloaded once, not duplicated."""
    from unittest.mock import AsyncMock
    from uuid import uuid4

    # Mock _download_wheel to track calls
    calls = []

    async def mock_download(req, platform_tag, dest_dir):
        calls.append((req, platform_tag))
        # Simulate: requests is pure-python
        if "requests" in req and platform_tag == "py3-none-any":
            return {"found": True, "filename": "requests-2.31.0-py3-none-any.whl"}
        return {"found": False, "filename": None}

    monkeypatch.setattr(MirrorService, "_download_wheel", mock_download)

    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id=str(uuid4()),
        name="requests",
        version_constraint="==2.31.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="PENDING"
    )

    # Mirror the ingredient
    await MirrorService._mirror_pypi(mock_db, ingredient)

    # Verify only py3-none-any was checked, not manylinux/musllinux
    platform_checks = [c[1] for c in calls]
    assert "py3-none-any" in platform_checks
    assert "manylinux2014_x86_64" not in platform_checks  # Should not check

    # Verify mirror succeeded
    assert ingredient.mirror_status == "MIRRORED"


@pytest.mark.asyncio
async def test_c_extension_dual_platform(monkeypatch):
    """Test C-extension: attempt manylinux + musllinux."""
    from unittest.mock import AsyncMock
    from uuid import uuid4

    calls = []

    async def mock_download(req, platform_tag, dest_dir):
        calls.append((req, platform_tag))
        # Simulate: numpy has manylinux but not musllinux
        if "numpy" in req and platform_tag == "manylinux2014_x86_64":
            return {"found": True, "filename": "numpy-1.24.0-cp312-cp312-manylinux2014_x86_64.whl"}
        elif "numpy" in req and platform_tag == "musllinux_1_1_x86_64":
            return {"found": False, "filename": None}
        return {"found": False, "filename": None}

    monkeypatch.setattr(MirrorService, "_download_wheel", mock_download)

    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id=str(uuid4()),
        name="numpy",
        version_constraint="==1.24.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="PENDING"
    )

    await MirrorService._mirror_pypi(mock_db, ingredient)

    # Both platforms should be checked
    platform_checks = [c[1] for c in calls]
    assert "manylinux2014_x86_64" in platform_checks
    assert "musllinux_1_1_x86_64" in platform_checks


@pytest.mark.asyncio
async def test_musllinux_fallback_to_sdist(monkeypatch):
    """Test sdist fallback when musllinux wheel not available."""
    from unittest.mock import AsyncMock
    from uuid import uuid4

    calls = []

    async def mock_download(req, platform_tag, dest_dir):
        calls.append((req, platform_tag))
        # Simulate: no manylinux, no musllinux, but sdist available
        if "cython" in req and platform_tag == "sdist":
            return {"found": True, "filename": "Cython-0.29.32.tar.gz"}
        return {"found": False, "filename": None}

    monkeypatch.setattr(MirrorService, "_download_wheel", mock_download)

    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id=str(uuid4()),
        name="cython",
        version_constraint="==0.29.32",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="PENDING"
    )

    await MirrorService._mirror_pypi(mock_db, ingredient)

    # Verify sdist was attempted as fallback
    platform_checks = [c[1] for c in calls]
    assert "sdist" in platform_checks

    # Verify success despite missing wheels
    assert ingredient.mirror_status == "MIRRORED"
    assert "sdist fallback" in ingredient.mirror_log


@pytest.mark.asyncio
async def test_mirror_log_documents_attempts(monkeypatch):
    """Test that mirror_log documents all platform attempts."""
    from unittest.mock import AsyncMock
    from uuid import uuid4

    async def mock_download(req, platform_tag, dest_dir):
        if "requests" in req and platform_tag == "py3-none-any":
            return {"found": True, "filename": "requests-2.31.0-py3-none-any.whl"}
        return {"found": False, "filename": None}

    monkeypatch.setattr(MirrorService, "_download_wheel", mock_download)

    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id=str(uuid4()),
        name="requests",
        version_constraint="==2.31.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="PENDING"
    )

    await MirrorService._mirror_pypi(mock_db, ingredient)

    log = ingredient.mirror_log

    # Log should document attempts
    assert "pure-python" in log or "py3-none-any" in log
    assert "manylinux" in log or "musllinux" in log


@pytest.mark.asyncio
async def test_mirror_ingredient_and_dependencies(monkeypatch):
    """Test that mirror_ingredient_and_dependencies mirrors parent + all transitive deps."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4
    from agent_service.db import IngredientDependency

    # Setup: Flask (parent) with Werkzeug (child) dependency
    flask = ApprovedIngredient(
        id=str(uuid4()),
        name="Flask",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="RESOLVING"
    )
    werkzeug = ApprovedIngredient(
        id=str(uuid4()),
        name="Werkzeug",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="PENDING",
        auto_discovered=True
    )

    edge = IngredientDependency(
        id=str(uuid4()),
        parent_id=flask.id,
        child_id=werkzeug.id,
        dependency_type="transitive",
        version_constraint="==2.3.0",
        ecosystem="PYPI"
    )

    # Mock download
    async def mock_download(req, platform_tag, dest_dir):
        if platform_tag == "py3-none-any":
            return {"found": True, "filename": f"{req.split('==')[0]}-py3-none-any.whl"}
        return {"found": False, "filename": None}

    monkeypatch.setattr(MirrorService, "_download_wheel", mock_download)

    # Mock db
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(side_effect=lambda model, id: flask if id == flask.id else werkzeug if id == werkzeug.id else None)

    # Mock select result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [edge]
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mirror entire tree
    await MirrorService.mirror_ingredient_and_dependencies(mock_db, flask.id)

    # Verify both parent and child are MIRRORED
    assert flask.mirror_status == "MIRRORED"
    assert werkzeug.mirror_status == "MIRRORED"
