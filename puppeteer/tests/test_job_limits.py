"""
Unit tests for Job model limit fields (memory_limit, cpu_limit).

These tests are in RED (failing) state until Phase 120 Wave 1 adds:
1. memory_limit and cpu_limit columns to Job DB model
2. memory_limit and cpu_limit fields to JobCreate, JobResponse, WorkResponse Pydantic models
3. Field validators for format validation (memory: \d+[mMgG][bB]?|[0-9.]+[Gg][iI]?, cpu: \d+(\.\d+)?)
"""

import pytest
from pydantic import ValidationError
from agent_service.models import JobCreate, JobResponse, WorkResponse
from agent_service.db import Job, AsyncSessionLocal
from datetime import datetime
import json


class TestMemoryLimitInJobCreate:
    """Test that JobCreate accepts memory_limit field."""

    def test_memory_limit_accepted_512m(self):
        """JobCreate with memory_limit='512m' should be accepted."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={},
            memory_limit="512m"
        )
        assert job.memory_limit == "512m"

    def test_memory_limit_accepted_1g(self):
        """JobCreate with memory_limit='1g' should be accepted."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={},
            memory_limit="1g"
        )
        assert job.memory_limit == "1g"

    def test_memory_limit_accepted_1gi(self):
        """JobCreate with memory_limit='1Gi' (binary) should be accepted."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={},
            memory_limit="1Gi"
        )
        assert job.memory_limit == "1Gi"

    def test_memory_limit_nullable_none(self):
        """JobCreate with memory_limit=None should be accepted."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={},
            memory_limit=None
        )
        assert job.memory_limit is None

    def test_memory_limit_omitted(self):
        """JobCreate without memory_limit field should default to None."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={}
        )
        assert job.memory_limit is None


class TestCPULimitInJobCreate:
    """Test that JobCreate accepts cpu_limit field."""

    def test_cpu_limit_accepted_2(self):
        """JobCreate with cpu_limit='2' should be accepted."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={},
            cpu_limit="2"
        )
        assert job.cpu_limit == "2"

    def test_cpu_limit_accepted_0_5(self):
        """JobCreate with cpu_limit='0.5' should be accepted."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={},
            cpu_limit="0.5"
        )
        assert job.cpu_limit == "0.5"

    def test_cpu_limit_nullable_none(self):
        """JobCreate with cpu_limit=None should be accepted."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={},
            cpu_limit=None
        )
        assert job.cpu_limit is None

    def test_cpu_limit_omitted(self):
        """JobCreate without cpu_limit field should default to None."""
        job = JobCreate(
            task_type="script",
            runtime="python",
            payload={}
        )
        assert job.cpu_limit is None


class TestMemoryFormatValidation:
    """Test memory_limit format validation."""

    def test_memory_limit_invalid_format_xyz(self):
        """JobCreate with memory_limit='xyz' should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                task_type="script",
                runtime="python",
                payload={},
                memory_limit="xyz"
            )
        # Ensure validation error is present
        assert "memory_limit" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()

    def test_memory_limit_invalid_format_512(self):
        """JobCreate with memory_limit='512' (no unit) should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                task_type="script",
                runtime="python",
                payload={},
                memory_limit="512"
            )
        assert "memory_limit" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()


class TestCPUFormatValidation:
    """Test cpu_limit format validation."""

    def test_cpu_limit_invalid_format_abc(self):
        """JobCreate with cpu_limit='abc' should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                task_type="script",
                runtime="python",
                payload={},
                cpu_limit="abc"
            )
        assert "cpu_limit" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()

    def test_cpu_limit_invalid_format_with_unit(self):
        """JobCreate with cpu_limit='2c' should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                task_type="script",
                runtime="python",
                payload={},
                cpu_limit="2c"
            )
        assert "cpu_limit" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()


class TestJobResponseLimitFields:
    """Test that JobResponse includes memory_limit and cpu_limit fields."""

    def test_job_response_has_memory_limit_field(self):
        """JobResponse should have memory_limit field."""
        response = JobResponse(
            guid="test-123",
            status="PENDING",
            payload={},
            memory_limit="512m"
        )
        assert response.memory_limit == "512m"
        assert "memory_limit" in response.model_dump()

    def test_job_response_has_cpu_limit_field(self):
        """JobResponse should have cpu_limit field."""
        response = JobResponse(
            guid="test-123",
            status="PENDING",
            payload={},
            cpu_limit="2"
        )
        assert response.cpu_limit == "2"
        assert "cpu_limit" in response.model_dump()

    def test_job_response_limits_serialization(self):
        """JobResponse with limits should serialize to JSON correctly."""
        response = JobResponse(
            guid="test-123",
            status="PENDING",
            payload={},
            memory_limit="512m",
            cpu_limit="2"
        )
        json_data = response.model_dump()
        assert json_data["memory_limit"] == "512m"
        assert json_data["cpu_limit"] == "2"


class TestWorkResponseLimitFields:
    """Test that WorkResponse includes memory_limit and cpu_limit fields."""

    def test_work_response_has_memory_limit_field(self):
        """WorkResponse should have memory_limit field."""
        response = WorkResponse(
            guid="test-123",
            task_type="script",
            payload={},
            memory_limit="512m"
        )
        assert response.memory_limit == "512m"

    def test_work_response_has_cpu_limit_field(self):
        """WorkResponse should have cpu_limit field."""
        response = WorkResponse(
            guid="test-123",
            task_type="script",
            payload={},
            cpu_limit="2"
        )
        assert response.cpu_limit == "2"

    def test_work_response_limits_in_dump(self):
        """WorkResponse limits should appear in model_dump()."""
        response = WorkResponse(
            guid="test-123",
            task_type="script",
            payload={},
            memory_limit="512m",
            cpu_limit="2"
        )
        data = response.model_dump()
        assert "memory_limit" in data
        assert "cpu_limit" in data
        assert data["memory_limit"] == "512m"
        assert data["cpu_limit"] == "2"


@pytest.mark.asyncio
class TestJobDBPersistence:
    """Test that Job limits persist to database."""

    async def test_job_limits_persist_to_db(self):
        """
        Create a Job with memory_limit and cpu_limit, commit to test DB,
        retrieve it, and verify limits are preserved.

        Requires: AsyncSessionLocal fixture and DB columns to exist.
        """
        from uuid import uuid4

        job_guid = str(uuid4())

        async with AsyncSessionLocal() as session:
            # Create job with limits
            job = Job(
                guid=job_guid,
                task_type="script",
                payload=json.dumps({}),
                status="PENDING",
                memory_limit="512m",
                cpu_limit="2"
            )
            session.add(job)
            await session.commit()

            # Retrieve job
            from sqlalchemy import select
            stmt = select(Job).where(Job.guid == job_guid)
            result = await session.execute(stmt)
            retrieved_job = result.scalar_one()

            # Verify limits are preserved
            assert retrieved_job.memory_limit == "512m"
            assert retrieved_job.cpu_limit == "2"

    async def test_backward_compatibility_old_jobs_no_limits(self):
        """
        Legacy jobs without limits should still be queryable,
        with limits returning None.

        Tests backward compatibility when columns are nullable.
        """
        from uuid import uuid4

        job_guid = str(uuid4())

        async with AsyncSessionLocal() as session:
            # Create job without limits (legacy behavior)
            job = Job(
                guid=job_guid,
                task_type="script",
                payload=json.dumps({}),
                status="PENDING"
                # No memory_limit or cpu_limit
            )
            session.add(job)
            await session.commit()

            # Retrieve job
            from sqlalchemy import select
            stmt = select(Job).where(Job.guid == job_guid)
            result = await session.execute(stmt)
            retrieved_job = result.scalar_one()

            # Verify limits are None (not missing)
            assert retrieved_job.memory_limit is None
            assert retrieved_job.cpu_limit is None
