"""
Test execution_mode field in heartbeat payload and API response.

Tests verify that:
1. HeartbeatPayload accepts execution_mode field (docker, podman, or None)
2. NodeResponse includes execution_mode field
3. Backward compatibility: execution_mode is optional (old nodes don't have it)
"""
import pytest
from datetime import datetime
from pydantic import ValidationError
from agent_service.models import HeartbeatPayload, NodeResponse


class TestHeartbeatExecutionMode:
    """Test execution_mode field in heartbeat payload."""

    def test_heartbeat_accepts_execution_mode(self):
        """HeartbeatPayload accepts execution_mode field."""
        payload = HeartbeatPayload(
            node_id="test-node",
            hostname="testhost",
            execution_mode="docker"
        )
        assert payload.execution_mode == "docker"

    def test_heartbeat_accepts_podman_mode(self):
        """HeartbeatPayload accepts podman mode."""
        payload = HeartbeatPayload(
            node_id="test-node",
            hostname="testhost",
            execution_mode="podman"
        )
        assert payload.execution_mode == "podman"

    def test_heartbeat_execution_mode_optional(self):
        """execution_mode is optional (backward compatible)."""
        payload = HeartbeatPayload(
            node_id="test-node",
            hostname="testhost"
            # No execution_mode field
        )
        assert payload.execution_mode is None


class TestNodeResponseExecutionMode:
    """Test execution_mode field in API response."""

    def test_node_response_includes_execution_mode(self):
        """NodeResponse includes execution_mode field."""
        response = NodeResponse(
            node_id="test-node",
            hostname="testhost",
            ip="127.0.0.1",
            last_seen=datetime.utcnow(),
            status="online",
            execution_mode="docker"
        )
        assert response.execution_mode == "docker"

    def test_node_response_execution_mode_optional(self):
        """NodeResponse execution_mode is optional."""
        response = NodeResponse(
            node_id="test-node",
            hostname="testhost",
            ip="127.0.0.1",
            last_seen=datetime.utcnow(),
            status="online"
            # No execution_mode
        )
        assert response.execution_mode is None
