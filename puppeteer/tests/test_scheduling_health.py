import pytest


def test_health_aggregate():
    """
    Future shape: given scheduled fire logs for 3 definitions across a 24h window,
    health endpoint returns aggregate {fired, skipped, failed} totals + per-definition rows.
    """
    pytest.fail('not implemented')


def test_missed_fire_detection():
    """
    Future shape: given a ScheduledFireLog row with no matching ExecutionRecord within
    5-min grace, the health endpoint classifies it as LATE then MISSED after next scheduled
    fire time.
    """
    pytest.fail('not implemented')
