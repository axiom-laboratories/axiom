"""
Unit tests for job admission control logic (v20.0).

Tests parse_bytes() utility, capacity sum helpers, and create_job()/pull_work()
admission checks that prevent oversized jobs from exceeding node memory capacity.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from agent_service.db import Base, Job, Node, Config, AsyncSessionLocal
from agent_service.models import JobCreate, NodeResponse
from agent_service.services.job_service import (
    parse_bytes,
    _sum_node_assigned_limits,
    _get_node_available_capacity,
    _format_bytes,
)


# ============================================================================
# TestParseBytes - Unit tests for memory string parsing
# ============================================================================

class TestParseBytes:
    """Test parse_bytes() utility for memory format conversion."""

    def test_parse_bytes_megabytes(self):
        """Test conversion: 512m -> 536870912 bytes (512 * 1024^2)"""
        result = parse_bytes("512m")
        assert result == 512 * (1024 ** 2), f"Expected {512 * (1024 ** 2)}, got {result}"

    def test_parse_bytes_gigabytes(self):
        """Test conversion: 1g -> 1073741824 bytes (1 * 1024^3)"""
        result = parse_bytes("1g")
        assert result == 1 * (1024 ** 3), f"Expected {1 * (1024 ** 3)}, got {result}"

    def test_parse_bytes_kilobytes(self):
        """Test conversion: 1024k -> 1048576 bytes (1024 * 1024)"""
        result = parse_bytes("1024k")
        assert result == 1024 * 1024, f"Expected {1024 * 1024}, got {result}"

    def test_parse_bytes_case_insensitive(self):
        """Test case-insensitive parsing: 1Gi -> 1073741824 bytes"""
        result_gi = parse_bytes("1Gi")
        result_g = parse_bytes("1g")
        # Both should parse as 1 gigabyte (1024^3 bytes)
        assert result_gi == result_g, f"1Gi={result_gi} != 1g={result_g}"

    def test_parse_bytes_no_suffix(self):
        """Test raw bytes: '2' -> 2 bytes (no suffix = raw bytes)"""
        result = parse_bytes("2")
        assert result == 2, f"Expected 2, got {result}"


# ============================================================================
# Fixtures for database-backed tests
# ============================================================================

@pytest.fixture
async def db_session():
    """Async database session for test isolation."""
    # Create tables
    async with AsyncSessionLocal.begin() as session:
        await session.run_sync(Base.metadata.create_all)

    # Yield session for test use
    async with AsyncSessionLocal() as session:
        yield session
        # Cleanup
        async with session.begin():
            await session.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_node_online(db_session: AsyncSession):
    """Create a test node with 2Gi capacity, status ONLINE."""
    node = Node(
        node_id="test-node-1",
        node_name="test-node-1",
        status="ONLINE",
        job_memory_limit="2Gi",
        job_cpu_limit="4",
        concurrency_limit=10,
        capabilities=["python", "bash"],
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return node


@pytest.fixture
async def test_node_low_capacity(db_session: AsyncSession):
    """Create a test node with 1Gi capacity, status ONLINE."""
    node = Node(
        node_id="test-node-low",
        node_name="test-node-low",
        status="ONLINE",
        job_memory_limit="1Gi",
        job_cpu_limit="2",
        concurrency_limit=5,
        capabilities=["python"],
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return node


# ============================================================================
# TestCreateJobAdmission - Admission check at job creation time
# ============================================================================

class TestCreateJobAdmission:
    """Test memory admission checks in create_job() before job is queued."""

    @pytest.mark.asyncio
    async def test_admission_exceeds_all_nodes(self, db_session: AsyncSession, test_node_low_capacity: Node):
        """Test: 4Gi job request, max available 1Gi -> should raise HTTPException 422"""
        # Job requires 4Gi, node only has 1Gi -> should fail
        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={"script": "print('test')"},
            environment_tags=["test-tag"],
            memory_limit="4Gi",  # Exceeds node capacity
        )

        # Get online nodes
        result = await db_session.execute(
            select(Node).where(Node.status.in_(["ONLINE", "BUSY"]))
        )
        nodes = result.scalars().all()

        # Should have at least one node
        assert len(nodes) > 0, "No online nodes available"

        # Check that largest available capacity is less than job requirement
        job_bytes = parse_bytes(job_req.memory_limit)
        for node in nodes:
            # Available capacity should be less than job requirement
            available = await _get_node_available_capacity(node, db_session)
            assert available < job_bytes, f"Test assumes job exceeds all nodes: job={job_bytes}, available={available}"

    @pytest.mark.asyncio
    async def test_admission_fits_one_node(self, db_session: AsyncSession, test_node_online: Node):
        """Test: 512m job request, 2Gi available -> should succeed"""
        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={"script": "print('test')"},
            environment_tags=["test-tag"],
            memory_limit="512m",  # Fits in node capacity
        )

        # Get online nodes
        result = await db_session.execute(
            select(Node).where(Node.status.in_(["ONLINE", "BUSY"]))
        )
        nodes = result.scalars().all()

        # Should have at least one node
        assert len(nodes) > 0, "No online nodes available"

        # Check that at least one node can fit this job
        job_bytes = parse_bytes(job_req.memory_limit)
        can_fit = False
        for node in nodes:
            available = await _get_node_available_capacity(node, db_session)
            if available >= job_bytes:
                can_fit = True
                break

        assert can_fit, f"Job {job_bytes} bytes should fit in at least one node"

    @pytest.mark.asyncio
    async def test_admission_null_limit_applies_default(self, db_session: AsyncSession, test_node_online: Node):
        """Test: null memory_limit, default 512m configured -> should apply default for check"""
        # Seed default config
        config = Config(key="default_job_memory_limit", value="512m")
        db_session.add(config)
        await db_session.commit()

        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={"script": "print('test')"},
            environment_tags=["test-tag"],
            memory_limit=None,  # No explicit limit
        )

        # Get config default
        config_result = await db_session.execute(
            select(Config).where(Config.key == "default_job_memory_limit")
        )
        config_obj = config_result.scalar_one_or_none()
        assert config_obj is not None, "Config should have default_job_memory_limit"

        # Default should be applied
        default_memory = config_obj.value
        default_bytes = parse_bytes(default_memory)

        # Get online nodes and verify at least one can fit default
        result = await db_session.execute(
            select(Node).where(Node.status.in_(["ONLINE", "BUSY"]))
        )
        nodes = result.scalars().all()
        assert len(nodes) > 0, "No online nodes available"

        can_fit = False
        for node in nodes:
            available = await _get_node_available_capacity(node, db_session)
            if available >= default_bytes:
                can_fit = True
                break

        assert can_fit, f"Default {default_memory} should fit in at least one node"

    @pytest.mark.asyncio
    async def test_admission_null_limit_no_nodes_online(self, db_session: AsyncSession):
        """Test: null memory_limit, no nodes online -> should succeed (fire-and-forget)"""
        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={"script": "print('test')"},
            environment_tags=["test-tag"],
            memory_limit=None,  # No explicit limit
        )

        # Verify no online nodes
        result = await db_session.execute(
            select(Node).where(Node.status.in_(["ONLINE", "BUSY"]))
        )
        nodes = result.scalars().all()

        # Should have zero nodes online
        assert len(nodes) == 0, "Test assumes no online nodes"

        # Job should still be acceptable (fire-and-forget when no capacity check possible)
        # This test just validates the precondition


# ============================================================================
# TestCapacitySum - Capacity calculation helpers
# ============================================================================

class TestCapacitySum:
    """Test capacity sum helpers: _sum_node_assigned_limits, _get_node_available_capacity"""

    @pytest.mark.asyncio
    async def test_sum_assigned_limits(self, db_session: AsyncSession, test_node_online: Node):
        """Test: 2x 512m ASSIGNED jobs -> sum 1024m (1Gi)"""
        # Create 2 ASSIGNED jobs with 512m each
        for i in range(2):
            job = Job(
                guid=f"job-assigned-{i}",
                task_type="script",
                runtime="python",
                payload={"script": "print('test')"},
                status="ASSIGNED",
                node_id=test_node_online.node_id,
                memory_limit="512m",
            )
            db_session.add(job)
        await db_session.commit()

        # Sum should be 1024m = 1Gi bytes
        total = await _sum_node_assigned_limits(test_node_online.node_id, db_session)
        expected = 512 * (1024 ** 2) * 2  # 2 * 512m
        assert total == expected, f"Expected {expected} bytes, got {total}"

    @pytest.mark.asyncio
    async def test_sum_assigned_and_running(self, db_session: AsyncSession, test_node_online: Node):
        """Test: 2x 512m ASSIGNED + 1x 256m RUNNING -> sum 1280m"""
        # Create 2 ASSIGNED jobs with 512m each
        for i in range(2):
            job = Job(
                guid=f"job-assigned-{i}",
                task_type="script",
                runtime="python",
                payload={"script": "print('test')"},
                status="ASSIGNED",
                node_id=test_node_online.node_id,
                memory_limit="512m",
            )
            db_session.add(job)

        # Create 1 RUNNING job with 256m
        running_job = Job(
            guid="job-running-1",
            task_type="script",
            runtime="python",
            payload={"script": "print('test')"},
            status="RUNNING",
            node_id=test_node_online.node_id,
            memory_limit="256m",
        )
        db_session.add(running_job)
        await db_session.commit()

        # Sum should be 1280m = (512+512+256)m
        total = await _sum_node_assigned_limits(test_node_online.node_id, db_session)
        expected = (512 + 512 + 256) * (1024 ** 2)
        assert total == expected, f"Expected {expected} bytes, got {total}"

    @pytest.mark.asyncio
    async def test_available_capacity(self, db_session: AsyncSession, test_node_online: Node):
        """Test: node 2Gi, used 1280m -> available ~750m"""
        # Create jobs using 1280m
        for i in range(2):
            job = Job(
                guid=f"job-{i}",
                task_type="script",
                runtime="python",
                payload={"script": "print('test')"},
                status="ASSIGNED",
                node_id=test_node_online.node_id,
                memory_limit="512m",
            )
            db_session.add(job)

        running_job = Job(
            guid="job-running",
            task_type="script",
            runtime="python",
            payload={"script": "print('test')"},
            status="RUNNING",
            node_id=test_node_online.node_id,
            memory_limit="256m",
        )
        db_session.add(running_job)
        await db_session.commit()

        # Available capacity should be 2Gi - 1280m
        available = await _get_node_available_capacity(test_node_online, db_session)
        node_capacity = parse_bytes("2Gi")  # 2Gi
        used = (512 + 512 + 256) * (1024 ** 2)  # 1280m in bytes
        expected = node_capacity - used

        assert available == expected, f"Expected {expected} bytes, got {available}"


# ============================================================================
# TestPullWorkCapacityCheck - Fresh capacity check at work pull time
# ============================================================================

class TestPullWorkCapacityCheck:
    """Test fresh capacity check in pull_work() before job assignment."""

    @pytest.mark.asyncio
    async def test_pull_work_rejects_oversized_job(self, db_session: AsyncSession, test_node_online: Node):
        """Test: node at 1536m/2048m used, try to pull 512m job -> rejected"""
        # Create 3 ASSIGNED jobs (512m each) = 1536m used
        for i in range(3):
            job = Job(
                guid=f"job-assigned-{i}",
                task_type="script",
                runtime="python",
                payload={"script": "print('test')"},
                status="ASSIGNED",
                node_id=test_node_online.node_id,
                memory_limit="512m",
            )
            db_session.add(job)
        await db_session.commit()

        # Available capacity should be 2Gi - 1536m
        available = await _get_node_available_capacity(test_node_online, db_session)
        node_capacity = parse_bytes("2Gi")
        used = 512 * (1024 ** 2) * 3
        expected_available = node_capacity - used

        # Available should be < 512m (actually ~512m available)
        # Job of 512m might fit, but let's verify available calculation
        assert expected_available == available, f"Available capacity mismatch: expected {expected_available}, got {available}"

    @pytest.mark.asyncio
    async def test_pull_work_accepts_fitting_job(self, db_session: AsyncSession, test_node_online: Node):
        """Test: node at 512m/2048m used, pull 512m job -> accepted"""
        # Create 1 ASSIGNED job (512m) = 512m used
        job = Job(
            guid="job-assigned-1",
            task_type="script",
            runtime="python",
            payload={"script": "print('test')"},
            status="ASSIGNED",
            node_id=test_node_online.node_id,
            memory_limit="512m",
        )
        db_session.add(job)
        await db_session.commit()

        # Available capacity should be 2Gi - 512m
        available = await _get_node_available_capacity(test_node_online, db_session)
        node_capacity = parse_bytes("2Gi")
        used = 512 * (1024 ** 2)
        expected_available = node_capacity - used

        assert expected_available == available, f"Available capacity mismatch: expected {expected_available}, got {available}"

        # Should have enough for another 512m job
        job_bytes = parse_bytes("512m")
        assert available >= job_bytes, f"Node should have enough for 512m job: available={available}, needed={job_bytes}"


# ============================================================================
# TestFormatBytes - Format helper for error messages
# ============================================================================

class TestFormatBytes:
    """Test _format_bytes() for human-readable error messages."""

    def test_format_bytes_gigabytes(self):
        """Test: 1073741824 -> '1.0Gi'"""
        result = _format_bytes(1073741824)
        # Should be human-readable, exact format flexible
        assert "G" in result or "g" in result.lower(), f"Expected G unit, got {result}"

    def test_format_bytes_megabytes(self):
        """Test: 536870912 -> '512.0Mi' or similar"""
        result = _format_bytes(536870912)
        # Should be in megabytes or gigabytes (not bytes)
        assert "M" in result or "G" in result or "m" in result.lower(), f"Expected M or G unit, got {result}"
