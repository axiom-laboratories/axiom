"""
Test job_service heartbeat handler execution_mode persistence.

Tests verify that:
1. HeartbeatPayload accepts execution_mode field from nodes
2. execution_mode is properly stored for both docker and podman modes
3. Backward compatibility: missing execution_mode handled gracefully
4. execution_mode persists alongside other heartbeat fields like cgroup detection
"""
import pytest
from agent_service.models import HeartbeatPayload


class TestHeartbeatHandlerExecutionMode:
    """Test heartbeat execution_mode field parsing and model validation."""

    def test_heartbeat_accepts_execution_mode_docker(self):
        """HeartbeatPayload accepts execution_mode=docker from nodes."""
        payload = HeartbeatPayload(
            node_id="test-node-exec-docker",
            hostname="testhost",
            execution_mode="docker"
        )
        assert payload.execution_mode == "docker"
        assert payload.node_id == "test-node-exec-docker"

    def test_heartbeat_accepts_execution_mode_podman(self):
        """HeartbeatPayload accepts execution_mode=podman from nodes."""
        payload = HeartbeatPayload(
            node_id="test-node-exec-podman",
            hostname="testhost",
            execution_mode="podman"
        )
        assert payload.execution_mode == "podman"

    def test_heartbeat_backward_compatible_no_execution_mode(self):
        """HeartbeatPayload handles missing execution_mode (old nodes)."""
        # Old nodes don't send execution_mode field
        payload = HeartbeatPayload(
            node_id="test-node-no-exec-mode",
            hostname="testhost"
        )
        # Should not crash and execution_mode should be None
        assert payload.execution_mode is None

    def test_heartbeat_execution_mode_with_all_fields(self):
        """HeartbeatPayload carries execution_mode alongside other heartbeat fields."""
        payload = HeartbeatPayload(
            node_id="test-node-both-fields",
            hostname="testhost",
            execution_mode="docker",
            detected_cgroup_version="v2",
            stats={"cpu": 50.0, "ram": 512},
            tags=["linux", "prod"],
            capabilities={"python": "3.12", "nodejs": "20"}
        )
        assert payload.execution_mode == "docker"
        assert payload.detected_cgroup_version == "v2"
        assert payload.stats == {"cpu": 50.0, "ram": 512}
        assert payload.tags == ["linux", "prod"]
        assert payload.capabilities == {"python": "3.12", "nodejs": "20"}

    def test_heartbeat_serialization_includes_execution_mode(self):
        """HeartbeatPayload serializes execution_mode when present."""
        payload = HeartbeatPayload(
            node_id="test-node",
            hostname="testhost",
            execution_mode="podman"
        )
        serialized = payload.model_dump()
        assert "execution_mode" in serialized
        assert serialized["execution_mode"] == "podman"

    def test_heartbeat_serialization_handles_missing_execution_mode(self):
        """HeartbeatPayload serializes with null execution_mode when not provided."""
        payload = HeartbeatPayload(
            node_id="test-node",
            hostname="testhost"
        )
        serialized = payload.model_dump()
        assert "execution_mode" in serialized
        assert serialized["execution_mode"] is None
