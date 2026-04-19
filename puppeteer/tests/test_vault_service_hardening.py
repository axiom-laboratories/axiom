"""
Vault service hardening tests for Phase 171-03.

Tests VaultConfigSnapshot immutability, narrowed exception handling,
renewal_failures property, and auto re-authentication recovery.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def vault_config_snapshot():
    """Create a test VaultConfigSnapshot."""
    from ee.services.vault_service import VaultConfigSnapshot

    return VaultConfigSnapshot(
        enabled=True,
        vault_address="http://localhost:8200",
        role_id="test-role",
        secret_id="test-secret",
        mount_path="secret",
        namespace=None,
        provider_type="approle"
    )


class TestVaultConfigSnapshot:
    """Test VaultConfigSnapshot frozen dataclass."""

    @pytest.mark.asyncio
    async def test_snapshot_immutable(self, vault_config_snapshot):
        """Verify VaultConfigSnapshot is frozen (immutable)."""
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            vault_config_snapshot.enabled = False

    @pytest.mark.asyncio
    async def test_snapshot_from_orm(self):
        """Verify from_orm conversion from ORM VaultConfig."""
        from ee.services.vault_service import VaultConfigSnapshot
        from agent_service.db import VaultConfig
        from agent_service.security import cipher_suite
        from uuid import uuid4

        # Create a mock ORM object
        orm_config = MagicMock(spec=VaultConfig)
        orm_config.enabled = True
        orm_config.vault_address = "http://vault:8200"
        orm_config.role_id = "test-role"
        orm_config.secret_id = cipher_suite.encrypt(b"secret").decode()
        orm_config.mount_path = "secret"
        orm_config.namespace = None
        orm_config.provider_type = "approle"

        # Convert to snapshot
        snapshot = VaultConfigSnapshot.from_orm(orm_config)

        assert snapshot.enabled is True
        assert snapshot.vault_address == "http://vault:8200"
        assert snapshot.role_id == "test-role"


class TestVaultServiceRenewalFailures:
    """Test renewal_failures property."""

    @pytest.mark.asyncio
    async def test_renewal_failures_property(self, db_session: AsyncSession):
        """Verify renewal_failures property exposes counter."""
        from ee.services.vault_service import VaultService

        service = VaultService(None, db_session)

        # Initially 0
        assert service.renewal_failures == 0

        # Increment internal counter and verify property reads it
        service._consecutive_renewal_failures = 5
        assert service.renewal_failures == 5

    @pytest.mark.asyncio
    async def test_renewal_failures_increments_on_failure(self, db_session: AsyncSession):
        """Verify renewal_failures increments on renewal failure."""
        from ee.services.vault_service import VaultService

        service = VaultService(None, db_session)
        service._client = MagicMock()  # Use MagicMock, not AsyncMock for sync code in to_thread
        service._status = "healthy"

        # Mock a renewal failure (to_thread wraps sync code, so no async needed)
        def mock_renew_failure():
            raise Exception("Connection refused")

        service._client.auth.token.renew_self = mock_renew_failure

        # Run renewal (will fail and increment counter)
        await service.renew()

        assert service.renewal_failures == 1


class TestVaultServiceExceptionHandling:
    """Test narrowed exception handling in resolve()."""

    @pytest.mark.asyncio
    async def test_exception_handler_catches_hvac_errors(self, db_session: AsyncSession, vault_config_snapshot):
        """Verify exception handler in resolve() catches hvac errors."""
        from ee.services.vault_service import VaultService, VaultError
        import hvac.exceptions

        service = VaultService(vault_config_snapshot, db_session)
        service._client = MagicMock()
        service._status = "healthy"

        # Simulate hvac error in sync code (used in to_thread)
        def mock_read_failure(**kwargs):
            raise hvac.exceptions.VaultError("Vault unreachable")

        service._client.secrets.kv.v2.read_secret_version = mock_read_failure

        with pytest.raises(VaultError):
            await service.resolve(["test-secret"])

        # Status should be degraded
        assert service._status == "degraded"

    @pytest.mark.asyncio
    async def test_exception_handler_catches_connection_error(self, db_session: AsyncSession, vault_config_snapshot):
        """Verify exception handler in resolve() catches ConnectionError."""
        from ee.services.vault_service import VaultService, VaultError

        service = VaultService(vault_config_snapshot, db_session)
        service._client = MagicMock()
        service._status = "healthy"

        # Simulate network error (sync code in to_thread)
        def mock_read_network_error(**kwargs):
            raise ConnectionError("Network unreachable")

        service._client.secrets.kv.v2.read_secret_version = mock_read_network_error

        with pytest.raises(VaultError):
            await service.resolve(["test-secret"])

        assert service._status == "degraded"


class TestVaultAutoReauth:
    """Test auto re-authentication in renew() when degraded."""

    @pytest.mark.asyncio
    async def test_auto_reauth_on_degraded(self, db_session: AsyncSession, vault_config_snapshot):
        """Verify renew() attempts re-auth when degraded."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config_snapshot, db_session)
        service._status = "degraded"
        service._consecutive_renewal_failures = 2
        service._client = AsyncMock()

        # Mock _connect to succeed
        with patch.object(service, '_connect', new_callable=AsyncMock) as mock_connect:
            await service.renew()

            # Should have attempted _connect
            mock_connect.assert_called_once()
            # Status should be restored
            assert service._status == "healthy"
            assert service._consecutive_renewal_failures == 0

    @pytest.mark.asyncio
    async def test_auto_reauth_failure_keeps_degraded(self, db_session: AsyncSession, vault_config_snapshot):
        """Verify renew() keeps degraded status if re-auth fails."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config_snapshot, db_session)
        service._status = "degraded"
        service._consecutive_renewal_failures = 1
        service._client = AsyncMock()

        # Mock _connect to fail
        with patch.object(service, '_connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Still unreachable")
            await service.renew()

            # Status should remain degraded
            assert service._status == "degraded"
            # Failure count should have incremented
            assert service._consecutive_renewal_failures == 2

    @pytest.mark.asyncio
    async def test_disabled_config_no_reauth(self, db_session: AsyncSession):
        """Verify renew() doesn't attempt re-auth if config is disabled."""
        from ee.services.vault_service import VaultService

        service = VaultService(None, db_session)
        service._status = "degraded"
        service._client = AsyncMock()

        # Mock _connect (should not be called)
        with patch.object(service, '_connect', new_callable=AsyncMock) as mock_connect:
            await service.renew()

            # Should NOT have attempted _connect (config is None)
            mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_renew_continues_after_successful_reauth(self, db_session: AsyncSession, vault_config_snapshot):
        """Verify normal renewal continues after successful re-auth."""
        from ee.services.vault_service import VaultService

        service = VaultService(vault_config_snapshot, db_session)
        service._status = "degraded"
        service._consecutive_renewal_failures = 2
        service._client = AsyncMock()

        # Mock _connect to succeed, renewal to succeed
        with patch.object(service, '_connect', new_callable=AsyncMock) as mock_connect:
            service._client.auth.token.renew_self = AsyncMock()

            await service.renew()

            # re-auth should have been attempted
            mock_connect.assert_called_once()
            # Status should be healthy
            assert service._status == "healthy"
            # Failure counter should be reset
            assert service._consecutive_renewal_failures == 0
            # renewal_self should have been called (normal renewal flow)
            service._client.auth.token.renew_self.assert_called_once()
