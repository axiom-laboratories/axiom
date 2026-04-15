# Phase 146: Workflow Data Model - Research

**Researched:** 2026-04-15
**Domain:** Database schema design, DAG validation, normalized relational storage
**Confidence:** HIGH

## Summary

Phase 146 delivers the complete data layer and API surface for Workflow definitions in Master of Puppets. The phase introduces 5 new database tables (normalized, no JSON blobs) with full CRUD API, cycle detection via networkx, depth validation (max 30 levels), and a Save-as-New endpoint that atomically clones workflows and pauses cron schedules. The scope is intentionally bounded: data model and validation only. Execution logic (Phase 147), gate node types (Phase 148), triggers and parameters (Phase 149), and UI (Phases 150–151) are deferred.

The implementation follows established project patterns: SQLAlchemy ORM for models, Pydantic for request/response shapes, FastAPI for routes, and networkx for graph algorithms. HTTP 422 is used for validation errors (structured error bodies with cycle_path and depth info), HTTP 409 for business logic conflicts (active runs blocking delete). All IDs are UUIDs stored as strings, consistent with existing Job and ScheduledJob models.

**Primary recommendation:** Build 5 new ORM models (Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter, optional WebhookNonce for Phase 149), add networkx to requirements.txt, implement workflow_service.py with cycle detection + depth calculation, create 8–10 API routes in main.py, and write migration_v53.sql for existing Postgres deployments.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Normalized tables only** — `workflows` table has NO `definition_json` blob; source of truth is `workflow_steps` + `workflow_edges` tables
- **Storage strategy** — Phase 147 BFS engine queries `workflow_steps`/`workflow_edges` directly; no JSON parsing at dispatch time
- **API contract** — Full-graph in one request: POST/PUT sends complete steps[], edges[], parameters[] array; GET returns nested graph
- **Save-as-New (fork)** — Atomically clones all steps/edges/parameters into new Workflow AND sets `source_workflow.is_paused = true`
- **Validation errors** — HTTP 422 with structured error body (CYCLE_DETECTED, DEPTH_LIMIT_EXCEEDED, INVALID_EDGE_REFERENCE); HTTP 409 for active runs
- **Max depth** — 30 levels enforced (not configurable)
- **node_type** — Free string column (SCRIPT allowed; IF_GATE, AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT added in Phase 148); validated at service layer (not DB CHECK)
- **All IDs** — UUIDs as strings (consistent with Job.id, ScheduledJob.id)
- **Graph library** — networkx for cycle detection and depth calculation
- **Next migration** — migration_v53.sql (follows migration_v52.sql)

### Claude's Discretion
- Exact Pydantic model names and field aliases
- Internal networkx implementation details (DiGraph vs MultiDiGraph choice)
- Whether workflow_service.py lives under `services/` or a new `workflow/` sub-package
- Test file structure and fixtures
- Migration file naming

### Deferred Ideas (OUT OF SCOPE)
- WorkflowRun execution, BFS dispatch, status machine — Phase 147
- IF/AND/OR/Parallel/Signal gate node types — Phase 148
- Cron trigger scheduling, webhook trigger config — Phase 149
- DAG visualization, run history UI — Phase 150
- Visual drag-drop canvas editor — Phase 151

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WORKFLOW-01 | User can create a named Workflow composed of ScheduledJob steps connected by dependency edges | ORM models (Workflow, WorkflowStep, WorkflowEdge), POST /api/workflows route with full-graph contract, signature validation (steps must reference valid ScheduledJob IDs) |
| WORKFLOW-02 | User can list all Workflow definitions with step count, trigger config, and last-run status | GET /api/workflows list endpoint returning metadata + step_count, last_run_status; single DB query or JOIN pattern |
| WORKFLOW-03 | User can update a Workflow definition; system re-validates DAG (cycle detection, depth check) | PUT /api/workflows/{id} with full-graph replace, atomic delete/insert of steps/edges/parameters, networkx cycle detection (nx.is_directed_acyclic_graph, nx.simple_cycles), depth calculation via longest_path or BFS-based traversal |
| WORKFLOW-04 | User can delete a Workflow definition (blocked if active WorkflowRuns exist) | DELETE /api/workflows/{id} with check for active runs (WorkflowRun.status != COMPLETED/FAILED), HTTP 409 response if blocked |
| WORKFLOW-05 | System auto-pauses an existing cron schedule when user executes "Save as New" | POST /api/workflows/{id}/fork atomically: (1) clone all steps/edges/parameters into new Workflow, (2) set source_workflow.is_paused = true, returns full new Workflow with same response shape as GET |
</phase_requirements>

## Standard Stack

### Core Libraries
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | (existing, 2.x async) | ORM and relational mapping | Already used for Job, ScheduledJob, Node; create_all at startup handles new tables automatically |
| Pydantic | (existing, 2.x) | Request/response validation | Project standard for API contracts; field_validator and model_validator for complex validation |
| FastAPI | (existing, 0.10x) | HTTP framework | Project standard; Depends() for auth, HTTPException for error responses |
| networkx | 3.6.1 (ADD to requirements.txt) | Graph algorithms for cycle detection + depth calculation | De facto standard for DAG validation in Python; lightweight, well-tested, no external dependencies; provides `is_directed_acyclic_graph()`, `simple_cycles()`, `longest_path()` |

### Supporting Libraries (Already Present)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncpg | (existing) | Async Postgres driver | DB access; already configured in `engine` |
| aiosqlite | (existing) | Async SQLite for dev | Local testing without Postgres |
| cryptography | (existing) | Ed25519 for job signing | Referenced in ScheduledJob model (signature_id, signature_payload) |

### Installation
```bash
# Add to puppeteer/requirements.txt
networkx>=3.6,<4.0
```

## Architecture Patterns

### Recommended Project Structure

New files to create:
```
puppeteer/agent_service/
├── db.py                          # Add 5 ORM classes (Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter, optional WebhookNonce)
├── models.py                      # Add Pydantic request/response models (WorkflowCreate, WorkflowResponse, WorkflowValidationError, etc.)
├── services/
│   └── workflow_service.py        # New: CRUD, validation, fork logic (300–400 lines)
├── main.py                        # Add ~8–10 workflow routes
├── deps.py                        # (existing) authorization helpers — workflow routes use require_permission("workflows:write")
└── (migration_v53.sql)            # New: 5 CREATE TABLE statements
```

### Pattern 1: Full-Graph API Contract

**What:** API requests/responses include the entire DAG as nested arrays (steps, edges, parameters) in a single request/response.

**When to use:** Creating/updating workflows. Caller owns the full graph definition and submits it atomically. Server validates before write.

**Example (from CONTEXT.md):**
```python
# POST /api/workflows
{
    "name": "data-pipeline",
    "steps": [
        {"id": "step1", "scheduled_job_id": "job-uuid-1", "node_type": "SCRIPT", "config_json": "{}"},
        {"id": "step2", "scheduled_job_id": "job-uuid-2", "node_type": "SCRIPT", "config_json": "{}"}
    ],
    "edges": [
        {"from_step_id": "step1", "to_step_id": "step2", "branch_name": null}
    ],
    "parameters": [
        {"name": "dataset", "type": "string", "default_value": "prod"}
    ]
}

# GET /api/workflows/{id}
# Response: same shape (full graph always returned)
```

**Atomic writes:** In `workflow_service.update()`, wrap DELETE + INSERT in a transaction:
```python
async with db.transaction():
    await db.execute(delete(WorkflowEdge).where(...))
    await db.execute(delete(WorkflowStep).where(...))
    # Insert new ones
```

### Pattern 2: Cycle Detection with networkx

**What:** Build a DiGraph from submitted steps/edges, then check acyclicity.

**When to use:** Before saving POST /api/workflows or PUT /api/workflows/{id}, or when calling POST /api/workflows/validate.

**Example (source: [networkx DAG reference](https://networkx.org/documentation/stable/reference/algorithms/dag.html)):**
```python
import networkx as nx

def validate_dag(steps: List[WorkflowStep], edges: List[WorkflowEdge]) -> Tuple[bool, Optional[str]]:
    """Check for cycles. Returns (is_valid, error_message)."""
    # Build graph
    G = nx.DiGraph()
    for step in steps:
        G.add_node(step.id)
    for edge in edges:
        G.add_edge(edge.from_step_id, edge.to_step_id)
    
    # Check acyclicity
    if not nx.is_directed_acyclic_graph(G):
        # Find a cycle to report
        try:
            cycle = next(nx.simple_cycles(G))
            return False, {
                "error": "CYCLE_DETECTED",
                "cycle_path": cycle
            }
        except StopIteration:
            return False, {"error": "CYCLE_DETECTED", "cycle_path": []}
    
    return True, None
```

**Confidence:** HIGH — networkx 3.6.1 is current and widely adopted; these functions are stable.

### Pattern 3: Depth Calculation (Max 30 Levels)

**What:** Traverse the DAG from all root nodes (in-degree == 0) and calculate the longest path to any node.

**When to use:** Validation before save; reject if max_depth > 30.

**Example (source: [DAG algorithm patterns](https://www.mungingdata.com/python/dag-directed-acyclic-graph-networkx/)):**
```python
def calculate_max_depth(G: nx.DiGraph) -> int:
    """Calculate the longest path length in a DAG (number of edges)."""
    if len(G) == 0:
        return 0
    
    # networkx.dag_longest_path returns the longest path as a list of nodes
    # path length = number of edges = len(path) - 1
    longest_path = nx.dag_longest_path(G)
    return len(longest_path) - 1 if longest_path else 0

def validate_depth(steps, edges, max_depth=30):
    """Check depth limit."""
    G = nx.DiGraph()
    for step in steps:
        G.add_node(step.id)
    for edge in edges:
        G.add_edge(edge.from_step_id, edge.to_step_id)
    
    depth = calculate_max_depth(G)
    if depth > max_depth:
        return False, {
            "error": "DEPTH_LIMIT_EXCEEDED",
            "max_depth": max_depth,
            "actual_depth": depth
        }
    return True, None
```

**Confidence:** HIGH — networkx.dag_longest_path is documented and O(V+E).

### Pattern 4: Referential Integrity (All Edges Reference Valid Steps)

**What:** Before accepting edges, verify every from_step_id and to_step_id exists in the submitted steps array.

**When to use:** POST /api/workflows, PUT /api/workflows/{id}, POST /api/workflows/validate.

**Example:**
```python
def validate_edge_references(steps: List[WorkflowStep], edges: List[WorkflowEdge]):
    """Ensure all edge endpoints reference valid steps."""
    step_ids = {s.id for s in steps}
    for edge in edges:
        if edge.from_step_id not in step_ids or edge.to_step_id not in step_ids:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "INVALID_EDGE_REFERENCE",
                    "edge": {
                        "from_step_id": edge.from_step_id,
                        "to_step_id": edge.to_step_id
                    }
                }
            )
```

### Pattern 5: Save-as-New (Fork with Cron Pause)

**What:** POST /api/workflows/{id}/fork clones all steps/edges/parameters into a new Workflow and sets source_workflow.is_paused = true.

**When to use:** User wants to "save as new" from an existing scheduled workflow without duplicating cron runs.

**Example (atomicity critical):**
```python
async def fork_workflow(workflow_id: str, new_name: str, db: AsyncSession, current_user: User):
    """Clone all steps/edges/params and pause source cron."""
    async with db.begin_nested():
        # Load source
        source = await db.get(Workflow, workflow_id)
        if not source:
            raise HTTPException(404)
        
        # Create new workflow
        new_wf = Workflow(id=str(uuid4()), name=new_name, created_by=current_user.username, ...)
        db.add(new_wf)
        
        # Clone steps
        for step in source.steps:
            new_step = WorkflowStep(
                id=str(uuid4()),
                workflow_id=new_wf.id,
                scheduled_job_id=step.scheduled_job_id,
                node_type=step.node_type,
                config_json=step.config_json
            )
            db.add(new_step)
        
        # Clone edges (map old step IDs to new ones)
        step_mapping = {old.id: new.id for old, new in zip(source.steps, new_wf.steps)}
        for edge in source.edges:
            new_edge = WorkflowEdge(
                id=str(uuid4()),
                workflow_id=new_wf.id,
                from_step_id=step_mapping[edge.from_step_id],
                to_step_id=step_mapping[edge.to_step_id],
                branch_name=edge.branch_name
            )
            db.add(new_edge)
        
        # Clone parameters
        for param in source.parameters:
            new_param = WorkflowParameter(
                id=str(uuid4()),
                workflow_id=new_wf.id,
                name=param.name,
                type=param.type,
                default_value=param.default_value
            )
            db.add(new_param)
        
        # Pause source cron
        source.is_paused = True
        
        await db.commit()
    
    return new_wf
```

**Confidence:** HIGH — pattern follows existing `scheduler_service` patterns (is_active flag, explicit state transitions).

### Anti-Patterns to Avoid

- **Storing definition_json blob alongside normalized tables** — Creates sync risk and contradicts Phase 147 query patterns (BFS engine reads tables directly, not JSON)
- **Treating node_type as enum with DB CHECK constraint** — Locks schema to Phase 146 knowledge; Phase 148 cannot add new gate types without migration. Use service-layer validation instead.
- **Accepting partial graph updates (only steps, only edges)** — Opens validation gaps and makes transaction logic complex. Full-graph contract is cleaner.
- **Calculating depth on-the-fly in main.py during validation** — Couple request handling to algorithm logic. Delegate to workflow_service with clear contract.
- **Storing cycle detection result in a DB column** — Anti-pattern; cycles are invalid state, not a valid state to persist. Reject at request time.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cycle detection in directed graphs | Custom DFS with cycle tracking | `networkx.is_directed_acyclic_graph()` + `networkx.simple_cycles()` | networkx handles all edge cases (self-loops, multiple paths, unreachable nodes); home-brewed DFS will have bugs (off-by-one depth, missed cycles in disconnected subgraphs) |
| DAG longest-path (depth) calculation | Custom Dijkstra or BFS | `networkx.dag_longest_path()` | NetworkX optimizes for DAGs (O(V+E)); custom BFS will recompute unnecessarily for each node |
| Topological ordering | Custom Kahn's algorithm | `networkx.topological_sort()` | Library version is battle-tested; custom version risks subtle bugs in circular reference handling |
| JSON blob parsing in Phase 147 dispatch | Custom `json.loads()` + manual step indexing | Query `workflow_steps` and `workflow_edges` tables directly | Avoids deserialization overhead, enables index-based lookups on step_id |
| Cron pause/resume state management | Custom flags and timestamp logic | Reuse ScheduledJob pattern: `is_active` boolean + `schedule_cron` stored (not nullified) | Consistent with existing CRUD patterns; allows operators to re-enable without re-entering cron expression |

**Key insight:** The project deliberately chose normalized storage + service-layer validation to enable Phase 147's BFS dispatcher to query tables directly without JSON parsing. Deviating from this (e.g., adding definition_json) breaks the architecture.

## Common Pitfalls

### Pitfall 1: Cycle Detection Reporting Incomplete Information

**What goes wrong:** Returning `{"error": "CYCLE_DETECTED"}` without the actual cycle path. Phase 150/151 UI cannot highlight offending nodes/edges.

**Why it happens:** `nx.simple_cycles()` returns all cycles, but picking the "first" one is non-deterministic. Developer assumes caller doesn't need the specific path.

**How to avoid:** Always extract and return the cycle path in the error response:
```python
cycle = next(nx.simple_cycles(G))
return {
    "error": "CYCLE_DETECTED",
    "cycle_path": cycle  # e.g., ["step1", "step2", "step1"]
}
```

**Warning signs:** Phase 150/151 designer asks "which nodes form the cycle?" and you don't have a programmatic answer.

### Pitfall 2: Accepting Invalid Step IDs in Edges (Referential Integrity)

**What goes wrong:** API accepts `{"edges": [{"from_step_id": "step1", "to_step_id": "missing_step_id"}]}` because you only validated cycles, not references. Phase 147 BFS engine crashes with KeyError.

**Why it happens:** Developer assumes "if the DAG validates, all edges must be valid" — but cycle validation only checks acyclicity, not existence.

**How to avoid:** Validate edge references BEFORE running cycle detection:
```python
step_ids = {s.id for s in steps}
for edge in edges:
    if edge.from_step_id not in step_ids or edge.to_step_id not in step_ids:
        raise HTTPException(status_code=422, detail={"error": "INVALID_EDGE_REFERENCE", ...})
```

**Warning signs:** Unit tests pass but Phase 147 integration tests fail with KeyError on first BFS run.

### Pitfall 3: Using MultiDiGraph Instead of DiGraph

**What goes wrong:** Allowing multiple edges between the same two nodes (branch names). networkx treats them the same for cycle detection but DAG operations may behave unexpectedly.

**Why it happens:** Developer thinks "branch_name means multiple edges, so MultiDiGraph." But phase 146 explicitly models edges as individual rows; branch_name is a nullable attribute, not a reason to use MultiDiGraph.

**How to avoid:** Use simple `nx.DiGraph()`. Multiple edges between the same step_pair are caught at the service layer as invalid workflow definition (ambiguous routing), not stored.

```python
G = nx.DiGraph()  # Not MultiDiGraph
for edge in edges:
    if G.has_edge(edge.from_step_id, edge.to_step_id):
        # Already an edge; reject as duplicate
        raise HTTPException(422, {"error": "DUPLICATE_EDGE_REFERENCE", ...})
    G.add_edge(edge.from_step_id, edge.to_step_id)
```

**Warning signs:** Phase 148 IF gate branching logic (true/false branches) breaks because graph treats all edges equally.

### Pitfall 4: Depth Limit Enforcement Off By One

**What goes wrong:** Allowing depth == 31 when max is 30, or rejecting depth == 30.

**Why it happens:** Confusion over whether "30 levels" means 30 nodes or 30 edges. networkx.dag_longest_path returns nodes, so path length N means N-1 edges.

**How to avoid:** Define clearly: max_depth = 30 means max 30 **levels** (nodes). Edge count = level count - 1.
```python
# networkx.dag_longest_path returns a list of nodes in the longest path
longest_path = nx.dag_longest_path(G)
num_levels = len(longest_path)  # This is the node count (levels)
num_edges = num_levels - 1
# Reject if num_levels > 30
if num_levels > 30:
    raise HTTPException(422, {"error": "DEPTH_LIMIT_EXCEEDED", "actual_depth": num_levels})
```

**Warning signs:** Phase 147 BFS dispatcher reports "max_depth enforcement inconsistent with DAG shape" in logs.

### Pitfall 5: Not Validating on /validate Endpoint (Lightweight Validation Bypass)

**What goes wrong:** `POST /api/workflows/validate` is fast and reads-only (calls workflow_service directly), but actual POST/PUT routes skip validation or validate differently, allowing invalid state into the DB.

**Why it happens:** Developer assumes "validation before write" and forgets to call the same validation in both paths (POST + /validate).

**How to avoid:** Extract validation into a shared service method:
```python
# workflow_service.py
async def validate_workflow_definition(
    steps: List[WorkflowStepCreate],
    edges: List[WorkflowEdgeCreate],
    parameters: List[WorkflowParameterCreate]
) -> Dict[str, Any]:
    """Pure validation, no DB access. Returns {} if valid, else error dict."""
    # Check referential integrity, cycles, depth
    # Return errors or {}

# main.py
@app.post("/api/workflows/validate", ...)
async def validate_workflow(...):
    errors = await workflow_service.validate_workflow_definition(steps, edges, parameters)
    if errors:
        raise HTTPException(422, detail=errors)
    return {"status": "valid"}

@app.post("/api/workflows", ...)
async def create_workflow(...):
    errors = await workflow_service.validate_workflow_definition(steps, edges, parameters)
    if errors:
        raise HTTPException(422, detail=errors)
    # Save
```

**Warning signs:** Phase 151 visual editor calls /validate for every change, but then creates invalid workflows when submitting.

## Code Examples

Verified patterns from existing project code:

### Example 1: ORM Model with Relationship (from scheduler_service pattern)

```python
# In db.py
from sqlalchemy.orm import relationship

class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships (optional, for convenience)
    steps: Mapped[List["WorkflowStep"]] = relationship("WorkflowStep", cascade="all, delete-orphan")
    edges: Mapped[List["WorkflowEdge"]] = relationship("WorkflowEdge", cascade="all, delete-orphan")
    parameters: Mapped[List["WorkflowParameter"]] = relationship("WorkflowParameter", cascade="all, delete-orphan")

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("workflows.id"))
    scheduled_job_id: Mapped[str] = mapped_column(String, ForeignKey("scheduled_jobs.id"))
    node_type: Mapped[str] = mapped_column(String)  # e.g., "SCRIPT"
    config_json: Mapped[str] = mapped_column(Text, default="{}")

class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("workflows.id"))
    from_step_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_steps.id"))
    to_step_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_steps.id"))
    branch_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class WorkflowParameter(Base):
    __tablename__ = "workflow_parameters"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("workflows.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # e.g., "string", "int"
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

Source: Existing pattern from `ScheduledJob`, `Job`, `Node` models in [db.py](file:///home/thomas/Development/master_of_puppets/puppeteer/agent_service/db.py)

### Example 2: Pydantic Models for Full-Graph Contract

```python
# In models.py

class WorkflowStepCreate(BaseModel):
    id: str  # Client-provided step ID (for reference in edges)
    scheduled_job_id: str
    node_type: str  # e.g., "SCRIPT"
    config_json: Optional[Dict[str, Any]] = None

class WorkflowEdgeCreate(BaseModel):
    from_step_id: str
    to_step_id: str
    branch_name: Optional[str] = None

class WorkflowParameterCreate(BaseModel):
    name: str
    type: str
    default_value: Optional[str] = None

class WorkflowCreate(BaseModel):
    name: str
    steps: List[WorkflowStepCreate]
    edges: List[WorkflowEdgeCreate]
    parameters: Optional[List[WorkflowParameterCreate]] = None

class WorkflowResponse(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    is_paused: bool
    steps: List[WorkflowStepCreate]
    edges: List[WorkflowEdgeCreate]
    parameters: List[WorkflowParameterCreate]
    
    model_config = ConfigDict(from_attributes=True)

class WorkflowListItem(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: datetime
    step_count: int
    is_paused: bool
    last_run_status: Optional[str] = None  # PENDING, RUNNING, COMPLETED, FAILED

class WorkflowValidationError(BaseModel):
    error: Literal["CYCLE_DETECTED", "DEPTH_LIMIT_EXCEEDED", "INVALID_EDGE_REFERENCE"]
    cycle_path: Optional[List[str]] = None
    max_depth: Optional[int] = None
    actual_depth: Optional[int] = None
    edge: Optional[Dict[str, str]] = None
```

Source: Existing pattern from `JobDefinitionCreate`, `JobDefinitionResponse` in [models.py](file:///home/thomas/Development/master_of_puppets/puppeteer/agent_service/models.py)

### Example 3: Service-Layer Validation and CRUD

```python
# In services/workflow_service.py

import networkx as nx
from typing import List, Dict, Any, Optional, Tuple

class WorkflowService:
    @staticmethod
    def validate_edges_reference_steps(steps: List, edges: List) -> Tuple[bool, Optional[Dict]]:
        """Check all edge endpoints exist in steps."""
        step_ids = {s.id for s in steps}
        for edge in edges:
            if edge.from_step_id not in step_ids or edge.to_step_id not in step_ids:
                return False, {
                    "error": "INVALID_EDGE_REFERENCE",
                    "edge": {
                        "from_step_id": edge.from_step_id,
                        "to_step_id": edge.to_step_id
                    }
                }
        return True, None
    
    @staticmethod
    def validate_no_cycles(steps: List, edges: List) -> Tuple[bool, Optional[Dict]]:
        """Check DAG is acyclic using networkx."""
        G = nx.DiGraph()
        for step in steps:
            G.add_node(step.id)
        for edge in edges:
            G.add_edge(edge.from_step_id, edge.to_step_id)
        
        if not nx.is_directed_acyclic_graph(G):
            try:
                cycle = list(next(nx.simple_cycles(G)))
                return False, {
                    "error": "CYCLE_DETECTED",
                    "cycle_path": cycle
                }
            except StopIteration:
                return False, {"error": "CYCLE_DETECTED", "cycle_path": []}
        return True, None
    
    @staticmethod
    def validate_depth(steps: List, edges: List, max_depth: int = 30) -> Tuple[bool, Optional[Dict]]:
        """Check longest path <= max_depth."""
        G = nx.DiGraph()
        for step in steps:
            G.add_node(step.id)
        for edge in edges:
            G.add_edge(edge.from_step_id, edge.to_step_id)
        
        if len(G) == 0:
            return True, None
        
        longest_path = nx.dag_longest_path(G)
        depth = len(longest_path)  # Number of nodes = levels
        
        if depth > max_depth:
            return False, {
                "error": "DEPTH_LIMIT_EXCEEDED",
                "max_depth": max_depth,
                "actual_depth": depth
            }
        return True, None
    
    @staticmethod
    async def validate_workflow_definition(
        steps: List, edges: List, parameters: List = None, max_depth: int = 30
    ) -> Optional[Dict]:
        """Run all validations. Returns error dict or None if valid."""
        # 1. Referential integrity
        valid, error = WorkflowService.validate_edges_reference_steps(steps, edges)
        if not valid:
            return error
        
        # 2. Cycle detection
        valid, error = WorkflowService.validate_no_cycles(steps, edges)
        if not valid:
            return error
        
        # 3. Depth limit
        valid, error = WorkflowService.validate_depth(steps, edges, max_depth)
        if not valid:
            return error
        
        return None  # All valid
    
    @staticmethod
    async def create_workflow(
        req: WorkflowCreate, current_user: User, db: AsyncSession
    ) -> Workflow:
        """Create workflow after validation."""
        # Validate
        error = await WorkflowService.validate_workflow_definition(
            req.steps, req.edges, req.parameters
        )
        if error:
            raise HTTPException(status_code=422, detail=error)
        
        # Save
        workflow = Workflow(
            id=str(uuid4()),
            name=req.name,
            created_by=current_user.username,
            created_at=datetime.utcnow()
        )
        db.add(workflow)
        
        # Save steps
        for step in req.steps:
            db.add(WorkflowStep(
                id=str(uuid4()),
                workflow_id=workflow.id,
                scheduled_job_id=step.scheduled_job_id,
                node_type=step.node_type,
                config_json=step.config_json or "{}"
            ))
        
        # Save edges
        for edge in req.edges:
            db.add(WorkflowEdge(
                id=str(uuid4()),
                workflow_id=workflow.id,
                from_step_id=edge.from_step_id,
                to_step_id=edge.to_step_id,
                branch_name=edge.branch_name
            ))
        
        # Save parameters
        if req.parameters:
            for param in req.parameters:
                db.add(WorkflowParameter(
                    id=str(uuid4()),
                    workflow_id=workflow.id,
                    name=param.name,
                    type=param.type,
                    default_value=param.default_value
                ))
        
        await db.commit()
        return workflow
```

Source: Pattern adapted from `SchedulerService.create_job_definition()` in [scheduler_service.py](file:///home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/scheduler_service.py)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-coded cycle detection (DFS with explicit visited set) | networkx library (is_directed_acyclic_graph + simple_cycles) | 2020s ecosystem shift | Eliminates subtle bugs (off-by-one depth, unreachable subgraphs); O(V+E) instead of O(V² + E) |
| Definition as JSON blob in DB | Normalized tables (workflow_steps + workflow_edges) | Phase 146 design (2026-04-15) | Enables Phase 147 dispatcher to query tables directly without parsing; improves query efficiency for large workflows |
| Single /api/workflows endpoint handling all operations | Dedicated /api/workflows/{id}/fork endpoint for Save-as-New | Phase 146 design | Explicit atomic behavior; prevents accidental cron pausing on regular updates |
| Hardcoded depth limit (varies by implementation) | Configurable max_depth parameter with explicit enforcement | Phase 146 design | 30-level limit reflects job execution depth constraints in Phase 147; changeable in future without code edits |

**Deprecated/outdated:**
- **Custom DFS cycle detection:** Modern Python projects use networkx; hand-rolled DFS has edge cases (e.g., multiple paths to same node, unreachable subgraph cycles)
- **Definition JSON blobs:** Airflow 1.x used JSON DAGs; Airflow 2.x moved to Python code + database operators. Industry moved away from DAG-as-blob.

## Open Questions

1. **Should workflow_service.py live under `services/` or a new `workflow/` sub-package?**
   - What we know: Existing services (job_service, scheduler_service) live in `services/` directory; no sub-packages currently exist
   - What's unclear: Whether a workflow subpackage (for future Phase 147–151 code) would reduce main.py complexity
   - Recommendation: Start with `services/workflow_service.py` to follow existing pattern. If Phase 147 adds 500+ lines, refactor to `services/workflow/` then.

2. **How should failed ScheduledJob IDs be handled (referential integrity)?**
   - What we know: WorkflowStep.scheduled_job_id FK to ScheduledJob(id); CONTEXT.md says steps reference ScheduledJob IDs
   - What's unclear: Should API validate that referenced ScheduledJob IDs exist, or allow dangling references (fail later in Phase 147)?
   - Recommendation: Validate at save time. Query DB for each scheduled_job_id in steps and raise HTTP 422 if not found. Prevents orphaned workflows.

3. **Should POST /api/workflows/{id}/fork also copy last_run_status, or reset to null?**
   - What we know: CONTEXT.md says GET /workflows list includes last_run_status; fork clones all steps/edges/parameters
   - What's unclear: Should new workflow inherit the source's last_run_status (creating confusion) or start fresh?
   - Recommendation: Reset new workflow's last_run_status to null. Fork is a "clean slate" from user perspective.

## Validation Architecture

**Test Framework:** pytest (existing, used in puppeteer/tests/)

| Property | Value |
|----------|-------|
| Framework | pytest 7.x (from pyproject.toml) |
| Config file | puppeteer/pyproject.toml (ruff + black config; no pytest.ini needed) |
| Quick run command | `cd puppeteer && pytest tests/test_workflow.py -x -v` |
| Full suite command | `cd puppeteer && pytest tests/ -x` |

**Phase Requirements → Test Map**

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WORKFLOW-01 | POST /api/workflows creates workflow with valid steps/edges | unit + integration | `pytest tests/test_workflow.py::test_create_workflow_success -x` | ❌ Wave 0 |
| WORKFLOW-01 | POST /api/workflows rejects invalid step IDs in edges (INVALID_EDGE_REFERENCE) | unit | `pytest tests/test_workflow.py::test_create_workflow_invalid_edges -x` | ❌ Wave 0 |
| WORKFLOW-02 | GET /api/workflows lists workflows with step_count and last_run_status | integration | `pytest tests/test_workflow.py::test_list_workflows -x` | ❌ Wave 0 |
| WORKFLOW-03 | PUT /api/workflows/{id} replaces full graph atomically | integration | `pytest tests/test_workflow.py::test_update_workflow -x` | ❌ Wave 0 |
| WORKFLOW-03 | Cycle detection rejects cyclic graphs with cycle_path | unit | `pytest tests/test_workflow.py::test_validate_cycle_detection -x` | ❌ Wave 0 |
| WORKFLOW-03 | Depth limit rejects graphs > 30 levels | unit | `pytest tests/test_workflow.py::test_validate_depth_limit -x` | ❌ Wave 0 |
| WORKFLOW-04 | DELETE /api/workflows/{id} rejects if active runs exist (HTTP 409) | integration | `pytest tests/test_workflow.py::test_delete_workflow_with_active_runs -x` | ❌ Wave 0 |
| WORKFLOW-05 | POST /api/workflows/{id}/fork clones all steps/edges/params and pauses source | integration | `pytest tests/test_workflow.py::test_fork_workflow -x` | ❌ Wave 0 |
| WORKFLOW-05 | Verify source workflow.is_paused = true after fork | unit | `pytest tests/test_workflow.py::test_fork_pauses_source -x` | ❌ Wave 0 |

**Sampling Rate**
- **Per task commit:** `cd puppeteer && pytest tests/test_workflow.py -x` (quick validation of new changes)
- **Per wave merge:** `cd puppeteer && pytest tests/ -x` (full suite across all phases)
- **Phase gate:** Full suite green before `/gsd:verify-work`

**Wave 0 Gaps**
- [ ] `puppeteer/tests/test_workflow.py` — covers all WORKFLOW-01..05 test cases
- [ ] `puppeteer/tests/conftest.py` — add `workflow_fixture` (pre-created workflow with valid steps/edges) and `async_db_session` fixture for transaction rollback
- [ ] Framework install: `pip install -r puppeteer/requirements.txt` (adds networkx)
- [ ] Migration script run: `sqlite3 jobs.db < migration_v53.sql` (for local SQLite tests)

## Sources

### Primary (HIGH confidence)
- [NetworkX 3.6.1 DAG algorithms documentation](https://networkx.org/documentation/stable/reference/algorithms/dag.html) — is_directed_acyclic_graph, simple_cycles, dag_longest_path
- [NetworkX cycle detection reference](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.cycles.find_cycle.html) — find_cycle and simple_cycles functions
- [Existing db.py patterns](file:///home/thomas/Development/master_of_puppets/puppeteer/agent_service/db.py) — ORM model structure, relationships, create_all approach
- [Existing scheduler_service.py patterns](file:///home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/scheduler_service.py) — service-layer CRUD, validation helpers
- [Existing models.py patterns](file:///home/thomas/Development/master_of_puppets/puppeteer/agent_service/models.py) — Pydantic request/response shapes, field_validator

### Secondary (MEDIUM confidence)
- [MungingData DAG with networkx guide](https://www.mungingdata.com/python/dag-directed-acyclic-graph-networkx/) — practical DAG patterns in Python (verified with official networkx docs)
- [NetworkX topological sort reference](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.topological_sort.html) — topological_sort() function signature and use cases
- [DAG depth calculation patterns](https://www.mungingdata.com/python/dag-directed-acyclic-graph-networkx/) — longest_path algorithms for depth validation

### Tertiary (LOW confidence — informational only)
- [Wikipedia: Directed Acyclic Graph](https://en.wikipedia.org/wiki/Directed_acyclic_graph) — theoretical background on DAG properties

## Metadata

**Confidence breakdown:**
- **Standard stack (HIGH):** networkx is established library (3.6.1 current); SQLAlchemy ORM patterns verified in existing codebase; Pydantic request/response models follow project conventions
- **Architecture (HIGH):** Normalized table structure and full-graph API contract are explicit in CONTEXT.md; cycle detection/depth validation patterns are standard across Airflow, Dagster, and networkx docs
- **Pitfalls (HIGH):** Derived from common DAG validation bugs (cycle detection incompleteness, referential integrity gaps, off-by-one depth errors); project-specific pit falls (JSON blob storage conflicts with Phase 147 queries)
- **Validation (MEDIUM):** Test framework and patterns verified in existing conftest.py; Wave 0 gaps identified but fixture implementations deferred to planner

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (30 days; networkx is stable; schema finalized in CONTEXT.md)

---

*Phase: 146-workflow-data-model*
*Research complete: 2026-04-15*
