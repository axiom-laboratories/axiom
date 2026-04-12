"""
Integration tests for non-root user (appuser) verification.

Tests verify that container processes run as UID 1000 (appuser) and that
/app directory and /app/secrets volume are owned by appuser:appuser.

Requirements verified: CONT-01 (non-root user), CONT-06 (secrets volume ownership)
"""

import subprocess
import pytest


def get_container_id(service_name):
    """
    Get the container ID for a service by querying docker ps.

    Args:
        service_name: Name of the container (e.g., 'puppeteer-agent-1')

    Returns:
        Container ID as string

    Raises:
        RuntimeError: If container is not running
    """
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={service_name}', '-q'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        container_id = result.stdout.strip()
        if not container_id:
            raise RuntimeError(f"Container '{service_name}' not running")
        return container_id
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout getting container ID for {service_name}")


@pytest.fixture
def agent_container_id():
    """Fixture: Get agent container ID."""
    return get_container_id('puppeteer-agent-1')


@pytest.fixture
def model_container_id():
    """Fixture: Get model container ID."""
    return get_container_id('puppeteer-model-1')


@pytest.fixture
def node_container_id():
    """Fixture: Get node container ID (looks for 'node' prefix)."""
    try:
        # Try 'node' first, then 'node-1' pattern
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=node', '-q'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        container_ids = result.stdout.strip().split('\n')
        if not container_ids or not container_ids[0]:
            raise RuntimeError("Node container not running")
        # Return the first match (may be 'node' or 'node-1' depending on compose setup)
        return container_ids[0]
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout getting node container ID")


def test_agent_process_uid(agent_container_id):
    """
    CONT-01: Verify agent process runs as UID 1000.

    Checks that the current user in the agent container is UID 1000.
    Uses 'id' command which is more portable than 'ps'.
    """
    result = subprocess.run(
        ['docker', 'exec', agent_container_id, 'id', '-u'],
        capture_output=True,
        text=True,
        check=True,
        timeout=10
    )

    uid = result.stdout.strip()
    assert uid == '1000', f"Expected agent uid 1000, got {uid}"


def test_model_process_uid(model_container_id):
    """
    CONT-01: Verify model process runs as UID 1000.

    Checks that the current user in the model container is UID 1000.
    Uses 'id' command which is more portable than 'ps'.
    """
    result = subprocess.run(
        ['docker', 'exec', model_container_id, 'id', '-u'],
        capture_output=True,
        text=True,
        check=True,
        timeout=10
    )

    uid = result.stdout.strip()
    assert uid == '1000', f"Expected model uid 1000, got {uid}"


def test_node_process_uid(node_container_id):
    """
    CONT-01: Verify node process runs as UID 1000.

    Checks that the current user in the node container is UID 1000.
    Uses 'id' command which is more portable than 'ps'.
    """
    result = subprocess.run(
        ['docker', 'exec', node_container_id, 'id', '-u'],
        capture_output=True,
        text=True,
        check=True,
        timeout=10
    )

    uid = result.stdout.strip()
    assert uid == '1000', f"Expected node uid 1000, got {uid}"


def test_agent_app_ownership(agent_container_id):
    """
    CONT-01: Verify /app directory in agent is owned by appuser:appuser.

    Checks that stat -c %U:%G /app returns 'appuser:appuser'.
    """
    result = subprocess.run(
        ['docker', 'exec', agent_container_id, 'stat', '-c', '%U:%G', '/app'],
        capture_output=True,
        text=True,
        check=True,
        timeout=10
    )

    ownership = result.stdout.strip()
    assert ownership == 'appuser:appuser', \
        f"Expected agent /app owned by appuser:appuser, got {ownership}"


def test_model_app_ownership(model_container_id):
    """
    CONT-01: Verify /app directory in model is owned by appuser:appuser.

    Checks that stat -c %U:%G /app returns 'appuser:appuser'.
    """
    result = subprocess.run(
        ['docker', 'exec', model_container_id, 'stat', '-c', '%U:%G', '/app'],
        capture_output=True,
        text=True,
        check=True,
        timeout=10
    )

    ownership = result.stdout.strip()
    assert ownership == 'appuser:appuser', \
        f"Expected model /app owned by appuser:appuser, got {ownership}"


def test_node_app_ownership(node_container_id):
    """
    CONT-01: Verify /app directory in node is owned by appuser:appuser.

    Checks that stat -c %U:%G /app returns 'appuser:appuser'.
    """
    result = subprocess.run(
        ['docker', 'exec', node_container_id, 'stat', '-c', '%U:%G', '/app'],
        capture_output=True,
        text=True,
        check=True,
        timeout=10
    )

    ownership = result.stdout.strip()
    assert ownership == 'appuser:appuser', \
        f"Expected node /app owned by appuser:appuser, got {ownership}"


def test_secrets_volume_ownership(agent_container_id):
    """
    CONT-06: Verify /app/secrets volume in agent is owned by appuser:appuser.

    Checks that stat -c %U:%G /app/secrets returns 'appuser:appuser'.
    """
    result = subprocess.run(
        ['docker', 'exec', agent_container_id, 'stat', '-c', '%U:%G', '/app/secrets'],
        capture_output=True,
        text=True,
        check=True,
        timeout=10
    )

    ownership = result.stdout.strip()
    assert ownership == 'appuser:appuser', \
        f"Expected agent /app/secrets owned by appuser:appuser, got {ownership}"


def test_volume_write_access(agent_container_id):
    """
    CONT-06: Verify /app/secrets volume is writable by appuser.

    Creates and deletes a test file in /app/secrets via docker exec.
    Confirms appuser can write to the volume at runtime.
    """
    test_file = '/app/secrets/test_write_verify.txt'
    test_content = 'test write access verification'

    # Write test file
    result = subprocess.run(
        ['docker', 'exec', agent_container_id, 'sh', '-c',
         f'echo "{test_content}" > {test_file}'],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        raise AssertionError(
            f"Failed to write test file to /app/secrets: {result.stderr}"
        )

    # Verify file was created
    result = subprocess.run(
        ['docker', 'exec', agent_container_id, 'test', '-f', test_file],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        raise AssertionError("Test file was not created in /app/secrets")

    # Delete test file
    result = subprocess.run(
        ['docker', 'exec', agent_container_id, 'rm', test_file],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        raise AssertionError(
            f"Failed to delete test file from /app/secrets: {result.stderr}"
        )
