"""
Phase 52 — Queue Visibility, Node Drawer, and Draining: Tests for VIS-03.
6 tests covering the node detail enrichment (running job, eligible pending
jobs, recent history, capabilities).
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
        env_tag="test",
    )


def _make_job(guid=None, status="PENDING", node_id=None,
              target_tags=None, created_at=None, completed_at=None,
              env_tag="test"):
    return Job(
        guid=guid or str(uuid.uuid4()),
        status=status,
        node_id=node_id,
        task_type="script",
        payload=json.dumps({"script": "print('hello')"}),
        target_tags=json.dumps(target_tags or []),
        capability_requirements=json.dumps({}),
        env_tag=env_tag,
        created_at=created_at or datetime.utcnow(),
        completed_at=completed_at,
        created_by="test-user",
    )


# ---------------------------------------------------------------------------
# VIS-03 tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_node_detail_running_job_present(db):
    """
    One ASSIGNED job exists for the node.

    Expected result:
        result["running_job"] is not None
        result["running_job"]["guid"] == job.guid
    """
    node = _make_node()
    db.add(node)
    job = _make_job(status="ASSIGNED", node_id=node.node_id)
    db.add(job)
    await db.commit()

    result = await JobService.get_node_detail(node_id=node.node_id, db=db)

    assert result is not None
    assert result["running_job"] is not None
    assert result["running_job"]["guid"] == job.guid


@pytest.mark.asyncio
async def test_node_detail_running_job_absent(db):
    """
    No ASSIGNED jobs exist for the node (node is idle).

    Expected result:
        result["running_job"] is None
    """
    node = _make_node()
    db.add(node)
    await db.commit()

    result = await JobService.get_node_detail(node_id=node.node_id, db=db)

    assert result is not None
    assert result["running_job"] is None


@pytest.mark.asyncio
async def test_node_detail_eligible_pending_jobs(db):
    """
    Two PENDING jobs have target_tags matching the node's tags; a third PENDING
    job has mismatched tags and must NOT appear in the result.

    Expected result:
        len(result["eligible_pending_jobs"]) == 2
        all guids in result["eligible_pending_jobs"] belong to the matching jobs
    """
    node = _make_node(tags=["worker"])
    db.add(node)

    job_a = _make_job(status="PENDING", target_tags=["worker"])
    job_b = _make_job(status="PENDING", target_tags=["worker"])
    job_mismatch = _make_job(status="PENDING", target_tags=["gpu-required"])
    db.add(job_a)
    db.add(job_b)
    db.add(job_mismatch)
    await db.commit()

    result = await JobService.get_node_detail(node_id=node.node_id, db=db)

    assert result is not None
    guids = {j["guid"] for j in result["eligible_pending_jobs"]}
    assert len(result["eligible_pending_jobs"]) == 2
    assert job_a.guid in guids
    assert job_b.guid in guids
    assert job_mismatch.guid not in guids


@pytest.mark.asyncio
async def test_node_detail_eligible_pending_jobs_capped_at_50(db):
    """
    55 eligible PENDING jobs exist for the node; the result must cap the list at 50.

    Expected result:
        len(result["eligible_pending_jobs"]) == 50
    """
    node = _make_node()
    db.add(node)

    for i in range(55):
        db.add(_make_job(status="PENDING"))
    await db.commit()

    result = await JobService.get_node_detail(node_id=node.node_id, db=db)

    assert result is not None
    assert len(result["eligible_pending_jobs"]) == 50


@pytest.mark.asyncio
async def test_node_detail_recent_history(db):
    """
    3 COMPLETED jobs ran on this node in the past 24 hours; 1 COMPLETED job ran
    more than 24 hours ago. Only the recent 3 should appear in recent_history.

    Expected result:
        len(result["recent_history"]) == 3
    """
    node = _make_node()
    db.add(node)

    now = datetime.utcnow()
    for i in range(3):
        job = _make_job(status="COMPLETED", node_id=node.node_id,
                        completed_at=now - timedelta(hours=i + 1))
        db.add(job)

    # One job older than 24h — should be excluded
    old_job = _make_job(status="COMPLETED", node_id=node.node_id,
                        completed_at=now - timedelta(hours=25))
    db.add(old_job)
    await db.commit()

    result = await JobService.get_node_detail(node_id=node.node_id, db=db)

    assert result is not None
    assert len(result["recent_history"]) == 3


@pytest.mark.asyncio
async def test_node_detail_capabilities_returned(db):
    """
    Node has a non-empty capabilities JSON dict (e.g. {"gpu": "2.0", "ram": "16g"}).
    The result must include a capabilities field that matches the parsed dict.

    Expected result:
        result["capabilities"] == {"gpu": "2.0", "ram": "16g"}
    """
    caps = {"gpu": "2.0", "ram": "16g"}
    node = _make_node(capabilities=caps)
    db.add(node)
    await db.commit()

    result = await JobService.get_node_detail(node_id=node.node_id, db=db)

    assert result is not None
    assert result["capabilities"] == caps
