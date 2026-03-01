import logging
import uuid
import json
from datetime import datetime
from typing import List, Optional
from packaging.version import Version, InvalidVersion
from sqlalchemy.future import select
from sqlalchemy import desc, func, delete
from ..db import Job, Node, NodeStats, AsyncSession
from ..models import (
    ResultReport, JobResponse, JobCreate, WorkResponse, PollResponse, 
    NodeConfig, HeartbeatPayload
)
from ..security import mask_secrets, encrypt_secrets, decrypt_secrets

logger = logging.getLogger(__name__)


def parse_bytes(s: str) -> int:
    """Convert memory string like '300m', '2g', '1024k' to bytes."""
    s = s.strip().lower()
    if s.endswith('g'):
        return int(s[:-1]) * 1024 ** 3
    elif s.endswith('m'):
        return int(s[:-1]) * 1024 ** 2
    elif s.endswith('k'):
        return int(s[:-1]) * 1024
    return int(s)


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
            capability_requirements=json.dumps(job_req.capability_requirements) if job_req.capability_requirements else None,
            memory_limit=job_req.memory_limit,
            cpu_limit=job_req.cpu_limit,
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
        node_caps_dict = json.loads(node.capabilities) if node and node.capabilities else {}

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
            
            # Check Memory Limit
            if candidate.memory_limit and node.job_memory_limit:
                try:
                    if parse_bytes(candidate.memory_limit) > parse_bytes(node.job_memory_limit):
                        continue
                except Exception:
                    pass

            # Check Capabilities
            if candidate.capability_requirements:
                try:
                    req_caps = json.loads(candidate.capability_requirements)
                    if not isinstance(req_caps, dict):
                         continue
                    # Match: Node must have ALL required capabilities,
                    # and versions must be >= required (proper semver comparison)
                    match = True
                    for cap_name, min_version in req_caps.items():
                        if cap_name not in node_caps_dict:
                            match = False
                            break
                        node_ver = node_caps_dict[cap_name]
                        try:
                            satisfies = Version(node_ver) >= Version(min_version)
                        except InvalidVersion:
                            satisfies = node_ver >= min_version
                        if not satisfies:
                            match = False
                            break
                    if not match:
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
        
        work_resp = WorkResponse(
            guid=selected_job.guid,
            task_type=selected_job.task_type,
            payload=payload,
            memory_limit=selected_job.memory_limit,
            cpu_limit=selected_job.cpu_limit,
        )
        return PollResponse(job=work_resp, config=node_config)

    @staticmethod
    async def receive_heartbeat(node_id: str, node_ip: str, hb: HeartbeatPayload, db: AsyncSession) -> dict:
        """Processes a heartbeat from a node."""
        stats_json = json.dumps(hb.stats) if hb.stats else None
        tags_json = json.dumps(hb.tags) if hb.tags else None
        caps_json = json.dumps(hb.capabilities) if hb.capabilities else None

        # Upsert
        result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = result.scalar_one_or_none()
        
        if node:
            node.last_seen = datetime.utcnow()
            node.status = "ONLINE"
            if stats_json:
                node.stats = stats_json
            if tags_json:
                node.tags = tags_json
            if caps_json:
                node.capabilities = caps_json
            # Check IP drift
            if node.ip != node_ip: 
                node.ip = node_ip
        else:
            node = Node(
                node_id=node_id, 
                hostname=hb.hostname if hb.hostname else node_id, 
                ip=node_ip, 
                status="ONLINE", 
                stats=stats_json, 
                tags=tags_json,
                capabilities=caps_json
            )
            db.add(node)
        
        # Record stats history
        if hb.stats:
            db.add(NodeStats(node_id=node_id, cpu=hb.stats.get("cpu"), ram=hb.stats.get("ram")))
            await db.flush()
            # Prune: keep last 60 rows per node
            subq = (
                select(NodeStats.id)
                .where(NodeStats.node_id == node_id)
                .order_by(desc(NodeStats.recorded_at))
                .offset(60)
                .subquery()
            )
            await db.execute(delete(NodeStats).where(NodeStats.id.in_(select(subq.c.id))))

        # Process Job Telemetry
        if hb.job_telemetry:
            for guid, metrics in hb.job_telemetry.items():
                job_res = await db.execute(select(Job).where(Job.guid == guid))
                job_obj = job_res.scalar_one_or_none()
                if job_obj:
                    # Update telemetry field (JSON string)
                    job_obj.telemetry = json.dumps(metrics)

        await db.commit()
        return {"status": "ack"}

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
        result_payload = report.result or {}
        
        # Flight Recorder Logic for Failures
        if not report.success:
            error_info = report.error_details or {}
            flight_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "node_ip": node_ip,
                "error": error_info.get("message", "Unknown error"),
                "exit_code": error_info.get("exit_code"),
                "stack_trace": error_info.get("stack_trace"),
                "analysis": "Automated Flight Recorder: Job failed during node execution."
            }
            result_payload["flight_recorder"] = flight_report
            
        job.result = json.dumps(result_payload)
        job.completed_at = datetime.utcnow()

        await db.commit()
        return {"status": "updated"}
    @staticmethod
    async def get_job_stats(db: AsyncSession) -> dict:
        """Returns aggregated job statistics for the dashboard."""
        # Count statuses
        result = await db.execute(
            select(Job.status, func.count(Job.guid))
            .group_by(Job.status)
        )
        counts = {status: count for status, count in result.all()}
        
        # Ensure all standard statuses are present
        for status in ["PENDING", "ASSIGNED", "COMPLETED", "FAILED"]:
            if status not in counts:
                counts[status] = 0
                
        # Calculate success rate
        total_finished = counts["COMPLETED"] + counts["FAILED"]
        success_rate = (counts["COMPLETED"] / total_finished * 100) if total_finished > 0 else 100
        
        return {
            "counts": counts,
            "success_rate": round(success_rate, 2),
            "total_jobs": sum(counts.values())
        }
