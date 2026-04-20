"""SecretsProvider Protocol for extensible secrets backends.

Enables future backends (Azure KV, AWS Secrets Manager, GCP Secret Manager, etc.)
without modifying dispatch layer. Per D-13 and D-14.
"""

from typing import Protocol, Literal


class SecretsProvider(Protocol):
    """Protocol for secret backends (Vault, Azure KV, AWS Secrets Manager, GCP Secret Manager).

    Enables future backends without modifying dispatch layer (D-13, D-14).
    """

    async def resolve(self, names: list[str]) -> dict[str, str]:
        """Resolve secret names to values.

        Args:
            names: List of secret names/paths to resolve

        Returns:
            dict mapping each name to its resolved value

        Raises:
            SecretsError: if resolution fails (network, auth, secret not found)
        """
        ...

    async def status(self) -> Literal["healthy", "degraded", "disabled"]:
        """Return current provider status.

        healthy: Connected, credentials valid, ready to resolve
        degraded: Connection lost or repeated failures, but platform continues
        disabled: Provider not configured or disabled via config
        """
        ...

    async def renew(self) -> None:
        """Renew leases or refresh credentials.

        Called by background task (APScheduler, every 5 min).
        Should not raise; failures are logged and tracked in status.
        """
        ...
