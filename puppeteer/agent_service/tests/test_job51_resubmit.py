"""
Phase 51 — Wave 0 test stubs: Job resubmit endpoint (JOB-05).

These tests define the contract for Plan 02 implementation.
All stubs fail immediately with pytest.fail("not implemented").

Endpoint contract:
  POST /jobs/{guid}/resubmit
    - Returns 200 + new job JSON when source job is FAILED or DEAD_LETTER
    - Returns 409 when source job is in a non-resubmittable state (PENDING, RUNNING, COMPLETED, CANCELLED)
    - New job gets a fresh guid, status=PENDING, retry_count=0
    - New job has originating_guid == source job guid
"""
import pytest


@pytest.mark.anyio
async def test_resubmit_creates_new_guid(db_session):
    """POST /jobs/{guid}/resubmit on a FAILED job must return 200 with a NEW guid.

    Setup:
      - Create a job with status=FAILED
    Assert:
      - Response status 200
      - Response body contains a 'guid' field
      - The new guid is different from the original job guid
      - The new job's originating_guid equals the original job guid
    """
    pytest.fail("not implemented")


@pytest.mark.anyio
async def test_resubmit_sets_pending(db_session):
    """POST /jobs/{guid}/resubmit must create a new job with status=PENDING and retry_count=0.

    Setup:
      - Create a job with status=FAILED, retry_count=3
    Assert:
      - The new job has status == 'PENDING'
      - The new job has retry_count == 0
      - The new job inherits task_type, payload, and target_tags from the original
    """
    pytest.fail("not implemented")


@pytest.mark.anyio
async def test_resubmit_rejects_non_failed(db_session):
    """POST /jobs/{guid}/resubmit on a PENDING or COMPLETED job must return 409.

    Setup:
      - Create a job with status=PENDING
    Assert:
      - Response status 409

    Also check for status=COMPLETED:
      - Response status 409

    Rationale: only terminal error states (FAILED, DEAD_LETTER) are resubmittable.
    Active or successfully completed jobs must not be resubmitted.
    """
    pytest.fail("not implemented")


@pytest.mark.anyio
async def test_resubmit_dead_letter_allowed(db_session):
    """POST /jobs/{guid}/resubmit on a DEAD_LETTER job must return 200.

    Setup:
      - Create a job with status=DEAD_LETTER
    Assert:
      - Response status 200
      - New job created with originating_guid set to source job guid
      - New job has status=PENDING
    """
    pytest.fail("not implemented")
