# Phase 57: Research — Parallel Job Swarming - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce a design document (`57-RESEARCH.md`) that gives the team everything needed to make an informed build/defer decision on parallel job swarming. No implementation. Output is a research artifact consumed by the planner and future milestone planning.

</domain>

<decisions>
## Implementation Decisions

### Swarming definition
- Two distinct patterns must be researched: **fan-out** (same job dispatched to all matching nodes simultaneously) and **work-queue** (N tasks distributed across M workers via shared queue)
- Core use case is fan-out — "run the same job on multiple nodes simultaneously"
- Campaign concept: the doc must define the distinction between today's tag targeting (dispatching to one node at a time with a matching tag) and a proper "campaign" that dispatches to all matching nodes at once
- Results model: N separate job records grouped under a parent swarm/campaign ID (not a single job with sub-results)

### Document format and location
- Lives at `.planning/phases/57-research-parallel-job-swarming/57-RESEARCH.md`
- Required sections:
  1. Use case analysis — when fan-out / campaigns are sufficient vs when genuine swarming is needed
  2. Pull-model impact — race conditions, backpressure, barrier synchronisation
  3. Data model sketch — how swarm job / campaign is represented relative to existing Job and ExecutionRecord tables
  4. Brief comparison with external systems (Celery, Ray, Kubernetes Jobs) — grounding the recommendation in prior art
  5. Complexity/value recommendation — tiered build path with rough effort estimate and draft API shape
- Doc must be readable by someone with no prior swarming context

### Recommendation framing
- **Tiered**: recommend fan-out swarming as the next milestone feature; defer work-queue / sharding to a future phase
- Include a rough phase/plan count estimate for the fan-out implementation to aid scheduling decisions
- Include a draft API endpoint signature for fan-out dispatch (e.g., `POST /api/jobs/swarm`) — concrete enough for the planner to start from

### Pull-model analysis depth
- Cover **both** race conditions (how do N nodes all claim the same swarm job without double-assignment?) and **backpressure** (what happens when nodes are at concurrency limit when a swarm is dispatched?)
- **Barrier synchronisation is required**: the doc must specify how a swarm transitions through PENDING → RUNNING (7/10) → COMPLETE/PARTIAL aggregate status
- Work-queue pattern: problem-definition only — identify it as a distinct pattern, explain why it's harder in a pull model, and explicitly defer detailed design

### Claude's Discretion
- Exact section headings and prose structure within each doc section
- Which external systems to include in the brief comparison
- Whether to include sequence diagrams or pseudo-code in the pull-model analysis

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Job` model in `db.py`: has `originating_guid` (nullable FK for resubmit lineage) — analogous concept to swarm parent ID; researcher should note this as a pattern to extend
- `ExecutionRecord` table: per-execution tracking with node, status, stdout/stderr — already supports "N results from one job run"
- `target_tags` on Job: tag-based node targeting already exists; the doc should analyse whether this is a degenerate form of fan-out or a fundamentally different concept

### Established Patterns
- `/work/pull` in `job_service.py`: assigns exactly **one** job to **one** node per poll cycle — this is the key architectural constraint the swarming design must solve
- Node concurrency limit (default 5 per node): backpressure mechanism already exists at the node level; the swarm design needs to interact with it
- Cursor pagination on Jobs: large result sets already handled; swarm job groups will amplify this need

### Integration Points
- `job_service.py` → `assign_job()` or equivalent: this is where swarm job creation logic would hook in
- Jobs view (Jobs.tsx): where grouped swarm results would need to appear — researcher should note the UI impact without designing it

</code_context>

<specifics>
## Specific Ideas

- "Run the same job on multiple nodes simultaneously" is the primary motivating scenario
- Fan-out result grouping under a parent ID mirrors the existing `originating_guid` pattern for resubmit lineage — a swarm parent is a natural extension
- The doc should clearly distinguish "tag targeting dispatches to one node" (today) from "swarm dispatches to all matching nodes at once" (desired)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 57-research-parallel-job-swarming*
*Context gathered: 2026-03-24*
