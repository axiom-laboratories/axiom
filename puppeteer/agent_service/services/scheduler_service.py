import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import delete
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .. import db as db_module
from ..db import ScheduledJob, Job, Signature, Node, NodeStats, AsyncSession, User
from ..models import JobDefinitionCreate, JobDefinitionResponse
from .signature_service import SignatureService

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Starts the internal APScheduler."""
        try:
            self.scheduler.start()
            logger.info("🕒 Scheduler Started")
            self.scheduler.add_job(
                self.prune_stale_node_stats,
                'interval',
                hours=6,
                id='__prune_node_stats__',
                replace_existing=True,
            )
        except Exception as e:
            logger.error(f"⚠️ Scheduler Failed to Start: {e}")

    async def prune_stale_node_stats(self):
        """Delete NodeStats rows for nodes that have been offline for >24h."""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        async with db_module.AsyncSessionLocal() as session:
            offline_result = await session.execute(
                select(Node.node_id).where(Node.last_seen < cutoff)
            )
            stale_ids = [r[0] for r in offline_result.all()]
            if stale_ids:
                await session.execute(delete(NodeStats).where(NodeStats.node_id.in_(stale_ids)))
                await session.commit()
                logger.info(f"🧹 Pruned NodeStats for {len(stale_ids)} stale nodes")

    async def sync_scheduler(self):
        """Syncs DB ScheduledJobs with APScheduler."""
        logger.info("🔄 Syncing Scheduler...")
        self.scheduler.remove_all_jobs()
        async with db_module.AsyncSessionLocal() as session:
            result = await session.execute(select(ScheduledJob).where(ScheduledJob.is_active == True))
            jobs = result.scalars().all()
            count = 0
            for j in jobs:
                if j.schedule_cron:
                     try:
                         parts = j.schedule_cron.split()
                         if len(parts) == 5:
                             self.scheduler.add_job(
                                 self.execute_scheduled_job, 
                                 'cron', 
                                 args=[j.id], 
                                 minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4],
                                 id=j.id
                             )
                             count += 1
                     except Exception as e:
                         logger.error(f"❌ Failed to schedule {j.name}: {e}")
        logger.info(f"✅ Scheduler Synced: {count} jobs active.")

    async def execute_scheduled_job(self, scheduled_job_id: str):
        """Callback for APScheduler. Creates an Execution Job from the Definition."""
        logger.info(f"⏰ Triggering Scheduled Job: {scheduled_job_id}")
        async with db_module.AsyncSessionLocal() as session:
            result = await session.execute(select(ScheduledJob).where(ScheduledJob.id == scheduled_job_id))
            s_job = result.scalar_one_or_none()
            
            if not s_job or not s_job.is_active:
                 logger.warning(f"⚠️ Job {scheduled_job_id} not found or inactive.")
                 return

            # Construct Execution Payload
            execution_guid = uuid.uuid4().hex
            
            payload_dict = {
                "script_content": s_job.script_content,
                "signature": s_job.signature_payload, 
                "secrets": {} 
            }
            
            payload_json = json.dumps(payload_dict)
            
            # Create Job
            new_job = Job(
                guid=execution_guid,
                task_type="python_script",
                payload=payload_json,
                status="PENDING",
                node_id=s_job.target_node_id,
                target_tags=s_job.target_tags,
                scheduled_job_id=s_job.id
            )
            session.add(new_job)
            await session.commit()
            logger.info(f"✅ Job {execution_guid} created for scheduled task {s_job.name}")

    async def create_job_definition(self, def_req: JobDefinitionCreate, current_user: User, db_session: AsyncSession) -> ScheduledJob:
        """Creates a new Scheduled Job. VALIDATES SIGNATURE First."""
        # 1. Load Signature
        res = await db_session.execute(select(Signature).where(Signature.id == def_req.signature_id))
        sig = res.scalar_one_or_none()
        if not sig:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Signature ID not found")
            
        # 2. Verify Signature
        try:
            SignatureService.verify_payload_signature(sig.public_key, def_req.signature, def_req.script_content)
            logger.info(f"✅ Signature Validated for new job: {def_req.name}")
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail=f"Invalid Signature: {str(e)}")

        # 3. Store Definition
        new_def = ScheduledJob(
            id=uuid.uuid4().hex,
            name=def_req.name,
            script_content=def_req.script_content,
            signature_id=def_req.signature_id,
            signature_payload=def_req.signature, 
            schedule_cron=def_req.schedule_cron,
            target_node_id=def_req.target_node_id,
            target_tags=json.dumps(def_req.target_tags) if def_req.target_tags else None,
            created_by=current_user.username
        )
        db_session.add(new_def)
        await db_session.commit()
        await db_session.refresh(new_def)
        
        # 4. Update Scheduler
        if new_def.is_active and new_def.schedule_cron:
            await self.sync_scheduler()
        
        return new_def

    async def list_job_definitions(self, db_session: AsyncSession) -> List[ScheduledJob]:
        """Lists all job definitions."""
        result = await db_session.execute(select(ScheduledJob))
        return result.scalars().all()

# Global Instance
scheduler_service = SchedulerService()
