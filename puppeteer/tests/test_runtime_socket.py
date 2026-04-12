"""
Unit tests for socket detection logic in runtime.py
Tests the socket-first detection order and EXECUTION_MODE override.
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock


# Add puppets/environment_service to path so we can import runtime
PUPPETS_PATH = Path(__file__).parent.parent.parent / "puppets" / "environment_service"
if str(PUPPETS_PATH) not in sys.path:
    sys.path.insert(0, str(PUPPETS_PATH))

from runtime import ContainerRuntime


class TestSocketDetection:
    """Test socket-first detection order."""

    def test_docker_socket_first(self):
        """When /var/run/docker.sock exists, return 'docker' immediately."""
        with patch("os.environ.get", return_value="auto"), \
             patch("os.path.exists") as mock_exists, \
             patch("shutil.which", return_value=None):

            # /var/run/docker.sock exists, Podman socket absent
            mock_exists.side_effect = lambda path: path == "/var/run/docker.sock"

            runtime = ContainerRuntime()
            assert runtime.runtime == "docker"

    def test_podman_socket_fallback(self):
        """When Docker socket absent but /run/podman/podman.sock exists, return 'podman'."""
        with patch("os.environ.get", return_value="auto"), \
             patch("os.path.exists") as mock_exists, \
             patch("shutil.which", return_value=None):

            # /var/run/docker.sock absent, Podman socket exists
            mock_exists.side_effect = lambda path: path == "/run/podman/podman.sock"

            runtime = ContainerRuntime()
            assert runtime.runtime == "podman"

    def test_binary_detection_podman_first(self):
        """When no sockets, podman binary in PATH returns 'podman'."""
        with patch("os.environ.get", return_value="auto"), \
             patch("os.path.exists", return_value=False), \
             patch("shutil.which") as mock_which:

            # podman binary exists, docker binary does not
            mock_which.side_effect = lambda cmd: "/usr/bin/podman" if cmd == "podman" else None

            runtime = ContainerRuntime()
            assert runtime.runtime == "podman"

    def test_binary_detection_docker_fallback(self):
        """When no sockets and no podman, docker binary in PATH returns 'docker'."""
        with patch("os.environ.get", return_value="auto"), \
             patch("os.path.exists", return_value=False), \
             patch("shutil.which") as mock_which:

            # neither podman nor docker binary exists
            # Actually, for this test we want docker to exist but podman to not
            mock_which.side_effect = lambda cmd: "/usr/bin/docker" if cmd == "docker" else None

            runtime = ContainerRuntime()
            assert runtime.runtime == "docker"

    def test_no_runtime_raises_error(self):
        """When no sockets and no binaries, raise RuntimeError."""
        with patch("os.environ.get", return_value="auto"), \
             patch("os.path.exists", return_value=False), \
             patch("shutil.which", return_value=None):

            with pytest.raises(RuntimeError) as exc_info:
                runtime = ContainerRuntime()

            assert "No container runtime detected" in str(exc_info.value)

    def test_execution_mode_docker_override(self):
        """EXECUTION_MODE=docker env var overrides all detection."""
        with patch("os.environ.get") as mock_env, \
             patch("os.path.exists", return_value=False), \
             patch("shutil.which", return_value=None):

            # EXECUTION_MODE=docker is set
            mock_env.side_effect = lambda key, default=None: "docker" if key == "EXECUTION_MODE" else default

            runtime = ContainerRuntime()
            assert runtime.runtime == "docker"

    def test_execution_mode_podman_override(self):
        """EXECUTION_MODE=podman env var overrides all detection."""
        with patch("os.environ.get") as mock_env, \
             patch("os.path.exists", return_value=False), \
             patch("shutil.which", return_value=None):

            # EXECUTION_MODE=podman is set
            mock_env.side_effect = lambda key, default=None: "podman" if key == "EXECUTION_MODE" else default

            runtime = ContainerRuntime()
            assert runtime.runtime == "podman"
