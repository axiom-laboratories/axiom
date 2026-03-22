import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import delete
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .. import db as db_module
from ..db import ScheduledJob, Job, Signature, Node, NodeStats, AsyncSession, User, Config, ExecutionRecord
from ..models import JobDefinitionCreate, JobDefinitionResponse, JobDefinitionUpdate
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
            self.scheduler.add_job(
                self.prune_execution_history,
                'interval',
                hours=24,
                id='__prune_execution_history__',
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

    async def prune_execution_history(self):
        """Prune old execution history based on retention config."""
        async with db_module.AsyncSessionLocal() as session:
            # 1. Get retention period
            res = await session.execute(select(Config.value).where(Config.key == 'history_retention_days'))
            retention_str = res.scalar_one_or_none()
            retention_days = int(retention_str) if retention_str else 30
            
            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            
            # 2. Perform deletion
            result = await session.execute(
                delete(ExecutionRecord).where(ExecutionRecord.started_at < cutoff)
            )
            count = result.rowcount
            await session.commit()
            
            if count > 0:
                logger.info(f"🧹 Pruned {count} old execution records (cutoff: {cutoff.isoformat()})")

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
                                 id=j.id,
                                 misfire_grace_time=60
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

            # Status governance guard (Phase 17) — must come after is_active check
            SKIP_STATUSES = {"DRAFT", "REVOKED", "DEPRECATED"}
            if hasattr(s_job, 'status') and s_job.status in SKIP_STATUSES:
                logger.warning(f"Skipping cron fire for '{s_job.name}' — status={s_job.status}")
                from ..db import AuditLog as _AuditLog
                session.add(_AuditLog(
                    username="scheduler",
                    action=f"job:{s_job.status.lower()}_skip",
                    resource_id=s_job.id,
                    detail=json.dumps({"status": s_job.status, "name": s_job.name}),
                ))
                await session.commit()
                return

            # Cron overlap guard: skip if a previous instance is still active
            from sqlalchemy import desc as _sched_desc
            overlap_result = await session.execute(
                select(Job)
                .where(Job.scheduled_job_id == s_job.id)
                .where(Job.status.in_(["PENDING", "ASSIGNED", "RETRYING"]))
                .order_by(_sched_desc(Job.created_at))
                .limit(1)
            )
            active_job = overlap_result.scalar_one_or_none()
            if active_job:
                logger.warning(
                    f"Skipping cron fire for '{s_job.name}' — previous job {active_job.guid} "
                    f"still active (status: {active_job.status})"
                )
                from ..db import AuditLog as _AuditLog
                session.add(_AuditLog(
                    username="scheduler",
                    action="job:cron_skip",
                    resource_id=s_job.id,
                    detail=f"Skipped fire; job {active_job.guid} still {active_job.status}",
                ))
                await session.commit()
                return

            # Construct Execution Payload
            execution_guid = uuid.uuid4().hex
            runtime = getattr(s_job, 'runtime', None) or 'python'

            payload_dict = {
                "script_content": s_job.script_content,
                "signature": s_job.signature_payload,
                "secrets": {},
                "runtime": runtime,
            }

            payload_json = json.dumps(payload_dict)

            # Create Job
            new_job = Job(
                guid=execution_guid,
                task_type="script",
                payload=payload_json,
                status="PENDING",
                node_id=s_job.target_node_id,
                target_tags=s_job.target_tags,
                scheduled_job_id=s_job.id,
                max_retries=s_job.max_retries,
                backoff_multiplier=s_job.backoff_multiplier,
                timeout_minutes=s_job.timeout_minutes,
                env_tag=s_job.env_tag,
                runtime=runtime,
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
            created_by=current_user.username,
            runtime=def_req.runtime or "python",
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

    async def get_job_definition(self, job_id: str, db_session: AsyncSession) -> ScheduledJob:
        """Fetches a single job definition by ID."""
        from fastapi import HTTPException
        result = await db_session.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job definition not found")
        return job

    async def update_job_definition(self, job_id: str, update_req: JobDefinitionUpdate, current_user: User, db_session: AsyncSession) -> ScheduledJob:
        """Partially updates a scheduled job definition. Re-validates signature if script changes."""
        from fastapi import HTTPException
        result = await db_session.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job definition not found")

        # If script content is changing, a new signature is required
        if update_req.script_content is not None and update_req.script_content != job.script_content:
            if not update_req.signature or not update_req.signature_id:
                raise HTTPException(
                    status_code=400,
                    detail="A new signature and signature_id are required when changing script content"
                )
            sig_result = await db_session.execute(select(Signature).where(Signature.id == update_req.signature_id))
            sig = sig_result.scalar_one_or_none()
            if not sig:
                raise HTTPException(status_code=404, detail="Signature ID not found")
            try:
                SignatureService.verify_payload_signature(sig.public_key, update_req.signature, update_req.script_content)
                logger.info(f"✅ Signature re-validated for job update: {job_id}")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid Signature: {str(e)}")
            job.script_content = update_req.script_content
            job.signature_id = update_req.signature_id
            job.signature_payload = update_req.signature
        elif update_req.script_content is not None:
            # Same content — update without re-sign
            job.script_content = update_req.script_content

        # Apply remaining optional fields (skip None = not provided)
        if update_req.name is not None:
            job.name = update_req.name
        if update_req.schedule_cron is not None:
            job.schedule_cron = update_req.schedule_cron or None
        if update_req.target_node_id is not None:
            job.target_node_id = update_req.target_node_id or None
        if update_req.target_tags is not None:
            job.target_tags = json.dumps(update_req.target_tags) if update_req.target_tags else None
        if update_req.capability_requirements is not None:
            job.capability_requirements = json.dumps(update_req.capability_requirements) if update_req.capability_requirements else None
        if update_req.max_retries is not None:
            job.max_retries = update_req.max_retries
        if update_req.backoff_multiplier is not None:
            job.backoff_multiplier = update_req.backoff_multiplier
        if update_req.timeout_minutes is not None:
            job.timeout_minutes = update_req.timeout_minutes
        if update_req.status is not None:
            job.status = update_req.status
        if hasattr(update_req, 'runtime') and update_req.runtime is not None:
            job.runtime = update_req.runtime

        job.updated_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(job)
        await self.sync_scheduler()
        return job

# Global Instance
scheduler_service = SchedulerService()
