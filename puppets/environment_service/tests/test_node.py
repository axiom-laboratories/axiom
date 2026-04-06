import pytest
import asyncio
import json
import os
import base64
from unittest.mock import patch, MagicMock, AsyncMock
from puppets.environment_service.node import Node

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_node_env(tmp_path):
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    
    with patch("puppets.environment_service.node.Node.bootstrap_trust"), \
         patch("puppets.environment_service.node.Node.ensure_identity"), \
         patch("puppets.environment_service.node.Node.fetch_verification_key"), \
         patch("puppets.environment_service.node.os.makedirs"):
         
        node = Node("https://localhost:8001", "test-node")
        node.cert_file = str(secrets_dir / "node.crt")
        node.key_file = str(secrets_dir / "node.key")
        node.verify_key_path = str(secrets_dir / "verification.key")
        node.join_token = "dummy-token"
        
        # Identity files
        with open(node.cert_file, "w") as f: f.write("CERT")
        with open(node.key_file, "w") as f: f.write("KEY")
        
        return node

@pytest.mark.anyio
async def test_poll_for_work(mock_node_env):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"job": {"guid": "job1"}}
    
    # Mock AsyncClient as a context manager
    with patch("puppets.environment_service.node.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_resp
        mock_client_class.return_value = mock_client
        
        work = await mock_node_env.poll_for_work()
        assert work["job"]["guid"] == "job1"

@pytest.mark.anyio
async def test_report_result(mock_node_env):
    with patch("puppets.environment_service.node.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock()
        mock_client_class.return_value = mock_client
        
        await mock_node_env.report_result("job1", True, {"out": "ok"})
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert "/work/job1/result" in args[0]
        assert kwargs["json"]["success"] is True

def test_run_python_script_local(mock_node_env):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="")
        res = mock_node_env.run_python_script("job1", "print('hello')")
        assert res["exit_code"] == 0
        assert res["stdout"] == "hello"

def test_bootstrap_trust_logic(tmp_path):
    # Testing the logic of bootstrap_trust directly
    ca_content = "-----BEGIN CERTIFICATE-----\nABC\n-----END CERTIFICATE-----"
    token_dict = {"t": "real-token", "ca": ca_content}
    encoded = base64.b64encode(json.dumps(token_dict).encode()).decode()

    with patch("puppets.environment_service.node.Node.ensure_identity"), \
         patch("puppets.environment_service.node.Node.fetch_verification_key"):

        node = Node("url", "nodeid")
        node.join_token = encoded

        # Point secrets/root_ca.crt to a tmp path by mocking open for that specific file
        # or just let it write if we are in a safe env, but better mock it.
        with patch("puppets.environment_service.node.open", create=True) as mock_open:
            node.bootstrap_trust()
            assert node.join_token == "real-token"
            # Verify CA content was saved
            # mock_open(root_ca_dest, "w")
            # We can check calls


# Test parse_bytes with valid inputs
def test_parse_bytes_valid():
    """parse_bytes converts memory strings correctly."""
    from puppets.environment_service.node import parse_bytes
    assert parse_bytes("512m") == 512 * 1024 ** 2
    assert parse_bytes("1g") == 1024 ** 3
    assert parse_bytes("256k") == 256 * 1024
    assert parse_bytes("1024") == 1024
    assert parse_bytes("2G") == 2 * 1024 ** 3  # uppercase


# Test parse_bytes with invalid inputs
def test_parse_bytes_invalid():
    """parse_bytes raises on invalid format."""
    from puppets.environment_service.node import parse_bytes
    with pytest.raises((ValueError, KeyError)):
        parse_bytes("10x")
    with pytest.raises((ValueError, KeyError)):
        parse_bytes("hello")
    with pytest.raises((ValueError, KeyError)):
        parse_bytes("")


# Test parse_cpu with valid inputs
def test_parse_cpu_valid():
    """parse_cpu converts CPU strings correctly."""
    from puppets.environment_service.node import parse_cpu
    assert parse_cpu("2") == 2.0
    assert parse_cpu("0.5") == 0.5
    assert parse_cpu("1.0") == 1.0
    assert parse_cpu("  0.25  ") == 0.25


# Test parse_cpu with invalid inputs
def test_parse_cpu_invalid():
    """parse_cpu raises on invalid format."""
    from puppets.environment_service.node import parse_cpu
    with pytest.raises(ValueError):
        parse_cpu("fast")
    with pytest.raises(ValueError):
        parse_cpu("abc")
    with pytest.raises(ValueError):
        parse_cpu("")
    with pytest.raises(ValueError):
        parse_cpu("1.2.3")


# Test execute_task with invalid memory_limit
@pytest.mark.anyio
async def test_execute_task_invalid_memory_format(mock_node_env):
    """execute_task fails job if memory_limit format is invalid."""
    job = {
        "guid": "job-123",
        "task_type": "script",
        "memory_limit": "10x",  # invalid
        "cpu_limit": None,
        "payload": {
            "runtime": "python",
            "script_content": "print('hello')",
            "signature_payload": "base64sig"
        }
    }

    with patch("puppets.environment_service.node.Node.report_result", new_callable=AsyncMock) as mock_report:
        await mock_node_env.execute_task(job)
        mock_report.assert_called_once()
        args, kwargs = mock_report.call_args
        assert args[0] == "job-123"  # guid
        assert args[1] is False  # success = False
        assert "Invalid memory_limit format" in args[2]["error"]
        assert args[2]["value"] == "10x"


# Test execute_task with invalid cpu_limit
@pytest.mark.anyio
async def test_execute_task_invalid_cpu_format(mock_node_env):
    """execute_task fails job if cpu_limit format is invalid."""
    job = {
        "guid": "job-456",
        "task_type": "script",
        "memory_limit": "512m",  # valid
        "cpu_limit": "invalid",  # invalid
        "payload": {
            "runtime": "python",
            "script_content": "print('hello')",
            "signature_payload": "base64sig"
        }
    }

    with patch("puppets.environment_service.node.Node.report_result", new_callable=AsyncMock) as mock_report:
        await mock_node_env.execute_task(job)
        mock_report.assert_called_once()
        args, kwargs = mock_report.call_args
        assert args[0] == "job-456"  # guid
        assert args[1] is False  # success = False
        assert "Invalid cpu_limit format" in args[2]["error"]
        assert args[2]["value"] == "invalid"


# Test execute_task logs limit extraction
@pytest.mark.anyio
async def test_execute_task_logs_limits(mock_node_env):
    """execute_task logs successful limit extraction at job start."""
    job = {
        "guid": "job-789",
        "task_type": "script",
        "memory_limit": "512m",
        "cpu_limit": "1.0",
        "payload": {
            "runtime": "python",
            "script_content": "print('hello')",
            "signature_payload": "base64sig"
        }
    }

    # Mock report_result to prevent actual execution
    with patch("puppets.environment_service.node.Node.report_result", new_callable=AsyncMock):
        # We'll check that logger.info is called (format validation logs)
        with patch("puppets.environment_service.node.logger") as mock_logger:
            # This will fail during signature check, but that's ok — we're testing the log was called
            try:
                await mock_node_env.execute_task(job)
            except:
                pass
            # Verify logger.info was called with limit info
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("memory_limit=512m" in str(call) for call in log_calls)
