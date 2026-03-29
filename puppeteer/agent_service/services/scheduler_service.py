import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import delete, func
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .. import db as db_module
from ..db import ScheduledJob, Job, Signature, Node, NodeStats, AsyncSession, User, Config, ExecutionRecord, ScheduledFireLog, JobDefinitionVersion
from ..models import JobDefinitionCreate, JobDefinitionResponse, JobDefinitionUpdate
from .signature_service import SignatureService
from .alert_service import AlertService
from ..deps import audit

logger = logging.getLogger(__name__)


def expected_fires_in_window(cron_expr: str, window_start: datetime, window_end: datetime) -> List[datetime]:
    """Return all expected fire times for a cron expression within [window_start, window_end)."""
    parts = cron_expr.split()
    if len(parts) != 5:
        return []
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1], day=parts[2],
        month=parts[3], day_of_week=parts[4]
    )
    fires = []
    t = window_start
    while True:
        next_fire = trigger.get_next_fire_time(None, t)
        if next_fire is None or next_fire.replace(tzinfo=None) >= window_end:
            break
        fires.append(next_fire.replace(tzinfo=None))
        t = next_fire + timedelta(seconds=1)
    return fires


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
            self.scheduler.add_job(
                self.sweep_dispatch_timeouts,
                'interval',
                minutes=5,
                id='__dispatch_timeout_sweeper__',
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
        """Prune old execution history based on retention config. Respects pinned=True rows."""
        async with db_module.AsyncSessionLocal() as session:
            # 1. Get retention period — prefer execution_retention_days, fallback to history_retention_days, then 14
            res = await session.execute(select(Config.value).where(Config.key == 'execution_retention_days'))
            retention_str = res.scalar_one_or_none()
            if not retention_str:
                res2 = await session.execute(select(Config.value).where(Config.key == 'history_retention_days'))
                retention_str = res2.scalar_one_or_none()
            retention_days = int(retention_str) if retention_str else 14

            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            # 2. Perform deletion — only unpinned rows
            result = await session.execute(
                delete(ExecutionRecord).where(
                    ExecutionRecord.completed_at < cutoff,
                    ExecutionRecord.pinned.is_(False),
                )
            )
            count = result.rowcount
            await session.commit()

            if count > 0:
                logger.info(f"🧹 Pruned {count} old execution records (cutoff: {cutoff.isoformat()})")

            # 3. Prune ScheduledFireLog rows older than 31 days
            fire_log_cutoff = datetime.utcnow() - timedelta(days=31)
            await session.execute(
                delete(ScheduledFireLog).where(ScheduledFireLog.created_at < fire_log_cutoff)
            )
            await session.commit()

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

            # Write a ScheduledFireLog row immediately (before any skip checks)
            fire_time = datetime.utcnow()
            fire_log = ScheduledFireLog(
                scheduled_job_id=scheduled_job_id,
                expected_at=fire_time,
                status='fired',
            )
            session.add(fire_log)
            await session.flush()  # get fire_log.id without committing

            # Status governance guard (Phase 17) — must come after is_active check
            SKIP_STATUSES = {"DRAFT", "REVOKED", "DEPRECATED"}
            if hasattr(s_job, 'status') and s_job.status in SKIP_STATUSES:
                reason = (
                    "Skipped: job in DRAFT state, pending re-signing"
                    if s_job.status == "DRAFT"
                    else f"Skipped: job status={s_job.status}"
                )
                logger.warning(f"Skipping cron fire for '{s_job.name}' — {reason}")
                detail = json.dumps({"status": s_job.status, "reason": reason, "name": s_job.name})
                try:
                    from sqlalchemy import text as _text
                    from datetime import datetime as _dt
                    await session.execute(
                        _text("INSERT INTO audit_log (timestamp, username, action, resource_id, detail) VALUES (:ts, :u, :a, :r, :d)"),
                        {"ts": _dt.utcnow(), "u": "scheduler", "a": f"job:{s_job.status.lower()}_skip", "r": s_job.id, "d": detail},
                    )
                except Exception:
                    pass  # CE mode: audit_log table absent — silently ignore
                fire_log.status = 'skipped_draft'
                await session.commit()
                return

            # Cron overlap guard: skip if a previous instance is still active
            # allow_overlap=True skips the overlap check entirely
            if not getattr(s_job, 'allow_overlap', False):
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
                    try:
                        from ..db import AuditLog as _AuditLog
                        session.add(_AuditLog(
                            username="scheduler",
                            action="job:cron_skip",
                            resource_id=s_job.id,
                            detail=f"Skipped fire; job {active_job.guid} still {active_job.status}",
                        ))
                    except Exception:
                        pass  # CE mode: AuditLog may be absent
                    fire_log.status = 'skipped_overlap'
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

            # Stamp the current signed version on the dispatch
            ver_result = await session.execute(
                select(JobDefinitionVersion)
                .where(JobDefinitionVersion.job_def_id == s_job.id, JobDefinitionVersion.is_signed == True)
                .order_by(JobDefinitionVersion.version_number.desc())
                .limit(1)
            )
            current_version = ver_result.scalar_one_or_none()

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
                name=s_job.name,          # SRCH-04: auto-populate from scheduled job name
                created_by=s_job.created_by,  # SRCH-03: stamp submitter
                definition_version_id=current_version.id if current_version else None,
            )
            session.add(new_job)
            await session.commit()
            logger.info(f"✅ Job {execution_guid} created for scheduled task {s_job.name}")

    async def sweep_dispatch_timeouts(self):
        """Mark PENDING jobs past their dispatch_timeout_minutes as FAILED."""
        async with db_module.AsyncSessionLocal() as session:
            now = datetime.utcnow()
            result = await session.execute(
                select(Job).where(Job.status == "PENDING", Job.dispatch_timeout_minutes.isnot(None))
            )
            jobs = result.scalars().all()
            failed_count = 0
            for job in jobs:
                deadline = job.created_at + timedelta(minutes=job.dispatch_timeout_minutes)
                if now > deadline:
                    job.status = "FAILED"
                    job.result = json.dumps({"error": f"Dispatch timeout: no node picked up the job within {job.dispatch_timeout_minutes} minutes"})
                    job.completed_at = now
                    failed_count += 1
            if failed_count:
                await session.commit()
                logger.info(f"Dispatch timeout sweeper: failed {failed_count} jobs")

    async def _create_version_snapshot(
        self,
        db_session: AsyncSession,
        job: ScheduledJob,
        created_by: str,
        is_signed: bool,
        change_summary: Optional[str] = None,
    ) -> "JobDefinitionVersion":
        """Write an immutable version snapshot for a job definition. Auto-increments version_number."""
        import uuid as _uuid
        result = await db_session.execute(
            select(func.max(JobDefinitionVersion.version_number)).where(
                JobDefinitionVersion.job_def_id == job.id
            )
        )
        max_ver = result.scalar_one_or_none() or 0
        version = JobDefinitionVersion(
            id=_uuid.uuid4().hex,
            job_def_id=job.id,
            version_number=max_ver + 1,
            script_content=job.script_content,
            signature_id=job.signature_id,
            signature_payload=job.signature_payload,
            cron_expression=job.schedule_cron,
            target_tags=job.target_tags,
            target_node_id=job.target_node_id,
            runtime=job.runtime,
            max_retries=job.max_retries,
            backoff_multiplier=job.backoff_multiplier,
            change_summary=change_summary,
            is_signed=is_signed,
            created_at=datetime.utcnow(),
            created_by=created_by,
        )
        db_session.add(version)
        return version

    async def get_scheduling_health(self, window: str, db: AsyncSession) -> dict:
        """Return aggregate and per-definition scheduling health for the given window."""
        window_hours = {"24h": 24, "7d": 168, "30d": 720}.get(window, 24)
        now = datetime.utcnow()
        window_start = now - timedelta(hours=window_hours)

        # Query ScheduledFireLog rows in the window grouped by job_id + status
        log_result = await db.execute(
            select(ScheduledFireLog).where(
                ScheduledFireLog.expected_at >= window_start,
                ScheduledFireLog.expected_at <= now,
            )
        )
        log_rows = log_result.scalars().all()

        # Aggregate counts by scheduled_job_id
        from collections import defaultdict
        counts: dict = defaultdict(lambda: {"fired": 0, "skipped": 0, "failed": 0})
        for row in log_rows:
            jid = row.scheduled_job_id
            if row.status == 'fired':
                counts[jid]["fired"] += 1
            elif row.status in ('skipped_draft', 'skipped_overlap'):
                counts[jid]["skipped"] += 1
            # 'failed' status could be added in the future

        # Also count FAILED Job rows dispatched from each scheduled job in the window
        failed_result = await db.execute(
            select(Job.scheduled_job_id, func.count(Job.guid)).where(
                Job.scheduled_job_id.isnot(None),
                Job.status == "FAILED",
                Job.created_at >= window_start,
            ).group_by(Job.scheduled_job_id)
        )
        for jid, cnt in failed_result.all():
            counts[jid]["failed"] += cnt

        # Load all active ScheduledJobs with cron schedules
        active_result = await db.execute(
            select(ScheduledJob).where(
                ScheduledJob.is_active == True,
                ScheduledJob.schedule_cron.isnot(None),
            )
        )
        active_jobs = active_result.scalars().all()
        job_map = {j.id: j for j in active_jobs}

        # Compute LATE/MISSED via expected_fires_in_window vs. actual fire log rows
        grace = timedelta(minutes=5)
        definition_rows = []

        # Aggregate totals
        total_fired = 0
        total_skipped = 0
        total_failed = 0
        total_late = 0
        total_missed = 0

        for sj in active_jobs:
            jid = sj.id
            # Skip DRAFT/REVOKED jobs — they intentionally skip; exclude from missed calc
            if hasattr(sj, 'status') and sj.status in ("DRAFT", "REVOKED", "DEPRECATED"):
                continue

            c = counts[jid]
            fired = c["fired"]
            skipped = c["skipped"]
            failed = c["failed"]

            # Compute expected fires and classify late/missed
            late = 0
            missed = 0
            if sj.schedule_cron:
                expected = expected_fires_in_window(sj.schedule_cron, window_start, now)
                # Get actual fire log rows for this job
                actual_times = [r.expected_at for r in log_rows if r.scheduled_job_id == jid]
                for exp_t in expected:
                    # Check if there's an actual fire within 5 min of expected
                    matched = any(abs((actual - exp_t).total_seconds()) <= 300 for actual in actual_times)
                    if not matched:
                        # Unmatched — compute next expected fire
                        time_since = now - exp_t
                        if time_since > grace:
                            # Compute next fire after exp_t
                            try:
                                next_fires = expected_fires_in_window(
                                    sj.schedule_cron, exp_t + timedelta(seconds=1), now + timedelta(hours=1)
                                )
                                next_fire = next_fires[0] if next_fires else None
                            except Exception:
                                next_fire = None
                            if next_fire is not None and next_fire <= now:
                                missed += 1
                            else:
                                late += 1

            health = "ok"
            if missed > 0 or failed > 0:
                health = "error"
            elif late > 0:
                health = "warning"

            total_fired += fired
            total_skipped += skipped
            total_failed += failed
            total_late += late
            total_missed += missed

            definition_rows.append({
                "id": jid,
                "name": sj.name,
                "fired": fired,
                "skipped": skipped,
                "failed": failed,
                "missed": missed,
                "health": health,
            })

        return {
            "aggregate": {
                "fired": total_fired,
                "skipped": total_skipped,
                "failed": total_failed,
                "late": total_late,
                "missed": total_missed,
            },
            "definitions": definition_rows,
        }

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
            raise HTTPException(status_code=403, detail=(
                "Signature verification failed — the script content does not match the provided signature. "
                "Ensure you signed the exact script bytes with the private key paired to the registered public key. "
                "See the Signatures page in the dashboard for getting-started instructions."
            ))

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

        # 4. Create initial version snapshot
        await self._create_version_snapshot(db_session, new_def, current_user.username, is_signed=True, change_summary="Initial version")
        await db_session.commit()

        # 5. Update Scheduler
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

        # Case (e): Re-sign without script change — signature + signature_id provided, no script_content change
        if (
            update_req.signature
            and update_req.signature_id
            and (update_req.script_content is None or update_req.script_content == job.script_content)
        ):
            sig_result = await db_session.execute(select(Signature).where(Signature.id == update_req.signature_id))
            sig = sig_result.scalar_one_or_none()
            if not sig:
                raise HTTPException(status_code=404, detail="Signature ID not found")
            try:
                SignatureService.verify_payload_signature(sig.public_key, update_req.signature, job.script_content)
                logger.info(f"✅ Signature re-validated for job re-sign: {job_id}")
            except Exception as e:
                raise HTTPException(status_code=400, detail=(
                    "Signature verification failed — ensure you signed the current script content "
                    "with the private key paired to the selected registered key. "
                    "See the Signatures page in the dashboard for getting-started instructions."
                ))
            job.signature_id = update_req.signature_id
            job.signature_payload = update_req.signature
            job.status = "ACTIVE"
            audit(db_session, current_user, "job_definition:reactivated", job.id, {"name": job.name})

        # Case (a): Signature ID replaced without a valid accompanying signature payload → DRAFT
        elif update_req.signature_id is not None and update_req.signature_id != job.signature_id and not update_req.signature:
            no_script_change = (update_req.script_content is None or update_req.script_content == job.script_content)
            if no_script_change and job.status == "ACTIVE":
                job.status = "DRAFT"
                await AlertService.create_alert(
                    db_session,
                    type="scheduled_job_draft",
                    severity="WARNING",
                    message=f"Scheduled job '{job.name}' moved to DRAFT — re-sign required before next cron fire.",
                    resource_id=job.id,
                )
                audit(db_session, current_user, "job_definition:draft", job.id,
                      {"previous_status": "ACTIVE", "name": job.name, "reason": "signature_id_change_without_signature"})

        # Case (b/c/d): Script content changed
        elif update_req.script_content is not None and update_req.script_content != job.script_content:
            if update_req.signature and update_req.signature_id:
                # Case (b/c): new signature provided — verify it
                sig_result = await db_session.execute(select(Signature).where(Signature.id == update_req.signature_id))
                sig = sig_result.scalar_one_or_none()
                if not sig:
                    raise HTTPException(status_code=404, detail="Signature ID not found")
                try:
                    SignatureService.verify_payload_signature(sig.public_key, update_req.signature, update_req.script_content)
                    logger.info(f"✅ Signature re-validated for job update: {job_id}")
                except Exception as e:
                    raise HTTPException(status_code=400, detail=(
                        "Signature verification failed — ensure you signed the updated script content "
                        "with the private key paired to the selected registered key. "
                        "See the Signatures page in the dashboard for getting-started instructions."
                    ))
                job.script_content = update_req.script_content
                job.signature_id = update_req.signature_id
                job.signature_payload = update_req.signature
            else:
                # Case (d): script changed, no signature → soft DRAFT transition
                job.script_content = update_req.script_content
                if job.status == "ACTIVE":
                    job.status = "DRAFT"
                    await AlertService.create_alert(
                        db_session,
                        type="scheduled_job_draft",
                        severity="WARNING",
                        message=f"Scheduled job '{job.name}' moved to DRAFT — re-sign required before next cron fire.",
                        resource_id=job.id,
                    )
                    audit(db_session, current_user, "job_definition:draft", job.id,
                          {"previous_status": "ACTIVE", "name": job.name})
                # If already DRAFT: just update content, no new alert

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

        # Build change summary
        change_parts = []
        if update_req.script_content is not None and update_req.script_content != job.script_content:
            change_parts.append("script updated")
        if update_req.schedule_cron is not None:
            change_parts.append("schedule updated")
        if update_req.target_tags is not None:
            change_parts.append("tags updated")
        if (
            update_req.signature
            and update_req.signature_id
            and (update_req.script_content is None or update_req.script_content == job.script_content)
            and not change_parts
        ):
            change_parts.append("re-signed")
        change_summary = "; ".join(change_parts) if change_parts else "updated"

        # is_signed: True if job will be ACTIVE after this update
        final_status = update_req.status if update_req.status is not None else job.status
        is_signed = final_status == "ACTIVE"

        await self._create_version_snapshot(db_session, job, current_user.username, is_signed=is_signed, change_summary=change_summary)

        job.updated_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(job)
        await self.sync_scheduler()
        return job

    async def list_job_definition_versions(self, job_id: str, db_session: AsyncSession) -> list:
        """Returns all versions for a job definition, ordered newest first."""
        from fastapi import HTTPException
        # Verify definition exists
        result = await db_session.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Job definition not found")
        ver_result = await db_session.execute(
            select(JobDefinitionVersion)
            .where(JobDefinitionVersion.job_def_id == job_id)
            .order_by(JobDefinitionVersion.version_number.desc())
        )
        return ver_result.scalars().all()

    async def get_job_definition_version(self, job_id: str, version_num: int, db_session: AsyncSession):
        """Returns a specific version of a job definition."""
        from fastapi import HTTPException
        ver_result = await db_session.execute(
            select(JobDefinitionVersion)
            .where(JobDefinitionVersion.job_def_id == job_id, JobDefinitionVersion.version_number == version_num)
        )
        ver = ver_result.scalar_one_or_none()
        if not ver:
            raise HTTPException(status_code=404, detail="Version not found")
        return ver

# Global Instance
scheduler_service = SchedulerService()
