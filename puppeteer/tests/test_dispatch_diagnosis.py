"""
Phase 52 — Queue Visibility, Node Drawer, and Draining: Test scaffold for VIS-01.
6 failing stubs covering dispatch diagnosis / pending job explanations.

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

def _make_node(node_id=None, status="ONLINE", concurrency_limit=2,
               capabilities=None, tags=None):
    return Node(
        node_id=node_id or str(uuid.uuid4()),
        hostname="test-host",
        ip="127.0.0.1",
        status=status,
        last_seen=datetime.utcnow(),
        tags=json.dumps(tags or []),
        capabilities=json.dumps(capabilities or {}),
        env_tag="test",
        concurrency_limit=concurrency_limit,
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
        env_tag="test",
        created_at=created_at or datetime.utcnow(),
        created_by="test-user",
        target_node_id=target_node_id,
    )


# ---------------------------------------------------------------------------
# VIS-01 stubs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_diagnosis_no_nodes_online(db):
    """
    No nodes exist in the DB; the dispatch diagnosis result has:
        reason == "no_nodes_online"
        message is a non-empty string

    Expected call:
        result = await JobService.get_dispatch_diagnosis(job.guid, db)
        assert result.reason == "no_nodes_online"
        assert result.message
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_diagnosis_capability_mismatch(db):
    """
    One ONLINE node exists; the job requires capability "gpu" >= "1.0" but the
    node's capabilities dict does not include "gpu".

    Expected result:
        result.reason == "capability_mismatch"
        result.message contains the missing capability name (e.g. "gpu")

    Expected call:
        result = await JobService.get_dispatch_diagnosis(job.guid, db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_diagnosis_all_nodes_busy(db):
    """
    Two eligible nodes exist (tags and capabilities match), both at full capacity
    (number of ASSIGNED jobs equals their concurrency_limit).

    Expected result:
        result.reason == "all_nodes_busy"
        result.queue_position >= 1  (int)

    Expected call:
        result = await JobService.get_dispatch_diagnosis(job.guid, db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_diagnosis_target_node_unavailable(db):
    """
    The job has an explicit target_node_id pointing to a node whose status is
    OFFLINE or DRAINING (not ONLINE).

    Expected result:
        result.reason == "target_node_unavailable"

    Expected call:
        result = await JobService.get_dispatch_diagnosis(job.guid, db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_diagnosis_pending_dispatch(db):
    """
    An eligible ONLINE node with spare capacity exists for the job.

    Expected result:
        result.reason == "pending_dispatch"
        result.message indicates the job will be dispatched soon (non-empty string)

    Expected call:
        result = await JobService.get_dispatch_diagnosis(job.guid, db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_diagnosis_queue_position_is_count_of_earlier_pending(db):
    """
    3 PENDING jobs were created BEFORE this job, and 2 PENDING jobs were created
    AFTER this job (all eligible for the same nodes).

    Expected: result.queue_position == 3
    (Only jobs created before this one count toward queue_position.)

    Expected call:
        result = await JobService.get_dispatch_diagnosis(job.guid, db)
        assert result.queue_position == 3
    """
    pytest.fail("not implemented")
