# Technology Stack — DAG/Workflow Orchestration

**Project:** Master of Puppets (Axiom) — Workflow/DAG Orchestration Milestone  
**Researched:** 2026-04-15  
**Confidence:** HIGH (Core libraries verified via NPM/PyPI; design patterns from official docs)

## Executive Summary

The workflow DAG milestone requires visual editing, graph validation, and real-time live updates of workflow runs. The recommended stack extends the existing FastAPI + React ecosystem with minimal new dependencies:

**Frontend:** `@xyflow/react` v12.8.3 (DAG canvas) + `elkjs` v0.11.1 (auto-layout) + `zustand` (workflow state)  
**Backend:** `networkx` v3.6.1 (cycle validation) + FastAPI background tasks (workflow execution) + existing WebSocket infrastructure  
**Runtime:** No new runtimes needed — Python/JavaScript async models already in place

The stack avoids heavy orchestration frameworks (Airflow, Prefect, Dagster) because the execution model is already solid. The job is to add a **visual composition and monitoring layer** on top of what works.

## Recommended Stack

### Frontend — DAG Editor & Visualization

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `@xyflow/react` | 12.8.3 | Interactive DAG canvas: drag nodes, connect edges, zoom/pan | Industry standard (React Flow rebranded). Zero learning curve for devs familiar with Radix. Out-of-the-box node rendering, handles, keyboard shortcuts. Used in production by enterprises. Alternative (Excalidraw) would require building custom node model. |
| `elkjs` | 0.11.1 | Hierarchical auto-layout (arranges nodes to avoid crosses) | Deterministic layout — same workflow always looks the same. Configurable direction (top-down, left-right). Solves the "nodes everywhere" UX problem. Lighter than Graphviz, more feature-complete than dagre. Bundles as JavaScript (no external server needed). |
| `recharts` | 3.6.0 (existing) | Workflow run timeline / step duration visualization | Already in stack; reuse for timeline view showing which steps ran when. Avoid adding a second charting library. |
| `zustand` | ^5.4.0 | Workflow editor state (nodes, edges, selected node, panel state, undo/redo) | Minimal (~1.2KB), no boilerplate. Plays well with `@xyflow/react` (atomic hooks). Avoid Redux/Context for this — too verbose. |
| `@radix-ui/*` | (existing) | Panels, dialogs, dropdowns (step config, palette, settings) | Already in use; consistency. |

### Backend — DAG Validation & Execution

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `networkx` | 3.6.1 | DAG cycle detection, topological sort, path analysis | Official library for graph algorithms. Used by 10k+ projects. `networkx.algorithms.dag.is_directed_acyclic_graph()` is the standard. Alternatives (graphlib) are too minimal for step dependencies. |
| `pydantic` | 2.x (existing in FastAPI) | Validate WorkflowDefinition, Step, Parameter schemas | No new dependency — already required. Use `@field_validator` for custom DAG validation rules. |
| FastAPI `BackgroundTasks` | (built-in) | Enqueue workflow runs as background jobs | Sufficient for orchestration — runs immediately, no queue server. For high volume, graduate to Redis/ARQ later. |
| `asyncio` | (built-in) | Concurrent workflow step execution and cancellation | Already used in FastAPI. Chain steps with `await`, cancel with tasks.cancel(). |

### Database — New Tables (No New ORM)

| What | Tool | Purpose |
|------|------|---------|
| Workflow definition storage | SQLAlchemy ORM (existing) | Add `Workflow`, `WorkflowStep`, `WorkflowParameter` tables to existing SQLAlchemy schema. No migration needed — just `create_all()` at startup. |
| Workflow run tracking | SQLAlchemy ORM | Add `WorkflowRun`, `WorkflowStepExecution` tables with status/timestamps. Reuse existing Job/ExecutionRecord patterns. |
| Step output storage | PostgreSQL JSONB (existing) | Store condition results, step outputs in JSONB columns for querying. |

### WebSocket — Live Workflow Run Updates (Existing)

| Technology | Version | Purpose | How to Use |
|------------|---------|---------|-----------|
| `websockets` | (existing FastAPI) | Stream workflow run updates to dashboard | Reuse existing `/ws?token=<jwt>` endpoint. Broadcast `{"type": "workflow_run_update", "run_id": "...", "step_id": "...", "status": "RUNNING"}` messages. Frontend listens via existing `useWebSocket.ts` hook. |

### Webhook Ingestion (Optional MVP2)

If you want external systems to trigger workflows:

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| `hmac` | (Python stdlib) | HMAC-SHA256 webhook signature verification | No dependency. Pattern: get raw request body, verify signature with `hmac.compare_digest()`, then route to handler. See FastAPI security docs. |
| `httpx` | (existing) | Async HTTP calls (e.g., send webhook outbound after workflow completes) | Already in requirements. |
| FastAPI `BackgroundTasks` | (built-in) | Async webhook retry logic | No Celery needed for MVP. Simple retry loop in background task. |

**Decision:** Webhooks deferred to Phase 2. Core workflow execution doesn't need them. Phase 1 focuses on UI + internal triggering (cron, manual).

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| DAG Canvas | `@xyflow/react` | `Excalidraw` SDK | Excalidraw is draw-focused, not node-flow-focused. Requires custom node types. More overhead for less benefit. |
| DAG Canvas | `@xyflow/react` | `vis.js` | Older, less active maintenance. No React integration. Steeper learning curve. |
| Layout Engine | `elkjs` | `dagre` | Dagre is faster but produces lower-quality layouts (more edge crossings). For small workflows (<50 nodes), fine. For complex ones, elkjs is worth the overhead. |
| Layout Engine | `elkjs` | `d3-dag` | d3-dag (1.1.0) is mature but low-maintenance (last update 2 years ago). ELKjs more actively maintained and better integrated with React Flow examples. |
| Graph Validation | `networkx` | `graphlib` (Python stdlib) | `graphlib.TopologicalSorter` exists in Python 3.9+ but lacks cycle detection, path analysis, SCC discovery. NetworkX is fuller-featured, widely adopted. Worth the ~5MB import. |
| State Management | `zustand` | `Jotai` | Jotai is atomic/bottom-up; Zustand is store/top-down. For a single "workflow editor state" object, Zustand is simpler. Jotai shines with many independent atoms. Use Zustand. |
| State Management | `zustand` | Redux Toolkit | Overkill for a single-page editor. Redux adds ceremony (slices, thunks) we don't need. |
| Execution | `BackgroundTasks` | Celery | Celery requires Redis/RabbitMQ. For MVP, BackgroundTasks (same-process) is fine. Graduate to Celery if workflows grow long (>5min) or volume balloons (>100/hr). |
| Execution | `BackgroundTasks` | ARQ | ARQ is better than BackgroundTasks long-term (persistent queue, retries), but adds Redis dependency. Start simple. |

## Installation

### Frontend

```bash
cd puppeteer/dashboard

# Core workflow editor
npm install @xyflow/react@12.8.3 elkjs@0.11.1 zustand@^5.4.0

# State management
# (zustand above covers this)

# No additional Radix, recharts, or date-fns — already installed
```

### Backend

```bash
cd puppeteer

# Graph validation
pip install networkx==3.6.1

# No new major dependencies. Existing requirements cover:
# - FastAPI (already has WebSocket support)
# - asyncio (Python stdlib)
# - SQLAlchemy (ORM, already in use)
# - Pydantic (validation, already in use)
```

### Verification

```bash
# Frontend
npm ls @xyflow/react elkjs zustand

# Backend
pip show networkx
python3 -c "import networkx; print(networkx.__version__)"
```

## Integration Points with Existing Stack

### Database

New tables fit cleanly into existing schema:

```python
# puppeteer/agent_service/db.py (SQLAlchemy models)

class Workflow(Base):
    """DAG of scheduled jobs and gates."""
    __tablename__ = "workflows"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True)
    created_by = Column(String)
    definition = Column(JSON)  # {"nodes": [...], "edges": [...]}
    status = Column(Enum(JobLifecycleStatus))  # DRAFT/ACTIVE/DEPRECATED/REVOKED
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class WorkflowRun(Base):
    """Single execution of a workflow."""
    __tablename__ = "workflow_runs"
    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id"))
    status = Column(Enum(JobStatusEnum))  # QUEUED/RUNNING/SUCCESS/FAILED
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

class WorkflowStepExecution(Base):
    """Single step within a workflow run."""
    __tablename__ = "workflow_step_executions"
    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("workflow_runs.id"))
    step_id = Column(String)  # Node ID from DAG
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)  # If script step
    status = Column(Enum(JobStatusEnum))
    output = Column(JSON)  # Result from /tmp/axiom/result.json or signal wait
    created_at = Column(DateTime)
```

### API Endpoints

New routes in `puppeteer/agent_service/main.py`:

```python
# Workflow CRUD
POST   /api/workflows/definitions
GET    /api/workflows/definitions
GET    /api/workflows/definitions/{id}
PATCH  /api/workflows/definitions/{id}
DELETE /api/workflows/definitions/{id}

# Trigger workflow
POST   /api/workflows/{id}/trigger
GET    /api/workflows/runs/{run_id}
GET    /api/workflows/runs/{run_id}/steps/{step_id}

# WebSocket: broadcast workflow updates
# (Reuse existing /ws?token=<jwt> with new message types)
```

### Frontend Routes

New views in `puppeteer/dashboard/src/views/`:

```
Workflows.tsx          # List of workflow definitions
WorkflowEditor.tsx     # Visual DAG editor (canvas + node palette)
WorkflowRuns.tsx       # History and monitoring of workflow executions
WorkflowRunDetail.tsx  # Step-level timeline + outputs
```

### Validation Layer

Leverage existing Pydantic + SQLAlchemy validation:

```python
# puppeteer/agent_service/models.py

class WorkflowStepInput(BaseModel):
    node_id: str
    node_type: Literal["script", "if_gate", "and_gate", "or_gate", "parallel", "signal_wait"]
    script_id: Optional[str]  # ScheduledJob.id (if script type)
    condition: Optional[str]  # Python expression for IF gates
    
class WorkflowDefinitionCreate(BaseModel):
    name: str
    nodes: List[WorkflowStepInput]
    edges: List[dict]  # {source: str, target: str}
    
    @field_validator("edges")
    @classmethod
    def validate_dag(cls, edges: List[dict]):
        """Check for cycles using NetworkX."""
        import networkx as nx
        g = nx.DiGraph()
        g.add_edges_from([(e["source"], e["target"]) for e in edges])
        if not nx.is_directed_acyclic_graph(g):
            raise ValueError("Workflow contains cycles")
        return edges
```

### WebSocket Broadcasting

Reuse existing pattern from `puppeteer/agent_service/main.py`:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Existing auth + connection logic
    await websocket.accept()
    
    # Existing handlers for job updates
    # Add new handlers:
    if message["type"] == "workflow_step_update":
        # Broadcast to all clients watching this workflow run
        await broadcast_to_workflow_run(
            message["run_id"],
            {
                "type": "workflow_step_update",
                "step_id": message["step_id"],
                "status": message["status"],
                "output": message.get("output"),
            }
        )
```

## Explicit Non-Additions

**Why we don't add:**

| Tool | Why Not | Impact if Added |
|------|---------|-----------------|
| Airflow / Prefect / Dagster | Full orchestration platforms overkill. We already have job scheduling (APScheduler), execution (Docker), and state (PostgreSQL). Adding them means duplicate job definitions, duplicate execution engines, sync pain. | +500MB dependencies, operational overhead, coupling to external service. |
| Celery / RQ | Job queue. Unnecessary for MVP — workflows are typically <10min. BackgroundTasks suffices. Graduate if execution time grows or concurrency spikes. | Adds Redis/RabbitMQ infra dependency. |
| GraphQL | No client asked for it. REST + WebSocket covers all use cases. GraphQL would only help if workflows are queried from 5+ different clients (they're not). | +200KB bundle, more API surface to secure. |
| Bull/Bee-Queue (JS) | Don't mix JavaScript and Python for orchestration. Queue server should live on backend. | Increases complexity, splits responsibility. |
| TensorFlow / PyTorch | Not ML-focused. Workflows may *call* ML jobs, but don't need a deep learning framework. | Massive dependency bloat. |

## Performance & Scalability Notes

### Frontend

- `@xyflow/react` v12+ renders only nodes in viewport (virtualization). No UI slowdown until ~500 nodes.
- `elkjs` layout: blocking operation. For >100 nodes, run in `Web Worker` to prevent janky UI. Deferred to Phase 2.
- `zustand` store updates: O(1) re-renders (atomic selectors). No Redux re-render thrashing.

### Backend

- `networkx.is_directed_acyclic_graph()`: O(n+e) complexity. Fast enough for graphs <1000 nodes.
- Concurrent workflow execution: Use `asyncio.TaskGroup()` (Python 3.11+) to run parallel steps, cancel all on first failure.
- Database: Queries on `workflow_runs` and `workflow_step_executions` will benefit from indexes on `(run_id, created_at)` and `(workflow_id, status)`. Add after Phase 1 if necessary.

### Webhook Expansion (Future)

If Phase 2 adds webhook ingestion:
- Use `fastapi.BackgroundTasks` to verify + record quickly, offload async processing.
- Store webhook payloads in database (audit trail) before processing.
- Implement idempotency via `webhook_id` deduplication (same ID = replay-safe).

## Version Pinning Rationale

| Library | Version | Why Pin | Stability |
|---------|---------|---------|-----------|
| `@xyflow/react` | 12.8.3 | Major API changes between v10 → v12. Pin to 12.x to avoid breaking upgrades. | HIGH — actively maintained, releases monthly. |
| `elkjs` | 0.11.1 | Pre-1.0. Minor bumps may have breaking layout changes. Prefer explicit version. | MEDIUM — lighter maintenance, but solid. |
| `zustand` | ^5.4.0 | Allow patch/minor bumps (5.x range). API stable post-v4. | HIGH — mature, widely used. |
| `networkx` | 3.6.1 | Stable series. 3.x is long-term support. Allow patch upgrades (3.6.x). | HIGH — standardized, production-ready. |

## Source Material

- [React Flow Docs: Overview & Layouting](https://reactflow.dev/)
- [React Flow Pro: Workflow Editor Template](https://reactflow.dev/ui/templates/workflow-editor)
- [ELKjs: Hierarchical Layout Engine](https://eclipse.dev/elk/)
- [NetworkX: DAG Algorithms](https://networkx.org/documentation/stable/reference/algorithms/dag.html)
- [Zustand: State Management](https://github.com/pmndrs/zustand)
- [FastAPI: WebSocket Support](https://fastapi.tiangolo.com/advanced/websockets/)
- [FastAPI: Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI: Webhook Security](https://fastapi.tiangolo.com/advanced/openapi-webhooks/)
- [NPM: @dagrejs/dagre v3.0.0](https://www.npmjs.com/package/@dagrejs/dagre)
- [NPM: d3-dag v1.1.0](https://www.npmjs.com/package/d3-dag)

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| `@xyflow/react` v12 API changes between sprints | Low (v12 is stable) | Lock version in package.json. Test before upgrade. |
| `elkjs` layout determinism issues (different layout on same graph) | Low | Write layout tests. Snapshot current layout on Phase 1 completion. |
| `networkx` cycle detection misses cycles in edge cases | Very Low | Test with pathological graphs (complete graphs, deeply nested). Existing tests in networkx cover this. |
| WebSocket broadcast scalability (100s of clients on same workflow run) | Medium | Use Redis pub/sub at Phase 2 if needed. For MVP (<50 concurrent), in-memory broadcast works. |
| AsyncIO task cancellation edge cases (step cleanup on cancel) | Low | Use `asyncio.TaskGroup()` and proper exception handling. Test cancel scenarios in Phase 2 QA. |

## Recommendation for Roadmap

**Phase 1 (MVP):** Frontend editor + backend DAG validation + basic execution  
→ Install: `@xyflow/react`, `elkjs`, `zustand`, `networkx`

**Phase 2:** Webhook triggering + advanced scheduling (cron on workflow, not just steps)  
→ Install: `svix-python` (if using managed webhooks) or just `hmac` (stdlib)

**Phase 3+:** Scaling — Redis-backed job queue, distributed workflow execution  
→ Evaluate: ARQ, Celery (not recommended for now)

