"""
Phase 52 — Queue Visibility, Node Drawer, and Draining: Test scaffold for VIS-04.
8 failing stubs covering node DRAINING state transitions and work-pull exclusion.

Each stub documents the expected future API shape via its docstring, then immediately
calls pytest.fail("not implemented") so they fail with the correct marker before
any implementation lands. Plan 02 will remove the pytest.fail lines and complete
the assertions.
"""
import json
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from agent_service.db import Base, Job, Node


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

def _make_node(node_id=None, status="ONLINE", concurrency_limit=2):
    return Node(
        node_id=node_id or str(uuid.uuid4()),
        hostname="test-host",
        ip="127.0.0.1",
        status=status,
        last_seen=datetime.utcnow(),
        tags=json.dumps([]),
        capabilities=json.dumps({}),
        env_tag="test",
        concurrency_limit=concurrency_limit,
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
        env_tag="test",
        created_at=datetime.utcnow(),
        created_by="test-user",
    )


# ---------------------------------------------------------------------------
# VIS-04 stubs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_drain_endpoint_sets_status_draining(db):
    """
    POST /nodes/{node_id}/drain on an ONLINE node returns 200 and sets
    node.status == "DRAINING" in the database.

    Expected call: POST /nodes/{node_id}/drain via httpx TestClient or
    direct call to a drain helper in job_service.py.
    After the call: await db.refresh(node); assert node.status == "DRAINING"
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_undrain_endpoint_sets_status_online(db):
    """
    POST /nodes/{node_id}/undrain (or PATCH) on a DRAINING node returns 200
    and sets node.status == "ONLINE" in the database.

    Expected call: POST /nodes/{node_id}/undrain via httpx TestClient.
    After the call: await db.refresh(node); assert node.status == "ONLINE"
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_drain_rejects_already_draining(db):
    """
    POST /nodes/{node_id}/drain on a node that is already in DRAINING state
    returns HTTP 409 Conflict.

    Expected: response.status_code == 409
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_pull_work_skips_draining_node(db):
    """
    When a DRAINING node calls JobService.pull_work (or the /work/pull endpoint),
    it must receive PollResponse(job=None) — no job is assigned to it.

    Expected call:
        result = await JobService.pull_work(node_id=node.node_id, db=db)
        assert result.job is None

    The PENDING job in DB must remain PENDING (not ASSIGNED to the draining node).
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_heartbeat_preserves_draining_status(db):
    """
    receive_heartbeat called for a DRAINING node must NOT revert the status
    back to "ONLINE". After the heartbeat call, node.status must still be "DRAINING".

    Expected call:
        await JobService.receive_heartbeat(node_id=node.node_id, db=db, ...)
        await db.refresh(node)
        assert node.status == "DRAINING"
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_list_nodes_draining_preserved(db):
    """
    GET /nodes response for a DRAINING node carries status="DRAINING",
    not "ONLINE" — even if last_seen is within the 60-second online window.

    Expected: the node dict/model in the response has status == "DRAINING"
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_auto_offline_transition_when_last_job_completes(db):
    """
    A DRAINING node with exactly one ASSIGNED job: when report_result is called
    for that job (marking it COMPLETED), the node.status automatically transitions
    to "OFFLINE" (no more active work to finish).

    Expected call:
        await JobService.report_result(job_guid=job.guid, success=True, db=db)
        await db.refresh(node)
        assert node.status == "OFFLINE"
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_draining_node_not_reverted_with_active_jobs(db):
    """
    A DRAINING node with two ASSIGNED jobs: first result arrives (one job completes);
    node.status must remain "DRAINING" because one active job still remains.

    Expected call:
        await JobService.report_result(job_guid=job1.guid, success=True, db=db)
        await db.refresh(node)
        assert node.status == "DRAINING"  # NOT "OFFLINE" — still has job2 running
    """
    pytest.fail("not implemented")
