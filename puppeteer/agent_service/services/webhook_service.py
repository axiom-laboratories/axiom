"""
Webhook service — CE outbound HTTP POST delivery.
EE plugin may extend this with multiple destinations, retry queues, etc.
"""
import httpx
import json
import logging
from datetime import datetime
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..db import Config

logger = logging.getLogger(__name__)

# Event types eligible for webhook delivery
_ALERT_EVENTS = {"job:failed", "job:dead_letter"}
_SECURITY_EVENT = "job:security_rejected"


class WebhookService:
    @staticmethod
    async def dispatch_event(db: AsyncSession, event_type: str, payload: Any):
        """Dispatch a webhook notification for terminal job failure events.

        Reads config from DB, filters by event type, POSTs to the configured URL,
        and records delivery status. Never raises — delivery failures are logged only.
        """
        try:
            # Read all config keys in one query
            keys = [
                "alerts.webhook_url",
                "alerts.webhook_enabled",
                "alerts.webhook_security_rejections",
            ]
            rows = await db.execute(select(Config).where(Config.key.in_(keys)))
            config_map = {r.key: r.value for r in rows.scalars().all()}

            webhook_url = config_map.get("alerts.webhook_url", "")
            webhook_enabled = config_map.get("alerts.webhook_enabled", "false") == "true"
            security_rejections = config_map.get("alerts.webhook_security_rejections", "false") == "true"

            # Guard: must be enabled and have a URL
            if not webhook_enabled or not webhook_url:
                return

            # Guard: event type filter
            if event_type not in _ALERT_EVENTS and event_type != _SECURITY_EVENT:
                return
            if event_type == _SECURITY_EVENT and not security_rejections:
                return

            # Build locked payload shape
            if event_type == _SECURITY_EVENT:
                event_name = "job.security_rejected"
            else:
                event_name = "job.failed"

            outbound = {
                "event": event_name,
                "job_guid": payload.get("guid", ""),
                "job_name": payload.get("job_name", ""),
                "node_id": payload.get("node_id", ""),
                "error_summary": payload.get("error_summary", ""),
                "failed_at": payload.get("failed_at", datetime.utcnow().isoformat() + "Z"),
            }

            # Perform HTTP POST
            status_code = None
            body_snippet = None
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(webhook_url, json=outbound)
                    status_code = response.status_code
                    body_snippet = response.text[:200]
                logger.info(
                    "Webhook delivery: event=%s url=%s status=%s",
                    event_type, webhook_url, status_code,
                )
            except Exception as exc:
                body_snippet = str(exc)[:200]
                logger.warning(
                    "Webhook delivery failed: event=%s url=%s error=%s",
                    event_type, webhook_url, exc,
                )

            # Record last delivery status regardless of success/failure
            status_json = json.dumps({
                "status_code": status_code,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "body_snippet": body_snippet or "",
            })
            existing = await db.execute(
                select(Config).where(Config.key == "alerts.last_delivery_status")
            )
            row = existing.scalar_one_or_none()
            if row:
                row.value = status_json
            else:
                db.add(Config(key="alerts.last_delivery_status", value=status_json))
            await db.commit()

        except Exception as exc:
            logger.error("Unexpected error in WebhookService.dispatch_event: %s", exc)
