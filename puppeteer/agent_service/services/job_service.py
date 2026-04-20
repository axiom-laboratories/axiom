import base64
import logging
import uuid
import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Union, Dict
from packaging.version import Version, InvalidVersion
from sqlalchemy import select, desc, func, delete, or_, and_
from ..db import Job, Node, NodeStats, ExecutionRecord, AsyncSession, Config, Signal, IS_POSTGRES, WorkflowRun, WorkflowStepRun
from ..models import (
    ResultReport, JobResponse, JobCreate, WorkResponse, PollResponse,
    HeartbeatPayload
)
from ..security import mask_secrets, encrypt_secrets, decrypt_secrets, compute_signature_hmac, verify_signature_hmac, ENCRYPTION_KEY
from ..deps import audit
from .alert_service import AlertService
from .webhook_service import WebhookService
from . import attestation_service

logger = logging.getLogger(__name__)

MAX_OUTPUT_BYTES = 1_048_576  # 1 MB


def _compute_display_type(task_type: str, payload: dict) -> str:
    """Server-authoritative display string — never let frontend parse payload."""
    if task_type == "script":
        runtime = payload.get("runtime", "python")
        return f"script ({runtime})"
    return task_type


def _encode_cursor(created_at: datetime, guid: str) -> str:
    """Base64-encode a pagination cursor from (created_at, guid)."""
    payload = {"ts": created_at.isoformat(), "guid": guid}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple:
    """Decode a pagination cursor back to (datetime, guid)."""
    payload = json.loads(base64.urlsafe_b64decode(cursor).decode())
    return datetime.fromisoformat(payload["ts"]), payload["guid"]


def parse_bytes(s: str) -> int:
    """Convert memory string like '300m', '2g', '1024k' to bytes.

    Args:
        s: Memory string (e.g., "512m", "1g", "1Gi", "1024k", "2")

    Returns:
        Integer byte count

    Examples:
        parse_bytes("512m") -> 536870912 (512 * 1024^2)
        parse_bytes("1g") -> 1073741824 (1 * 1024^3)
        parse_bytes("1Gi") -> 1073741824 (1 * 1024^3, case-insensitive)
        parse_bytes("1024k") -> 1048576 (1024 * 1024)
        parse_bytes("2") -> 2 (raw bytes, no suffix)
    """
    s = s.strip().lower()
    if s.endswith('gi'):
        return int(s[:-2]) * (1024 ** 3)
    elif s.endswith('mi'):
        return int(s[:-2]) * (1024 ** 2)
    elif s.endswith('ki'):
        return int(s[:-2]) * 1024
    elif s.endswith('g'):
        return int(s[:-1]) * (1024 ** 3)
    elif s.endswith('m'):
        return int(s[:-1]) * (1024 ** 2)
    elif s.endswith('k'):
        return int(s[:-1]) * 1024
    return int(s)  # Assume bytes if no suffix


def _format_bytes(num_bytes: int) -> str:
    """Convert byte count back to human-readable format.

    Args:
        num_bytes: Number of bytes

    Returns:
        Human-readable string (e.g., "1.0Gi", "512.0Mi")
    """
    for unit, divisor in [("Gi", 1024 ** 3), ("Mi", 1024 ** 2), ("Ki", 1024)]:
        if num_bytes >= divisor:
            return f"{num_bytes / divisor:.1f}{unit}"
    return f"{num_bytes}B"


async def _sum_node_assigned_limits(node_id: str, db: AsyncSession) -> int:
    """Sum memory limits for all ASSIGNED and RUNNING jobs on a node.

    Args:
        node_id: Node ID to query
        db: Async database session

    Returns:
        Total memory in bytes used by assigned/running jobs (default 0 if none)
    """
    result = await db.execute(
        select(Job).where(
            and_(
                Job.node_id == node_id,
                Job.status.in_(["ASSIGNED", "RUNNING"]),
                Job.memory_limit.isnot(None)
            )
        )
    )
    jobs = result.scalars().all()

    total = 0
    for job in jobs:
        if job.memory_limit:
            total += parse_bytes(job.memory_limit)

    return total


async def _get_node_available_capacity(node: Node, db: AsyncSession) -> int:
    """Calculate available memory capacity for a node.

    Args:
        node: Node record
        db: Async database session

    Returns:
        Available memory in bytes (may be negative if oversubscribed)
    """
    # Get node capacity (default to 512m if None)
    capacity_str = node.job_memory_limit or "512m"
    capacity_bytes = parse_bytes(capacity_str)

    # Get sum of assigned/running job limits
    used = await _sum_node_assigned_limits(node.node_id, db)

    return capacity_bytes - used


class JobService:
    @staticmethod
    async def _get_zombie_timeout(db: AsyncSession) -> int:
        result = await db.execute(select(Config).where(Config.key == "zombie_timeout_minutes"))
        cfg = result.scalar_one_or_none()
        return int(cfg.value) if cfg else 30

    @staticmethod
    def _build_job_filter_queries(
        base_query,
        count_query,
        *,
        status: Optional[str] = None,
        runtime: Optional[str] = None,
        task_type: Optional[str] = None,
        node_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
    ):
        """Apply 9-axis filter composition to both items query and count query.

        Returns (filtered_base_query, filtered_count_query).
        All axes compose with AND; tags use OR within the axis.
        """
        if status and status.upper() != 'ALL':
            # Support comma-separated status values (e.g., "COMPLETED,FAILED,CANCELLED")
            status_values = [s.strip().upper() for s in status.split(',') if s.strip()]
            if status_values:
                if len(status_values) == 1:
                    f = Job.status == status_values[0]
                else:
                    f = Job.status.in_(status_values)
                base_query = base_query.where(f)
                count_query = count_query.where(f)

        if runtime:
            f = Job.runtime == runtime
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        if task_type:
            f = Job.task_type == task_type
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        if node_id:
            f = Job.node_id == node_id
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        if tags:
            # OR logic within axis; exact JSON-quoted match avoids substring ambiguity
            tag_filters = [Job.target_tags.like(f'%"{t}"%') for t in tags]
            f = or_(*tag_filters)
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        if created_by:
            f = Job.created_by == created_by
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        if date_from:
            f = Job.created_at >= date_from
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        if date_to:
            f = Job.created_at <= date_to
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        if search:
            # ILIKE for Postgres; SQLite LIKE is case-insensitive for ASCII by default
            pattern = f"%{search}%"
            f = or_(Job.name.ilike(pattern), Job.guid.ilike(pattern))
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        return base_query, count_query

    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        limit: int = 50,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        runtime: Optional[str] = None,
        task_type: Optional[str] = None,
        node_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> dict:
        """Cursor-paginated job list with 9-axis filter composition.

        Returns {"items": List[dict], "total": int, "next_cursor": Optional[str]}.
        total is computed BEFORE cursor filter so it remains stable across pages.
        """
        base_filter = Job.task_type != 'system_heartbeat'
        query = select(Job).where(base_filter)
        count_query = select(func.count()).select_from(Job).where(base_filter)

        # Apply all 9 filter axes to both queries
        query, count_query = JobService._build_job_filter_queries(
            query, count_query,
            status=status, runtime=runtime, task_type=task_type,
            node_id=node_id, tags=tags, created_by=created_by,
            date_from=date_from, date_to=date_to, search=search,
        )

        # Count BEFORE cursor filter — total stays stable across "load more"
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        # Apply cursor WHERE to items query only
        if cursor:
            ts, guid_val = _decode_cursor(cursor)
            cursor_filter = or_(
                Job.created_at < ts,
                and_(Job.created_at == ts, Job.guid < guid_val),
            )
            query = query.where(cursor_filter)

        query = query.order_by(desc(Job.created_at), desc(Job.guid)).limit(limit)
        result = await db.execute(query)
        jobs = result.scalars().all()

        response_jobs = []
        for job in jobs:
            payload = json.loads(job.payload)

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
                "depends_on": json.loads(job.depends_on) if job.depends_on else None,
                "task_type": job.task_type,
                "display_type": _compute_display_type(job.task_type, payload),
                "name": job.name,
                "created_by": job.created_by,
                "created_at": job.created_at,
                "runtime": job.runtime,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "retry_after": job.retry_after.isoformat() if job.retry_after else None,
                "originating_guid": job.originating_guid,
            })

        next_cursor = None
        if len(jobs) == limit:
            last = jobs[-1]
            next_cursor = _encode_cursor(last.created_at, last.guid)

        return {"items": response_jobs, "total": total, "next_cursor": next_cursor}

    @staticmethod
    async def list_jobs_for_export(
        db: AsyncSession,
        limit: int = 10_000,
        status: Optional[str] = None,
        runtime: Optional[str] = None,
        task_type: Optional[str] = None,
        node_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """Flat metadata-only export list capped at limit rows.

        Does not include payload content, result, or secrets.
        Returns dicts with: guid, name, status, task_type, display_type, runtime,
        node_id, created_at, started_at, completed_at, duration_seconds, target_tags.
        """
        base_filter = Job.task_type != 'system_heartbeat'
        query = select(Job).where(base_filter)
        count_query = select(func.count()).select_from(Job).where(base_filter)

        query, count_query = JobService._build_job_filter_queries(
            query, count_query,
            status=status, runtime=runtime, task_type=task_type,
            node_id=node_id, tags=tags, created_by=created_by,
            date_from=date_from, date_to=date_to, search=search,
        )

        query = query.order_by(desc(Job.created_at), desc(Job.guid)).limit(limit)
        result = await db.execute(query)
        jobs = result.scalars().all()

        rows = []
        for job in jobs:
            payload = json.loads(job.payload)
            duration = None
            if job.started_at:
                end = job.completed_at or datetime.utcnow()
                duration = (end - job.started_at).total_seconds()

            rows.append({
                "guid": job.guid,
                "name": job.name,
                "status": job.status,
                "task_type": job.task_type,
                "display_type": _compute_display_type(job.task_type, payload),
                "runtime": job.runtime,
                "node_id": job.node_id,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "duration_seconds": duration,
                "target_tags": json.loads(job.target_tags) if job.target_tags else None,
            })
        return rows

    @staticmethod
    async def list_nodes(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        """Return a page-based paginated list of nodes.

        Returns {"items": List[dict], "total": int, "page": int, "pages": int}.
        Each item contains: node_id, hostname, ip, status, last_seen, env_tag.
        """
        import math

        total_result = await db.execute(select(func.count()).select_from(Node))
        total = total_result.scalar() or 0

        result = await db.execute(
            select(Node).order_by(Node.hostname)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        nodes = result.scalars().all()

        items = [
            {
                "node_id": n.node_id,
                "hostname": n.hostname,
                "ip": n.ip,
                "status": n.status,
                "last_seen": n.last_seen,
                "env_tag": getattr(n, "env_tag", None),
            }
            for n in nodes
        ]

        pages = math.ceil(total / page_size) if total > 0 else 1
        return {"items": items, "total": total, "page": page, "pages": pages}

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

        # Validate that at least one ONLINE node can serve this env_tag
        if job_req.env_tag:
            from fastapi import HTTPException
            result = await db.execute(
                select(Node).where(
                    Node.status == "ONLINE",
                    Node.env_tag == job_req.env_tag,
                )
            )
            eligible = result.scalars().first()
            if eligible is None:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "no_eligible_node",
                        "env_tag": job_req.env_tag,
                        "message": f"No ONLINE node with env_tag='{job_req.env_tag}' available.",
                    },
                )

        # ENFC-03: Memory admission control — check job fits on at least one node
        if job_req.memory_limit is not None or True:  # Always check (may use default)
            from fastapi import HTTPException

            # Determine effective memory limit (explicit or default)
            effective_memory = job_req.memory_limit
            if effective_memory is None:
                # Get default from Config table
                config_result = await db.execute(
                    select(Config).where(Config.key == 'default_job_memory_limit')
                )
                config_obj = config_result.scalar_one_or_none()
                effective_memory = config_obj.value if config_obj else "512m"

            # Query online nodes with capacity
            online_result = await db.execute(
                select(Node).where(Node.status.in_(["ONLINE", "BUSY"]))
            )
            online_nodes = online_result.scalars().all()

            # If online nodes exist, check admission
            if online_nodes:
                job_bytes = parse_bytes(effective_memory)
                largest_available = 0
                nodes_info = []

                for node in online_nodes:
                    available = await _get_node_available_capacity(node, db)
                    largest_available = max(largest_available, available)
                    capacity_mb = parse_bytes(node.job_memory_limit or "512m") // (1024 ** 2)
                    used_mb = (await _sum_node_assigned_limits(node.node_id, db)) // (1024 ** 2)
                    available_mb = available // (1024 ** 2)
                    nodes_info.append({
                        "node_id": node.node_id,
                        "capacity_mb": capacity_mb,
                        "used_mb": used_mb,
                        "available_mb": available_mb,
                    })

                # Reject if job exceeds all nodes
                if job_bytes > largest_available:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "error": "insufficient_capacity",
                            "message": f"No online node can accommodate memory_limit={job_req.memory_limit or '(default 512m)'}. Largest available: {_format_bytes(largest_available)}",
                            "nodes_info": nodes_info,
                        },
                    )

        # Merge runtime into payload dict before encryption (RT-05)
        payload_dict = dict(job_req.payload)
        if job_req.runtime is not None:
            payload_dict["runtime"] = job_req.runtime

        # Encrypt secrets before storing
        encrypted_payload = encrypt_secrets(payload_dict)
        
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
            runtime=job_req.runtime,
            created_at=datetime.utcnow(),
            name=getattr(job_req, 'name', None),        # SRCH-04: optional job name label
            created_by=getattr(job_req, 'created_by', None),  # SRCH-03: submitter username
            target_node_id=getattr(job_req, 'target_node_id', None),
        )
        
        # SEC-02: Stamp HMAC tag on signature_payload before persisting
        _hmac_payload = encrypted_payload  # work with the pre-encryption dict (encryption is on secrets)
        _sig_payload = _hmac_payload.get("signature_payload") if isinstance(_hmac_payload, dict) else None
        _sig_id = _hmac_payload.get("signature_id") if isinstance(_hmac_payload, dict) else None
        if not _sig_payload and not _sig_id:
            # Fall back to payload_dict (original, unencrypted, with runtime merged in)
            _sig_payload = payload_dict.get("signature_payload")
            _sig_id = payload_dict.get("signature_id")
        if _sig_payload and _sig_id:
            new_job.signature_hmac = compute_signature_hmac(ENCRYPTION_KEY, _sig_payload, _sig_id, guid)

        try:
            db.add(new_job)
            await db.commit()
            await db.refresh(new_job)
        except Exception as e:
            await db.rollback()
            raise e

        return {"guid": guid, "status": initial_status, "payload": encrypted_payload, "target_tags": job_req.target_tags, "depends_on": job_req.depends_on, "task_type": job_req.task_type, "display_type": _compute_display_type(job_req.task_type, payload_dict)}

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
    def _node_is_eligible(node: Node, job: Job, node_tags: List[str], node_caps_dict: dict) -> bool:
        """Returns True if node can accept the given job based on tags, env isolation, and capabilities."""
        req_tags = json.loads(job.target_tags) if job.target_tags else []
        if not isinstance(req_tags, list):
            req_tags = []

        # 1. Standard: Node must have ALL requested tags
        if not all(t in node_tags for t in req_tags):
            return False

        # 2. Strict Environment isolation (env: prefix)
        node_env_tags = [t for t in node_tags if t.startswith("env:")]
        job_env_tags = [t for t in req_tags if t.startswith("env:")]

        # Rule: If Node is env-restricted, Job must match at least one of those env tags
        if node_env_tags and not any(et in job_env_tags for et in node_env_tags):
            return False

        # Rule: If Job is env-targeted, Node must have at least one of those env tags
        if job_env_tags and not any(et in node_env_tags for et in job_env_tags):
            return False

        # ENVTAG-02: first-class env_tag column check
        if job.env_tag:
            node_env_tag = (node.env_tag or "").upper() if node.env_tag else None
            if node_env_tag != job.env_tag.upper():
                return False

        # Check Capabilities
        if job.capability_requirements:
            try:
                req_caps = json.loads(job.capability_requirements)
                if not isinstance(req_caps, dict):
                    return False
                for cap_name, min_version in req_caps.items():
                    if cap_name not in node_caps_dict:
                        return False
                    node_ver = node_caps_dict[cap_name]
                    try:
                        satisfies = Version(node_ver) >= Version(min_version)
                    except InvalidVersion:
                        satisfies = node_ver >= min_version
                    if not satisfies:
                        return False
            except Exception:
                return False

        return True

    @staticmethod
    async def get_node_detail(node_id: str, db: AsyncSession) -> "dict | None":
        """Returns compound node detail: running job, eligible pending jobs, 24h history, capabilities."""
        # 1. Load node
        node_result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = node_result.scalar_one_or_none()
        if not node:
            return None

        # 2. Running job (ASSIGNED on this node)
        running_result = await db.execute(
            select(Job).where(Job.status == 'ASSIGNED', Job.node_id == node_id).limit(1)
        )
        running_job = running_result.scalar_one_or_none()

        # 3. Eligible pending jobs (evaluate first 100 PENDING, return up to 50 matches)
        pending_result = await db.execute(
            select(Job).where(Job.status == 'PENDING').order_by(Job.created_at).limit(100)
        )
        pending_jobs = pending_result.scalars().all()
        node_tags = JobService._get_effective_tags(node)
        node_caps_dict = json.loads(node.capabilities) if node.capabilities else {}
        eligible = []
        for job in pending_jobs:
            if len(eligible) >= 50:
                break
            if JobService._node_is_eligible(node, job, node_tags, node_caps_dict):
                eligible.append(job)

        # 4. Recent execution history (jobs completed on this node in past 24h)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        history_result = await db.execute(
            select(Job).where(
                Job.node_id == node_id,
                Job.status.in_(['COMPLETED', 'FAILED', 'DEAD_LETTER', 'SECURITY_REJECTED']),
                Job.completed_at >= cutoff
            ).order_by(Job.completed_at.desc()).limit(100)
        )
        recent_jobs = history_result.scalars().all()

        def job_summary(j: Job) -> dict:
            return {
                "guid": j.guid,
                "status": j.status,
                "task_type": j.task_type,
                "name": getattr(j, 'name', None),
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "runtime": getattr(j, 'runtime', None),
            }

        return {
            "running_job": job_summary(running_job) if running_job else None,
            "eligible_pending_jobs": [job_summary(j) for j in eligible],
            "recent_history": [job_summary(j) for j in recent_jobs],
            "capabilities": json.loads(node.capabilities) if node.capabilities else {},
        }

    @staticmethod
    async def pull_work(node_id: str, node_ip: str, db: AsyncSession) -> PollResponse:
        """Called by Environment Nodes."""
        # 1. Fetch Node Configuration
        result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = result.scalar_one_or_none()
        
        # Default concurrency limit
        concurrency = 5

        if node:
            # Security TDA-04: Quarantine check; DRAINING nodes also get no new work
            if node.status in ("TAMPERED", "DRAINING"):
                if node.status == "TAMPERED":
                    logger.error(f"Rejecting work request from TAMPERED node {node_id}")
                return PollResponse(job=None)

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
        current_env_tag = node.env_tag if node.operator_env_tag and node.env_tag else ("" if node.operator_env_tag else None)

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
            return PollResponse(job=None, env_tag=current_env_tag)
        
        # 3. Find highest priority PENDING or eligible RETRYING job matching criteria
        # target_node_id enforcement: jobs with target_node_id set are only visible
        # to the targeted node; jobs without target_node_id are visible to all nodes.
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
            ).where(
                (Job.target_node_id == None) | (Job.target_node_id == node_id)
            ).order_by(Job.created_at.asc()).limit(50)
        )
        jobs = result.scalars().all()

        selected_job = None
        node_tags = JobService._get_effective_tags(node) if node else []
        node_caps_dict = json.loads(node.capabilities) if node and node.capabilities else {}

        import sys
        print(f"[pull_work DEBUG] Node {node_id}: Found {len(jobs)} candidate jobs, node_tags={node_tags}, caps={list(node_caps_dict.keys())}", file=sys.stderr)

        for i, candidate in enumerate(jobs):
            if not JobService._node_is_eligible(node, candidate, node_tags, node_caps_dict):
                print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): INELIGIBLE (target_tags={candidate.target_tags}, env_tag={candidate.env_tag}, caps={candidate.capability_requirements})", file=sys.stderr)
                continue
            print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): ELIGIBLE", file=sys.stderr)

            # ENFC-03b: Check node capacity before assigning (fresh check at dispatch)
            if candidate.memory_limit:
                available_capacity = await _get_node_available_capacity(node, db)
                job_bytes = parse_bytes(candidate.memory_limit)
                if job_bytes > available_capacity:
                    # Job doesn't fit on this node — try next candidate
                    print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): SKIP (capacity: need {job_bytes}, have {available_capacity})", file=sys.stderr)
                    continue
                print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): Capacity OK ({job_bytes}/{available_capacity})", file=sys.stderr)
            else:
                print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): No memory limit", file=sys.stderr)

            if IS_POSTGRES:
                # Two-phase lock: lock only the single chosen row to prevent double-assignment
                # SKIP LOCKED means if another node grabbed it first, we try the next candidate
                # Status filter guards against the race where Session A commits (releasing lock)
                # before Session B's lock query runs — without it, B would re-lock an ASSIGNED row
                print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): Attempting to lock (POSTGRES)", file=sys.stderr)
                lock_result = await db.execute(
                    select(Job)
                    .where(Job.guid == candidate.guid)
                    .where(or_(Job.status == 'PENDING', Job.status == 'RETRYING'))
                    .with_for_update(skip_locked=True)
                )
                locked_job = lock_result.scalar_one_or_none()
                if locked_job is None:
                    print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): SKIP (locked by another node)", file=sys.stderr)
                    continue  # Another node grabbed this job — try next candidate
                print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): LOCKED, assigning", file=sys.stderr)
                selected_job = locked_job
            else:
                # SQLite: serialised writes provide equivalent correctness — no locking needed
                print(f"[pull_work DEBUG]   Job {i} ({candidate.guid}): Selected (SQLite, no lock needed)", file=sys.stderr)
                selected_job = candidate
            break

        if not selected_job:
            return PollResponse(job=None, env_tag=current_env_tag)
            
        selected_job.status = 'ASSIGNED'
        selected_job.node_id = node_id
        selected_job.started_at = datetime.utcnow()

        # RETRY-02: Set job_run_id at first dispatch; idempotent — retries reuse the same UUID
        if selected_job.job_run_id is None:
            selected_job.job_run_id = str(uuid.uuid4())

        # SEC-02: Verify HMAC integrity before dispatching to node
        if selected_job.signature_hmac and selected_job.payload:
            try:
                _pl = json.loads(selected_job.payload)
                _sp = _pl.get("signature_payload")
                _si = _pl.get("signature_id")
                if _sp and _si and not verify_signature_hmac(
                    ENCRYPTION_KEY, selected_job.signature_hmac, _sp, _si, selected_job.guid
                ):
                    # HMAC mismatch — reject before dispatch; do NOT assign to node
                    selected_job.status = "SECURITY_REJECTED"
                    selected_job.completed_at = datetime.utcnow()
                    selected_job.node_id = None
                    selected_job.started_at = None

                    class _SystemActor:
                        username = "system"

                    audit(db, _SystemActor(), "security:hmac_mismatch", resource_id=selected_job.guid, detail={
                        "job_id": selected_job.guid,
                        "node_id": node_id,
                        "reason": "signature_payload HMAC integrity check failed at dispatch",
                    })
                    await db.commit()
                    return PollResponse(job=None, env_tag=current_env_tag)
            except Exception:
                pass  # Malformed payload — allow dispatch; node will handle

        encrypted_payload = json.loads(selected_job.payload)
        payload = decrypt_secrets(encrypted_payload)

        # Phase 149: Populate env_vars from workflow parameters if this is a workflow job
        env_vars = None
        if selected_job.workflow_step_run_id:
            try:
                # Fetch the WorkflowStepRun to get run_id
                step_run = await db.get(WorkflowStepRun, selected_job.workflow_step_run_id)
                if step_run:
                    # Fetch the WorkflowRun to get parameters_json
                    run = await db.get(WorkflowRun, step_run.workflow_run_id)
                    if run and run.parameters_json:
                        parameters_dict = json.loads(run.parameters_json)
                        # Build env_vars: WORKFLOW_PARAM_<NAME>=<value>
                        env_vars = {f"WORKFLOW_PARAM_{k}": str(v) for k, v in parameters_dict.items()}
            except Exception as e:
                logger.warning(f"Failed to populate env_vars for job {selected_job.guid}: {e}")
                env_vars = None

        # Phase 167-02: Resolve Vault secrets if enabled on job
        vault_secrets_resolved = {}
        if getattr(selected_job, 'use_vault_secrets', False) and getattr(selected_job, 'vault_secrets', None):
            try:
                vault_secret_names = json.loads(selected_job.vault_secrets) if isinstance(selected_job.vault_secrets, str) else selected_job.vault_secrets
                if vault_secret_names:
                    # Get vault_service from app state
                    from ..main import app
                    vault_service = getattr(app.state, 'vault_service', None)
                    if not vault_service:
                        raise HTTPException(status_code=422, detail="Vault service not available")

                    # Check vault status before resolution
                    vault_status = await vault_service.status()
                    if vault_status != "healthy":
                        raise HTTPException(
                            status_code=422,
                            detail=f"Vault unavailable for secret resolution (status: {vault_status})"
                        )

                    # Resolve secrets from Vault
                    vault_secrets_resolved = await vault_service.resolve(vault_secret_names)
            except HTTPException:
                raise  # Re-raise HTTP exceptions
            except Exception as e:
                logger.error(f"Vault secret resolution failed for job {selected_job.guid}: {e}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Secret resolution failed: {str(e)}"
                )

        await db.commit()

        # Phase 167-02: Inject resolved Vault secrets into env_vars as VAULT_SECRET_<NAME>=<value>
        if vault_secrets_resolved:
            if env_vars is None:
                env_vars = {}
            for secret_name, secret_value in vault_secrets_resolved.items():
                env_vars[f"VAULT_SECRET_{secret_name}"] = secret_value

        work_resp = WorkResponse(
            guid=selected_job.guid,
            task_type=selected_job.task_type,
            payload=payload,
            max_retries=selected_job.max_retries,
            backoff_multiplier=selected_job.backoff_multiplier,
            timeout_minutes=selected_job.timeout_minutes,
            started_at=selected_job.started_at,
            memory_limit=selected_job.memory_limit,
            cpu_limit=selected_job.cpu_limit,
            env_vars=env_vars,
        )
        return PollResponse(job=work_resp, env_tag=current_env_tag)

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
            # VIS-04: Preserve DRAINING/TAMPERED/REVOKED status — heartbeat must not overwrite
            if node.status not in ("DRAINING", "TAMPERED", "REVOKED"):
                node.status = "ONLINE"
            if stats_json:
                node.stats = stats_json
            if tags_json:
                node.tags = tags_json
            # Operator-set env_tag takes precedence over node self-reporting.
            # Only update from heartbeat when no operator override is in place.
            if not node.operator_env_tag:
                node.env_tag = hb.env_tag

            # NEW: Always update cgroup version + raw info (unconditional, stateless)
            node.detected_cgroup_version = hb.detected_cgroup_version
            node.cgroup_raw = hb.cgroup_raw

            # Phase 124: Update execution_mode from heartbeat
            node.execution_mode = hb.execution_mode

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
            # Prune: keep last 60 rows per node — DEBT-01: two-step approach
            # for SQLite compatibility (correlated subquery with OFFSET is not
            # reliably supported on older SQLite versions).
            _keep_result = await db.execute(
                select(NodeStats.id)
                .where(NodeStats.node_id == node_id)
                .order_by(desc(NodeStats.recorded_at))
                .limit(60)
            )
            keep_ids = [row[0] for row in _keep_result.all()]
            if keep_ids:
                await db.execute(
                    delete(NodeStats)
                    .where(NodeStats.node_id == node_id)
                    .where(NodeStats.id.notin_(keep_ids))
                )

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
        audit_after_commit = None
        if report.security_rejected:
            new_status = "SECURITY_REJECTED"
            # SEC-01: Audit SECURITY_REJECTED with node attribution (defer until after commit)
            _payload_data = {}
            try:
                _payload_data = json.loads(job.payload) if job.payload else {}
            except Exception:
                pass

            class _NodeActor:
                username = job.node_id or "unknown-node"

            audit_after_commit = (_NodeActor(), "security:rejected", guid, {
                "script_hash": report.script_hash,
                "job_id": guid,
                "signature_id": _payload_data.get("signature_id"),
                "node_id": job.node_id,
            })
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

        # Update job — include stdout/stderr in result for orchestrator clients
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
            job.result = json.dumps({"flight_recorder": flight_report, "stdout": stdout_text, "stderr": stderr_text})
        else:
            job.result = json.dumps({"exit_code": report.exit_code, "stdout": stdout_text, "stderr": stderr_text})

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

        # Store node_id before commit clears it on retry
        _reporting_node_id = job.node_id
        await db.commit()

        # SEC-01: Perform deferred audit after commit to avoid transaction abort
        if audit_after_commit:
            user, action, resource_id, detail = audit_after_commit
            audit(db, user, action, resource_id=resource_id, detail=detail)

        # VIS-04: DRAINING auto-transition — if the last ASSIGNED job on this node just completed,
        # transition the node to OFFLINE. Runs AFTER commit so the count sees updated state.
        if _reporting_node_id:
            _node_result = await db.execute(select(Node).where(Node.node_id == _reporting_node_id))
            _draining_node = _node_result.scalar_one_or_none()
            if _draining_node and _draining_node.status == "DRAINING":
                _count_result = await db.execute(
                    select(func.count(Job.guid)).where(
                        Job.status == 'ASSIGNED',
                        Job.node_id == _reporting_node_id,
                    )
                )
                if (_count_result.scalar() or 0) == 0:
                    _draining_node.status = "OFFLINE"
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
    async def get_dispatch_diagnosis(guid: str, db: AsyncSession) -> dict:
        """Returns {reason, message, queue_position} explaining why a PENDING job hasn't dispatched."""
        # 1. Load job
        job_result = await db.execute(select(Job).where(Job.guid == guid))
        job = job_result.scalar_one_or_none()
        if not job:
            return {"reason": "not_found", "message": "Job not found", "queue_position": None}
        if job.status == "ASSIGNED" and job.started_at is not None:
            threshold_minutes = (job.timeout_minutes or 30) * 1.2
            elapsed_minutes = (datetime.utcnow() - job.started_at).total_seconds() / 60
            if elapsed_minutes > threshold_minutes:
                return {
                    "reason": "stuck_assigned",
                    "message": f"Assigned to {job.node_id} — no response in {int(elapsed_minutes)} min",
                    "queue_position": None,
                }
        if job.status != "PENDING":
            return {
                "reason": "not_pending",
                "message": f"Job is {job.status}, not PENDING",
                "queue_position": None,
            }

        # 2. Handle explicit target_node_id targeting
        if job.target_node_id:
            tn_result = await db.execute(select(Node).where(Node.node_id == job.target_node_id))
            target_node = tn_result.scalar_one_or_none()
            if not target_node or target_node.status not in ("ONLINE", "BUSY"):
                status_str = target_node.status if target_node else "not found"
                return {
                    "reason": "target_node_unavailable",
                    "message": f"Target node '{job.target_node_id}' is {status_str} and cannot accept work.",
                    "queue_position": None,
                }

        # 3. Check if any ONLINE/BUSY node exists at all
        nodes_result = await db.execute(
            select(Node).where(Node.status.in_(["ONLINE", "BUSY"]))
        )
        online_nodes = nodes_result.scalars().all()

        if not online_nodes:
            return {
                "reason": "no_nodes_online",
                "message": "No nodes are currently online. The job will dispatch when a node connects.",
                "queue_position": None,
            }

        # 4. Find eligible nodes using _node_is_eligible helper
        eligible_nodes = []
        missing_cap = None
        for node in online_nodes:
            node_tags = JobService._get_effective_tags(node)
            node_caps_dict = json.loads(node.capabilities) if node.capabilities else {}
            if JobService._node_is_eligible(node, job, node_tags, node_caps_dict):
                eligible_nodes.append(node)
            else:
                # Try to identify the missing capability for better error messages
                if job.capability_requirements:
                    try:
                        req_caps = json.loads(job.capability_requirements)
                        for cap_name in req_caps:
                            if cap_name not in node_caps_dict:
                                missing_cap = cap_name
                                break
                    except Exception:
                        pass

        if not eligible_nodes:
            msg = "No nodes match this job's requirements."
            if missing_cap:
                msg = f"No nodes have the required capability '{missing_cap}'."
            return {"reason": "capability_mismatch", "message": msg, "queue_position": None}

        # 4.5. Memory admission check: verify job fits on at least one eligible node
        if job.memory_limit and eligible_nodes:
            job_bytes = parse_bytes(job.memory_limit)
            nodes_breakdown = []
            largest_available = 0

            for node in eligible_nodes:
                available = await _get_node_available_capacity(node, db)
                largest_available = max(largest_available, available)

                capacity = parse_bytes(node.job_memory_limit or "512m")
                used = await _sum_node_assigned_limits(node.node_id, db)

                nodes_breakdown.append({
                    "node_id": node.node_id,
                    "capacity_mb": capacity // (1024 ** 2),
                    "used_mb": used // (1024 ** 2),
                    "available_mb": available // (1024 ** 2),
                    "fits": "yes" if available >= job_bytes else "no"
                })

            if job_bytes > largest_available:
                return {
                    "reason": "insufficient_memory",
                    "message": f"Job requires {job.memory_limit} but no eligible node has sufficient capacity. "
                              f"Largest available: {_format_bytes(largest_available)}",
                    "nodes_breakdown": nodes_breakdown,
                    "queue_position": None
                }

        # 5. Check if all eligible nodes are at concurrency limit (default 5)
        all_busy = True
        for node in eligible_nodes:
            assigned_result = await db.execute(
                select(func.count(Job.guid)).where(
                    Job.status == 'ASSIGNED',
                    Job.node_id == node.node_id,
                )
            )
            assigned = assigned_result.scalar() or 0
            if assigned < 5:
                all_busy = False
                break

        if all_busy:
            # Count jobs ahead in queue (created before this job, PENDING or RETRYING)
            pos_result = await db.execute(
                select(func.count(Job.guid)).where(
                    Job.status.in_(["PENDING", "RETRYING"]),
                    Job.created_at < job.created_at,
                )
            )
            queue_position = (pos_result.scalar() or 0) + 1
            return {
                "reason": "all_nodes_busy",
                "message": f"All eligible nodes are at capacity. Approximately {queue_position - 1} jobs ahead in queue.",
                "queue_position": queue_position,
            }

        return {
            "reason": "pending_dispatch",
            "message": "This job will be dispatched on the next poll cycle.",
            "queue_position": 1,
        }

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
