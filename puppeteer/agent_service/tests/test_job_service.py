import pytest
from puppeteer.agent_service.services.job_service import JobService
from puppeteer.agent_service.db import Job, Node
from puppeteer.agent_service.models import JobCreate, ResultReport
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
    assert job["result"] == {"output": "success"}
