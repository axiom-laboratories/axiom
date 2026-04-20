"""Real-time audit log streaming to SIEM platforms (webhook/syslog) with CEF formatting.

Implements Phase 168 SIEM Audit Streaming (EE).
Non-blocking startup; graceful degradation; best-effort delivery (local audit_log is canonical).
Module-level singleton via get_siem_service() / set_active().
"""

import asyncio
import json
import logging
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse
from typing import Optional, Literal
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent_service.db import SIEMConfig


@dataclass(frozen=True)
class _SIEMConfigSnapshot:
    """Immutable snapshot of SIEMConfig values taken at service construction time.

    Avoids DetachedInstanceError when the ORM session that loaded the config
    is closed or committed while the long-lived singleton still holds a reference.
    """
    backend: str
    destination: str
    syslog_port: int
    syslog_protocol: str
    cef_device_vendor: str
    cef_device_product: str
    enabled: bool

logger = logging.getLogger(__name__)

# Sensitive field keys that must be masked before transmission (D-11, D-12)
SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key", "secret_id", "role_id",
    "encryption_key", "access_token", "refresh_token",
    # MEDIUM-01: Additional variants to catch (D-11, D-12)
    "jwt", "jwt_token",
    "connection_string",
    "tls_cert", "client_cert",
    "webhook_auth", "webhook_secret",
    "private_key", "signing_key",
}


def _mask_sensitive(obj: object) -> object:
    """Recursively mask sensitive fields in a nested dict/list structure.

    Never modifies the input; always returns a new object.
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            k_lower = k.lower()
            if k_lower in SENSITIVE_KEYS or k_lower.endswith(("_key", "_secret")):
                result[k] = "***"
            else:
                result[k] = _mask_sensitive(v)
        return result
    if isinstance(obj, list):
        return [_mask_sensitive(item) for item in obj]
    return obj


def _parse_syslog_destination(destination: str, default_port: int) -> tuple[str, int]:
    """Parse syslog destination into (host, port), handling IPv4, hostname, and IPv6.

    Accepted formats:
      hostname:514  →  ("hostname", 514)
      1.2.3.4:514   →  ("1.2.3.4", 514)
      [::1]:514     →  ("::1", 514)   # bracketed IPv6 with port
      ::1           →  ("::1", default_port)  # bare IPv6, no port
      hostname      →  ("hostname", default_port)
    """
    # Bracketed IPv6: [::1]:514 or [::1]
    if destination.startswith("["):
        bracket_end = destination.find("]")
        if bracket_end != -1:
            host = destination[1:bracket_end]
            remainder = destination[bracket_end + 1:]
            if remainder.startswith(":"):
                try:
                    return host, int(remainder[1:])
                except ValueError:
                    pass
            return host, default_port
    # Bare IPv6 (multiple colons, no brackets) — no port extractable
    if destination.count(":") > 1:
        return destination, default_port
    # hostname:port or IPv4:port
    if ":" in destination:
        host, port_str = destination.rsplit(":", 1)
        try:
            return host, int(port_str)
        except ValueError:
            return host, default_port
    return destination, default_port


def _redact_destination(destination: str) -> str:
    """Redact query parameters from webhook URLs to avoid leaking embedded tokens."""
    try:
        parsed = urlparse(destination)
        if parsed.scheme in ("http", "https") and parsed.query:
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "***", ""))
    except Exception:
        pass
    return destination


class SIEMService:
    """Real-time audit log streaming to SIEM platforms (webhook/syslog) with CEF formatting.

    Non-blocking startup; graceful degradation; best-effort delivery (local audit_log is canonical).
    Batches events (100 events or 5s, whichever first) before transmission.
    Masks sensitive fields at format time (never modifies audit_log DB).
    Retries failed deliveries with exponential backoff (5s → 10s → 20s, max 3 attempts).
    """

    def __init__(
        self,
        config: Optional[SIEMConfig],
        db: AsyncSession,
        scheduler: AsyncIOScheduler,
    ):
        """Initialize SIEM service.

        Args:
            config: SIEMConfig DB model (None in CE or dormant mode)
            db: AsyncSession for DB operations
            scheduler: APScheduler AsyncIOScheduler instance for batch flush and retry jobs
        """
        # Snapshot config values into a plain dataclass to prevent DetachedInstanceError
        # when the SQLAlchemy session that loaded the ORM object closes after startup.
        self.config: Optional[_SIEMConfigSnapshot] = (
            _SIEMConfigSnapshot(
                backend=config.backend,
                destination=config.destination,
                syslog_port=config.syslog_port,
                syslog_protocol=config.syslog_protocol,
                cef_device_vendor=config.cef_device_vendor,
                cef_device_product=config.cef_device_product,
                enabled=config.enabled,
            )
            if config else None
        )
        self.db = db
        self.scheduler = scheduler
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)
        self._status: Literal["healthy", "degraded", "disabled"] = (
            "disabled" if not config or not config.enabled else "unknown"
        )
        self._consecutive_failures = 0
        self._dropped_events_count = 0
        self._alert_pending = False
        self._last_error: Optional[str] = None
        self._last_checked_at: Optional[datetime] = None

    async def startup(self) -> None:
        """Initialize SIEM connection (non-blocking). Sets status DEGRADED if fails (D-07)."""
        if not self.config or not self.config.enabled:
            self._status = "disabled"
            logger.info("SIEM not configured; running in dormant mode")
            return

        # Always register the flush job so the service can recover if the destination
        # becomes reachable after startup (degraded → healthy on next successful delivery).
        self.scheduler.add_job(
            self._flush_periodically,
            "interval",
            seconds=5,
            id="__siem_flush__",
            replace_existing=True,
        )

        try:
            # Test destination reachability
            await self._test_connection()
            self._status = "healthy"
            self._last_checked_at = datetime.now(timezone.utc)
            logger.info(
                f"SIEM connection healthy: {self.config.backend} → {self.config.destination}"
            )
        except Exception as e:
            self._status = "degraded"
            self._last_error = str(e)
            self._last_checked_at = datetime.now(timezone.utc)
            logger.warning(f"SIEM unavailable at startup; running degraded: {e}")

    def enqueue(self, event: dict) -> None:
        """Queue an audit event (fire-and-forget, non-blocking, D-03, D-09).

        If queue is full, drops oldest event and logs warning.
        Never blocks or raises exceptions that propagate to caller.
        """
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            # Oldest event is always discarded on overflow — count it before retrying
            self._dropped_events_count += 1
            if self._dropped_events_count % 100 == 0 and not self._alert_pending:
                logger.warning(
                    f"SIEM event queue overflow: {self._dropped_events_count} events dropped so far"
                )
                self._alert_pending = True
                asyncio.create_task(self._fire_queue_overflow_alert())
            # Drop oldest and retry once
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self.queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
        except Exception:
            # Never propagate exceptions from enqueue to caller
            pass

    async def _flush_periodically(self) -> None:
        """APScheduler job: flush batch if queue has events (D-09).

        Reads up to 100 events from queue and calls flush_batch().
        Runs every 5 seconds (registered in startup()).
        """
        batch = []
        while len(batch) < 100:  # Max 100 events per flush (D-09)
            try:
                event = self.queue.get_nowait()
                batch.append(event)
            except asyncio.QueueEmpty:
                break

        if batch:
            await self.flush_batch(batch)

    async def flush_batch(self, batch: list[dict], attempt: int = 0) -> None:
        """Format batch to CEF and deliver with retry (D-13, D-14).

        Single attempt per call. On failure, schedules the next retry via APScheduler
        with escalating backoff (5s → 10s → 20s). The attempt counter is passed to
        each scheduled retry so backoff escalates correctly across calls.

        Attempt 0: immediate (called by _flush_periodically or lifespan shutdown)
        Attempt 1: retry after 5s
        Attempt 2: retry after 10s
        Attempt 3 (final): retry after 20s → on failure, transitions to DEGRADED
        """
        if not batch:
            return

        max_attempts = 4  # attempts 0-3
        backoff_delays = [5, 10, 20]  # delay before attempt 1, 2, 3

        cef_lines = [self._format_cef(event) for event in batch]
        payload = "\n".join(cef_lines)

        try:
            await self._deliver(payload)
            self._consecutive_failures = 0
            self._status = "healthy"
            self._last_checked_at = datetime.now(timezone.utc)
            logger.debug(f"SIEM batch delivered: {len(batch)} events (attempt {attempt})")
            return
        except Exception as e:
            self._last_error = str(e)
            self._consecutive_failures += 1
            self._last_checked_at = datetime.now(timezone.utc)

            next_attempt = attempt + 1
            if next_attempt < max_attempts:
                delay = backoff_delays[attempt]  # 5s, 10s, 20s for attempts 0→1, 1→2, 2→3
                job_id = f"siem_retry_{uuid4()}_{next_attempt}"
                self.scheduler.add_job(
                    self.flush_batch,
                    "date",
                    run_date=datetime.now(timezone.utc) + timedelta(seconds=delay),
                    args=[batch, next_attempt],
                    id=job_id,
                    replace_existing=False,
                )
                logger.warning(
                    f"SIEM delivery failed (attempt {attempt}/{max_attempts - 1}), "
                    f"retrying in {delay}s: {e}"
                )
            else:
                logger.error(
                    f"SIEM delivery failed after {max_attempts} attempts; "
                    f"dropping batch of {len(batch)} events: {e}"
                )
                if self._consecutive_failures >= 3:
                    self._status = "degraded"
                    logger.error(
                        "SIEM transitioned to DEGRADED after 3 consecutive batch failures"
                    )

    def _format_cef(self, event: dict) -> str:
        """Format audit event to CEF with field masking (D-11, D-12).

        Masks sensitive fields (password, secret, token, api_key, *_key, *_secret).
        Masking happens at format time only; never modifies the stored audit_log.
        """
        # Mask sensitive fields in detail recursively (D-11, D-12)
        detail = event.get("detail") or {}
        masked_detail = _mask_sensitive(detail)

        # Build CEF header and extensions
        # CEF:0|Vendor|Product|Version|SignatureID|Name|Severity|[Extensions]
        cef_version = "0"
        device_vendor = (
            self.config.cef_device_vendor if self.config else None
        ) or "Axiom"
        device_product = (
            self.config.cef_device_product if self.config else None
        ) or "MasterOfPuppets"
        device_version = "24.0"
        action = event.get("action", "unknown")
        signature_id = f"audit.{action}"
        name = f"Audit: {action}"
        severity = self._map_severity(action)

        # Extensions (ArcSight/CEF extension dictionary)
        event_timestamp = event.get("timestamp", datetime.now(timezone.utc))
        if isinstance(event_timestamp, datetime):
            timestamp_ms = int(event_timestamp.timestamp() * 1000)
        else:
            timestamp_ms = int(datetime.fromisoformat(event_timestamp).timestamp() * 1000)

        extensions = {
            "rt": timestamp_ms,
            "msg": json.dumps(masked_detail, default=str),
            "duser": event.get("username", "unknown"),
            "cs1Label": "audit_action",
            "cs1": action,
            "cs2Label": "resource_id",
            "cs2": event.get("resource_id", "—"),
        }

        def _escape_cef_extension_value(v) -> str:
            # CEF spec: escape \ → \\, = → \=, newline → \n in extension values
            s = str(v)
            s = s.replace("\\", "\\\\")
            s = s.replace("=", "\\=")
            s = s.replace("\n", "\\n")
            s = s.replace("\r", "\\r")
            return s

        def _escape_cef_header_field(v: str) -> str:
            # CEF spec: escape \ → \\ and | → \| in header fields
            s = v.replace("\\", "\\\\")
            s = s.replace("|", "\\|")
            return s

        # Format CEF header and extensions
        cef_header = (
            f"CEF:{cef_version}"
            f"|{_escape_cef_header_field(device_vendor)}"
            f"|{_escape_cef_header_field(device_product)}"
            f"|{device_version}"
            f"|{_escape_cef_header_field(signature_id)}"
            f"|{_escape_cef_header_field(name)}"
            f"|{severity}"
        )
        cef_extensions = " ".join(
            [f"{k}={_escape_cef_extension_value(v)}" for k, v in extensions.items()]
        )
        return f"{cef_header}|{cef_extensions}"

    async def _fire_queue_overflow_alert(self) -> None:
        """Fire admin alert when SIEM queue overflows (MEDIUM-03)."""
        try:
            from agent_service.db import Alert, AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                alert = Alert(
                    type="siem_queue_overflow",
                    severity="WARNING",
                    message=f"SIEM event queue overflow: {self._dropped_events_count} events dropped. "
                            f"Increase queue size or reduce audit event rate. "
                            f"Local audit_log is canonical; events are queued for transmission only.",
                )
                session.add(alert)
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to create SIEM queue overflow alert: {e}")
        finally:
            self._alert_pending = False

    def _map_severity(self, action: str) -> int:
        """Map audit action to CEF severity (1-10).

        Severity scale:
        1=Unknown, 2=Very Low, 3=Low, 4=Medium, 5=High, 6=Very High,
        7=High, 8=Critical, 9-10=Emergency
        """
        severity_map = {
            "login": 5,
            "login_failure": 6,
            "user_create": 5,
            "user_delete": 7,
            "config_change": 6,
            "job_execute": 4,
            "job_failure": 7,
            "permission_grant": 6,
            "permission_revoke": 6,
            "vault:config_update": 6,
            "siem:config_update": 6,
        }
        return severity_map.get(action, 4)  # Default: Medium

    async def _deliver(self, payload: str) -> None:
        """Deliver CEF payload via webhook or syslog.

        Webhook: POST to destination URL with Content-Type: application/cef
        Syslog: Send via UDP or TCP to destination:port
        """
        if not self.config:
            raise Exception("SIEM not configured")

        if self.config.backend == "webhook":
            await self._deliver_webhook(payload)
        elif self.config.backend == "syslog":
            await self._deliver_syslog(payload)
        else:
            raise Exception(f"Unknown SIEM backend: {self.config.backend}")

    async def _deliver_webhook(self, payload: str) -> None:
        """Deliver payload to webhook URL."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.config.destination,
                content=payload,
                headers={"Content-Type": "application/cef"},
            )
            response.raise_for_status()

    async def _deliver_syslog(self, payload: str) -> None:
        """Deliver payload to syslog server via UDP or TCP."""

        def _sync_send():
            host, port = _parse_syslog_destination(
                self.config.destination, self.config.syslog_port
            )
            protocol = self.config.syslog_protocol.upper()
            socktype = (
                socket.SOCK_DGRAM if protocol == "UDP" else socket.SOCK_STREAM
            )

            # Use logging.handlers.SysLogHandler for syslog delivery
            import logging.handlers

            handler = logging.handlers.SysLogHandler(
                address=(host, port), socktype=socktype
            )
            # Override default formatter so the raw CEF string is sent without
            # the "INFO:siem:" prefix that the default formatter would prepend.
            handler.setFormatter(logging.Formatter("%(message)s"))

            # Send each CEF line as a syslog message
            for line in payload.split("\n"):
                if line.strip():
                    record = logging.makeRecord(
                        name="siem",
                        level=logging.INFO,
                        pathname="",
                        lineno=0,
                        msg=line,
                        args=(),
                        exc_info=None,
                    )
                    handler.emit(record)

            handler.close()

        # Run sync syslog send in thread pool to avoid blocking event loop
        await asyncio.to_thread(_sync_send)

    async def _test_connection(self) -> None:
        """Test destination reachability (webhook or syslog)."""
        if not self.config:
            raise Exception("SIEM not configured")

        if self.config.backend == "webhook":
            await self._test_webhook_connection()
        elif self.config.backend == "syslog":
            await self._test_syslog_connection()
        else:
            raise Exception(f"Unknown SIEM backend: {self.config.backend}")

    async def _test_webhook_connection(self) -> None:
        """Test webhook destination reachability."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.config.destination,
                content="CEF:0|Axiom|MasterOfPuppets|24.0|test|Test Connection|5|msg=Test CEF event",
                headers={"Content-Type": "application/cef"},
            )
            response.raise_for_status()

    async def _test_syslog_connection(self) -> None:
        """Test syslog destination reachability."""

        def _sync_test():
            host, port = _parse_syslog_destination(
                self.config.destination, self.config.syslog_port
            )
            protocol = self.config.syslog_protocol.upper()
            socktype = (
                socket.SOCK_DGRAM if protocol == "UDP" else socket.SOCK_STREAM
            )

            # Create socket and test connection
            sock = socket.socket(socket.AF_INET, socktype)
            try:
                if protocol == "TCP":
                    sock.connect((host, port))
                    sock.close()
                else:
                    # UDP: just create socket and close (no connect needed)
                    sock.close()
            except Exception as e:
                raise Exception(f"Syslog connection failed: {e}")

        await asyncio.to_thread(_sync_test)

    async def shutdown(self) -> None:
        """Gracefully stop background scheduler jobs for this service instance."""
        try:
            self.scheduler.remove_job("__siem_flush__")
        except Exception:
            pass
        # Cancel any pending retry jobs (scheduled with siem_retry_{uuid} IDs)
        for job in list(self.scheduler.get_jobs()):
            if job.id.startswith("siem_retry_"):
                try:
                    job.remove()
                except Exception:
                    pass

    async def status(self) -> Literal["healthy", "degraded", "disabled"]:
        """Return current SIEM status."""
        return self._status

    def status_detail(self) -> dict:
        """Return detailed status for admin UI."""
        return {
            "status": self._status,
            "backend": self.config.backend if self.config else None,
            "destination": _redact_destination(self.config.destination) if self.config else None,
            "last_checked_at": (
                self._last_checked_at.isoformat()
                if self._last_checked_at
                else None
            ),
            "error_detail": self._last_error,
            "consecutive_failures": self._consecutive_failures,
            "dropped_events": self._dropped_events_count,
            "syslog_port": self.config.syslog_port if self.config else None,
            "syslog_protocol": self.config.syslog_protocol if self.config else None,
        }


# Module-level singleton (D-04)
_siem_service: Optional[SIEMService] = None


def get_siem_service() -> Optional[SIEMService]:
    """Get active SIEM service (None in CE/dormant mode)."""
    return _siem_service


def set_active(service: SIEMService) -> None:
    """Set active SIEM service (called from main.py lifespan)."""
    global _siem_service
    _siem_service = service
