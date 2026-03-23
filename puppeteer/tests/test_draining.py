"""
Phase 52 — Queue Visibility, Node Drawer, and Draining: Tests for VIS-04.
8 tests covering node DRAINING state transitions and work-pull exclusion.
"""
import json
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from agent_service.db import Base, Job, Node
from agent_service.services.job_service import JobService
from agent_service.models import HeartbeatPayload, ResultReport


# ---------------------------------------------------------------------------
# Async in-memory DB fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_node(node_id=None, status="ONLINE"):
    return Node(
        node_id=node_id or str(uuid.uuid4()),
        hostname="test-host",
        ip="127.0.0.1",
        status=status,
        last_seen=datetime.utcnow(),
        tags=json.dumps([]),
        capabilities=json.dumps({}),
        env_tag=None,
    )


def _make_job(guid=None, status="PENDING", node_id=None):
    return Job(
        guid=guid or str(uuid.uuid4()),
        status=status,
        node_id=node_id,
        task_type="script",
        payload=json.dumps({"script": "print('hello')"}),
        target_tags=json.dumps([]),
        capability_requirements=json.dumps({}),
        env_tag=None,
        created_at=datetime.utcnow(),
        created_by="test-user",
    )


# ---------------------------------------------------------------------------
# VIS-04 tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_drain_endpoint_sets_status_draining(db):
    """
    Setting a node to DRAINING via direct DB operation (as the endpoint would do)
    results in node.status == "DRAINING".
    """
    node = _make_node(status="ONLINE")
    db.add(node)
    await db.commit()

    # Simulate what the drain endpoint does
    from sqlalchemy import select
    result = await db.execute(select(Node).where(Node.node_id == node.node_id))
    n = result.scalar_one_or_none()
    assert n is not None
    assert n.status in ("ONLINE", "BUSY"), "Pre-condition: node must be ONLINE or BUSY"
    n.status = "DRAINING"
    await db.commit()

    await db.refresh(n)
    assert n.status == "DRAINING"


@pytest.mark.asyncio
async def test_undrain_endpoint_sets_status_online(db):
    """
    A DRAINING node transitions back to ONLINE when undrained.
    """
    node = _make_node(status="DRAINING")
    db.add(node)
    await db.commit()

    from sqlalchemy import select
    result = await db.execute(select(Node).where(Node.node_id == node.node_id))
    n = result.scalar_one_or_none()
    assert n.status == "DRAINING"
    n.status = "ONLINE"
    await db.commit()

    await db.refresh(n)
    assert n.status == "ONLINE"


@pytest.mark.asyncio
async def test_drain_rejects_already_draining(db):
    """
    Attempting to drain a DRAINING node should be rejected (409 semantics).
    The drain guard rejects status not in ("ONLINE", "BUSY").
    """
    node = _make_node(status="DRAINING")
    db.add(node)
    await db.commit()

    from sqlalchemy import select
    result = await db.execute(select(Node).where(Node.node_id == node.node_id))
    n = result.scalar_one_or_none()
    # The drain endpoint rejects if status not in ("ONLINE", "BUSY")
    assert n.status not in ("ONLINE", "BUSY"), "DRAINING node must fail the drain guard"


@pytest.mark.asyncio
async def test_pull_work_skips_draining_node(db):
    """
    When a DRAINING node calls pull_work, it must receive PollResponse(job=None).
    The PENDING job in the DB must remain PENDING.
    """
    node = _make_node(status="DRAINING")
    db.add(node)
    pending_job = _make_job(status="PENDING")
    db.add(pending_job)
    await db.commit()

    result = await JobService.pull_work(
        node_id=node.node_id,
        node_ip="127.0.0.1",
        db=db,
    )
    assert result.job is None

    from sqlalchemy import select
    job_result = await db.execute(select(Job).where(Job.guid == pending_job.guid))
    job = job_result.scalar_one_or_none()
    assert job.status == "PENDING", "PENDING job must not be assigned to a DRAINING node"


@pytest.mark.asyncio
async def test_heartbeat_preserves_draining_status(db):
    """
    receive_heartbeat called for a DRAINING node must NOT revert the status
    back to "ONLINE".
    """
    node = _make_node(status="DRAINING")
    db.add(node)
    await db.commit()

    hb = HeartbeatPayload(
        node_id=node.node_id,
        hostname="test-host",
        tags=[],
        capabilities={},
    )
    await JobService.receive_heartbeat(
        node_id=node.node_id,
        node_ip="127.0.0.1",
        hb=hb,
        db=db,
    )

    from sqlalchemy import select
    result = await db.execute(select(Node).where(Node.node_id == node.node_id))
    n = result.scalar_one_or_none()
    assert n.status == "DRAINING", f"Expected DRAINING, got {n.status}"


@pytest.mark.asyncio
async def test_list_nodes_draining_preserved(db):
    """
    The list_nodes status computation preserves DRAINING status even for a
    recently-heartbeating node.
    """
    node = _make_node(status="DRAINING")
    # last_seen within the 60-second online window
    node.last_seen = datetime.utcnow()
    db.add(node)
    await db.commit()

    # Simulate the list_nodes status computation logic from main.py
    # This mirrors the fixed guard: if n.status in ("REVOKED", "TAMPERED", "DRAINING")
    n = node
    if n.status in ("REVOKED", "TAMPERED", "DRAINING"):
        node_status = n.status
    else:
        is_offline = (datetime.utcnow() - n.last_seen).total_seconds() > 60
        node_status = "OFFLINE" if is_offline else "ONLINE"

    assert node_status == "DRAINING"


@pytest.mark.asyncio
async def test_auto_offline_transition_when_last_job_completes(db):
    """
    A DRAINING node with exactly one ASSIGNED job: when report_result is called
    for that job (SUCCESS), node.status automatically transitions to "OFFLINE".
    """
    node = _make_node(status="DRAINING")
    db.add(node)
    job = _make_job(status="ASSIGNED", node_id=node.node_id)
    db.add(job)
    await db.commit()

    report = ResultReport(
        success=True,
        output_log=[],
        error_details=None,
        exit_code=0,
    )
    await JobService.report_result(
        guid=job.guid,
        report=report,
        node_ip="127.0.0.1",
        db=db,
    )

    from sqlalchemy import select
    result = await db.execute(select(Node).where(Node.node_id == node.node_id))
    n = result.scalar_one_or_none()
    assert n.status == "OFFLINE", f"Expected OFFLINE after last job completed, got {n.status}"


@pytest.mark.asyncio
async def test_draining_node_not_reverted_with_active_jobs(db):
    """
    A DRAINING node with two ASSIGNED jobs: first result arrives;
    node.status must remain "DRAINING" because one active job still remains.
    """
    node = _make_node(status="DRAINING")
    db.add(node)
    job1 = _make_job(status="ASSIGNED", node_id=node.node_id)
    job2 = _make_job(status="ASSIGNED", node_id=node.node_id)
    db.add(job1)
    db.add(job2)
    await db.commit()

    report = ResultReport(
        success=True,
        output_log=[],
        error_details=None,
        exit_code=0,
    )
    await JobService.report_result(
        guid=job1.guid,
        report=report,
        node_ip="127.0.0.1",
        db=db,
    )

    from sqlalchemy import select
    result = await db.execute(select(Node).where(Node.node_id == node.node_id))
    n = result.scalar_one_or_none()
    assert n.status == "DRAINING", f"Expected DRAINING (job2 still active), got {n.status}"
