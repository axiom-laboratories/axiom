"""
Phase 51 — Wave 0 test stubs: Bulk job operations (BULK-02, BULK-03, BULK-04).

These tests define the contract for Plan 03 implementation.
All stubs fail immediately with pytest.fail("not implemented").

Endpoint contracts:
  POST /jobs/bulk-cancel
    - Body: {"guids": [...]}
    - Returns {processed: N, skipped: M} where skipped = jobs not in cancellable state
    - Only PENDING and RUNNING jobs can be cancelled; terminal states are skipped

  POST /jobs/bulk-resubmit
    - Body: {"guids": [...]}
    - Resubmits each FAILED/DEAD_LETTER job; returns list of new job guids
    - Each new job has originating_guid set to its source guid

  DELETE /jobs/bulk
    - Body: {"guids": [...]}
    - Deletes only terminal-state jobs (COMPLETED, FAILED, CANCELLED, DEAD_LETTER, SECURITY_REJECTED)
    - Returns {deleted: N, skipped: [...guids...]} for non-terminal jobs
"""
import pytest


@pytest.mark.anyio
async def test_bulk_cancel_pending(db_session):
    """POST /jobs/bulk-cancel with PENDING job guids must return {processed: N, skipped: 0}.

    Setup:
      - Create N PENDING jobs
    Assert:
      - Response status 200
      - Response body: {processed: N, skipped: 0}
      - Each job has status == 'CANCELLED' afterwards
    """
    pytest.fail("not implemented")


@pytest.mark.anyio
async def test_bulk_cancel_skips_terminal(db_session):
    """POST /jobs/bulk-cancel with a mix of PENDING + COMPLETED must skip the COMPLETED ones.

    Setup:
      - Create 2 PENDING jobs and 1 COMPLETED job
      - Submit all 3 guids to bulk-cancel
    Assert:
      - Response status 200
      - Response body: {processed: 2, skipped: 1}
      - The COMPLETED job's status is unchanged
    """
    pytest.fail("not implemented")


@pytest.mark.anyio
async def test_bulk_resubmit_creates_new_jobs(db_session):
    """POST /jobs/bulk-resubmit must create N new jobs with originating_guids set.

    Setup:
      - Create 2 FAILED jobs and 1 COMPLETED job
      - Submit all 3 guids to bulk-resubmit
    Assert:
      - Response status 200
      - 2 new jobs are created (one per FAILED job)
      - Each new job has originating_guid == the corresponding source job guid
      - The COMPLETED job is skipped (not resubmitted)
      - Response body contains the list of new guids (or processed/skipped counts)
    """
    pytest.fail("not implemented")


@pytest.mark.anyio
async def test_bulk_delete_terminal_only(db_session):
    """DELETE /jobs/bulk must delete only terminal-state jobs and skip non-terminal ones.

    Setup:
      - Create 1 COMPLETED job, 1 FAILED job, 1 PENDING job
      - Submit all 3 guids to bulk delete
    Assert:
      - Response status 200
      - Response body: {deleted: 2, skipped: [<pending_guid>]}
      - COMPLETED and FAILED jobs are removed from DB
      - PENDING job remains in DB with status == 'PENDING'
    """
    pytest.fail("not implemented")
