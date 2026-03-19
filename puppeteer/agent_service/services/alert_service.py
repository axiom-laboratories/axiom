import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import Alert, Node

logger = logging.getLogger(__name__)

class AlertService:
    @staticmethod
    async def create_alert(
        db: AsyncSession,
        type: str,
        severity: str,
        message: str,
        resource_id: Optional[str] = None
    ) -> Alert:
        """Creates a new system alert, broadcasts it, and logs to Audit."""
        from .. import main
        
        alert = Alert(
            type=type,
            severity=severity,
            message=message,
            resource_id=resource_id,
            created_at=datetime.utcnow()
        )
        db.add(alert)

        await db.flush()

        logger.info(f"ALERT CREATED [{severity}]: {message}")
        
        # Broadcast to dashboard
        try:
            await main.ws_manager.broadcast("alert:new", {
                "id": alert.id,
                "type": type,
                "severity": severity,
                "message": message,
                "resource_id": resource_id,
                "created_at": alert.created_at.isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to broadcast alert: {e}")
            
        return alert

    @staticmethod
    async def resolve_alert(
        db: AsyncSession,
        type: str,
        resource_id: str
    ) -> int:
        """
        Automatically acknowledges/resolves alerts of a certain type for a resource.
        Useful when a node comes back online or a condition clears.
        """
        result = await db.execute(
            select(Alert).where(
                and_(
                    Alert.type == type,
                    Alert.resource_id == resource_id,
                    Alert.acknowledged == False
                )
            )
        )
        alerts = result.scalars().all()
        for alert in alerts:
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = "system:auto_resolve"
            
        if alerts:
            await db.flush()
            logger.info(f"✅ Resolved {len(alerts)} alerts for {resource_id} ({type})")
            
        return len(alerts)

    @staticmethod
    async def list_alerts(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 50, 
        unacknowledged_only: bool = False
    ) -> List[Alert]:
        """Lists alerts with optional filtering."""
        query = select(Alert).order_by(Alert.created_at.desc()).offset(skip).limit(limit)
        if unacknowledged_only:
            query = query.where(Alert.acknowledged == False)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def acknowledge_alert(
        db: AsyncSession,
        alert_id: int,
        username: str
    ) -> Optional[Alert]:
        """Marks an alert as acknowledged."""
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert:
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = username
            await db.flush()
            return alert
        return None

    @staticmethod
    async def check_node_health(db: AsyncSession) -> int:
        """
        Checks for nodes that have missed heartbeats and generates alerts.
        Returns the number of nodes newly marked as OFFLINE.
        """
        # Threshold: 5 minutes since last seen
        threshold = datetime.utcnow() - timedelta(minutes=5)
        
        # Find nodes that are currently ONLINE but haven't been seen recently
        result = await db.execute(
            select(Node).where(
                and_(
                    Node.status == "ONLINE",
                    Node.last_seen < threshold
                )
            )
        )
        offline_nodes = result.scalars().all()
        
        count = 0
        for node in offline_nodes:
            node.status = "OFFLINE"
            await AlertService.create_alert(
                db,
                type="node_offline",
                severity="WARNING",
                message=f"Node {node.hostname} ({node.node_id}) is offline. Last seen at {node.last_seen}.",
                resource_id=node.node_id
            )
            count += 1
        
        if count > 0:
            await db.commit()
            
        return count
