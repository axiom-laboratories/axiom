"""
Compose file validation tests for node containers.
Tests verify that node-compose.yaml and node-compose.podman.yaml
meet Phase 134 security hardening and networking requirements.
"""

import pytest
import yaml
import subprocess
import os
from pathlib import Path


COMPOSE_DIR = Path(__file__).parent.parent.parent / "puppets"
DOCKER_COMPOSE = COMPOSE_DIR / "node-compose.yaml"
PODMAN_COMPOSE = COMPOSE_DIR / "node-compose.podman.yaml"


@pytest.fixture
def docker_compose_data():
    """Load and parse node-compose.yaml"""
    assert DOCKER_COMPOSE.exists(), f"node-compose.yaml not found at {DOCKER_COMPOSE}"
    with open(DOCKER_COMPOSE) as f:
        return yaml.safe_load(f)


@pytest.fixture
def podman_compose_data():
    """Load and parse node-compose.podman.yaml"""
    assert PODMAN_COMPOSE.exists(), f"node-compose.podman.yaml not found at {PODMAN_COMPOSE}"
    with open(PODMAN_COMPOSE) as f:
        return yaml.safe_load(f)


# ============================================================================
# Docker Compose Tests
# ============================================================================

class TestDockerCompose:
    """Tests for node-compose.yaml (Docker variant)"""

    def test_docker_compose_config_valid(self):
        """Test 1: node-compose.yaml is valid YAML and passes docker compose config validation"""
        # Validate with docker compose config
        result = subprocess.run(
            ["docker", "compose", "-f", str(DOCKER_COMPOSE), "config", "--quiet"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"docker compose config failed: {result.stderr}"

    def test_docker_compose_no_privileged(self, docker_compose_data):
        """Test 2: node-compose.yaml does NOT contain privileged: true"""
        node_service = docker_compose_data["services"]["node"]
        privileged = node_service.get("privileged", False)
        assert privileged is False, "privileged: true found in node service (should be removed)"

    def test_docker_compose_docker_socket_mount(self, docker_compose_data):
        """Test 3: node-compose.yaml contains Docker socket mount"""
        node_service = docker_compose_data["services"]["node"]
        volumes = node_service.get("volumes", [])
        socket_mount = "/var/run/docker.sock:/var/run/docker.sock:rw"
        assert socket_mount in volumes, f"Docker socket mount not found. Volumes: {volumes}"

    def test_docker_compose_cap_drop_all(self, docker_compose_data):
        """Test 4: node-compose.yaml contains cap_drop: ALL"""
        node_service = docker_compose_data["services"]["node"]
        cap_drop = node_service.get("cap_drop", [])
        assert "ALL" in cap_drop, f"cap_drop: ALL not found. cap_drop: {cap_drop}"

    def test_docker_compose_security_opt(self, docker_compose_data):
        """Test 5: node-compose.yaml contains security_opt: no-new-privileges:true"""
        node_service = docker_compose_data["services"]["node"]
        security_opt = node_service.get("security_opt", [])
        assert "no-new-privileges:true" in security_opt, f"security_opt not found. security_opt: {security_opt}"

    def test_docker_compose_jobs_network_defined(self, docker_compose_data):
        """Test 6: node-compose.yaml defines jobs_network bridge"""
        networks = docker_compose_data.get("networks", {})
        assert "jobs_network" in networks, f"jobs_network not defined. Networks: {networks}"
        jobs_network = networks["jobs_network"]
        driver = jobs_network.get("driver", "bridge")
        assert driver == "bridge", f"jobs_network driver is {driver}, expected bridge"

    def test_docker_compose_node_joins_both_networks(self, docker_compose_data):
        """Test 7: node service joins both puppeteer_default and jobs_network"""
        node_service = docker_compose_data["services"]["node"]
        networks = node_service.get("networks", [])
        assert "puppeteer_default" in networks, f"puppeteer_default not in node networks. Networks: {networks}"
        assert "jobs_network" in networks, f"jobs_network not in node networks. Networks: {networks}"

    def test_docker_compose_group_add(self, docker_compose_data):
        """Test 8: node-compose.yaml contains group_add: [999]"""
        node_service = docker_compose_data["services"]["node"]
        group_add = node_service.get("group_add", [])
        # group_add might be list of ints or strings
        group_add_str = [str(g) for g in group_add]
        assert "999" in group_add_str, f"group_add: [999] not found. group_add: {group_add}"

    def test_docker_compose_docker_host_env(self, docker_compose_data):
        """Test 9: node-compose.yaml contains DOCKER_HOST env var"""
        node_service = docker_compose_data["services"]["node"]
        environment = node_service.get("environment", [])
        env_dict = {}
        for item in environment:
            if isinstance(item, str):
                if "=" in item:
                    k, v = item.split("=", 1)
                    env_dict[k] = v
        assert "DOCKER_HOST" in env_dict, f"DOCKER_HOST env var not found. Env: {env_dict}"
        assert env_dict["DOCKER_HOST"] == "unix:///var/run/docker.sock", \
            f"DOCKER_HOST has unexpected value: {env_dict['DOCKER_HOST']}"


# ============================================================================
# Podman Compose Tests
# ============================================================================

class TestPodmanCompose:
    """Tests for node-compose.podman.yaml (Podman variant)"""

    def test_podman_compose_config_valid(self):
        """Test 10: node-compose.podman.yaml is valid YAML and passes docker compose config validation"""
        result = subprocess.run(
            ["docker", "compose", "-f", str(PODMAN_COMPOSE), "config", "--quiet"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"docker compose config failed: {result.stderr}"

    def test_podman_compose_userns_mode_keep_id(self, podman_compose_data):
        """Test 11: node-compose.podman.yaml contains userns_mode: keep-id"""
        node_service = podman_compose_data["services"]["node"]
        userns_mode = node_service.get("userns_mode")
        assert userns_mode == "keep-id", f"userns_mode not set to keep-id. Found: {userns_mode}"

    def test_podman_compose_podman_socket_mount(self, podman_compose_data):
        """Test 12: node-compose.podman.yaml contains Podman socket mount with env var default"""
        node_service = podman_compose_data["services"]["node"]
        volumes = node_service.get("volumes", [])
        # Should contain a mount with ${PODMAN_SOCK:-...} pattern
        found_podman_socket = False
        for vol in volumes:
            if isinstance(vol, str) and "/run/podman/podman.sock" in vol:
                found_podman_socket = True
                break
        assert found_podman_socket, f"Podman socket mount not found. Volumes: {volumes}"

    def test_podman_compose_execution_mode_podman(self, podman_compose_data):
        """Test 13: node-compose.podman.yaml contains EXECUTION_MODE=podman env var"""
        node_service = podman_compose_data["services"]["node"]
        environment = node_service.get("environment", [])
        env_dict = {}
        for item in environment:
            if isinstance(item, str):
                if "=" in item:
                    k, v = item.split("=", 1)
                    env_dict[k] = v
        assert "EXECUTION_MODE" in env_dict, f"EXECUTION_MODE env var not found. Env: {env_dict}"
        assert env_dict["EXECUTION_MODE"] == "podman", \
            f"EXECUTION_MODE has unexpected value: {env_dict['EXECUTION_MODE']}"

    def test_podman_compose_no_group_add(self, podman_compose_data):
        """Test 14: node-compose.podman.yaml does NOT contain group_add"""
        node_service = podman_compose_data["services"]["node"]
        group_add = node_service.get("group_add")
        assert group_add is None or group_add == [], \
            f"group_add should not be present in Podman variant. Found: {group_add}"

    def test_podman_compose_jobs_network_defined(self, podman_compose_data):
        """Test 15: node-compose.podman.yaml defines jobs_network bridge"""
        networks = podman_compose_data.get("networks", {})
        assert "jobs_network" in networks, f"jobs_network not defined. Networks: {networks}"
        jobs_network = networks["jobs_network"]
        driver = jobs_network.get("driver", "bridge")
        assert driver == "bridge", f"jobs_network driver is {driver}, expected bridge"


# ============================================================================
# Capability Restrictions (Common to Both)
# ============================================================================

class TestCapabilityRestrictions:
    """Common capability restriction tests for both Docker and Podman variants"""

    def test_docker_compose_security_opt_no_new_privs(self, docker_compose_data):
        """Docker variant: security_opt no-new-privileges"""
        node_service = docker_compose_data["services"]["node"]
        security_opt = node_service.get("security_opt", [])
        assert "no-new-privileges:true" in security_opt

    def test_podman_compose_security_opt_no_new_privs(self, podman_compose_data):
        """Podman variant: security_opt no-new-privileges"""
        node_service = podman_compose_data["services"]["node"]
        security_opt = node_service.get("security_opt", [])
        assert "no-new-privileges:true" in security_opt

    def test_docker_compose_cap_drop(self, docker_compose_data):
        """Docker variant: cap_drop: ALL"""
        node_service = docker_compose_data["services"]["node"]
        cap_drop = node_service.get("cap_drop", [])
        assert "ALL" in cap_drop

    def test_podman_compose_cap_drop(self, podman_compose_data):
        """Podman variant: cap_drop: ALL"""
        node_service = podman_compose_data["services"]["node"]
        cap_drop = node_service.get("cap_drop", [])
        assert "ALL" in cap_drop
