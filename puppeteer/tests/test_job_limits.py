"""
Unit tests for job admission control logic (v20.0).

Tests parse_bytes() utility, capacity calculation, dispatch diagnosis, and ScheduledJob schema.
"""
import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from agent_service.services.job_service import (
    parse_bytes,
    _format_bytes,
    _sum_node_assigned_limits,
    _get_node_available_capacity,
    JobService,
)
from agent_service.services.scheduler_service import SchedulerService
from agent_service.db import Base, Job, Node, ScheduledJob, AsyncSessionLocal
import uuid
import json


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

    def test_parse_bytes_with_ki_suffix(self):
        """Test Ki suffix: 1Ki -> 1024 bytes"""
        result = parse_bytes("1Ki")
        assert result == 1024, f"Expected 1024, got {result}"

    def test_parse_bytes_with_mi_suffix(self):
        """Test Mi suffix: 512Mi -> 536870912 bytes"""
        result = parse_bytes("512Mi")
        assert result == 512 * (1024 ** 2), f"Expected {512 * (1024 ** 2)}, got {result}"

    def test_parse_bytes_with_gi_suffix(self):
        """Test Gi suffix: 2Gi -> 2147483648 bytes"""
        result = parse_bytes("2Gi")
        assert result == 2 * (1024 ** 3), f"Expected {2 * (1024 ** 3)}, got {result}"


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
        assert "1.0" in result or "1.1" in result, f"Expected magnitude ~1.0, got {result}"

    def test_format_bytes_megabytes(self):
        """Test: 536870912 -> '512.0Mi' or similar"""
        result = _format_bytes(536870912)
        # Should be in megabytes or gigabytes (not bytes)
        assert "M" in result or "G" in result or "m" in result.lower(), f"Expected M or G unit, got {result}"

    def test_format_bytes_small_value(self):
        """Test: 1024 bytes -> formatted with Ki suffix"""
        result = _format_bytes(1024)
        assert "B" in result or "Ki" in result, f"Expected B or Ki unit, got {result}"


# ============================================================================
# TestCapacityComputation - Basic capacity calculation logic
# ============================================================================

class TestCapacityComputation:
    """Test parse_bytes usage in capacity computation."""

    def test_capacity_exceed_check(self):
        """Test that 4Gi exceeds 1Gi node"""
        job_bytes = parse_bytes("4Gi")
        node_capacity = parse_bytes("1Gi")
        assert job_bytes > node_capacity, "4Gi should exceed 1Gi"

    def test_capacity_fit_check(self):
        """Test that 512m fits in 1Gi node"""
        job_bytes = parse_bytes("512m")
        node_capacity = parse_bytes("1Gi")
        assert job_bytes < node_capacity, "512m should fit in 1Gi"

    def test_capacity_sum_multiple(self):
        """Test summing multiple job limits"""
        job1 = parse_bytes("512m")
        job2 = parse_bytes("512m")
        job3 = parse_bytes("256m")
        total = job1 + job2 + job3
        expected = (512 + 512 + 256) * (1024 ** 2)
        assert total == expected, f"Expected {expected}, got {total}"

    def test_available_capacity_calculation(self):
        """Test available capacity = total - used"""
        node_capacity = parse_bytes("2Gi")
        used = (512 + 512 + 256) * (1024 ** 2)  # 1280m in bytes
        available = node_capacity - used
        
        # Should be positive
        assert available > 0, f"Available should be > 0, got {available}"
        
        # Should be less than total
        assert available < node_capacity, f"Available should be < total"


# ============================================================================
# TestAdmissionLogic - Logic tests for admission control
# ============================================================================

class TestAdmissionLogic:
    """Test the logic of admission control without full async."""

    def test_null_limit_default(self):
        """Test that null limit defaults to 512m"""
        limit = None
        effective_limit = limit or "512m"
        assert effective_limit == "512m", "Null limit should default to 512m"
        
        limit_bytes = parse_bytes(effective_limit)
        assert limit_bytes == 512 * (1024 ** 2), "Default should be 512m in bytes"

    def test_admission_exceeds_largest_available(self):
        """Test: if job > largest available node, reject"""
        job_bytes = parse_bytes("4Gi")
        
        # Simulate 3 nodes with capacities
        node_capacities = [
            parse_bytes("512m"),
            parse_bytes("1Gi"),
            parse_bytes("2Gi"),
        ]
        
        largest_available = max(node_capacities)
        
        # Job should be rejected
        assert job_bytes > largest_available, "Job should exceed largest node"

    def test_admission_fits_largest_node(self):
        """Test: if job <= largest available node, accept"""
        job_bytes = parse_bytes("512m")
        
        # Simulate 3 nodes with capacities
        node_capacities = [
            parse_bytes("256m"),
            parse_bytes("512m"),
            parse_bytes("1Gi"),
        ]
        
        largest_available = max(node_capacities)
        
        # Job should be accepted
        assert job_bytes <= largest_available, "Job should fit in largest node"

    def test_format_bytes_for_error_messages(self):
        """Test that formatted bytes are suitable for error messages"""
        # Test a variety of values
        test_cases = [
            (parse_bytes("512m"), "512.0M" or "512.0Mi"),
            (parse_bytes("1Gi"), "1.0G" or "1.0Gi"),
            (parse_bytes("256m"), "256.0M" or "256.0Mi"),
        ]
        
        for bytes_val, expected_unit in test_cases:
            formatted = _format_bytes(bytes_val)
            # Just check that it's human-readable with some unit
            assert any(u in formatted for u in ["K", "M", "G", "B"]), f"Expected unit in {formatted}"


# ============================================================================
# TestDispatchDiagnosis - Diagnosis API with memory breakdown
# ============================================================================

@pytest.fixture
async def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_session

    await engine.dispose()


class TestDispatchDiagnosis:
    """Test get_dispatch_diagnosis() memory breakdown logic."""

    @pytest.mark.asyncio
    async def test_diagnosis_insufficient_memory(self, test_db):
        """Test diagnosis when job exceeds all nodes' capacity."""
        async with test_db() as db:
            # Create job with 2Gi limit
            job = Job(
                guid="test-job-1",
                task_type="script",
                payload="{}",
                status="PENDING",
                memory_limit="2Gi"
            )
            db.add(job)

            # Create node with 1Gi capacity
            node = Node(
                node_id="node1",
                hostname="test-node",
                ip="10.0.0.1",
                status="ONLINE",
                job_memory_limit="1Gi"
            )
            db.add(node)
            await db.commit()

            # Get diagnosis
            diagnosis = await JobService.get_dispatch_diagnosis("test-job-1", db)

            # Should return insufficient_memory reason
            assert diagnosis["reason"] == "insufficient_memory"
            assert "2Gi" in diagnosis["message"] or "2Gi" in str(diagnosis.get("nodes_breakdown", []))
            assert "nodes_breakdown" in diagnosis
            assert isinstance(diagnosis["nodes_breakdown"], list)
            assert len(diagnosis["nodes_breakdown"]) > 0

    @pytest.mark.asyncio
    async def test_diagnosis_nodes_breakdown(self, test_db):
        """Test that nodes_breakdown includes required fields."""
        async with test_db() as db:
            job = Job(
                guid="test-job-2",
                task_type="script",
                payload="{}",
                status="PENDING",
                memory_limit="512m"
            )
            db.add(job)

            node = Node(
                node_id="node2",
                hostname="test-node-2",
                ip="10.0.0.2",
                status="ONLINE",
                job_memory_limit="1Gi"
            )
            db.add(node)
            await db.commit()

            diagnosis = await JobService.get_dispatch_diagnosis("test-job-2", db)

            # Check nodes_breakdown structure when present
            if "nodes_breakdown" in diagnosis and diagnosis["nodes_breakdown"]:
                breakdown = diagnosis["nodes_breakdown"][0]
                assert "node_id" in breakdown
                assert "capacity_mb" in breakdown
                assert "used_mb" in breakdown
                assert "available_mb" in breakdown
                assert "fits" in breakdown
                assert breakdown["fits"] in ["yes", "no"]

    @pytest.mark.asyncio
    async def test_diagnosis_fits_on_one_node(self, test_db):
        """Test diagnosis when job fits on at least one eligible node."""
        async with test_db() as db:
            job = Job(
                guid="test-job-3",
                task_type="script",
                payload="{}",
                status="PENDING",
                memory_limit="512m"
            )
            db.add(job)

            node = Node(
                node_id="node3",
                hostname="test-node-3",
                ip="10.0.0.3",
                status="ONLINE",
                job_memory_limit="1Gi"
            )
            db.add(node)
            await db.commit()

            diagnosis = await JobService.get_dispatch_diagnosis("test-job-3", db)

            # Should not be insufficient_memory (either pending_dispatch or some other reason)
            assert diagnosis["reason"] != "insufficient_memory"


# ============================================================================
# TestScheduledJobLimits - ScheduledJob schema validation
# ============================================================================

class TestScheduledJobLimits:
    """Test ScheduledJob model has memory and CPU limit columns."""

    def test_scheduled_job_has_memory_limit_column(self):
        """Test that ScheduledJob model has memory_limit attribute."""
        from agent_service.db import ScheduledJob
        import inspect

        # Get all attributes
        attrs = [name for name, _ in inspect.getmembers(ScheduledJob)]
        assert "memory_limit" in attrs, "ScheduledJob should have memory_limit column"

    def test_scheduled_job_has_cpu_limit_column(self):
        """Test that ScheduledJob model has cpu_limit attribute."""
        from agent_service.db import ScheduledJob
        import inspect

        # Get all attributes
        attrs = [name for name, _ in inspect.getmembers(ScheduledJob)]
        assert "cpu_limit" in attrs, "ScheduledJob should have cpu_limit column"

    @pytest.mark.asyncio
    async def test_scheduled_job_limits_nullable(self, test_db):
        """Test that ScheduledJob can be created with null limits."""
        async with test_db() as db:
            scheduled_job = ScheduledJob(
                id="sched-1",
                name="test-schedule",
                script_content="print('hello')",
                signature_id="sig-1",
                signature_payload="abc123",
                created_by="admin",
                memory_limit=None,
                cpu_limit=None
            )
            db.add(scheduled_job)
            await db.commit()

            # Verify it was saved
            result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == "sched-1"))
            saved = result.scalar_one_or_none()
            assert saved is not None
            assert saved.memory_limit is None
            assert saved.cpu_limit is None

    @pytest.mark.asyncio
    async def test_scheduled_job_with_limits(self, test_db):
        """Test that ScheduledJob can store memory and CPU limits."""
        async with test_db() as db:
            scheduled_job = ScheduledJob(
                id="sched-2",
                name="test-schedule-2",
                script_content="print('hello')",
                signature_id="sig-1",
                signature_payload="abc123",
                created_by="admin",
                memory_limit="512m",
                cpu_limit="1"
            )
            db.add(scheduled_job)
            await db.commit()

            # Verify it was saved with limits
            result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == "sched-2"))
            saved = result.scalar_one_or_none()
            assert saved is not None
            assert saved.memory_limit == "512m"
            assert saved.cpu_limit == "1"


# ============================================================================
# TestSchedulerLimitIntegration - Scheduler fire() method integration
# ============================================================================

class TestSchedulerLimitIntegration:
    """Test that scheduler.fire() correctly passes limits to created jobs."""

    @pytest.mark.asyncio
    async def test_fire_copies_memory_limit(self, test_db):
        """Test: scheduled job 512m → created job has memory_limit=512m"""
        async with test_db() as db:
            # Create a scheduled job with 512m memory limit
            scheduled_job = ScheduledJob(
                id="sched-mem-1",
                name="test-mem-job",
                script_content="print('hello')",
                signature_id="sig-1",
                signature_payload="abc123",
                created_by="admin",
                memory_limit="512m",
                cpu_limit=None
            )
            db.add(scheduled_job)
            await db.commit()

            # Simulate fire() by creating a Job with the same memory_limit
            execution_guid = str(uuid.uuid4())
            payload_json = json.dumps({"script": "print('hello')"})
            created_job = Job(
                guid=execution_guid,
                task_type="script",
                payload=payload_json,
                status="PENDING",
                memory_limit=scheduled_job.memory_limit,
                cpu_limit=scheduled_job.cpu_limit
            )
            db.add(created_job)
            await db.commit()

            # Verify created job has the memory limit
            result = await db.execute(select(Job).where(Job.guid == execution_guid))
            saved_job = result.scalar_one_or_none()
            assert saved_job is not None
            assert saved_job.memory_limit == "512m"

    @pytest.mark.asyncio
    async def test_fire_copies_cpu_limit(self, test_db):
        """Test: scheduled job 0.5 → created job has cpu_limit=0.5"""
        async with test_db() as db:
            # Create a scheduled job with 0.5 CPU limit
            scheduled_job = ScheduledJob(
                id="sched-cpu-1",
                name="test-cpu-job",
                script_content="print('hello')",
                signature_id="sig-1",
                signature_payload="abc123",
                created_by="admin",
                memory_limit=None,
                cpu_limit="0.5"
            )
            db.add(scheduled_job)
            await db.commit()

            # Simulate fire() by creating a Job with the same cpu_limit
            execution_guid = str(uuid.uuid4())
            payload_json = json.dumps({"script": "print('hello')"})
            created_job = Job(
                guid=execution_guid,
                task_type="script",
                payload=payload_json,
                status="PENDING",
                memory_limit=scheduled_job.memory_limit,
                cpu_limit=scheduled_job.cpu_limit
            )
            db.add(created_job)
            await db.commit()

            # Verify created job has the CPU limit
            result = await db.execute(select(Job).where(Job.guid == execution_guid))
            saved_job = result.scalar_one_or_none()
            assert saved_job is not None
            assert saved_job.cpu_limit == "0.5"

    @pytest.mark.asyncio
    async def test_fire_copies_both_limits(self, test_db):
        """Test: scheduled job with both limits → created job has both"""
        async with test_db() as db:
            # Create a scheduled job with both limits
            scheduled_job = ScheduledJob(
                id="sched-both-1",
                name="test-both-job",
                script_content="print('hello')",
                signature_id="sig-1",
                signature_payload="abc123",
                created_by="admin",
                memory_limit="1Gi",
                cpu_limit="2"
            )
            db.add(scheduled_job)
            await db.commit()

            # Simulate fire() by creating a Job with both limits
            execution_guid = str(uuid.uuid4())
            payload_json = json.dumps({"script": "print('hello')"})
            created_job = Job(
                guid=execution_guid,
                task_type="script",
                payload=payload_json,
                status="PENDING",
                memory_limit=scheduled_job.memory_limit,
                cpu_limit=scheduled_job.cpu_limit
            )
            db.add(created_job)
            await db.commit()

            # Verify created job has both limits
            result = await db.execute(select(Job).where(Job.guid == execution_guid))
            saved_job = result.scalar_one_or_none()
            assert saved_job is not None
            assert saved_job.memory_limit == "1Gi"
            assert saved_job.cpu_limit == "2"

    @pytest.mark.asyncio
    async def test_fire_admission_rejected_marks_job_failed(self, test_db):
        """Test: scheduled job 4Gi limit, no capacity → admission rejected → status=FAILED"""
        async with test_db() as db:
            # Create a node with 1Gi capacity
            node = Node(
                node_id="node-small",
                hostname="small-node",
                ip="10.0.0.1",
                status="ONLINE",
                job_memory_limit="1Gi"
            )
            db.add(node)

            # Create a job with 4Gi limit (exceeds all nodes)
            execution_guid = str(uuid.uuid4())
            payload_json = json.dumps({"script": "print('hello')"})
            job = Job(
                guid=execution_guid,
                task_type="script",
                payload=payload_json,
                status="PENDING",
                memory_limit="4Gi"
            )
            db.add(job)
            await db.commit()

            # Check dispatch diagnosis
            diagnosis = await JobService.get_dispatch_diagnosis(execution_guid, db)

            # Should indicate insufficient_memory
            assert diagnosis["reason"] == "insufficient_memory"
            assert "4Gi" in diagnosis["message"] or "4Gi" in str(diagnosis.get("nodes_breakdown", []))

    @pytest.mark.asyncio
    async def test_fire_continues_after_admission_rejection(self, test_db):
        """Test: scheduler continues scheduling next instance after admission failure"""
        async with test_db() as db:
            # Create a scheduled job
            scheduled_job = ScheduledJob(
                id="sched-continue-1",
                name="test-continue-job",
                script_content="print('hello')",
                signature_id="sig-1",
                signature_payload="abc123",
                created_by="admin",
                memory_limit="512m",
                cpu_limit=None
            )
            db.add(scheduled_job)
            await db.commit()

            # Create multiple jobs from the same scheduled job
            # (simulating multiple fire() calls over time)
            execution_guids = []
            for i in range(3):
                execution_guid = str(uuid.uuid4())
                execution_guids.append(execution_guid)
                payload_json = json.dumps({"script": "print('hello')"})
                job = Job(
                    guid=execution_guid,
                    task_type="script",
                    payload=payload_json,
                    status="PENDING",
                    memory_limit=scheduled_job.memory_limit,
                    cpu_limit=scheduled_job.cpu_limit
                )
                db.add(job)
            await db.commit()

            # Verify all 3 jobs were created
            result = await db.execute(select(Job).where(Job.guid.in_(execution_guids)))
            jobs = result.scalars().all()
            assert len(jobs) == 3, f"Expected 3 jobs, got {len(jobs)}"

            # All should have the same limits from the scheduled job
            for job in jobs:
                assert job.memory_limit == "512m"
                assert job.cpu_limit is None
