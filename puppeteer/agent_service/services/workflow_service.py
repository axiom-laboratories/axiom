import json
from typing import Optional, List, Tuple, Dict, Any
from uuid import uuid4
from datetime import datetime

import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from fastapi import HTTPException

from puppeteer.agent_service.db import (
    Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter,
    ScheduledJob, WorkflowRun
)
from puppeteer.agent_service.models import (
    WorkflowCreate, WorkflowResponse, WorkflowUpdate, WorkflowValidationError,
    WorkflowStepResponse, WorkflowEdgeResponse, WorkflowParameterResponse
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
        """List all Workflows with metadata."""
        stmt = select(Workflow).offset(skip).limit(limit)
        result = await db.execute(stmt)
        workflows = result.scalars().all()

        responses = []
        for w in workflows:
            responses.append(await self._to_response(db, w))
        return responses

    async def get(self, db: AsyncSession, workflow_id: str) -> WorkflowResponse:
        """Get a single Workflow by ID with full graph."""
        stmt = select(Workflow).where(Workflow.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return await self._to_response(db, workflow)

    async def update(
        self, db: AsyncSession, workflow_id: str, update: WorkflowUpdate
    ) -> WorkflowResponse:
        """Update a Workflow (atomic delete/insert of steps/edges/parameters)."""
        stmt = select(Workflow).where(Workflow.id == workflow_id)
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
        await db.commit()
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
        stmt = select(Workflow).where(Workflow.id == workflow_id)
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

    async def _to_response(self, db: AsyncSession, workflow: Workflow) -> WorkflowResponse:
        """Convert Workflow ORM to WorkflowResponse with nested steps/edges/parameters."""
        # Get last run status
        stmt = select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow.id
        ).order_by(WorkflowRun.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        last_run = result.scalar_one_or_none()
        last_run_status = last_run.status if last_run else None

        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            created_by=workflow.created_by,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            is_paused=workflow.is_paused,
            step_count=len(workflow.steps),
            last_run_status=last_run_status,
            steps=[
                WorkflowStepResponse.model_validate(s)
                for s in workflow.steps
            ],
            edges=[
                WorkflowEdgeResponse.model_validate(e)
                for e in workflow.edges
            ],
            parameters=[
                WorkflowParameterResponse.model_validate(p)
                for p in workflow.parameters
            ]
        )
