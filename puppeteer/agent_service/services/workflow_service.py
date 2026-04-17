import json
import logging
from typing import Optional, List, Tuple, Dict, Any
from uuid import uuid4
from datetime import datetime

import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

logger = logging.getLogger(__name__)

from agent_service.db import (
    Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter,
    ScheduledJob, WorkflowRun, WorkflowStepRun, Job
)
from agent_service.models import (
    WorkflowCreate, WorkflowResponse, WorkflowUpdate, WorkflowValidationError,
    WorkflowStepResponse, WorkflowEdgeResponse, WorkflowParameterResponse,
    WorkflowRunResponse, WorkflowStepRunResponse, JobCreate,
    WorkflowRunUpdatedEvent, WorkflowStepUpdatedEvent
)


class WorkflowService:
    """CRUD and validation service for Workflow definitions."""

    @staticmethod
    def validate_dag(
        steps: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        max_depth: int = 30
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate DAG: cycle detection, referential integrity, depth limit.
        Returns (is_valid, error_dict).
        """
        # Build graph
        G = nx.DiGraph()
        step_ids = set()
        for step in steps:
            G.add_node(step["id"])
            step_ids.add(step["id"])

        # Check referential integrity and add edges
        for edge in edges:
            if edge["from_step_id"] not in step_ids or edge["to_step_id"] not in step_ids:
                return False, {
                    "error": "INVALID_EDGE_REFERENCE",
                    "edge": {"from_step_id": edge["from_step_id"], "to_step_id": edge["to_step_id"]}
                }
            G.add_edge(edge["from_step_id"], edge["to_step_id"])

        # Check acyclicity
        if not nx.is_directed_acyclic_graph(G):
            try:
                cycle = next(nx.simple_cycles(G))
                return False, {
                    "error": "CYCLE_DETECTED",
                    "cycle_path": cycle
                }
            except StopIteration:
                return False, {"error": "CYCLE_DETECTED", "cycle_path": []}

        # Check depth
        depth = WorkflowService.calculate_max_depth(G)
        if depth > max_depth:
            return False, {
                "error": "DEPTH_LIMIT_EXCEEDED",
                "max_depth": max_depth,
                "actual_depth": depth
            }

        return True, None

    @staticmethod
    def calculate_max_depth(G: nx.DiGraph) -> int:
        """Calculate longest path in DAG (number of edges)."""
        if len(G) == 0:
            return 0
        longest_path = nx.dag_longest_path(G)
        return len(longest_path) - 1 if longest_path else 0

    async def create(
        self, db: AsyncSession, workflow_create: WorkflowCreate, current_user_id: str
    ) -> WorkflowResponse:
        """Create a new Workflow with full validation."""
        # Convert Pydantic to dicts for validation
        steps_data = [s.model_dump() for s in workflow_create.steps]
        edges_data = [e.model_dump() for e in workflow_create.edges]

        # Generate temporary IDs for validation (they will be replaced with DB IDs)
        for i, step in enumerate(steps_data):
            if "id" not in step:
                step["id"] = f"temp_step_{i}"

        # Validate DAG
        is_valid, error = self.validate_dag(steps_data, edges_data)
        if not is_valid:
            raise HTTPException(status_code=422, detail=error)

        # Validate SIGNAL_WAIT gate nodes
        for step_data in steps_data:
            if step_data.get('node_type') == 'SIGNAL_WAIT':
                config = step_data.get('config_json', {})
                if isinstance(config, str):
                    try:
                        config = json.loads(config)
                    except json.JSONDecodeError:
                        raise HTTPException(status_code=422, detail=f"Step {step_data['id']}: SIGNAL_WAIT config_json is not valid JSON")
                
                signal_name = config.get('signal_name')
                if not signal_name or not isinstance(signal_name, str):
                    raise HTTPException(status_code=422, detail=f"Step {step_data['id']}: SIGNAL_WAIT requires config_json with 'signal_name' (string)")
                
                if ' ' in signal_name or len(signal_name) > 255:
                    raise HTTPException(status_code=422, detail=f"Step {step_data['id']}: signal_name must be non-empty, <255 chars, no whitespace")


        # Create Workflow
        workflow_id = str(uuid4())
        workflow = Workflow(
            id=workflow_id,
            name=workflow_create.name,
            created_by=current_user_id,
            is_paused=False
        )
        db.add(workflow)

        # Create WorkflowSteps
        step_id_map = {}  # Map from submitted step["id"] to DB step object
        for i, step_data in enumerate(steps_data):
            step_db_id = str(uuid4())
            step_id_map[step_data["id"]] = step_db_id
            step = WorkflowStep(
                id=step_db_id,
                workflow_id=workflow_id,
                scheduled_job_id=step_data["scheduled_job_id"],
                node_type=step_data["node_type"],
                config_json=step_data.get("config_json")
            )
            db.add(step)

        # Create WorkflowEdges (using remapped IDs)
        for edge_data in edges_data:
            edge = WorkflowEdge(
                id=str(uuid4()),
                workflow_id=workflow_id,
                from_step_id=step_id_map[edge_data["from_step_id"]],
                to_step_id=step_id_map[edge_data["to_step_id"]],
                branch_name=edge_data.get("branch_name")
            )
            db.add(edge)

        # Create WorkflowParameters
        for param_data in workflow_create.parameters:
            param = WorkflowParameter(
                id=str(uuid4()),
                workflow_id=workflow_id,
                name=param_data.name,
                type=param_data.type,
                default_value=param_data.default_value
            )
            db.add(param)

        await db.commit()
        await db.refresh(workflow)
        return await self.get(db, workflow_id)

    async def list(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[WorkflowResponse]:
        """List all Workflows with metadata (no full graph)."""
        stmt = select(Workflow).options(
            selectinload(Workflow.steps),
            selectinload(Workflow.edges),
            selectinload(Workflow.parameters)
        ).offset(skip).limit(limit)
        result = await db.execute(stmt)
        workflows = result.scalars().all()

        responses = []
        for w in workflows:
            responses.append(await self._to_response(db, w, include_graph=False))
        return responses

    async def get(self, db: AsyncSession, workflow_id: str) -> WorkflowResponse:
        """Get a single Workflow by ID with full graph."""
        stmt = select(Workflow).where(Workflow.id == workflow_id).options(
            selectinload(Workflow.steps),
            selectinload(Workflow.edges),
            selectinload(Workflow.parameters)
        )
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return await self._to_response(db, workflow)

    async def update(
        self, db: AsyncSession, workflow_id: str, update: WorkflowUpdate
    ) -> WorkflowResponse:
        """Update a Workflow (atomic delete/insert of steps/edges/parameters)."""
        stmt = select(Workflow).where(Workflow.id == workflow_id).options(
            selectinload(Workflow.steps),
            selectinload(Workflow.edges),
            selectinload(Workflow.parameters)
        )
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Prepare update data
        steps_data = [s.model_dump() for s in update.steps] if update.steps else []
        edges_data = [e.model_dump() for e in update.edges] if update.edges else []
        params_data = update.parameters if update.parameters else []

        # Generate temporary IDs for validation
        for i, step in enumerate(steps_data):
            if "id" not in step:
                step["id"] = f"temp_step_{i}"

        # Validate DAG
        is_valid, error = self.validate_dag(steps_data, edges_data)
        if not is_valid:
            raise HTTPException(status_code=422, detail=error)

        # Atomic delete/insert
        async with db.begin_nested():
            # Delete existing
            await db.execute(delete(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow_id))
            await db.execute(delete(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id))
            await db.execute(delete(WorkflowParameter).where(WorkflowParameter.workflow_id == workflow_id))

            # Insert new
            step_id_map = {}
            for step_data in steps_data:
                step_db_id = str(uuid4())
                step_id_map[step_data["id"]] = step_db_id
                step = WorkflowStep(
                    id=step_db_id,
                    workflow_id=workflow_id,
                    scheduled_job_id=step_data["scheduled_job_id"],
                    node_type=step_data["node_type"],
                    config_json=step_data.get("config_json")
                )
                db.add(step)

            for edge_data in edges_data:
                edge = WorkflowEdge(
                    id=str(uuid4()),
                    workflow_id=workflow_id,
                    from_step_id=step_id_map[edge_data["from_step_id"]],
                    to_step_id=step_id_map[edge_data["to_step_id"]],
                    branch_name=edge_data.get("branch_name")
                )
                db.add(edge)

            for param_data in params_data:
                param = WorkflowParameter(
                    id=str(uuid4()),
                    workflow_id=workflow_id,
                    name=param_data.name,
                    type=param_data.type,
                    default_value=param_data.default_value
                )
                db.add(param)

        workflow.updated_at = datetime.utcnow()
        await db.flush()  # Flush to make new steps/edges visible
        await db.commit()

        # Expunge the old workflow object so get() fetches fresh
        db.expunge(workflow)
        return await self.get(db, workflow_id)

    async def delete(self, db: AsyncSession, workflow_id: str) -> None:
        """Delete a Workflow (blocked if active runs exist)."""
        # Check for active runs
        stmt = select(WorkflowRun).where(
            and_(
                WorkflowRun.workflow_id == workflow_id,
                WorkflowRun.status == "RUNNING"
            )
        )
        result = await db.execute(stmt)
        active_runs = result.scalars().all()

        if active_runs:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "ACTIVE_RUNS_EXIST",
                    "active_run_ids": [r.id for r in active_runs]
                }
            )

        stmt = select(Workflow).where(Workflow.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        await db.delete(workflow)
        await db.commit()

    async def fork(
        self, db: AsyncSession, workflow_id: str, new_name: str, current_user_id: str
    ) -> WorkflowResponse:
        """Clone a Workflow and pause the source."""
        # Get source workflow
        stmt = select(Workflow).where(Workflow.id == workflow_id).options(
            selectinload(Workflow.steps),
            selectinload(Workflow.edges),
            selectinload(Workflow.parameters)
        )
        result = await db.execute(stmt)
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(status_code=404, detail="Workflow not found")

        new_workflow_id = str(uuid4())

        async with db.begin_nested():
            # Create new workflow
            new_workflow = Workflow(
                id=new_workflow_id,
                name=new_name,
                created_by=current_user_id,
                is_paused=False
            )
            db.add(new_workflow)

            # Clone steps
            step_id_map = {}
            stmt_steps = select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id)
            result = await db.execute(stmt_steps)
            source_steps = result.scalars().all()

            for old_step in source_steps:
                new_step_id = str(uuid4())
                step_id_map[old_step.id] = new_step_id
                new_step = WorkflowStep(
                    id=new_step_id,
                    workflow_id=new_workflow_id,
                    scheduled_job_id=old_step.scheduled_job_id,
                    node_type=old_step.node_type,
                    config_json=old_step.config_json
                )
                db.add(new_step)

            # Clone edges
            stmt_edges = select(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow_id)
            result = await db.execute(stmt_edges)
            source_edges = result.scalars().all()

            for old_edge in source_edges:
                new_edge = WorkflowEdge(
                    id=str(uuid4()),
                    workflow_id=new_workflow_id,
                    from_step_id=step_id_map[old_edge.from_step_id],
                    to_step_id=step_id_map[old_edge.to_step_id],
                    branch_name=old_edge.branch_name
                )
                db.add(new_edge)

            # Clone parameters
            stmt_params = select(WorkflowParameter).where(WorkflowParameter.workflow_id == workflow_id)
            result = await db.execute(stmt_params)
            source_params = result.scalars().all()

            for old_param in source_params:
                new_param = WorkflowParameter(
                    id=str(uuid4()),
                    workflow_id=new_workflow_id,
                    name=old_param.name,
                    type=old_param.type,
                    default_value=old_param.default_value
                )
                db.add(new_param)

            # Pause source
            source.is_paused = True

        await db.commit()
        return await self.get(db, new_workflow_id)

    async def _to_response(self, db: AsyncSession, workflow: Workflow, include_graph: bool = True) -> WorkflowResponse:
        """Convert Workflow ORM to WorkflowResponse with optional nested steps/edges/parameters."""
        # Get last run status
        stmt = select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow.id
        ).order_by(WorkflowRun.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        last_run = result.scalar_one_or_none()
        last_run_status = last_run.status if last_run else None

        # If include_graph=False, return empty lists for steps/edges/parameters (list endpoint)
        steps = [
            WorkflowStepResponse.model_validate(s)
            for s in workflow.steps
        ] if include_graph else []
        edges = [
            WorkflowEdgeResponse.model_validate(e)
            for e in workflow.edges
        ] if include_graph else []
        parameters = [
            WorkflowParameterResponse.model_validate(p)
            for p in workflow.parameters
        ] if include_graph else []

        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            created_by=workflow.created_by,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            is_paused=workflow.is_paused,
            step_count=len(workflow.steps),
            last_run_status=last_run_status,
            steps=steps,
            edges=edges,
            parameters=parameters
        )

    async def dispatch_next_wave(
        self,
        run_id: str,
        db: AsyncSession
    ) -> List[str]:
        """
        Dispatch all steps whose predecessors have COMPLETED.
        Atomically transitions PENDING→RUNNING, creates jobs for eligible steps.
        Uses BFS topological order via networkx.predecessors().
        Returns list of newly created job GUIDs.
        """
        # Get WorkflowRun
        run = await db.get(WorkflowRun, run_id)
        if run is None or run.status == "CANCELLED":
            return []

        # Get Workflow with eager-loaded relationships
        stmt = select(Workflow).where(Workflow.id == run.workflow_id).options(
            selectinload(Workflow.steps),
            selectinload(Workflow.edges)
        )
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if workflow is None:
            return []

        # Build graph for BFS dispatch order (reuse validate_dag pattern)
        G = nx.DiGraph()
        for step in workflow.steps:
            G.add_node(step.id)
        for edge in workflow.edges:
            if edge.branch_name is None:  # Only unconditional edges in Phase 147
                G.add_edge(edge.from_step_id, edge.to_step_id)

        # Create step_map for quick lookup
        step_map = {step.id: step for step in workflow.steps}

        # Get all existing WorkflowStepRuns for this run
        stmt = select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run_id)
        result = await db.execute(stmt)
        existing_step_runs = result.scalars().all()
        step_run_map = {sr.workflow_step_id: sr for sr in existing_step_runs}

        new_jobs = []

        # Process each step in topological order
        for step in workflow.steps:
            # Create WorkflowStepRun if it doesn't exist
            if step.id not in step_run_map:
                sr = WorkflowStepRun(
                    id=str(uuid4()),
                    workflow_run_id=run_id,
                    workflow_step_id=step.id,
                    status="PENDING",
                    created_at=datetime.utcnow()
                )
                db.add(sr)
                await db.flush()  # Ensure sr.id is available
                step_run_map[step.id] = sr
            else:
                sr = step_run_map[step.id]

            # Check if any predecessor is FAILED → cascade to CANCELLED
            predecessors = list(G.predecessors(step.id))
            has_failed_predecessor = False
            for pred_id in predecessors:
                pred_sr = step_run_map.get(pred_id)
                if pred_sr and pred_sr.status == "FAILED":
                    has_failed_predecessor = True
                    break

            if has_failed_predecessor:
                # Mark this step as CANCELLED
                sr.status = "CANCELLED"
                sr.completed_at = datetime.utcnow()
                continue

            # Check if all predecessors are COMPLETED (or no predecessors for root steps)
            if len(predecessors) == 0:
                # Root step
                all_complete = True
            else:
                all_complete = all(
                    step_run_map.get(pred_id) and step_run_map.get(pred_id).status == "COMPLETED"
                    for pred_id in predecessors
                )

            if not all_complete:
                # Not ready yet
                continue

            # Atomic CAS: try to transition status PENDING→RUNNING
            stmt_update = (
                update(WorkflowStepRun)
                .where(
                    and_(
                        WorkflowStepRun.id == sr.id,
                        WorkflowStepRun.status == "PENDING"
                    )
                )
                .values(status="RUNNING", started_at=datetime.utcnow())
            )
            result = await db.execute(stmt_update)

            # If rowcount == 0, another process already claimed it — skip
            if result.rowcount == 0:
                continue
            # NEW: Gate node handling (Phase 148)
            # Skip job creation for gate nodes; handle them with gate-specific logic
            if step.node_type == "PARALLEL":
                # PARALLEL gate: mark immediately COMPLETED (no job dispatch)
                stmt = update(WorkflowStepRun).where(
                    and_(WorkflowStepRun.id == sr.id, WorkflowStepRun.status == "PENDING")
                ).values(status="COMPLETED", completed_at=datetime.utcnow())
                result = await db.execute(stmt)
                if result.rowcount == 0:
                    continue  # Already transitioned; skip
                # Next wave will naturally fan out via BFS to all outgoing edges
                continue  # Skip job creation
            
            elif step.node_type == "AND_JOIN":
                # AND_JOIN gate: check all predecessors
                all_predecessors_complete = True
                any_predecessor_failed = False
                
                for pred_id in predecessors:
                    pred_sr = step_run_map.get(pred_id)
                    if not pred_sr:
                        all_predecessors_complete = False
                        break
                    if pred_sr.status == "FAILED" or pred_sr.status == "CANCELLED":
                        any_predecessor_failed = True
                        break
                    if pred_sr.status != "COMPLETED":
                        all_predecessors_complete = False
                        break
                
                if any_predecessor_failed:
                    # Fail fast
                    stmt = update(WorkflowStepRun).where(
                        and_(WorkflowStepRun.id == sr.id, WorkflowStepRun.status == "PENDING")
                    ).values(status="FAILED", completed_at=datetime.utcnow())
                    await db.execute(stmt)
                    continue
                
                if not all_predecessors_complete:
                    # Wait for remaining predecessors
                    continue
                
                # All predecessors complete: mark this AND_JOIN COMPLETED
                stmt = update(WorkflowStepRun).where(
                    and_(WorkflowStepRun.id == sr.id, WorkflowStepRun.status == "PENDING")
                ).values(status="COMPLETED", completed_at=datetime.utcnow())
                await db.execute(stmt)
                continue  # Skip job creation
            
            elif step.node_type == "OR_GATE":
                # OR_GATE: check if any predecessor is COMPLETED
                any_complete = any(
                    step_run_map.get(p_id) and step_run_map.get(p_id).status == "COMPLETED"
                    for p_id in predecessors
                )
                
                if any_complete:
                    # Mark OR_GATE COMPLETED
                    stmt = update(WorkflowStepRun).where(
                        and_(WorkflowStepRun.id == sr.id, WorkflowStepRun.status == "PENDING")
                    ).values(status="COMPLETED", completed_at=datetime.utcnow())
                    await db.execute(stmt)
                    
                    # Eagerly mark non-triggering branches SKIPPED
                    for p_id in predecessors:
                        p_status = step_run_map.get(p_id, None)
                        if p_status and p_status.status != "COMPLETED":
                            # Mark all descendants of this predecessor SKIPPED
                            await self._mark_branch_skipped(p_id, sr.workflow_run_id, G, db)
                    
                    continue  # Skip job creation
                else:
                    # No predecessor complete; wait for one
                    continue
            
            elif step.node_type == "SIGNAL_WAIT":
                # SIGNAL_WAIT: mark RUNNING; signal creation endpoint will advance it
                stmt = update(WorkflowStepRun).where(
                    and_(WorkflowStepRun.id == sr.id, WorkflowStepRun.status == "PENDING")
                ).values(status="RUNNING", started_at=datetime.utcnow())
                await db.execute(stmt)
                continue  # Skip job creation
            
            # For non-gate nodes (SCRIPT), continue to job creation below


            # Create Job for this step
            # Get the ScheduledJob to fetch job details
            scheduled_job = await db.get(ScheduledJob, step.scheduled_job_id)
            if scheduled_job is None:
                # Skip if scheduled job not found
                continue

            # Construct payload from script_content
            payload = {
                "script_content": scheduled_job.script_content,
                "signature_payload": scheduled_job.signature_payload
            }

            # Calculate depth: max(predecessor_depths) + 1, capped at 30
            if len(predecessors) == 0:
                job_depth = 0
            else:
                # Fetch predecessor jobs to get their depths
                pred_job_guids = []
                for pred_id in predecessors:
                    pred_sr = step_run_map.get(pred_id)
                    if pred_sr:
                        # Get the job for this predecessor step run
                        stmt_job = select(Job).where(Job.workflow_step_run_id == pred_sr.id)
                        job_result = await db.execute(stmt_job)
                        pred_job = job_result.scalar_one_or_none()
                        if pred_job:
                            pred_job_guids.append(pred_job.guid)

                # Get max depth from predecessor jobs
                if pred_job_guids:
                    stmt_depths = select(Job.depth).where(Job.guid.in_(pred_job_guids))
                    depth_result = await db.execute(stmt_depths)
                    depths = depth_result.scalars().all()
                    max_pred_depth = max(depths) if depths else 0
                    job_depth = min(max_pred_depth + 1, 30)  # ENGINE-02: cap at 30
                else:
                    job_depth = 0

            # Create Job for this workflow step (script task type)
            try:
                # Create job GUID
                job_guid = str(uuid4())
                job = Job(
                    guid=job_guid,
                    task_type="script",  # Workflow jobs are always script tasks
                    payload=json.dumps(payload),
                    status="PENDING",
                    target_tags=json.dumps(json.loads(scheduled_job.target_tags)) if scheduled_job.target_tags else None,
                    capability_requirements=json.dumps(json.loads(scheduled_job.capability_requirements)) if scheduled_job.capability_requirements else None,
                    max_retries=scheduled_job.max_retries or 0,
                    backoff_multiplier=scheduled_job.backoff_multiplier or 2.0,
                    timeout_minutes=scheduled_job.timeout_minutes,
                    scheduled_job_id=step.scheduled_job_id,
                    env_tag=scheduled_job.env_tag,
                    runtime=scheduled_job.runtime or "python",
                    name=scheduled_job.name,
                    workflow_step_run_id=sr.id,
                    depth=job_depth
                )
                db.add(job)
                new_jobs.append(job_guid)
            except Exception as e:
                # Skip on job creation failure
                continue

        # Commit all changes
        await db.commit()
        return new_jobs

    async def advance_workflow(
        self,
        run_id: str,
        db: AsyncSession
    ) -> None:
        """
        After a step completes, re-evaluate workflow and dispatch eligible next steps.
        Checks for terminal condition and computes final status.
        """
        # NEW: Evaluate IF gates for COMPLETED steps
        await self._evaluate_if_gates(run_id, db)

        # Dispatch next wave of eligible steps
        await self.dispatch_next_wave(run_id, db)

        # Query all WorkflowStepRuns to check if run is complete
        stmt = select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run_id)
        result = await db.execute(stmt)
        step_runs = result.scalars().all()

        # Count by status
        pending_count = sum(1 for sr in step_runs if sr.status == "PENDING")
        running_count = sum(1 for sr in step_runs if sr.status == "RUNNING")
        completed_count = sum(1 for sr in step_runs if sr.status == "COMPLETED")
        failed_count = sum(1 for sr in step_runs if sr.status == "FAILED")
        cancelled_count = sum(1 for sr in step_runs if sr.status == "CANCELLED")
        skipped_count = sum(1 for sr in step_runs if sr.status == "SKIPPED")

        # If there's still pending or running work, return early
        if pending_count > 0 or running_count > 0:
            return

        # Compute final status
        total_steps = len(step_runs)
        if total_steps == 0:
            final_status = "COMPLETED"
        elif completed_count == total_steps:
            final_status = "COMPLETED"
        elif completed_count > 0 and failed_count > 0:
            final_status = "PARTIAL"
        elif completed_count == 0 and failed_count > 0:
            final_status = "FAILED"
        else:
            # All CANCELLED or SKIPPED — edge case
            final_status = "FAILED"

        # Update WorkflowRun
        run = await db.get(WorkflowRun, run_id)
        if run:
            old_status = run.status
            run.status = final_status
            run.completed_at = datetime.utcnow()
            await db.commit()

            # Emit workflow_run_updated event if status changed
            if old_status != final_status:
                try:
                    from .. import main
                    event = WorkflowRunUpdatedEvent(
                        id=run.id,
                        workflow_id=run.workflow_id,
                        status=final_status,
                        started_at=run.started_at,
                        completed_at=run.completed_at,
                        triggered_by='all_steps_done'
                    )
                    await main.ws_manager.broadcast_workflow_run_updated(event)
                except Exception as e:
                    logger.error(f"Failed to broadcast workflow_run_updated event: {e}")

    async def _run_to_response(
        self,
        db: AsyncSession,
        run: WorkflowRun
    ) -> WorkflowRunResponse:
        """
        Populate a WorkflowRunResponse with all step_runs.
        Queries WorkflowStepRuns and converts to response objects.
        """
        stmt = select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run.id)
        result = await db.execute(stmt)
        step_runs = result.scalars().all()

        step_runs_response = [
            WorkflowStepRunResponse.model_validate(sr, from_attributes=True)
            for sr in step_runs
        ]

        return WorkflowRunResponse(
            id=run.id,
            workflow_id=run.workflow_id,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            trigger_type=run.trigger_type,
            triggered_by=run.triggered_by,
            parameters_json=run.parameters_json,
            created_at=run.created_at,
            step_runs=step_runs_response
        )

    async def start_run(
        self,
        workflow_id: str,
        parameters: Dict[str, Any] = None,
        trigger_type: str = "MANUAL",
        triggered_by: str = None,
        db: AsyncSession = None
    ) -> WorkflowRunResponse:
        """
        Create and start a WorkflowRun with parameter resolution and validation.

        Args:
            workflow_id: ID of workflow to run
            parameters: Dict of trigger-specific parameter overrides (optional)
            trigger_type: "MANUAL", "CRON", or "WEBHOOK" (default: MANUAL)
            triggered_by: username, "scheduler", or webhook name (default: "unknown")
            db: AsyncSession for database operations

        Returns:
            WorkflowRunResponse with created run details

        Raises:
            HTTPException(404): Workflow not found
            HTTPException(409): Workflow is paused
            HTTPException(422): Required parameters unsatisfied
        """
        # Fetch workflow with eager-loaded parameters
        stmt = select(Workflow).where(Workflow.id == workflow_id).options(
            selectinload(Workflow.parameters)
        )
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Check if workflow is paused
        if workflow.is_paused:
            raise HTTPException(status_code=409, detail="Workflow is paused")

        # Merge and validate parameters (trigger-specific override + defaults)
        parameters = parameters or {}
        resolved_params = {}

        for param in workflow.parameters:
            # Determine whether to allow caller override (trigger-type-specific)
            allow_caller_override = trigger_type in ("MANUAL", "WEBHOOK")

            # Check if parameter was explicitly provided (even if None)
            param_provided = param.name in parameters if allow_caller_override else False
            caller_value = parameters.get(param.name) if param_provided else None

            # Fall back to parameter default
            resolved_value = caller_value if param_provided else param.default_value

            # Validate: if required (no default) AND not provided, error
            if not param_provided and param.default_value is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Required parameter '{param.name}' not provided and has no default"
                )

            resolved_params[param.name] = resolved_value

        # Include extra caller-provided parameters not in workflow definition (for MANUAL/WEBHOOK)
        if trigger_type in ("MANUAL", "WEBHOOK"):
            for key, value in parameters.items():
                if key not in resolved_params:
                    resolved_params[key] = value

        # Snapshot parameters to JSON (always create JSON, even if empty dict)
        parameters_json = json.dumps(resolved_params)

        # Create WorkflowRun with trigger metadata
        run_id = str(uuid4())
        run = WorkflowRun(
            id=run_id,
            workflow_id=workflow_id,
            status="RUNNING",
            started_at=datetime.utcnow(),
            trigger_type=trigger_type,
            triggered_by=triggered_by or "unknown",
            parameters_json=parameters_json
        )
        db.add(run)
        await db.flush()  # Ensure run.id is set before dispatch

        # Log trigger info
        logger.info(f"WorkflowRun {run_id} triggered by {triggered_by or 'unknown'} ({trigger_type})")

        # Dispatch first wave (root steps)
        await self.dispatch_next_wave(run_id, db)

        # Commit
        await db.commit()

        # Return populated response
        return await self._run_to_response(db, run)

    async def _mark_branch_skipped(
        self,
        starting_step_id: str,
        run_id: str,
        graph: nx.DiGraph,
        db: AsyncSession
    ) -> None:
        """
        Recursively mark all descendant steps on a branch SKIPPED.
        Used by OR_GATE to mark non-selected branches.
        """
        visited = set()
        to_process = [starting_step_id]
        
        while to_process:
            step_id = to_process.pop(0)
            if step_id in visited:
                continue
            visited.add(step_id)
            
            # Get all descendants of this step
            descendants = list(graph.successors(step_id))
            for desc_id in descendants:
                # Query WorkflowStepRun for this descendant in this run
                stmt = select(WorkflowStepRun).where(
                    and_(
                        WorkflowStepRun.workflow_run_id == run_id,
                        WorkflowStepRun.workflow_step_id == desc_id,
                        WorkflowStepRun.status == "PENDING"  # Only mark PENDING steps
                    )
                )
                desc_run = (await db.execute(stmt)).scalar_one_or_none()
                if desc_run:
                    desc_run.status = "SKIPPED"
                    to_process.append(desc_id)
        
        await db.flush()

    async def _evaluate_if_gates(self, run_id: str, db: AsyncSession) -> None:
        """
        For each COMPLETED step with node_type IF_GATE, evaluate its condition
        against the predecessor's result_json and route to matching branch or fail.
        """
        from agent_service.services.gate_evaluation_service import GateEvaluationService
        
        # Get all COMPLETED IF_GATE step runs in this run
        stmt = select(WorkflowStepRun).join(
            WorkflowStep, WorkflowStepRun.workflow_step_id == WorkflowStep.id
        ).where(
            and_(
                WorkflowStepRun.workflow_run_id == run_id,
                WorkflowStep.node_type == "IF_GATE",
                WorkflowStepRun.status == "COMPLETED"
            )
        )
        if_gate_runs = (await db.execute(stmt)).scalars().all()
        
        for gate_run in if_gate_runs:
            step = await db.get(WorkflowStep, gate_run.workflow_step_id)
            
            # Get predecessor's result_json via edge lookup
            # IF gates should have exactly one unconditional predecessor
            edge_stmt = select(WorkflowEdge).where(
                and_(
                    WorkflowEdge.to_step_id == step.id,
                    WorkflowEdge.branch_name.is_(None)  # Only unconditional edges
                )
            )
            pred_edges = (await db.execute(edge_stmt)).scalars().all()
            
            if not pred_edges:
                # No predecessors — mark FAILED
                gate_run.status = "FAILED"
                continue
            
            pred_step_id = pred_edges[0].from_step_id
            pred_run_stmt = select(WorkflowStepRun).where(
                and_(
                    WorkflowStepRun.workflow_run_id == run_id,
                    WorkflowStepRun.workflow_step_id == pred_step_id
                )
            )
            pred_run = (await db.execute(pred_run_stmt)).scalar_one_or_none()
            
            if not pred_run or not pred_run.result_json:
                # No result — mark FAILED
                gate_run.status = "FAILED"
                continue
            
            # Evaluate IF gate
            try:
                result = json.loads(pred_run.result_json)
            except json.JSONDecodeError:
                gate_run.status = "FAILED"
                continue
            
            branch_taken, error = GateEvaluationService.evaluate_if_gate(
                step.config_json or '{"branches": {}}', result
            )
            
            if branch_taken is None:
                # No branch matched — mark FAILED
                gate_run.status = "FAILED"
                # Cascade failure: mark all descendants CANCELLED
                await self._cascade_cancel(step.id, run_id, db)
            else:
                # Branch matched — status is already COMPLETED
                pass

    async def _cascade_cancel(self, step_id: str, run_id: str, db: AsyncSession) -> None:
        """
        Recursively mark all PENDING descendants of a step as CANCELLED.
        Used when a step fails to cascade failure downstream.
        """
        visited = set()
        to_process = [step_id]
        
        while to_process:
            current_id = to_process.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            
            # Find all descendants in workflow
            edge_stmt = select(WorkflowEdge).where(WorkflowEdge.from_step_id == current_id)
            edges = (await db.execute(edge_stmt)).scalars().all()
            
            for edge in edges:
                desc_id = edge.to_step_id
                
                # Query for step run
                stmt = select(WorkflowStepRun).where(
                    and_(
                        WorkflowStepRun.workflow_run_id == run_id,
                        WorkflowStepRun.workflow_step_id == desc_id,
                        WorkflowStepRun.status == "PENDING"
                    )
                )
                desc_run = (await db.execute(stmt)).scalar_one_or_none()
                if desc_run:
                    desc_run.status = "CANCELLED"
                    to_process.append(desc_id)
        
        await db.flush()

    async def store_step_result(self, step_run_id: str, result: Optional[Dict], db: AsyncSession) -> None:
        """Store step execution result for IF gate evaluation."""
        if result is None:
            return
        
        result_json_str = json.dumps(result)
        
        stmt = update(WorkflowStepRun).where(
            WorkflowStepRun.id == step_run_id
        ).values(result_json=result_json_str)
        await db.execute(stmt)
        await db.flush()


    async def advance_signal_wait(self, signal_name: str, db: AsyncSession) -> None:
        """
        Wake up any RUNNING SIGNAL_WAIT step runs waiting on the given signal.
        Called from signal creation endpoint after signal is persisted.
        """
        # Find all RUNNING SIGNAL_WAIT step runs waiting on this signal_name
        stmt = select(WorkflowStepRun).join(
            WorkflowStep, WorkflowStepRun.workflow_step_id == WorkflowStep.id
        ).where(
            and_(
                WorkflowStep.node_type == "SIGNAL_WAIT",
                WorkflowStepRun.status == "RUNNING"
            )
        )
        signal_wait_runs = (await db.execute(stmt)).scalars().all()
        
        # Filter to runs waiting on this specific signal_name
        run_ids_to_advance = set()
        for sr in signal_wait_runs:
            step = await db.get(WorkflowStep, sr.workflow_step_id)
            try:
                config = json.loads(step.config_json or '{}')
                waiting_signal = config.get('signal_name', '')
                
                # Match signal names (exact string comparison)
                if waiting_signal == signal_name:
                    # Mark SIGNAL_WAIT as COMPLETED
                    sr.status = "COMPLETED"
                    sr.completed_at = datetime.utcnow()
                    run_ids_to_advance.add(sr.workflow_run_id)
            except json.JSONDecodeError:
                # Invalid config; skip this step
                pass
        
        await db.flush()
        
        # Advance any affected workflow runs
        for run_id in run_ids_to_advance:
            await self.advance_workflow(run_id, db)



    async def cancel_run(
        self,
        run_id: str,
        db: AsyncSession
    ) -> WorkflowRunResponse:
        """
        Cancel a running WorkflowRun.
        Blocks further step dispatches; running jobs continue to completion.
        """
        # Fetch run
        run = await db.get(WorkflowRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="WorkflowRun not found")

        # Check if run is already terminal
        if run.status in ["COMPLETED", "PARTIAL", "FAILED", "CANCELLED"]:
            raise HTTPException(status_code=409, detail="Run is already terminal")

        # Set status to CANCELLED
        run.status = "CANCELLED"
        run.completed_at = datetime.utcnow()

        # Mark all PENDING WorkflowStepRuns as CANCELLED
        stmt = (
            update(WorkflowStepRun)
            .where(
                and_(
                    WorkflowStepRun.workflow_run_id == run_id,
                    WorkflowStepRun.status == "PENDING"
                )
            )
            .values(status="CANCELLED", completed_at=datetime.utcnow())
        )
        await db.execute(stmt)

        # Also mark any RUNNING SIGNAL_WAIT steps as CANCELLED (prevents wakeup after cancel)
        stmt = select(WorkflowStepRun).where(
            and_(
                WorkflowStepRun.workflow_run_id == run_id,
                WorkflowStepRun.status == "RUNNING"
            )
        )
        running_steps = (await db.execute(stmt)).scalars().all()
        for sr in running_steps:
            step = await db.get(WorkflowStep, sr.workflow_step_id)
            if step and step.node_type == "SIGNAL_WAIT":
                sr.status = "CANCELLED"
                sr.completed_at = datetime.utcnow()

        await db.flush()

        # Commit
        await db.commit()

        # Phase 150: Emit workflow_run_updated and workflow_step_updated events
        try:
            from .. import main

            # Emit run update event
            run_event = WorkflowRunUpdatedEvent(
                id=run.id,
                workflow_id=run.workflow_id,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                triggered_by='manual_cancel'
            )
            await main.ws_manager.broadcast_workflow_run_updated(run_event)

            # Emit step update events for all cancelled steps
            for sr in running_steps:
                if sr.status == "CANCELLED":
                    step_event = WorkflowStepUpdatedEvent(
                        id=sr.id,
                        workflow_run_id=sr.workflow_run_id,
                        workflow_step_id=sr.workflow_step_id,
                        status=sr.status,
                        started_at=sr.started_at,
                        completed_at=sr.completed_at
                    )
                    await main.ws_manager.broadcast_workflow_step_updated(step_event)
        except Exception as e:
            logger.error(f"Failed to broadcast cancel run events: {e}")

        # Return response
        return await self._run_to_response(db, run)
