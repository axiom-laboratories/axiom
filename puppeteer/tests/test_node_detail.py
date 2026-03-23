"""
Phase 52 — Queue Visibility, Node Drawer, and Draining: Test scaffold for VIS-03.
6 failing stubs covering the node detail enrichment (running job, eligible pending
jobs, recent history, capabilities).

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
              target_tags=None, created_at=None, completed_at=None):
    return Job(
        guid=guid or str(uuid.uuid4()),
        status=status,
        node_id=node_id,
        task_type="script",
        payload=json.dumps({"script": "print('hello')"}),
        target_tags=json.dumps(target_tags or []),
        capability_requirements=json.dumps({}),
        env_tag="test",
        created_at=created_at or datetime.utcnow(),
        created_by="test-user",
    )


# ---------------------------------------------------------------------------
# VIS-03 stubs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_node_detail_running_job_present(db):
    """
    One ASSIGNED job exists for the node.

    Expected result:
        result.running_job is not None
        result.running_job.guid == job.guid  (or result.running_job["guid"])

    Expected call:
        result = await JobService.get_node_detail(node_id=node.node_id, db=db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_node_detail_running_job_absent(db):
    """
    No ASSIGNED jobs exist for the node (node is idle).

    Expected result:
        result.running_job is None

    Expected call:
        result = await JobService.get_node_detail(node_id=node.node_id, db=db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_node_detail_eligible_pending_jobs(db):
    """
    Two PENDING jobs have target_tags matching the node's tags; a third PENDING
    job has mismatched tags and must NOT appear in the result.

    Expected result:
        len(result.eligible_pending_jobs) == 2
        all guids in result.eligible_pending_jobs belong to the matching jobs

    Expected call:
        result = await JobService.get_node_detail(node_id=node.node_id, db=db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_node_detail_eligible_pending_jobs_capped_at_50(db):
    """
    55 eligible PENDING jobs exist for the node; the result must cap the list at 50.

    Expected result:
        len(result.eligible_pending_jobs) == 50

    Expected call:
        result = await JobService.get_node_detail(node_id=node.node_id, db=db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_node_detail_recent_history(db):
    """
    3 COMPLETED jobs ran on this node in the past 24 hours; 1 COMPLETED job ran
    more than 24 hours ago. Only the recent 3 should appear in recent_history.

    Expected result:
        len(result.recent_history) == 3

    Expected call:
        result = await JobService.get_node_detail(node_id=node.node_id, db=db)
    """
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_node_detail_capabilities_returned(db):
    """
    Node has a non-empty capabilities JSON dict (e.g. {"gpu": "2.0", "ram": "16g"}).
    The result must include a capabilities field that matches the parsed dict.

    Expected result:
        result.capabilities == {"gpu": "2.0", "ram": "16g"}

    Expected call:
        result = await JobService.get_node_detail(node_id=node.node_id, db=db)
    """
    pytest.fail("not implemented")
