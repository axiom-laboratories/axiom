import pytest
import os
from httpx import ASGITransport, AsyncClient
from agent_service.main import app
from agent_service.db import Job
from sqlalchemy.future import select
import json

@pytest.mark.anyio
async def test_get_job_stats(db_session):
    # Create some jobs with different statuses
    j1 = Job(guid="stat1", task_type="test", status="COMPLETED", payload="{}")
    j2 = Job(guid="stat2", task_type="test", status="FAILED", payload="{}")
    j3 = Job(guid="stat3", task_type="test", status="PENDING", payload="{}")
    
    db_session.add_all([j1, j2, j3])
    await db_session.commit()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/jobs/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["counts"]["COMPLETED"] == 1
        assert data["counts"]["FAILED"] == 1
        assert data["counts"]["PENDING"] == 1
        assert data["counts"]["ASSIGNED"] == 0
        assert data["total_jobs"] == 3
        assert data["success_rate"] == 50.0

@pytest.mark.anyio
async def test_flight_recorder_on_failure(db_session):
    # Create a job to report failure for
    job = Job(guid="fail-guid", task_type="test", status="ASSIGNED", node_id="node1", payload="{}")
    db_session.add(job)
    await db_session.commit()
    
    report_payload = {
        "success": False,
        "result": {"partial": "data"},
        "error_details": {
            "message": "Division by zero",
            "exit_code": 1,
            "stack_trace": "line 10: x/0"
        }
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"X-API-Key": os.getenv("API_KEY", "test-key-123")}
        # Note: In main.py, reporting is POST /work/{guid}/result
        response = await ac.post("/work/fail-guid/result", json=report_payload, headers=headers)
        assert response.status_code == 200
        
    # Verify DB state
    result = await db_session.execute(select(Job).where(Job.guid == "fail-guid"))
    updated_job = result.scalar_one()
    assert updated_job.status == "FAILED"
    
    result_data = json.loads(updated_job.result)
    assert "flight_recorder" in result_data
    assert result_data["flight_recorder"]["error"] == "Division by zero"
    assert result_data["flight_recorder"]["exit_code"] == 1
    assert "analysis" in result_data["flight_recorder"]
