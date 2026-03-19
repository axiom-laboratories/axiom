import pytest
from agent_service.services.job_service import JobService
from agent_service.db import Job, Node
from agent_service.models import JobCreate, ResultReport
import json

@pytest.mark.anyio
async def test_create_and_list_jobs(db_session):
    # Test Create
    job_req = JobCreate(
        task_type="python_script",
        payload={"code": "print('hello')"},
        target_tags=["linux"]
    )
    result = await JobService.create_job(job_req, db_session)
    assert "guid" in result
    guid = result["guid"]
    
    # Test List
    jobs = await JobService.list_jobs(db_session)
    assert len(jobs) > 0
    assert any(j["guid"] == guid for j in jobs)

@pytest.mark.anyio
async def test_pull_work_matching_tags(db_session):
    # Create a node with tags
    node = Node(
        node_id="node1",
        hostname="node1",
        ip="127.0.0.1",
        status="ONLINE",
        tags=json.dumps(["gpu", "linux"])
    )
    db_session.add(node)
    await db_session.commit()
    
    # Create a job requiring "gpu"
    job_req = JobCreate(
        task_type="python_script",
        payload={"cmd": "nvidia-smi"},
        target_tags=["gpu"]
    )
    await JobService.create_job(job_req, db_session)
    
    # Pull work for node1
    poll_resp = await JobService.pull_work("node1", "127.0.0.1", db_session)
    assert poll_resp.job is not None
    assert poll_resp.job.task_type == "python_script"

@pytest.mark.anyio
async def test_pull_work_mismatch_tags(db_session):
    # Create a job requiring "secure"
    job_req = JobCreate(
        task_type="python_script",
        payload={"cmd": "secret_task"},
        target_tags=["secure"]
    )
    await JobService.create_job(job_req, db_session)
    
    # Node1 doesn't have "secure" tag
    poll_resp = await JobService.pull_work("node1", "127.0.0.1", db_session)
    assert poll_resp.job is None

@pytest.mark.anyio
async def test_report_result(db_session):
    # Create job
    job_req = JobCreate(task_type="python_script", payload={"x": 1})
    result = await JobService.create_job(job_req, db_session)
    guid = result["guid"]
    
    # Report success
    report = ResultReport(success=True, result={"output": "success"})
    await JobService.report_result(guid, report, "127.0.0.1", db_session)
    
    # Verify status
    jobs = await JobService.list_jobs(db_session)
    job = next(j for j in jobs if j["guid"] == guid)
    assert job["status"] == "COMPLETED"
    # Job.result stores a minimal summary; full output goes to ExecutionRecord
    assert job["result"] == {"exit_code": None}

@pytest.mark.anyio
async def test_receive_heartbeat(db_session):
    from agent_service.models import HeartbeatPayload
    
    # 1. New node heartbeat
    payload = HeartbeatPayload(
        node_id="heartbeat_node",
        hostname="heartbeat_host",
        stats={"cpu": 10, "ram": 50},
        tags=["linux"]
    )
    await JobService.receive_heartbeat("heartbeat_node", "192.168.1.10", payload, db_session)
    
    # Verify node created
    from sqlalchemy.future import select
    from agent_service.db import Node
    res = await db_session.execute(select(Node).where(Node.node_id == "heartbeat_node"))
    node = res.scalar_one()
    assert node.hostname == "heartbeat_host"
    assert node.ip == "192.168.1.10"
    assert node.status == "ONLINE"
    assert json.loads(node.tags) == ["linux"]

    # 2. Update existing node
    payload.stats = {"cpu": 20, "ram": 60}
    await JobService.receive_heartbeat("heartbeat_node", "192.168.1.11", payload, db_session)
    
    await db_session.refresh(node)
    assert node.ip == "192.168.1.11"
    assert json.loads(node.stats) == {"cpu": 20, "ram": 60}
