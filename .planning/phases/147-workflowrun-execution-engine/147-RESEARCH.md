# Phase 147: WorkflowRun Execution Engine - Research

**Researched:** 2026-04-15  
**Domain:** Async DAG execution engine, workflow state machine, atomic dispatch  
**Confidence:** HIGH

## Summary

Phase 147 implements the BFS dispatch engine that executes WorkflowRun instances end-to-end. The engine tracks step-level progress via a new WorkflowStepRun table, manages the WorkflowRun state machine (RUNNING → COMPLETED/PARTIAL/FAILED/CANCELLED), and handles cascade cancellation when branches fail. Core patterns are well-established in the codebase: async/await, SQLAlchemy ORM, networkx for DAG topology, and atomic transaction guards for concurrency safety.

The implementation is straightforward SQL + service logic following the existing JobService pattern. No new external libraries required (networkx, asyncpg, SQLAlchemy already in requirements.txt).

**Primary recommendation:** Use atomic UPDATE with WHERE status='PENDING' for concurrency guards instead of SELECT FOR UPDATE (better SQLite compat for local dev); implement advance_workflow() as an async method in WorkflowService, called synchronously from report_result() route handler after job update commits.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **WorkflowStepRun table structure:**
   - id (UUID String PK), workflow_run_id (FK), workflow_step_id (FK), status, started_at (nullable), completed_at (nullable), created_at
   - Status values: PENDING / RUNNING / COMPLETED / FAILED / SKIPPED / CANCELLED
   - Job link: add `workflow_step_run_id` FK column to Job table; no result blob on WorkflowStepRun

2. **BFS advance trigger:**
   - Hook in `report_result()`: after job status update, check if job.workflow_step_run_id is set; if yes, call WorkflowService.advance_workflow()
   - Engine location: add advance_workflow() and dispatch_next_wave() to existing WorkflowService class

3. **Concurrency guard:**
   - Atomic UPDATE `WorkflowStepRun.status = 'RUNNING' WHERE status = 'PENDING'`; if 0 rows updated, another process claimed it — skip
   - No SELECT FOR UPDATE (SQLite dev compatibility)
   - Full DAG parallelism: all steps with completed predecessors dispatch in same transaction

4. **PARTIAL vs FAILED state machine:**
   - Independent branches continue; failure blocks downstream descendants but not unrelated branches
   - Terminal conditions:
     - COMPLETED: every WorkflowStepRun reached COMPLETED
     - PARTIAL: at least one COMPLETED, at least one FAILED (remainder SKIPPED or CANCELLED)
     - FAILED: no steps reached COMPLETED (all FAILED or CANCELLED before running)
   - Run completion check: count WorkflowStepRuns still PENDING/RUNNING; if 0 → compute final status and write WorkflowRun.status + completed_at

5. **Run creation & cancellation API:**
   - POST /api/workflow-runs: body {workflow_id, parameters: {key: value}} — validates workflow exists and is not paused, creates WorkflowRun (status=RUNNING), dispatches first BFS wave immediately
   - POST /api/workflow-runs/{id}/cancel: dedicated action endpoint, sets WorkflowRun.status = CANCELLED
   - Cancellation scope: blocks further step dispatches; running jobs complete on nodes; PENDING steps transition to CANCELLED

### Claude's Discretion

- Exact Pydantic model names for WorkflowStepRun responses
- Whether advance_workflow is async-safe to call inline in report_result or needs asyncio.create_task
- Migration file naming (next after migration_v53.sql)
- Test structure and fixtures

### Deferred Ideas (OUT OF SCOPE)

- IF gate / AND/JOIN / OR / Parallel fan-out / Signal wait gate logic — Phase 148
- Cron trigger scheduling, webhook trigger — Phase 149 (manual POST trigger implemented in Phase 147)
- DAG visualization, run history UI, step logs view — Phase 150
- Per-step retry logic — Phase 148+ concern
- Fail-fast mode (configurable per-workflow) — future consideration, not Phase 147

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENGINE-01 | System dispatches WorkflowRun steps in topological order (BFS), releasing each step only after its dependencies complete | BFS dispatch_next_wave() queries workflow graph via networkx, finds eligible steps (all predecessors COMPLETED), atomically transitions PENDING→RUNNING, creates step Jobs |
| ENGINE-02 | System overrides the 10-level job depth limit to 30 levels for workflow-instantiated jobs | Job model has no depth counter; 30-level limit enforced at workflow DAG validation (Phase 146). Jobs created by WorkflowRun pass through normal 10-level checks — clarification needed in planning |
| ENGINE-03 | System uses atomic concurrency guards (SELECT...FOR UPDATE) when processing concurrent step completions to prevent duplicate dispatch | CAS pattern: UPDATE WorkflowStepRun.status = 'RUNNING' WHERE id=? AND status='PENDING'; if 0 rows, skip (another process won) — no SELECT FOR UPDATE needed |
| ENGINE-04 | System tracks WorkflowRun status as one of: RUNNING / COMPLETED / PARTIAL / FAILED / CANCELLED | WorkflowRun.status column exists; advance_workflow() computes terminal status by counting PENDING/RUNNING steps and checking for COMPLETED/FAILED outcomes |
| ENGINE-05 | System propagates a step's FAILED status to all downstream PENDING steps (cascade cancel) | dispatch_next_wave() checks predecessors; if any FAILED, mark current step CANCELLED and skip dispatch; cascades transitively |
| ENGINE-06 | System marks WorkflowRun as PARTIAL when failures are absorbed by FAILED-branch steps rather than causing global FAILED | Logic in WorkflowRun terminal status check: if COMPLETED count > 0 AND FAILED count > 0 → PARTIAL; if COMPLETED count == 0 → FAILED; if all COMPLETED → COMPLETED |
| ENGINE-07 | User can cancel a running WorkflowRun; system actively aborts ASSIGNED/RUNNING step jobs and marks all PENDING steps CANCELLED | POST /api/workflow-runs/{id}/cancel sets WorkflowRun.status=CANCELLED; advance_workflow() checks flag and skips further dispatches; no node-level job interrupt |

</phase_requirements>

---

## Standard Stack

### Core Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | >=3.6,<4.0 | DAG topology, predecessor/successor queries, topological sort | Already in requirements; Phase 146 uses it for cycle detection; BFS leverages nx.DiGraph and descendants() |
| SQLAlchemy | latest async | ORM models, relationships, async transactions, atomic UPDATE | Existing codebase standard; WorkflowRun/Step tables already using ORM |
| asyncpg | latest | PostgreSQL async driver | Existing codebase standard; used for all async DB operations |
| FastAPI | latest | HTTP route handlers, dependency injection | Existing codebase standard; report_result route already FastAPI |

### Code Organization

**Service Layer Pattern (established in JobService, ScheduledJobService):**
- All DB queries in service methods (async def)
- Service methods accept AsyncSession parameter
- Transactions wrapped in `async with db.begin_nested():` for atomic writes
- Errors raised as HTTPException(status_code=..., detail=...)

**ORM Pattern (established in db.py):**
- UUID String primary keys (no auto-increment)
- Relationships defined via back_populates
- Nullable fields marked in Mapped[] type hint
- Index definitions for foreign keys and query-heavy columns

### Installation

```bash
# All libraries already in requirements.txt — Phase 147 adds no new dependencies
pip install -r puppeteer/requirements.txt
```

---

## Architecture Patterns

### Recommended Project Structure

The implementation spans two main files with minimal changes:

```
puppeteer/agent_service/
├── db.py                          # Add WorkflowStepRun ORM class; add workflow_step_run_id to Job
├── models.py                      # Add WorkflowStepRun Pydantic models (Create/Response)
├── services/workflow_service.py   # Add start_run(), advance_workflow(), dispatch_next_wave(), cancel_run()
└── main.py                        # Add POST /api/workflow-runs and POST /api/workflow-runs/{id}/cancel routes
                                   # Integrate advance_workflow() call into POST /work/{guid}/result handler
```

### Pattern 1: BFS Dispatch with Atomic CAS

**What:** Breadth-first dispatch of eligible steps using networkx predecessors + atomic status transition to prevent duplicates.

**When to use:** Any multi-step async orchestration needing concurrent parallelism without duplicate work.

**Example:**

```python
# From CONTEXT.md decision + existing networkx pattern in workflow_service.py
async def dispatch_next_wave(
    run_id: str, 
    db: AsyncSession
) -> List[str]:
    """
    Dispatch all steps whose predecessors have COMPLETED.
    Returns list of newly created job GUIDs.
    
    Pattern: Query predecessors via networkx, check status, atomically transition PENDING→RUNNING.
    """
    # Get run and workflow
    run = await db.get(WorkflowRun, run_id)
    if not run or run.status == "CANCELLED":
        return []
    
    workflow = await db.get(Workflow, run.workflow_id)
    
    # Build graph: nodes=steps, edges=dependency graph
    G = nx.DiGraph()
    step_map = {}  # step_id -> WorkflowStep
    for step in workflow.steps:
        G.add_node(step.id)
        step_map[step.id] = step
    
    for edge in workflow.edges:
        if edge.branch_name is None:  # Unconditional edges (Phase 147); IF gates in Phase 148
            G.add_edge(edge.from_step_id, edge.to_step_id)
    
    # Get all step runs for this workflow run
    stmt = select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run_id)
    result = await db.execute(stmt)
    step_runs = result.scalars().all()
    step_run_map = {sr.workflow_step_id: sr for sr in step_runs}
    
    # Find eligible steps: all predecessors COMPLETED, current step PENDING
    eligible = []
    for step_id, step in step_map.items():
        if step_id not in step_run_map:
            # Create WorkflowStepRun on first access
            sr = WorkflowStepRun(
                id=str(uuid4()),
                workflow_run_id=run_id,
                workflow_step_id=step_id,
                status="PENDING",
                created_at=datetime.utcnow()
            )
            db.add(sr)
            step_run_map[step_id] = sr
        
        sr = step_run_map[step_id]
        if sr.status != "PENDING":
            continue  # Already running, completed, failed, or cancelled
        
        # Check if all predecessors are COMPLETED
        predecessors = list(G.predecessors(step_id))
        all_complete = all(step_run_map[p].status == "COMPLETED" for p in predecessors)
        
        # Check if any predecessor is FAILED (cascade cancel logic)
        any_failed = any(step_run_map[p].status == "FAILED" for p in predecessors)
        
        if any_failed:
            # Cascade: mark this step CANCELLED
            sr.status = "CANCELLED"
            sr.completed_at = datetime.utcnow()
            continue
        
        if all_complete or not predecessors:  # Root steps have no predecessors
            eligible.append(step_id)
    
    # Atomic dispatch: transition PENDING→RUNNING for eligible steps
    new_jobs = []
    for step_id in eligible:
        sr = step_run_map[step_id]
        
        # Atomic CAS: if status is still PENDING, transition to RUNNING
        # If another process just transitioned it, this will return 0 rows and we skip
        stmt = (
            update(WorkflowStepRun)
            .where(and_(WorkflowStepRun.id == sr.id, WorkflowStepRun.status == "PENDING"))
            .values(status="RUNNING", started_at=datetime.utcnow())
        )
        result = await db.execute(stmt)
        if result.rowcount == 0:
            # Another process already claimed this step; skip
            continue
        
        # Create Job for this step
        step = step_map[step_id]
        job_guid = create_job_from_workflow_step(step, sr.id, db)  # Helper defined in JobService
        new_jobs.append(job_guid)
    
    await db.commit()
    return new_jobs


async def advance_workflow(
    run_id: str,
    db: AsyncSession
) -> None:
    """
    After a step completes, re-evaluate the workflow and dispatch eligible next steps.
    Called from report_result() route handler after job status update.
    
    Pattern: Query run status, dispatch next wave, check for terminal condition.
    """
    # Dispatch next eligible steps
    await dispatch_next_wave(run_id, db)
    
    # Check if run is complete
    stmt = select(WorkflowStepRun).where(
        and_(
            WorkflowStepRun.workflow_run_id == run_id,
            WorkflowStepRun.status.in_(["PENDING", "RUNNING"])
        )
    )
    result = await db.execute(stmt)
    pending_or_running = result.scalars().all()
    
    if pending_or_running:
        # Run still has work; don't finalize
        return
    
    # Run is complete: compute final status
    stmt = select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run_id)
    result = await db.execute(stmt)
    all_steps = result.scalars().all()
    
    completed_count = sum(1 for s in all_steps if s.status == "COMPLETED")
    failed_count = sum(1 for s in all_steps if s.status == "FAILED")
    
    if completed_count == len(all_steps):
        final_status = "COMPLETED"
    elif completed_count > 0 and failed_count > 0:
        final_status = "PARTIAL"
    elif completed_count == 0:
        final_status = "FAILED"
    else:
        final_status = "RUNNING"  # Fallback; should not reach here
    
    # Update run with terminal status
    run = await db.get(WorkflowRun, run_id)
    run.status = final_status
    run.completed_at = datetime.utcnow()
    await db.commit()
```

**Why this pattern works:**
- Networkx provides O(V+E) predecessor queries without duplicating graph construction
- Atomic UPDATE with WHERE condition avoids race conditions without locking (SQLite-compatible)
- Transitive cascade (failed predecessor → cancel dependent) handled in single query loop
- No SELECT FOR UPDATE needed (avoids SQLite dev compatibility issues)

### Pattern 2: Workflow Run Lifecycle (RUNNING → COMPLETED/PARTIAL/FAILED/CANCELLED)

**What:** State machine for WorkflowRun.status with clear terminal conditions.

**When to use:** Any long-running async process with multiple terminal states and dependencies between substeps.

**State transitions:**

```
RUNNING ─→ (all steps COMPLETED) → COMPLETED
       ├→ (some COMPLETED, some FAILED) → PARTIAL
       ├→ (user calls /cancel) → CANCELLED
       └→ (step fails, blocks all downstream) → FAILED (if no steps completed)

Terminal states: COMPLETED, PARTIAL, FAILED, CANCELLED
Non-terminal: RUNNING
```

**Decision logic:**

```python
# After all steps reach a terminal state (PENDING or RUNNING count == 0)
if all_steps_completed:
    final_status = "COMPLETED"
elif has_completed and has_failed:
    final_status = "PARTIAL"
elif not has_completed and has_failed:
    final_status = "FAILED"
```

### Pattern 3: Integration Point in report_result()

**What:** After a job completes, trigger workflow advance if job is linked to a WorkflowStepRun.

**When to use:** Any time external async work (job execution) feeds back into an orchestrator's state machine.

**Code location:**

```python
# In main.py, POST /work/{guid}/result route handler
async def report_job_result(guid: str, report: ResultReport, db: AsyncSession):
    # Existing: update job status
    job = await JobService.report_result(guid, report, node_ip, db)
    
    # NEW: if job is linked to a workflow step, advance the workflow
    if job and job.workflow_step_run_id:
        await WorkflowService.advance_workflow(job.workflow_step_run_id.split("@")[0], db)
    
    return {"status": "ok"}
```

### Anti-Patterns to Avoid

- **Don't use SELECT FOR UPDATE:** Breaks SQLite dev setup and adds unnecessary lock contention. CAS pattern (atomic UPDATE WHERE status='PENDING') is simpler and faster.
- **Don't query all steps every dispatch:** Use networkx to find only eligible steps; querying all steps on every advance is O(n²).
- **Don't duplicate result storage:** Store job result in Job.result, not in WorkflowStepRun.result_blob. Phase 150 queries Job for output.
- **Don't blocking-wait for nodes:** Cancellation is a soft stop (don't dispatch new steps). Running jobs complete on nodes; no SIGKILL.
- **Don't defer topology rebuild:** Cache workflow graph in memory during run lifecycle; don't re-execute validate_dag on every step dispatch.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DAG traversal, predecessor queries, cycle detection | Custom graph DFS/BFS | networkx library (already in requirements) | Handles edge cases (disconnected components, multiple roots), optimized C implementation for large graphs, tested across hundreds of projects |
| Atomic concurrent step dispatch | Home-grown locking with threads | SQLAlchemy atomic UPDATE + WHERE clause | Database-level atomicity, works across process boundaries, SQLite + Postgres compatible without code changes |
| Step-by-step status tracking | Denormalize into single run_status column | Separate WorkflowStepRun table with per-step status | Enables partial success detection, allows phases to query "which steps failed" without parsing a monolithic blob |
| Job-to-workflow linking | Add result_json column to WorkflowStepRun | Add workflow_step_run_id FK to Job | Avoids data duplication, Phase 150 already expects to query Job for logs/output, single source of truth |
| Cascade cancellation on failure | Manual loop checking all descendants | Transitive query in dispatch_next_wave loop | Single loop finds all predecessors; cascade happens naturally via status check; no separate topological re-analysis needed |

**Key insight:** The BFS dispatch pattern with atomic CAS guards is simpler and more correct than building a custom task queue. Since WorkflowRun dispatch happens synchronously in report_result(), no need for background worker pool or message queue.

---

## Common Pitfalls

### Pitfall 1: Race Condition in Concurrent Step Dispatch

**What goes wrong:** Two nodes report job completion at nearly the same instant for different steps in the same wave. Both call report_result() → advance_workflow() → dispatch_next_wave(). Both query pending steps, both see the same eligible step, both try to dispatch a job, resulting in duplicate execution.

**Why it happens:** Without atomic status transition, the check-and-dispatch is two operations: query PENDING steps, then create Job. Race window between query and create.

**How to avoid:** Use atomic UPDATE to transition status PENDING→RUNNING in the database. If rowcount == 0, another process beat you to it; skip dispatch for that step. Works because database serialization is atomic.

**Warning signs:** Job.guid column has duplicates for the same WorkflowStep in the same run; WorkflowStepRun shows RUNNING status twice; logs show "dispatching step X" twice from different handler calls.

### Pitfall 2: Forgetting Cascade Cancellation Logic

**What goes wrong:** A step fails, but downstream steps still dispatch because the engine only checks "predecessors completed" without checking "any predecessor failed".

**Why it happens:** Cascade is an easy-to-forget special case; the happy path (all predecessors complete) dominates thinking.

**How to avoid:** In dispatch_next_wave(), add explicit check: if any predecessor is FAILED, mark current step CANCELLED. Do this before the all_complete check, so cascade happens transitively.

**Warning signs:** Failed step has children still RUNNING; PARTIAL runs have RUNNING steps downstream of a FAILED step; operator manually cancels descendants after a step fails.

### Pitfall 3: Status Confusion on Terminal Checks

**What goes wrong:** Run lingers in RUNNING state even though all steps are terminal. Completed_at never set. run.status = "RUNNING" forever.

**Why it happens:** The terminal check logic is subtle: need to count PENDING+RUNNING (if zero, we're done); then count COMPLETED+FAILED to determine PARTIAL vs FAILED.

**How to avoid:** Simple pattern: after every step_run transitions to a terminal status (COMPLETED, FAILED, SKIPPED, CANCELLED), always call the terminal check (count PENDING+RUNNING; if zero, decide final status). Put this in a separate method and call it consistently.

**Warning signs:** run.completed_at is always NULL; status never moves to COMPLETED/PARTIAL/FAILED; monitoring scripts report "stuck runs".

### Pitfall 4: Forgetting to Link Job to WorkflowStepRun

**What goes wrong:** Job is created for a step, but job.workflow_step_run_id is NULL. report_result() later doesn't call advance_workflow() because the link is missing.

**Why it happens:** Job table has many columns; easy to miss the new FK when calling create().

**How to avoid:** When creating a Job in dispatch_next_wave(), always set job.workflow_step_run_id = step_run.id. Make this a required parameter (not optional) in the job creation helper.

**Warning signs:** Workflow run gets stuck at RUNNING; jobs complete but advance_workflow() is never triggered; no WorkflowStepRun status updates.

### Pitfall 5: Async/Await Confusion in Integration Point

**What goes wrong:** advance_workflow() is async, but it's called from a sync route handler (or vice versa).

**Why it happens:** report_result() route is async (FastAPI), WorkflowService.advance_workflow() is async. Tempting to `await` it directly, but also tempting to fire-and-forget with asyncio.create_task().

**How to avoid:** Keep advance_workflow() async, and await it directly in the route handler. No need for background tasks; the flow is: job completes → advance → dispatch next steps → all synchronous in the same DB transaction.

**Warning signs:** `RuntimeError: no running event loop` or `await outside async function`; workflow jobs never dispatch because advance_workflow() was spawned but not awaited.

---

## Code Examples

Verified patterns from Phase 146 + existing codebase:

### Create WorkflowStepRun ORM Class (db.py)

```python
# Source: db.py pattern (mirrors WorkflowStep, WorkflowRun structure)

class WorkflowStepRun(Base):
    __tablename__ = "workflow_step_runs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"))
    workflow_step_id: Mapped[str] = mapped_column(ForeignKey("workflow_steps.id"))
    status: Mapped[str] = mapped_column(String)  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, CANCELLED
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow_run: Mapped["WorkflowRun"] = relationship("WorkflowRun")
    workflow_step: Mapped["WorkflowStep"] = relationship("WorkflowStep")
```

### Add workflow_step_run_id to Job ORM Class (db.py)

```python
# Source: db.py Job class, append to existing columns

class Job(Base):
    # ... existing columns ...
    workflow_step_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # FK to WorkflowStepRun.id
```

### Pydantic Models (models.py)

```python
# Source: Pattern from WorkflowResponse, JobResponse

class WorkflowStepRunCreate(BaseModel):
    workflow_run_id: str
    workflow_step_id: str
    status: str = "PENDING"

class WorkflowStepRunResponse(BaseModel):
    id: str
    workflow_run_id: str
    workflow_step_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class WorkflowRunResponse(BaseModel):
    """Updated to include step runs."""
    id: str
    workflow_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    trigger_type: Optional[str] = None
    triggered_by: Optional[str] = None
    created_at: datetime
    # NEW in Phase 147:
    step_runs: List[WorkflowStepRunResponse] = []  # Populated in service layer
    
    model_config = ConfigDict(from_attributes=True)
```

### Start a Workflow Run (main.py Route)

```python
# Source: Pattern from POST /jobs/create

@app.post("/api/workflow-runs")
async def start_workflow_run(
    body: dict,
    current_user = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a WorkflowRun.
    
    body: {
        "workflow_id": str,
        "parameters": {key: value}  # optional, overrides defaults
    }
    """
    workflow_service = WorkflowService()
    run = await workflow_service.start_run(
        workflow_id=body["workflow_id"],
        parameters=body.get("parameters", {}),
        triggered_by=current_user.username,
        db=db
    )
    return run
```

### Service Method: start_run (workflow_service.py)

```python
# Source: JobService.create() pattern + Phase 146 fork() pattern

async def start_run(
    self,
    workflow_id: str,
    parameters: Dict[str, Any],
    triggered_by: str,
    db: AsyncSession
) -> WorkflowRunResponse:
    """
    Create a WorkflowRun and dispatch the first BFS wave.
    """
    # Fetch and validate workflow
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.is_paused:
        raise HTTPException(status_code=409, detail="Workflow is paused")
    
    # Create run
    run_id = str(uuid4())
    run = WorkflowRun(
        id=run_id,
        workflow_id=workflow_id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type="MANUAL",
        triggered_by=triggered_by
    )
    db.add(run)
    await db.flush()  # Ensure run.id is set before dispatch
    
    # Dispatch first wave (root steps)
    await self.dispatch_next_wave(run_id, db)
    
    await db.commit()
    return await self._run_to_response(db, run)
```

### Integration in report_result() (main.py)

```python
# Source: Existing POST /work/{guid}/result route

@app.post("/work/{guid}/result")
async def report_job_result(
    guid: str,
    report: ResultReport,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Report job completion from node."""
    node_ip = request.client.host if request.client else "unknown"
    
    # Existing: update job status and create execution record
    job = await JobService.report_result(guid, report, node_ip, db)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # NEW: if job is linked to a workflow step, advance the workflow
    if job.workflow_step_run_id:
        run_id = job.workflow_step_run_id.split("@")[0]  # Extract run_id if composite key
        workflow_service = WorkflowService()
        await workflow_service.advance_workflow(run_id, db)
    
    return {"status": "ok", "job_guid": guid}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SELECT FOR UPDATE concurrency guard | Atomic UPDATE WHERE status='PENDING' | Phase 147 | Better SQLite compat; faster (no lock waits); simpler code |
| Monolithic job table tracking all orchestration | Separate WorkflowStepRun for per-step tracking | Phase 147 | Enables partial success; Phase 150 can query step-level history |
| Result blob in WorkflowStepRun | Store results in Job table (single source of truth) | Phase 147 | No data duplication; Phase 150 queries Job for logs/output |
| Manual graph traversal for dispatch | networkx DiGraph for predecessor/successor queries | Phase 146+ | O(V+E) complexity instead of O(V²); handles disconnected graphs |
| Cron triggers for all scheduling | Manual trigger + Phase 149 webhook/cron | Phase 147 | Phase 147 is execution only; Phase 149 adds triggers |

**Deprecated/outdated:**
- Custom retry logic in workflows: deferred to Phase 148 (per-step retry)
- Fail-fast mode: not in Phase 147 scope; future addition if needed
- Nested workflows: deferred; Phase 147 assumes flat DAG

---

## Open Questions

1. **Job depth override for workflow-instantiated jobs (ENGINE-02):**
   - Question: Jobs created by WorkflowRun should bypass the 10-level depth limit and allow up to 30 levels (the workflow DAG limit). How is this enforced?
   - What we know: WorkflowRun DAG itself is validated to 30 levels (Phase 146). Individual jobs from scheduled_job don't have a depth counter in the Job table.
   - What's unclear: Where does the 10-level limit live? Is it in JobService.create() or in the node execution? Does a Job created from a workflow step need a special flag?
   - Recommendation: Clarify in planning phase — may be a validation rule in dispatch_next_wave() or a passed-through flag from ScheduledJob to Job.

2. **Cascade cancellation with IF gates (Phase 148 dependency):**
   - Question: In Phase 147 (before IF gates exist), cascade is simple: if predecessor FAILED, cancel dependent. With Phase 148 IF gates, some branches may be conditionally skipped. Should a SKIPPED predecessor trigger cascade or not?
   - What we know: Phase 147 uses only unconditional edges (branch_name is NULL).
   - What's unclear: Phase 148 will add branch_name-based routing. SKIPPED steps should probably not cause cascade (they didn't fail, they were just not taken).
   - Recommendation: Phase 148 research will clarify. For now, treat SKIPPED as a non-terminal state; only FAILED triggers cascade.

3. **Async safety of advance_workflow() in report_result():**
   - Question: Should advance_workflow() be awaited directly in the route handler, or should it be scheduled as a background task with asyncio.create_task()?
   - What we know: report_result() is an async FastAPI route. Awaiting advance_workflow() directly ensures completion before returning HTTP 200.
   - What's unclear: Performance impact if dispatch is slow (many steps); retry semantics if advance fails.
   - Recommendation: Await directly (simple, correct). If dispatch is slow, add logging and timeout. No background task needed — the flow is synchronous and DB-backed.

4. **Parameter override validation (Phase 149 dependency):**
   - Question: When POST /api/workflow-runs supplies parameters={}, how are overrides validated? Must all parameters be supplied, or are defaults from workflow_parameters used?
   - What we know: WorkflowParameter has default_value column.
   - What's unclear: Validation logic (required vs optional fields); error response if missing required param without default.
   - Recommendation: Phase 149 planning will define. For Phase 147, implement basic: if parameter not in body, use default_value; if no default and missing, HTTP 400.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing; vitest for frontend) |
| Config file | pytest.ini (or conftest.py) |
| Quick run command | `cd puppeteer && pytest tests/test_workflow.py -x -v` |
| Full suite command | `cd puppeteer && pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGINE-01 | BFS dispatch creates jobs in topological order | unit | `pytest tests/test_workflow.py::test_dispatch_bfs_order -xvs` | ❌ Wave 0 |
| ENGINE-02 | Workflow depth 30-level limit enforced | unit | `pytest tests/test_workflow.py::test_workflow_depth_limit -xvs` | ✅ Phase 146 |
| ENGINE-03 | Concurrent dispatch uses atomic CAS (no duplicates) | integration | `pytest tests/test_workflow.py::test_concurrent_step_dispatch -xvs` | ❌ Wave 0 |
| ENGINE-04 | WorkflowRun status machine (RUNNING→COMPLETED/PARTIAL/FAILED) | unit | `pytest tests/test_workflow.py::test_run_status_machine -xvs` | ❌ Wave 0 |
| ENGINE-05 | Cascade cancellation on predecessor failure | integration | `pytest tests/test_workflow.py::test_cascade_cancellation -xvs` | ❌ Wave 0 |
| ENGINE-06 | PARTIAL state for mixed success/failure | unit | `pytest tests/test_workflow.py::test_partial_status -xvs` | ❌ Wave 0 |
| ENGINE-07 | Cancel run blocks new dispatches, running jobs complete | integration | `pytest tests/test_workflow.py::test_cancel_run -xvs` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_workflow.py -x -v` (quick unit tests, ~5s)
- **Per wave merge:** `pytest -x` (full suite, ~30s)
- **Phase gate:** Full suite green + POST /api/workflow-runs returns 200 + job dispatch observes job.workflow_step_run_id set

### Wave 0 Gaps

- [ ] `tests/test_workflow.py` — test fixtures for WorkflowRun creation, step dispatch, status transitions (extends Phase 146 fixtures)
- [ ] Test fixtures for concurrent execution (mock multiple report_result calls)
- [ ] Test fixtures for cascade cancellation (multi-level dependency chains)
- [ ] Integration test: POST /api/workflow-runs → check first wave dispatches → check WorkflowStepRun.status = RUNNING
- [ ] Integration test: job completion via POST /work/{guid}/result → check advance_workflow() runs → check next wave dispatches
- [ ] Database migration test: ensure migration_v54.sql applies cleanly to existing Postgres deployments

---

## Sources

### Primary (HIGH confidence)

- **Phase 146 research & codebase:** WorkflowService.validate_dag(), networkx DiGraph construction, SQLAlchemy ORM patterns for Workflow/WorkflowStep/WorkflowEdge
- **Existing JobService:** report_result() integration point, atomic job status updates, execution record creation (lines 1217–1350 in job_service.py)
- **CONTEXT.md (147-CONTEXT.md):** Locked architectural decisions for BFS dispatch, CAS concurrency guards, status machine, cascade cancellation
- **requirements.txt:** networkx >=3.6,<4.0 and asyncpg confirmed in current stack
- **Phase 146 code (workflow_service.py, tests/test_workflow.py):** Established patterns for async service methods, transaction handling, DAG validation

### Secondary (MEDIUM confidence)

- **SQLAlchemy async patterns:** Established in codebase (db.py, job_service.py); atomic UPDATE with WHERE validated via existing usage in job retry logic
- **FastAPI dependency injection:** Confirmed pattern in main.py (require_permission, get_db, etc.)

### Tertiary (LOW confidence)

- Open questions above (depth override, IF gate cascade semantics) — will be clarified in planning phase based on Phase 148 context

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all libraries in requirements.txt; patterns established in Phase 146 + JobService
- Architecture: **HIGH** — CONTEXT.md locks implementation decisions; networkx usage proven in validate_dag()
- Pitfalls: **HIGH** — race conditions and state machine edge cases are standard orchestration gotchas; mitigation patterns clear
- Open questions: **MEDIUM** — will be resolved in planning phase

**Research date:** 2026-04-15  
**Valid until:** 2026-05-15 (30 days — stable architecture, no major fastapi/sqlalchemy/networkx updates expected)

---

**Phase 147 — WorkflowRun Execution Engine Research Complete**
