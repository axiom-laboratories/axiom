import logging
import uuid
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import desc, func
from ..db import Job, Node, AsyncSession
from ..models import (
    ResultReport, JobResponse, JobCreate, WorkResponse, PollResponse, 
    NodeConfig, HeartbeatPayload
)
from ..security import mask_secrets, encrypt_secrets, decrypt_secrets

logger = logging.getLogger(__name__)

class JobService:
    @staticmethod
    async def list_jobs(db: AsyncSession) -> List[dict]:
        """For the Dashboard. Filters system jobs by default."""
        result = await db.execute(
            select(Job).where(Job.task_type != 'system_heartbeat') \
            .order_by(desc(Job.created_at)).limit(50)
        )
        jobs = result.scalars().all()
        
        response_jobs = []
        for job in jobs:
            payload = json.loads(job.payload)
            
            # Calculate duration
            duration = None
            if job.started_at:
                end = job.completed_at or datetime.utcnow()
                duration = (end - job.started_at).total_seconds()

            response_jobs.append({
                "guid": job.guid,
                "status": job.status,
                "payload": mask_secrets(payload), 
                "result": json.loads(job.result) if job.result else None,
                "node_id": job.node_id,
                "started_at": job.started_at,
                "duration_seconds": duration,
                "target_tags": json.loads(job.target_tags) if job.target_tags else None
            })
        return response_jobs

    @staticmethod
    async def create_job(job_req: JobCreate, db: AsyncSession) -> dict:
        """Received from Model Service or Authorized User."""
        guid = str(uuid.uuid4())
        
        # Encrypt secrets before storing
        encrypted_payload = encrypt_secrets(job_req.payload)
        
        new_job = Job(
            guid=guid,
            task_type=job_req.task_type,
            status="PENDING",
            payload=json.dumps(encrypted_payload),
            target_tags=json.dumps(job_req.target_tags) if job_req.target_tags else None,
            created_at=datetime.utcnow()
        )
        
        try:
            db.add(new_job)
            await db.commit()
            await db.refresh(new_job)
        except Exception as e:
            await db.rollback()
            raise e
        
        return {"guid": guid, "status": "PENDING", "payload": encrypted_payload, "target_tags": job_req.target_tags}

    @staticmethod
    async def pull_work(node_id: str, node_ip: str, db: AsyncSession) -> PollResponse:
        """Called by Environment Nodes."""
        # 1. Fetch Node Configuration
        result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = result.scalar_one_or_none()
        
        # Default Config
        concurrency = 5
        memory = "512m"
        
        if node:
            concurrency = node.concurrency_limit
            memory = node.job_memory_limit
            node.last_seen = datetime.utcnow()
            if node.ip != node_ip:
                 node.ip = node_ip
        else:
            node = Node(
                node_id=node_id, 
                hostname=node_id, 
                ip=node_ip, 
                status="ONLINE", 
                concurrency_limit=concurrency,
                job_memory_limit=memory
            )
            db.add(node)
        
        await db.commit()
        
        node_config = NodeConfig(concurrency_limit=concurrency, job_memory_limit=memory)

        # 2. Check Concurrency Limit
        result = await db.execute(select(func.count(Job.guid)).where(Job.status == 'ASSIGNED', Job.node_id == node_id))
        active_count = result.scalar()
        
        if active_count >= concurrency:
            return PollResponse(job=None, config=node_config)
        
        # 3. Find highest priority PENDING job matching criteria
        result = await db.execute(
            select(Job).where(
                Job.status == 'PENDING'
            ).where(
                (Job.node_id == None) | (Job.node_id == node_id)
            ).order_by(Job.created_at.asc()).limit(50)
        )
        jobs = result.scalars().all()
        
        selected_job = None
        node_tags_list = json.loads(node.tags) if node and node.tags else []

        for candidate in jobs:
            # Check Tags
            if candidate.target_tags:
                try:
                    req_tags = json.loads(candidate.target_tags)
                    if not isinstance(req_tags, list):
                         continue
                    if not all(t in node_tags_list for t in req_tags):
                        continue
                except:
                    continue
                    
            selected_job = candidate
            break
        
        if not selected_job:
            return PollResponse(job=None, config=node_config)
            
        selected_job.status = 'ASSIGNED'
        selected_job.node_id = node_id
        selected_job.started_at = datetime.utcnow()
        
        encrypted_payload = json.loads(selected_job.payload)
        payload = decrypt_secrets(encrypted_payload)
        
        await db.commit()
        
        work_resp = WorkResponse(guid=selected_job.guid, task_type=selected_job.task_type, payload=payload)
        return PollResponse(job=work_resp, config=node_config)

    @staticmethod
    async def report_result(guid: str, report: ResultReport, node_ip: str, db: AsyncSession) -> dict:
        """Matches 'Environment -> Agent' reporting."""
        result = await db.execute(select(Job).where(Job.guid == guid))
        job = result.scalar_one_or_none()
        
        if not job:
            return None # Handle in route
            
        # HEARTBEAT LOGIC
        if job.task_type == "system_heartbeat":
            stats_json = None
            if report.result and "stats" in report.result:
                stats_json = json.dumps(report.result["stats"])
                
            node_id = job.node_id or node_ip
            
            sub_result = await db.execute(select(Node).where(Node.node_id == node_id))
            node = sub_result.scalar_one_or_none()
            if node:
                node.last_seen = datetime.utcnow()
                node.status = "ONLINE"
                if stats_json:
                    node.stats = stats_json
            else:
                node = Node(node_id=node_id, hostname=node_id, ip=node_ip, status="ONLINE", stats=stats_json)
                db.add(node)

        job.status = "COMPLETED" if report.success else "FAILED"
        job.result = json.dumps(report.result) if report.result else None
        job.completed_at = datetime.utcnow()

        await db.commit()
        return {"status": "updated"}
