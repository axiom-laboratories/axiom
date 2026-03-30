"""EE Router: Execution History — list, get, attestation, pin/unpin, CSV export."""
from __future__ import annotations

import csv
import io
import json
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.future import select
from sqlalchemy import desc

from ...db import get_db, AsyncSession, ExecutionRecord, Job, NodeStats, User, JobDefinitionVersion
from ...deps import require_auth, require_permission, audit
from ...models import ExecutionRecordResponse, AttestationExportResponse

executions_router = APIRouter()

EXEC_CSV_HEADERS = ["job_guid", "node_id", "status", "exit_code",
                    "started_at", "completed_at", "duration_s", "attempt_number", "pinned"]


@executions_router.get("/api/executions", response_model=List[ExecutionRecordResponse], tags=["Execution Records"])
async def list_executions(
    skip: int = 0,
    limit: int = 50,
    node_id: Optional[str] = None,
    status: Optional[str] = None,
    job_guid: Optional[str] = None,
    scheduled_job_id: Optional[str] = None,
    job_run_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List execution history with filtering and pagination."""
    query = select(ExecutionRecord, Job.max_retries, Job.definition_version_id, Job.runtime).outerjoin(Job, Job.guid == ExecutionRecord.job_guid)
    if node_id:
        query = query.where(ExecutionRecord.node_id == node_id)
    if status:
        query = query.where(ExecutionRecord.status == status)
    if job_guid:
        query = query.where(ExecutionRecord.job_guid == job_guid)
    if scheduled_job_id:
        subq = select(Job.guid).where(Job.scheduled_job_id == scheduled_job_id)
        query = query.where(ExecutionRecord.job_guid.in_(subq))
    if job_run_id:
        query = query.where(ExecutionRecord.job_run_id == job_run_id)

    query = query.order_by(desc(ExecutionRecord.started_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    # Batch-fetch version numbers for all non-null definition_version_ids (avoids N+1)
    all_version_ids = [row[2] for row in rows if row[2] is not None]
    version_number_map: dict = {}
    if all_version_ids:
        ver_result = await db.execute(
            select(JobDefinitionVersion.id, JobDefinitionVersion.version_number)
            .where(JobDefinitionVersion.id.in_(all_version_ids))
        )
        version_number_map = {vid: vnum for vid, vnum in ver_result.all()}

    responses = []
    for r, job_max_retries, job_definition_version_id, job_runtime in rows:
        duration = None
        if r.started_at and r.completed_at:
            duration = (r.completed_at - r.started_at).total_seconds()

        log = []
        if r.output_log:
            try:
                log = json.loads(r.output_log)
            except:
                log = [{"t": str(r.started_at), "stream": "stderr", "line": "Failed to parse log JSON"}]

        responses.append(ExecutionRecordResponse(
            id=r.id,
            job_guid=r.job_guid,
            node_id=r.node_id,
            status=r.status,
            exit_code=r.exit_code,
            started_at=r.started_at,
            completed_at=r.completed_at,
            output_log=log,
            truncated=r.truncated,
            duration_seconds=duration,
            stdout=r.stdout,
            stderr=r.stderr,
            script_hash=r.script_hash,
            hash_mismatch=r.hash_mismatch,
            attempt_number=r.attempt_number,
            job_run_id=r.job_run_id,
            attestation_verified=r.attestation_verified,
            max_retries=job_max_retries,
            definition_version_id=job_definition_version_id,
            definition_version_number=version_number_map.get(job_definition_version_id) if job_definition_version_id else None,
            runtime=job_runtime,
        ))
    return responses


@executions_router.get("/api/executions/{id}", response_model=ExecutionRecordResponse, tags=["Execution Records"])
async def get_execution(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get details for a single execution record."""
    result = await db.execute(select(ExecutionRecord).where(ExecutionRecord.id == id))
    r = result.scalar_one_or_none()
    if not r:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Execution not found")

    duration = None
    if r.started_at and r.completed_at:
        duration = (r.completed_at - r.started_at).total_seconds()

    log = []
    if r.output_log:
        try:
            log = json.loads(r.output_log)
        except:
            log = [{"t": str(r.started_at), "stream": "stderr", "line": "Failed to parse log JSON"}]

    return ExecutionRecordResponse(
        id=r.id,
        job_guid=r.job_guid,
        node_id=r.node_id,
        status=r.status,
        exit_code=r.exit_code,
        started_at=r.started_at,
        completed_at=r.completed_at,
        output_log=log,
        truncated=r.truncated,
        duration_seconds=duration,
        stdout=r.stdout,
        stderr=r.stderr,
        script_hash=r.script_hash,
        hash_mismatch=r.hash_mismatch,
        attempt_number=r.attempt_number,
        job_run_id=r.job_run_id,
        attestation_verified=r.attestation_verified,
    )


@executions_router.get("/api/executions/{id}/attestation", response_model=AttestationExportResponse,
                       tags=["Execution Records"])
async def get_execution_attestation(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Export attestation bundle and verification result for an execution record.

    Returns 404 if the execution record does not exist or has no attestation data.
    """
    from fastapi import HTTPException
    result = await db.execute(select(ExecutionRecord).where(ExecutionRecord.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Execution record not found")
    if not record.attestation_bundle:
        raise HTTPException(status_code=404, detail="No attestation for this execution")

    # Extract cert_serial from bundle bytes if possible
    cert_serial = None
    try:
        import json as _json
        import base64 as _b64
        bundle_data = _json.loads(_b64.b64decode(record.attestation_bundle))
        cert_serial = bundle_data.get("cert_serial")
    except Exception:
        pass

    return AttestationExportResponse(
        bundle_b64=record.attestation_bundle,
        signature_b64=record.attestation_signature or "",
        cert_serial=cert_serial,
        node_id=record.node_id,
        attestation_verified=record.attestation_verified,
    )


@executions_router.get("/jobs/{guid}/executions", tags=["Jobs"])
async def list_job_executions(
    guid: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    # Fetch the job to get node_id and started_at for health snapshot
    job_result = await db.execute(select(Job).where(Job.guid == guid))
    job_obj = job_result.scalar_one_or_none()

    result = await db.execute(
        select(ExecutionRecord, Job.max_retries)
        .outerjoin(Job, Job.guid == ExecutionRecord.job_guid)
        .where(ExecutionRecord.job_guid == guid)
        .order_by(ExecutionRecord.id.desc())
    )
    rows = result.all()
    records = [
        {
            "id": r.id,
            "job_guid": r.job_guid,
            "node_id": r.node_id,
            "status": r.status,
            "exit_code": r.exit_code,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "output_log": json.loads(r.output_log) if r.output_log else [],
            "truncated": r.truncated,
            "duration_seconds": (
                (r.completed_at - r.started_at).total_seconds()
                if r.started_at and r.completed_at else None
            ),
            "stdout": r.stdout,
            "stderr": r.stderr,
            "attempt_number": r.attempt_number,
            "job_run_id": r.job_run_id,
            "attestation_verified": r.attestation_verified,
            "max_retries": job_max_retries,
        }
        for r, job_max_retries in rows
    ]

    # Query NodeStats for the execution-time health snapshot
    node_health = None
    if job_obj and job_obj.node_id and job_obj.started_at:
        nh_result = await db.execute(
            select(NodeStats)
            .where(NodeStats.node_id == job_obj.node_id)
            .where(NodeStats.recorded_at <= job_obj.started_at)
            .order_by(desc(NodeStats.recorded_at))
            .limit(1)
        )
        nh = nh_result.scalar_one_or_none()
        if nh:
            node_health = {
                "cpu": nh.cpu,
                "ram": nh.ram,
                "recorded_at": nh.recorded_at.isoformat(),
            }

    return {
        "records": records,
        "node_health_at_execution": node_health,
    }


@executions_router.patch("/api/executions/{exec_id}/pin", tags=["Execution Records"])
async def pin_execution(
    exec_id: int,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Pin an execution record to protect it from retention pruning."""
    from fastapi import HTTPException
    result = await db.execute(select(ExecutionRecord).where(ExecutionRecord.id == exec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Execution record not found")
    rec.pinned = True
    audit(db, current_user.username, "execution:pin", str(exec_id), {"exec_id": exec_id})
    await db.commit()
    return {"id": exec_id, "pinned": True}


@executions_router.patch("/api/executions/{exec_id}/unpin", tags=["Execution Records"])
async def unpin_execution(
    exec_id: int,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Unpin an execution record, making it eligible for retention pruning."""
    from fastapi import HTTPException
    result = await db.execute(select(ExecutionRecord).where(ExecutionRecord.id == exec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Execution record not found")
    rec.pinned = False
    audit(db, current_user.username, "execution:unpin", str(exec_id), {"exec_id": exec_id})
    await db.commit()
    return {"id": exec_id, "pinned": False}


@executions_router.get("/api/jobs/{guid}/executions/export", tags=["Execution Records"])
async def export_job_executions(
    guid: str,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    """Stream a CSV of all execution records for a specific job."""
    result = await db.execute(
        select(ExecutionRecord)
        .where(ExecutionRecord.job_guid == guid)
        .order_by(ExecutionRecord.started_at)
    )
    records = result.scalars().all()

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(EXEC_CSV_HEADERS)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()
        for rec in records:
            duration = (
                (rec.completed_at - rec.started_at).total_seconds()
                if rec.started_at and rec.completed_at
                else None
            )
            writer.writerow([
                rec.job_guid, rec.node_id, rec.status, rec.exit_code,
                rec.started_at, rec.completed_at, duration,
                rec.attempt_number, rec.pinned,
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=executions-{guid}.csv"},
    )
