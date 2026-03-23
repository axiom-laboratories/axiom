"""
Phase 52 — Queue Visibility, Node Drawer, and Draining: Tests for VIS-01.
6 tests covering dispatch diagnosis / pending job explanations.
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

def _make_node(node_id=None, status="ONLINE", capabilities=None, tags=None):
    return Node(
        node_id=node_id or str(uuid.uuid4()),
        hostname="test-host",
        ip="127.0.0.1",
        status=status,
        last_seen=datetime.utcnow(),
        tags=json.dumps(tags or []),
        capabilities=json.dumps(capabilities or {}),
        env_tag=None,
    )


def _make_job(guid=None, status="PENDING", node_id=None,
              target_tags=None, capability_requirements=None,
              created_at=None, target_node_id=None):
    return Job(
        guid=guid or str(uuid.uuid4()),
        status=status,
        node_id=node_id,
        task_type="script",
        payload=json.dumps({"script": "print('hello')"}),
        target_tags=json.dumps(target_tags or []),
        capability_requirements=json.dumps(capability_requirements or {}),
        env_tag=None,
        created_at=created_at or datetime.utcnow(),
        created_by="test-user",
        target_node_id=target_node_id,
    )


# ---------------------------------------------------------------------------
# VIS-01 tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_diagnosis_no_nodes_online(db):
    """No nodes exist; diagnosis returns reason=="no_nodes_online"."""
    job = _make_job(status="PENDING")
    db.add(job)
    await db.commit()

    result = await JobService.get_dispatch_diagnosis(job.guid, db)
    assert result["reason"] == "no_nodes_online"
    assert result["message"]


@pytest.mark.asyncio
async def test_diagnosis_capability_mismatch(db):
    """
    One ONLINE node, but job requires capability "gpu" >= "1.0" that node lacks.
    Result: reason=="capability_mismatch", message mentions "gpu".
    """
    node = _make_node(status="ONLINE", capabilities={"python": "3.11"})
    db.add(node)
    job = _make_job(status="PENDING", capability_requirements={"gpu": "1.0"})
    db.add(job)
    await db.commit()

    result = await JobService.get_dispatch_diagnosis(job.guid, db)
    assert result["reason"] == "capability_mismatch"
    assert "gpu" in result["message"]


@pytest.mark.asyncio
async def test_diagnosis_all_nodes_busy(db):
    """
    Two eligible nodes, both at concurrency limit (5 ASSIGNED jobs each).
    Result: reason=="all_nodes_busy", queue_position >= 1.
    """
    node1 = _make_node(status="ONLINE")
    node2 = _make_node(status="ONLINE")
    db.add(node1)
    db.add(node2)

    # Fill both nodes to capacity (5 each)
    for _ in range(5):
        db.add(_make_job(status="ASSIGNED", node_id=node1.node_id))
        db.add(_make_job(status="ASSIGNED", node_id=node2.node_id))

    job = _make_job(status="PENDING")
    db.add(job)
    await db.commit()

    result = await JobService.get_dispatch_diagnosis(job.guid, db)
    assert result["reason"] == "all_nodes_busy"
    assert isinstance(result["queue_position"], int)
    assert result["queue_position"] >= 1


@pytest.mark.asyncio
async def test_diagnosis_target_node_unavailable(db):
    """
    Job has explicit target_node_id pointing to an OFFLINE node.
    Result: reason=="target_node_unavailable".
    """
    offline_node = _make_node(status="OFFLINE")
    db.add(offline_node)
    job = _make_job(status="PENDING", target_node_id=offline_node.node_id)
    db.add(job)
    await db.commit()

    result = await JobService.get_dispatch_diagnosis(job.guid, db)
    assert result["reason"] == "target_node_unavailable"


@pytest.mark.asyncio
async def test_diagnosis_pending_dispatch(db):
    """
    Eligible ONLINE node with spare capacity exists.
    Result: reason=="pending_dispatch", non-empty message.
    """
    node = _make_node(status="ONLINE")
    db.add(node)
    job = _make_job(status="PENDING")
    db.add(job)
    await db.commit()

    result = await JobService.get_dispatch_diagnosis(job.guid, db)
    assert result["reason"] == "pending_dispatch"
    assert result["message"]


@pytest.mark.asyncio
async def test_diagnosis_queue_position_is_count_of_earlier_pending(db):
    """
    3 PENDING jobs created BEFORE this job; 2 created AFTER.
    All nodes at capacity.
    Result: queue_position == 4 (3 earlier jobs + 1 for the current job itself).
    """
    node = _make_node(status="BUSY")
    db.add(node)

    # Fill node to capacity
    for _ in range(5):
        db.add(_make_job(status="ASSIGNED", node_id=node.node_id))

    base_time = datetime.utcnow()

    # 3 PENDING jobs created BEFORE
    for i in range(3):
        db.add(_make_job(status="PENDING", created_at=base_time + timedelta(seconds=i)))

    # The target job
    target_job = _make_job(status="PENDING", created_at=base_time + timedelta(seconds=10))
    db.add(target_job)

    # 2 PENDING jobs created AFTER
    for i in range(2):
        db.add(_make_job(status="PENDING", created_at=base_time + timedelta(seconds=20 + i)))

    await db.commit()

    result = await JobService.get_dispatch_diagnosis(target_job.guid, db)
    assert result["reason"] == "all_nodes_busy"
    # queue_position = count of earlier PENDING/RETRYING + 1 = 3 + 1 = 4
    assert result["queue_position"] == 4
