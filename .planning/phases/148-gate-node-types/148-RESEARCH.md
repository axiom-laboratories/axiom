# Phase 148: Gate Node Types - Research

**Researched:** 2026-04-16
**Domain:** Workflow execution engine — gate node types (IF, AND/JOIN, OR, PARALLEL, SIGNAL_WAIT)
**Confidence:** HIGH

## Summary

Phase 148 adds 5 gate node types to the BFS execution engine established in Phase 147. The phase extends the existing workflow execution model without changing job dispatch, script execution, or the WorkflowRun lifecycle — only gate node handling is new.

Key discovery: The Phase 147 execution engine is already in place with atomic BFS dispatch (`dispatch_next_wave`), CAS guards (`UPDATE WHERE status='PENDING'`), and the `advance_workflow()` hook. Phase 148 will extend `dispatch_next_wave()` to handle structural gate nodes (PARALLEL, AND_JOIN, OR_GATE, IF_GATE, SIGNAL_WAIT) and add gate-specific evaluation logic in `advance_workflow()`. The data model is complete: `WorkflowStep.scheduled_job_id` is already nullable (ready for gate nodes), `config_json` is in place for gate configuration, and `WorkflowStepRun.status` already has the SKIPPED enum value.

**Primary recommendation:** Implement gate evaluation in two phases: (1) Synchronous inline evaluation of IF gate conditions in `advance_workflow()` when an upstream SCRIPT step completes; (2) Extend `dispatch_next_wave()` to handle structural gates (PARALLEL, AND_JOIN, OR_GATE) and SIGNAL_WAIT blocking. Use a helper service (`GateEvaluationService`) to keep gate logic isolated from the main workflow service.

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Gate nodes without scripts:** `WorkflowStep.scheduled_job_id` becomes nullable; NULL = structural gate node. PARALLEL marks its own `WorkflowStepRun` COMPLETED immediately without job dispatch.
- **AND/JOIN predecessor scope:** All steps with direct outgoing edges to the AND/JOIN node.
- **IF gate condition schema:** Stored in `config_json` as `{"branches": {"true": [...conditions...], "false": [...conditions...]}}`. Multiple conditions per branch use AND logic. Supported operators: `eq`, `neq`, `gt`, `lt`, `contains`, `exists`. First matching branch is taken; no match → step FAILED and cascade.
- **result.json transport:** Node populates `ResultReport.result: Optional[Dict]` from `/tmp/axiom/result.json` after execution. Server reads it during `advance_workflow()` for IF gate evaluation.
- **Persistence:** Add `result_json: Mapped[Optional[str]]` (nullable Text column) to `WorkflowStepRun`. Server writes it when processing the result report.
- **AND/JOIN failure semantics:** Fails immediately when any predecessor reaches FAILED or CANCELLED — does not wait for remaining predecessors.
- **SKIPPED distinctness:** SKIPPED (branch not taken) is distinct from CANCELLED (operator-stopped). OR_GATE marks non-triggering branches SKIPPED immediately at OR completion time (eager, not lazy).
- **SIGNAL_WAIT wakeup:** Signal name stored in `config_json` as `{"signal_name": "deploy-approved"}`. Wakeup via direct synchronous `advance_workflow()` call from signal creation endpoint — same pattern as `report_result`. No timeout in Phase 148.
- **Run cancellation:** RUNNING SIGNAL_WAIT steps get status CANCELLED when the run is cancelled (existing cancel_run path handles this).

### Claude's Discretion

- Exact dot-path parsing implementation for IF gate field resolution
- Internal helper method names and factoring within workflow_service.py
- Error message text for unmatched IF gate branches

### Deferred Ideas (OUT OF SCOPE)

- Timeout support for SIGNAL_WAIT — Phase 149+
- UI visualization of gate nodes and branch paths — Phase 150
- Nested workflow invocation as a gate type — out of scope for v23.0
- AND/JOIN partial-failure recovery (retry individual branches) — out of scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GATE-01 | IF gate evaluates conditions against structured output from `/tmp/axiom/result.json` using operators: `eq`, `neq`, `gt`, `lt`, `contains`, `exists` | `ResultReport.result` Pydantic model accepts arbitrary dict; Phase 147 advances on job completion; need to add result_json persistence to WorkflowStepRun and implement dot-path field resolver |
| GATE-02 | IF gate routes to first matching branch; unmatched IF gate marks step FAILED and cascades cancellation downstream | Cascade failure is already implemented in dispatch_next_wave (lines 449-462); need to add IF gate condition evaluation inline in advance_workflow |
| GATE-03 | AND/JOIN gate releases downstream steps only when all incoming branches have completed | Need to identify incoming edges to AND_JOIN node and block dispatch of downstream steps until all predecessors are COMPLETED |
| GATE-04 | OR gate releases downstream steps when any single incoming branch completes | Need to implement eager marking of non-triggering branches SKIPPED at OR gate completion time |
| GATE-05 | Parallel fan-out node dispatches multiple independent downstream branches concurrently | PARALLEL is structural (no job); dispatch_next_wave naturally fans out to all downstream edges via BFS; mark PARALLEL COMPLETED immediately without job dispatch |
| GATE-06 | Signal wait node pauses workflow execution until a named signal is posted via Signal mechanism | Signal table already exists (name PK, payload nullable JSON Text, created_at); need to wire signal creation endpoint to call advance_workflow and implement SIGNAL_WAIT blocking in dispatch_next_wave |

</phase_requirements>

## Standard Stack

### Core Engine
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| FastAPI | current | HTTP API for workflow execution | Phase 147 established |
| SQLAlchemy | 2.0+ async | ORM for workflow + execution models | Phase 147 established |
| networkx | already in requirements | DAG validation and topological traversal | Phase 146 established for cycle detection |
| asyncpg/aiosqlite | current | Async database drivers (Postgres/SQLite) | Phase 147 established |

### Workflow Models (Established)

| Table | Fields Relevant to Phase 148 | Purpose |
|-------|------------------------------|---------|
| `workflow_steps` | `scheduled_job_id` (NOW NULLABLE), `node_type`, `config_json` | Gate node definition; scheduled_job_id=NULL for structural gates |
| `workflow_step_runs` | `status` (PENDING/RUNNING/COMPLETED/FAILED/SKIPPED/CANCELLED), `result_json` (NEW) | Execution state; result_json holds result from node for IF gate evaluation |
| `workflow_runs` | `status` (RUNNING/COMPLETED/PARTIAL/FAILED/CANCELLED) | Run-level status computed by advance_workflow |
| `signals` | `name` (PK), `payload` (JSON), `created_at` | Signal mechanism for SIGNAL_WAIT nodes |
| `workflow_edges` | `branch_name` (NULL for unconditional, non-NULL for IF/OR branch) | Routing edges; Phase 147 reserves NULL for unconditional, Phase 148 uses branch_name for IF/OR branches |

### Supporting Libraries
| Library | Purpose | Required |
|---------|---------|----------|
| `pydantic` | Request/response validation | Phase 147 |
| `json` | Parsing config_json, result_json | Phase 147 |

**Installation:** All libraries already in `puppeteer/requirements.txt` from Phase 147.

## Architecture Patterns

### Established Execution Flow (Phase 147)

```
WorkflowRun created (status=RUNNING)
  ↓
dispatch_next_wave(run_id)
  — For each step with all predecessors COMPLETED:
    — Atomic CAS: UPDATE status PENDING→RUNNING
    — Create Job from ScheduledJob
    — Return list of job GUIDs
  ↓
[Jobs dispatched to nodes, executed]
  ↓
report_result(job_guid, result_report)
  — Mark Job COMPLETED/FAILED
  — Update WorkflowStepRun status
  — Call advance_workflow(run_id)
  ↓
advance_workflow(run_id)
  — dispatch_next_wave(run_id)
  — Check all steps complete → update WorkflowRun status
```

### Phase 148 Extension: Gate Evaluation Points

#### Entry Point 1: `dispatch_next_wave()` — Structural Gate Handling
**When:** During BFS traversal, when checking if a step is eligible to dispatch.
**For gate types:** PARALLEL, AND_JOIN, OR_GATE, SIGNAL_WAIT.

- **PARALLEL (structural):** Skip job creation; mark WorkflowStepRun COMPLETED immediately. BFS naturally fans out to all downstream edges in next iteration.
- **AND_JOIN (synchronization):** Check all incoming edges. Only transition to COMPLETED if all predecessors are COMPLETED. Block downstream dispatch until AND_JOIN is COMPLETED.
- **OR_GATE (fan-in):** When any incoming branch reaches COMPLETED, mark OR_GATE COMPLETED. Simultaneously mark all PENDING step runs on non-triggering branches SKIPPED (eager).
- **SIGNAL_WAIT (blocking):** Create WorkflowStepRun with status RUNNING. Block in RUNNING state until signal arrives. `advance_workflow()` only advances it when signal fires.

#### Entry Point 2: `advance_workflow()` — Condition Evaluation
**When:** After `dispatch_next_wave()`, for each COMPLETED step run.
**For gate types:** IF_GATE, SIGNAL_WAIT wakeup.

- **IF_GATE (branching):** Evaluate conditions in `config_json` against `result_json` of immediate predecessor. Route to matching branch edge, or mark FAILED if no match. Create next-wave steps on selected branch only.
- **SIGNAL_WAIT (wakeup):** When signal is created with matching name, call `advance_workflow()`. Check if any RUNNING SIGNAL_WAIT exists for that name; transition to COMPLETED.

### Recommended Project Structure

Gate logic is isolated into a new service to keep workflow_service.py focused:

```
puppeteer/agent_service/services/
├── workflow_service.py         # CRUD + execute flow (Phase 146-147, extended for gate hooks)
├── gate_evaluation_service.py  # NEW: Gate condition evaluation
└── [existing job_service.py, scheduler_service.py, ...]
```

### Pattern: Dot-Path Field Resolution

IF gate conditions reference fields in result.json using dot-path notation (e.g., `"exit_code"`, `"data.status"`).

**Implementation strategy:**
```python
def resolve_field(data: Dict, path: str) -> Any:
    """
    Resolve dot-path in data dict.
    'exit_code' → data['exit_code']
    'data.status' → data['data']['status']
    Returns (found, value) tuple to handle missing keys gracefully.
    """
    parts = path.split('.')
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return (False, None)  # Path not found
    return (True, current)
```

### Pattern: Condition Evaluation

```python
def evaluate_conditions(conditions: List[Dict], result: Dict) -> bool:
    """
    All conditions in list must match (AND logic).
    condition = {"field": "exit_code", "op": "eq", "value": 0}
    """
    for cond in conditions:
        field = cond['field']
        op = cond['op']
        value = cond['value']
        found, actual = resolve_field(result, field)
        
        if not found:
            return False  # Field missing → condition fails
        
        if op == 'eq' and actual != value:
            return False
        elif op == 'neq' and actual == value:
            return False
        elif op == 'gt' and not (actual > value):
            return False
        elif op == 'lt' and not (actual < value):
            return False
        elif op == 'contains' and value not in str(actual):
            return False
        elif op == 'exists' and actual is None:
            return False
    return True  # All conditions matched
```

### Pattern: Gate Node Routing in `advance_workflow()`

```python
async def advance_workflow(run_id: str, db: AsyncSession) -> None:
    # ... (existing dispatch_next_wave call)
    
    # NEW: Evaluate gates after dispatch
    await evaluate_gates(run_id, db)
    
    # ... (existing completion check)

async def evaluate_gates(run_id: str, db: AsyncSession) -> None:
    """
    Iterate through all COMPLETED step runs in this run.
    For each step with node_type in {IF_GATE, SIGNAL_WAIT}:
      — Evaluate condition/signal
      — Mark downstream branches SKIPPED or dispatch next wave
    """
    # Get all COMPLETED step runs
    stmt = select(WorkflowStepRun).where(
        and_(
            WorkflowStepRun.workflow_run_id == run_id,
            WorkflowStepRun.status == "COMPLETED"
        )
    )
    completed_runs = (await db.execute(stmt)).scalars().all()
    
    for sr in completed_runs:
        step = await db.get(WorkflowStep, sr.workflow_step_id)
        if step.node_type == "IF_GATE":
            await handle_if_gate(sr, step, run_id, db)
        elif step.node_type == "SIGNAL_WAIT":
            # Wakeup handled by signal creation endpoint
            pass
```

### Pattern: CAS for Gate Status Transitions

Apply the CAS pattern from Phase 147 to gate nodes:

```python
# When transitioning a gate to COMPLETED
stmt_update = (
    update(WorkflowStepRun)
    .where(
        and_(
            WorkflowStepRun.id == step_run_id,
            WorkflowStepRun.status == "RUNNING"  # or "PENDING" for some gates
        )
    )
    .values(status="COMPLETED", completed_at=datetime.utcnow())
)
result = await db.execute(stmt_update)

if result.rowcount == 0:
    # Another process already completed this gate
    return
```

### Anti-Patterns to Avoid

- **Lazy SKIPPED marking (OR_GATE):** Do NOT mark non-triggering branches SKIPPED lazily (only when they reach dispatch time). SKIPPED must be marked eagerly at OR gate completion to ensure step runs are finalized and downstream never tries to dispatch them.
- **Blocking on signal with polling:** Do NOT add a polling loop waiting for signals. Instead, inject `advance_workflow()` into the signal creation endpoint synchronously.
- **Hardcoding gate logic in dispatch_next_wave():** Refactor gate handling into separate methods (`handle_parallel()`, `handle_and_join()`, etc.) for clarity and testability.
- **Ignoring dot-path edge cases:** Do NOT silently return None for missing paths. Distinguish between "path exists with value None" (which may be a valid condition match) and "path does not exist" (condition fails).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON condition evaluation | Regex-based parsing of condition strings | Pydantic model + dict-based condition structure | Avoids parsing fragility; reuse Pydantic validation |
| Dot-path resolution | Manual recursive descent with try/catch blocks | Encapsulated `resolve_field()` helper in GateEvaluationService | Reusable, testable, handles edge cases consistently |
| Signal-to-workflow linking | New signal-subscription table + polling job | Direct `advance_workflow()` call from signal creation endpoint | Keeps signal table schema simple; synchronous is faster than polling |
| Topological ordering for gate logic | Manual depth-first traversal of edges | Reuse networkx graph from Phase 147 validation | NetworkX is battle-tested; dispatch_next_wave already uses it for BFS |
| AND_JOIN predecessor detection | Query all workflow edges every time | Compute predecessor set once per run, cache in-memory | Reduces DB queries; AND_JOIN may be evaluated multiple times per run |

**Key insight:** Gate logic is complex but should remain close to the existing BFS dispatch engine. Isolation via a separate service prevents workflow_service.py from becoming unmaintainable, but gates must hook into the same atomic transaction model (CAS guards, flush/commit pattern) used by Phase 147.

## Common Pitfalls

### Pitfall 1: IF Gate Condition Mismatch Handling
**What goes wrong:** IF gate has multiple branches but none match the result → step hangs or causes inconsistent state.
**Why it happens:** Result doesn't contain expected field, or condition logic has typo.
**How to avoid:** 
- Validate condition schema in `config_json` at workflow creation time (same place as DAG validation).
- In `advance_workflow()`, if no branch matches, immediately mark IF_GATE step FAILED and cascade.
- Log unmatched IF gate with full result and condition set for debugging.
**Warning signs:** WorkflowRun status stuck in RUNNING with no PENDING steps; IF_GATE step run in COMPLETED state but no downstream dispatch.

### Pitfall 2: AND_JOIN Waits for Dead Predecessors
**What goes wrong:** One predecessor FAILED → AND_JOIN waits forever for other predecessors to complete, even though the run will never succeed.
**Why it happens:** AND_JOIN completion logic checks "all COMPLETED" but doesn't check for FAILED/CANCELLED predecessors.
**How to avoid:** 
- In dispatch_next_wave(), when evaluating AND_JOIN eligibility, check if ANY predecessor is FAILED or CANCELLED → immediately mark AND_JOIN FAILED and cascade.
- This mirrors the existing cascade failure pattern (lines 449-462 in workflow_service.py).
**Warning signs:** AND_JOIN step stuck in PENDING with one predecessor FAILED, others PENDING.

### Pitfall 3: SIGNAL_WAIT Never Wakes Up
**What goes wrong:** SIGNAL_WAIT step blocks forever; signal is created but step remains RUNNING.
**Why it happens:** Signal creation endpoint doesn't call `advance_workflow()`, or signal name doesn't match exactly (case sensitivity, whitespace).
**How to avoid:** 
- Signal creation endpoint MUST call `await workflow_service.advance_workflow()` after persisting signal.
- Store signal name in lowercase in config_json and DB (or enforce case-insensitive comparison).
- Return error (HTTP 400) if signal name contains whitespace.
**Warning signs:** Signal row created in DB; WorkflowRun status stuck RUNNING with SIGNAL_WAIT step in RUNNING state.

### Pitfall 4: OR_GATE Not Eagerly Marking Non-Triggering Branches SKIPPED
**What goes wrong:** OR_GATE completes (triggers one branch); other non-triggering steps are still PENDING and later dispatch tries to dispatch them.
**Why it happens:** SKIPPED marking deferred to lazy dispatch time (only when non-triggering steps reach eligibility).
**How to avoid:** 
- When OR_GATE reaches COMPLETED status, immediately iterate all outgoing edges.
- For edges NOT on the triggered branch, query all WorkflowStepRuns on that branch path and mark SKIPPED.
- Use CAS pattern to ensure atomicity.
**Warning signs:** OR_GATE branch not taken, but steps on that branch show as PENDING in run history.

### Pitfall 5: Null scheduled_job_id Migration Breaks Existing Code
**What goes wrong:** Phase 148 makes scheduled_job_id nullable; existing code assumes it's always non-null → KeyError or FK constraint failures.
**Why it happens:** Code paths that query/insert WorkflowSteps don't check for NULL scheduled_job_id.
**How to avoid:** 
- Add migration SQL: `ALTER TABLE workflow_steps ALTER COLUMN scheduled_job_id DROP NOT NULL;`
- Update WorkflowStepCreate Pydantic model to make scheduled_job_id optional.
- In dispatch_next_wave(), skip job creation if scheduled_job_id is NULL and node_type is a structural gate.
- In workflow creation/update, validate that SCRIPT steps MUST have scheduled_job_id, gate steps MUST have NULL scheduled_job_id.
**Warning signs:** Database migration fails with constraint violation; WorkflowStepCreate fails on creation of gate node.

### Pitfall 6: Result JSON Serialization/Deserialization
**What goes wrong:** Node sends `/tmp/axiom/result.json` as valid JSON; server reads it, but comparison operators fail due to type mismatch (string "123" vs int 123).
**Why it happens:** JSON deserialization is lenient; conditions are strict about types.
**How to avoid:** 
- Node documentation MUST specify that result.json values are JSON-native types (strings, numbers, booleans, arrays, objects).
- Conditions in config_json MUST include type coercion hint if needed (e.g., `{"op": "eq", "value": 123, "type": "int"}`), OR condition evaluator tries type coercion on mismatch.
- Add test cases for string/int/float comparisons with operators (gt, lt, eq).
**Warning signs:** Condition works in unit test but fails at runtime with type mismatch error.

### Pitfall 7: Cascade Failure During Gate Evaluation
**What goes wrong:** IF_GATE is marked FAILED → should cascade to all downstream steps, but cascade is incomplete (only marks direct children CANCELLED, misses grandchildren).
**Why it happens:** Cascade failure only checks immediate predecessors; doesn't recursively mark downstream.
**How to avoid:** 
- Reuse existing cascade logic from dispatch_next_wave() (lines 449-462): for each step, check predecessors; if any FAILED/CANCELLED, mark self CANCELLED.
- This is transitive: if step A FAILS, step B (child of A) marks CANCELLED; if B is then evaluated, its children mark CANCELLED.
- Verify cascade in tests with multi-level IF_GATE failure scenarios.
**Warning signs:** IF_GATE marks FAILED; one-level-deep downstream steps CANCELLED, but two-level-deep steps remain PENDING.

## Code Examples

Verified patterns from Phase 147 codebase and Phase 148 CONTEXT.md decisions.

### Example 1: Dispatch Structural Gate Nodes (PARALLEL, AND_JOIN, OR_GATE)

```python
# Source: workflow_service.py dispatch_next_wave() — extending Phase 147
async def dispatch_next_wave(self, run_id: str, db: AsyncSession) -> List[str]:
    """Existing pattern from Phase 147; extend to handle gates."""
    
    # ... (existing root setup: fetch run, workflow, build graph, create step_runs) ...
    
    for step in workflow.steps:
        # Create step run if missing
        if step.id not in step_run_map:
            sr = WorkflowStepRun(...)
            db.add(sr)
            await db.flush()
            step_run_map[step.id] = sr
        
        # Check predecessors for failure cascade
        # ... (existing lines 449-462) ...
        
        # NEW: Handle structural gates
        if step.node_type == "PARALLEL":
            # PARALLEL is virtual; mark COMPLETED immediately
            stmt = (
                update(WorkflowStepRun)
                .where(and_(
                    WorkflowStepRun.id == sr.id,
                    WorkflowStepRun.status == "PENDING"
                ))
                .values(status="COMPLETED", completed_at=datetime.utcnow())
            )
            await db.execute(stmt)
            continue  # Skip job creation; next wave will dispatch downstream
        
        elif step.node_type in ("AND_JOIN", "OR_GATE"):
            # Check if all incoming predecessors complete
            predecessors = list(G.predecessors(step.id))
            if len(predecessors) > 0:
                all_complete = all(
                    step_run_map.get(p_id) and step_run_map.get(p_id).status == "COMPLETED"
                    for p_id in predecessors
                )
                if not all_complete:
                    continue  # Wait for predecessors
            
            # All predecessors done: mark this gate COMPLETED
            stmt = (
                update(WorkflowStepRun)
                .where(and_(
                    WorkflowStepRun.id == sr.id,
                    WorkflowStepRun.status == "PENDING"
                ))
                .values(status="COMPLETED", completed_at=datetime.utcnow())
            )
            await db.execute(stmt)
            continue  # Skip job creation
        
        elif step.node_type == "SIGNAL_WAIT":
            # Mark RUNNING; will unblock only when signal is created
            stmt = (
                update(WorkflowStepRun)
                .where(and_(
                    WorkflowStepRun.id == sr.id,
                    WorkflowStepRun.status == "PENDING"
                ))
                .values(status="RUNNING", started_at=datetime.utcnow())
            )
            await db.execute(stmt)
            continue  # Skip job creation; signal endpoint will advance
        
        # Existing logic for SCRIPT (and future other job-based steps)
        # ... (lines 478-559 in Phase 147) ...
        
        new_jobs.append(job_guid)
    
    await db.commit()
    return new_jobs
```

### Example 2: IF Gate Condition Evaluation

```python
# Source: gate_evaluation_service.py (NEW service)
class GateEvaluationService:
    @staticmethod
    def resolve_field(data: Dict, path: str) -> Tuple[bool, Any]:
        """
        Resolve dot-path in data. e.g., "exit_code", "data.status"
        Returns (found, value).
        """
        parts = path.split('.')
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return (False, None)
        return (True, current)
    
    @staticmethod
    def evaluate_condition(condition: Dict, result: Dict) -> bool:
        """
        Single condition: {"field": "...", "op": "eq|neq|gt|lt|contains|exists", "value": ...}
        """
        field = condition.get('field')
        op = condition.get('op')
        value = condition.get('value')
        
        if not field or not op:
            return False
        
        found, actual = GateEvaluationService.resolve_field(result, field)
        
        if op == 'exists':
            return found  # exists checks field presence
        
        if not found:
            return False  # Field missing fails all other operators
        
        try:
            if op == 'eq':
                return actual == value
            elif op == 'neq':
                return actual != value
            elif op == 'gt':
                return actual > value
            elif op == 'lt':
                return actual < value
            elif op == 'contains':
                return str(value) in str(actual)
            else:
                return False
        except TypeError:
            return False  # Type mismatch on comparison
    
    @staticmethod
    def evaluate_conditions(conditions: List[Dict], result: Dict) -> bool:
        """All conditions must match (AND logic)."""
        return all(
            GateEvaluationService.evaluate_condition(cond, result)
            for cond in conditions
        )
    
    @staticmethod
    def evaluate_if_gate(config_json: str, result: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Evaluate IF gate.
        config_json = '{"branches": {"true": [...], "false": [...]}}'
        Returns (branch_taken, error_message).
        branch_taken in ("true", "false"), error_message if no match.
        """
        try:
            config = json.loads(config_json)
        except json.JSONDecodeError:
            return None, "Invalid config_json"
        
        branches = config.get('branches', {})
        
        # Evaluate "true" branch first (convention: primary branch)
        for branch_name in ["true", "false"]:
            conditions = branches.get(branch_name, [])
            if GateEvaluationService.evaluate_conditions(conditions, result):
                return branch_name, None
        
        # No match
        return None, f"No IF gate branch matched result {result}"

# Usage in advance_workflow():
async def handle_if_gate_completion(
    step_run: WorkflowStepRun,
    step: WorkflowStep,
    run_id: str,
    db: AsyncSession
):
    """Called when IF_GATE predecessor completes."""
    
    # Get result from predecessor's WorkflowStepRun.result_json
    # (result_json populated by report_result endpoint)
    if not step_run.result_json:
        # Predecessor had no result (shouldn't happen for SCRIPT nodes)
        await mark_step_failed(step_run.id, "No result from predecessor", db)
        return
    
    result = json.loads(step_run.result_json)
    
    # Evaluate IF gate
    branch_taken, error = GateEvaluationService.evaluate_if_gate(
        step.config_json, result
    )
    
    if branch_taken is None:
        # No branch matched
        await mark_step_failed(step_run.id, error or "No matching branch", db)
        return
    
    # Branch matched: find outgoing edge with matching branch_name
    # Downstream dispatch will pick it up in next dispatch_next_wave() call
    # (via BFS on edges with matching branch_name)
```

### Example 3: Signal Creation Triggers Workflow Advance

```python
# Source: main.py — signal creation endpoint (Phase 149 scope, but gate-aware)
@app.post("/api/signals/{signal_name}")
async def create_signal(
    signal_name: str,
    body: SignalFire,
    current_user: User = Depends(require_permission("workflows:trigger")),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a signal and wake up any SIGNAL_WAIT steps waiting on this signal.
    """
    # Persist signal
    signal = Signal(
        name=signal_name,
        payload=json.dumps(body.payload) if body.payload else None,
        created_at=datetime.utcnow()
    )
    db.add(signal)
    await db.commit()
    
    # NEW: Wake up SIGNAL_WAIT steps
    # Find all RUNNING SIGNAL_WAIT step runs waiting on this signal
    stmt = select(WorkflowStepRun).join(
        WorkflowStep, WorkflowStepRun.workflow_step_id == WorkflowStep.id
    ).where(
        and_(
            WorkflowStep.node_type == "SIGNAL_WAIT",
            WorkflowStepRun.status == "RUNNING"
        )
    )
    waiting_runs = (await db.execute(stmt)).scalars().all()
    
    # Filter to runs waiting on this specific signal_name
    for sr in waiting_runs:
        step = await db.get(WorkflowStep, sr.workflow_step_id)
        config = json.loads(step.config_json or '{}')
        if config.get('signal_name') == signal_name:
            # Mark SIGNAL_WAIT as COMPLETED
            sr.status = "COMPLETED"
            sr.completed_at = datetime.utcnow()
            
            # Advance the run (dispatch downstream)
            await workflow_service.advance_workflow(sr.workflow_run_id, db)
    
    await db.commit()
    
    return {"signal_name": signal_name, "status": "created"}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Simple linear workflows | DAG with gates (Phase 148) | v23.0 | Enables branching logic, parallel fan-out, synchronization |
| Manual step creation | BFS dispatch with atomic CAS (Phase 147) | v23.0 | Prevents duplicate dispatch; atomicity on concurrent completions |
| Branch selection via code | Declarative condition evaluation (Phase 148) | v23.0 | Decouples workflow definition from execution logic; conditions are data |
| Polling for signal wakeup | Synchronous signal endpoint call (Phase 148) | v23.0 | Faster, simpler; no polling overhead |

**Deprecated/outdated:**
- Old approach: Manual state machine in a single monolithic service. Current: Service layer separation (workflow_service + gate_evaluation_service).

## Open Questions

1. **Backward compatibility for nullable scheduled_job_id:** Existing workflows (Phase 146-147) have scheduled_job_id non-nullable. Migration SQL will handle the schema change, but should we add a validation flag to require backward-compatible workflows to explicitly opt-in to gate node support? Or allow gates in all workflows?
   - **Recommendation:** Allow gates in all new workflows (no flag). For existing workflows, gate nodes can't be added (safe, avoids breaking existing definitions). Migrations update the schema but don't change existing workflow data.

2. **Order of branch evaluation in IF_GATE:** If both "true" and "false" branches have matching conditions, which is taken?
   - **Recommendation:** Evaluate "true" first (convention); if it matches, take it. Only if "true" doesn't match, try "false". Prevents ambiguity.

3. **AND_JOIN with only one predecessor:** Is a gate with one incoming edge valid, or should we reject it?
   - **Recommendation:** Allow it; it's a no-op synchronization point. Acts like a pass-through.

4. **OR_GATE with zero incoming edges:** What happens if OR_GATE has no predecessors (root-level gate)?
   - **Recommendation:** Treat as immediate fan-out (no predecessors = all complete). Mark COMPLETED immediately in dispatch_next_wave().

5. **PARALLEL node with no outgoing edges:** Valid structure or error?
   - **Recommendation:** Allow it; it's a dead end (absorbs a branch). No error.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (vitest for frontend) |
| Config file | `puppeteer/pytest.ini` |
| Quick run command | `cd puppeteer && pytest tests/test_workflow.py -xvs` |
| Full suite command | `cd puppeteer && pytest tests/test_workflow*.py -xvs` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GATE-01 | IF gate evaluates operators (eq, neq, gt, lt, contains, exists) against result.json | unit | `pytest tests/test_gate_evaluation.py::test_if_gate_operators -xvs` | ❌ Wave 0 |
| GATE-02 | IF gate unmatched branch marks step FAILED + cascades | unit | `pytest tests/test_gate_evaluation.py::test_if_gate_no_match_cascades -xvs` | ❌ Wave 0 |
| GATE-03 | AND_JOIN blocks downstream until all predecessors complete | integration | `pytest tests/test_workflow_execution.py::test_and_join_synchronization -xvs` | ✅ (Phase 147) |
| GATE-04 | OR_GATE routes to triggered branch; non-triggering branches SKIPPED | integration | `pytest tests/test_workflow_execution.py::test_or_gate_branch_skip -xvs` | ❌ Wave 0 |
| GATE-05 | PARALLEL marks immediate COMPLETED; fans out downstream | integration | `pytest tests/test_workflow_execution.py::test_parallel_fan_out -xvs` | ❌ Wave 0 |
| GATE-06 | SIGNAL_WAIT blocks; signal creation wakes it up | integration | `pytest tests/test_workflow_execution.py::test_signal_wait_wakeup -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_workflow.py -xvs` (quick unit tests only)
- **Per wave merge:** `pytest tests/test_workflow*.py -xvs` (all workflow tests including integration)
- **Phase gate:** Full suite + manual E2E test of one gate node type against Docker stack

### Wave 0 Gaps
- [ ] `tests/test_gate_evaluation.py` — unit tests for GateEvaluationService (resolve_field, evaluate_condition, evaluate_if_gate)
- [ ] `tests/test_workflow_execution.py` — extended with OR_GATE, PARALLEL, SIGNAL_WAIT integration tests
- [ ] Fixture: `conftest.py` helper to create gate node workflows (templates for IF, AND, OR, PARALLEL, SIGNAL_WAIT)
- [ ] Migration: `migration_v14.sql` to make `workflow_steps.scheduled_job_id` nullable and add `workflow_step_runs.result_json` column

## Sources

### Primary (HIGH confidence)

- **Phase 147 codebase** — `puppeteer/agent_service/services/workflow_service.py` (dispatch_next_wave, advance_workflow, BFS patterns, CAS guards)
- **Phase 146-147 DB models** — `puppeteer/agent_service/db.py` (Workflow*, WorkflowStepRun, Signal, Job tables)
- **Phase 148 CONTEXT.md** — Locked decisions, gate node semantics, config_json schema, result.json transport
- **Phase 147 REQUIREMENTS.md** — ENGINE-01 through ENGINE-07 (execution engine guarantees)
- **CLAUDE.md** — Architecture section describes workflow system, atomicity patterns, database schema management

### Secondary (MEDIUM confidence)

- **Phase 147 test suite** — `puppeteer/tests/test_workflow_execution.py` (BFS dispatch patterns, cascade failure, status transitions)
- **Phase 146 test suite** — `puppeteer/tests/test_workflow.py` (workflow CRUD, DAG validation, networkx usage)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries already in use (networkx, SQLAlchemy, asyncpg, Pydantic)
- Architecture: HIGH — Phase 147 execution engine is complete and tested; gates are extensions to that model
- Gate semantics: HIGH — Locked decisions in CONTEXT.md are explicit and detailed
- Pitfalls: HIGH — Derived from CAS patterns in Phase 147 and common gate orchestration issues
- Testing gaps: MEDIUM — Test frameworks exist; need to write gate-specific test cases

**Research date:** 2026-04-16
**Valid until:** 2026-05-07 (21 days — gate semantics stable, engine changes low-risk)

---

**RESEARCH COMPLETE.** Planner can now design Phase 148 plans with confidence. Gate node implementation extends the Phase 147 BFS engine via `dispatch_next_wave()` and `advance_workflow()` hooks. Key deliverables: GateEvaluationService for condition logic, schema migration for nullable scheduled_job_id + result_json column, signal endpoint integration, comprehensive test coverage for all 5 gate types.
