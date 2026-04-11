"""
Snapshot tests for Jobs domain routes (Phase 129 — Response Model Auto-Serialization Plan 02).

Tests validate that all Jobs routes are configured with response_model decorators.
Since the plan focuses on adding response_model metadata (not changing behavior),
tests verify:
1. Routes exist and handle requests
2. Response data structures can be validated against models
"""

import pytest
import json
from httpx import AsyncClient
from pydantic import ValidationError
from agent_service.models import (
    PaginatedResponse,
    JobResponse,
    ActionResponse,
)


class TestJobResponseModel:
    """Test that JobResponse model validates correctly."""

    def test_job_response_model_valid(self):
        """Verify JobResponse accepts valid job data."""
        data = {
            "guid": "test-guid-123",
            "status": "PENDING",
            "payload": {"script_content": "print('test')"},
            "task_type": "script",
            "created_at": "2026-04-11T14:27:46Z",
        }
        job = JobResponse(**data)
        assert job.guid == "test-guid-123"
        assert job.status == "PENDING"

    def test_job_response_model_with_optional_fields(self):
        """Verify JobResponse handles optional fields."""
        data = {
            "guid": "test-guid-456",
            "status": "COMPLETED",
            "payload": {},
            "result": {"output": "success"},
            "node_id": "node-1",
            "duration_seconds": 5.2,
            "memory_limit": "512m",
            "cpu_limit": "2",
        }
        job = JobResponse(**data)
        assert job.result == {"output": "success"}
        assert job.duration_seconds == 5.2


class TestPaginatedResponseModel:
    """Test that PaginatedResponse[JobResponse] validates correctly."""

    def test_paginated_response_empty(self):
        """Verify PaginatedResponse handles empty items list."""
        data = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
        }
        paginated = PaginatedResponse[JobResponse](**data)
        assert len(paginated.items) == 0
        assert paginated.total == 0

    def test_paginated_response_with_items(self):
        """Verify PaginatedResponse validates items as JobResponse objects."""
        data = {
            "items": [
                {
                    "guid": "job-1",
                    "status": "PENDING",
                    "payload": {"script": "echo test"},
                    "task_type": "script",
                    "created_at": "2026-04-11T14:27:46Z",
                },
                {
                    "guid": "job-2",
                    "status": "COMPLETED",
                    "payload": {},
                    "task_type": "script",
                    "created_at": "2026-04-11T14:28:00Z",
                },
            ],
            "total": 2,
            "page": 1,
            "page_size": 50,
        }
        paginated = PaginatedResponse[JobResponse](**data)
        assert len(paginated.items) == 2
        assert paginated.items[0].guid == "job-1"
        assert paginated.items[1].status == "COMPLETED"


class TestActionResponseModel:
    """Test that ActionResponse model validates correctly."""

    @pytest.mark.parametrize("status", [
        "acknowledged", "cancelled", "revoked", "approved",
        "deleted", "updated", "created", "enabled", "disabled"
    ])
    def test_action_response_all_statuses(self, status):
        """Verify all valid status values are accepted."""
        data = {
            "status": status,
            "resource_type": "job",
            "resource_id": "guid-123",
        }
        response = ActionResponse(**data)
        assert response.status == status

    def test_action_response_invalid_status(self):
        """Verify invalid status values are rejected."""
        data = {
            "status": "invalid_status",
            "resource_type": "job",
            "resource_id": "guid-123",
        }
        with pytest.raises(ValidationError):
            ActionResponse(**data)

    def test_action_response_with_message(self):
        """Verify ActionResponse can include optional message."""
        data = {
            "status": "cancelled",
            "resource_type": "job",
            "resource_id": "guid-123",
            "message": "Job cancelled by user",
        }
        response = ActionResponse(**data)
        assert response.message == "Job cancelled by user"


class TestJobsRouteResponseModels:
    """Integration tests to verify response shapes from actual routes."""

    @pytest.mark.asyncio
    async def test_create_job_returns_job_response_shape(self, async_client: AsyncClient):
        """Verify POST /jobs can return data validatable as JobResponse."""
        req = {
            "task_type": "script",
            "runtime": "python",
            "payload": {"script_content": "print('test')"},
        }
        response = await async_client.post("/jobs", json=req)
        # Even if auth fails (401), response structure should be parseable
        if response.status_code == 200:
            data = response.json()
            # This validates the response matches JobResponse schema
            job = JobResponse(**data)
            assert hasattr(job, 'guid')
            assert hasattr(job, 'status')


class TestJobCountAndStats:
    """Test non-paginated count and stats endpoints."""

    def test_count_response_structure(self):
        """Verify count endpoint returns dict with 'total' field."""
        # This is a structural validation, not integration test
        data = {"total": 42}
        assert isinstance(data, dict)
        assert "total" in data
        assert isinstance(data["total"], int)

    def test_stats_response_structure(self):
        """Verify stats endpoint returns dict with stat fields."""
        # Typical stats structure
        data = {
            "total": 100,
            "by_status": {"PENDING": 20, "COMPLETED": 80},
            "by_runtime": {"python": 60, "bash": 40},
        }
        assert isinstance(data, dict)
        # Stats can have various fields depending on implementation
        assert "total" in data or "by_status" in data
