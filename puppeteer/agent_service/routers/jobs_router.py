"""
Jobs domain router: job CRUD, job definitions, job templates, CI/CD dispatch.

Endpoints:
- GET /jobs - List jobs with pagination and filters
- POST /jobs - Create a job
- GET /jobs/{guid} - Get a single job
- PATCH /jobs/{guid}/cancel - Cancel a PENDING or ASSIGNED job
- POST /jobs/{guid}/retry - Retry a FAILED or DEAD_LETTER job
- POST /jobs/{guid}/resubmit - Create a new job from a failed one (originating_guid)
- GET /jobs/{guid}/dispatch-diagnosis - Get diagnostic info about why a job hasn't dispatched
- POST /jobs/bulk-cancel - Cancel multiple jobs
- POST /jobs/bulk-resubmit - Resubmit multiple failed jobs
- DELETE /jobs/bulk - Delete multiple terminal jobs
- POST /jobs/dispatch-diagnosis/bulk - Get diagnosis for multiple jobs
- GET /jobs/count - Get count of jobs (optionally by status)
- GET /jobs/export - Export jobs as CSV
- POST /api/dispatch - CI/CD dispatch: create job from definition
- GET /api/dispatch/{job_guid}/status - CI/CD poll endpoint
- POST /api/job-templates - Create a job template
- GET /api/job-templates - List job templates
- GET /api/job-templates/{template_id} - Get a single template
- PATCH /api/job-templates/{template_id} - Update a template
- DELETE /api/job-templates/{template_id} - Delete a template
- POST /jobs/definitions - Create a job definition
- GET /jobs/definitions - List job definitions
- DELETE /jobs/definitions/{id} - Delete a job definition
- PATCH /jobs/definitions/{id}/toggle - Enable/disable a job definition
- GET /jobs/definitions/{id} - Get a single job definition
- POST /api/jobs/push - Push a job definition with Ed25519 signature
- PATCH /jobs/definitions/{id} - Update a job definition
- GET /api/schedule - Get unified schedule (merged ScheduledJob + Workflow items)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
import logging
import json
import csv
import io
import uuid
from datetime import datetime, timedelta, UTC

from ..db import get_db, AsyncSession, User, Job, ScheduledJob, JobTemplate, ExecutionRecord, Signature
from ..deps import get_current_user, require_permission, require_auth, audit
from ..models import (
    JobCreate, JobResponse, JobDefinitionCreate, JobDefinitionResponse,
    JobTemplateCreate, JobTemplateResponse, JobTemplateUpdate,
    DispatchRequest, DispatchResponse, DispatchStatusResponse,
    BulkActionResponse, PaginatedResponse, BulkJobActionRequest,
    ActionResponse, JobCountResponse, DispatchDiagnosisResponse,
    BulkDiagnosisRequest, BulkDispatchDiagnosisResponse,
    JobDefinitionUpdate, JobPushRequest, ScheduleListResponse,
    PaginatedJobResponse
)
from ..services.job_service import JobService
from ..services.signature_service import SignatureService
from ..services.scheduler_service import scheduler_service
from ..services.workflow_service import WorkflowService
from ..models import WorkflowStepUpdatedEvent

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level constants for job state management
CANCELLABLE_STATES = {"PENDING", "ASSIGNED"}
RESUBMITTABLE_STATES = {"FAILED", "DEAD_LETTER"}
TERMINAL_STATES = {"COMPLETED", "FAILED", "DEAD_LETTER", "CANCELLED", "SECURITY_REJECTED"}
_TERMINAL_STATUSES = TERMINAL_STATES

# Signing fields stripped from job template payloads
SIGNING_FIELDS = {"signature", "signature_id"}

# CSV export headers
EXEC_CSV_HEADERS = ["job_guid", "node_id", "status", "exit_code",
                    "started_at", "completed_at", "duration_s", "attempt_number", "pinned"]


def _job_to_response(job: Job) -> JobResponse:
    """Build a JobResponse from a Job ORM object."""
    payload = json.loads(job.payload) if isinstance(job.payload, str) else job.payload
    duration = None
    if job.started_at:
        end = job.completed_at or datetime.utcnow()
        duration = (end - job.started_at).total_seconds()
    return JobResponse(
        guid=job.guid,
        status=job.status,
        payload=payload,
        result=json.loads(job.result) if job.result else None,
        node_id=job.node_id,
        started_at=job.started_at,
        duration_seconds=duration,
        target_tags=json.loads(job.target_tags) if job.target_tags else None,
        depends_on=json.loads(job.depends_on) if job.depends_on else None,
        task_type=job.task_type,
        name=job.name,
        created_by=job.created_by,
        created_at=job.created_at,
        runtime=job.runtime,
        originating_guid=job.originating_guid,
    )


# ===== Jobs CRUD =====

@router.get(
    "/jobs",
    response_model=PaginatedJobResponse,
    tags=["Jobs"],
    summary="List all jobs",
    description="Retrieve a paginated list of all jobs with optional filtering by status, runtime, tags, and other criteria."
)
async def list_jobs(
    cursor: Optional[str] = None,
    limit: int = 50,
    status: Optional[str] = None,
    runtime: Optional[str] = None,
    task_type: Optional[str] = None,
    node_id: Optional[str] = None,
    tags: Optional[str] = None,
    created_by: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = await JobService.list_jobs(
        db, limit=limit, cursor=cursor,
        status=status, runtime=runtime, task_type=task_type,
        node_id=node_id, tags=tags_list,
        created_by=created_by, date_from=date_from, date_to=date_to, search=search,
    )
    return result  # {items, total, next_cursor}


@router.get(
    "/jobs/count",
    response_model=JobCountResponse,
    tags=["Jobs"],
    summary="Get job count",
    description="Get total count of jobs, optionally filtered by status."
)
async def count_jobs(status: Optional[str] = None, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    query = select(func.count()).select_from(Job).where(Job.task_type != 'system_heartbeat')
    if status and status.upper() != 'ALL':
        query = query.where(Job.status == status.upper())
    result = await db.execute(query)
    return {"total": result.scalar()}


@router.get(
    "/jobs/export",
    response_class=StreamingResponse,
    tags=["Jobs"],
    summary="Export jobs as CSV",
    description="Export filtered job records as a CSV file with streaming response"
)
async def export_jobs(
    status: Optional[str] = None,
    runtime: Optional[str] = None,
    task_type: Optional[str] = None,
    node_id: Optional[str] = None,
    tags: Optional[str] = None,
    created_by: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    EXPORT_LIMIT = 10_000
    jobs = await JobService.list_jobs_for_export(
        db, limit=EXPORT_LIMIT,
        status=status, runtime=runtime, task_type=task_type,
        node_id=node_id, tags=tags_list,
        created_by=created_by, date_from=date_from, date_to=date_to, search=search,
    )

    HEADERS = ["guid", "name", "status", "task_type", "display_type", "runtime",
               "node_id", "created_at", "started_at", "completed_at", "duration_seconds", "target_tags"]

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(HEADERS)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()
        for job in jobs:
            writer.writerow([
                job.get("guid", ""), job.get("name", ""), job.get("status", ""),
                job.get("task_type", ""), job.get("display_type", ""), job.get("runtime", ""),
                job.get("node_id", ""), job.get("created_at", ""), job.get("started_at", ""),
                job.get("completed_at", ""), job.get("duration_seconds", ""),
                ",".join(job.get("target_tags") or []),
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()

    return StreamingResponse(generate(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=jobs.csv"})


@router.post("/jobs", response_model=JobResponse, tags=["Jobs"])
async def create_job(job_req: JobCreate, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    try:
        # SRCH-03: stamp submitter username so Jobs view can filter by creator
        job_req = job_req.model_copy(update={"created_by": current_user.username})

        # SEC-JOB: If the payload carries a user signature, verify it server-side
        # against the registered public key, then countersign with the server's own
        # Ed25519 signing key so the node can verify using its cached verification.key.
        payload_dict = dict(job_req.payload)
        user_sig = payload_dict.get("signature")
        sig_id = payload_dict.get("signature_id")
        script_content = payload_dict.get("script_content")

        # WIN-05: Normalize CRLF → LF before signature verification and countersigning.
        # This matches the normalization in node.py (line 585) so both sides agree on bytes.
        if script_content:
            script_content = script_content.replace('\r\n', '\n').replace('\r', '\n')
            payload_dict["script_content"] = script_content

        if user_sig and sig_id and script_content:
            # 1. Verify user's signature against the registered public key
            sig_result = await db.execute(select(Signature).where(Signature.id == sig_id))
            sig_rec = sig_result.scalar_one_or_none()
            if not sig_rec:
                raise HTTPException(status_code=422, detail=f"Signature key ID '{sig_id}' not found in registry")
            try:
                SignatureService.verify_payload_signature(sig_rec.public_key, user_sig, script_content)
            except Exception as _ve:
                raise HTTPException(status_code=422, detail=f"Signature verification failed: {_ve}")

        # 2. Countersign script with the server's Ed25519 signing key so the
        #    node can verify using its fetched verification.key (which is the
        #    server's public counterpart). This is mandatory for all job scripts.
        if script_content:
            try:
                server_sig = SignatureService.countersign_for_node(script_content)
                # Set server countersignature so node verifies correctly
                payload_dict["signature"] = server_sig
                job_req = job_req.model_copy(update={"payload": payload_dict})
            except Exception as e:
                raise HTTPException(status_code=500, detail="Server signing key unavailable — contact admin")

        result = await JobService.create_job(job_req, db)
        from ..main import ws_manager
        await ws_manager.broadcast("job:created", {"guid": result["guid"], "status": "PENDING", "task_type": job_req.task_type})
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{guid}", response_model=JobResponse, tags=["Jobs"])
async def get_job(guid: str, current_user: User = Depends(require_permission("jobs:read")), db: AsyncSession = Depends(get_db)):
    """Retrieve a single job by its GUID."""
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    payload = job.payload if isinstance(job.payload, dict) else json.loads(job.payload or '{}')
    result_val = job.result if isinstance(job.result, dict) else json.loads(job.result or 'null') if job.result else None
    target_tags = job.target_tags if isinstance(job.target_tags, list) else json.loads(job.target_tags or 'null') if job.target_tags else None

    # Calculate duration_seconds from started_at and completed_at
    duration = None
    if job.started_at and job.completed_at:
        duration = int((job.completed_at - job.started_at).total_seconds())

    return JobResponse(
        guid=job.guid,
        status=job.status,
        payload=payload,
        result=result_val,
        node_id=job.node_id,
        started_at=job.started_at,
        duration_seconds=duration,
        target_tags=target_tags,
        task_type=job.task_type,
        display_type=getattr(job, 'display_type', None),
        name=getattr(job, 'name', None),
        created_by=getattr(job, 'created_by', None),
        created_at=job.created_at,
        runtime=getattr(job, 'runtime', None),
        originating_guid=getattr(job, 'originating_guid', None),
    )


@router.patch(
    "/jobs/{guid}/cancel",
    response_model=ActionResponse,
    tags=["Jobs"],
    summary="Cancel a job",
    description="Cancel a PENDING or ASSIGNED job, transitioning it to CANCELLED status."
)
async def cancel_job(guid: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("PENDING", "ASSIGNED"):
        raise HTTPException(status_code=409, detail=f"Cannot cancel a job with status {job.status}")
    job.status = "CANCELLED"
    job.completed_at = datetime.utcnow()
    audit(db, current_user, "job:cancel", guid)
    await db.commit()
    from ..main import ws_manager
    await ws_manager.broadcast("job:updated", {"guid": guid, "status": "CANCELLED"})
    return {"status": "cancelled", "resource_type": "job", "resource_id": guid}


@router.get(
    "/jobs/{guid}/dispatch-diagnosis",
    response_model=DispatchDiagnosisResponse,
    tags=["Jobs"],
    summary="Get dispatch diagnosis",
    description="Get diagnostic information explaining why a PENDING job has not yet been dispatched to a node."
)
async def get_dispatch_diagnosis(guid: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Returns structured explanation for why a PENDING job has not yet dispatched."""
    result = await JobService.get_dispatch_diagnosis(guid, db)
    if result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.post(
    "/jobs/dispatch-diagnosis/bulk",
    response_model=BulkDispatchDiagnosisResponse,
    tags=["Jobs"],
    summary="Get bulk dispatch diagnosis",
    description="Get dispatch diagnostic information for multiple jobs in one request."
)
async def bulk_dispatch_diagnosis(
    req: BulkDiagnosisRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Returns dispatch diagnosis for multiple jobs in one call (Phase 88 — DIAG-01)."""
    results = {}
    for guid in req.guids:
        results[guid] = await JobService.get_dispatch_diagnosis(guid, db)
    return {"results": results}


@router.post(
    "/jobs/{guid}/retry",
    response_model=JobResponse,
    tags=["Jobs"],
    summary="Retry a job",
    description="Reset a FAILED or DEAD_LETTER job back to PENDING status to retry execution."
)
async def retry_job(
    guid: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Resets a FAILED or DEAD_LETTER job to PENDING."""
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("FAILED", "DEAD_LETTER"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry job with status {job.status}. Only FAILED and DEAD_LETTER jobs can be retried."
        )
    job.status = "PENDING"
    job.retry_count = 0
    job.retry_after = None
    job.node_id = None
    job.completed_at = None
    audit(db, current_user, "job:retry", guid)
    await db.commit()
    from ..main import ws_manager
    await ws_manager.broadcast("job:updated", {"guid": guid, "status": "PENDING"})
    # Construct JobResponse from updated job
    payload = job.payload if isinstance(job.payload, dict) else json.loads(job.payload or '{}')
    result_val = job.result if isinstance(job.result, dict) else json.loads(job.result or 'null') if job.result else None
    target_tags = job.target_tags if isinstance(job.target_tags, list) else json.loads(job.target_tags or 'null') if job.target_tags else None
    return JobResponse(
        guid=job.guid,
        status=job.status,
        payload=payload,
        result=result_val,
        node_id=job.node_id,
        started_at=job.started_at,
        duration_seconds=None,
        target_tags=target_tags,
        task_type=job.task_type,
        display_type=getattr(job, 'display_type', None),
        name=getattr(job, 'name', None),
        created_by=getattr(job, 'created_by', None),
        created_at=job.created_at,
        runtime=getattr(job, 'runtime', None),
        originating_guid=getattr(job, 'originating_guid', None),
    )


@router.post("/jobs/bulk-cancel", response_model=BulkActionResponse, tags=["Jobs"])
async def bulk_cancel_jobs(
    req: BulkJobActionRequest,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel PENDING/ASSIGNED jobs in bulk; skips terminal-state jobs and reports them."""
    result = await db.execute(select(Job).where(Job.guid.in_(req.guids)))
    jobs = result.scalars().all()
    processed, skipped_guids = 0, []
    for job in jobs:
        if job.status in CANCELLABLE_STATES:
            job.status = "CANCELLED"
            job.completed_at = datetime.utcnow()
            audit(db, current_user, "job:cancel", job.guid)
            processed += 1
        else:
            skipped_guids.append(job.guid)
    await db.commit()
    return BulkActionResponse(processed=processed, skipped=len(skipped_guids), skipped_guids=skipped_guids)


@router.post("/jobs/bulk-resubmit", response_model=BulkActionResponse, tags=["Jobs"])
async def bulk_resubmit_jobs(
    req: BulkJobActionRequest,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Resubmit FAILED/DEAD_LETTER jobs in bulk; creates a new PENDING job for each."""
    result = await db.execute(select(Job).where(Job.guid.in_(req.guids)))
    jobs = result.scalars().all()
    processed, skipped_guids = 0, []
    for job in jobs:
        if job.status in RESUBMITTABLE_STATES:
            new_guid = str(uuid.uuid4())
            new_job = Job(
                guid=new_guid,
                task_type=job.task_type,
                payload=job.payload,
                status="PENDING",
                target_tags=job.target_tags,
                capability_requirements=job.capability_requirements,
                max_retries=job.max_retries,
                backoff_multiplier=job.backoff_multiplier,
                timeout_minutes=job.timeout_minutes,
                runtime=job.runtime,
                name=job.name,
                created_by=current_user.username,
                signature_hmac=job.signature_hmac,
                originating_guid=job.guid,
            )
            db.add(new_job)
            audit(db, current_user, "job:resubmit", new_guid)
            processed += 1
        else:
            skipped_guids.append(job.guid)
    await db.commit()
    return BulkActionResponse(processed=processed, skipped=len(skipped_guids), skipped_guids=skipped_guids)


@router.delete("/jobs/bulk", response_model=BulkActionResponse, tags=["Jobs"])
async def bulk_delete_jobs(
    req: BulkJobActionRequest,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Delete terminal-state jobs in bulk; skips non-terminal jobs and reports them."""
    result = await db.execute(select(Job).where(Job.guid.in_(req.guids)))
    jobs = result.scalars().all()
    processed, skipped_guids = 0, []
    for job in jobs:
        if job.status in TERMINAL_STATES:
            await db.delete(job)
            audit(db, current_user, "job:delete", job.guid)
            processed += 1
        else:
            skipped_guids.append(job.guid)
    await db.commit()
    return BulkActionResponse(processed=processed, skipped=len(skipped_guids), skipped_guids=skipped_guids)


@router.post("/jobs/{guid}/resubmit", response_model=JobResponse, tags=["Jobs"])
async def resubmit_job(
    guid: str,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new PENDING job from a FAILED/DEAD_LETTER job, with originating_guid set."""
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in RESUBMITTABLE_STATES:
        raise HTTPException(status_code=409, detail="Only FAILED or DEAD_LETTER jobs can be resubmitted")
    new_guid = str(uuid.uuid4())
    new_job = Job(
        guid=new_guid,
        task_type=job.task_type,
        payload=job.payload,
        status="PENDING",
        target_tags=job.target_tags,
        capability_requirements=job.capability_requirements,
        max_retries=job.max_retries,
        backoff_multiplier=job.backoff_multiplier,
        timeout_minutes=job.timeout_minutes,
        runtime=job.runtime,
        name=job.name,
        created_by=current_user.username,
        signature_hmac=job.signature_hmac,
        originating_guid=guid,
    )
    db.add(new_job)
    audit(db, current_user, "job:resubmit", new_guid)
    await db.commit()
    await db.refresh(new_job)
    from ..main import ws_manager
    await ws_manager.broadcast("job:created", {"guid": new_guid, "status": "PENDING"})
    return _job_to_response(new_job)


# ===== CI/CD Dispatch =====

@router.post("/api/dispatch", response_model=DispatchResponse, tags=["CI/CD Dispatch"])
async def dispatch_job(
    req: DispatchRequest,
    request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """CI/CD dispatch endpoint. Creates a job from a job definition and returns a poll URL.
    Intended caller: service principals with jobs:write permission.
    No-node condition: job is created as PENDING; pipelines detect timeout by polling poll_url."""

    # 1. Fetch the job definition
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == req.job_definition_id))
    s_job = result.scalar_one_or_none()
    if not s_job:
        raise HTTPException(
            status_code=404,
            detail={"error": "job_definition_not_found", "job_definition_id": req.job_definition_id},
        )

    # 1b. Reject REVOKED definitions — cannot dispatch a job from a revoked definition
    if s_job.status == "REVOKED":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "job_definition_revoked",
                "id": s_job.id,
                "message": "Cannot dispatch a REVOKED job definition.",
            },
        )

    # 2. Resolve env_tag: dispatch request overrides definition's env_tag; fall back to definition
    effective_env_tag = req.env_tag if req.env_tag is not None else s_job.env_tag

    # 3. Build JobCreate
    import os
    runtime = getattr(s_job, 'runtime', None) or 'python'
    payload_dict = {
        "script_content": s_job.script_content,
        "signature": s_job.signature_payload,
        "secrets": {},
        "runtime": runtime,
    }
    job_create = JobCreate(
        task_type="script",
        runtime=runtime,
        payload=payload_dict,
        target_tags=json.loads(s_job.target_tags) if s_job.target_tags else None,
        capability_requirements=json.loads(s_job.capability_requirements) if s_job.capability_requirements else None,
        scheduled_job_id=s_job.id,
        max_retries=req.max_retries if req.max_retries is not None else s_job.max_retries,
        backoff_multiplier=s_job.backoff_multiplier,
        timeout_minutes=req.timeout_minutes if req.timeout_minutes is not None else s_job.timeout_minutes,
        env_tag=effective_env_tag,
    )

    # 4. Create the job
    job_result = await JobService.create_job(job_create, db)
    job_guid = job_result["guid"]

    # 5. Build poll_url — use PUBLIC_URL env var to avoid localhost in Docker
    public_url = os.getenv("PUBLIC_URL", str(request.base_url).rstrip("/"))
    poll_url = f"{public_url}/api/dispatch/{job_guid}/status"

    # 6. Audit (sync — do not await, must be before db.commit)
    audit(db, current_user, "dispatch_job", job_guid,
          {"job_definition_id": req.job_definition_id, "env_tag": effective_env_tag})
    await db.commit()

    return DispatchResponse(
        job_guid=job_guid,
        status=job_result.get("status", "PENDING"),
        job_definition_id=s_job.id,
        job_definition_name=s_job.name,
        env_tag=effective_env_tag,
        poll_url=poll_url,
    )


@router.get("/api/dispatch/{job_guid}/status", response_model=DispatchStatusResponse, tags=["CI/CD Dispatch"])
async def get_dispatch_status(
    job_guid: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """CI/CD poll endpoint. Returns structured status for a dispatched job.
    Poll this URL until is_terminal=True to detect pass/fail in pipelines."""

    # 1. Fetch job
    result = await db.execute(select(Job).where(Job.guid == job_guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": "job_not_found", "job_guid": job_guid},
        )

    # 2. Fetch most recent execution record for exit_code
    er_result = await db.execute(
        select(ExecutionRecord)
        .where(ExecutionRecord.job_guid == job_guid)
        .order_by(ExecutionRecord.completed_at.desc())
        .limit(1)
    )
    latest_record = er_result.scalar_one_or_none()

    return DispatchStatusResponse(
        job_guid=job.guid,
        status=job.status,
        exit_code=latest_record.exit_code if latest_record else None,
        node_id=job.node_id,
        attempt=job.retry_count + 1,
        started_at=job.started_at,
        completed_at=job.completed_at,
        is_terminal=job.status in _TERMINAL_STATUSES,
    )


# ===== Job Definitions =====

@router.post("/jobs/definitions", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def create_job_definition(def_req: JobDefinitionCreate, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.create_job_definition(def_req, current_user, db)


@router.get("/jobs/definitions", response_model=List[JobDefinitionResponse], tags=["Job Definitions"])
async def list_job_definitions(current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.list_job_definitions(db)


@router.get(
    "/job-definitions",
    response_model=List[JobDefinitionResponse],
    tags=["Job Definitions"],
    summary="List job definitions (alias)",
    description="Alias for GET /jobs/definitions - returns list of all scheduled job definitions"
)
async def dashboard_job_definitions(current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /job-definitions instead of /jobs/definitions"""
    return await scheduler_service.list_job_definitions(db)


@router.delete("/jobs/definitions/{id}", response_model=ActionResponse, tags=["Job Definitions"])
async def delete_job_definition(id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == id))
    job_def = result.scalar_one_or_none()
    if not job_def:
        raise HTTPException(status_code=404, detail="Job definition not found")
    try:
        scheduler_service.scheduler.remove_job(id)
    except Exception:
        pass
    await db.delete(job_def)
    await db.commit()
    return {"status": "deleted", "resource_type": "job_definition", "resource_id": id}


@router.patch("/jobs/definitions/{id}/toggle", response_model=ActionResponse, tags=["Job Definitions"])
async def toggle_job_definition(id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == id))
    job_def = result.scalar_one_or_none()
    if not job_def:
        raise HTTPException(status_code=404, detail="Job definition not found")
    job_def.is_active = not job_def.is_active
    await db.commit()
    await scheduler_service.sync_scheduler()
    return {"status": "updated", "resource_type": "job_definition", "resource_id": id, "message": f"Job definition is now {'active' if job_def.is_active else 'inactive'}"}


@router.get("/jobs/definitions/{id}", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def get_job_definition(id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.get_job_definition(id, db)


@router.get("/api/schedule", response_model=ScheduleListResponse, tags=["Schedule"])
async def get_schedule(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("jobs:read"))
) -> ScheduleListResponse:
    """
    Unified schedule view: merges ScheduledJob and cron-scheduled Workflow entries.
    Returns sorted by next_run_time ascending (soonest first).
    Only includes active items with cron schedules.
    """
    return await scheduler_service.get_unified_schedule(db)


@router.post("/api/jobs/push", response_model=JobDefinitionResponse, status_code=201, tags=["Job Definitions"])
async def push_job_definition(
    req: JobPushRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """RFC-compliant push endpoint: creates DRAFT or updates existing job with dual JWT+Ed25519 verification."""
    # 1. Validate Ed25519 signature BEFORE any DB write (STAGE-03)
    sig_result = await db.execute(select(Signature).where(Signature.id == req.signature_id))
    sig = sig_result.scalar_one_or_none()
    if not sig:
        raise HTTPException(404, detail="Signature ID not found")
    try:
        SignatureService.verify_payload_signature(sig.public_key, req.signature, req.script_content)
    except Exception as e:
        raise HTTPException(422, detail=(
            "Signature verification failed — the script content does not match the provided signature. "
            "Ensure you signed the exact script content with the private key paired to the registered public key. "
            "See the Signatures page in the dashboard for key generation instructions."
        ))

    # 2. Identity attribution (STAGE-04)
    pushed_by = current_user.username  # "username" or "sp:name" for service principals

    # 3. Upsert logic (STAGE-02)
    if req.id:
        # Update existing job by ID
        result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == req.id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(404, detail="Job definition not found")
        if job.status == "REVOKED":
            raise HTTPException(409, detail={"error": "job_revoked", "id": job.id,
                                             "message": "Job is REVOKED. Un-REVOKE to DEPRECATED before re-pushing."})
        job.script_content = req.script_content
        job.signature_id = req.signature_id
        job.signature_payload = req.signature
        job.pushed_by = pushed_by
        job.updated_at = datetime.utcnow()
    else:
        # Create new job by name — check for name conflict first
        existing_result = await db.execute(select(ScheduledJob).where(ScheduledJob.name == req.name))
        existing = existing_result.scalar_one_or_none()
        if existing:
            raise HTTPException(409, detail={"error": "name_conflict", "id": existing.id,
                                             "message": f"Job '{req.name}' already exists. Use id to update."})
        job = ScheduledJob(
            id=uuid.uuid4().hex,
            name=req.name,
            script_content=req.script_content,
            signature_id=req.signature_id,
            signature_payload=req.signature,
            schedule_cron="",  # DRAFT jobs have no schedule yet
            status="DRAFT",
            pushed_by=pushed_by,
            created_by=pushed_by,
        )
        db.add(job)

    audit(db, current_user, "job:pushed", job.id if req.id else None,
          {"name": req.name or job.name, "pushed_by": pushed_by, "action": "update" if req.id else "create"})
    await db.commit()
    await db.refresh(job)
    return JobDefinitionResponse.model_validate(job)


@router.patch("/jobs/definitions/{id}", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def update_job_definition(id: str, update_req: JobDefinitionUpdate, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.update_job_definition(id, update_req, current_user, db)


# ===== Job Templates =====

@router.post(
    "/api/job-templates",
    response_model=JobTemplateResponse,
    status_code=201,
    tags=["Job Templates"],
    summary="Create job template",
    description="Create a new reusable job template with visibility controls (private or shared)"
)
async def create_job_template(
    body: JobTemplateCreate,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new job template. Signing state fields are stripped from the payload."""
    payload_clean = {k: v for k, v in body.payload.items() if k not in SIGNING_FIELDS}
    template = JobTemplate(
        id=uuid.uuid4().hex,
        name=body.name,
        creator_id=current_user.username,
        visibility=body.visibility,
        payload=json.dumps(payload_clean),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return {
        "id": template.id,
        "name": template.name,
        "creator_id": template.creator_id,
        "visibility": template.visibility,
        "payload": payload_clean,
        "created_at": template.created_at,
    }


@router.get(
    "/api/job-templates",
    response_model=List[JobTemplateResponse],
    tags=["Job Templates"],
    summary="List job templates",
    description="List all job templates visible to the current user (own private templates + all shared templates)"
)
async def list_job_templates(
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    """List job templates visible to the current user (own private + all shared)."""
    result = await db.execute(
        select(JobTemplate).where(
            (JobTemplate.visibility == "shared") | (JobTemplate.creator_id == current_user.username)
        ).order_by(JobTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "creator_id": t.creator_id,
            "visibility": t.visibility,
            "payload": json.loads(t.payload),
            "created_at": t.created_at,
        }
        for t in templates
    ]


@router.get(
    "/api/job-templates/{template_id}",
    response_model=JobTemplateResponse,
    tags=["Job Templates"],
    summary="Get job template",
    description="Fetch a single job template by ID (visibility rules apply - admin can see all, others see own + shared)"
)
async def get_job_template(
    template_id: str,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single job template (visibility rules apply)."""
    result = await db.execute(select(JobTemplate).where(JobTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Job template not found")
    if t.visibility != "shared" and t.creator_id != current_user.username and current_user.role != "admin":
        raise HTTPException(404, "Job template not found")
    return {
        "id": t.id,
        "name": t.name,
        "creator_id": t.creator_id,
        "visibility": t.visibility,
        "payload": json.loads(t.payload),
        "created_at": t.created_at,
    }


@router.patch(
    "/api/job-templates/{template_id}",
    response_model=JobTemplateResponse,
    tags=["Job Templates"],
    summary="Update a job template",
    description="Update job template name or visibility"
)
async def update_job_template(
    template_id: str,
    body: JobTemplateUpdate,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Update a job template's name or visibility. Restricted to creator or admin."""
    result = await db.execute(select(JobTemplate).where(JobTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Job template not found")
    if t.creator_id != current_user.username and current_user.role != "admin":
        raise HTTPException(403, "Only the template creator or an admin can modify this template")
    if body.name is not None:
        t.name = body.name
    if body.visibility is not None:
        t.visibility = body.visibility
    await db.commit()
    await db.refresh(t)
    return {
        "id": t.id,
        "name": t.name,
        "creator_id": t.creator_id,
        "visibility": t.visibility,
        "payload": json.loads(t.payload),
        "created_at": t.created_at,
    }


@router.delete(
    "/api/job-templates/{template_id}",
    status_code=204,
    response_class=Response,
    tags=["Job Templates"],
    summary="Delete a job template",
    description="Permanently delete a job template"
)
async def delete_job_template(
    template_id: str,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a job template. Restricted to creator or admin."""
    result = await db.execute(select(JobTemplate).where(JobTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Job template not found")
    if t.creator_id != current_user.username and current_user.role != "admin":
        raise HTTPException(403, "Only the template creator or an admin can delete this template")
    await db.delete(t)
    await db.commit()
