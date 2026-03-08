import json
import logging
import secrets
from typing import Dict, List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from ..db import Trigger, ScheduledJob, Job
from .job_service import JobService

logger = logging.getLogger(__name__)

class TriggerService:
    @staticmethod
    async def fire_trigger(slug: str, token: str, payload_data: Dict, db: AsyncSession) -> Dict:
        """Resolves a trigger slug, verifies the token, and launches the job."""
        # 1. Fetch Trigger
        result = await db.execute(select(Trigger).where(Trigger.slug == slug))
        trigger = result.scalar_one_or_none()
        
        if not trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")
        
        if not trigger.is_active:
            raise HTTPException(status_code=403, detail="Trigger is inactive")
            
        # 2. Verify Token
        if trigger.secret_token != token:
            logger.warning(f"🚨 Invalid trigger token attempt for slug: {slug}")
            raise HTTPException(status_code=401, detail="Invalid trigger key")
            
        # 3. Fetch Job Definition
        job_def_res = await db.execute(select(ScheduledJob).where(ScheduledJob.id == trigger.job_definition_id))
        job_def = job_def_res.scalar_one_or_none()
        
        if not job_def:
            logger.error(f"❌ Trigger {slug} references missing job definition {trigger.job_definition_id}")
            raise HTTPException(status_code=500, detail="Associated job definition not found")

        # 4. Construct Job Request
        # Merge trigger-provided data into the job's default payload
        base_payload = json.loads(job_def.payload) if hasattr(job_def, 'payload') and job_def.payload else {}
        # If ScheduledJob doesn't have a payload field directly (it has script_content), 
        # we treat script_content as the payload or wrap it.
        # ScheduledJob has: name, script_content, signature_payload, target_tags, etc.
        
        from ..models import JobCreate
        job_req = JobCreate(
            task_type="python_script", # Default for scheduled jobs
            payload={
                "script": job_def.script_content,
                "signature": job_def.signature_payload,
                "vars": payload_data # Injected from trigger caller
            },
            target_tags=json.loads(job_def.target_tags) if job_def.target_tags else None,
            capability_requirements=json.loads(job_def.capability_requirements) if job_def.capability_requirements else None,
            max_retries=job_def.max_retries
        )
        
        # 5. Launch
        job_result = await JobService.create_job(job_req, db)
        
        logger.info(f"🚀 Trigger {slug} fired successfully. Job created: {job_result['guid']}")
        return {
            "status": "triggered",
            "job_guid": job_result["guid"],
            "slug": slug
        }

    @staticmethod
    async def list_triggers(db: AsyncSession) -> List[Trigger]:
        result = await db.execute(select(Trigger).order_by(Trigger.created_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def create_trigger(name: str, slug: str, job_definition_id: str, db: AsyncSession) -> Trigger:
        # Check uniqueness
        existing = await db.execute(select(Trigger).where(Trigger.slug == slug))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already in use")
            
        token = "trg_" + secrets.token_hex(24)
        new_trigger = Trigger(
            name=name,
            slug=slug,
            job_definition_id=job_definition_id,
            secret_token=token
        )
        db.add(new_trigger)
        await db.commit()
        await db.refresh(new_trigger)
        return new_trigger

    @staticmethod
    async def delete_trigger(trigger_id: str, db: AsyncSession) -> bool:
        result = await db.execute(select(Trigger).where(Trigger.id == trigger_id))
        trigger = result.scalar_one_or_none()
        if not trigger:
            return False
        await db.delete(trigger)
        await db.commit()
        return True

    @staticmethod
    async def update_trigger(trigger_id: str, is_active: Optional[bool], db: AsyncSession) -> Trigger:
        result = await db.execute(select(Trigger).where(Trigger.id == trigger_id))
        trigger = result.scalar_one_or_none()
        if not trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")
        if is_active is not None:
            trigger.is_active = is_active
        await db.commit()
        await db.refresh(trigger)
        return trigger

    @staticmethod
    async def regenerate_token(trigger_id: str, db: AsyncSession) -> Trigger:
        result = await db.execute(select(Trigger).where(Trigger.id == trigger_id))
        trigger = result.scalar_one_or_none()
        if not trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")
        trigger.secret_token = "trg_" + secrets.token_hex(24)
        await db.commit()
        await db.refresh(trigger)
        return trigger

trigger_service = TriggerService()
