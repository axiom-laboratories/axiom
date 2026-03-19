import logging
import uuid
import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Union, Dict
from packaging.version import Version, InvalidVersion
from sqlalchemy import select, desc, func, delete, or_, and_
from ..db import Job, Node, NodeStats, ExecutionRecord, AsyncSession, Config, Signal
from ..models import (
    ResultReport, JobResponse, JobCreate, WorkResponse, PollResponse, 
    NodeConfig, HeartbeatPayload
)
from ..security import mask_secrets, encrypt_secrets, decrypt_secrets
from .alert_service import AlertService
from .webhook_service import WebhookService
from . import attestation_service

logger = logging.getLogger(__name__)

MAX_OUTPUT_BYTES = 1_048_576  # 1 MB


class JobService:
    @staticmethod
    async def _get_zombie_timeout(db: AsyncSession) -> int:
        result = await db.execute(select(Config).where(Config.key == "zombie_timeout_minutes"))
        cfg = result.scalar_one_or_none()
        return int(cfg.value) if cfg else 30

    @staticmethod
    async def list_jobs(db: AsyncSession, skip: int = 0, limit: int = 50, status: Optional[str] = None) -> List[dict]:
        """For the Dashboard. Filters system jobs by default."""
        query = select(Job).where(Job.task_type != 'system_heartbeat')
        if status and status.upper() != 'ALL':
            query = query.where(Job.status == status.upper())
        query = query.order_by(desc(Job.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
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
                "target_tags": json.loads(job.target_tags) if job.target_tags else None,
                "depends_on": json.loads(job.depends_on) if job.depends_on else None
            })
        return response_jobs

    @staticmethod
    async def _get_dependency_depth(guid: str, db: AsyncSession, current_depth: int = 1) -> int:
        """Trace the graph upwards to calculate depth (protects against complex DAG DoS)."""
        if current_depth > 10: 
            return current_depth
        res = await db.execute(select(Job.depends_on).where(Job.guid == guid))
        deps_json = res.scalar_one_or_none()
        if not deps_json: 
            return current_depth
        
        try:
            deps = json.loads(deps_json)
            if not deps: 
                return current_depth
            
            max_d = current_depth
            for d_guid in deps:
                d = await JobService._get_dependency_depth(d_guid, db, current_depth + 1)
                if d > max_d: 
                    max_d = d
            return max_d
        except:
            return current_depth

    @staticmethod
    async def create_job(job_req: JobCreate, db: AsyncSession) -> dict:
        """Received from Model Service or Authorized User."""
        guid = str(uuid.uuid4())
        
        # Encrypt secrets before storing
        encrypted_payload = encrypt_secrets(job_req.payload)
        
        initial_status = "PENDING"
        depends_on_json = None
        
        if job_req.depends_on:
            # Validate existence
            result = await db.execute(select(Job).where(Job.guid.in_(job_req.depends_on)))
            upstreams = result.scalars().all()
            if len(upstreams) != len(job_req.depends_on):
                # Using 400 for bad request (dependency not found)
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="One or more dependency GUIDs not found")
            
            # Security SEC-03: Protect against deep DAGs (DoS mitigation)
            for upstream in upstreams:
                depth = await JobService._get_dependency_depth(upstream.guid, db)
                if depth >= 10:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=400, detail="Maximum dependency depth (10) exceeded")

            # Check if all completed
            if any(u.status != "COMPLETED" for u in upstreams):
                initial_status = "BLOCKED"
            
            depends_on_json = json.dumps(job_req.depends_on)

        new_job = Job(
            guid=guid,
            task_type=job_req.task_type,
            status=initial_status,
            payload=json.dumps(encrypted_payload),
            target_tags=json.dumps(job_req.target_tags) if job_req.target_tags else None,
            capability_requirements=json.dumps(job_req.capability_requirements) if job_req.capability_requirements else None,
            depends_on=depends_on_json,
            env_tag=job_req.env_tag,
            max_retries=job_req.max_retries,
            backoff_multiplier=job_req.backoff_multiplier,
            timeout_minutes=job_req.timeout_minutes,
            scheduled_job_id=job_req.scheduled_job_id,
            created_at=datetime.utcnow()
        )
        
        try:
            db.add(new_job)
            await db.commit()
            await db.refresh(new_job)
        except Exception as e:
            await db.rollback()
            raise e
        
        return {"guid": guid, "status": initial_status, "payload": encrypted_payload, "target_tags": job_req.target_tags, "depends_on": job_req.depends_on}

    @staticmethod
    def _get_effective_tags(node: Node) -> List[str]:
        """Prioritizes operator_tags over node-reported tags."""
        if node.operator_tags is not None:
            try:
                return json.loads(node.operator_tags)
            except Exception:
                return []
        return json.loads(node.tags) if node.tags else []

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
            # Security TDA-04: Quarantine check
            if node.status == "TAMPERED":
                logger.error(f"Rejecting work request from TAMPERED node {node_id}")
                node_config = NodeConfig(
                    concurrency_limit=0, # Disable execution
                    job_memory_limit=memory,
                    tags=JobService._get_effective_tags(node)
                )
                return PollResponse(job=None, config=node_config)

            node.last_seen = datetime.utcnow()
            if node.ip != node_ip:
                 node.ip = node_ip
        else:
            node = Node(
                node_id=node_id,
                hostname=node_id,
                ip=node_ip,
                status="ONLINE",
            )
            db.add(node)
        
        await db.commit()
        
        # Push operator env_tag to node so it adopts and reports it in heartbeats.
        # None = never managed (node uses own env var). "" = explicitly cleared. "X" = set to X.
        node_config = NodeConfig(
            concurrency_limit=concurrency,
            job_memory_limit=memory,
            env_tag=node.env_tag if node.operator_env_tag and node.env_tag else ("" if node.operator_env_tag else None),
        )

        # ZOMBIE REAPER: reclaim ASSIGNED jobs on this node that exceeded their timeout
        zombie_timeout_minutes = await JobService._get_zombie_timeout(db)
        global_cutoff = datetime.utcnow() - timedelta(minutes=zombie_timeout_minutes)
        zombie_result = await db.execute(
            select(Job).where(
                Job.status == 'ASSIGNED',
                Job.node_id == node_id,
                Job.started_at < global_cutoff,
            )
        )
        zombie_jobs = zombie_result.scalars().all()

        for zombie in zombie_jobs:
            # Per-job timeout override
            effective_timeout = zombie.timeout_minutes or zombie_timeout_minutes
            job_cutoff = datetime.utcnow() - timedelta(minutes=effective_timeout)
            if zombie.started_at >= job_cutoff:
                continue  # Not yet timed out per per-job override

            zombie.retry_count += 1
            db.add(ExecutionRecord(
                job_guid=zombie.guid,
                node_id=zombie.node_id,
                status="ZOMBIE_REAPED",
                started_at=zombie.started_at,
                completed_at=datetime.utcnow(),
                output_log=None,
                truncated=False,
            ))

            if zombie.max_retries > 0 and zombie.retry_count <= zombie.max_retries:
                base_delay = min(30.0 * (zombie.backoff_multiplier ** (zombie.retry_count - 1)), 3600.0)
                jitter = base_delay * 0.2
                delay = base_delay + random.uniform(-jitter, jitter)
                zombie.retry_after = datetime.utcnow() + timedelta(seconds=max(delay, 1.0))
                zombie.status = "RETRYING"
                zombie.node_id = None
                zombie.completed_at = None
            else:
                zombie.status = "DEAD_LETTER" if zombie.max_retries > 0 else "FAILED"
                zombie.completed_at = datetime.utcnow()
                zombie.node_id = None
                
                if zombie.status == "DEAD_LETTER":
                    await AlertService.create_alert(
                        db,
                        type="job_failure",
                        severity="CRITICAL",
                        message=f"Job {zombie.guid} failed terminally after reap/retry exhaustion.",
                        resource_id=zombie.guid
                    )

        if zombie_jobs:
            await db.flush()  # Persist zombie changes before concurrency check

        # 2. Check Concurrency Limit
        result = await db.execute(select(func.count(Job.guid)).where(Job.status == 'ASSIGNED', Job.node_id == node_id))
        active_count = result.scalar()
        
        if active_count >= concurrency:
            return PollResponse(job=None, config=node_config)
        
        # 3. Find highest priority PENDING or eligible RETRYING job matching criteria
        result = await db.execute(
            select(Job).where(
                or_(
                    Job.status == 'PENDING',
                    and_(
                        Job.status == 'RETRYING',
                        or_(Job.retry_after == None, Job.retry_after <= datetime.utcnow())
                    )
                )
            ).where(
                (Job.node_id == None) | (Job.node_id == node_id)
            ).order_by(Job.created_at.asc()).limit(50)
        )
        jobs = result.scalars().all()
        
        selected_job = None
        node_tags = JobService._get_effective_tags(node) if node else []
        node_caps_dict = json.loads(node.capabilities) if node and node.capabilities else {}

        for candidate in jobs:
            # Check Tags
            req_tags = json.loads(candidate.target_tags) if candidate.target_tags else []
            if not isinstance(req_tags, list):
                req_tags = []

            # 1. Standard: Node must have ALL requested tags
            if not all(t in node_tags for t in req_tags):
                continue
                
            # 2. Strict Environment isolation (env: prefix)
            node_env_tags = [t for t in node_tags if t.startswith("env:")]
            job_env_tags = [t for t in req_tags if t.startswith("env:")]
            
            # Rule: If Node is env-restricted, Job must match at least one of those env tags
            if node_env_tags and not any(et in job_env_tags for et in node_env_tags):
                continue
                
            # Rule: If Job is env-targeted, Node must have at least one of those env tags
            if job_env_tags and not any(et in node_env_tags for et in job_env_tags):
                continue

            # ENVTAG-02: first-class env_tag column check (added Phase 31)
            # Runs AFTER the env: tag prefix guard, which is preserved for backward compat.
            if candidate.env_tag:
                node_env_tag = (node.env_tag or "").upper() if node and node.env_tag else None
                if node_env_tag != candidate.env_tag.upper():
                    continue

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

        # RETRY-02: Set job_run_id at first dispatch; idempotent — retries reuse the same UUID
        if selected_job.job_run_id is None:
            selected_job.job_run_id = str(uuid.uuid4())

        encrypted_payload = json.loads(selected_job.payload)
        payload = decrypt_secrets(encrypted_payload)

        await db.commit()

        work_resp = WorkResponse(
            guid=selected_job.guid,
            task_type=selected_job.task_type,
            payload=payload,
            max_retries=selected_job.max_retries,
            backoff_multiplier=selected_job.backoff_multiplier,
            timeout_minutes=selected_job.timeout_minutes,
            started_at=selected_job.started_at,
        )
        return PollResponse(job=work_resp, config=node_config)

    @staticmethod
    async def receive_heartbeat(node_id: str, node_ip: str, hb: HeartbeatPayload, db: AsyncSession) -> dict:
        """Processes a heartbeat from a node."""
        stats_json = json.dumps(hb.stats) if hb.stats else None
        
        # Security SEC-02: Prevent self-escalation via env: tags.
        # Only operator_tags can control environment segmentation.
        sanitized_tags = [t for t in hb.tags if not t.startswith("env:")] if hb.tags else None
        tags_json = json.dumps(sanitized_tags) if sanitized_tags is not None else None
        # ENVTAG-01: store first-class env_tag from heartbeat (already normalised to uppercase by HeartbeatPayload validator)
        # This is a dedicated column, NOT subject to SEC-02 stripping.
        
        caps_json = json.dumps(hb.capabilities) if hb.capabilities else None

        # Upsert
        result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = result.scalar_one_or_none()
        
        if node:
            # If node was previously OFFLINE or TAMPERED, auto-resolve alerts when it returns ONLINE
            if node.status in ["OFFLINE", "TAMPERED"]:
                await AlertService.resolve_alert(db, "node_offline", node_id)
                # Note: We don't auto-resolve TAMPERED unless specified by a security clear event, 
                # but if it was just OFFLINE, we clear those.
            
            node.last_seen = datetime.utcnow()
            prev_status = node.status
            node.status = "ONLINE"
            if stats_json:
                node.stats = stats_json
            if tags_json:
                node.tags = tags_json
            # Operator-set env_tag takes precedence over node self-reporting.
            # Only update from heartbeat when no operator override is in place.
            if not node.operator_env_tag:
                node.env_tag = hb.env_tag

            # Security TDA-03: Zero-Trust Capability Guard
            if caps_json:
                if node.expected_capabilities:
                    expected = json.loads(node.expected_capabilities)
                    reported = hb.capabilities or {}
                    
                    # Rule: Reported must NOT contain tools not present in Expected
                    unauthorized = [k for k in reported.keys() if k not in expected]
                    if unauthorized:
                        node.status = "TAMPERED"
                        node.tamper_details = f"Unauthorized tools reported: {', '.join(unauthorized)}"
                        logger.warning(f"🚨 TAMPER DETECTED on node {node_id}: {node.tamper_details}")
                        
                        # Trigger Security Alert
                        await AlertService.create_alert(
                            db,
                            type="security_tamper",
                            severity="CRITICAL",
                            message=f"SECURITY TAMPER on node {node.hostname}: {node.tamper_details}",
                            resource_id=node_id
                        )
                
                # Only update reported capabilities if not currently tampered (to preserve state for investigation)
                if node.status != "TAMPERED":
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
                capabilities=caps_json,
                env_tag=hb.env_tag,   # ENVTAG-01: store on first heartbeat
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

        # Security HUE-04/05: C2 Delivery and Promotion
        resp = {"status": "ack"}
        
        # 1. Process Results from previous task
        if hasattr(hb, 'upgrade_result') or (isinstance(hb, dict) and "upgrade_result" in hb):
            # Pydantic model might not have it yet, check dict or handle model update
            # (Assuming HeartbeatPayload was updated or using raw access)
            res = getattr(hb, 'upgrade_result', None) or (hb.get("upgrade_result") if isinstance(hb, dict) else None)
            
            if res and node.pending_upgrade:
                task = json.loads(node.pending_upgrade)
                status = res.get("status")
                tool_id = task.get("tool_id")
                
                # Update history
                history = json.loads(node.upgrade_history) if node.upgrade_history else []
                history.insert(0, {
                    "tool_id": tool_id,
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat(),
                    "output": res.get("output"),
                    "error": res.get("error")
                })
                node.upgrade_history = json.dumps(history[:10]) # Keep last 10
                
                if status == "SUCCESS":
                    # Promotion: Update expectations
                    expected = json.loads(node.expected_capabilities) if node.expected_capabilities else {}
                    expected[tool_id] = "latest"
                    node.expected_capabilities = json.dumps(expected)
                    logger.info(f"✨ Node {node_id} upgraded successfully to {tool_id}")
                else:
                    logger.error(f"❌ Node {node_id} upgrade failed: {res.get('error')}")
                
                node.pending_upgrade = None
                node.status = "ONLINE" # Exit UPGRADING state

        # 2. Deliver Pending Task
        if node.pending_upgrade:
            resp["upgrade_task"] = json.loads(node.pending_upgrade)

        await db.commit()
        return resp

    @staticmethod
    async def _check_dependency_met(dep: Union[str, Dict], db: AsyncSession) -> bool:
        """Determines if a single dependency requirement is satisfied."""
        if isinstance(dep, str):
            # Legacy/Simple: Wait for Job(GUID) to be COMPLETED
            res = await db.execute(select(Job.status).where(Job.guid == dep))
            status = res.scalar_one_or_none()
            return status == "COMPLETED"
        
        dep_type = dep.get("type", "job")
        ref = dep.get("ref")
        
        if dep_type == "job":
            condition = dep.get("condition", "COMPLETED")
            res = await db.execute(select(Job.status).where(Job.guid == ref))
            status = res.scalar_one_or_none()
            if not status: return False
            
            if condition == "COMPLETED": return status == "COMPLETED"
            if condition == "FAILED": return status in ["FAILED", "DEAD_LETTER"]
            if condition == "ANY": return status in ["COMPLETED", "FAILED", "DEAD_LETTER", "CANCELLED", "SECURITY_REJECTED"]
            
        if dep_type == "signal":
            res = await db.execute(select(Signal).where(Signal.name == ref))
            return res.scalar_one_or_none() is not None
            
        return False

    @staticmethod
    async def _unblock_dependents(trigger_ref: str, db: AsyncSession):
        """
        Finds jobs blocked by this GUID or Signal and unblocks them if conditions are met.
        Also handles propagation of failures (cancellation) for jobs that will never be unblocked.
        """
        # Find potential dependents using LIKE for JSON column search
        # We search for the GUID or Signal name in the depends_on JSON string
        result = await db.execute(
            select(Job).where(
                Job.status == 'BLOCKED',
                Job.depends_on.like(f"%{trigger_ref}%")
            )
        )
        dependents = result.scalars().all()
        
        for dep in dependents:
            try:
                deps_list = json.loads(dep.depends_on) if dep.depends_on else []
                
                # Check if all dependencies are now satisfied
                met_results = [await JobService._check_dependency_met(d, db) for d in deps_list]
                
                if all(met_results):
                    dep.status = "PENDING"
                    logger.info(f"🔓 Job {dep.guid} unblocked by {trigger_ref}")
                else:
                    # Check for "Impossible" dependencies (Deadlocks)
                    # e.g. depending on Job A (COMPLETED) but Job A just FAILED.
                    for d in deps_list:
                        if isinstance(d, dict) and d.get("type") == "job" and d.get("ref") == trigger_ref:
                            # This is the job that just changed state. 
                            # If it reached a terminal state that doesn't match the condition, 
                            # the dependent job can NEVER be unblocked.
                            res = await db.execute(select(Job.status).where(Job.guid == trigger_ref))
                            new_status = res.scalar_one_or_none()
                            condition = d.get("condition", "COMPLETED")
                            
                            impossible = False
                            if condition == "COMPLETED" and new_status in ["FAILED", "DEAD_LETTER", "CANCELLED", "SECURITY_REJECTED"]:
                                impossible = True
                            if condition == "FAILED" and new_status == "COMPLETED":
                                impossible = True
                                
                            if impossible:
                                dep.status = "CANCELLED"
                                dep.completed_at = datetime.utcnow()
                                logger.warning(f"🚫 Job {dep.guid} cancelled: condition '{condition}' for {trigger_ref} can no longer be met.")
                                # Propagate cancellation recursively (iterative BFS approach already implemented in _cancel_dependents)
                                await JobService._cancel_dependents(dep.guid, db)
            except Exception as e:
                logger.error(f"Error processing dependent {dep.guid}: {e}")
                continue

    @staticmethod
    async def unblock_jobs_by_signal(signal_name: str, db: AsyncSession):
        """Entry point for Signal-based unblocking."""
        await JobService._unblock_dependents(signal_name, db)

    @staticmethod
    async def _cancel_dependents(failed_guid: str, db: AsyncSession):
        """Iteratively cancels jobs blocked by terminal failures (preventing stack exhaustion)."""
        queue = [failed_guid]
        processed = set()

        while queue:
            current_guid = queue.pop(0)
            if current_guid in processed:
                continue
            processed.add(current_guid)

            # Find potential dependents using LIKE for JSON column search
            result = await db.execute(
                select(Job).where(
                    Job.status == 'BLOCKED',
                    Job.depends_on.like(f"%{current_guid}%")
                )
            )
            dependents = result.scalars().all()
            
            for dep in dependents:
                try:
                    upstreams = json.loads(dep.depends_on) if dep.depends_on else []
                    # We only cancel if the dependency was on this job being COMPLETED (default)
                    # If it was on FAILED or ANY, it might have just been unblocked by _unblock_dependents.
                    # This iterative BFS handles transitive COMPLETED failures.
                    
                    is_direct_dep = False
                    for d in upstreams:
                        if isinstance(d, str) and d == current_guid: is_direct_dep = True
                        if isinstance(d, dict) and d.get("ref") == current_guid and d.get("condition", "COMPLETED") == "COMPLETED":
                            is_direct_dep = True
                    
                    if is_direct_dep:
                        dep.status = "CANCELLED"
                        dep.completed_at = datetime.utcnow()
                        logger.warning(f"🚫 Job {dep.guid} cancelled because upstream {current_guid} failed")
                        queue.append(dep.guid)
                except Exception:
                    continue

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

        # Determine status
        if report.security_rejected:
            new_status = "SECURITY_REJECTED"
        elif report.success:
            new_status = "COMPLETED"
        else:
            new_status = "FAILED"

        # Build truncated output_log
        output_log = report.output_log or []
        
        # Security SEC-01: Scrub secrets from logs before persistence
        try:
            decrypted_payload = decrypt_secrets(json.loads(job.payload))
            if "secrets" in decrypted_payload and isinstance(decrypted_payload["secrets"], dict):
                secrets_to_redact = [str(v) for v in decrypted_payload["secrets"].values() if v and len(str(v)) > 3]
                for entry in output_log:
                    if "line" in entry and isinstance(entry["line"], str):
                        for secret in secrets_to_redact:
                            entry["line"] = entry["line"].replace(secret, "[REDACTED]")
        except Exception as e:
            logger.error(f"Failed to scrub logs for job {guid}: {e}")

        # OUTPUT-01: Extract stdout/stderr streams from scrubbed log BEFORE truncation
        stdout_text = "\n".join(e["line"] for e in output_log if e.get("stream") == "stdout")
        stderr_text = "\n".join(e["line"] for e in output_log if e.get("stream") == "stderr")

        truncated = False
        output_json = json.dumps(output_log)
        if len(output_json.encode("utf-8")) > MAX_OUTPUT_BYTES:
            while output_log and len(json.dumps(output_log).encode("utf-8")) > MAX_OUTPUT_BYTES:
                output_log.pop()
            truncated = True

        # OUTPUT-02: Compute orchestrator-side script_hash and detect mismatch
        try:
            _job_payload = decrypt_secrets(json.loads(job.payload))
            _script_bytes = _job_payload.get("script_content", "").encode("utf-8")
            orchestrator_hash = hashlib.sha256(_script_bytes).hexdigest()
        except Exception as e:
            logger.error("Failed to compute script_hash for job %s: %s", guid, e)
            orchestrator_hash = None
        _node_hash = report.script_hash  # Optional[str] from ResultReport
        hash_mismatch = (
            _node_hash is not None and orchestrator_hash is not None
            and _node_hash != orchestrator_hash
        )
        if hash_mismatch:
            logger.warning(
                "script_hash mismatch for job %s: node=%s orchestrator=%s",
                guid, _node_hash, orchestrator_hash,
            )

        # Write ExecutionRecord (same transaction as job update)
        record = ExecutionRecord(
            job_guid=guid,
            node_id=job.node_id,
            status=new_status,
            exit_code=report.exit_code,
            started_at=job.started_at,
            completed_at=datetime.utcnow(),
            output_log=json.dumps(output_log),
            truncated=truncated,
            # OUTPUT-01: separate stdout/stderr columns
            stdout=stdout_text,
            stderr=stderr_text,
            # OUTPUT-02: script integrity
            script_hash=orchestrator_hash,
            hash_mismatch=hash_mismatch,
            # RETRY-01: attempt number (retry_count not yet incremented at this point)
            attempt_number=job.retry_count + 1,
            # RETRY-02: link all attempts to the same logical run
            job_run_id=job.job_run_id,
            # OUTPUT-06: attestation fields (verified after record is constructed)
            attestation_bundle=report.attestation_bundle,
            attestation_signature=report.attestation_signature,
            attestation_verified=None,  # Set below after verification
        )
        # OUTPUT-06: verify attestation bundle before persisting
        attestation_status = await attestation_service.verify_bundle(
            node_id=job.node_id,
            bundle_b64=report.attestation_bundle,
            signature_b64=report.attestation_signature,
            db=db,
        )
        record.attestation_verified = attestation_status
        db.add(record)

        # Update job — keep result as minimal summary only (no stdout/stderr)
        if not report.success and not report.security_rejected:
            error_info = report.error_details or {}
            flight_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "node_ip": node_ip,
                "error": error_info.get("message", "Unknown error"),
                "exit_code": report.exit_code,
                "stack_trace": error_info.get("stack_trace"),
                "analysis": "Automated Flight Recorder: Job failed during node execution."
            }
            job.result = json.dumps({"flight_recorder": flight_report})
        else:
            job.result = json.dumps({"exit_code": report.exit_code})

        # Retry classification (only for genuine failures, not security rejections)
        if new_status == "FAILED":
            is_retriable = report.retriable is True  # None or False = non-retriable
            if is_retriable and job.max_retries > 0 and job.retry_count < job.max_retries:
                job.retry_count += 1
                base_delay = min(30.0 * (job.backoff_multiplier ** (job.retry_count - 1)), 3600.0)
                jitter = base_delay * 0.2
                delay = base_delay + random.uniform(-jitter, jitter)
                job.retry_after = datetime.utcnow() + timedelta(seconds=max(delay, 1.0))
                job.status = "RETRYING"
                job.node_id = None
                job.completed_at = None
            elif is_retriable and job.max_retries > 0:
                # Retries exhausted
                job.status = "DEAD_LETTER"
                job.completed_at = datetime.utcnow()
                await AlertService.create_alert(
                    db,
                    type="job_failure",
                    severity="CRITICAL",
                    message=f"Job {guid} exhausted all {job.max_retries} retries and failed terminally.",
                    resource_id=guid
                )
            else:
                # Non-retriable: stays FAILED
                job.status = "FAILED"
                job.completed_at = datetime.utcnow()
        else:
            # COMPLETED, SECURITY_REJECTED — set completed_at
            job.status = new_status
            job.completed_at = datetime.utcnow()

        # Handle dependencies
        if job.status == "COMPLETED":
            await JobService._unblock_dependents(guid, db)
        elif job.status in ["FAILED", "DEAD_LETTER", "SECURITY_REJECTED"]:
            # If a job is rejected or failed terminally, we cancel dependents to avoid deadlocks
            await JobService._cancel_dependents(guid, db)

        await db.commit()
        # 4. Final Terminal Status Webhook
        is_terminal = job.status in ["COMPLETED", "FAILED", "DEAD_LETTER", "SECURITY_REJECTED"]
        if is_terminal:
            await WebhookService.dispatch_event(db, f"job:{job.status.lower()}", {
                "guid": job.guid,
                "node_id": job.node_id,
                "status": job.status,
                "exit_code": report.exit_code
            })

        return {"status": job.status}
    @staticmethod
    async def get_job_stats(db: AsyncSession) -> dict:
        """Returns aggregated job statistics for the dashboard."""
        # Count statuses
        result = await db.execute(
            select(Job.status, func.count(Job.guid))
            .group_by(Job.status)
        )
        counts = {status: count for status, count in result.all()}
        
        # Ensure all standard statuses are present (SECURITY_REJECTED tracked separately)
        for status in ["PENDING", "ASSIGNED", "COMPLETED", "FAILED", "SECURITY_REJECTED", "RETRYING", "DEAD_LETTER"]:
            if status not in counts:
                counts[status] = 0

        # Calculate success rate (SECURITY_REJECTED excluded — security events tracked separately)
        total_finished = counts["COMPLETED"] + counts["FAILED"] + counts["DEAD_LETTER"]
        success_rate = (counts["COMPLETED"] / total_finished * 100) if total_finished > 0 else 100
        
        return {
            "counts": counts,
            "success_rate": round(success_rate, 2),
            "total_jobs": sum(counts.values())
        }
