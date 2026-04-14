"""
Security capabilities tests for Phase 133.

Tests verify that:
- CONT-03: cap_drop: ALL and security_opt: no-new-privileges:true on all services
- CONT-04: Postgres port binding restricted to 127.0.0.1:5432

Tests include both static YAML parsing and live container inspection.

Requirements verified: CONT-03, CONT-04
"""

import yaml
import json
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
def db_container_id():
    """Fixture: Get db container ID."""
    return get_container_id('puppeteer-db-1')


class TestStaticYAMLCapabilities:
    """Static YAML parsing tests — no Docker required."""

    def test_cap_drop_all_on_all_services(self):
        """CONT-03: Verify cap_drop: ALL in compose.server.yaml."""
        with open('compose.server.yaml', 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})
        assert len(services) > 0, "No services found in compose file"

        for service_name, config in services.items():
            cap_drop = config.get('cap_drop', [])
            # For Caddy: cap_drop: ALL + cap_add: NET_BIND_SERVICE is OK (exception case)
            # For all others: must have cap_drop: ALL
            if service_name == 'cert-manager' and config.get('cap_add'):
                # Exception: cert-manager/caddy adds back NET_BIND_SERVICE
                continue
            assert 'ALL' in cap_drop, \
                f"Service '{service_name}' missing cap_drop: ALL, got {cap_drop}"

    def test_security_opt_no_new_privileges(self):
        """CONT-03: Verify security_opt: no-new-privileges:true on all services."""
        with open('compose.server.yaml', 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})
        assert len(services) > 0, "No services found in compose file"

        for service_name, config in services.items():
            security_opt = config.get('security_opt', [])
            assert 'no-new-privileges:true' in security_opt, \
                f"Service '{service_name}' missing security_opt: no-new-privileges:true, got {security_opt}"

    def test_postgres_loopback_binding(self):
        """CONT-04: Verify Postgres port binding restricted to 127.0.0.1:5432."""
        with open('compose.server.yaml', 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})
        db_service = services.get('db')
        assert db_service is not None, "db service not found in compose file"

        ports = db_service.get('ports', [])
        assert len(ports) > 0, "db service has no port bindings"

        # Should contain loopback-only binding like "127.0.0.1:5432:5432"
        loopback_bindings = [p for p in ports if '127.0.0.1:5432' in str(p)]
        assert len(loopback_bindings) > 0, \
            f"Postgres not bound to 127.0.0.1:5432, got ports: {ports}"

    def test_caddy_has_net_bind_service(self):
        """CONT-03: Verify cert-manager/caddy has NET_BIND_SERVICE exception."""
        with open('compose.server.yaml', 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})
        caddy_service = services.get('cert-manager')
        assert caddy_service is not None, "cert-manager service not found"

        cap_drop = caddy_service.get('cap_drop', [])
        cap_add = caddy_service.get('cap_add', [])

        assert 'ALL' in cap_drop, "cert-manager missing cap_drop: ALL"
        assert 'NET_BIND_SERVICE' in cap_add, \
            f"cert-manager missing cap_add: NET_BIND_SERVICE, got {cap_add}"


class TestLiveContainerCapabilities:
    """Live container inspection tests — requires running stack."""

    def test_agent_cap_drop_enforced(self, agent_container_id):
        """CONT-03: Verify cap_drop actually enforced in running agent container."""
        result = subprocess.run(
            ['docker', 'inspect', agent_container_id],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        config = json.loads(result.stdout)[0]  # docker inspect returns array
        cap_drop = config['HostConfig'].get('CapDrop', [])

        assert 'ALL' in cap_drop, \
            f"Agent CapDrop not set to ALL: {cap_drop}"

    def test_agent_no_new_privileges_enforced(self, agent_container_id):
        """CONT-03: Verify no-new-privileges enforced in running agent container."""
        result = subprocess.run(
            ['docker', 'inspect', agent_container_id],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        config = json.loads(result.stdout)[0]
        security_opt = config['HostConfig'].get('SecurityOpt', [])

        assert any('no-new-privileges' in opt for opt in security_opt), \
            f"Agent SecurityOpt missing no-new-privileges: {security_opt}"

    def test_postgres_not_publicly_accessible(self, db_container_id):
        """CONT-04: Verify Postgres not exposed on public interfaces."""
        result = subprocess.run(
            ['docker', 'inspect', db_container_id],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        config = json.loads(result.stdout)[0]
        port_bindings = config['HostConfig'].get('PortBindings', {})

        # Should not have any 0.0.0.0 or :: (IPv6) bindings for port 5432
        for port_spec, bindings in port_bindings.items():
            if '5432' in port_spec:
                for binding in bindings:
                    host_ip = binding.get('HostIp', '')
                    # Must be 127.0.0.1 or empty (loopback)
                    assert host_ip in ['127.0.0.1', ''], \
                        f"Postgres port {port_spec} bound to {host_ip} (should be 127.0.0.1 only)"
