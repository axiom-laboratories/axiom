from puppeteer.agent_service.models import JobCreate, NodeResponse
import pytest
from datetime import datetime

def test_job_create_model():
    payload = {"cmd": "echo hello"}
    job = JobCreate(task_type="script", payload=payload, priority=10)
    assert job.task_type == "script"
    assert job.priority == 10
    assert job.payload == payload

def test_node_response_model():
    now = datetime.utcnow()
    node = NodeResponse(
        node_id="n1", 
        hostname="host1", 
        ip="1.1.1.1", 
        last_seen=now, 
        status="ONLINE"
    )
    assert node.node_id == "n1"
    assert node.status == "ONLINE"