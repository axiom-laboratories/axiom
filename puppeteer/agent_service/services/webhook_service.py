import logging
import hmac
import hashlib
import json
import asyncio
import httpx
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import Webhook

logger = logging.getLogger(__name__)

class WebhookService:
    @staticmethod
    async def create_webhook(
        db: AsyncSession,
        url: str,
        events: str = "*"
    ) -> Webhook:
        """Registers a new outbound webhook."""
        import secrets
        # Generate a unique signing secret for this webhook
        secret = f"whsec_{secrets.token_hex(24)}"
        
        webhook = Webhook(
            url=url,
            secret=secret,
            events=events
        )
        db.add(webhook)
        await db.flush()
        logger.info(f"🔗 WEBHOOK REGISTERED: {url} (Events: {events})")
        return webhook

    @staticmethod
    async def list_webhooks(db: AsyncSession) -> List[Webhook]:
        """Lists all registered webhooks."""
        result = await db.execute(select(Webhook).where(Webhook.active == True))
        return list(result.scalars().all())

    @staticmethod
    async def delete_webhook(db: AsyncSession, webhook_id: int) -> bool:
        """Removes a webhook."""
        result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
        webhook = result.scalar_one_or_none()
        if webhook:
            await db.delete(webhook)
            await db.flush()
            return True
        return False

    @staticmethod
    async def dispatch_event(
        db: AsyncSession,
        event_type: str,
        payload: Any
    ):
        """
        Identifies active webhooks interested in the event and dispatches them.
        This is non-blocking (spawned as a task).
        """
        # Find all webhooks that want this event type (or all '*')
        result = await db.execute(select(Webhook).where(Webhook.active == True))
        webhooks = result.scalars().all()
        
        to_dispatch = []
        for wh in webhooks:
            event_list = [e.strip() for e in wh.events.split(",")]
            if wh.events == "*" or event_type in event_list:
                to_dispatch.append(wh)
        
        if not to_dispatch:
            return

        # Prepare payload wrapper
        full_payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload
        }
        payload_str = json.dumps(full_payload)
        
        # Dispatch asynchronously
        for wh in to_dispatch:
            asyncio.create_task(WebhookService._send_webhook(wh.id, wh.url, wh.secret, payload_str))

    @staticmethod
    async def _send_webhook(wh_id: int, url: str, secret: str, payload_str: str):
        """Internal helper to send the HTTP POST with signing."""
        # Calculate HMAC signature
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "X-MOP-Signature": f"sha256={signature}",
            "User-Agent": "Master-of-Puppets-Orchestrator/1.0"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, content=payload_str, headers=headers)
                
                if resp.is_success:
                    logger.debug(f"✅ Webhook {wh_id} dispatched successfully to {url}")
                else:
                    logger.warning(f"⚠️ Webhook {wh_id} failed with status {resp.status_code}")
                    # Future: Implement retry logic or failure counting
        except Exception as e:
            logger.error(f"❌ Webhook {wh_id} dispatch error to {url}: {e}")
