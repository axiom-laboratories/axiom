"""Tests for audit() function SIEM enqueue hook."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from agent_service.deps import audit


@pytest.mark.asyncio
async def test_audit_enqueues_to_siem():
    """Test audit() calls siem.enqueue() with correct event structure."""
    mock_siem = Mock()
    mock_siem.enqueue = Mock()

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        # Create a mock user object
        mock_user = Mock()
        mock_user.username = "alice"

        # Create a mock DB session
        mock_db = Mock()

        # Call audit()
        audit(
            db=mock_db,
            user=mock_user,
            action="job_execute",
            resource_id="job_123",
            detail={"result": "success"}
        )

        # Verify enqueue was called
        assert mock_siem.enqueue.called

        # Get the event passed to enqueue
        event = mock_siem.enqueue.call_args[0][0]
        assert event["username"] == "alice"
        assert event["action"] == "job_execute"
        assert event["resource_id"] == "job_123"
        assert event["detail"] == {"result": "success"}
        assert "timestamp" in event


@pytest.mark.asyncio
async def test_audit_works_in_ce_mode():
    """Test audit() continues to work when SIEM service is None (CE mode)."""
    with patch('ee.services.siem_service.get_siem_service', return_value=None):
        mock_user = Mock()
        mock_user.username = "bob"
        mock_db = Mock()

        # Should not raise even if SIEM is None
        audit(
            db=mock_db,
            user=mock_user,
            action="user_create",
            resource_id="user_456",
            detail={"username": "newuser"}
        )


@pytest.mark.asyncio
async def test_audit_never_propagates_siem_errors():
    """Test audit() never raises even if siem.enqueue() fails."""
    mock_siem = Mock()
    mock_siem.enqueue = Mock(side_effect=Exception("Queue overflow"))

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        mock_user = Mock()
        mock_user.username = "charlie"
        mock_db = Mock()

        # Should not raise despite enqueue() failure
        audit(
            db=mock_db,
            user=mock_user,
            action="secret_access",
            resource_id="secret_123",
            detail={"field": "accessed"}
        )


@pytest.mark.asyncio
async def test_audit_never_blocks():
    """Test audit() is synchronous and non-blocking."""
    import time

    mock_siem = Mock()
    # Simulate a slow enqueue (shouldn't happen, but test anyway)
    mock_siem.enqueue = Mock(side_effect=lambda e: time.sleep(0.001))

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        mock_user = Mock()
        mock_user.username = "dave"
        mock_db = Mock()

        start = time.time()
        audit(
            db=mock_db,
            user=mock_user,
            action="config_change",
            resource_id="config_1",
            detail={"change": "enabled_flag"}
        )
        elapsed = time.time() - start

        # enqueue() wrapped in try/except, so should return quickly
        assert elapsed < 0.1, f"audit() took too long: {elapsed}s"


@pytest.mark.asyncio
async def test_audit_event_payload_has_all_fields():
    """Test audit() event includes all required fields."""
    mock_siem = Mock()
    mock_siem.enqueue = Mock()

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        mock_user = Mock()
        mock_user.username = "eve"
        mock_db = Mock()

        audit(
            db=mock_db,
            user=mock_user,
            action="vault_access",
            resource_id="vault_secret_1",
            detail={"operation": "read"}
        )

        event = mock_siem.enqueue.call_args[0][0]

        # Verify all fields present
        assert "username" in event
        assert "action" in event
        assert "resource_id" in event
        assert "detail" in event
        assert "timestamp" in event

        # Verify timestamp is ISO format
        assert "T" in event["timestamp"]  # ISO format includes T


@pytest.mark.asyncio
async def test_audit_with_none_detail():
    """Test audit() handles None detail gracefully."""
    mock_siem = Mock()
    mock_siem.enqueue = Mock()

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        mock_user = Mock()
        mock_user.username = "frank"
        mock_db = Mock()

        audit(
            db=mock_db,
            user=mock_user,
            action="test_action",
            resource_id="test_resource",
            detail=None
        )

        event = mock_siem.enqueue.call_args[0][0]
        assert event["detail"] is None


@pytest.mark.asyncio
async def test_audit_with_none_resource_id():
    """Test audit() handles None resource_id gracefully."""
    mock_siem = Mock()
    mock_siem.enqueue = Mock()

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        mock_user = Mock()
        mock_user.username = "grace"
        mock_db = Mock()

        audit(
            db=mock_db,
            user=mock_user,
            action="system_event",
            resource_id=None,
            detail={"type": "startup"}
        )

        event = mock_siem.enqueue.call_args[0][0]
        assert event["resource_id"] is None


@pytest.mark.asyncio
async def test_audit_preserves_complex_detail():
    """Test audit() preserves complex nested detail structures."""
    mock_siem = Mock()
    mock_siem.enqueue = Mock()

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        mock_user = Mock()
        mock_user.username = "henry"
        mock_db = Mock()

        complex_detail = {
            "operation": "workflow_execute",
            "steps": [
                {"id": "step_1", "status": "completed"},
                {"id": "step_2", "status": "pending"},
            ],
            "metadata": {
                "duration_ms": 1234,
                "node_ids": ["node_1", "node_2"],
            }
        }

        audit(
            db=mock_db,
            user=mock_user,
            action="workflow_event",
            resource_id="workflow_123",
            detail=complex_detail
        )

        event = mock_siem.enqueue.call_args[0][0]
        assert event["detail"] == complex_detail
        assert event["detail"]["steps"][0]["status"] == "completed"


@pytest.mark.asyncio
async def test_audit_timestamp_is_valid_iso():
    """Test audit() generates valid ISO 8601 timestamp."""
    mock_siem = Mock()
    mock_siem.enqueue = Mock()

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        mock_user = Mock()
        mock_user.username = "iris"
        mock_db = Mock()

        audit(
            db=mock_db,
            user=mock_user,
            action="timestamp_test",
            resource_id="test",
            detail={}
        )

        event = mock_siem.enqueue.call_args[0][0]
        timestamp_str = event["timestamp"]

        # Parse to verify it's valid ISO format
        try:
            # ISO format: YYYY-MM-DDTHH:MM:SS.ffffff
            datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Timestamp {timestamp_str} is not valid ISO 8601")


@pytest.mark.asyncio
async def test_audit_with_special_characters_in_detail():
    """Test audit() handles special characters in detail values."""
    mock_siem = Mock()
    mock_siem.enqueue = Mock()

    with patch('ee.services.siem_service.get_siem_service', return_value=mock_siem):
        mock_user = Mock()
        mock_user.username = "jack"
        mock_db = Mock()

        detail = {
            "command": "curl -H 'Authorization: Bearer token' https://example.com",
            "error": "Connection timeout (>5000ms)",
            "path": "/var/log/app.log",
            "json_data": '{"key": "value"}',
        }

        audit(
            db=mock_db,
            user=mock_user,
            action="command_execute",
            resource_id="cmd_123",
            detail=detail
        )

        event = mock_siem.enqueue.call_args[0][0]
        assert event["detail"]["command"] == "curl -H 'Authorization: Bearer token' https://example.com"
        assert event["detail"]["error"] == "Connection timeout (>5000ms)"
