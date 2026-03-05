# Roadmap: Master of Puppets — Production Reliability Milestone

## Overview

This milestone adds the production-readiness layer to a functioning, security-hardened orchestration platform. The five phases follow a strict data dependency chain: output capture must exist before retry can make non-blind decisions, retry must produce multiple execution attempts before history becomes meaningful, history must be reliable before job dependencies can safely evaluate upstream completion, and environment tags can ship cleanly once the core execution pipeline is solid. Every phase delivers a coherent, independently verifiable capability on top of the existing system.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Output Capture** - Node captures stdout/stderr/exit code per execution; dashboard surfaces output logs (completed 2026-03-04)
- [ ] **Phase 2: Retry Policy** - Configurable retries with exponential backoff, failure classification, and zombie reaper
- [ ] **Phase 3: Execution History** - Queryable timeline of past runs per job and node, with output retention pruning
- [ ] **Phase 4: Environment Tags** - Operator-assignable env tags on nodes with strict enforcement for job targeting
- [ ] **Phase 5: Job Dependencies** - Job chaining and fan-in with cycle detection and transactional readiness checks

## Phase Details

### Phase 1: Output Capture
**Goal**: Every job execution produces a durable, queryable output record — stdout, stderr, exit code, and duration stored server-side, viewable from the dashboard
**Depends on**: Nothing (first phase — extends existing job execution pipeline)
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04
**Success Criteria** (what must be TRUE):
  1. After a job runs on a node, the dashboard job detail page shows the captured stdout and stderr for that execution
  2. Each execution attempt has its own record — running the same job twice produces two separate, individually viewable output records
  3. The exit code is visible alongside the output log (0 = success, non-zero = failure)
  4. Output is truncated at 1 MB with a visible indicator; jobs producing more than 1 MB do not crash the system
**Plans**: 5 plans

Plans:
- [ ] 01-01-PLAN.md — DB contracts: ExecutionRecord ORM model, extended ResultReport/ExecutionRecordResponse models, migration_v14.sql
- [ ] 01-02-PLAN.md — Execution pipeline: node output capture (build_output_log), server report_result extension with 1MB truncation and SECURITY_REJECTED classification
- [ ] 01-03-PLAN.md — User-facing: GET /jobs/{guid}/executions API route, ExecutionLogModal full-screen log viewer, SECURITY_REJECTED status badge
- [ ] 01-04-PLAN.md — Gap closure: Copy button overlap fix in ExecutionLogModal (cosmetic UAT issue)
- [ ] 01-05-PLAN.md — Gap closure: Server-side status filter for Jobs view across all pages (major UAT issue)

### Phase 2: Retry Policy
**Goal**: Failed jobs retry automatically with backoff, dead-letter after exhausting retries, and crashed-node zombie jobs are reaped and rescheduled — no failed job is silently lost
**Depends on**: Phase 1 (retry decisions reference execution output and exit codes)
**Requirements**: RETR-01, RETR-02, RETR-03, RETR-04
**Success Criteria** (what must be TRUE):
  1. A job definition can be configured with max_retries > 0; on failure the job re-queues automatically and the dashboard shows retry count incrementing
  2. Retries use exponential backoff with jitter — a second attempt does not fire immediately after the first
  3. After exhausting all retries, the job shows a terminal DEAD_LETTER status and does not re-queue
  4. Signature verification failures and explicit non-retriable exit codes do not trigger retries — only transient failures do
  5. A job that was assigned to a node which then crashed is reclaimed within the configured zombie timeout and re-enters the retry cycle
**Plans**: TBD

### Phase 3: Execution History
**Goal**: Operators can query a timeline of past executions across all jobs and nodes, drill into per-attempt output, and the system automatically prunes old records to prevent runaway disk growth
**Depends on**: Phase 2 (multiple retry attempts make per-attempt history meaningful)
**Requirements**: HIST-01, HIST-02, HIST-03, HIST-04
**Success Criteria** (what must be TRUE):
  1. The dashboard has an Execution History view showing past runs across all jobs, with columns for node, start time, duration, exit code, and status
  2. History can be filtered by node, status (COMPLETED / FAILED / DEAD_LETTER), and date range — filtered results update without a full page reload
  3. Clicking an execution row shows the per-attempt drill-down: attempt 1 (FAILED, exit 1), attempt 2 (COMPLETED) with output for each
  4. Old execution records are automatically pruned on a configurable schedule — the default retention limit is configurable via the Config table and does not require a code change
**Plans**: TBD

### Phase 4: Environment Tags
**Goal**: Operators can tag nodes with environment labels (env:dev, env:test, env:prod) and target jobs to specific environments — untagged nodes are rejected for env-targeted jobs, not silently included
**Depends on**: Phase 1 (tags interact with the existing job assignment path; output capture must be stable first)
**Requirements**: TAG-01, TAG-02, TAG-03, TAG-04
**Success Criteria** (what must be TRUE):
  1. An operator can assign environment tags to a node from the Nodes dashboard page without editing config files or restarting anything
  2. A job definition can require a specific environment tag — it will only be dispatched to nodes carrying that tag
  3. A node with env:prod in its tags rejects a job that does not require env:prod — the rejection is logged and the job is re-queued for a matching node
  4. Node cards in the dashboard show environment tag badges (color-coded: green = prod, amber = test, blue = dev) and untagged nodes are visually distinct
**Plans**: TBD

### Phase 5: Job Dependencies
**Goal**: Operators can chain jobs so that job B only runs after job A succeeds, fan-in waits for multiple upstreams, and the system detects and rejects cycles at creation time — no deadlock, no manual polling
**Depends on**: Phase 3 (dependency evaluation reads execution history to determine upstream completion; retry semantics from Phase 2 define what "completed" means)
**Requirements**: DEP-01, DEP-02, DEP-03, DEP-04
**Success Criteria** (what must be TRUE):
  1. A job can be created with a "depends on" field referencing one or more other jobs; it remains in BLOCKED state until all upstream jobs show COMPLETED status
  2. Defining a dependency that creates a cycle (A → B → A) returns an HTTP 400 error at creation time — the cycle is never saved
  3. A fan-in job with two upstream dependencies stays BLOCKED until both upstreams complete — it does not start when only one completes
  4. The dashboard job detail pane shows whether a job is BLOCKED (with which upstream is pending) or READY to run
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Output Capture | 3/5 | Gap closure | 2026-03-04 |
| 2. Retry Policy | 0/TBD | Not started | - |
| 3. Execution History | 0/TBD | Not started | - |
| 4. Environment Tags | 0/TBD | Not started | - |
| 5. Job Dependencies | 0/TBD | Not started | - |
