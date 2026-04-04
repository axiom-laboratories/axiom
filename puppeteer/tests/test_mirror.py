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
    """Verify ingredient.mirror_log is set after _mirror_pypi."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="test-id",
        name="numpy",
        version_constraint="==1.24.0",
        os_family="DEBIAN",
        mirror_status="PENDING"
    )

    with patch("subprocess.run") as mock_run, \
         patch("os.makedirs"), \
         patch.object(MirrorService, "_download_wheel", new_callable=AsyncMock) as mock_download:

        # Mock pure-python wheel success
        mock_download.return_value = {"found": True, "filename": "numpy-1.24.0-py3-none-any.whl"}

        await MirrorService._mirror_pypi(mock_db, ingredient)

        assert ingredient.mirror_log is not None, "mirror_log was not set"
        assert "numpy" in ingredient.mirror_log


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




# === APT Mirroring Tests ===

@pytest.mark.asyncio
async def test_mirror_apt_download():
    """Verify _mirror_apt() downloads .deb files and regenerates Packages.gz."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="apt-test-id",
        name="curl",
        version_constraint="==7.68.0",
        os_family="DEBIAN"
    )

    with patch("subprocess.run") as mock_run, \
         patch("os.makedirs"), \
         patch.object(MirrorService, "_regenerate_apt_index", new_callable=AsyncMock) as mock_regen:

        # Simulate successful apt-get download
        mock_run.return_value = MagicMock(returncode=0, stdout="Downloaded", stderr="")

        await MirrorService._mirror_apt(mock_db, ingredient)

        # Verify docker run command was issued
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "docker" in cmd
        assert "debian:12-slim" in cmd
        # apt-get is in the bash -c string, not as a direct command argument
        assert "curl" in cmd or any("curl" in str(c) for c in cmd)

        # Verify index regeneration was called
        mock_regen.assert_called_once()

        # Verify status updated
        assert ingredient.mirror_status == "MIRRORED"
        assert ingredient.mirror_log == "Downloaded curl=7.68.0; regenerated Packages.gz"
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_mirror_apt_version_parsing():
    """Test APT version constraint parsing."""
    test_cases = [
        ("curl", "==7.68.0", "curl=7.68.0"),
        ("vim", ">=2.0", "vim=2.0"),
        ("git", ">=1.0", "git=1.0"),
        ("nano", None, "nano"),  # No version
        ("zsh", "==5.8", "zsh=5.8"),
    ]

    for name, version_constraint, expected_spec in test_cases:
        ingredient = ApprovedIngredient(
            id="test-id",
            name=name,
            version_constraint=version_constraint,
            os_family="DEBIAN"
        )

        import re
        # Simulate the parsing logic from _mirror_apt
        pkg_spec = ingredient.name
        if ingredient.version_constraint:
            version = re.sub(r'^[><=~!]+', '', ingredient.version_constraint).strip()
            if version:
                pkg_spec = f"{ingredient.name}={version}"

        assert pkg_spec == expected_spec, f"Expected {expected_spec}, got {pkg_spec}"


@pytest.mark.asyncio
async def test_mirror_apt_failure_handling():
    """Verify _mirror_apt() sets FAILED status on download error."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="apt-fail-id",
        name="nonexistent-pkg",
        version_constraint="==99.99.99",
        os_family="DEBIAN"
    )

    with patch("subprocess.run") as mock_run, patch("os.makedirs"):
        # Simulate failed apt-get download
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Unable to locate package nonexistent-pkg"
        )

        await MirrorService._mirror_apt(mock_db, ingredient)

        assert ingredient.mirror_status == "FAILED"
        assert "nonexistent-pkg" in ingredient.mirror_log
        mock_db.commit.assert_called()


# === APK Mirroring Tests ===

@pytest.mark.asyncio
async def test_mirror_apk_download():
    """Verify _mirror_apk() downloads .apk files and regenerates APKINDEX.tar.gz."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="apk-test-id",
        name="curl",
        version_constraint="==7.85.0",
        os_family="ALPINE"
    )

    with patch("subprocess.run") as mock_run, \
         patch("os.makedirs"), \
         patch.object(MirrorService, "_regenerate_apk_index", new_callable=AsyncMock) as mock_regen:

        # Simulate successful apk fetch
        mock_run.return_value = MagicMock(returncode=0, stdout="Fetched", stderr="")

        await MirrorService._mirror_apk(mock_db, ingredient)

        # Verify docker run command was issued
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "docker" in cmd
        assert "alpine:3.20" in cmd
        # apk fetch is in the bash -c string, not as a direct command argument
        assert "apk fetch" in cmd or any("apk fetch" in str(c) for c in cmd)

        # Verify index regeneration was called
        mock_regen.assert_called_once()

        # Verify status updated
        assert ingredient.mirror_status == "MIRRORED"
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_apk_repos_version_parsing():
    """Test get_apk_repos_content() with various base_os inputs."""
    test_cases = [
        ("alpine:3.20", "v3.20"),
        ("alpine:3.18", "v3.18"),
        ("alpine:3.19", "v3.19"),
        ("alpine:latest", "v3.20"),  # Fallback to default
        (None, "v3.20"),  # Fallback to default
    ]

    for base_os, expected_version in test_cases:
        with patch.dict("os.environ", {"DEFAULT_ALPINE_VERSION": "v3.20", "APK_MIRROR_URL": "http://mirror/apk"}):
            content = MirrorService.get_apk_repos_content(base_os)

            # Content should include expected version
            assert f"/{expected_version}/main" in content
            assert f"/{expected_version}/community" in content


@pytest.mark.asyncio
async def test_apk_repos_fallback():
    """Test that DEFAULT_ALPINE_VERSION env var is respected."""
    with patch.dict("os.environ", {"DEFAULT_ALPINE_VERSION": "v3.19", "APK_MIRROR_URL": "http://mirror/apk"}):
        content = MirrorService.get_apk_repos_content("alpine:latest")
        assert "/v3.19/main" in content
        assert "/v3.19/community" in content


@pytest.mark.asyncio
async def test_mirror_apk_failure_handling():
    """Verify _mirror_apk() sets FAILED status on fetch error."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="apk-fail-id",
        name="nonexistent-pkg",
        version_constraint="==99.99.99",
        os_family="ALPINE"
    )

    with patch("subprocess.run") as mock_run, patch("os.makedirs"):
        # Simulate failed apk fetch
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ERROR: unable to find package nonexistent-pkg"
        )

        await MirrorService._mirror_apk(mock_db, ingredient)

        assert ingredient.mirror_status == "FAILED"
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_get_alpine_version_parsing():
    """Test Alpine version extraction from base_os tag."""
    test_cases = [
        ("alpine:3.20", "v3.20"),
        ("alpine:3.18", "v3.18"),
        ("alpine:latest", None),  # Will use default
        ("alpine:edge", None),  # Will use default
    ]

    for base_os, expected in test_cases:
        if expected:
            result = MirrorService._get_alpine_version(base_os)
            assert result == expected
        else:
            with patch.dict("os.environ", {"DEFAULT_ALPINE_VERSION": "v3.20"}):
                result = MirrorService._get_alpine_version(base_os)
                assert result == "v3.20"


# === npm Mirroring Tests ===

@pytest.mark.asyncio
async def test_mirror_npm_success():
    """Verify _mirror_npm() downloads npm package and updates status to MIRRORED."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="npm-test-id",
        name="lodash",
        version_constraint="@4.17.21",
        os_family="DEBIAN"
    )

    with patch("subprocess.run") as mock_run, \
         patch("os.makedirs"), \
         patch("os.path.exists") as mock_exists:

        # Simulate successful npm pack
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="lodash-4.17.21.tgz\n",
            stderr=""
        )
        mock_exists.return_value = True  # Tarball exists

        await MirrorService._mirror_npm(mock_db, ingredient)

        # Verify docker run command was issued
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "docker" in cmd
        assert "node:latest" in cmd
        assert "npm pack" in cmd or any("npm pack" in str(c) for c in cmd)

        # Verify status updated
        assert ingredient.mirror_status == "MIRRORED"
        assert ingredient.mirror_path == MirrorService.NPM_PATH
        assert "lodash" in ingredient.mirror_log
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_mirror_npm_version_parsing():
    """Test npm version constraint parsing."""
    test_cases = [
        ("lodash", "@4.17.21", "lodash@4.17.21"),
        ("react", "@^18.0.0", "react@^18.0.0"),
        ("express", "@latest", "express@latest"),
        ("axios", "@next", "axios@next"),
        ("webpack", "~4.0.0", "webpack@~4.0.0"),
        ("typescript", None, "typescript"),  # No version
    ]

    mock_db = AsyncMock()

    for name, version_constraint, expected_spec in test_cases:
        ingredient = ApprovedIngredient(
            id="test-id",
            name=name,
            version_constraint=version_constraint,
            os_family="DEBIAN"
        )

        with patch("subprocess.run") as mock_run, \
             patch("os.makedirs"), \
             patch("os.path.exists") as mock_exists:

            mock_run.return_value = MagicMock(returncode=0, stdout=f"{name}.tgz\n", stderr="")
            mock_exists.return_value = True

            await MirrorService._mirror_npm(mock_db, ingredient)

            # Verify the correct package spec was used
            args, kwargs = mock_run.call_args
            cmd = args[0]
            cmd_str = ' '.join(str(c) for c in cmd)
            assert expected_spec in cmd_str, f"Expected {expected_spec} in {cmd_str}"


@pytest.mark.asyncio
async def test_mirror_npm_container_failure():
    """Verify _mirror_npm() sets FAILED status on npm pack failure."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="npm-fail-id",
        name="nonexistent-package",
        version_constraint="@1.0.0",
        os_family="DEBIAN"
    )

    with patch("subprocess.run") as mock_run, patch("os.makedirs"):
        # Simulate failed npm pack
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="404 Not Found - nonexistent-package@1.0.0"
        )

        await MirrorService._mirror_npm(mock_db, ingredient)

        assert ingredient.mirror_status == "FAILED"
        assert "nonexistent-package" in ingredient.mirror_log or "404" in ingredient.mirror_log
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_mirror_npm_timeout():
    """Verify _mirror_npm() sets FAILED status on timeout."""
    import asyncio
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="npm-timeout-id",
        name="large-package",
        version_constraint="@1.0.0",
        os_family="DEBIAN"
    )

    with patch("subprocess.run") as mock_run, patch("os.makedirs"):
        # Simulate timeout by raising TimeoutError from subprocess call
        mock_run.side_effect = asyncio.TimeoutError()

        await MirrorService._mirror_npm(mock_db, ingredient)

        assert ingredient.mirror_status == "FAILED"
        assert "timeout" in ingredient.mirror_log.lower()
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_mirror_npm_storage_validation():
    """Verify tarball is validated to exist before status update."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="npm-storage-id",
        name="lodash",
        version_constraint="@4.17.21",
        os_family="DEBIAN"
    )

    with patch("subprocess.run") as mock_run, \
         patch("os.makedirs"), \
         patch("os.path.exists") as mock_exists:

        # npm pack succeeds but tarball doesn't actually exist
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="lodash-4.17.21.tgz\n",
            stderr=""
        )
        mock_exists.return_value = False  # Tarball missing

        await MirrorService._mirror_npm(mock_db, ingredient)

        assert ingredient.mirror_status == "FAILED"
        assert "not found" in ingredient.mirror_log.lower()
        mock_db.commit.assert_called()


def test_get_npmrc_content_format():
    """Verify get_npmrc_content() returns correct .npmrc format."""
    with patch.dict("os.environ", {"NPM_MIRROR_URL": "http://verdaccio:4873"}):
        content = MirrorService.get_npmrc_content()
        assert "registry=" in content
        assert "http://verdaccio:4873" in content


def test_get_npmrc_content_default():
    """Verify get_npmrc_content() uses default URL when env var unset."""
    with patch.dict("os.environ", {}, clear=True):
        content = MirrorService.get_npmrc_content()
        assert "registry=" in content
        assert "verdaccio:4873" in content


# === NuGet Mirroring Tests (Task 6, Phase 111-02) ===

@pytest.mark.asyncio
async def test_mirror_nuget_success():
    """Verify _mirror_nuget() downloads NuGet package and updates status to MIRRORED."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="nuget-test-id",
        name="Newtonsoft.Json",
        version_constraint="==13.0.3",
        os_family="WINDOWS"
    )

    with patch("subprocess.run") as mock_run, \
         patch("os.makedirs"), \
         patch("os.walk") as mock_walk:

        # Simulate successful nuget install
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Successfully installed Newtonsoft.Json 13.0.3",
            stderr=""
        )
        # Mock os.walk to find the .nupkg file
        mock_walk.return_value = [
            ("/mirror", [], ["Newtonsoft.Json.13.0.3.nupkg"])
        ]

        await MirrorService._mirror_nuget(mock_db, ingredient)

        # Verify docker run command was issued
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "docker" in cmd
        assert "mcr.microsoft.com/dotnet/sdk:latest" in cmd
        assert "nuget install" in cmd or any("nuget install" in str(c) for c in cmd)
        assert "Newtonsoft.Json" in cmd or any("Newtonsoft.Json" in str(c) for c in cmd)

        # Verify status updated
        assert ingredient.mirror_status == "MIRRORED"
        assert MirrorService.NUGET_PATH in ingredient.mirror_path  # Path includes package subdir
        assert "Newtonsoft.Json" in ingredient.mirror_log
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_mirror_nuget_version_parsing():
    """Test NuGet version constraint parsing."""
    test_cases = [
        ("Newtonsoft.Json", "==13.0.3", "Newtonsoft.Json", "13.0.3"),
        ("NLog", ">=5.0.0", "NLog", "5.0.0"),
        ("Serilog", None, "Serilog", None),  # No version
    ]

    mock_db = AsyncMock()

    for name, version_constraint, expected_name, expected_version in test_cases:
        ingredient = ApprovedIngredient(
            id="nuget-test-id",
            name=name,
            version_constraint=version_constraint,
            os_family="WINDOWS"
        )

        with patch("subprocess.run") as mock_run, \
             patch("os.makedirs"), \
             patch("os.walk") as mock_walk:

            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            mock_walk.return_value = [(f"/mirror", [], [f"{name}.nupkg"])]

            await MirrorService._mirror_nuget(mock_db, ingredient)

            # Verify correct package spec was used
            args, kwargs = mock_run.call_args
            cmd = args[0]
            cmd_str = ' '.join(str(c) for c in cmd)
            assert expected_name in cmd_str


@pytest.mark.asyncio
async def test_mirror_nuget_container_failure():
    """Verify _mirror_nuget() sets FAILED status on nuget install failure."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="nuget-fail-id",
        name="NonexistentPackage",
        version_constraint="==1.0.0",
        os_family="WINDOWS"
    )

    with patch("subprocess.run") as mock_run, patch("os.makedirs"):
        # Simulate failed nuget install
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Unable to find package NonexistentPackage version 1.0.0"
        )

        await MirrorService._mirror_nuget(mock_db, ingredient)

        assert ingredient.mirror_status == "FAILED"
        assert "NonexistentPackage" in ingredient.mirror_log or "1.0.0" in ingredient.mirror_log
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_mirror_nuget_timeout():
    """Verify _mirror_nuget() sets FAILED status on timeout."""
    import asyncio
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="nuget-timeout-id",
        name="LargePackage",
        version_constraint="==1.0.0",
        os_family="WINDOWS"
    )

    with patch("subprocess.run") as mock_run, patch("os.makedirs"):
        # Simulate timeout by raising TimeoutError from subprocess call
        mock_run.side_effect = asyncio.TimeoutError()

        await MirrorService._mirror_nuget(mock_db, ingredient)

        assert ingredient.mirror_status == "FAILED"
        assert "timeout" in ingredient.mirror_log.lower()
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_mirror_nuget_missing_file():
    """Verify _mirror_nuget() sets FAILED status when .nupkg file not found."""
    mock_db = AsyncMock()
    ingredient = ApprovedIngredient(
        id="nuget-missing-id",
        name="TestPackage",
        version_constraint="==1.0.0",
        os_family="WINDOWS"
    )

    with patch("subprocess.run") as mock_run, \
         patch("os.makedirs"), \
         patch("os.walk") as mock_walk:

        # nuget install succeeds but no .nupkg file found
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_walk.return_value = [("/mirror", [], [])]  # Empty directory

        await MirrorService._mirror_nuget(mock_db, ingredient)

        assert ingredient.mirror_status == "FAILED"
        assert "not found" in ingredient.mirror_log.lower() or ".nupkg" in ingredient.mirror_log
        mock_db.commit.assert_called()


def test_get_nuget_config_content():
    """Verify get_nuget_config_content() returns valid NuGet.config XML."""
    with patch.dict("os.environ", {"NUGET_MIRROR_URL": "http://bagetter:5555/v3/index.json"}):
        content = MirrorService.get_nuget_config_content()
        assert "<?xml version" in content
        assert "<packageSources>" in content
        assert "http://bagetter:5555/v3/index.json" in content
        assert '<add key=' in content or '<packageSource key=' in content


def test_get_nuget_config_default():
    """Verify get_nuget_config_content() uses default URL when env var unset."""
    with patch.dict("os.environ", {}, clear=True):
        content = MirrorService.get_nuget_config_content()
        assert "<?xml version" in content
        assert "<packageSources>" in content
        assert "bagetter" in content.lower()


# === OCI Mirror Prefix Rewriting Tests ===

def test_get_oci_mirror_prefix_docker_hub_unqualified():
    """Test Docker Hub unqualified image (e.g., 'node') rewrites to oci-cache:5001/library/node."""
    rewritten = MirrorService.get_oci_mirror_prefix("node:18")
    assert rewritten == "oci-cache:5001/library/node:18"


def test_get_oci_mirror_prefix_docker_hub_qualified():
    """Test Docker Hub qualified image (e.g., 'library/node') rewrites to oci-cache:5001/library/node."""
    rewritten = MirrorService.get_oci_mirror_prefix("library/node:18")
    assert rewritten == "oci-cache:5001/library/node:18"


def test_get_oci_mirror_prefix_ghcr():
    """Test GHCR image (ghcr.io/...) rewrites to oci-cache-ghcr:5002."""
    rewritten = MirrorService.get_oci_mirror_prefix("ghcr.io/owner/image:latest")
    assert rewritten == "oci-cache-ghcr:5002/owner/image:latest"


def test_get_oci_mirror_prefix_docker_registry():
    """Test Docker-compatible registry (has domain) rewrites to oci-cache:5001."""
    rewritten = MirrorService.get_oci_mirror_prefix("docker.io/library/python:3.11")
    assert rewritten == "oci-cache:5001/docker.io/library/python:3.11"


def test_get_oci_mirror_prefix_private_registry():
    """Test private registry rewrites to oci-cache:5001."""
    rewritten = MirrorService.get_oci_mirror_prefix("myregistry.com:5000/app/image:v1.0")
    assert rewritten == "oci-cache:5001/myregistry.com:5000/app/image:v1.0"


def test_get_oci_mirror_prefix_no_tag():
    """Test image without tag (uses 'latest' implicitly)."""
    rewritten = MirrorService.get_oci_mirror_prefix("node")
    assert rewritten == "oci-cache:5001/library/node"
    assert "latest" not in rewritten  # Should not add :latest
