"""
Test suite for workflow CRUD operations and DAG validation (Phase 146).

Tests are organized by requirement (WORKFLOW-01 through WORKFLOW-05).
All test cases validate create, list, update, delete, fork, and validate endpoints.
"""
import pytest
from uuid import uuid4


# WORKFLOW-01: Create Workflow with DAG validation

@pytest.mark.asyncio
async def test_create_workflow_success(async_client, auth_headers):
    """WORKFLOW-01: Create a valid workflow with steps and edges.

    Verifies that a workflow can be created with a valid DAG structure.
    """
    # Arrange: build request payload with explicit step IDs matching API temp naming
    job_ids = [str(uuid4()) for _ in range(3)]
    step_ids = ["temp_step_0", "temp_step_1", "temp_step_2"]  # Match API's auto-generated temp naming
    request_payload = {
        "name": f"test-workflow-{uuid4().hex[:8]}",
        "steps": [
            {"node_type": "SCRIPT", "scheduled_job_id": job_ids[i]}
            for i in range(3)
        ],
        "edges": [
            {"from_step_id": step_ids[0], "to_step_id": step_ids[1]},
            {"from_step_id": step_ids[1], "to_step_id": step_ids[2]}
        ],
        "parameters": [
            {"name": "param1", "type": "string", "default_value": "default"}
        ]
    }

    # Act: create workflow via API
    response = await async_client.post("/api/workflows", json=request_payload, headers=auth_headers)

    # Assert: status code and response structure
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["id"]
    assert data["name"] == request_payload["name"]
    assert data["created_by"] == "admin"
    assert data["is_paused"] == False
    assert len(data["steps"]) == 3
    assert len(data["edges"]) == 2  # Two edges: step0→step1, step1→step2
    assert len(data["parameters"]) == 1
    assert all(step["node_type"] == "SCRIPT" for step in data["steps"])
    # Verify each step has required fields
    for step in data["steps"]:
        assert "id" in step
        assert "scheduled_job_id" in step
        assert "node_type" in step


@pytest.mark.asyncio
async def test_create_workflow_invalid_edges(async_client, auth_headers):
    """WORKFLOW-01: Reject workflow creation if edge references non-existent step.

    Verifies referential integrity: all from_step_id and to_step_id must exist in steps[].
    Expected response: HTTP 422 with error: INVALID_EDGE_REFERENCE
    """
    # Arrange: workflow with invalid edge reference
    request_payload = {
        "name": f"test-invalid-edges-{uuid4().hex[:8]}",
        "steps": [
            {"node_type": "SCRIPT", "scheduled_job_id": str(uuid4())},
            {"node_type": "SCRIPT", "scheduled_job_id": str(uuid4())}
        ],
        "edges": [
            {"from_step_id": str(uuid4()), "to_step_id": str(uuid4())}  # Non-existent IDs
        ],
        "parameters": []
    }

    # Act: attempt to create workflow with invalid edge
    response = await async_client.post("/api/workflows", json=request_payload, headers=auth_headers)

    # Assert: HTTP 422 with INVALID_EDGE_REFERENCE
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    data = response.json()
    assert data["detail"]["error"] == "INVALID_EDGE_REFERENCE"
    assert "edge" in data["detail"]


@pytest.mark.asyncio
async def test_create_workflow_cycle_detected(async_client, auth_headers):
    """WORKFLOW-01: Reject workflow creation if DAG contains a cycle.

    Verifies cycle detection using networkx library.
    Expected response: HTTP 422 with error: CYCLE_DETECTED and cycle_path.
    """
    # Arrange: create 3 steps with temp_step_* IDs, edges forming a cycle s1→s2→s3→s1
    step_ids = ["temp_step_0", "temp_step_1", "temp_step_2"]  # Match API's auto-generated temp naming
    job_ids = [str(uuid4()) for _ in range(3)]
    request_payload = {
        "name": f"test-cycle-{uuid4().hex[:8]}",
        "steps": [
            {"node_type": "SCRIPT", "scheduled_job_id": job_ids[i]}
            for i in range(3)
        ],
        "edges": [
            {"from_step_id": step_ids[0], "to_step_id": step_ids[1]},
            {"from_step_id": step_ids[1], "to_step_id": step_ids[2]},
            {"from_step_id": step_ids[2], "to_step_id": step_ids[0]}  # Cycle back
        ],
        "parameters": []
    }

    # Act: attempt to create workflow with cycle
    response = await async_client.post("/api/workflows", json=request_payload, headers=auth_headers)

    # Assert: HTTP 422 with CYCLE_DETECTED
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    data = response.json()
    assert data["detail"]["error"] == "CYCLE_DETECTED"
    assert "cycle_path" in data["detail"]
    assert isinstance(data["detail"]["cycle_path"], list)


# WORKFLOW-02: List Workflows

@pytest.mark.asyncio
async def test_list_workflows(async_client, auth_headers):
    """WORKFLOW-02: List all workflows with metadata and counts.

    Verifies that GET /api/workflows returns list with step_count and last_run_status.
    Full graph (steps[], edges[], parameters[]) is NOT returned in list — only metadata.
    """
    # Arrange: create 2 workflows via API
    job_id = str(uuid4())
    workflow_names = [f"workflow-list-test-{i}-{uuid4().hex[:4]}" for i in range(2)]

    for name in workflow_names:
        request_payload = {
            "name": name,
            "steps": [{"node_type": "SCRIPT", "scheduled_job_id": job_id}],
            "edges": [],
            "parameters": []
        }
        response = await async_client.post("/api/workflows", json=request_payload, headers=auth_headers)
        assert response.status_code == 201

    # Act: list all workflows
    response = await async_client.get("/api/workflows", headers=auth_headers)

    # Assert: list response has metadata only (no nested graph)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Verify each item has metadata but NOT full graph
    for item in data:
        assert "id" in item
        assert "name" in item
        assert "created_by" in item
        assert "created_at" in item
        assert "is_paused" in item
        assert "step_count" in item
        # Verify full graph is NOT in list response
        assert "steps" not in item or len(item.get("steps", [])) == 0


# WORKFLOW-03: Update Workflow with DAG re-validation

@pytest.mark.asyncio
async def test_update_workflow_success(async_client, auth_headers, workflow_fixture):
    """WORKFLOW-03: Update an existing workflow's steps and edges.

    Verifies that PUT /api/workflows/{id} atomically replaces all steps/edges/parameters.
    Server deletes existing graph and inserts new one only after validation passes.
    """
    workflow_id = workflow_fixture["id"]

    # Arrange: modify workflow by replacing with a simpler 2-step chain
    job_ids = [str(uuid4()) for _ in range(2)]
    request_payload = {
        "steps": [
            {"node_type": "SCRIPT", "scheduled_job_id": job_ids[0]},
            {"node_type": "SCRIPT", "scheduled_job_id": job_ids[1]}
        ],
        "edges": [
            # The API will auto-generate temp_step_0, temp_step_1 IDs, so we reference those
            {"from_step_id": "temp_step_0", "to_step_id": "temp_step_1"}
        ],
        "parameters": []
    }

    # Act: update workflow
    response = await async_client.put(f"/api/workflows/{workflow_id}", json=request_payload, headers=auth_headers)

    # Assert: status code and updated structure
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["id"] == workflow_id
    assert len(data["steps"]) == 2
    assert len(data["edges"]) == 1


@pytest.mark.asyncio
async def test_update_workflow_cycle_detected(async_client, auth_headers, workflow_fixture):
    """WORKFLOW-03: Reject workflow update if it creates a cycle.

    Verifies that validation runs before any write to the database.
    Expected response: HTTP 422 with error: CYCLE_DETECTED
    """
    workflow_id = workflow_fixture["id"]

    # Arrange: update workflow with temp_step_* IDs that form a cycle
    job_ids = [str(uuid4()) for _ in range(3)]
    request_payload = {
        "steps": [
            {"node_type": "SCRIPT", "scheduled_job_id": job_ids[i]}
            for i in range(3)
        ],
        "edges": [
            {"from_step_id": "temp_step_0", "to_step_id": "temp_step_1"},
            {"from_step_id": "temp_step_1", "to_step_id": "temp_step_2"},
            {"from_step_id": "temp_step_2", "to_step_id": "temp_step_0"}  # Cycle back
        ],
        "parameters": []
    }

    # Act: attempt to update workflow with cycle
    response = await async_client.put(f"/api/workflows/{workflow_id}", json=request_payload, headers=auth_headers)

    # Assert: HTTP 422 with CYCLE_DETECTED and DB unchanged
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["error"] == "CYCLE_DETECTED"

    # Verify workflow is unchanged in DB (still has 2 original edges)
    verify_response = await async_client.get(f"/api/workflows/{workflow_id}", headers=auth_headers)
    assert verify_response.status_code == 200
    verify_data = verify_response.json()
    assert len(verify_data["edges"]) == 2  # Still has original 2 edges


@pytest.mark.asyncio
async def test_update_workflow_depth_exceeded(async_client, auth_headers, workflow_fixture):
    """WORKFLOW-03: Reject workflow update if DAG depth exceeds 30 levels.

    Verifies depth limit validation using networkx topological traversal.
    Expected response: HTTP 422 with error: DEPTH_LIMIT_EXCEEDED and max_depth: 30
    """
    workflow_id = workflow_fixture["id"]

    # Arrange: create a deep workflow with 35 steps in a chain (depth = 34 edges, exceeds 30)
    # Use temp_step_0 through temp_step_34 to match API's auto-generated naming
    step_ids = [f"temp_step_{i}" for i in range(35)]
    job_ids = [str(uuid4()) for _ in range(35)]

    request_payload = {
        "steps": [
            {"node_type": "SCRIPT", "scheduled_job_id": job_ids[i]}
            for i in range(35)
        ],
        "edges": [
            {"from_step_id": step_ids[i], "to_step_id": step_ids[i+1]}
            for i in range(34)
        ],
        "parameters": []
    }

    # Act: attempt to update workflow with excessive depth
    response = await async_client.put(f"/api/workflows/{workflow_id}", json=request_payload, headers=auth_headers)

    # Assert: HTTP 422 with DEPTH_LIMIT_EXCEEDED
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["detail"]["error"] == "DEPTH_LIMIT_EXCEEDED"
    assert data["detail"]["max_depth"] == 30


# WORKFLOW-04: Delete Workflow with active run blocking

@pytest.mark.asyncio
async def test_delete_workflow_success(async_client, auth_headers, workflow_fixture):
    """WORKFLOW-04: Delete a workflow with no active runs.

    Verifies that DELETE /api/workflows/{id} succeeds when no workflow_runs exist.
    Cascades to delete all workflow_steps, workflow_edges, workflow_parameters.
    """
    workflow_id = workflow_fixture["id"]

    # Act: delete workflow
    response = await async_client.delete(f"/api/workflows/{workflow_id}", headers=auth_headers)

    # Assert: successful deletion (204 or 200)
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"

    # Verify workflow is deleted (should return 404)
    verify_response = await async_client.get(f"/api/workflows/{workflow_id}", headers=auth_headers)
    assert verify_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_workflow_blocked_by_active_runs(async_client, auth_headers, workflow_fixture):
    """WORKFLOW-04: Reject deletion if active workflow runs exist.

    Verifies business logic: cannot delete workflows with running instances (Phase 147).
    Expected response: HTTP 409 CONFLICT with error: ACTIVE_RUNS_EXIST and active_run_ids[]
    """
    from agent_service.db import AsyncSessionLocal, WorkflowRun
    from datetime import datetime

    workflow_id = workflow_fixture["id"]

    # Create a workflow run directly in the database (outside of async_client's session)
    async with AsyncSessionLocal() as session:
        run = WorkflowRun(
            id=str(uuid4()),
            workflow_id=workflow_id,
            status="RUNNING",
            started_at=datetime.utcnow(),
            trigger_type="MANUAL",
            triggered_by="test_user"
        )
        session.add(run)
        await session.commit()

    # Act: attempt to delete workflow with active run
    response = await async_client.delete(f"/api/workflows/{workflow_id}", headers=auth_headers)

    # Assert: HTTP 409 CONFLICT with ACTIVE_RUNS_EXIST
    assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["detail"]["error"] == "ACTIVE_RUNS_EXIST"
    assert "active_run_ids" in data["detail"]
    assert isinstance(data["detail"]["active_run_ids"], list)

    # Verify workflow is NOT deleted
    verify_response = await async_client.get(f"/api/workflows/{workflow_id}", headers=auth_headers)
    assert verify_response.status_code == 200


# WORKFLOW-05: Fork (Save-as-New) with source pausing

@pytest.mark.asyncio
async def test_fork_workflow_success(async_client, auth_headers, workflow_fixture):
    """WORKFLOW-05: Clone a workflow into a new one (Save-as-New pattern).

    Verifies POST /api/workflows/{id}/fork clones the entire graph:
    - New workflow created with new ID
    - All steps, edges, parameters cloned atomically
    - Source workflow.is_paused set to true (prevents ghost cron execution)
    - Response: full new workflow with steps[], edges[], parameters[]
    """
    source_id = workflow_fixture["id"]

    # Act: fork workflow
    response = await async_client.post(f"/api/workflows/{source_id}/fork", json={"new_name": f"forked-{uuid4().hex[:8]}"}, headers=auth_headers)

    # Assert: HTTP 201 with new workflow
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    forked = response.json()
    assert forked["id"] != source_id, "Forked workflow should have unique ID"
    assert len(forked["steps"]) == 3
    assert len(forked["edges"]) == 2
    assert len(forked["parameters"]) == 1

    # Verify source is paused
    source_response = await async_client.get(f"/api/workflows/{source_id}", headers=auth_headers)
    assert source_response.status_code == 200
    source_data = source_response.json()
    assert source_data["is_paused"] == True


@pytest.mark.asyncio
async def test_fork_pauses_source(async_client, auth_headers, workflow_fixture):
    """WORKFLOW-05: Verify that forking a workflow pauses the source.

    Verifies that after POST /api/workflows/{id}/fork succeeds,
    the source workflow's is_paused flag is set to true.
    Fetch source via GET /api/workflows/{source_id} and verify is_paused: true.
    """
    source_id = workflow_fixture["id"]

    # Verify source is NOT paused initially
    initial_response = await async_client.get(f"/api/workflows/{source_id}", headers=auth_headers)
    assert initial_response.status_code == 200
    initial_data = initial_response.json()
    assert initial_data["is_paused"] == False

    # Act: fork the workflow
    fork_response = await async_client.post(f"/api/workflows/{source_id}/fork", json={"new_name": f"forked-{uuid4().hex[:8]}"}, headers=auth_headers)
    assert fork_response.status_code == 201

    # Assert: source is now paused
    final_response = await async_client.get(f"/api/workflows/{source_id}", headers=auth_headers)
    assert final_response.status_code == 200
    final_data = final_response.json()
    assert final_data["is_paused"] == True


# Bonus: Workflow validation endpoint (used by Phase 151 canvas)

@pytest.mark.asyncio
async def test_validate_workflow_no_cycle(async_client, auth_headers):
    """Bonus: Validate a workflow without saving it.

    Verifies POST /api/workflows/validate returns validation results (no writes).
    Used by Phase 151 visual editor to validate on every canvas change.
    Expected response: HTTP 200 with {valid: true} or {valid: false, errors: [...]}
    """
    # Arrange: valid workflow payload
    job_id = str(uuid4())
    request_payload = {
        "name": f"validate-test-{uuid4().hex[:8]}",
        "steps": [
            {"node_type": "SCRIPT", "scheduled_job_id": job_id}
        ],
        "edges": [],
        "parameters": []
    }

    # Act: validate workflow
    response = await async_client.post("/api/workflows/validate", json=request_payload, headers=auth_headers)

    # Assert: HTTP 200 with valid: true
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["valid"] == True


@pytest.mark.asyncio
async def test_validate_workflow_with_cycle(async_client, auth_headers):
    """Bonus: Validate detects cycles without saving.

    Verifies that POST /api/workflows/validate catches cycle errors.
    Expected response: HTTP 200 with {valid: false, error: CYCLE_DETECTED, cycle_path: [...]}
    """
    # Arrange: workflow with cycle using temp_step_* IDs (same as API generates)
    step_ids = ["temp_step_0", "temp_step_1", "temp_step_2"]
    job_ids = [str(uuid4()) for _ in range(3)]
    request_payload = {
        "name": f"validate-cycle-test-{uuid4().hex[:8]}",
        "steps": [
            {"node_type": "SCRIPT", "scheduled_job_id": job_ids[i]}
            for i in range(3)
        ],
        "edges": [
            {"from_step_id": step_ids[0], "to_step_id": step_ids[1]},
            {"from_step_id": step_ids[1], "to_step_id": step_ids[2]},
            {"from_step_id": step_ids[2], "to_step_id": step_ids[0]}  # Cycle back
        ]
    }

    # Act: validate workflow with cycle
    response = await async_client.post("/api/workflows/validate", json=request_payload, headers=auth_headers)

    # Assert: HTTP 200 with valid: false and error: CYCLE_DETECTED
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["valid"] == False
    assert data["error"] == "CYCLE_DETECTED"
    assert "cycle_path" in data
    assert isinstance(data["cycle_path"], list)
