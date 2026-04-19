"""HashiCorp Vault integration via AppRole auth.

Implements SecretsProvider protocol for extensibility (D-13).
Non-blocking startup; graceful degradation if Vault unreachable (D-07).
"""

import hvac
import asyncio
import logging
import json
from typing import Optional, Literal
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .secrets_provider import SecretsProvider
from agent_service.db import VaultConfig
from agent_service.security import cipher_suite

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VaultConfigSnapshot:
    """Immutable snapshot of VaultConfig values taken at service construction time.

    Avoids DetachedInstanceError when the ORM session that loaded the config
    is closed or committed while the long-lived singleton still holds a reference.
    """
    enabled: bool
    vault_address: str
    role_id: str
    secret_id: str
    mount_path: str
    namespace: Optional[str]
    provider_type: str

    @classmethod
    def from_orm(cls, vc: "VaultConfig") -> "VaultConfigSnapshot":
        """Convert VaultConfig ORM object to snapshot."""
        return cls(
            enabled=vc.enabled,
            vault_address=vc.vault_address,
            role_id=vc.role_id,
            secret_id=vc.secret_id,
            mount_path=vc.mount_path,
            namespace=vc.namespace,
            provider_type=vc.provider_type,
        )


class VaultError(Exception):
    """Base exception for Vault service errors."""
    pass


class VaultService(SecretsProvider):
    """HashiCorp Vault integration via AppRole auth.

    Implements SecretsProvider protocol for extensibility (D-13).
    Non-blocking startup; graceful degradation if Vault unreachable (D-07).
    """

    def __init__(self, config: Optional[VaultConfig], db: AsyncSession):
        self.config: Optional[VaultConfigSnapshot] = (
            VaultConfigSnapshot.from_orm(config) if config else None
        )
        self.db = db
        self._client: Optional[hvac.Client] = None
        self._status: Literal["healthy", "degraded", "disabled"] = \
            "disabled" if not config or not config.enabled else "degraded"
        self._consecutive_renewal_failures = 0
        self._last_error: Optional[str] = None
        self._last_checked_at: Optional[datetime] = None

    async def startup(self) -> None:
        """Initialize Vault connection. Non-blocking; sets status to DEGRADED if fails (D-07)."""
        if not self.config or not self.config.enabled:
            self._status = "disabled"
            logger.info("Vault not configured; running in dormant mode")
            return

        try:
            await self._connect()
            self._status = "healthy"
            self._last_checked_at = datetime.utcnow()
            logger.info(f"Vault connection established: {self.config.vault_address}")
        except Exception as e:
            self._status = "degraded"
            self._last_error = str(e)
            self._last_checked_at = datetime.utcnow()
            logger.warning(f"Vault unavailable at startup; running in degraded mode: {e}")

    @property
    def renewal_failures(self) -> int:
        """Return count of consecutive lease renewal failures."""
        return self._consecutive_renewal_failures

    async def _connect(self) -> None:
        """Establish Vault connection via AppRole auth."""
        if not self.config:
            raise VaultError("No Vault config available")

        # Decrypt secret_id from DB (encrypted at rest per D-05)
        decrypted_secret_id = cipher_suite.decrypt(self.config.secret_id.encode()).decode()

        def _sync_login():
            client = hvac.Client(
                url=self.config.vault_address,
                namespace=self.config.namespace or None,
                verify=True  # Always verify TLS in production
            )
            client.auth.approle.login(
                role_id=self.config.role_id,
                secret_id=decrypted_secret_id
            )
            return client

        # Run sync hvac in thread pool (asyncio.to_thread for async compatibility)
        self._client = await asyncio.to_thread(_sync_login)

    async def resolve(self, names: list[str]) -> dict[str, str]:
        """Resolve secret names to values (server-side, D-03)."""
        if self._status == "disabled":
            raise VaultError("Vault not configured")

        if self._status != "healthy":
            raise VaultError(f"Vault unavailable (status: {self._status})")

        if not self._client:
            raise VaultError("Vault client not initialized")

        resolved = {}
        try:
            for name in names:
                def _sync_read():
                    response = self._client.secrets.kv.v2.read_secret_version(
                        path=name,
                        mount_point=self.config.mount_path
                    )
                    # KV v2 response structure: response['data']['data'][key]
                    return response['data']['data']

                secret_data = await asyncio.to_thread(_sync_read)
                # Extract value or entire dict if single 'value' key
                if 'value' in secret_data:
                    resolved[name] = secret_data['value']
                else:
                    # If secret is a complex object, return as JSON string
                    resolved[name] = json.dumps(secret_data)

            return resolved
        except Exception as e:
            self._status = "degraded"
            self._last_error = str(e)
            raise VaultError(f"Secret resolution failed: {e}")

    async def status(self) -> Literal["healthy", "degraded", "disabled"]:
        """Return current Vault status."""
        return self._status

    async def renew(self) -> None:
        """Renew Vault token lease. Called by background task (D-10)."""
        if self._status == "disabled":
            return  # No-op if not configured

        if not self._client:
            return  # No-op if not connected

        try:
            def _sync_renew():
                self._client.auth.token.renew_self()

            await asyncio.to_thread(_sync_renew)
            self._consecutive_renewal_failures = 0
            self._last_checked_at = datetime.utcnow()
        except Exception as e:
            self._consecutive_renewal_failures += 1
            self._last_error = str(e)
            self._last_checked_at = datetime.utcnow()
            logger.warning(f"Lease renewal failed (attempt {self._consecutive_renewal_failures}): {e}")

            if self._consecutive_renewal_failures >= 3:
                self._status = "degraded"
                logger.error("Lease renewal failed 3 times; Vault status set to DEGRADED")
