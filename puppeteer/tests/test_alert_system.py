import pytest
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Mock ws_manager before importing services
mock_main = MagicMock()
mock_ws = AsyncMock()
mock_main.ws_manager = mock_ws
sys.modules['agent_service.main'] = mock_main

from agent_service.services.job_service import JobService
from agent_service.services.alert_service import AlertService
from agent_service.db import Job, Node, Alert, AuditLog, ExecutionRecord
from agent_service.models import ResultReport, HeartbeatPayload

def _make_mock_db(objects_to_return=None):
    """Create a mock DB session."""
    mock_db = AsyncMock()
    execute_result = MagicMock()
    
    if isinstance(objects_to_return, dict):
        def side_effect(query):
            query_str = str(query).lower()
            m = MagicMock()
            found = False
            for key, val in objects_to_return.items():
                if key.lower() in query_str:
                    if isinstance(val, list):
                        m.scalars().all.return_value = val
                        m.scalar_one_or_none.return_value = val[0] if val else None
                    else:
                        m.scalar_one_or_none.return_value = val
                        m.scalars().all.return_value = [val] if val else []
                    found = True
                    break
            
            if not found:
                m.scalar_one_or_none.return_value = None
                m.scalars().all.return_value = []
            return m
        mock_db.execute.side_effect = side_effect
    else:
        execute_result.scalar_one_or_none.return_value = objects_to_return
        execute_result.scalars().all.return_value = [objects_to_return] if objects_to_return else []
        mock_db.execute.return_value = execute_result

    added_objects = []
    mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    return mock_db, added_objects

@pytest.mark.asyncio
async def test_job_failure_triggers_alert():
    """Test that exhausting retries triggers a DEAD_LETTER status and an Alert."""
    mock_ws.reset_mock()
    fake_job = Job(
        guid="fail-guid-001",
        task_type="python_script",
        max_retries=1,
        retry_count=1,
        backoff_multiplier=2.0,
        status="ASSIGNED",
        payload=json.dumps({"script": "print(1)", "secrets": {}}),
        started_at=datetime.utcnow(),
        node_id="node-1"
    )

    mock_db, added_objects = _make_mock_db({"job": [fake_job]})

    report = ResultReport(
        success=False,
        result={"error": "exit 1"},
        exit_code=1,
        retriable=True
    )

    await JobService.report_result("fail-guid-001", report, "10.0.0.1", mock_db)

    assert fake_job.status == "DEAD_LETTER"
    alerts = [obj for obj in added_objects if isinstance(obj, Alert)]
    assert len(alerts) == 1
    assert alerts[0].type == "job_failure"

@pytest.mark.asyncio
async def test_node_offline_triggers_alert():
    """Test that missed heartbeats trigger OFFLINE status and an Alert."""
    mock_ws.reset_mock()
    old_time = datetime.utcnow() - timedelta(minutes=10)
    fake_node = Node(
        node_id="node-123",
        hostname="test-node",
        status="ONLINE",
        ip="10.0.0.1",
        last_seen=old_time
    )

    mock_db, added_objects = _make_mock_db({"node": [fake_node]})

    count = await AlertService.check_node_health(mock_db)
    
    assert count == 1
    assert fake_node.status == "OFFLINE"
    alerts = [obj for obj in added_objects if isinstance(obj, Alert)]
    assert len(alerts) == 1
    assert alerts[0].type == "node_offline"

@pytest.mark.asyncio
async def test_auto_resolve_on_heartbeat():
    """Test that a new heartbeat resolves existing offline alerts."""
    mock_ws.reset_mock()
    node_id = "node-offline-1"
    
    fake_node = Node(
        node_id=node_id,
        hostname="test-node",
        status="OFFLINE",
        ip="10.0.0.1",
        last_seen=datetime.utcnow() - timedelta(minutes=10),
        pending_upgrade=None
    )

    fake_alert = Alert(
        id=1,
        type="node_offline",
        resource_id=node_id,
        acknowledged=False,
        message="Node is offline",
        severity="WARNING"
    )

    mock_db, added_objects = _make_mock_db({
        "node": [fake_node],
        "alert": [fake_alert]
    })

    hb = HeartbeatPayload(
        node_id=node_id,
        hostname="test-node",
        status="ONLINE",
        stats={"cpu": 10, "ram": 20},
        capabilities={},
        tags=[]
    )

    await JobService.receive_heartbeat(node_id, "10.0.0.1", hb, mock_db)

    assert fake_node.status == "ONLINE"
    assert fake_alert.acknowledged is True
    assert fake_alert.acknowledged_by == "system:auto_resolve"

@pytest.mark.asyncio
async def test_security_tamper_triggers_alert():
    """Test that reporting unauthorized tools triggers a TAMPERED status and a security alert."""
    mock_ws.reset_mock()
    node_id = "node-tamper-1"
    
    fake_node = Node(
        node_id=node_id,
        hostname="tamper-node",
        status="ONLINE",
        ip="10.0.0.1",
        expected_capabilities=json.dumps({"python": "3.11"}),
        last_seen=datetime.utcnow(),
        pending_upgrade=None
    )

    mock_db, added_objects = _make_mock_db({"node": [fake_node]})

    hb = HeartbeatPayload(
        node_id=node_id,
        hostname="tamper-node",
        status="ONLINE",
        stats={"cpu": 1, "ram": 2},
        capabilities={"python": "3.11", "netcat": "7.9"},
        tags=[]
    )

    await JobService.receive_heartbeat(node_id, "10.0.0.1", hb, mock_db)

    assert fake_node.status == "TAMPERED"
    assert "unauthorized tools" in fake_node.tamper_details.lower()
    alerts = [obj for obj in added_objects if isinstance(obj, Alert)]
    assert any(a.type == "security_tamper" for a in alerts)

@pytest.mark.asyncio
async def test_webhook_dispatch_on_alert():
    """Test that creating an alert triggers a webhook dispatch task."""
    from agent_service.db import Webhook
    mock_ws.reset_mock()
    
    fake_webhook = Webhook(
        id=99,
        url="https://example.com/hook",
        secret="whsec_123",
        events="*",
        active=True
    )
    
    # Mock DB to return the webhook
    mock_db, added_objects = _make_mock_db({"webhook": [fake_webhook]})
    
    # We need to patch the async task creation or the _send_webhook call
    with patch("agent_service.services.webhook_service.WebhookService._send_webhook", new_callable=AsyncMock) as mock_send:
        await AlertService.create_alert(
            mock_db,
            type="test_event",
            severity="INFO",
            message="Test webhook dispatch"
        )
        
        # Verify dispatch_event logic triggered the task
        assert mock_send.called
        # Check that the URL matches
        args, kwargs = mock_send.call_args
        assert args[1] == "https://example.com/hook"
        # Check that secret is used
        assert args[2] == "whsec_123"
