"""
Unit tests for network isolation in runtime.py
Tests the network_ref parameter wiring and jobs_network bridge usage.
"""
import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock, call


# Add puppets/environment_service to path so we can import runtime
PUPPETS_PATH = Path(__file__).parent.parent.parent / "puppets" / "environment_service"
if str(PUPPETS_PATH) not in sys.path:
    sys.path.insert(0, str(PUPPETS_PATH))

from runtime import ContainerRuntime


class TestNetworkIsolation:
    """Test network isolation and network_ref parameter wiring."""

    @pytest.mark.asyncio
    async def test_jobs_network_parameter(self):
        """run() called with network_ref='jobs_network' includes --network=jobs_network in cmd."""
        with patch("os.environ.get", return_value="auto"), \
             patch("os.path.exists") as mock_exists, \
             patch("shutil.which", return_value="/usr/bin/docker"):

            mock_exists.side_effect = lambda path: path == "/var/run/docker.sock"

            with patch("asyncio.create_subprocess_exec") as mock_exec:
                # Mock the subprocess
                mock_proc = AsyncMock()
                mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
                mock_proc.returncode = 0
                mock_exec.return_value = mock_proc

                runtime = ContainerRuntime()
                result = await runtime.run(
                    image="test:latest",
                    command=["echo", "hello"],
                    network_ref="jobs_network"
                )

                # Verify the command includes --network=jobs_network
                # asyncio.create_subprocess_exec(*cmd, ...) unpacks the command list
                call_args = mock_exec.call_args
                cmd_list = list(call_args[0])  # Get unpacked positional args as list
                assert "--network=jobs_network" in cmd_list, f"Command was: {cmd_list}"

    @pytest.mark.asyncio
    async def test_network_default_to_jobs_network(self):
        """run() without network_ref defaults to --network=jobs_network."""
        with patch("os.environ.get", return_value="auto"), \
             patch("os.path.exists") as mock_exists, \
             patch("shutil.which", return_value="/usr/bin/docker"):

            mock_exists.side_effect = lambda path: path == "/var/run/docker.sock"

            with patch("asyncio.create_subprocess_exec") as mock_exec:
                # Mock the subprocess
                mock_proc = AsyncMock()
                mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
                mock_proc.returncode = 0
                mock_exec.return_value = mock_proc

                runtime = ContainerRuntime()
                result = await runtime.run(
                    image="test:latest",
                    command=["echo", "hello"]
                )

                # Verify the command includes --network=jobs_network (default)
                call_args = mock_exec.call_args
                cmd_list = list(call_args[0])  # Get unpacked positional args as list
                assert "--network=jobs_network" in cmd_list, f"Command was: {cmd_list}"

    @pytest.mark.asyncio
    async def test_no_network_host_in_command(self):
        """Verify --network=host does NOT appear in docker/podman command."""
        with patch("os.environ.get", return_value="auto"), \
             patch("os.path.exists") as mock_exists, \
             patch("shutil.which", return_value="/usr/bin/docker"):

            mock_exists.side_effect = lambda path: path == "/var/run/docker.sock"

            with patch("asyncio.create_subprocess_exec") as mock_exec:
                # Mock the subprocess
                mock_proc = AsyncMock()
                mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
                mock_proc.returncode = 0
                mock_exec.return_value = mock_proc

                runtime = ContainerRuntime()
                result = await runtime.run(
                    image="test:latest",
                    command=["echo", "hello"],
                    network_ref="jobs_network"
                )

                # Verify --network=host is NOT present
                call_args = mock_exec.call_args
                cmd_list = list(call_args[0])  # Get unpacked positional args as list
                assert "--network=host" not in cmd_list, f"Command contains --network=host: {cmd_list}"
