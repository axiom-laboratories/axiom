# Architecture: DAG Workflow Orchestration Integration

**Domain:** Enterprise job orchestration platform with new workflow/DAG capability
**Researched:** 2026-04-15
**Overall confidence:** HIGH

## Executive Summary

Master of Puppets has a working job dependency model (`Job.depends_on` JSON, `_unblock_dependents()` BFS cascade) suitable for linear chains but not DAGs. The workflow orchestration milestone adds structured DAG definitions with visual editing, IF gates (conditional execution on job result), webhook triggers, and multi-run tracking.

The recommended architecture **reuses the existing BFS cascade logic** rather than replacing it. A new `WorkflowRun` entity acts as a "meta-orchestrator" that: (1) reads the workflow's DAG definition (stored as serialized node/edge graph), (2) dispatches jobs in topological dependency order, (3) evaluates IF gate conditions by reading job `result` (structured JSON), and (4) cascades cancellation on failed gates. This keeps the existing job system intact while layering workflow-specific semantics on top.

Webhook security uses HMAC-SHA256 with raw-body verification and timestamp validation (industry standard 2026). Build order: database schema first (enables async development), BFS runner second (core orchestration logic), trigger/webhook ingest third, then UI/canvas editor last.

**Key integration point:** `WorkflowRun` dispatches regular `Job` records via existing `JobService.create_job()`, inheriting all existing security (Ed25519 signing, mTLS, resource limits, RBAC). No job architecture rewrites needed.

---

## Recommended Architecture

### 1. Data Model & Schema

#### New Tables

```sql
-- Workflow definitions (DAG template)
CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    dag_json TEXT NOT NULL,  -- {"nodes": [...], "edges": [...]}
    created_at DATETIME DEFAULT NOW(),
    created_by TEXT NOT NULL,
    updated_at DATETIME,
    is_active BOOLEAN DEFAULT true
);

-- Workflow execution runs (trace of one workflow invocation)
CREATE TABLE workflow_runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    trigger_type TEXT,  -- 'manual', 'scheduled', 'webhook', 'api'
    trigger_payload JSON,  -- {"variables": {...}} or null
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT NOW(),
    created_by TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

-- Per-step execution tracking within a run
CREATE TABLE workflow_run_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,  -- DAG node identifier (not Node.node_id)
    job_guid TEXT,  -- FK to Job.guid (nullable until dispatch)
    status TEXT NOT NULL,  -- PENDING, BLOCKED, ASSIGNED, COMPLETED, FAILED, SKIPPED (IF gate), CANCELLED
    started_at DATETIME,
    completed_at DATETIME,
    result_summary JSON,  -- Cache of job result for gate evaluation
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id),
    FOREIGN KEY (job_guid) REFERENCES jobs(guid)
);

-- Webhook triggers (inbound entry points)
CREATE TABLE workflow_webhooks (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,  -- URL-safe identifier
    secret_hash TEXT NOT NULL,  -- bcrypt(shared_secret)
    is_active BOOLEAN DEFAULT true,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
```

#### Modified Tables

**`Job` table** — add optional FK to workflow context:
```sql
ALTER TABLE jobs ADD COLUMN workflow_run_id TEXT;
ALTER TABLE jobs ADD COLUMN workflow_run_step_id TEXT;
-- FK optional; allows jobs to exist outside workflows
```

**Job.depth limit relaxation:**
The existing `_get_dependency_depth()` limit (max 10) must be **overridable for workflow-spawned jobs**. Rationale: a workflow DAG might have 15+ levels (e.g., multi-stage data pipeline), but random user jobs should stay shallow to prevent DoS.

```python
# In job_service.py
async def _get_dependency_depth(guid: str, db: AsyncSession, current_depth: int = 1, 
                                 max_depth: int = 10) -> int:
    """Trace depth with configurable limit."""
    if current_depth > max_depth:
        return current_depth
    # ... rest unchanged
```

---

### 2. DAG Representation (JSON Schema)

Workflows are serialized as JSON in `workflow.dag_json`:

```json
{
  "metadata": {
    "name": "multi-stage-deploy",
    "version": "1.0"
  },
  "nodes": [
    {
      "id": "step_1_validate",
      "type": "job",
      "job_definition_id": "def-validate-code",
      "display_name": "Validate Code",
      "retry_policy": { "max_retries": 2, "backoff_multiplier": 1.5 }
    },
    {
      "id": "step_2_test",
      "type": "job",
      "job_definition_id": "def-run-tests",
      "display_name": "Run Tests"
    },
    {
      "id": "step_3_check_results",
      "type": "gate",
      "condition": "{{ steps.step_2_test.result.exit_code == 0 }}",
      "display_name": "Tests Passed?"
    },
    {
      "id": "step_4_deploy",
      "type": "job",
      "job_definition_id": "def-deploy",
      "display_name": "Deploy"
    }
  ],
  "edges": [
    { "from": "step_1_validate", "to": "step_2_test" },
    { "from": "step_2_test", "to": "step_3_check_results" },
    { "from": "step_3_check_results", "to": "step_4_deploy" }
  ]
}
```

**Gate nodes** are structural (don't execute a job) — they evaluate a condition expression against upstream job results. If condition is false, downstream tasks are skipped (not cancelled). If condition is true, execution continues.

---

### 3. WorkflowRun BFS Executor

The `WorkflowRun` executor **reuses existing BFS logic** but operates at the workflow level. Pseudo-code:

```python
# puppeteer/agent_service/services/workflow_service.py

class WorkflowRunService:
    @staticmethod
    async def dispatch_workflow_run(
        workflow_id: str, 
        trigger_type: str,
        trigger_payload: Optional[dict],
        db: AsyncSession
    ) -> str:
        """
        1. Create a WorkflowRun record
        2. Create WorkflowRunStep records for all DAG nodes
        3. Dispatch root jobs (nodes with no upstream dependencies)
        4. Return run_id
        """
        # Fetch workflow DAG
        workflow = (workflow DAG from DB)
        dag = json.loads(workflow.dag_json)
        
        # Create run record
        run = WorkflowRun(...)
        db.add(run)
        
        # Create step records (one per DAG node)
        for node in dag["nodes"]:
            step = WorkflowRunStep(...)
            db.add(step)
        
        # Build adjacency + topological sort
        adjacency = {node["id"]: [...downstream...]}
        in_degree = {node["id"]: (# of upstream)}
        
        # Dispatch root nodes (in_degree == 0)
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        
        for root_node_id in queue:
            node_def = (find node def by id)
            if node_def["type"] == "job":
                job = JobService.create_job(node_def)
                (link job to step)
        
        run.status = "RUNNING"
        await db.commit()
        return run_id
    
    @staticmethod
    async def _unblock_workflow_steps_after_job(
        job_guid: str,
        db: AsyncSession
    ):
        """
        Called when a Job completes (via existing JobService._unblock_dependents).
        
        Finds WorkflowRunSteps blocked by this job and:
        1. Checks if upstream dependencies satisfied
        2. Evaluates IF gates
        3. Dispatches next jobs or skips branches
        """
        step = (find WorkflowRunStep with job_guid)
        run = (fetch WorkflowRun)
        dag = (deserialize from workflow)
        job = (fetch Job)
        
        # Update step with job result
        step.status = job.status
        step.result_summary = job.result
        
        # For each downstream neighbor
        for next_node_id in (neighbors of step.node_id):
            next_step = (fetch WorkflowRunStep)
            node_def = (find node def)
            
            # If gate node, evaluate condition
            if node_def["type"] == "gate":
                passed = _evaluate_gate_condition(
                    node_def["condition"],
                    json.loads(job.result)
                )
                if passed:
                    next_step.status = "PENDING"
                else:
                    next_step.status = "SKIPPED"
                    _skip_descendants(next_node_id, run_id, dag)
                    continue
            
            # Check all upstream deps satisfied
            upstreams = (find all predecessors of next_node)
            if all(upstream.status in ["COMPLETED", "SKIPPED"]):
                if node_def["type"] == "job":
                    job = JobService.create_job(node_def)
                    next_step.job_guid = job.guid
        
        await db.commit()

async def _evaluate_gate_condition(condition: str, job_result: dict) -> bool:
    """
    Evaluate a condition expression like:
      '{{ steps.step_2_test.result.exit_code == 0 }}'
    
    Uses Jinja2 with restricted scope for safety.
    """
    import jinja2
    
    env = jinja2.Environment()
    try:
        template = env.from_string(condition)
        context = {
            "result": job_result,
            "exit_code": job_result.get("exit_code"),
            "stdout": job_result.get("stdout", ""),
            "stderr": job_result.get("stderr", ""),
        }
        rendered = template.render(context)
        return rendered.lower() in ["true", "1", "yes"]
    except Exception as e:
        logger.error(f"Gate condition evaluation failed: {e}")
        return False
```

---

### 4. Webhook Ingestion (Inbound Triggers)

```python
# POST /api/workflows/{workflow_id}/trigger (inbound webhook)

@router.post("/api/workflows/{workflow_id}/trigger", tags=["Workflows"])
async def trigger_workflow_webhook(
    workflow_id: str,
    request: Request,
    x_mop_webhook_signature: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Inbound webhook endpoint for triggering a workflow.
    
    Security:
    - Slug-based lookup + HMAC-SHA256 verification
    - Raw body read before parsing
    - Timestamp validation (±5 min)
    """
    # Get raw body
    body = await request.body()
    
    # Parse header: "sha256=<hex>"
    if not x_mop_webhook_signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Invalid signature format")
    
    provided_sig = x_mop_webhook_signature[7:]
    
    # Verify webhook exists for this workflow
    hook = (query workflow_webhooks by workflow_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not configured")
    
    # Compute HMAC over raw body
    import hmac
    computed_sig = hmac.new(
        hook.secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    if not hmac.compare_digest(provided_sig, computed_sig):
        raise HTTPException(status_code=401, detail="Signature mismatch")
    
    # Parse payload
    try:
        payload = json.loads(body.decode()) if body else {}
    except:
        payload = {}
    
    # Timestamp validation (optional but recommended)
    if "timestamp" in payload:
        ts = int(payload["timestamp"])
        now = int(datetime.utcnow().timestamp())
        if abs(now - ts) > 300:  # 5 min window
            raise HTTPException(status_code=400, detail="Request expired")
    
    # Dispatch workflow
    run_id = await WorkflowRunService.dispatch_workflow_run(
        workflow_id,
        trigger_type="webhook",
        trigger_payload=payload,
        db=db
    )
    
    return {"workflow_run_id": run_id, "status": "dispatched"}
```

---

### 5. Integration Points with Existing Job System

#### Point 1: Job Completion Handler
**Location:** `agent_service/services/job_service.py` line ~1398 (`handle_job_completion()`)
**Existing call:** `await JobService._unblock_dependents(guid, db)`
**New integration:**

```python
# In job_service.py handle_job_completion()
if job.status == "COMPLETED":
    await JobService._unblock_dependents(guid, db)
    # NEW: also unblock workflow steps
    from . import workflow_service
    await workflow_service.WorkflowRunService._unblock_workflow_steps_after_job(guid, db)
```

#### Point 2: Job Creation
**Location:** `agent_service/services/job_service.py` line ~436 (`create_job()`)
**Integration:** Pass optional `workflow_run_id` and `workflow_run_step_id` when creating jobs from workflows
**No signature change needed** — these are optional fields on Job model

```python
# When WorkflowRun dispatches a job:
job_create = JobCreate(...)
job_result = await JobService.create_job(job_create, db)
step.job_guid = job_result["guid"]
```

#### Point 3: Job Dependency Model
**Existing:** `Job.depends_on` (list of GUIDs or Signal names) — used by `_unblock_dependents()`
**Unchanged:** Workflow jobs can use `depends_on` too if needed (for example, multiple upstream jobs)
**Workflow-specific:** Instead of manually setting `depends_on`, let WorkflowRun orchestrator manage it via DAG topology

#### Point 4: API Authentication
**Workflow CRUD routes:** Protected by `require_permission("workflows:write")` — operator/admin only
**Webhook triggers:** Unauthenticated, verified by HMAC-SHA256 signature only
**Rationale:** Webhooks are meant for CI/CD pipelines that don't have user credentials

---

### 6. Data Flow: Create → Dispatch → Gate → Complete

```
1. User or Webhook:
   POST /api/workflows/{id}/trigger
     ↓
2. WorkflowRunService.dispatch_workflow_run():
   - Create WorkflowRun (status=PENDING)
   - Create WorkflowRunStep for each DAG node
   - Topological sort: find root nodes (in_degree=0)
   - For each root, call _dispatch_workflow_step()
     ↓
3. _dispatch_workflow_step():
   - Fetch job definition
   - Call JobService.create_job()
   - Job created (status=PENDING)
   - Link step.job_guid = job.guid
   - WorkflowRun.status = RUNNING
     ↓
4. Job executes on node:
   - Node polls /work/pull
   - Node executes job in container
   - Node reports completion via /api/heartbeat
     ↓
5. JobService.handle_job_completion():
   - Store result in job.result (structured JSON)
   - Call _unblock_dependents() [existing: job-level BFS]
   - Call WorkflowRunService._unblock_workflow_steps_after_job() [NEW]
     ↓
6. _unblock_workflow_steps_after_job():
   - Find WorkflowRunStep owning this job
   - For each downstream node:
     a. If GATE node:
        - Evaluate condition (Jinja2) against job.result
        - If passes: mark PENDING, dispatch next
        - If fails: mark SKIPPED, mark descendants SKIPPED
     b. If JOB node:
        - Check all upstream deps satisfied
        - If yes: dispatch via _dispatch_workflow_step()
     ↓
7. WorkflowRun completion:
   - Query all steps in run
   - If all steps (COMPLETED or SKIPPED): run.status = COMPLETED
   - If any step FAILED: run.status = FAILED
   - Set completed_at timestamp
```

---

## Patterns to Follow

### Pattern 1: Reuse Job Dispatch
**What:** Workflow steps invoke `JobService.create_job()` directly, not a new job creation path.
**When:** Building all workflow job dispatch logic.
**Benefit:** Inherits Ed25519 signing, mTLS validation, resource limits, RBAC, capability matching without reimplementing.

### Pattern 2: Structured JSON Result Caching
**What:** Gate evaluation reads `job.result` (structured JSON) and caches summary in `WorkflowRunStep.result_summary`.
**When:** Job completion → gate evaluation.
**Benefit:** Gates don't need to re-query job; have local snapshot for offline evaluation.

### Pattern 3: BFS at Both Levels
**What:** Job-level BFS (`_unblock_dependents`) handles job chains; workflow-level BFS (`_unblock_workflow_steps_after_job`) handles DAG propagation.
**When:** Dispatching and unblocking.
**Benefit:** Clean separation — job system doesn't know about workflows; workflows layer on top.

### Pattern 4: Webhook Secret as Plain Text in DB
**What:** Store plain secret in `workflow_webhooks.secret`; compute HMAC-SHA256 over raw body.
**When:** Webhook creation and verification.
**Why:** Unlike passwords, secrets are randomly generated (not user-chosen), and HMAC doesn't reveal the secret even if attacker has the signature.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Workflow Runner as Separate Service
**What:** Building a standalone workflow engine that polls WorkflowRun state.
**Why bad:** Adds operational complexity, latency, and another component to monitor.
**Instead:** Embed workflow BFS in job_service.py as a side-effect of job completion.

### Anti-Pattern 2: Complex Condition Languages
**What:** Full Python eval() or Turing-complete expression language for gates.
**Why bad:** Security risk (arbitrary code execution), hard to audit, overkill for most gates.
**Instead:** Jinja2 template with restricted context ({result, exit_code, stdout, stderr}).

### Anti-Pattern 3: Depth Limit per Workflow
**What:** Each workflow defines its own max depth.
**Why bad:** Requires per-workflow configuration, adds UI complexity, opens DoS.
**Instead:** Global override (e.g., max 30 for all workflow jobs) hardcoded or in Config.

### Anti-Pattern 4: Webhook Signature in Query Param
**What:** `POST /trigger?sig=...`
**Why bad:** Signature logged in HTTP logs, exposed in browser history.
**Instead:** HTTP header `X-MOP-Webhook-Signature: sha256=<hex>`.

---

## Scalability Considerations

| Concern | At 10 workflows | At 100 workflows | At 1000 workflows |
|---------|-----------------|------------------|-------------------|
| **DAG size** | Steps: 5–20 | Steps: 10–100 | Steps: 50–500 |
| **Run dispatch** | Topological sort ~1ms | Topo sort ~5ms | Topo sort ~50ms |
| **Gate eval** | JSON parse ~0.1ms | Batch parse ~10ms | Jinja2 cache recommended |
| **Step lookup** | Simple query; no index | Index (run_id, node_id) | Partition by run_id |

**Recommended indices:**
```sql
CREATE INDEX ix_workflow_run_steps_run_node 
  ON workflow_run_steps(run_id, node_id);

CREATE INDEX ix_workflows_active 
  ON workflows(is_active, created_at DESC);

CREATE INDEX ix_workflow_webhooks_workflow 
  ON workflow_webhooks(workflow_id);
```

---

## Suggested Build Order (Phases)

### Phase 1: Data Model (1–2 days)
**Deliverables:** Schema + ORM models
- Workflow, WorkflowRun, WorkflowRunStep, WorkflowWebhook tables
- Pydantic models: WorkflowCreate, WorkflowResponse, WorkflowRunResponse
- DB migrations for existing deployments

**Why first:** Unblocks parallel development; enables E2E tests.

### Phase 2: BFS Runner (2–3 days)
**Deliverables:** WorkflowRunService with dispatch + unblock logic
- `dispatch_workflow_run()` (topological sort, root dispatch)
- `_unblock_workflow_steps_after_job()` (gate eval, downstream dispatch)
- `_evaluate_gate_condition()` (Jinja2 gates)
- Integration hook in `job_service.handle_job_completion()`
- Unit tests for DAGs (linear, branching, gate conditions)

**Why second:** Core logic; enables Phase 3 and UI to build independently.

### Phase 3: Webhook Triggers (1–2 days)
**Deliverables:** Inbound webhook endpoint + HMAC verification
- `POST /api/workflows/{workflow_id}/trigger` endpoint
- Webhook secret generation + storage
- HMAC-SHA256 verification with constant-time comparison
- Timestamp validation
- Integration tests with curl

**Why third:** Depends on Phase 2; enables CI/CD integrations.

### Phase 4: REST CRUD (1 day)
**Deliverables:** Workflow definition CRUD
- `POST/GET/PATCH/DELETE /api/workflows`
- Webhook registration endpoints
- List runs, list steps endpoints

**Why fourth:** Ready once Phase 1 & 2 work.

### Phase 5: Canvas Editor UI (3–5 days)
**Deliverables:** React visual DAG editor
- Draggable node/edge canvas (React Flow or similar)
- Node palette + condition editor for gates
- DAG serialization → `dag_json`
- Test run feature
- Live preview of dispatch order

**Why last:** UI can iterate against stable API from Phases 1–4.

---

## Sources & References

**Workflow Orchestration Architecture:**
- [Temporal vs Airflow: Which Orchestrator Fits Your Workflows?](https://www.zenml.io/blog/temporal-vs-airflow)
- [Workflow Orchestration Platforms: Kestra vs Temporal vs Prefect (2025 Guide)](https://procycons.com/en/blogs/workflow-orchestration-platforms-comparison-2025/)
- [DAG - Argo Workflows Documentation](https://argo-workflows.readthedocs.io/en/latest/walk-through/dag/)
- [Declarative Workflow Design (DAGs) - Hatchet Documentation](https://docs.hatchet.run/home/dags)

**Conditional Execution & IF Gates:**
- [How to Use Argo Workflows for Complex DAG-Based Batch Processing](https://oneuptime.com/blog/post/2026-02-09-argo-workflows-dag-batch-processing/view)
- [Building a DAG-Based Workflow Execution Engine in Java](https://medium.com/@amit.anjani89/building-a-dag-based-workflow-execution-engine-in-java-with-spring-boot-ba4a5376713d)

**Webhook Security (HMAC-SHA256):**
- [Webhook Security Best Practices: The Complete Guide](https://gethookmesh.io/blog/webhook-security-best-practices/)
- [Hash-based Message Authentication Code (HMAC) - Docs](https://webhooks.fyi/security/hmac)
- [How to Implement SHA256 Webhook Signature Verification](https://hookdeck.com/webhooks/guides/how-to-implement-sha256-webhook-signature-verification)
- [Webhook Security Fundamentals: Complete Protection Guide [2026]](https://www.hooklistener.com/learn/webhook-security-fundamentals)
