"""
Webhook service — CE stub. EE plugin replaces this with real outbound webhooks.
"""
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class WebhookService:
    @staticmethod
    async def dispatch_event(db: AsyncSession, event_type: str, payload: Any):
        """No-op in CE. EE plugin provides real webhook dispatch."""
        pass
