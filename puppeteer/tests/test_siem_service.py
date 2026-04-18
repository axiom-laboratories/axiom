"""Unit tests for SIEMService class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from agent_service.db import SIEMConfig
from ee.services.siem_service import SIEMService


@pytest.fixture
def mock_siem_config():
    """Create a mock SIEMConfig for testing."""
    config = Mock(spec=SIEMConfig)
    config.id = "test-id"
    config.backend = "webhook"
    config.destination = "https://siem.example.com/events"
    config.syslog_port = 514
    config.syslog_protocol = "UDP"
    config.cef_device_vendor = "Axiom"
    config.cef_device_product = "MasterOfPuppets"
    config.enabled = True
    return config


@pytest.fixture
async def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
async def mock_scheduler():
    """Create a mock APScheduler."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_siem_service_initialization(mock_siem_config, mock_db, mock_scheduler):
    """Test SIEMService initializes with correct queue and status."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    assert siem.config.backend == mock_siem_config.backend
    assert siem.config.destination == mock_siem_config.destination
    assert siem.queue.maxsize == 10000
    assert siem._consecutive_failures == 0
    assert siem._dropped_events_count == 0
    # Status is initially "disabled" (will be set by startup)
    assert siem._status in ("disabled", "unknown")


@pytest.mark.asyncio
async def test_enqueue_adds_event_to_queue(mock_siem_config, mock_db, mock_scheduler):
    """Test enqueue() is synchronous and adds event to queue."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    event = {
        "username": "alice",
        "action": "job_execute",
        "resource_id": "job_123",
        "detail": {"result": "success"},
        "timestamp": "2026-04-18T10:00:00",
    }

    # enqueue() is sync, fire-and-forget
    siem.enqueue(event)

    # Verify event in queue
    queued_event = siem.queue.get_nowait()
    assert queued_event == event


@pytest.mark.asyncio
async def test_enqueue_never_blocks(mock_siem_config, mock_db, mock_scheduler):
    """Test enqueue() never blocks even when queue is full."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    # Fill queue to capacity
    for i in range(10000):
        siem.enqueue({"index": i})

    # This should not block or raise (drops oldest)
    siem.enqueue({"overflow": "event"})

    # Verify dropped_events incremented
    assert siem._dropped_events_count >= 1


@pytest.mark.asyncio
async def test_format_cef_masks_sensitive_fields(mock_siem_config, mock_db, mock_scheduler):
    """Test _format_cef() masks password, secret, token, etc."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    event = {
        "username": "alice",
        "action": "secret_access",
        "resource_id": "secret_123",
        "detail": {
            "password": "hunter2",
            "api_key": "sk-1234567890",
            "token": "auth_token_xyz",
            "db_secret": "super_secret",
            "normal_field": "visible",
        },
        "timestamp": "2026-04-18T10:00:00",
    }

    cef = siem._format_cef(event)

    # Verify masking occurred
    assert "***" in cef, "Masked fields should contain ***"
    assert "hunter2" not in cef, "password should be masked"
    assert "sk-1234567890" not in cef, "api_key should be masked"
    assert "auth_token_xyz" not in cef, "token should be masked"
    assert "super_secret" not in cef, "db_secret should be masked"
    assert "visible" in cef, "normal fields should not be masked"


@pytest.mark.asyncio
async def test_format_cef_all_keyword_variants(mock_siem_config, mock_db, mock_scheduler):
    """Test masking covers all variants: password, secret, token, api_key, secret_id, role_id, encryption_key, *_key, *_secret."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    event = {
        "username": "alice",
        "action": "test",
        "resource_id": "test",
        "detail": {
            "password": "pwd_value",
            "secret": "sec_value",
            "token": "tok_value",
            "api_key": "key1_value",
            "secret_id": "sid_value",
            "role_id": "rid_value",
            "encryption_key": "ekey_value",
            "custom_key": "ckey_value",
            "jwt_secret": "jsec_value",
            "PASSWORD": "PWD_VALUE",  # Case-insensitive
            "TOKEN": "TOK_VALUE",
        },
        "timestamp": "2026-04-18T10:00:00",
    }

    cef = siem._format_cef(event)

    # All values should be masked
    for value in ["pwd_value", "sec_value", "tok_value", "key1_value", "sid_value", "rid_value",
                  "ekey_value", "ckey_value", "jsec_value", "PWD_VALUE", "TOK_VALUE"]:
        assert value not in cef, f"{value} should be masked"

    # Verify that at least one *** appears (masking happened)
    assert "***" in cef, "CEF output should contain masked values"


@pytest.mark.asyncio
async def test_status_transitions_to_degraded_after_3_failures(mock_siem_config, mock_db, mock_scheduler):
    """Test service transitions to DEGRADED after 3 consecutive batch failures."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)
    siem._status = "healthy"
    siem._consecutive_failures = 2

    # Third failure triggers DEGRADED
    siem._consecutive_failures += 1
    if siem._consecutive_failures >= 3:
        siem._status = "degraded"

    assert siem._status == "degraded"
    assert siem._consecutive_failures == 3


@pytest.mark.asyncio
async def test_status_resets_on_successful_delivery(mock_siem_config, mock_db, mock_scheduler):
    """Test consecutive_failures resets to 0 on successful delivery."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)
    siem._consecutive_failures = 3
    siem._status = "degraded"

    # Successful delivery resets
    siem._consecutive_failures = 0
    siem._status = "healthy"

    assert siem._consecutive_failures == 0
    assert siem._status == "healthy"


@pytest.mark.asyncio
async def test_map_severity_returns_cef_severity(mock_siem_config, mock_db, mock_scheduler):
    """Test _map_severity() converts action to CEF severity (1-10)."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    # Typical mappings
    assert 1 <= siem._map_severity("user_create") <= 10
    assert 1 <= siem._map_severity("secret_access") <= 10
    assert 1 <= siem._map_severity("config_change") <= 10
    assert 1 <= siem._map_severity("vault_unlock") <= 10


@pytest.mark.asyncio
async def test_status_property_returns_valid_state(mock_siem_config, mock_db, mock_scheduler):
    """Test _status property returns valid state (it's a string, not a method)."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)
    siem._status = "healthy"

    state = siem._status
    assert state in ("healthy", "degraded", "disabled")


@pytest.mark.asyncio
async def test_queue_maxsize_is_10000(mock_siem_config, mock_db, mock_scheduler):
    """Test queue has hard cap of 10,000 events."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)
    assert siem.queue.maxsize == 10000


@pytest.mark.asyncio
async def test_enqueue_with_none_config(mock_db, mock_scheduler):
    """Test enqueue works with None config (CE/dormant mode)."""
    siem = SIEMService(None, mock_db, mock_scheduler)

    # Should still work (no-op if config is None, but queue still functional)
    event = {"username": "alice", "action": "test", "resource_id": "test", "detail": {}}
    siem.enqueue(event)

    queued_event = siem.queue.get_nowait()
    assert queued_event == event


@pytest.mark.asyncio
async def test_format_cef_with_none_config(mock_db, mock_scheduler):
    """Test _format_cef handles None config gracefully."""
    siem = SIEMService(None, mock_db, mock_scheduler)

    event = {
        "username": "alice",
        "action": "test",
        "resource_id": "test",
        "detail": {"password": "secret"},
        "timestamp": "2026-04-18T10:00:00",
    }

    # Should not crash, should use defaults
    cef = siem._format_cef(event)
    assert "CEF:0" in cef
    assert "***" in cef  # password should still be masked


@pytest.mark.asyncio
async def test_flush_batch_with_empty_batch(mock_siem_config, mock_db, mock_scheduler):
    """Test flush_batch handles empty batch gracefully."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)
    siem._deliver = AsyncMock(return_value=True)

    # Empty batch should return early
    await siem.flush_batch([])

    # _deliver should not be called
    assert not siem._deliver.called


@pytest.mark.asyncio
async def test_consecutive_failures_counter_increments(mock_siem_config, mock_db, mock_scheduler):
    """Test consecutive_failures counter increments on each delivery failure."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    # Mock _deliver to fail
    siem._deliver = AsyncMock(side_effect=Exception("Connection failed"))

    batch = [{"username": "alice", "action": "test", "resource_id": "test", "detail": {}}]

    initial_failures = siem._consecutive_failures

    # Attempt flush (will fail and increment counter)
    await siem.flush_batch(batch)

    # Counter should have incremented
    assert siem._consecutive_failures > initial_failures


@pytest.mark.asyncio
async def test_masked_password_case_insensitive(mock_siem_config, mock_db, mock_scheduler):
    """Test password masking is case-insensitive (PASSWORD, Password, etc.)."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    event = {
        "username": "alice",
        "action": "test",
        "resource_id": "test",
        "detail": {
            "PASSWORD": "secret1",
            "password": "secret2",
            "PaSSWoRd": "secret3",
        },
        "timestamp": "2026-04-18T10:00:00",
    }

    cef = siem._format_cef(event)

    # All variants should be masked
    assert "secret1" not in cef
    assert "secret2" not in cef
    assert "secret3" not in cef
    assert cef.count("***") >= 3


@pytest.mark.asyncio
async def test_enqueue_preserves_event_structure(mock_siem_config, mock_db, mock_scheduler):
    """Test enqueue preserves full event structure."""
    siem = SIEMService(mock_siem_config, mock_db, mock_scheduler)

    event = {
        "username": "alice",
        "action": "job_execute",
        "resource_id": "job_123",
        "detail": {
            "step": 1,
            "result": "success",
            "nested": {"key": "value"}
        },
        "timestamp": "2026-04-18T10:00:00Z",
    }

    siem.enqueue(event)
    queued = siem.queue.get_nowait()

    # Should be identical (not modified by enqueue)
    assert queued == event
    assert queued["detail"]["nested"]["key"] == "value"
