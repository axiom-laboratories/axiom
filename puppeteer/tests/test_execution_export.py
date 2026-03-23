import pytest


def test_csv_export():
    """
    Future shape: GET /jobs/{guid}/executions/export returns CSV with headers
    job_guid, node_id, status, exit_code, started_at, completed_at, duration_s,
    attempt_number, pinned.
    """
    pytest.fail('not implemented')
