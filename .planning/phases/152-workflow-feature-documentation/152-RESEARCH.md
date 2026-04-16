# Phase 152: Workflow Feature Documentation - Research

**Researched:** 2026-04-16
**Domain:** Technical Documentation (API Reference, Feature Guides, Runbooks, Developer Guides)
**Confidence:** HIGH

## Summary

Phase 152 documents all workflow features built in Phases 146–150, plus the triggers and parameters completed in Phase 149. The project already has established documentation patterns via the MkDocs-based Axiom docs site, with feature guides for Jobs, Job Scheduling, Foundry, and RBAC. Workflow documentation follows the same patterns: hand-written prose + code examples in fenced blocks, feature guide structure from `docs/docs/feature-guides/jobs.md`, and runbook structure from `docs/docs/runbooks/jobs.md`.

The implementation is a **multi-file decomposition** (not a single flat file) with six dedicated workflow documentation pages under `docs/docs/workflows/`, plus updates to the existing API reference and a new operational runbook. The CONTEXT.md decisions lock the structure and API depth; all content is now discoverable in the codebase (Phases 146–150 complete, Phase 149 live and tested).

**Primary recommendation:** Build documentation in the prescribed six-file structure, following established patterns from Jobs/Foundry guides. Use the workflow_service.py BFS dispatch algorithm and 7-table schema as the authoritative source for internals. Leave trigger configuration UI guide blank with TODO callouts (Phase 151 deferred).

## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Doc structure**: Dedicated `docs/docs/workflows/` directory with six sub-pages (NOT a single flat file):
   - `index.md` — overview and navigation hub
   - `concepts.md` — step types, gate types, DAG model, execution lifecycle diagram
   - `user-guide.md` — dashboard monitoring (Workflows list, WorkflowDetail, WorkflowRunDetail, step log drawer)
   - `operator-guide.md` — observable behaviour, status transitions, cron/webhook setup via API
   - `developer-guide.md` — internals: BFS dispatch, CAS guards, state machine, cascade cancellation, mermaid ERD
   - (Plus `runbooks/workflows.md` and updates to `api-reference/index.md`)

2. **API reference depth**: 
   - `api-reference/index.md` gets real content (workflow API is inaugural section)
   - Per-endpoint: method + path + one-line description + key request fields (not exhaustive schema dumps)
   - One annotated example JSON per endpoint group (CRUD, management, webhooks, runs), not one per endpoint
   - HMAC webhook signing: describe mechanism only (what it is, where to find secret) — no worked curl example
   - Complex request bodies (create workflow with steps + edges + parameters): include realistic annotated example JSON

3. **User guide scope**:
   - Focus ONLY on **monitoring side** — creating workflows is Phase 151 (visual DAG editor, deferred)
   - Walkthrough: Workflows list → WorkflowDetail (run history) → WorkflowRunDetail (live overlay + step log drawer)
   - Gate types: explain each with "when to use this" rationale section (IF_GATE, AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT)
   - Trigger setup (cron, webhooks): **skip for now** — mark with TODO callout: `> TODO: This section will be completed when the workflow trigger configuration UI ships (Phase 151).`
   - Screenshots: include placeholder callouts for each major view (real screenshots post-build)

4. **Developer vs. operator separation**:
   - Two separate files: `operator-guide.md` and `developer-guide.md`
   - **Operator-guide**: observable behaviour, status state machine (6 statuses), cancellation propagation, monitoring via API/dashboard, Phase 149 parameter injection overview
   - **Developer-guide**: internals, BFS wave dispatch algorithm, compare-and-swap concurrency guards, cascade cancellation logic, lazy import pattern (circular dep avoidance), mermaid ERD of all 7 tables
   - Document **full intended design** including Phase 149 in-progress features (cron, webhook HMAC, WORKFLOW_PARAM_* injection) — verify Phase 149 landed before publishing

### Claude's Discretion

- Exact heading/section names within each file
- Whether `concepts.md` or `developer-guide.md` carries the step-type shape descriptions
- Mermaid diagram style for ERD and lifecycle state machine
- Which example workflow to use for annotated JSON (suggest: 3-step linear script → IF gate → parallel fan-out)

### Deferred Ideas (OUT OF SCOPE)

- Workflow trigger configuration UI guide — Phase 151 (Visual DAG Editor)
- Workflow creation walkthrough (drag-and-drop DAG editor) — Phase 151
- Full OpenAPI/Swagger auto-generation for API reference — hand-written docs are the pattern

---

## Standard Stack

### Documentation Framework
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| MkDocs | 1.5+ | Static site generator for Axiom docs | Project's established doc site; Material theme |
| Material for MkDocs | 9.x | Responsive Material Design theme | Already in use; supports mermaid, offline plugins |
| Mermaid | 10.x+ (via pymdownx.superfences) | Diagrams-as-code (ERD, state machines) | Embedded in MkDocs markdown; no external deps |

### Existing Doc Patterns (Source of Truth)
| Document | Location | Pattern | Use For |
|----------|----------|---------|---------|
| Jobs Feature Guide | `docs/docs/feature-guides/jobs.md` | Intro + concepts + UI walkthrough + API section | Follow this structure for `user-guide.md` |
| Jobs Runbook | `docs/docs/runbooks/jobs.md` | Quick ref table + symptom-driven troubleshooting | Follow this for `workflows.md` runbook |
| Foundry Feature Guide | `docs/docs/feature-guides/foundry.md` | Concepts + step-by-step UI operations | Pattern for multi-concept guides |

### Navigation (mkdocs.yml)
MkDocs nav is the source of truth for page registration. New workflow docs MUST be registered in `mkdocs.yml` under `Feature Guides` and `Runbooks` sections.

---

## Architecture Patterns

### Recommended Documentation Hierarchy

```
docs/docs/
├── workflows/
│   ├── index.md              # Overview, quick-start, file index
│   ├── concepts.md           # Data model, step/gate types, DAG lifecycle
│   ├── user-guide.md         # Dashboard monitoring walkthrough
│   ├── operator-guide.md     # Status transitions, observable behaviour
│   └── developer-guide.md    # Internals, BFS, CAS, cascade cancellation, ERD
├── api-reference/
│   └── index.md              # (UPDATE) Add workflow API section here
└── runbooks/
    └── workflows.md          # (NEW) Operational runbook
```

### Content Sources (HIGH confidence — all discoverable in live code)

| Document Section | Source Location | What to Extract |
|------------------|-----------------|-----------------|
| Workflow API endpoints | `puppeteer/agent_service/main.py` (routes) | 14 workflow endpoints: CRUD, runs, webhooks, manual trigger |
| DB schema (7 tables) | `puppeteer/agent_service/db.py` | Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter, WorkflowWebhook, WorkflowRun, WorkflowStepRun |
| BFS dispatch algorithm | `puppeteer/agent_service/services/workflow_service.py` | `dispatch_workflow_run()` method, wave-based step dispatch |
| Step node types (6) | `puppeteer/dashboard/src/components/WorkflowStepNode.tsx` | SCRIPT, IF_GATE, AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT |
| Gate type rationales | `puppeteer/agent_service/services/workflow_service.py` (gate evaluation) | Conditional logic per gate type |
| UI views (3 read-only) | `puppeteer/dashboard/src/views/{Workflows,WorkflowDetail,WorkflowRunDetail}.tsx` | Dashboard monitoring walkthrough |
| Lifecycle state machine | `puppeteer/agent_service/services/workflow_service.py` | 6 states: RUNNING, COMPLETED, PARTIAL, FAILED, CANCELLED, (incomplete) |
| Trigger types (Phase 149) | `puppeteer/agent_service/main.py` (webhook endpoint) | MANUAL, CRON, WEBHOOK trigger types and HMAC signing |

### Status State Machine

Workflows have **six distinct statuses** (from requirements + code inspection):

| Status | Meaning | When Set | Transitions To |
|--------|---------|----------|----------------|
| **RUNNING** | Workflow executing; at least one step pending/assigned/running | On first dispatch | COMPLETED, PARTIAL, FAILED, CANCELLED |
| **COMPLETED** | All steps succeeded; all gates passed | When last step reports success, no failures | (terminal) |
| **PARTIAL** | Some branches failed but failures were isolated (IF gate took failure branch) | When final status consolidation happens with isolated failures | (terminal) |
| **FAILED** | Critical failure; caused cascading cancellation of downstream steps | When a non-isolated step fails (no IF gate absorbing it) | (terminal) |
| **CANCELLED** | User explicitly cancelled the run via dashboard/API | On `DELETE /api/workflows/{id}/runs/{run_id}` | (terminal) |
| **(incomplete)** | Workflow still initializing (steps being created in DB) | Brief transient state | RUNNING |

Source: REQUIREMENTS.md ENGINE-04, ENGINE-05, ENGINE-06; workflow_service.py `finalize_workflow_run()` logic.

### BFS Wave Dispatch Algorithm

From `workflow_service.py::dispatch_workflow_run()`:

1. **Initialization**: All steps with zero incoming edges marked ready for dispatch
2. **Wave loop**: While pending steps remain:
   - Identify all steps with all dependencies completed
   - Dispatch that "wave" of steps concurrently (no inter-wave ordering guarantee)
   - Mark them ASSIGNED; poll for completion
   - On completion, update graph and identify next wave
3. **Termination**: When no pending steps remain, finalize WorkflowRun status

**Concurrency safety**: Atomic SELECT...FOR UPDATE on WorkflowRun + step row-level locks prevent duplicate dispatch if multiple poll cycles hit simultaneously (ENGINE-03).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DAG layout for workflow visualization | Custom node positioning algorithm | dagre (via elkjs/dagre React Flow integration) | Non-trivial; many edge-crossing cases; React Flow handles panning/zooming |
| Step execution state machine | Homegrown status tracking via flags | Explicit RUNNING/COMPLETED/FAILED/CANCELLED states in DB | Easier to reason about; audit trail in DB; race condition-free |
| Webhook signature verification | Parsing HMAC header manually | `security.py::verify_webhook_signature()` (HMAC-SHA256, timestamp, nonce dedup) | Timing attacks, nonce replay, clock skew all handled; don't reinvent |
| Cyclic dependency detection | Manual graph traversal | `networkx.is_directed_acyclic_graph()` (workflow_service.py) | Detects all cycle types; used in validation |
| Cron scheduling | Custom interval loop | APScheduler (Phase 149 complete; integrated in scheduler_service) | Handles timezone, daylight savings, missed runs, backoff |
| Parameter environment injection | String concatenation into script | Fernet encryption + `WORKFLOW_PARAM_<NAME>` env vars (Phase 149 complete) | Secrets never touch script content; audit trail in DB |

---

## Common Pitfalls

### Pitfall 1: Confusing "No Incoming Edges" with "Ready to Dispatch"

**What goes wrong:** A developer sees a step with zero edges from other steps and assumes it can be dispatched immediately. In reality, a step might have multiple *incoming* edges that haven't completed.

**Why it happens:** The distinction between "outgoing" and "incoming" edges is easy to flip; the BFS algorithm uses a directed graph where an edge from A→B means "B depends on A", so B's *incoming* edges must complete first.

**How to avoid:** Always iterate incoming edges (`workflow_edges WHERE to_step_id = ?`) when determining if a step is ready. The wave dispatch loop in `workflow_service.py` is the reference implementation.

**Warning signs:** Tests pass with simple linear workflows but fail on fan-out or diamonds.

### Pitfall 2: Treating PARTIAL Status as a Bug

**What goes wrong:** A run completes with status PARTIAL (some branches failed, but failure was isolated to an IF gate branch), and the operator assumes something went wrong. In reality, PARTIAL is correct behaviour when cascading cancellation is limited by gate logic.

**Why it happens:** Developers familiar with simple pipelines expect all runs to be either fully green (COMPLETED) or fully red (FAILED); PARTIAL is a third state introduced by conditional gates.

**How to avoid:** Document PARTIAL clearly in operator-guide.md. Explain the IF gate's "failure branch absorption" semantics. Provide a concrete example: "Step A → IF gate → [Branch 1 (fails) | Branch 2 (succeeds)] → Step B → Step C. Result: PARTIAL (not FAILED) because the IF gate routed execution to the success path; downstream steps B and C run normally."

**Warning signs:** Operators filing support tickets about "unexplained PARTIAL runs" when in fact the workflow executed correctly.

### Pitfall 3: Forgetting Webhook HMAC Secret is One-Time Reveal

**What goes wrong:** Operator creates a workflow webhook, forgets to copy the plaintext secret, then tries to call the webhook. The secret is lost forever (only hash is stored in DB).

**Why it happens:** The secret is intentionally revealed only once (like AWS IAM access keys) for security; if lost, a new webhook must be created.

**How to avoid:** Emphasize in user-guide and runbook that the secret is one-time-only. Provide copy-to-clipboard guidance. Suggest: "Webhook creation modal should highlight: 'Copy this secret now. You will not be able to see it again. If you lose it, delete this webhook and create a new one.'"

**Warning signs:** Operators asking "where do I find my webhook secret?" in support channels.

### Pitfall 4: Step Node Type vs. Execution Type Confusion

**What goes wrong:** A developer creates a step with `node_type: PARALLEL` and `scheduled_job_id: <some-job>`, expecting the job to run in parallel with other jobs. In reality, `node_type` describes the *control flow* (how the DAG branches), not how the job's runtime behaves.

**Why it happens:** The term "PARALLEL" sounds like execution concurrency, but it's a DAG fan-out primitive. True concurrency happens when multiple wave dispatch cycles happen simultaneously.

**How to avoid:** Clarify in concepts.md that node types describe DAG topology only. A PARALLEL node *releases* multiple downstream branches for concurrent execution, but each branch still runs jobs sequentially unless they have independent incoming edges. Provide a diagram.

**Warning signs:** Jobs submitted to a PARALLEL node don't run in parallel; developer opens a GitHub issue asking "how do I parallelize my jobs?"

### Pitfall 5: Cascade Cancellation Propagates PAST Isolation Gates

**What goes wrong:** Step A fails → Step A's failure is supposed to be isolated by an IF gate → BUT the failure propagates past the gate and cancels everything downstream (incorrect).

**Why it happens:** The cascade cancellation logic in `workflow_service.py::cascade_cancel()` must *not* cross isolation gates (IF_GATE with failure branch, AND_JOIN, OR_GATE) when the failure is meant to be absorbed.

**How to avoid:** The logic in `cascade_cancel()` is correct in the codebase (Phase 147), but documentation must emphasize: "An IF gate with a failure branch is an isolation point. If the condition fails, execution routes to the failure branch; the primary branch is NOT cascaded as cancelled."

**Warning signs:** Entire workflows being marked FAILED when they should be PARTIAL; downstream steps getting CANCELLED when they should have run.

### Pitfall 6: Parameter Injection Timing (Phase 149)

**What goes wrong:** A step's job is dispatched before `WORKFLOW_PARAM_*` env vars are injected, so the job runs without parameters.

**Why it happens:** Parameter injection (Phase 149) happens at dispatch time (before job submission to node), but if the timing is off (e.g., params loaded late), the job might execute without them.

**How to avoid:** Document that WORKFLOW_PARAM_* injection is synchronous with job creation — parameters are resolved from WorkflowParameter rows and injected into JobCreate before dispatch. Never dispatch a step without first materializing its parameter values.

**Warning signs:** Tests pass on single-parameter workflows; parametrized fan-out with different params per branch fails.

---

## Code Examples

Verified patterns from official sources:

### API: Create Workflow (Annotated Example)

```json
{
  "name": "Data Pipeline with Conditional Processing",
  "steps": [
    {
      "scheduled_job_id": "job-extract-001",
      "node_type": "SCRIPT"
    },
    {
      "scheduled_job_id": "job-validate-001",
      "node_type": "SCRIPT"
    },
    {
      "scheduled_job_id": null,
      "node_type": "IF_GATE",
      "config_json": {
        "conditions": [
          {
            "operator": "contains",
            "path": "data_quality",
            "value": "PASS"
          }
        ]
      }
    },
    {
      "scheduled_job_id": "job-transform-001",
      "node_type": "SCRIPT"
    },
    {
      "scheduled_job_id": "job-load-001",
      "node_type": "SCRIPT"
    },
    {
      "scheduled_job_id": "job-rollback-001",
      "node_type": "SCRIPT"
    }
  ],
  "edges": [
    { "from_step_id": "0", "to_step_id": "1" },
    { "from_step_id": "1", "to_step_id": "2" },
    { "from_step_id": "2", "to_step_id": "3" },
    { "from_step_id": "2", "to_step_id": "5" },
    { "from_step_id": "3", "to_step_id": "4" }
  ],
  "parameters": [
    {
      "name": "target_database",
      "type": "string",
      "default_value": "production"
    },
    {
      "name": "batch_size",
      "type": "integer",
      "default_value": "1000"
    }
  ],
  "schedule_cron": "0 2 * * *"
}
```

**Explanation**: Extract → Validate → [IF success: Transform→Load | IF fail: Rollback]. Parameters passed as WORKFLOW_PARAM_target_database and WORKFLOW_PARAM_batch_size env vars to each step's job. Scheduled to run at 2 AM daily via cron.

Source: `puppeteer/agent_service/models.py::WorkflowCreate`; Phase 149 integration.

### Gateway Types: IF_GATE Configuration

```python
# From workflow_service.py::evaluate_if_gate()

config = {
  "conditions": [
    {
      "operator": "eq",
      "path": "status",
      "value": "success"
    },
    {
      "operator": "gt",
      "path": "record_count",
      "value": 100
    }
  ]
}

# Evaluates result.json at step's execution:
# ALL conditions must be true (AND logic) to take the primary branch
# If any condition fails, execution routes to the failure branch
```

### Webhook HMAC Signature Verification

```python
# From security.py

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.hmac import HMAC

def verify_webhook_signature(
    payload_bytes: bytes,
    signature_header: str,
    secret: bytes,
    timestamp: str,
    max_age_seconds: int = 300
) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.
    1. Check timestamp freshness (±5 min default)
    2. Reconstruct signature: HMAC-SHA256(secret, payload + timestamp)
    3. Compare against signature_header (timing-safe comparison)
    """
    import time
    ts = int(timestamp)
    if abs(time.time() - ts) > max_age_seconds:
        return False  # Stale timestamp
    
    msg = payload_bytes + timestamp.encode()
    h = HMAC(secret, hashes.SHA256())
    h.update(msg)
    expected_sig = h.finalize().hex()
    
    return hmac.compare_digest(expected_sig, signature_header)
```

### Dashboard View: Workflows List (React Pattern)

```typescript
// From Workflows.tsx
interface WorkflowResponse {
  id: string;
  name: string;
  steps: Array<{ id: string; node_type: string }>;
  last_run?: {
    status: 'RUNNING' | 'COMPLETED' | 'PARTIAL' | 'FAILED' | 'CANCELLED';
    started_at: string;
  };
}

// Fetch and render
const { data } = useQuery({
  queryKey: ['workflows', skip, limit],
  queryFn: async () => {
    const res = await authenticatedFetch(`/api/workflows?skip=${skip}&limit=${limit}`);
    return res.json();
  },
  refetchInterval: 30000, // Polls every 30s for latest run status
});

// Click row to navigate to /workflows/{workflowId}
const handleRowClick = (workflowId: string) => {
  navigate(`/workflows/${workflowId}`);
};
```

---

## State of the Art

### Workflow Execution Paradigm

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Jobs with sequential dependencies (Phase 145) | DAG-based conditional workflows with fan-out gates (Phase 146–150) | 2026-04-16 | Enables complex pipelines: conditional branches, parallel fan-out, signal waits |
| Manual parameter passing via script editing | Environment variable injection via WORKFLOW_PARAM_* (Phase 149) | 2026-04-16 | Scripts immutable; parameters injected at runtime; audit trail in DB |
| Cron scheduling only at job level | Workflow-level cron scheduling + manual trigger + webhooks (Phase 149) | 2026-04-16 | Entire workflows scheduled; webhook trigger enables external integrations |
| Single linear execution path | Status PARTIAL introduced for isolated gate failures (Phase 147) | 2026-04-16 | Workflows can "succeed with exceptions"; IF gate absorbs failure without cascading |

### Deprecated/Outdated (None - this is new feature area)

All workflow features are new in v23.0. No deprecated features to document.

---

## Open Questions

1. **Phase 149 Webhook UI** — Trigger configuration UI (cron schedule builder, webhook secret display, manual trigger form) is deferred to Phase 151. Should `operator-guide.md` include a "manual API trigger example" for operators who want to bypass the UI? (Recommendation: Yes — provide curl + Python SDK examples for manual webhook testing.)

2. **ERD Mermaid Complexity** — 7-table schema with 6 FKs is large for a diagram. Should we break it into two sub-diagrams (core workflow model vs. execution model) or single comprehensive ERD? (Recommendation: Single comprehensive ERD with clear grouping via comments.)

3. **Step Log Retention** — User guide mentions "step log drawer" (Phase 150 feature) but doesn't specify log retention period. Should `developer-guide.md` document that logs are keyed by job_guid and pruned after X days? (Recommendation: Mention in operator-guide.md's "Monitoring" section; exact retention policy in runbook.)

4. **Nested Workflow Calls** — Requirements mention "Cross-workflow dependencies" as v24.0 feature. Should v23.0 user-guide include a "Future: Nested Workflows" section, or is it cleaner to add that in v24.0? (Recommendation: Skip in v23.0; add in v24.0 docs.)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` + `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer && pytest tests/test_workflow*.py -x -q` |
| Full suite command | `cd puppeteer && pytest tests/test_workflow*.py tests/test_workflow_execution.py tests/test_workflow_triggers.py && cd dashboard && npm run test` |

### Phase Requirements → Test Map

**Note**: Phase 152 is documentation-only. No new backend/frontend code, so no new tests required. Tests for workflows themselves are in Phase 146–150 and all passing (45/45 per git log, 2026-04-16).

Documentation validation checklist (manual + linting):

| Check | Type | Command | Status |
|-------|------|---------|--------|
| Markdown linting (syntax errors) | manual/lint | `markdownlint docs/docs/workflows/*.md` | Not yet run; can use pre-commit hook if available |
| MkDocs site build (orphaned links, nav errors) | integration | `mkdocs build --strict` | Must pass before PR merge |
| Code example syntax (YAML/JSON blocks) | linting | `python3 -m json.tool < example.json` | Validate examples |
| Link rot (internal wiki links, GitHub URLs) | integration | Manual spot-check; consider `markdown-link-check` | Deferred; can add to pre-commit |

### Sampling Rate

- **Per task commit:** No code commits; doc commits don't need test runs
- **Per wave merge:** Run `mkdocs build --strict` to catch nav/link errors
- **Phase gate:** MkDocs build passing + manual review of all 6 pages against CONTEXT.md decisions

### Wave 0 Gaps

None. All workflow implementation is complete (Phases 146–150 done, Phase 149 in production). Documentation is pure content creation (no code dependencies).

---

## Sources

### Primary (HIGH confidence)

- **Context7 / Codebase inspection**:
  - `puppeteer/agent_service/main.py` — 14 workflow API endpoints, response models
  - `puppeteer/agent_service/db.py` — 7 workflow DB tables (Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter, WorkflowWebhook, WorkflowRun, WorkflowStepRun)
  - `puppeteer/agent_service/services/workflow_service.py` — BFS dispatch, validation, cascade cancellation
  - `puppeteer/dashboard/src/views/{Workflows,WorkflowDetail,WorkflowRunDetail}.tsx` — Read-only UI views
  - `puppeteer/dashboard/src/components/WorkflowStepNode.tsx` — 6 step node types
  - `.planning/REQUIREMENTS.md` — 32 workflow requirements (23 implemented in Phases 146–150)

- **Established Patterns (HIGH confidence)**:
  - `docs/docs/feature-guides/jobs.md` — existing feature guide structure to follow
  - `docs/docs/runbooks/jobs.md` — existing runbook structure to follow
  - `docs/mkdocs.yml` — nav structure, plugin config
  - CONTEXT.md (2026-04-16) — locked decisions for Phase 152 scope

### Secondary (MEDIUM confidence)

- Phase 149 completion (git log 2026-04-16) — triggers, webhooks, HMAC signing, parameters confirmed live
- Phase 150 completion (git log 2026-04-16) — all read-only UI views confirmed complete and tested
- REQUIREMENTS.md Phase mapping — 32/32 requirements mapped to phases

---

## Metadata

**Confidence breakdown:**
- Standard stack (MkDocs, Material, existing patterns): **HIGH** — all tools confirmed in live codebase
- Architecture (6-file structure, content sources, test patterns): **HIGH** — CONTEXT.md locked decisions, sources verified in code
- Pitfalls (state machine, cascade cancellation, gate isolation): **HIGH** — extracted from workflow_service.py and requirements
- API reference content: **HIGH** — all 14 endpoints discoverable in main.py, tested in Phase 150
- User guide content: **HIGH** — UI views exist and tested; walkthrough can be written from code inspection
- Developer guide content (BFS, CAS, ERD): **HIGH** — algorithm and schema in live code; documented in workflow_service.py comments

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (workflow feature area stable; Phase 151 deferred to later sprint; API/schema locked in Phase 146–150)

