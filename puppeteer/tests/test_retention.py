import pytest


def test_pruner_respects_pinned():
    """
    Future shape: given 2 expired ExecutionRecords (one pinned, one not),
    pruner deletes only the unpinned one.
    """
    pytest.fail('not implemented')


def test_pin_unpin():
    """
    Future shape: PATCH /executions/{id}/pin sets pinned=True and writes an audit log entry;
    PATCH /executions/{id}/unpin sets pinned=False and writes audit log.
    """
    pytest.fail('not implemented')
