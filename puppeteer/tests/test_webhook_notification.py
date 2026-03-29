"""
Tests for CE webhook notification delivery (Phase 89 — ALRT-01, ALRT-02, ALRT-03).
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
mock_main = MagicMock()
mock_ws = AsyncMock()
mock_main.ws_manager = mock_ws
sys.modules['agent_service.main'] = mock_main

from agent_service.services.webhook_service import WebhookService
from agent_service.db import Config


def _make_db(config_map: dict):
    """Create a mock DB that returns Config rows from a dict."""
    mock_db = AsyncMock()
    added = []
    mock_db.add = MagicMock(side_effect=lambda obj: added.append(obj))

    async def execute(query):
        m = MagicMock()
        query_str = str(query)
        matched = None
        for key, val in config_map.items():
            if key in query_str:
                matched = Config(key=key, value=val)
                break
        m.scalar_one_or_none.return_value = matched
        m.scalars().all.return_value = [Config(key=k, value=v) for k, v in config_map.items()]
        return m

    mock_db.execute = execute
    return mock_db, added


@pytest.mark.asyncio
async def test_dispatch_sends_post():
    """Enabled webhook with valid URL triggers HTTP POST with correct payload."""
    config = {
        "alerts.webhook_url": "http://example.com/hook",
        "alerts.webhook_enabled": "true",
        "alerts.webhook_security_rejections": "false",
    }
    mock_db, added = _make_db(config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await WebhookService.dispatch_event(mock_db, "job:failed", {
            "guid": "abc-123",
            "job_name": "nightly-backup",
            "node_id": "node-alpha",
            "error_summary": "exit code 1",
            "failed_at": "2026-03-29T22:15:00Z",
        })

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://example.com/hook"
        payload = call_args[1]["json"]
        assert payload["event"] == "job.failed"
        assert payload["job_name"] == "nightly-backup"
        assert payload["node_id"] == "node-alpha"


@pytest.mark.asyncio
async def test_disabled_no_send():
    """Disabled toggle means no HTTP POST regardless of URL."""
    config = {
        "alerts.webhook_url": "http://example.com/hook",
        "alerts.webhook_enabled": "false",
        "alerts.webhook_security_rejections": "false",
    }
    mock_db, _ = _make_db(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        await WebhookService.dispatch_event(mock_db, "job:failed", {"guid": "x"})
        mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_security_rejected_opt_in():
    """SECURITY_REJECTED only delivers when webhook_security_rejections=true."""
    config_off = {
        "alerts.webhook_url": "http://example.com/hook",
        "alerts.webhook_enabled": "true",
        "alerts.webhook_security_rejections": "false",
    }
    mock_db, _ = _make_db(config_off)

    with patch("httpx.AsyncClient") as mock_client_cls:
        await WebhookService.dispatch_event(mock_db, "job:security_rejected", {"guid": "y"})
        mock_client_cls.assert_not_called()

    config_on = {**config_off, "alerts.webhook_security_rejections": "true"}
    mock_db2, _ = _make_db(config_on)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await WebhookService.dispatch_event(mock_db2, "job:security_rejected", {
            "guid": "y", "job_name": "sec-job", "node_id": "n1",
            "error_summary": "rejected", "failed_at": "2026-03-29T22:00:00Z",
        })
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["event"] == "job.security_rejected"


@pytest.mark.asyncio
async def test_completed_no_alert():
    """COMPLETED status does not trigger dispatch (filtering is in job_service, not webhook_service)."""
    # This tests that webhook_service properly ignores non-failure event types
    config = {
        "alerts.webhook_url": "http://example.com/hook",
        "alerts.webhook_enabled": "true",
        "alerts.webhook_security_rejections": "false",
    }
    mock_db, _ = _make_db(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        await WebhookService.dispatch_event(mock_db, "job:completed", {"guid": "z"})
        mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_delivery_status_written():
    """After successful delivery, last_delivery_status Config key is updated."""
    config = {
        "alerts.webhook_url": "http://example.com/hook",
        "alerts.webhook_enabled": "true",
        "alerts.webhook_security_rejections": "false",
    }
    mock_db, added = _make_db(config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "accepted"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await WebhookService.dispatch_event(mock_db, "job:failed", {
            "guid": "abc", "job_name": "job", "node_id": "n",
            "error_summary": "err", "failed_at": "2026-03-29T22:00:00Z",
        })

    status_configs = [obj for obj in added if isinstance(obj, Config) and obj.key == "alerts.last_delivery_status"]
    assert len(status_configs) == 1
    parsed = json.loads(status_configs[0].value)
    assert parsed["status_code"] == 200


@pytest.mark.asyncio
async def test_delivery_failure_no_exception():
    """Connection errors are caught and logged; no exception propagates."""
    config = {
        "alerts.webhook_url": "http://unreachable.invalid/hook",
        "alerts.webhook_enabled": "true",
        "alerts.webhook_security_rejections": "false",
    }
    mock_db, added = _make_db(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Should not raise
        await WebhookService.dispatch_event(mock_db, "job:failed", {
            "guid": "err", "job_name": "job", "node_id": "n",
            "error_summary": "err", "failed_at": "2026-03-29T22:00:00Z",
        })

    status_configs = [obj for obj in added if isinstance(obj, Config) and obj.key == "alerts.last_delivery_status"]
    assert len(status_configs) == 1
    parsed = json.loads(status_configs[0].value)
    assert parsed["status_code"] is None


def test_config_model_validation():
    """AlertsConfigUpdate rejects invalid URL format."""
    from agent_service.models import AlertsConfigUpdate
    from pydantic import ValidationError

    # Valid http
    m = AlertsConfigUpdate(webhook_url="http://example.com/hook")
    assert m.webhook_url == "http://example.com/hook"

    # Valid https
    m2 = AlertsConfigUpdate(webhook_url="https://example.com/hook")
    assert m2.webhook_url == "https://example.com/hook"

    # Empty string is allowed (clearing the URL)
    m3 = AlertsConfigUpdate(webhook_url="")
    assert m3.webhook_url == ""

    # Invalid format raises
    with pytest.raises(ValidationError):
        AlertsConfigUpdate(webhook_url="ftp://not-allowed")
