"""
TDD tests for Task 1: build_output_log helper and extended report_result.
RED phase: These tests will fail until build_output_log is implemented.
"""
import pytest
import re
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_build_output_log_normal():
    """build_output_log splits stdout/stderr into per-line dicts."""
    from node import build_output_log
    lines = build_output_log('hello\nworld\n', 'error line\n')
    assert len(lines) == 3
    assert lines[0]['stream'] == 'stdout'
    assert lines[0]['line'] == 'hello'
    assert lines[1]['stream'] == 'stdout'
    assert lines[1]['line'] == 'world'
    assert lines[2]['stream'] == 'stderr'
    assert lines[2]['line'] == 'error line'


def test_build_output_log_empty():
    """Empty strings produce empty list."""
    from node import build_output_log
    assert build_output_log('', '') == []


def test_build_output_log_whitespace_filtered():
    """Whitespace-only lines are excluded; non-empty lines preserved."""
    from node import build_output_log
    lines = build_output_log('  \n  real  \n', '')
    assert len(lines) == 1
    assert lines[0]['line'] == '  real  '


def test_build_output_log_timestamp_format():
    """Each entry has a 't' key with ISO datetime format."""
    from node import build_output_log
    lines = build_output_log('hello', 'err')
    assert len(lines) == 2
    assert re.match(r'\d{4}-\d{2}-\d{2}T', lines[0]['t'])
    assert re.match(r'\d{4}-\d{2}-\d{2}T', lines[1]['t'])


def test_build_output_log_keys():
    """Each entry has exactly the keys t, stream, line."""
    from node import build_output_log
    lines = build_output_log('foo', '')
    assert set(lines[0].keys()) == {'t', 'stream', 'line'}


@pytest.mark.asyncio
async def test_report_result_extended_fields():
    """report_result() POST body includes output_log, exit_code, security_rejected."""
    with patch("node.Node.bootstrap_trust"), \
         patch("node.Node.ensure_identity"), \
         patch("node.os.makedirs"):
        from node import Node
        node = Node("https://localhost:8001", "test-node")
        node.cert_file = "secrets/test.crt"
        node.key_file = "secrets/test.key"

    captured_json = {}

    async def fake_post(url, json=None, headers=None, **kwargs):
        captured_json.update(json or {})
        resp = MagicMock()
        resp.status_code = 200
        return resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=fake_post)

    with patch("node.httpx.AsyncClient", return_value=mock_client):
        await node.report_result(
            "guid-123", True, {"exit_code": 0},
            output_log=[{"t": "2026-01-01T00:00:00", "stream": "stdout", "line": "hi"}],
            exit_code=0,
            security_rejected=False
        )

    assert "output_log" in captured_json
    assert "exit_code" in captured_json
    assert "security_rejected" in captured_json
    assert captured_json["exit_code"] == 0
    assert captured_json["security_rejected"] is False


@pytest.mark.asyncio
async def test_report_result_security_rejected_flag():
    """security_rejected=True is forwarded in POST body."""
    with patch("node.Node.bootstrap_trust"), \
         patch("node.Node.ensure_identity"), \
         patch("node.os.makedirs"):
        from node import Node
        node = Node("https://localhost:8001", "test-node")
        node.cert_file = "secrets/test.crt"
        node.key_file = "secrets/test.key"

    captured_json = {}

    async def fake_post(url, json=None, headers=None, **kwargs):
        captured_json.update(json or {})
        resp = MagicMock()
        resp.status_code = 200
        return resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=fake_post)

    with patch("node.httpx.AsyncClient", return_value=mock_client):
        await node.report_result("guid-456", False, {"error": "Signature Verification Failed"},
                                 security_rejected=True)

    assert captured_json["security_rejected"] is True
    assert captured_json["success"] is False
