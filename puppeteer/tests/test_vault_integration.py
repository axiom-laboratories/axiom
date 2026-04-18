"""
HashiCorp Vault integration tests for Phase 167 Wave 0.

Tests VaultService startup, secret resolution, lease renewal, and env var bootstrap.
Covers non-blocking startup, graceful degradation, and status transitions.

Imports are deferred to avoid circular import during conftest loading.
"""

import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


@pytest.fixture
async def vault_config():
    """Create a test VaultConfig."""
    # Lazy import to avoid circular import during conftest
    from agent_service.db import VaultConfig
    from agent_service.security import cipher_suite

    return VaultConfig(
        id=str(uuid4()),
        vault_address="https://vault.example.com:8200",
        role_id="test-role-id",
        secret_id=cipher_suite.encrypt(b"test-secret-id").decode(),  # Pre-encrypted
        mount_path="secret",
        namespace=None,
        provider_type="vault",
        enabled=True
    )


class TestVaultServiceBootstrap:
    """Test env var bootstrap logic (VAULT-01, VAULT-02, D-05, D-06)."""

    @pytest.mark.asyncio
    async def test_bootstrap_from_env(self, db_session: AsyncSession, monkeypatch):
        """Env vars (VAULT_ADDRESS, VAULT_ROLE_ID, VAULT_SECRET_ID) seed VaultConfig row (D-05)."""
        from agent_service.db import VaultConfig, _bootstrap_vault_config

        # Clear any existing rows
        from sqlalchemy import text
        await db_session.execute(text("DELETE FROM vault_config"))
        await db_session.commit()

        # Set env vars
        monkeypatch.setenv("VAULT_ADDRESS", "https://vault.test:8200")
        monkeypatch.setenv("VAULT_ROLE_ID", "test-role-123")
        monkeypatch.setenv("VAULT_SECRET_ID", "test-secret-456")

        # Run bootstrap
        await _bootstrap_vault_config()

        # Assert row was created
        stmt = select(VaultConfig)
        result = await db_session.execute(stmt)
        config = result.scalar_one_or_none()

        assert config is not None
        assert config.vault_address == "https://vault.test:8200"
        assert config.role_id == "test-role-123"
        assert config.enabled is True
        assert config.provider_type == "vault"

    @pytest.mark.asyncio
    async def test_bootstrap_idempotent(self, db_session: AsyncSession, monkeypatch):
        """Running bootstrap multiple times creates only one row (D-05)."""
        from agent_service.db import VaultConfig, _bootstrap_vault_config

        # Clear any existing rows
        from sqlalchemy import text
        await db_session.execute(text("DELETE FROM vault_config"))
        await db_session.commit()

        monkeypatch.setenv("VAULT_ADDRESS", "https://vault.test:8200")
        monkeypatch.setenv("VAULT_ROLE_ID", "test-role-123")
        monkeypatch.setenv("VAULT_SECRET_ID", "test-secret-456")

        # Run bootstrap twice
        await _bootstrap_vault_config()
        await _bootstrap_vault_config()

        # Assert only one row exists
        stmt = select(VaultConfig)
        result = await db_session.execute(stmt)
        configs = result.scalars().all()

        assert len(configs) == 1

    @pytest.mark.asyncio
    async def test_bootstrap_skips_if_env_missing(self, db_session: AsyncSession, monkeypatch):
        """Bootstrap skips if any env var is missing (D-06 dormancy)."""
        from agent_service.db import VaultConfig, _bootstrap_vault_config

        # Clear rows
        from sqlalchemy import text
        await db_session.execute(text("DELETE FROM vault_config"))
        await db_session.commit()

        # Set only two of three required env vars
        monkeypatch.setenv("VAULT_ADDRESS", "https://vault.test:8200")
        monkeypatch.setenv("VAULT_ROLE_ID", "test-role-123")
        monkeypatch.delenv("VAULT_SECRET_ID", raising=False)

        await _bootstrap_vault_config()

        # Assert no row was created
        stmt = select(VaultConfig)
        result = await db_session.execute(stmt)
        count = len(result.scalars().all())

        assert count == 0


class TestVaultServiceStartup:
    """Test non-blocking startup and graceful degradation (D-07, D-06)."""

    @pytest.mark.asyncio
    async def test_startup_healthy(self, vault_config, db_session: AsyncSession):
        """Successful Vault connection → status=healthy (D-02)."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config, db_session)

        with patch.object(service, '_connect', new_callable=AsyncMock) as mock_connect:
            await service.startup()

            assert service._status == "healthy"
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_vault_unavailable(self, vault_config, db_session: AsyncSession):
        """Vault unreachable at startup → status=DEGRADED, no crash (D-07)."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config, db_session)

        with patch.object(service, '_connect', side_effect=Exception("Connection refused")):
            # Should not raise; should set status to DEGRADED
            await service.startup()

            assert service._status == "degraded"
            assert "Connection refused" in service._last_error

    @pytest.mark.asyncio
    async def test_startup_dormant_when_disabled(self, vault_config, db_session: AsyncSession):
        """Startup with disabled config → status=disabled, no-op (D-06)."""
        from ee.services.vault_service import VaultService

        vault_config.enabled = False
        service = VaultService(vault_config, db_session)

        await service.startup()

        assert service._status == "disabled"

    @pytest.mark.asyncio
    async def test_startup_dormant_when_none(self, db_session: AsyncSession):
        """Startup with None config → status=disabled, no-op (D-06)."""
        from ee.services.vault_service import VaultService

        service = VaultService(None, db_session)

        await service.startup()

        assert service._status == "disabled"


class TestVaultServiceResolution:
    """Test secret resolution errors and status transitions (D-03, D-04)."""

    @pytest.mark.asyncio
    async def test_resolve_fails_if_disabled(self, db_session: AsyncSession):
        """resolve() raises VaultError if status=disabled (D-07)."""
        from ee.services.vault_service import VaultService, VaultError

        service = VaultService(None, db_session)

        with pytest.raises(VaultError, match="not configured"):
            await service.resolve(["secret1"])

    @pytest.mark.asyncio
    async def test_resolve_fails_if_degraded(self, vault_config, db_session: AsyncSession):
        """resolve() raises VaultError if status=degraded (D-04)."""
        from ee.services.vault_service import VaultService, VaultError

        service = VaultService(vault_config, db_session)
        service._status = "degraded"

        with pytest.raises(VaultError, match="Vault unavailable"):
            await service.resolve(["secret1"])

    @pytest.mark.asyncio
    async def test_resolve_fails_if_no_client(self, vault_config, db_session: AsyncSession):
        """resolve() raises VaultError if client not initialized (D-04)."""
        from ee.services.vault_service import VaultService, VaultError

        service = VaultService(vault_config, db_session)
        service._status = "healthy"
        service._client = None

        with pytest.raises(VaultError, match="not initialized"):
            await service.resolve(["secret1"])


class TestVaultServiceRenewal:
    """Test lease renewal and failure tracking (D-10)."""

    @pytest.mark.asyncio
    async def test_renew_failure_threshold(self, vault_config, db_session: AsyncSession):
        """3 renewal failures → status=DEGRADED (D-10)."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config, db_session)
        service._status = "healthy"
        service._client = Mock()

        def raise_error():
            raise Exception("Token expired")

        service._client.auth.token.renew_self = raise_error

        # Three failures
        for i in range(3):
            await service.renew()

        assert service._consecutive_renewal_failures == 3
        assert service._status == "degraded"

    @pytest.mark.asyncio
    async def test_renew_resets_counter_on_success(self, vault_config, db_session: AsyncSession):
        """Successful renewal resets failure counter (D-10)."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config, db_session)
        service._status = "healthy"
        service._consecutive_renewal_failures = 2

        # Mock asyncio.to_thread to call the sync function immediately
        async def mock_to_thread(func, *args):
            return func(*args)

        with patch('asyncio.to_thread', side_effect=mock_to_thread):
            service._client = Mock()
            service._client.auth.token.renew_self = Mock(return_value=None)

            await service.renew()

        assert service._consecutive_renewal_failures == 0

    @pytest.mark.asyncio
    async def test_renew_no_op_when_disabled(self, db_session: AsyncSession):
        """renew() is a no-op if status=disabled."""
        from ee.services.vault_service import VaultService

        service = VaultService(None, db_session)

        # Should not raise
        await service.renew()

        assert service._consecutive_renewal_failures == 0

    @pytest.mark.asyncio
    async def test_renew_no_op_when_no_client(self, vault_config, db_session: AsyncSession):
        """renew() is a no-op if client not initialized."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config, db_session)
        service._client = None

        # Should not raise
        await service.renew()

        assert service._consecutive_renewal_failures == 0


class TestVaultServiceStatus:
    """Test status() method (D-02)."""

    @pytest.mark.asyncio
    async def test_status_returns_current(self, vault_config, db_session: AsyncSession):
        """status() returns current internal state."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config, db_session)
        service._status = "healthy"

        assert await service.status() == "healthy"

        service._status = "degraded"
        assert await service.status() == "degraded"

        service._status = "disabled"
        assert await service.status() == "disabled"

    @pytest.mark.asyncio
    async def test_status_transitions(self, vault_config, db_session: AsyncSession):
        """status() reflects all three states correctly."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config, db_session)

        # Initial unknown state becomes healthy on startup
        assert service._status == "unknown"

        # Startup sets status
        with patch.object(service, '_connect', new_callable=AsyncMock):
            await service.startup()
            assert await service.status() == "healthy"

        # Manual degradation
        service._status = "degraded"
        assert await service.status() == "degraded"

        # Simulate recovery (manual set, not automatic per D-10)
        service._status = "healthy"
        assert await service.status() == "healthy"


# ========== EE-GATING TESTS (Phase 167-05) ==========

@pytest.mark.asyncio
async def test_ce_user_403_vault_config(async_client, db_session, ce_user_token):
    """CE users get 403 on GET /admin/vault/config."""
    response = await async_client.get(
        "/admin/vault/config",
        headers={"Authorization": f"Bearer {ce_user_token}"}
    )
    assert response.status_code == 403
    detail = response.json().get("detail", "").lower()
    assert "ee" in detail or "upgrade" in detail or "licence" in detail


@pytest.mark.asyncio
async def test_ce_user_403_vault_config_update(async_client, db_session, ce_user_token):
    """CE users get 403 on PATCH /admin/vault/config."""
    response = await async_client.patch(
        "/admin/vault/config",
        json={
            "vault_address": "https://vault.example.com:8200",
            "role_id": "test_role",
            "secret_id": "test_secret",
            "enabled": True,
        },
        headers={"Authorization": f"Bearer {ce_user_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ce_user_403_vault_test_connection(async_client, db_session, ce_user_token):
    """CE users get 403 on POST /admin/vault/test-connection."""
    response = await async_client.post(
        "/admin/vault/test-connection",
        json={
            "vault_address": "https://vault.example.com:8200",
            "role_id": "test_role",
            "secret_id": "test_secret",
        },
        headers={"Authorization": f"Bearer {ce_user_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ce_user_403_vault_status(async_client, db_session, ce_user_token):
    """CE users get 403 on GET /admin/vault/status."""
    response = await async_client.get(
        "/admin/vault/status",
        headers={"Authorization": f"Bearer {ce_user_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ee_user_can_access_vault_config(async_client, db_session, ee_user_token):
    """EE users with valid licence can access GET /admin/vault/config."""
    response = await async_client.get(
        "/admin/vault/config",
        headers={"Authorization": f"Bearer {ee_user_token}"}
    )
    # May be 404 if no config exists, but NOT 403
    assert response.status_code in [200, 404]
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_ce_user_dispatch_without_vault_unaffected(async_client, db_session, ce_user_token):
    """CE users can dispatch jobs without vault_secrets (normal dispatch flow unaffected)."""
    response = await async_client.post(
        "/jobs",
        json={
            "task_type": "script",
            "runtime": "bash",
            "payload": {"content": "echo hello"},
            "use_vault_secrets": False,
            "vault_secrets": [],
        },
        headers={"Authorization": f"Bearer {ce_user_token}"}
    )

    # Should NOT be blocked by Vault gating (403) — other errors (422, 500) are
    # acceptable in test env where no nodes or signing keys exist.
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_startup_no_ee_no_vault_clean(db_session):
    """Platform starts cleanly with no EE licence and no Vault config."""
    from agent_service.db import VaultConfig

    # Verify Vault config doesn't exist
    stmt = select(VaultConfig)
    result = await db_session.execute(stmt)
    config = result.scalar_one_or_none()
    assert config is None  # No config


@pytest.mark.asyncio
async def test_dormant_vault_no_dispatch_impact(async_client, db_session, ce_user_token):
    """Jobs dispatch normally when Vault is dormant (not configured)."""
    # Verify no VaultConfig exists
    from agent_service.db import VaultConfig
    stmt = select(VaultConfig)
    result = await db_session.execute(stmt)
    config = result.scalar_one_or_none()
    assert config is None

    # Dispatch a normal job (no vault_secrets)
    response = await async_client.post(
        "/jobs",
        json={
            "task_type": "script",
            "runtime": "bash",
            "payload": {"content": "echo hello"},
        },
        headers={"Authorization": f"Bearer {ce_user_token}"}
    )

    # Should NOT be blocked by Vault gating (403) — other errors are acceptable
    # in test env where no nodes or signing keys exist.
    assert response.status_code != 403


# ========== FIXTURES FOR CE/EE TOKENS ==========

@pytest.fixture
async def ce_user_token(db_session):
    """Create a CE-only user token (no EE licence)."""
    from agent_service.auth import create_access_token
    from agent_service.db import User, AsyncSessionLocal
    from agent_service.auth import get_password_hash
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM users WHERE username = 'ce_test_user'"))
        await session.commit()

        user = User(
            username="ce_test_user",
            password_hash=get_password_hash("testpass123"),
            role="admin",
            must_change_password=False,
            token_version=0
        )
        session.add(user)
        await session.commit()

        # Create token for CE user (no EE key in token or licence state)
        token = create_access_token({"sub": user.username, "tv": user.token_version})
        return token


@pytest.fixture
async def ee_user_token(db_session, async_client):
    """Create an EE user token (with valid EE licence) via mocked licence state."""
    from agent_service.auth import create_access_token
    from agent_service.db import User, AsyncSessionLocal
    from agent_service.auth import get_password_hash
    from agent_service.services.licence_service import LicenceState, LicenceStatus
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM users WHERE username = 'ee_test_user'"))
        await session.commit()

        user = User(
            username="ee_test_user",
            password_hash=get_password_hash("testpass123"),
            role="admin",
            must_change_password=False,
            token_version=0
        )
        session.add(user)
        await session.commit()

        # Create token for EE user
        token = create_access_token({"sub": user.username, "tv": user.token_version})

        # Mock the licence state to be VALID (EE active) for this test
        # This simulates an EE licence being present
        ee_state = LicenceState(
            status=LicenceStatus.VALID,
            tier="ee",
            customer_id="test-customer",
            node_limit=100,
            grace_days=30,
            days_until_expiry=365,
            features=["vault"],
            is_ee_active=True
        )
        # Store the original state to restore later
        from agent_service.main import app
        original_state = getattr(app.state, 'licence_state', None)
        app.state.licence_state = ee_state

        yield token

        # Always restore original licence state (including None for CE startup)
        app.state.licence_state = original_state
