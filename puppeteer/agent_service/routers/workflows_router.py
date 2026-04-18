"""
Workflows domain router: workflow CRUD, execution runs, webhook management.

Endpoints:
- POST /api/workflows - Create a new workflow
- GET /api/workflows - List all workflows
- GET /api/workflows/{workflow_id} - Get a single workflow
- PUT /api/workflows/{workflow_id} - Update a workflow
- PATCH /api/workflows/{workflow_id} - Partially update a workflow
- DELETE /api/workflows/{workflow_id} - Delete a workflow
- POST /api/workflows/{workflow_id}/fork - Fork (clone) a workflow
- POST /api/workflows/validate - Validate a workflow definition
- POST /api/workflow-runs - Create a manual workflow run
- POST /api/workflows/{workflow_id}/webhooks - Create a webhook for a workflow
- GET /api/workflows/{workflow_id}/webhooks - List webhooks for a workflow
- DELETE /api/workflows/{workflow_id}/webhooks/{webhook_id} - Delete a webhook
- GET /api/workflows/{workflow_id}/runs - List workflow runs
- GET /api/workflows/{workflow_id}/runs/{run_id} - Get a specific workflow run
- POST /api/workflow-runs/{run_id}/cancel - Cancel a workflow run
- POST /api/webhooks/{webhook_id}/trigger - Trigger a workflow via webhook
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from typing import Optional, List, Dict
import logging
import uuid
import json
import secrets as _secrets
from datetime import datetime, timezone as tz
from cryptography.fernet import Fernet

from ..db import get_db, AsyncSession, User, Workflow, WorkflowRun, WorkflowWebhook
from ..deps import require_permission, audit
from ..models import (
    WorkflowCreate, WorkflowResponse, WorkflowUpdate,
    WorkflowRunResponse, WorkflowWebhookCreate, WorkflowWebhookResponse,
    WorkflowRunListResponse
)
from ..services.workflow_service import WorkflowService
from ..services.scheduler_service import scheduler_service
from ..security import cipher_suite

logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
UTC = tz.utc


def hash_webhook_secret(secret: str) -> str:
    """Hash webhook secret using bcrypt for storage."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(secret)


# --- WORKFLOW CRUD ENDPOINTS ---

@router.post("/api/workflows", tags=["workflows"], response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    workflow_create: WorkflowCreate,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Create a new Workflow with full-graph contract."""
    workflow_service = WorkflowService()
    return await workflow_service.create(db, workflow_create, current_user.username)


@router.get("/api/workflows", tags=["workflows"], response_model=list[WorkflowResponse])
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> list[WorkflowResponse]:
    """List all Workflows with metadata (step_count, last_run_status)."""
    workflow_service = WorkflowService()
    return await workflow_service.list(db, skip, limit)


@router.get("/api/workflows/{workflow_id}", tags=["workflows"], response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Get a single Workflow with full DAG (nested steps, edges, parameters)."""
    workflow_service = WorkflowService()
    return await workflow_service.get(db, workflow_id)


@router.put("/api/workflows/{workflow_id}", tags=["workflows"], response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Update a Workflow definition (atomic replace of steps/edges/parameters)."""
    workflow_service = WorkflowService()
    return await workflow_service.update(db, workflow_id, workflow_update)


@router.patch("/api/workflows/{workflow_id}", tags=["workflows"], response_model=WorkflowResponse)
async def patch_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """
    Partially update a Workflow definition with validation.

    Validates schedule_cron against required parameters (all must have defaults).
    Updates DAG if definition changes. Syncs APScheduler crons after save.

    Returns:
        200 OK with updated WorkflowResponse

    Raises:
        404: Workflow not found
        422: Validation failed (e.g., schedule_cron with required params lacking defaults)
    """
    # Fetch workflow
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # If schedule_cron is being set, validate that all required parameters have defaults
    if workflow_update.schedule_cron is not None:
        # Fetch parameters for this workflow
        from sqlalchemy.orm import selectinload
        stmt = select(Workflow).where(Workflow.id == workflow_id).options(
            selectinload(Workflow.parameters)
        )
        result = await db.execute(stmt)
        workflow_with_params = result.scalar_one_or_none()

        if workflow_with_params and workflow_with_params.parameters:
            for param in workflow_with_params.parameters:
                if param.default_value is None:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Cannot schedule workflow: required parameter '{param.name}' has no default value. All parameters must have defaults for cron scheduling."
                    )

    # Update fields
    if workflow_update.name is not None:
        workflow.name = workflow_update.name
    if workflow_update.definition is not None:
        workflow.definition = workflow_update.definition
        # Validate DAG if definition changed
        workflow_service = WorkflowService()
        await workflow_service.validate_workflow_definition(workflow)
    if workflow_update.schedule_cron is not None:
        workflow.schedule_cron = workflow_update.schedule_cron
    if workflow_update.is_paused is not None:
        workflow.is_paused = workflow_update.is_paused

    workflow.updated_at = datetime.now(UTC)
    audit(db, current_user, "workflow:update", workflow_id, {
        "name": workflow_update.name,
        "schedule_cron": workflow_update.schedule_cron,
        "is_paused": workflow_update.is_paused
    })
    await db.commit()

    # Sync crons with APScheduler if schedule_cron changed
    try:
        await scheduler_service.sync_workflow_crons()
    except Exception as e:
        logger.warning(f"Error syncing workflow crons: {e}")

    workflow_service = WorkflowService()
    return await workflow_service._workflow_to_response(db, workflow)


@router.delete("/api/workflows/{workflow_id}", tags=["workflows"], status_code=204)
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a Workflow (blocked if active WorkflowRuns exist)."""
    workflow_service = WorkflowService()
    await workflow_service.delete(db, workflow_id)


@router.post("/api/workflows/{workflow_id}/fork", tags=["workflows"], response_model=WorkflowResponse, status_code=201)
async def fork_workflow(
    workflow_id: str,
    fork_request: dict = Body({"new_name": "..."}),  # {"new_name": "cloned-workflow"}
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """
    Fork (Save-as-New) a Workflow: clone all steps/edges/parameters into a new Workflow,
    and pause the source workflow's cron schedule.
    """
    new_name = fork_request.get("new_name")
    if not new_name:
        raise HTTPException(status_code=422, detail="new_name is required")

    workflow_service = WorkflowService()
    return await workflow_service.fork(db, workflow_id, new_name, current_user.username)


@router.post("/api/workflows/validate", tags=["workflows"], response_model=dict)
async def validate_workflow(
    workflow_create: WorkflowCreate
) -> dict:
    """
    Validate a Workflow definition without saving (static check).
    Used by the DAG editor (Phase 151) on every canvas change.
    Returns {valid: true} or {valid: false, error: ..., cycle_path: ..., etc.}
    """
    steps_data = [s.model_dump() for s in workflow_create.steps]
    edges_data = [e.model_dump() for e in workflow_create.edges]

    # Generate temporary IDs for validation (like create() does)
    for i, step in enumerate(steps_data):
        if "id" not in step:
            step["id"] = f"temp_step_{i}"

    is_valid, error = WorkflowService.validate_dag(steps_data, edges_data)
    if is_valid:
        return {"valid": True}
    else:
        return {"valid": False, **error}


# --- WORKFLOW EXECUTION ENDPOINTS ---

@router.post("/api/workflow-runs", tags=["workflows"], response_model=WorkflowRunResponse, status_code=201)
async def create_workflow_run(
    body: dict,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger a WorkflowRun with optional parameter overrides.

    Request body: {
        "workflow_id": str,
        "parameters": {key: value} (optional)
    }

    Returns WorkflowRunResponse with initial step runs.

    Returns:
        201 Created with WorkflowRunResponse

    Raises:
        400: workflow_id missing
        404: Workflow not found
        409: Workflow is paused
        422: Required parameters unsatisfied
        500: Unexpected error
    """
    if not body.get("workflow_id"):
        raise HTTPException(status_code=400, detail="workflow_id required")

    workflow_service = WorkflowService()
    try:
        run = await workflow_service.start_run(
            workflow_id=body["workflow_id"],
            parameters=body.get("parameters", {}),
            trigger_type="MANUAL",
            triggered_by=current_user.username,
            db=db
        )

        # Audit log the manual trigger
        audit(db, current_user, "workflow:trigger_manual", run.id, {
            "workflow_id": body["workflow_id"],
            "run_id": run.id,
            "triggered_by": current_user.username
        })

        # Import ws_manager inside handler to avoid circular imports
        from ..main import ws_manager
        await ws_manager.broadcast("workflow:run:created", {"run_id": run.id, "workflow_id": run.workflow_id, "status": "RUNNING"})
        return run
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering workflow {body.get('workflow_id')}: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger workflow")


@router.get("/api/workflows/{workflow_id}/runs", tags=["workflows"], response_model=WorkflowRunListResponse)
async def get_workflow_runs(
    workflow_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_permission("workflows:read")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowRunListResponse:
    """Get paginated list of runs for a workflow (most recent first)."""
    # Verify workflow exists
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Count total runs
    count_stmt = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.workflow_id == workflow_id
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Fetch paginated runs (order by started_at DESC, most recent first)
    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id)
        .order_by(desc(WorkflowRun.started_at))
        .offset(skip)
        .limit(limit)
    )
    runs_result = await db.execute(stmt)
    runs = runs_result.scalars().all()

    # Convert to response models (with eager-loaded step runs)
    workflow_service = WorkflowService()
    run_responses = []
    for run in runs:
        run_response = await workflow_service._run_to_response(db, run)
        run_responses.append(run_response)

    return WorkflowRunListResponse(
        runs=run_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/api/workflows/{workflow_id}/runs/{run_id}", tags=["workflows"], response_model=WorkflowRunResponse)
async def get_workflow_run(
    workflow_id: str,
    run_id: str,
    current_user: User = Depends(require_permission("workflows:read")),
    db: AsyncSession = Depends(get_db),
) -> WorkflowRunResponse:
    """Get a single WorkflowRun with all step details."""
    run = await db.get(WorkflowRun, run_id)
    if run is None or run.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Run not found")
    workflow_service = WorkflowService()
    return await workflow_service._run_to_response(db, run)


@router.post("/api/workflow-runs/{run_id}/cancel", tags=["workflows"], response_model=WorkflowRunResponse)
async def cancel_workflow_run(
    run_id: str,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a running WorkflowRun.

    Blocks new step dispatches; running jobs continue to completion.
    """
    workflow_service = WorkflowService()
    run = await workflow_service.cancel_run(run_id, db)

    from ..main import ws_manager
    await ws_manager.broadcast("workflow:run:cancelled", {"run_id": run.id, "status": "CANCELLED"})
    return run


# --- WORKFLOW WEBHOOK ENDPOINTS ---

@router.post("/api/workflows/{workflow_id}/webhooks", tags=["workflows"], response_model=WorkflowWebhookResponse, status_code=201)
async def create_workflow_webhook(
    workflow_id: str,
    webhook_create: WorkflowWebhookCreate,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowWebhookResponse:
    """Create a webhook endpoint for a Workflow. Returns plaintext secret once at creation; never again."""
    # Verify workflow exists
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Generate webhook ID and plaintext secret
    webhook_id = str(uuid.uuid4())
    plaintext_secret = _secrets.token_urlsafe(32)  # ~256 bits of entropy

    # Hash secret for storage (bcrypt)
    secret_hash = hash_webhook_secret(plaintext_secret)

    # Encrypt plaintext secret for HMAC verification at trigger time (Fernet)
    secret_plaintext_encrypted = cipher_suite.encrypt(plaintext_secret.encode()).decode()

    # Create webhook in DB
    webhook = WorkflowWebhook(
        id=webhook_id,
        workflow_id=workflow_id,
        name=webhook_create.name,
        secret_hash=secret_hash,
        secret_plaintext=secret_plaintext_encrypted,  # Store encrypted plaintext for HMAC verification
        created_at=datetime.now(UTC)
    )
    db.add(webhook)
    await db.commit()

    # Audit log
    audit(db, current_user, "workflow:create_webhook", webhook_id, {
        "workflow_id": workflow_id,
        "webhook_name": webhook_create.name
    })

    # Return response with plaintext secret (only time it's exposed)
    response = WorkflowWebhookResponse(
        id=webhook_id,
        workflow_id=workflow_id,
        name=webhook_create.name,
        secret=plaintext_secret,  # ONLY in creation response
        created_at=webhook.created_at
    )
    return response


@router.get("/api/workflows/{workflow_id}/webhooks", tags=["workflows"], response_model=List[WorkflowWebhookResponse])
async def list_workflow_webhooks(
    workflow_id: str,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> List[WorkflowWebhookResponse]:
    """List all webhooks for a Workflow (secret field omitted for security)."""
    # Verify workflow exists
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Fetch all webhooks for this workflow
    stmt = select(WorkflowWebhook).where(WorkflowWebhook.workflow_id == workflow_id)
    result = await db.execute(stmt)
    webhooks = result.scalars().all()

    # Map to response (secret=None for all list responses)
    return [
        WorkflowWebhookResponse(
            id=w.id,
            workflow_id=w.workflow_id,
            name=w.name,
            secret=None,  # Never expose secret in list
            created_at=w.created_at
        )
        for w in webhooks
    ]


@router.delete("/api/workflows/{workflow_id}/webhooks/{webhook_id}", tags=["workflows"], status_code=204)
async def delete_workflow_webhook(
    workflow_id: str,
    webhook_id: str,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Revoke a webhook endpoint. Future trigger requests will fail with 404."""
    # Verify webhook exists and belongs to this workflow
    webhook = await db.get(WorkflowWebhook, webhook_id)
    if webhook is None or webhook.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Delete webhook
    await db.delete(webhook)
    await db.commit()

    # Audit log
    audit(db, current_user, "workflow:delete_webhook", webhook_id, {
        "workflow_id": workflow_id
    })


@router.post("/api/webhooks/{webhook_id}/trigger", tags=["webhooks"], status_code=202)
async def trigger_webhook(
    webhook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Unauthenticated webhook trigger endpoint. Validates HMAC signature before running workflow.

    Request body: JSON object with parameter overrides (e.g., {"env": "prod", "region": "us-east-1"})

    Header: X-Hub-Signature-256: sha256=<hex> (HMAC-SHA256 of raw request body)

    Returns:
        202 Accepted with {"run_id": "<workflow_run_id>"}

    Raises:
        400: Invalid request body
        401: Missing or invalid signature
        404: Webhook not found
        500: Failed to trigger workflow
    """
    # Read raw request body (required for HMAC verification)
    try:
        body_bytes = await request.body()
    except Exception as e:
        logger.error(f"Error reading webhook body: {e}")
        raise HTTPException(status_code=400, detail="Invalid request body")

    # Extract signature header
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header:
        logger.warning(f"Webhook {webhook_id} missing X-Hub-Signature-256 header")
        raise HTTPException(status_code=401, detail="Missing signature header")

    # Fetch webhook
    webhook = await db.get(WorkflowWebhook, webhook_id)
    if webhook is None:
        # Log but don't expose webhook existence
        logger.warning(f"Webhook trigger attempt for unknown webhook {webhook_id}")
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Get plaintext secret from webhook for verification
    # The secret_plaintext is stored Fernet-encrypted; decrypt it for HMAC verification
    if webhook.secret_plaintext is None:
        logger.error(f"Webhook {webhook_id} has no plaintext secret stored")
        raise HTTPException(status_code=500, detail="Webhook misconfiguration")

    try:
        plaintext_secret = cipher_suite.decrypt(webhook.secret_plaintext.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt webhook secret for {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Webhook misconfiguration")

    # Verify HMAC signature
    import hmac
    import hashlib
    expected_signature = hmac.new(
        plaintext_secret.encode(),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    # Parse signature header (format: sha256=<hex>)
    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Invalid signature format")

    provided_signature = signature_header[7:]  # Strip "sha256=" prefix

    if not hmac.compare_digest(provided_signature, expected_signature):
        logger.warning(f"Webhook {webhook_id} failed HMAC verification")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse request body as JSON
    try:
        body_dict = json.loads(body_bytes.decode())
    except Exception as e:
        logger.error(f"Error parsing webhook body as JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")

    # Trigger workflow run
    try:
        workflow_service = WorkflowService()
        run = await workflow_service.start_run(
            workflow_id=webhook.workflow_id,
            parameters=body_dict.get("parameters", {}),
            trigger_type="WEBHOOK",
            triggered_by=f"webhook:{webhook_id}",
            db=db
        )

        # Audit log (no current_user for webhooks)
        logger.info(f"Webhook {webhook_id} triggered workflow run {run.id}")

        from ..main import ws_manager
        await ws_manager.broadcast("workflow:run:created", {"run_id": run.id, "workflow_id": run.workflow_id, "status": "RUNNING"})

        return {"run_id": run.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering workflow via webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger workflow")
