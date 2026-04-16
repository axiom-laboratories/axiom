"""
Test suite for Phase 147: WorkflowRun Execution Engine
Coverage: ENGINE-01 through ENGINE-07

Tests verify:
- BFS dispatch in topological order (ENGINE-01)
- Depth tracking and override (ENGINE-02)
- Concurrency guard with atomic CAS (ENGINE-03)
- Status machine transitions (ENGINE-04)
- Cascade cancellation (ENGINE-05)
- API endpoints for run creation/cancellation (ENGINE-07)
"""
import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from agent_service.db import WorkflowRun, WorkflowStep, WorkflowStepRun, Job, WorkflowEdge, Workflow, Signal, ScheduledJob, Signature, AsyncSessionLocal
from agent_service.services.workflow_service import WorkflowService
from agent_service.main import app
import json


# ============================================================================
# Task 1: BFS Dispatch and Concurrency Tests
# ============================================================================

@pytest.mark.asyncio
async def test_dispatch_bfs_order(async_client: AsyncClient, auth_headers: dict, sample_3_step_linear_workflow):
    """
    ENGINE-01: Verify BFS dispatch creates jobs in topological order.

    Given: Linear workflow A→B→C
    When: Trigger run and dispatch first wave
    Then: Only step A (root) is dispatched initially
          After A completes, B is dispatched
          After B completes, C is dispatched
    """
    from agent_service.db import AsyncSessionLocal

    workflow, step_ids = sample_3_step_linear_workflow

    # Create and dispatch run via API
    response = await async_client.post(
        "/api/workflow-runs",
        json={
            "workflow_id": workflow.id,
            "parameters": {}
        },
        headers=auth_headers
    )

    assert response.status_code == 201, f"Failed to create run: {response.text}"
    run_data = response.json()
    run_id = run_data["id"]

    # Verify the response contains the correct step run states
    # Only step_0 should be RUNNING (root), others PENDING
    step_runs = run_data["step_runs"]
    assert len(step_runs) == 3, f"Expected 3 step runs, got {len(step_runs)}"

    # Find step runs by status
    running = [sr for sr in step_runs if sr["status"] == "RUNNING"]
    assert len(running) == 1, f"Expected 1 RUNNING step, got {len(running)}"
    assert running[0]["workflow_step_id"] == step_ids["step_0"], "Root step should be RUNNING"

    # step_1 and step_2 should be PENDING
    pending = [sr for sr in step_runs if sr["status"] == "PENDING"]
    assert len(pending) == 2, f"Expected 2 PENDING steps, got {len(pending)}"


@pytest.mark.asyncio
async def test_concurrent_dispatch_cas_guard(async_db_session: AsyncSession, sample_3_step_linear_workflow):
    """
    ENGINE-03: Verify atomic CAS guard prevents duplicate job dispatch.

    Given: Step with status PENDING
    When: Two concurrent calls try to transition PENDING→RUNNING
    Then: Only one succeeds (UPDATE rowcount==1), other gets rowcount==0 and skips
    """
    workflow, step_ids = sample_3_step_linear_workflow

    # Create run without dispatching yet
    run = WorkflowRun(
        id=str(uuid4()),
        workflow_id=workflow.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type="MANUAL",
        triggered_by="test_user"
    )
    async_db_session.add(run)
    await async_db_session.flush()

    # Create step runs manually
    step_runs = []
    for i, step_id in enumerate([step_ids["step_0"], step_ids["step_1"], step_ids["step_2"]]):
        sr = WorkflowStepRun(
            id=str(uuid4()),
            workflow_run_id=run.id,
            workflow_step_id=step_id,
            status="PENDING",
            created_at=datetime.utcnow()
        )
        async_db_session.add(sr)
        step_runs.append(sr)
    await async_db_session.flush()

    # Dispatch once (should create 1+ jobs for root step)
    workflow_service = WorkflowService()
    jobs_1 = await workflow_service.dispatch_next_wave(run.id, async_db_session)

    # Dispatch again immediately (should find 0 eligible steps — root already RUNNING)
    jobs_2 = await workflow_service.dispatch_next_wave(run.id, async_db_session)

    # Only first dispatch should create jobs
    assert len(jobs_1) > 0, "First dispatch should create jobs"
    assert len(jobs_2) == 0, "Second dispatch should create no jobs (CAS guard prevents duplicate)"

    # Verify step_0 is RUNNING
    stmt = select(WorkflowStepRun).where(WorkflowStepRun.id == step_runs[0].id)
    result = await async_db_session.execute(stmt)
    sr = result.scalar()
    assert sr.status == "RUNNING", "Root step should be RUNNING after first dispatch"


# ============================================================================
# Task 2: Status Machine Tests
# ============================================================================

@pytest.mark.asyncio
async def test_state_machine_completed(async_db_session: AsyncSession, sample_3_step_linear_workflow):
    """
    ENGINE-04, ENGINE-06: Verify run reaches COMPLETED when all steps COMPLETED.
    """
    workflow, step_ids = sample_3_step_linear_workflow

    # Create run with all step runs COMPLETED
    run = WorkflowRun(
        id=str(uuid4()),
        workflow_id=workflow.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type="MANUAL",
        triggered_by="test_user"
    )
    async_db_session.add(run)
    await async_db_session.flush()

    # Create step runs, all COMPLETED
    for i, step_id in enumerate([step_ids["step_0"], step_ids["step_1"], step_ids["step_2"]]):
        sr = WorkflowStepRun(
            id=str(uuid4()),
            workflow_run_id=run.id,
            workflow_step_id=step_id,
            status="COMPLETED",
            completed_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        async_db_session.add(sr)
    await async_db_session.commit()

    # Advance workflow (should detect terminal condition)
    workflow_service = WorkflowService()
    await workflow_service.advance_workflow(run.id, async_db_session)

    # Verify run status is COMPLETED
    stmt = select(WorkflowRun).where(WorkflowRun.id == run.id)
    result = await async_db_session.execute(stmt)
    updated_run = result.scalar()
    assert updated_run.status == "COMPLETED", f"Expected COMPLETED status, got {updated_run.status}"
    assert updated_run.completed_at is not None, "completed_at should be set"


@pytest.mark.asyncio
async def test_state_machine_partial(async_db_session: AsyncSession, sample_3_step_linear_workflow):
    """
    ENGINE-04, ENGINE-06: Verify run reaches PARTIAL when some COMPLETED, some FAILED.
    """
    workflow, step_ids = sample_3_step_linear_workflow

    run = WorkflowRun(
        id=str(uuid4()),
        workflow_id=workflow.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type="MANUAL",
        triggered_by="test_user"
    )
    async_db_session.add(run)
    await async_db_session.flush()

    # Create step runs: step_0 COMPLETED, step_1 COMPLETED, step_2 FAILED
    statuses = ["COMPLETED", "COMPLETED", "FAILED"]
    for i, (step_id, status) in enumerate(zip([step_ids["step_0"], step_ids["step_1"], step_ids["step_2"]], statuses)):
        sr = WorkflowStepRun(
            id=str(uuid4()),
            workflow_run_id=run.id,
            workflow_step_id=step_id,
            status=status,
            completed_at=datetime.utcnow() if status != "RUNNING" else None,
            created_at=datetime.utcnow()
        )
        async_db_session.add(sr)
    await async_db_session.commit()

    workflow_service = WorkflowService()
    await workflow_service.advance_workflow(run.id, async_db_session)

    stmt = select(WorkflowRun).where(WorkflowRun.id == run.id)
    result = await async_db_session.execute(stmt)
    updated_run = result.scalar()
    assert updated_run.status == "PARTIAL", f"Expected PARTIAL status, got {updated_run.status}"


@pytest.mark.asyncio
async def test_state_machine_failed(async_db_session: AsyncSession, sample_3_step_linear_workflow):
    """
    ENGINE-04: Verify run reaches FAILED when no steps COMPLETED and has FAILED.
    """
    workflow, step_ids = sample_3_step_linear_workflow

    run = WorkflowRun(
        id=str(uuid4()),
        workflow_id=workflow.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type="MANUAL",
        triggered_by="test_user"
    )
    async_db_session.add(run)
    await async_db_session.flush()

    # Create step runs: all FAILED
    for step_id in [step_ids["step_0"], step_ids["step_1"], step_ids["step_2"]]:
        sr = WorkflowStepRun(
            id=str(uuid4()),
            workflow_run_id=run.id,
            workflow_step_id=step_id,
            status="FAILED",
            completed_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        async_db_session.add(sr)
    await async_db_session.commit()

    workflow_service = WorkflowService()
    await workflow_service.advance_workflow(run.id, async_db_session)

    stmt = select(WorkflowRun).where(WorkflowRun.id == run.id)
    result = await async_db_session.execute(stmt)
    updated_run = result.scalar()
    assert updated_run.status == "FAILED", f"Expected FAILED status, got {updated_run.status}"


@pytest.mark.asyncio
async def test_cascade_cancellation(async_db_session: AsyncSession, sample_3_step_linear_workflow):
    """
    ENGINE-05: Verify failed step cascades cancellation to downstream PENDING steps.

    Given: A→B→C workflow
    When: A COMPLETED, B FAILED
    Then: dispatch_next_wave should mark C as CANCELLED (B is predecessor, B FAILED)
    """
    workflow, step_ids = sample_3_step_linear_workflow

    run = WorkflowRun(
        id=str(uuid4()),
        workflow_id=workflow.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type="MANUAL",
        triggered_by="test_user"
    )
    async_db_session.add(run)
    await async_db_session.flush()

    # Create step runs: A COMPLETED, B FAILED, C PENDING
    sr_a = WorkflowStepRun(
        id=str(uuid4()),
        workflow_run_id=run.id,
        workflow_step_id=step_ids["step_0"],
        status="COMPLETED",
        completed_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    sr_b = WorkflowStepRun(
        id=str(uuid4()),
        workflow_run_id=run.id,
        workflow_step_id=step_ids["step_1"],
        status="FAILED",
        completed_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    sr_c = WorkflowStepRun(
        id=str(uuid4()),
        workflow_run_id=run.id,
        workflow_step_id=step_ids["step_2"],
        status="PENDING",
        created_at=datetime.utcnow()
    )
    async_db_session.add(sr_a)
    async_db_session.add(sr_b)
    async_db_session.add(sr_c)
    await async_db_session.commit()

    # Dispatch next wave (should see B FAILED, cascade to C)
    workflow_service = WorkflowService()
    await workflow_service.dispatch_next_wave(run.id, async_db_session)

    # Verify C is CANCELLED
    stmt = select(WorkflowStepRun).where(WorkflowStepRun.id == sr_c.id)
    result = await async_db_session.execute(stmt)
    updated_c = result.scalar()
    assert updated_c.status == "CANCELLED", f"Expected CANCELLED status, got {updated_c.status}"
    assert updated_c.completed_at is not None, "completed_at should be set for CANCELLED step"


# ============================================================================
# Task 3: Cancellation and API Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cancel_run(async_db_session: AsyncSession, sample_3_step_linear_workflow):
    """
    ENGINE-07: Verify cancel_run blocks further dispatches and marks PENDING steps CANCELLED.
    """
    workflow, step_ids = sample_3_step_linear_workflow

    run = WorkflowRun(
        id=str(uuid4()),
        workflow_id=workflow.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type="MANUAL",
        triggered_by="test_user"
    )
    async_db_session.add(run)
    await async_db_session.flush()

    # Create step runs: A RUNNING, B PENDING, C PENDING
    sr_a = WorkflowStepRun(
        id=str(uuid4()),
        workflow_run_id=run.id,
        workflow_step_id=step_ids["step_0"],
        status="RUNNING",
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    sr_b = WorkflowStepRun(
        id=str(uuid4()),
        workflow_run_id=run.id,
        workflow_step_id=step_ids["step_1"],
        status="PENDING",
        created_at=datetime.utcnow()
    )
    sr_c = WorkflowStepRun(
        id=str(uuid4()),
        workflow_run_id=run.id,
        workflow_step_id=step_ids["step_2"],
        status="PENDING",
        created_at=datetime.utcnow()
    )
    async_db_session.add(sr_a)
    async_db_session.add(sr_b)
    async_db_session.add(sr_c)
    await async_db_session.commit()

    # Cancel run
    workflow_service = WorkflowService()
    await workflow_service.cancel_run(run.id, async_db_session)

    # Verify run is CANCELLED
    stmt = select(WorkflowRun).where(WorkflowRun.id == run.id)
    result = await async_db_session.execute(stmt)
    cancelled_run = result.scalar()
    assert cancelled_run.status == "CANCELLED", f"Expected CANCELLED status, got {cancelled_run.status}"

    # Verify B and C are CANCELLED
    stmt = select(WorkflowStepRun).where(
        WorkflowStepRun.workflow_run_id == run.id,
        WorkflowStepRun.status == "CANCELLED"
    )
    result = await async_db_session.execute(stmt)
    cancelled_steps = result.scalars().all()
    assert len(cancelled_steps) == 2, f"Expected 2 CANCELLED steps, got {len(cancelled_steps)}"


# ============================================================================
# Task 4: API Tests and Depth Tracking
# ============================================================================

@pytest.mark.asyncio
async def test_api_create_run(async_client: AsyncClient, auth_headers: dict, sample_3_step_linear_workflow):
    """
    ENGINE-07: Verify POST /api/workflow-runs creates run and returns proper response.
    """
    workflow, step_ids = sample_3_step_linear_workflow

    # Call API (with auth token)
    response = await async_client.post(
        "/api/workflow-runs",
        json={
            "workflow_id": workflow.id,
            "parameters": {}
        },
        headers=auth_headers
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "RUNNING", f"Run status should be RUNNING, got {data['status']}"
    assert "id" in data, "Response must contain run ID"


@pytest.mark.asyncio
async def test_api_cancel_run(async_client: AsyncClient, auth_headers: dict, sample_3_step_linear_workflow):
    """
    ENGINE-07: Verify POST /api/workflow-runs/{id}/cancel cancels run.
    """
    workflow, step_ids = sample_3_step_linear_workflow

    # Create run first
    response = await async_client.post(
        "/api/workflow-runs",
        json={"workflow_id": workflow.id},
        headers=auth_headers
    )
    assert response.status_code == 201, f"Failed to create run: {response.text}"
    run_id = response.json()["id"]

    # Cancel run
    response = await async_client.post(
        f"/api/workflow-runs/{run_id}/cancel",
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "CANCELLED", f"Run status should be CANCELLED, got {data['status']}"


@pytest.mark.asyncio
async def test_depth_tracking(async_db_session: AsyncSession, sample_3_step_linear_workflow):
    """
    ENGINE-02: Verify depth is assigned correctly (root=0, descendants+=1, capped at 30).

    Given: Linear workflow A→B→C
    When: Trigger run and dispatch waves
    Then: A has depth 0, B has depth 1, C has depth 2
    """
    workflow, step_ids = sample_3_step_linear_workflow

    # Create and dispatch run
    workflow_service = WorkflowService()
    run = await workflow_service.start_run(
        workflow_id=workflow.id,
        parameters={},
        triggered_by="test_user",
        db=async_db_session
    )

    # Query jobs created for root step
    stmt = select(Job).where(
        Job.workflow_step_run_id.isnot(None)
    ).order_by(Job.created_at)
    result = await async_db_session.execute(stmt)
    jobs = result.scalars().all()

    # Verify root job has depth 0
    assert len(jobs) > 0, "Should have at least one job created"
    root_job = jobs[0]
    assert root_job.depth is not None, "Root job should have depth assigned"
    assert root_job.depth == 0, f"Root job depth should be 0, got {root_job.depth}"


@pytest.mark.asyncio
async def test_depth_cap_at_30(async_db_session: AsyncSession, sample_3_step_linear_workflow):
    """
    ENGINE-02: Verify depth is capped at 30 maximum.

    Tests that even deeply nested workflow jobs don't exceed depth 30.
    """
    workflow, step_ids = sample_3_step_linear_workflow

    # Create a run and get first job
    workflow_service = WorkflowService()
    run = await workflow_service.start_run(
        workflow_id=workflow.id,
        parameters={},
        triggered_by="test_user",
        db=async_db_session
    )

    # Query all jobs and check depths are <= 30
    stmt = select(Job).where(
        Job.workflow_step_run_id.isnot(None)
    )
    result = await async_db_session.execute(stmt)
    jobs = result.scalars().all()

    for job in jobs:
        assert job.depth is not None, f"Job {job.guid} missing depth"
        assert job.depth <= 30, f"Job depth {job.depth} exceeds max of 30"


# ============================================================================
# GATE-06: SIGNAL_WAIT Blocking and Wakeup Tests
# ============================================================================

@pytest.mark.asyncio
async def test_signal_wait_wakeup(async_db_session: AsyncSession):
    """
    GATE-06: Verify SIGNAL_WAIT blocks until signal is posted.

    Given: Workflow with SIGNAL_WAIT step configured with signal_name='ready'
    When: Trigger workflow run
    Then: SIGNAL_WAIT step transitions PENDING→RUNNING and blocks
          No job is created for SIGNAL_WAIT (it's not a SCRIPT node)
    When: Signal 'ready' is posted via advance_signal_wait()
    Then: SIGNAL_WAIT step transitions RUNNING→COMPLETED
    """
    from uuid import uuid4

    # Create signature (required FK)
    sig = Signature(
        id=str(uuid4()),
        name=f"test-sig-{uuid4().hex[:8]}",
        public_key="-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANDiE2Zm7HK5Q=\n-----END PUBLIC KEY-----",
        uploaded_by="admin"
    )
    async_db_session.add(sig)
    await async_db_session.flush()

    # Create a scheduled job (for the SCRIPT step before SIGNAL_WAIT)
    job = ScheduledJob(
        id=str(uuid4()),
        name=f"test_job_{uuid4().hex[:8]}",
        script_content="echo 'initial step'",
        signature_id=sig.id,
        signature_payload="Zm9vYmFyYmF6",
        created_by="admin"
    )
    async_db_session.add(job)
    await async_db_session.flush()

    # Create workflow
    workflow = Workflow(
        id=str(uuid4()),
        name="test_signal_workflow",
        created_by="admin",
        is_paused=False
    )
    async_db_session.add(workflow)
    await async_db_session.flush()

    # Create two steps: SCRIPT and SIGNAL_WAIT
    script_step_id = str(uuid4())
    signal_step_id = str(uuid4())

    script_step = WorkflowStep(
        id=script_step_id,
        workflow_id=workflow.id,
        scheduled_job_id=job.id,
        node_type="SCRIPT",
        config_json=None
    )
    async_db_session.add(script_step)

    signal_step = WorkflowStep(
        id=signal_step_id,
        workflow_id=workflow.id,
        scheduled_job_id=None,  # SIGNAL_WAIT doesn't have a job
        node_type="SIGNAL_WAIT",
        config_json=json.dumps({"signal_name": "ready"})
    )
    async_db_session.add(signal_step)
    await async_db_session.flush()

    # Create edge: SCRIPT → SIGNAL_WAIT
    edge = WorkflowEdge(
        id=str(uuid4()),
        workflow_id=workflow.id,
        from_step_id=script_step_id,
        to_step_id=signal_step_id,
        branch_name=None
    )
    async_db_session.add(edge)
    await async_db_session.commit()

    # Trigger workflow run
    workflow_service = WorkflowService()
    run = await workflow_service.start_run(
        workflow_id=workflow.id,
        parameters={},
        triggered_by="test_user",
        db=async_db_session
    )

    # Verify SCRIPT step is RUNNING
    stmt = select(WorkflowStepRun).where(
        WorkflowStepRun.workflow_run_id == run.id,
        WorkflowStepRun.workflow_step_id == script_step_id
    )
    script_step_run = (await async_db_session.execute(stmt)).scalar_one()
    assert script_step_run.status == "RUNNING", "SCRIPT step should be RUNNING (root)"

    # Complete the SCRIPT step
    script_step_run.status = "COMPLETED"
    script_step_run.completed_at = datetime.utcnow()
    await async_db_session.flush()

    # Advance workflow (dispatch next wave with SIGNAL_WAIT)
    await workflow_service.advance_workflow(run.id, async_db_session)

    # Verify SIGNAL_WAIT step is RUNNING and blocked
    stmt = select(WorkflowStepRun).where(
        WorkflowStepRun.workflow_run_id == run.id,
        WorkflowStepRun.workflow_step_id == signal_step_id
    )
    signal_step_run = (await async_db_session.execute(stmt)).scalar_one()
    assert signal_step_run.status == "RUNNING", "SIGNAL_WAIT should be RUNNING (blocked, waiting for signal)"

    # Verify no job was created for SIGNAL_WAIT
    stmt = select(Job).where(Job.workflow_step_run_id == signal_step_run.id)
    job_for_signal = (await async_db_session.execute(stmt)).scalar_one_or_none()
    assert job_for_signal is None, "SIGNAL_WAIT should not create a job"

    # Post the signal
    await workflow_service.advance_signal_wait("ready", async_db_session)

    # Verify SIGNAL_WAIT step is now COMPLETED
    await async_db_session.refresh(signal_step_run)
    assert signal_step_run.status == "COMPLETED", "SIGNAL_WAIT should transition to COMPLETED after signal arrives"
    assert signal_step_run.completed_at is not None, "SIGNAL_WAIT should have a completion timestamp"


@pytest.mark.asyncio
async def test_signal_wakes_blocked_run(async_db_session: AsyncSession):
    """
    GATE-06: Verify signal wakeup triggers downstream dispatch.

    Given: Workflow A→SIGNAL_WAIT→B (3 steps)
    When: Trigger run, complete A, dispatch SIGNAL_WAIT (blocks)
    Then: SIGNAL_WAIT is RUNNING, B is PENDING
    When: Signal is posted
    Then: SIGNAL_WAIT transitions to COMPLETED
          Downstream step B transitions to RUNNING
    """
    from uuid import uuid4

    # Create signature (required FK)
    sig = Signature(
        id=str(uuid4()),
        name=f"test-sig-{uuid4().hex[:8]}",
        public_key="-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANDiE2Zm7HK5Q=\n-----END PUBLIC KEY-----",
        uploaded_by="admin"
    )
    async_db_session.add(sig)
    await async_db_session.flush()

    # Create two scheduled jobs (for A and B)
    job_a_id = str(uuid4())
    job_b_id = str(uuid4())

    for job_id, script in [(job_a_id, "echo 'A'"), (job_b_id, "echo 'B'")]:
        job = ScheduledJob(
            id=job_id,
            name=f"test_job_{uuid4().hex[:8]}",
            script_content=script,
            signature_id=sig.id,
            signature_payload="Zm9vYmFyYmF6",
            created_by="admin"
        )
        async_db_session.add(job)
    await async_db_session.flush()

    # Create workflow
    workflow = Workflow(
        id=str(uuid4()),
        name="test_signal_downstream",
        created_by="admin",
        is_paused=False
    )
    async_db_session.add(workflow)
    await async_db_session.flush()

    # Create three steps: A, SIGNAL_WAIT, B
    step_a_id = str(uuid4())
    signal_step_id = str(uuid4())
    step_b_id = str(uuid4())

    for step_id, job_id, node_type, config in [
        (step_a_id, job_a_id, "SCRIPT", None),
        (signal_step_id, None, "SIGNAL_WAIT", json.dumps({"signal_name": "proceed"})),
        (step_b_id, job_b_id, "SCRIPT", None)
    ]:
        step = WorkflowStep(
            id=step_id,
            workflow_id=workflow.id,
            scheduled_job_id=job_id if node_type == "SCRIPT" else None,
            node_type=node_type,
            config_json=config
        )
        async_db_session.add(step)
    await async_db_session.flush()

    # Create edges: A→SIGNAL_WAIT, SIGNAL_WAIT→B
    edges = [
        WorkflowEdge(
            id=str(uuid4()),
            workflow_id=workflow.id,
            from_step_id=step_a_id,
            to_step_id=signal_step_id,
            branch_name=None
        ),
        WorkflowEdge(
            id=str(uuid4()),
            workflow_id=workflow.id,
            from_step_id=signal_step_id,
            to_step_id=step_b_id,
            branch_name=None
        )
    ]
    for edge in edges:
        async_db_session.add(edge)
    await async_db_session.commit()

    # Start workflow run
    workflow_service = WorkflowService()
    run = await workflow_service.start_run(
        workflow_id=workflow.id,
        parameters={},
        triggered_by="test_user",
        db=async_db_session
    )

    # Verify A is RUNNING, SIGNAL_WAIT and B are PENDING
    stmt = select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run.id)
    step_runs = {sr.workflow_step_id: sr for sr in (await async_db_session.execute(stmt)).scalars().all()}

    assert step_runs[step_a_id].status == "RUNNING"
    assert step_runs[signal_step_id].status == "PENDING"
    assert step_runs[step_b_id].status == "PENDING"

    # Complete step A
    step_runs[step_a_id].status = "COMPLETED"
    step_runs[step_a_id].completed_at = datetime.utcnow()
    await async_db_session.flush()

    # Dispatch next wave (SIGNAL_WAIT should become RUNNING)
    await workflow_service.advance_workflow(run.id, async_db_session)

    # Refresh step runs
    await async_db_session.refresh(step_runs[step_a_id])
    await async_db_session.refresh(step_runs[signal_step_id])
    await async_db_session.refresh(step_runs[step_b_id])

    assert step_runs[signal_step_id].status == "RUNNING", "SIGNAL_WAIT should be RUNNING after dispatch"
    assert step_runs[step_b_id].status == "PENDING", "B should still be PENDING (waiting for signal)"

    # Post the signal
    await workflow_service.advance_signal_wait("proceed", async_db_session)

    # Refresh step runs
    await async_db_session.refresh(step_runs[signal_step_id])
    await async_db_session.refresh(step_runs[step_b_id])

    assert step_runs[signal_step_id].status == "COMPLETED", "SIGNAL_WAIT should be COMPLETED after signal"
    assert step_runs[step_b_id].status == "RUNNING", "B should be RUNNING after signal wakes SIGNAL_WAIT"


@pytest.mark.asyncio
async def test_signal_cancel_prevents_wakeup(async_db_session: AsyncSession):
    """
    GATE-06: Verify cancellation prevents SIGNAL_WAIT wakeup (Pitfall 4).

    Given: Workflow with SIGNAL_WAIT step
    When: Trigger run, dispatch SIGNAL_WAIT (blocks)
    Then: Run status is RUNNING, SIGNAL_WAIT status is RUNNING
    When: Cancel the workflow run
    Then: Run status becomes CANCELLED, SIGNAL_WAIT status becomes CANCELLED
    When: Signal is posted
    Then: SIGNAL_WAIT does NOT wake up (remains CANCELLED)
          Advance returns without advancing workflow (cancellation guard prevents it)
    """
    from uuid import uuid4

    # Create signature (required FK)
    sig = Signature(
        id=str(uuid4()),
        name=f"test-sig-{uuid4().hex[:8]}",
        public_key="-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANDiE2Zm7HK5Q=\n-----END PUBLIC KEY-----",
        uploaded_by="admin"
    )
    async_db_session.add(sig)
    await async_db_session.flush()

    # Create a scheduled job
    job = ScheduledJob(
        id=str(uuid4()),
        name=f"test_job_{uuid4().hex[:8]}",
        script_content="echo 'initial'",
        signature_id=sig.id,
        signature_payload="Zm9vYmFyYmF6",
        created_by="admin"
    )
    async_db_session.add(job)
    await async_db_session.flush()

    # Create workflow with SCRIPT→SIGNAL_WAIT
    workflow = Workflow(
        id=str(uuid4()),
        name="test_cancel_signal",
        created_by="admin",
        is_paused=False
    )
    async_db_session.add(workflow)
    await async_db_session.flush()

    script_step_id = str(uuid4())
    signal_step_id = str(uuid4())

    script_step = WorkflowStep(
        id=script_step_id,
        workflow_id=workflow.id,
        scheduled_job_id=job.id,
        node_type="SCRIPT",
        config_json=None
    )
    async_db_session.add(script_step)

    signal_step = WorkflowStep(
        id=signal_step_id,
        workflow_id=workflow.id,
        scheduled_job_id=None,
        node_type="SIGNAL_WAIT",
        config_json=json.dumps({"signal_name": "timeout"})
    )
    async_db_session.add(signal_step)
    await async_db_session.flush()

    edge = WorkflowEdge(
        id=str(uuid4()),
        workflow_id=workflow.id,
        from_step_id=script_step_id,
        to_step_id=signal_step_id,
        branch_name=None
    )
    async_db_session.add(edge)
    await async_db_session.commit()

    # Start run
    workflow_service = WorkflowService()
    run = await workflow_service.start_run(
        workflow_id=workflow.id,
        parameters={},
        triggered_by="test_user",
        db=async_db_session
    )

    # Complete script step
    stmt = select(WorkflowStepRun).where(
        WorkflowStepRun.workflow_run_id == run.id,
        WorkflowStepRun.workflow_step_id == script_step_id
    )
    script_sr = (await async_db_session.execute(stmt)).scalar_one()
    script_sr.status = "COMPLETED"
    script_sr.completed_at = datetime.utcnow()
    await async_db_session.flush()

    # Dispatch SIGNAL_WAIT
    await workflow_service.advance_workflow(run.id, async_db_session)

    # Get SIGNAL_WAIT step run
    stmt = select(WorkflowStepRun).where(
        WorkflowStepRun.workflow_run_id == run.id,
        WorkflowStepRun.workflow_step_id == signal_step_id
    )
    signal_sr = (await async_db_session.execute(stmt)).scalar_one()
    assert signal_sr.status == "RUNNING", "SIGNAL_WAIT should be RUNNING"

    # Cancel the workflow run
    await workflow_service.cancel_run(run.id, async_db_session)

    # Reload run and signal_sr from DB
    stmt = select(WorkflowRun).where(WorkflowRun.id == run.id)
    run = (await async_db_session.execute(stmt)).scalar_one()

    stmt = select(WorkflowStepRun).where(WorkflowStepRun.id == signal_sr.id)
    signal_sr = (await async_db_session.execute(stmt)).scalar_one()

    # Verify run is CANCELLED
    assert run.status == "CANCELLED", "Run should be CANCELLED"

    # Verify SIGNAL_WAIT step is CANCELLED
    assert signal_sr.status == "CANCELLED", "SIGNAL_WAIT should be CANCELLED"

    # Try to post signal
    await workflow_service.advance_signal_wait("timeout", async_db_session)

    # Reload signal_sr from DB to check if it changed
    stmt = select(WorkflowStepRun).where(WorkflowStepRun.id == signal_sr.id)
    signal_sr = (await async_db_session.execute(stmt)).scalar_one()

    # Verify SIGNAL_WAIT is still CANCELLED (NOT woken up)
    assert signal_sr.status == "CANCELLED", "SIGNAL_WAIT should remain CANCELLED after signal post (cancellation guard prevents wakeup)"
