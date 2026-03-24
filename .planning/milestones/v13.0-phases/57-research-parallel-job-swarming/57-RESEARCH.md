# Phase 57: Research — Parallel Job Swarming

**Researched:** 2026-03-24
**Domain:** Distributed job dispatch, fan-out swarming, pull-model architecture
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Two distinct patterns must be researched: **fan-out** (same job dispatched to all matching nodes simultaneously) and **work-queue** (N tasks distributed across M workers via shared queue)
- Core use case is fan-out — "run the same job on multiple nodes simultaneously"
- Campaign concept: the doc must define the distinction between today's tag targeting (dispatching to one node at a time with a matching tag) and a proper "campaign" that dispatches to all matching nodes at once
- Results model: N separate job records grouped under a parent swarm/campaign ID (not a single job with sub-results)
- Document format: lives at `.planning/phases/57-research-parallel-job-swarming/57-RESEARCH.md`
- Required sections: use case analysis, pull-model impact, data model sketch, brief comparison with external systems, complexity/value recommendation
- Doc must be readable by someone with no prior swarming context
- Tiered recommendation: fan-out swarming as next milestone feature; defer work-queue/sharding to a future phase
- Include rough phase/plan count estimate for fan-out implementation
- Include draft API endpoint signature for fan-out dispatch (e.g., `POST /api/jobs/swarm`)
- Cover **both** race conditions and backpressure in pull-model analysis
- Barrier synchronisation is required: swarm transitions PENDING → RUNNING (7/10) → COMPLETE/PARTIAL
- Work-queue pattern: problem-definition only — identify it, explain why harder in pull model, explicitly defer detailed design

### Claude's Discretion
- Exact section headings and prose structure within each doc section
- Which external systems to include in the brief comparison
- Whether to include sequence diagrams or pseudo-code in the pull-model analysis

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SWRM-01 | Design doc produced covering parallel job swarming use case analysis (is fan-out + campaigns sufficient or is there a genuine gap?) | Section: Use Case Analysis — defines fan-out, work-queue, and campaign patterns; identifies when each is needed |
| SWRM-02 | Design doc covers architectural impact on the pull model (what breaks, backpressure, ordering/barrier synchronisation) | Section: Pull-Model Impact — covers race conditions, backpressure, and barrier synchronisation state machine |
| SWRM-03 | Design doc delivers a complexity/value trade-off recommendation with clear next-step guidance | Section: Complexity/Value Recommendation — tiered build path, effort estimate, draft API shape |
</phase_requirements>

---

## Summary

Master of Puppets today dispatches exactly one job to exactly one node per `/work/pull` cycle. This is deliberate and correct for the current use case. The question this phase answers is: **what would it cost to make one job dispatch to all matching nodes at once, and is it worth doing?**

Two patterns are relevant. The first is **fan-out / campaign dispatch**: a single submitted job becomes N child jobs, one per matching node, all running simultaneously. The parent is a logical grouping record. This is the pattern operators actually want — "apply this config change to all production nodes right now" or "run this diagnostic on every node tagged `gpu`". The second pattern is **work-queue distribution**: a pool of M independent tasks is spread across N workers, each task executed by exactly one worker. This is harder in a pull model and is explicitly out of scope for this document beyond a problem-statement sketch.

The core finding is that fan-out swarming is **buildable on the existing architecture** with moderate complexity. The `Job` table already carries `originating_guid` (resubmit lineage) that directly maps to the concept of a swarm parent. The tag-targeting system already identifies eligible nodes. The main engineering challenge is not data modelling — it is the **race condition** inherent in a pull model: N nodes all poll simultaneously, and without a swarm-aware reservation mechanism, multiple nodes could each claim a different child or the same child job incorrectly. The recommendation is to implement fan-out as Tier 1 of a future milestone, defer work-queue to Tier 2 or later.

**Primary recommendation:** Implement fan-out swarming as a dedicated milestone (estimated 3 phases / 9–12 plans). Represent each swarm as a `SwarmRecord` parent with N child `Job` rows, extend `pull_work` to recognise swarm-mode child jobs and prevent double-assignment, and surface aggregate swarm status in the Jobs UI. Work-queue distribution requires a push-or-lease model incompatible with the current pure-pull architecture and should be deferred.

---

## Use Case Analysis

### Today's Behaviour: Tag Targeting is Not Fan-Out

When an operator dispatches a job with `target_tags: ["gpu"]`, the system finds **the first eligible node** with that tag and assigns the job exclusively to it. This is correct serial single-node dispatch. The job cannot be claimed by a second node. If five nodes share the `gpu` tag, four are idle while one runs.

This is not fan-out. It is tag-filtered single dispatch.

### Pattern 1: Fan-Out / Campaign Dispatch

**Definition:** One operator action creates N child jobs — one per matching node — all with `PENDING` status simultaneously. The operator sees a single campaign/swarm record in the dashboard with aggregate status (e.g., "7/10 COMPLETE"). Each child job runs independently, and all N run concurrently.

**When it is the right pattern:**
- "Run this security patch script on all 40 production nodes, now"
- "Execute this diagnostic on every node tagged `web-tier` before the deployment window"
- "Push a config change to all nodes in env `staging` simultaneously"
- "Audit every node's Python version at the same time so results are time-comparable"

The operator's intent is: **all eligible nodes, all at once, results grouped together**.

**When today's tag targeting is sufficient:**
- "Run this ML job on any one `gpu` node" — any eligible node is fine, no need for all
- "Execute this task on exactly one backup node" — resource competition exists, only one node should run it
- "Retry failed job on a different node" — already handled by `originating_guid`

**Conclusion:** Tag targeting and fan-out solve different problems. Tag targeting selects *any one* eligible node. Fan-out selects *all* eligible nodes. There is no redundancy — they are complementary dispatch strategies.

### Pattern 2: Work-Queue Distribution

**Definition:** A pool of M independent heterogeneous tasks (e.g., process 1,000 different files) is distributed across N workers. Each task is processed by exactly one worker. Workers are interchangeable consumers.

**When it is the right pattern:**
- Batch processing pipelines with per-item work
- Parallelising a single large computation across many workers
- Map-reduce style workloads

**Why it is harder in MoP's pull model:** In a pure pull model, workers select work rather than having work assigned to them. For work-queue semantics, a worker must claim an item atomically such that no other worker takes the same item. This requires either a push mechanism (server pushes to a specific worker) or a lease/claim mechanism (worker grabs a lock on an item before committing to run it). Neither exists today. The current `/work/pull` returns a job and immediately sets it to `ASSIGNED` — this works for single-node dispatch because only one assignment per job is valid. For work-queue, you need atomic "claim one task from pool" semantics with per-item locking.

**Recommendation:** Define work-queue as a distinct pattern. Defer detailed design. The complexity/value trade-off section covers this explicitly.

### The Campaign Concept

A **campaign** is the user-facing label for a fan-out swarm. It is how an operator thinks about the operation: "I'm running a campaign on all gpu nodes". Internally it maps to: one `SwarmRecord` parent + N child `Job` rows.

The distinction from today:

| Dimension | Today (tag targeting) | Campaign (fan-out) |
|-----------|----------------------|-------------------|
| How many nodes run the job? | 1 (first eligible) | All eligible |
| What does the operator see? | One job row | One campaign row + N child job rows |
| When does work start? | When first eligible node polls | All N child jobs enter PENDING simultaneously |
| Aggregate status | Job-level only | Swarm-level: X/N COMPLETE |
| Retries | Per-job | Per-child-job (independent) |

---

## Pull-Model Impact

This section is the core engineering analysis. The pull model means **nodes initiate all connections**. The server never pushes work. This creates specific challenges when N jobs must start simultaneously across N nodes.

### Race Condition: Double-Assignment

**The problem:** Suppose a swarm creates 10 child jobs for 10 eligible nodes. All 10 nodes happen to poll within the same second. Today's `pull_work` runs a `SELECT ... WHERE status = 'PENDING' LIMIT 50` and picks the first eligible job. If all 10 child jobs are visible to all 10 nodes (because child jobs carry `target_tags` but not `target_node_id`), nodes will race. Node A might claim child job 3, but Node B might also see child job 3 still as PENDING before Node A's commit completes.

**Is this actually a problem today?** No — today each job is intended for *one* node. Even if two nodes race on the same job, one wins the commit, the other finds the job already ASSIGNED on its next poll. But with swarming, we want each child job to go to a *specific* node, not just *any* node.

**Solution approaches:**

*Option A — Pre-pin at swarm creation time:* When `POST /api/jobs/swarm` is received, query all eligible ONLINE nodes immediately. Create one child `Job` per node with `target_node_id` set to that specific node. No race condition: each child job can only be claimed by its designated node. This is the **recommended approach** for fan-out swarming.

The existing `Job.target_node_id` column already exists (added in an earlier phase for explicit node targeting). The existing `pull_work` eligibility check already filters `(Job.node_id == None) | (Job.node_id == node_id)`. Pre-pinning requires no schema change and minimal logic change.

*Option B — Pessimistic locking at poll time:* Use `SELECT ... FOR UPDATE SKIP LOCKED` (Postgres) to atomically claim a job. This prevents double-assignment but requires Postgres-specific SQL and does not work cleanly with SQLite. It also still allows any node to claim any child job, which breaks the "each node runs its own copy" semantic.

*Option C — Swarm-reserved status:* Introduce `SWARM_PENDING` as a job status that is only visible to the designated `target_node_id`. This adds a new status value but does not require `SELECT FOR UPDATE`.

**Recommendation:** Option A (pre-pin at swarm creation) is the cleanest fit. It requires no new job statuses, uses existing `target_node_id`, and is compatible with both SQLite and Postgres. The trade-off is that node availability is snapshot-assessed at swarm creation: nodes that come online after dispatch don't join the swarm. This is acceptable behaviour.

```
Swarm Creation Sequence (pre-pin approach):

POST /api/jobs/swarm
  │
  ├─ Query: SELECT nodes WHERE status='ONLINE' AND tags match swarm target_tags
  │   → Returns [node_alpha, node_beta, node_gamma]
  │
  ├─ Create SwarmRecord (parent):
  │   swarm_id = uuid4()
  │   status = 'PENDING'
  │   total_nodes = 3
  │   completed_nodes = 0
  │
  ├─ Create Job for node_alpha (target_node_id='node_alpha', swarm_id=swarm_id, status='PENDING')
  ├─ Create Job for node_beta  (target_node_id='node_beta',  swarm_id=swarm_id, status='PENDING')
  └─ Create Job for node_gamma (target_node_id='node_gamma', swarm_id=swarm_id, status='PENDING')

node_alpha polls /work/pull:
  SELECT jobs WHERE status='PENDING' AND (node_id IS NULL OR node_id='node_alpha')
  → Claims its pre-pinned child job
  → No race: node_beta cannot claim node_alpha's child job
```

### Backpressure: Nodes at Concurrency Limit

**The problem:** When a swarm is dispatched, some target nodes may already be at their concurrency limit (default: 5 running jobs). Today's `pull_work` simply returns `PollResponse(job=None)` when `active_count >= concurrency`. A pre-pinned child job will sit in `PENDING` until the node has capacity and polls again. This is actually correct behaviour — the job waits in queue.

**However**, there are two sub-problems:

1. **Swarm partial start:** The swarm's N child jobs may start staggered if some nodes are busy. The aggregate status PENDING → RUNNING transition fires when *any* child starts, not when *all* children start. The swarm UI must show a "X/N started" counter rather than a binary RUNNING state.

2. **Dispatch timeout interaction:** The existing `dispatch_timeout_minutes` column on `Job` sets a deadline for assignment. A busy node that doesn't poll within the dispatch timeout window will have its child job expire. The swarm must handle partial completion (some children timed out, some completed) — hence the PARTIAL aggregate status.

**Recommendation:** Allow staggered start. Define swarm aggregate status as:
- `PENDING` — no child job has been assigned yet
- `RUNNING` — at least one child job is ASSIGNED or COMPLETED, not all COMPLETED/FAILED
- `COMPLETE` — all child jobs are COMPLETED
- `PARTIAL` — all child jobs have reached terminal status, at least one is FAILED/TIMED_OUT and at least one is COMPLETED
- `FAILED` — all child jobs failed

Backpressure is already handled correctly by the existing concurrency limit logic. No changes needed to the core pull mechanism.

### Barrier Synchronisation: Swarm Aggregate Status

**The problem:** How does the `SwarmRecord` know when to transition aggregate status? The server never pushes — it only learns a job completed when the node calls `POST /api/jobs/{guid}/result`. The swarm aggregate must be recomputed at that point.

**Proposed mechanism:** When a result is received for a job that has a `swarm_id`, the result handler triggers a swarm status recomputation:

```python
# In result-receipt handler (job_service.py or swarm_service.py):
if job.swarm_id:
    await SwarmService.recompute_aggregate(job.swarm_id, db)
```

`recompute_aggregate` runs a single query:

```python
# Pseudocode
children = SELECT * FROM jobs WHERE swarm_id = :swarm_id
terminal = [j for j in children if j.status in ('COMPLETED', 'FAILED', 'TIMED_OUT', 'DEAD_LETTER')]
running  = [j for j in children if j.status == 'ASSIGNED']

if len(terminal) == len(children):
    completed = [j for j in terminal if j.status == 'COMPLETED']
    if len(completed) == len(children):
        new_status = 'COMPLETE'
    elif len(completed) > 0:
        new_status = 'PARTIAL'
    else:
        new_status = 'FAILED'
elif running or len(terminal) > 0:
    new_status = 'RUNNING'
else:
    new_status = 'PENDING'

UPDATE swarm_records SET status = new_status, completed_nodes = len(terminal)
```

This is a **polling-free, event-driven barrier**: the barrier resolves naturally as child results arrive. No background job or cron sweep is required.

**Atomicity concern:** If two child jobs complete near-simultaneously and both trigger `recompute_aggregate` concurrently, there is a potential TOCTOU issue. Mitigation: run the recompute inside the same DB transaction as the result commit, or use optimistic concurrency on `SwarmRecord.completed_nodes`.

---

## Data Model Sketch

This section sketches the minimal schema additions required. No implementation here — this is input to the planner.

### New Table: `swarm_records`

```
swarm_records
├── swarm_id          TEXT PRIMARY KEY   -- UUID
├── name              TEXT NULLABLE      -- operator label, e.g. "Patch campaign Oct 2026"
├── status            TEXT NOT NULL      -- PENDING | RUNNING | COMPLETE | PARTIAL | FAILED
├── target_tags       TEXT NULLABLE      -- JSON list — tags used to select nodes at creation
├── total_nodes       INT NOT NULL       -- number of child jobs created
├── completed_nodes   INT DEFAULT 0      -- terminal child count (for progress display)
├── created_by        TEXT NOT NULL      -- operator username
├── created_at        DATETIME           -- swarm creation timestamp
├── completed_at      DATETIME NULLABLE  -- when all children reached terminal status
└── scheduled_job_id  TEXT NULLABLE      -- FK to ScheduledJob if triggered by scheduler
```

### Additions to Existing `Job` Table

Two columns needed, both nullable (backward compatible, no migration required for fresh installs, one-line ALTER for existing):

```
jobs
├── swarm_id          TEXT NULLABLE  -- FK to swarm_records.swarm_id; NULL for non-swarm jobs
└── (target_node_id already exists — used for pre-pinning, no addition needed)
```

The `originating_guid` pattern already establishes this lineage pattern in the codebase. `swarm_id` is the swarm equivalent: a FK that groups child jobs under their parent swarm.

### Relationship

```
SwarmRecord 1 ──── N Job (where Job.swarm_id = SwarmRecord.swarm_id)
                         Each child Job has target_node_id = specific node
                         Each child Job is an independent Job (has own guid, status, result)
```

### What Does NOT Change

- `Job` schema is otherwise unchanged — child swarm jobs are normal jobs that happen to carry a `swarm_id`
- `ExecutionRecord` is unchanged — each child job's execution history is captured per-job as today
- `/work/pull` logic is largely unchanged — pre-pinning via `target_node_id` already works
- Existing single-dispatch jobs are unaffected — `swarm_id IS NULL` means "normal job"

---

## Brief Comparison with External Systems

### Celery (Python Task Queue)

Celery uses a `group()` primitive to dispatch N tasks that execute in parallel across available workers. A `chord()` adds a callback that fires when all group members complete — this is Celery's barrier synchronisation. Celery uses a message broker (Redis, RabbitMQ) as the queue; workers pull from it. The broker provides atomic item-claim semantics (`BRPOP` on Redis, message acknowledgement on AMQP), eliminating the double-assignment race. MoP's equivalent of `chord()` is the `recompute_aggregate` trigger on result receipt.

**Key difference:** Celery workers are fungible (any worker can take any task). MoP nodes are not — a child job is pre-pinned to a specific node because the node may have specific hardware, tags, or environment. This makes MoP's fan-out semantically different from Celery's group: Celery distributes work *across* workers; MoP replicates work *to all* matching nodes.

### Kubernetes Jobs (Parallel Batch)

Kubernetes Jobs support `parallelism` and `completions` fields. A job with `completions: 10, parallelism: 3` runs 10 pods, 3 at a time. For work-queue patterns, Kubernetes supports indexed jobs where each pod gets a unique index. Kubernetes uses a Deployment/ReplicaSet controller loop to ensure the desired number of completions is reached, retrying failed pods automatically.

**Key difference:** Kubernetes Jobs target homogeneous compute (any pod can run the job). MoP's fan-out targets heterogeneous named nodes. Kubernetes has no concept of "run this on *that specific node* AND *that other specific node*" without node affinity/taints — a more complex construct. MoP's pre-pinning is cleaner for the named-node use case.

**Relevant pattern borrowed:** Kubernetes's aggregate `Complete` condition (firing when `succeeded >= completions`) directly maps to MoP's `recompute_aggregate` barrier. The conceptual model is identical.

### Ray (Distributed Python Framework)

Ray uses `@ray.remote` decorators and `ray.get([futures])` to fan out tasks and collect results. Ray manages scheduling, retries, and result collection transparently. The barrier is `ray.get()` — it blocks until all submitted futures complete.

**Key difference:** Ray is a same-cluster distributed computing framework; all workers share a Ray cluster. MoP nodes are edge/remote agents with intermittent connectivity. Ray assumes low-latency, high-reliability connections to a central scheduler. MoP assumes nodes may be slow-polling or temporarily unavailable — hence the pull model rather than Ray's push-via-gRPC model.

**Relevant insight:** Ray's `ray.get([task1.remote(), task2.remote(), task3.remote()])` is functionally identical to MoP's swarm dispatch + barrier. The structural difference is where the wait happens: Ray blocks the calling code; MoP stores aggregate state in `swarm_records` and updates it asynchronously.

### Summary

| System | Fan-Out Model | Race Prevention | Barrier |
|--------|--------------|-----------------|---------|
| Celery | `group()` to fungible workers | Broker atomic claim (BRPOP/AMQP ACK) | `chord()` callback |
| Kubernetes | `parallelism + completions` | API server serialises pod creation | `Complete` condition check |
| Ray | `@ray.remote` fan-out | Central scheduler, no shared queue | `ray.get()` blocking |
| MoP (proposed) | Pre-pinned child jobs per node | `target_node_id` pre-assignment at creation | `recompute_aggregate` on result receipt |

MoP's approach is simpler than all three because it eliminates the distributed queue entirely: each node has exactly one child job waiting for it, so there is nothing to race over.

---

## Complexity / Value Recommendation

### Value Assessment

Fan-out swarming addresses a clear operational need that cannot be met today: "push a change to all N nodes simultaneously and see a unified result". This is a standard capability in any node management platform (Ansible, Puppet, Salt, Fleet). Its absence is felt most when:
- Running security patches across a fleet
- Running post-deployment verification scripts on all nodes
- Performing scheduled fleet-wide audits

Without it, operators must either: (a) dispatch N separate jobs manually, (b) write a single job that orchestrates N nodes from within itself (fragile, breaks the security model), or (c) use a scheduled job that only hits one node per fire (doesn't scale).

**Verdict: HIGH value.** The use case is real, recurring, and cannot be adequately substituted by existing features.

### Complexity Assessment

| Component | Complexity | Notes |
|-----------|------------|-------|
| `swarm_records` table | LOW | ~8 columns, standard ORM, `create_all` handles fresh installs |
| `Job.swarm_id` column | LOW | One nullable column, one-line ALTER for existing DBs |
| `POST /api/jobs/swarm` endpoint | MEDIUM | Fan-out logic: query nodes, create N jobs, create SwarmRecord atomically |
| `pull_work` changes | LOW | Pre-pinning via existing `target_node_id` already works |
| `recompute_aggregate` logic | LOW | Simple count query, event-triggered |
| `GET /api/jobs/swarms` listing | LOW | Standard paginated list |
| `GET /api/jobs/swarms/{id}` detail | LOW | Aggregate + child job list |
| Jobs.tsx UI changes | MEDIUM | Campaign grouping row, progress bar, child job accordion |
| ScheduledJob → swarm dispatch | MEDIUM | Scheduler needs to understand swarm dispatch mode |
| Tests | MEDIUM | Race condition edge cases, partial completion scenarios |

**Overall complexity: MEDIUM.** No fundamentally new architecture is required. The existing codebase has all the primitives needed: `target_node_id`, `originating_guid` lineage pattern, tag-based eligibility, result receipt pipeline.

### Work-Queue Complexity (for comparison, deferred)

Work-queue distribution requires: (a) a task pool per swarm, (b) atomic task-claim semantics at poll time (`SELECT FOR UPDATE SKIP LOCKED` or a lease table), (c) progress tracking per task rather than per node, (d) Postgres-specific optimisations for high-concurrency claim workloads. Estimated 2-3x the complexity of fan-out swarming. Defer until there is a concrete operator request for it.

### Tiered Build Path

**Tier 1 — Fan-Out Swarming (recommended for next milestone after v13.0):**
- Estimated scope: 3 phases, ~9–12 plans
  - Phase A (backend): `swarm_records` table, `POST /api/jobs/swarm`, `GET /api/jobs/swarms`, `GET /api/jobs/swarms/{id}`, `recompute_aggregate`, result-handler hook, migration SQL
  - Phase B (frontend): Jobs.tsx swarm group row, campaign progress UI, child job accordion, swarm dispatch form
  - Phase C (scheduler + polish): `ScheduledJob` swarm dispatch mode, edge case handling (zero eligible nodes, all nodes at capacity), integration tests

**Tier 2 — Work-Queue Distribution (defer, future milestone):**
- Not designed in this document
- Prerequisites: evaluate whether Postgres `SELECT FOR UPDATE SKIP LOCKED` becomes mandatory (breaks SQLite dev path); consider dedicated lease table approach

### Draft API Shape

The following endpoint signatures are concrete enough for the planner to start from. They are not final — the implementing team should refine them.

```
POST /api/jobs/swarm
  Permission: jobs:write
  Request body:
    {
      "name":                  string | null,       // operator label for the campaign
      "task_type":             string,              // "script" (initially only supported type)
      "payload":               object,              // same payload structure as POST /api/jobs
      "target_tags":           string[],            // required — tags used to select ALL matching nodes
      "capability_requirements": object | null,
      "signature_id":          string | null,
      "signature_payload":     string | null,
      "runtime":               string | null,
      "timeout_minutes":       int | null,
      "dispatch_timeout_minutes": int | null
    }
  Response 201:
    {
      "swarm_id":     string,     // UUID of the SwarmRecord
      "total_nodes":  int,        // number of child jobs created
      "child_guids":  string[],   // list of created child job GUIDs
      "status":       "PENDING"
    }
  Error 422: no ONLINE nodes match the provided target_tags
  Error 422: target_tags not provided (fan-out requires explicit targeting)

GET /api/jobs/swarms
  Permission: jobs:read
  Query params: status, created_by, cursor, limit
  Response: { items: SwarmSummary[], total: int, next_cursor: string | null }
  SwarmSummary: { swarm_id, name, status, total_nodes, completed_nodes, created_at, created_by }

GET /api/jobs/swarms/{swarm_id}
  Permission: jobs:read
  Response: SwarmDetail
  SwarmDetail: {
    swarm_id, name, status, target_tags,
    total_nodes, completed_nodes, created_at, completed_at, created_by,
    children: JobResponse[]    // full child job list
  }
```

The existing `GET /api/jobs` endpoint should also accept an optional `swarm_id` filter so the Jobs view can show all children of a given swarm.

---

## Open Questions

1. **Scheduled swarms**
   - What we know: `ScheduledJob` fires one job per cron tick. A swarm would need to fire N jobs.
   - What's unclear: Should `ScheduledJob` gain a `dispatch_mode` field (`single` vs `swarm`), or should swarm scheduling be a separate `ScheduledSwarm` concept?
   - Recommendation: Add `dispatch_mode` to `ScheduledJob` in Phase A. Keep it simple — a `swarm` mode ScheduledJob triggers `POST /api/jobs/swarm` logic rather than `JobService.create_job`.

2. **Zero-node edge case**
   - What we know: If no ONLINE node matches target_tags at swarm creation time, returning 422 is the right default.
   - What's unclear: Should there be a `wait_for_nodes: true` mode that creates the SwarmRecord but defers child creation until nodes come online?
   - Recommendation: Defer this mode. Return 422 on zero matches for the initial implementation. An operator-facing warning in the UI is sufficient.

3. **Heterogeneous payloads per node**
   - What we know: Today's proposed API sends the same payload to all nodes in the swarm.
   - What's unclear: Is there a legitimate need to send different scripts/parameters to different nodes in a campaign?
   - Recommendation: Out of scope for fan-out swarming. If needed, that's a different feature (parameterised campaigns). Do not design for it in Tier 1.

4. **Swarm and the existing Jobs.tsx view**
   - What we know: Child swarm jobs are normal `Job` rows. They will appear in the existing Jobs list.
   - What's unclear: Should child jobs be hidden from the default Jobs list (de-cluttering) or shown with a swarm indicator?
   - Recommendation: Show them with a `[SWARM]` badge and swarm parent link. Hide them from default view only if operator feedback after launch requests it. Do not hide by default — observability is more important than tidiness.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` (if exists) or `cd puppeteer && pytest` |
| Quick run command | `cd puppeteer && pytest tests/ -x -q` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behaviour | Test Type | Automated Command | File Exists? |
|--------|-----------|-----------|-------------------|-------------|
| SWRM-01 | Use case analysis documented | manual | N/A — design document review | ❌ Wave 0 (document review only) |
| SWRM-02 | Pull-model impact documented | manual | N/A — design document review | ❌ Wave 0 (document review only) |
| SWRM-03 | Recommendation documented | manual | N/A — design document review | ❌ Wave 0 (document review only) |

**Note:** Phase 57 is a research/design phase. All three requirements are satisfied by the content of this document, not by executable tests. The validation approach for this phase is human review of the design document against the success criteria defined in CONTEXT.md. When swarming implementation begins (future milestone), the test map for those phases will include: `test_swarm_creation`, `test_pre_pin_race_condition`, `test_aggregate_status_barrier`, `test_zero_node_422`.

### Wave 0 Gaps

None — this is a documentation phase with no implementation. No test files need to be created as part of this phase.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `puppeteer/agent_service/db.py` — schema inspection of `Job`, `ExecutionRecord`, `SwarmRecord` patterns
- Direct codebase analysis: `puppeteer/agent_service/services/job_service.py` — `pull_work`, `create_job`, `_node_is_eligible` logic
- Kubernetes official docs: `https://kubernetes.io/docs/concepts/workloads/controllers/job/` — parallel jobs, completions/parallelism model
- Celery official docs: `https://docs.celeryq.dev/en/stable/userguide/canvas.html` — group, chord, canvas primitives

### Secondary (MEDIUM confidence)
- WebSearch → Celery patterns: group/chord fan-out pattern documented across multiple authoritative sources (appliku.com, reintech.io, docs.celeryq.dev)
- WebSearch → Kubernetes Jobs: parallelism/completions model verified against kubernetes.io official docs
- Ray documentation: `https://docs.ray.io/en/latest/ray-core/tasks.html` — remote task dispatch model

### Tertiary (LOW confidence)
- None — all claims in this document are grounded in either direct code inspection or verified official documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — based on direct code inspection of existing codebase
- Architecture patterns: HIGH — race condition and backpressure analysis derived from `pull_work` source code
- External system comparison: MEDIUM — based on official docs for Celery, Kubernetes, Ray; conceptual mapping to MoP is researcher's analysis
- Pitfalls / edge cases: MEDIUM — derived from code analysis + well-known distributed systems patterns

**Research date:** 2026-03-24
**Valid until:** 2026-09-24 (architecture is stable; external system docs change slowly)
