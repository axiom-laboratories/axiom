"""
Nodes domain router: node CRUD, enrollment, agent heartbeat, drain/revoke.

Endpoints:
- POST /work/pull - Agent polls for assigned jobs (unauthenticated, uses mTLS)
- POST /heartbeat - Agent reports heartbeat and health stats (unauthenticated, uses mTLS)
- POST /work/{guid}/result - Agent reports job execution result (unauthenticated)
- POST /api/enroll - Node enrollment with JOIN_TOKEN (unauthenticated)
- GET /nodes - List all nodes with pagination
- GET /nodes/{node_id}/detail - Get node details
- PATCH /nodes/{node_id} - Update node metadata (tags, env_tag)
- DELETE /nodes/{node_id} - Delete a node
- POST /nodes/{node_id}/revoke - Revoke node certificates
- PATCH /nodes/{node_id}/drain - Stop assigning new jobs
- PATCH /nodes/{node_id}/undrain - Resume accepting jobs
- POST /api/nodes/{node_id}/clear-tamper - Clear tamper flag
- POST /nodes/{node_id}/reinstate - Reinstate a revoked node
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, func, desc
from typing import Optional, List
from datetime import datetime
import logging
import json
from collections import defaultdict
from cryptography import x509 as _x509

from ..db import get_db, AsyncSession, User, Node, NodeStats, Ping, RevokedCert, Job, Token, WorkflowStepRun
from ..deps import require_auth, require_permission, audit
from ..models import (
    NodeResponse, PollResponse, NodeUpdateRequest, ActionResponse, PaginatedResponse,
    HeartbeatPayload, ResultReport, RegisterResponse, EnrollmentRequest,
    EnrollmentTokenResponse, EnrollmentTokenCreate, WorkflowStepUpdatedEvent
)
from ..services.job_service import JobService
from ..services.pki_service import pki_service
from ..security import verify_client_cert, verify_node_secret, mask_pii

logger = logging.getLogger(__name__)
router = APIRouter()


# --- UNAUTHENTICATED AGENT ENDPOINTS (use mTLS or node secrets) ---

@router.post("/work/pull", response_model=PollResponse, tags=["Node Agent"])
async def pull_work(request: Request, node_id: str = Depends(verify_node_secret), _: str = Depends(verify_client_cert), db: AsyncSession = Depends(get_db)):
    """Agent polls for assigned jobs. Uses mTLS client cert and node secret."""
    # LIC-04: DEGRADED_CE — return empty work, nodes stay enrolled and heartbeating
    _ls = getattr(request.app.state, "licence_state", None)
    if _ls and _ls.status == "EXPIRED":
        from ..models import WorkConfig
        return PollResponse(job=None, config=WorkConfig())

    node_ip = request.client.host
    r = await db.execute(select(Node).where(Node.node_id == node_id))
    n = r.scalar_one_or_none()
    if n and n.status == "REVOKED":
        raise HTTPException(status_code=403, detail="Node is revoked")
    return await JobService.pull_work(node_id, node_ip, db)


@router.post(
    "/heartbeat",
    response_model=dict,
    tags=["Node Agent"],
    summary="Receive node heartbeat",
    description="Process heartbeat from node agent with health status, resource stats, and system metrics"
)
async def receive_heartbeat(req: Request, hb: HeartbeatPayload, node_id: str = Depends(verify_node_secret), _: str = Depends(verify_client_cert), db: AsyncSession = Depends(get_db)):
    """Agent reports heartbeat and health stats. Uses mTLS client cert and node secret."""
    node_ip = req.client.host
    result = await JobService.receive_heartbeat(node_id, node_ip, hb, db)
    # Import ws_manager inside handler to avoid circular imports
    from ..main import ws_manager
    await ws_manager.broadcast("node:heartbeat", {"node_id": node_id, "status": "ONLINE", "stats": hb.stats})
    return result


@router.post(
    "/work/{guid}/result",
    response_model=dict,
    tags=["Node Agent"],
    summary="Report job execution result",
    description="Node agent reports job completion status, output, and execution metrics"
)
async def report_result(guid: str, report: ResultReport, req: Request, node_id: str = Depends(verify_node_secret), db: AsyncSession = Depends(get_db)):
    """Agent reports job execution result. Uses mTLS client cert and node secret."""
    node_ip = req.client.host
    if report.result:
        report.result = mask_pii(report.result)

    updated = await JobService.report_result(guid, report, node_ip, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")

    # Phase 147: If job is linked to a workflow step, advance the workflow
    job = await db.get(Job, guid)
    if job and job.workflow_step_run_id:
        # Extract run_id from workflow_step_run_id by querying the step run
        step_run = await db.get(WorkflowStepRun, job.workflow_step_run_id)
        if step_run:
            from ..services.workflow_service import WorkflowService
            workflow_service = WorkflowService()
            # NEW: Store result_json for IF gate evaluation
            if report.result:
                await workflow_service.store_step_result(step_run.id, report.result, db)

            # Phase 150: Update step_run status based on job completion
            old_step_status = step_run.status
            if updated.get("status") == "COMPLETED":
                step_run.status = "COMPLETED"
                step_run.completed_at = datetime.utcnow()
            elif updated.get("status") in ["FAILED", "DEAD_LETTER", "SECURITY_REJECTED"]:
                step_run.status = "FAILED"
                step_run.completed_at = datetime.utcnow()

            # Emit workflow_step_updated event if status changed
            if old_step_status != step_run.status:
                try:
                    event = WorkflowStepUpdatedEvent(
                        id=step_run.id,
                        workflow_run_id=step_run.workflow_run_id,
                        workflow_step_id=step_run.workflow_step_id,
                        status=step_run.status,
                        started_at=step_run.started_at,
                        completed_at=step_run.completed_at,
                        job_guid=guid
                    )
                    from ..main import ws_manager
                    await ws_manager.broadcast_workflow_step_updated(event)
                except Exception as e:
                    logger.error(f"Failed to broadcast workflow_step_updated event: {e}")

            await workflow_service.advance_workflow(step_run.workflow_run_id, db)

    from ..main import ws_manager
    await ws_manager.broadcast("job:updated", {"guid": guid, "status": updated.get("status", "COMPLETED")})
    return updated


@router.post("/api/enroll", response_model=RegisterResponse, tags=["Node Agent"])
async def enroll_node(req: EnrollmentRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Public endpoint for secure node enrollment using a one-time token."""
    # LIC-07: Node limit enforcement (checked before token validation to return correct status code)
    _ls = getattr(request.app.state, "licence_state", None)
    _node_limit = _ls.node_limit if _ls else 0
    if _node_limit > 0:
        from sqlalchemy import text as _sql_text
        _count_result = await db.execute(
            _sql_text("SELECT count(*) FROM nodes WHERE status NOT IN ('OFFLINE', 'REVOKED')")
        )
        _active_count = _count_result.scalar() or 0
        if _active_count >= _node_limit:
            raise HTTPException(
                status_code=402,
                detail="Node limit reached — upgrade your licence at axiom.sh/renew"
            )

    # 1. Verify Token
    result = await db.execute(select(Token).where(Token.token == req.token, Token.used == False))
    token_entry = result.scalar_one_or_none()

    if not token_entry:
         raise HTTPException(status_code=403, detail="Invalid or Expired Enrollment Token")

    # 2. Invalidate Token immediately
    token_entry.used = True

    try:
        # 3. Sign CSR
        signed_cert = pki_service.sign_csr(req.csr_pem, req.hostname)

        # 4. Create or Update Node with the secret binding
        node_id = req.hostname # Or derived from CSR/Certificate
        node_ip = request.client.host

        result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = result.scalar_one_or_none()

        if node:
            if node.status == "REVOKED":
                raise HTTPException(status_code=403, detail="Node has been revoked and cannot re-enroll")
            node.node_secret_hash = req.node_secret_hash
            node.machine_id = req.machine_id
            node.ip = node_ip
            node.last_seen = datetime.utcnow()
            node.client_cert_pem = signed_cert
            node.template_id = token_entry.template_id
        else:
            node = Node(
                node_id=node_id,
                hostname=req.hostname,
                ip=node_ip,
                status="ONLINE",
                template_id=token_entry.template_id,
                machine_id=req.machine_id,
                node_secret_hash=req.node_secret_hash,
                client_cert_pem=signed_cert,
            )
            db.add(node)
        await db.commit()

        return {
            "client_cert_pem": signed_cert,
            "ca_url": f"{request.base_url}"
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Enrollment Error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {str(e)}")


# --- AUTHENTICATED NODE MANAGEMENT ENDPOINTS ---

@router.get("/nodes", tags=["Nodes"], response_model=PaginatedResponse[NodeResponse], summary="List all nodes", description="Retrieve paginated list of nodes with online/offline status and capability info")
async def list_nodes(
    page: int = 1,
    page_size: int = 25,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List all nodes with pagination and statistics."""
    # Step 1: total count
    total_result = await db.execute(select(func.count()).select_from(Node))
    total = total_result.scalar() or 0

    # Step 2: paginated node list (paginate BEFORE stats batch query)
    result = await db.execute(
        select(Node).order_by(Node.hostname)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    nodes = result.scalars().all()

    # Step 3: batch stats history — scoped to this page's node_ids only
    history_map: dict = defaultdict(list)
    if nodes:
        page_node_ids = [n.node_id for n in nodes]
        hist_result = await db.execute(
            select(NodeStats)
            .where(NodeStats.node_id.in_(page_node_ids))
            .order_by(desc(NodeStats.recorded_at))
        )
        for stat in hist_result.scalars().all():
            bucket = history_map[stat.node_id]
            if len(bucket) < 20:
                bucket.append({"t": stat.recorded_at.isoformat(), "cpu": stat.cpu, "ram": stat.ram})
        # Reverse each bucket so oldest→newest (chronological for charts)
        for k in history_map:
            history_map[k].reverse()

    # Step 4: build resp list
    resp = []
    for n in nodes:
        if n.status in ("REVOKED", "TAMPERED", "DRAINING"):
            node_status = n.status
        else:
            is_offline = (datetime.utcnow() - n.last_seen).total_seconds() > 60
            node_status = "OFFLINE" if is_offline else "ONLINE"

        stats = json.loads(n.stats) if n.stats else None
        reported_tags = json.loads(n.tags) if n.tags else []
        op_tags = json.loads(n.operator_tags) if n.operator_tags else None
        effective_tags = op_tags if op_tags is not None else reported_tags

        resp.append({
            "node_id": n.node_id,
            "hostname": n.hostname,
            "ip": n.ip,
            "last_seen": n.last_seen,
            "status": node_status,
            "base_os_family": n.base_os_family,
            "stats": stats,
            "tags": effective_tags,
            "is_operator_managed": op_tags is not None,
            "capabilities": json.loads(n.capabilities) if n.capabilities else None,
            "stats_history": history_map.get(n.node_id, []),
            "env_tag": n.env_tag,
            "detected_cgroup_version": n.detected_cgroup_version,
            "execution_mode": n.execution_mode,  # Phase 124
        })

    return {
        "items": resp,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/nodes/{node_id}/detail", tags=["Nodes"], response_model=NodeResponse, summary="Get node details", description="Retrieve full details of a specific node")
async def get_node_detail(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Get details of a specific node."""
    detail = await JobService.get_node_detail(node_id, db)
    if detail is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return detail


@router.patch("/nodes/{node_id}", tags=["Nodes"], response_model=ActionResponse, summary="Update node metadata", description="Update node tags and environment tag")
async def update_node_config(node_id: str, config: NodeUpdateRequest, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Update node metadata (tags, env_tag)."""
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if config.tags is not None:
        node.operator_tags = json.dumps(config.tags)
    if config.env_tag is not None:
        node.env_tag = config.env_tag if config.env_tag != "" else None
        node.operator_env_tag = True  # Stays True even when cleared — distinguishes "never touched" from "explicitly cleared"

    audit(db, current_user, "node:update", node_id)
    await db.commit()
    return {
        "status": "updated",
        "resource_type": "node",
        "resource_id": node_id,
    }


@router.delete(
    "/nodes/{node_id}",
    status_code=204,
    response_class=Response,
    tags=["Nodes"],
    summary="Delete a node",
    description="Permanently delete a node and its associated metadata"
)
async def delete_node(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Delete a node and its associated data."""
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    await db.execute(delete(NodeStats).where(NodeStats.node_id == node_id))
    await db.execute(delete(Ping).where(Ping.node_id == node_id))
    audit(db, current_user, "node:delete", node_id)
    await db.delete(node)
    await db.commit()
    return Response(status_code=204)


@router.post("/nodes/{node_id}/revoke", tags=["Nodes"], response_model=ActionResponse, summary="Revoke node certificates", description="Prevent a node from accepting further work and block its enrollment")
async def revoke_node(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Revoke a node's certificates and prevent further work."""
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status == "REVOKED":
        raise HTTPException(status_code=409, detail="Node is already revoked")
    node.status = "REVOKED"
    if node.client_cert_pem:
        try:
            parsed = _x509.load_pem_x509_certificate(node.client_cert_pem.encode())
            db.add(RevokedCert(serial_number=str(parsed.serial_number), node_id=node_id))
        except Exception:
            pass
    audit(db, current_user, "node:revoke", node_id)
    await db.commit()
    return {"status": "revoked", "resource_type": "node", "resource_id": node_id}


@router.patch("/nodes/{node_id}/drain", response_model=ActionResponse, summary="Drain node workload", description="Stop assigning new jobs while completing existing jobs", tags=["Nodes"])
async def drain_node(node_id: str, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    """Stop assigning new jobs to a node, allowing existing jobs to complete."""
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status not in ("ONLINE", "BUSY"):
        raise HTTPException(status_code=409, detail=f"Cannot drain node in {node.status} state")
    node.status = "DRAINING"
    audit(db, current_user, "node:drain", node_id)
    await db.commit()
    from ..main import ws_manager
    await ws_manager.broadcast("node:updated", {"node_id": node_id, "status": "DRAINING"})
    return {"status": "enabled", "resource_type": "node", "resource_id": node_id, "message": "Draining jobs"}


@router.patch("/nodes/{node_id}/undrain", response_model=ActionResponse, summary="Resume assigning jobs to drained node", description="Re-enable job assignment on a previously drained node", tags=["Nodes"])
async def undrain_node(node_id: str, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    """Resume assigning jobs to a node after draining."""
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status != "DRAINING":
        raise HTTPException(status_code=409, detail="Node is not in DRAINING state")
    node.status = "ONLINE"
    audit(db, current_user, "node:undrain", node_id)
    await db.commit()
    from ..main import ws_manager
    await ws_manager.broadcast("node:updated", {"node_id": node_id, "status": "ONLINE"})
    return {"status": "enabled", "resource_type": "node", "resource_id": node_id, "message": "Node accepting jobs"}


@router.post("/api/nodes/{node_id}/clear-tamper", response_model=ActionResponse, summary="Clear tamper flag", description="Reset a node from TAMPERED to ONLINE after forensic review", tags=["Nodes"])
async def clear_node_tamper(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Clear tamper flag from a node after forensic review."""
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node.status != "TAMPERED":
        raise HTTPException(status_code=409, detail="Node is not in tampered state")

    node.status = "ONLINE"
    node.tamper_details = None
    await db.commit()

    audit(db, current_user, "node:clear_tamper", node_id)
    return {"status": "approved", "resource_type": "node", "resource_id": node_id}


@router.post("/nodes/{node_id}/reinstate", response_model=ActionResponse, summary="Reinstate a revoked node", description="Transition a REVOKED node back to OFFLINE status for re-enrollment", tags=["Nodes"])
async def reinstate_node(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Reinstate a revoked node for re-enrollment."""
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status != "REVOKED":
        raise HTTPException(status_code=409, detail="Node is not revoked")
    node.status = "OFFLINE"
    audit(db, current_user, "node:reinstate", node_id)
    await db.commit()
    return {"status": "approved", "resource_type": "node", "resource_id": node_id}
