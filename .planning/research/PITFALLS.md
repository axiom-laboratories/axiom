# Domain Pitfalls: DAG/Workflow Orchestration Integration

**Domain:** Task orchestration platform adding DAG/workflow capabilities to existing job scheduling system  
**Researched:** 2026-04-15  
**Focus:** Integration risks with existing infrastructure, concurrency hazards, state machine edge cases

---

## Executive Summary

Adding DAG/workflow orchestration to Axiom introduces **three critical risk categories**: (1) **Concurrency hazards** in the BFS unblock/cascade engine when multiple steps complete simultaneously, creating race conditions and stuck BLOCKED jobs; (2) **State machine brittleness** where PARTIAL vs FAILED distinctions break under transitive dependencies, leaving orphaned jobs in uncertain states; (3) **Security amplification** where webhook/output injection vulnerabilities are exponentially more damaging in workflows than single jobs.

The existing `depends_on` foundation (Job.depends_on JSON list + BFS cascade in job_service.py) handles linear chains correctly but lacks atomic guards for concurrent completion, FAILED propagation, and structured output validation. Integration with APScheduler for workflow cron triggers introduces a "ghost execution" risk where legacy scheduled jobs fire after a workflow is marked saved-as-new. Depth limits (currently 10 levels) are adequate but bypass mechanisms (edge-case handling in _unblock_dependents) create DoS exposure.

**Mitigation strategy:** Implement explicit phase gates: Phase 1 (serialized unblock), Phase 2 (result validation + injection hardening), Phase 3 (backward-compatible migration), Phase 4 (APScheduler isolation + pause semantics).

---

## Critical Pitfalls

### Pitfall 1: Race Condition in Concurrent Step Completion

**What goes wrong:**
When multiple independent jobs complete simultaneously (or near-simultaneously), the BFS unblock engine (`_unblock_dependents`) processes them serially but **without atomic guards**. A job waiting on `[A, B, C]` where all three complete within milliseconds of each other experiences:

1. **Time 0ms:** Job A completes → `_unblock_dependents(A)` starts DB query for jobs depending on A
2. **Time 1ms:** Job B completes → `_unblock_dependents(B)` starts a **second** DB query
3. **Time 2ms:** Both queries return the same waiting job, unblock logic executes **twice**
4. **Time 5ms:** Job C completes → third query, third unblock attempt on same job (now PENDING)

Result: Status churn in audit logs, potential double-execution if the job hasn't yet moved past PENDING, or orphaned job if second unblock reverts a state change.

**Why it happens:**
- `_unblock_dependents` uses a stateless BFS search (`Job.depends_on.like(...)`) that finds all blocked dependents
- No transaction boundary guards status transition atomicity
- Multiple concurrent calls to `_unblock_dependents` from different job completion handlers race
- In single-job deployments, this is invisible; in parallel workflows with 10+ simultaneous completions, it's common

**Consequences:**
- Jobs silently re-queued or double-executed if retry logic is downstream
- Audit log shows spurious state transitions (PENDING → PENDING)
- SLA violations on workflow completion (job stuck PENDING when dependencies are satisfied)
- Data corruption if job idempotency is not perfect

**Prevention:**
1. **Atomize unblock with SELECT...FOR UPDATE** — Use `SELECT ... FOR UPDATE` in a transaction to lock all dependent jobs before checking + updating status. Lock is released when transaction commits.
2. **Implement idempotent guard** — Track `last_unblock_attempt_at` timestamp on Job record; if called again within 5s with same upstream GUID, skip re-check.
3. **Move unblock to single background task** — Replace distributed callbacks with a single sweep job that runs every 100ms and processes all PENDING→eligible transitions in one pass.
4. **Write explicit race condition test** — Create workflow with 3 independent parallel jobs, complete all 3 within 10ms window, assert waiting job only transitions once.

**Detection:**
- Alert on repeated status transitions (same GUID, same status, multiple transitions in 1 minute)
- Log unblock latency; if >500ms, signal DB contention
- Audit log analysis: group by job GUID, alert if status change count > 1 per completion event

---

### Pitfall 2: PARTIAL Failures Break Cascade Logic

**What goes wrong:**
The cascade system (`_cancel_dependents`) assumes binary outcomes: a job is either COMPLETED or FAILED. Workflows introduce **partial success**:

- Job A completes with exit code 0 (COMPLETED), but structured output is invalid (missing required field)
- Logic checks `if upstream.status == "COMPLETED"`, finds true, unblocks dependent B
- Job B runs, expects a field that doesn't exist, fails with cryptic error
- No audit trail of what data B actually received; no clear signal that "partial failure" occurred

Additionally, **conditional gates** (IF steps) create a new failure mode:
- Job A completes SUCCESSFULLY but IF gate reads `/tmp/axiom/result.json` incorrectly
- Gate should route to step B but instead routes to step C (wrong path)
- Step C executes in wrong context, silently produces wrong output
- Workflow continues, appears COMPLETED, but data is corrupted

**Why it happens:**
- Existing status enum is {PENDING, BLOCKED, ASSIGNED, RUNNING, COMPLETED, FAILED, CANCELLED}
- No PARTIAL or VALIDATION_FAILED state
- `depends_on` logic is purely status-based, ignores result payload validation
- Result.json reading happens in IF gate evaluation, not in job completion handler
- No atomic semantics between job completion and output validation

**Consequences:**
- Silent data corruption in workflows (step runs with wrong input)
- Difficult debugging (error in step C with wrong input ≠ obvious cause in step A)
- Transitive failure propagation broken: cancelling step A doesn't prevent B if B was already unblocked
- Compliance/audit trail gaps: workflow marked COMPLETED but data quality unknown

**Prevention:**
1. **Add VALIDATION_FAILED state** — Introduce status = VALIDATION_FAILED when output validation rules (if defined) fail. Mark job as terminal but distinguishable from FAILED.
2. **Atomic validation before unblock** — Before calling `_unblock_dependents`, run output validation in same transaction. If validation fails, set VALIDATION_FAILED and skip unblock.
3. **IF gate atomicity** — Parse and validate result.json immediately after job completion, in same DB transaction. If parsing fails, mark job VALIDATION_FAILED and prevent downstream triggers.
4. **Transitive failure isolation** — Add `failed_upstream_guid` field to Job record. When cancelling, check this field; if set, this job was blocked by that upstream. Cancel it transitively only if upstream is actually FAILED or CANCELLED (not VALIDATION_FAILED).
5. **Output validation schema in workflow definition** — Store expected output schema alongside workflow. Validate at step completion time, not at IF gate runtime.

**Detection:**
- Alert on jobs in VALIDATION_FAILED state persisting >5 minutes
- Log all IF gate parsing errors with result.json sample
- Audit trail: compare expected output schema vs actual result.json fields

---

### Pitfall 3: Depth Limit Bypass via Conditional Unblocking

**What goes wrong:**
The current depth limit (10 levels) is enforced at **job creation time** only. An attacker (or misconfigured workflow) can **bypass this** by creating a workflow that appears to comply, then using conditional unblocking to create hidden depth, leading to stack exhaustion in recursive BFS traversal and exponential resource consumption when a single job failure cascades to 500+ downstream jobs.

**Why it happens:**
- Depth check is on direct `depends_on` list only
- Conditional dependencies are not depth-checked
- `_unblock_dependents` BFS can unblock jobs that themselves have dependents, creating exponential exploration
- No cycle detection in conditional logic

**Consequences:**
- Stack exhaustion in recursive BFS traversal (DoS)
- Exponential resource consumption on cascade
- Server CPU spike when exploring millions of potential paths
- Denial of service against other workflows

**Prevention:**
1. **Check transitive depth at creation time** — Recursively check depth of **all** listed upstreams, including conditional dependencies. Reject if any path exceeds depth 12.
2. **Implement IF gate depth limit** — Conditional dependencies are still dependencies; count them in depth calculation.
3. **Batch unblock with exponential backoff** — If `_unblock_dependents` discovers >100 potential unblocks, queue them for batch processing with 50ms delays between batches.
4. **Circuit breaker on cascade size** — Track jobs cancelled/unblocked per failure event. If a single job failure unblocks >1000 dependents, fail the cascade and alert ops.
5. **Explicit cycle detection in IF gates** — Before committing a workflow, check for logical cycles.

**Detection:**
- Log cascade size, alert if >500
- Monitor `_unblock_dependents` execution time; if >5s, signal DoS attempt
- Audit: flag workflows with conditional dependencies on jobs at depth >8

---

### Pitfall 4: Webhook Replay Attacks → Workflow State Corruption

**What goes wrong:**
Workflows accept external event triggers via webhooks. Without replay protection, an attacker (or network retry) can send the same webhook multiple times:

1. Send webhook with signed event payload
2. Server validates HMAC signature, emits signal "event-kafka-received"
3. All jobs waiting on this signal unblock simultaneously
4. **Network glitch or operator error**: Webhook retried 3 times
5. Signal emitted 4 times total; jobs unblock 4 times, re-execute, corrupt state

Compounded by Pitfall 1: concurrent `_unblock_dependents` calls process it twice, unblocking the same job twice.

**Why it happens:**
- Webhook handler validates HMAC but doesn't track `nonce` or `replay_id`
- `unblock_jobs_by_signal` is idempotent by design, **but** if a job re-executes instead of idempotently transitioning, state corrupts
- No timestamp on webhook; accepts events from any time in past
- APScheduler retry logic + network retries mean webhooks arrive multiple times

**Consequences:**
- Workflow executes steps multiple times (2x, 3x, or more)
- Duplicate data writes (payments charged twice, records inserted multiple times)
- State corruption if downstream steps assume "executed once" semantics
- Audit trail confusion (same job appears COMPLETED multiple times)

**Prevention:**
1. **Implement nonce tracking** — Store `webhook_nonce` in a dedicated table with TTL (24 hours). Reject any webhook with nonce already seen.
2. **Timestamp validation** — Include `timestamp` in HMAC payload. Reject if `current_time - timestamp > 300 seconds`.
3. **Idempotency key in signal definition** — Signals include `event_id` or `nonce`. Change the signal name if the event retries.
4. **Database-backed idempotency** — Before emitting a signal, check if this exact signal was emitted in last 60 seconds. If yes, return cached result.
5. **Explicit webhook signature format** — Require `X-Webhook-Signature: HMAC-SHA256=<hash>`, `X-Webhook-Timestamp: <unix_seconds>`, `X-Webhook-Nonce: <uuid>`. All three must be present and valid.

**Detection:**
- Alert on signal emitted twice with same name within 1 minute
- Log webhook handler latency; if retries happen, log it explicitly
- Audit trail: flag jobs that transitioned from PENDING multiple times

---

### Pitfall 5: Structured Output Injection via IF Gates

**What goes wrong:**
IF gates read `/tmp/axiom/result.json` to decide which step executes next. If the job's output is user-controlled or from an untrusted source, an attacker can inject malicious JSON to manipulate control flow:

1. Job A fetches data from a URL: `curl https://untrusted-api.com/data > result.json`
2. IF gate reads result.json: `if $.status == "success" then unblock B, else unblock C`
3. Attacker controls the API; returns JSON with injected fields
4. IF gate logic uses this to construct the next job name or targets
5. Workflow routes to wrong step or creates job with wrong node targeting

Compounded with Pitfall 2 (no validation): Job A completes, IF gate reads corrupted JSON, unblocks wrong step silently.

**Why it happens:**
- Jobs can execute arbitrary scripts; scripts can write arbitrary JSON to result.json
- IF gate evaluation trusts result.json content implicitly
- No schema validation on result.json
- JSON parsing might use unsafe deserialization

**Consequences:**
- Workflow takes wrong branch
- Sensitive data is accessed/leaked if wrong step executes
- If result.json is used to construct node IDs, job runs on wrong node
- Audit trail shows "wrong" step executed; difficult to trace to injection

**Prevention:**
1. **JSON Schema validation** — Before IF gate evaluation, validate result.json against a strict schema defined in the workflow. Reject if invalid.
2. **Sandbox IF gate expressions** — Use restricted expression language (Lua, Jinja2 with no function calls) instead of arbitrary eval. Disallow file access, network calls, imports.
3. **Typed field extraction** — If IF gate reads `$.status`, enforce that status is a string from a finite set {success, failure, retry}. No nested objects, no wildcards.
4. **Immutable result.json** — Once job completes, make result.json read-only. If a step tries to modify it, fail the workflow.
5. **Sign result.json** — Have the node sign result.json with its private key. Verify signature before using it in IF gate.

**Detection:**
- Log IF gate expression + inputs for each evaluation
- Alert on JSON parsing errors in result.json
- Audit: flag workflows where result.json size is >10 MB or contains non-scalar types

---

### Pitfall 6: APScheduler "Ghost Execution" in Workflow Scheduling

**What goes wrong:**
When a workflow is scheduled with a cron trigger via APScheduler, the "save as new" pattern creates a **ghost execution** risk:

1. User creates workflow W1 with cron trigger `0 9 * * *` (daily at 9 AM)
2. APScheduler registers this as job ID `w1-cron` that fires at 9 AM
3. User decides to modify W1, clicks "Save as New Workflow" → creates W1.2
4. The **original APScheduler job for W1 is never paused**; it still fires at 9 AM
5. At 9 AM, APScheduler triggers W1, spawns jobs, completes workflow
6. User expects W1.2 to run; instead W1 ran (invisibly, no UI indicator)
7. Workflow history is confusing; "which version ran?"

**Why it happens:**
- Workflow CRUD doesn't cascade to APScheduler job management
- APScheduler job IDs are based on workflow ID, not version
- "Save as new" creates a new workflow record but doesn't pause the old one
- No explicit pause/unpause workflow semantics in API

**Consequences:**
- Duplicate workflows executing (both W1 and W1.2 fire, different data)
- Missed expectation: user thinks W1.2 runs but W1 ran instead
- Audit trail confusion: workflow history shows W1 completed, but user "saved as new"
- Job contamination: W1's old data pipeline runs, corrupts state meant for W1.2

**Prevention:**
1. **Pause workflow explicitly on save-as-new** — When creating W1.2 from W1, auto-pause W1's APScheduler jobs. Require user confirmation if active jobs exist.
2. **Workflow version semantics** — Store `workflow_version` on both Workflow and Job records. APScheduler job ID includes version: `w1-v1-cron`, `w1-v2-cron`.
3. **Pause/resume API** — Add explicit `PATCH /workflows/{id}/pause` and `PATCH /workflows/{id}/resume` endpoints. Mark workflow with `paused_at` timestamp. Pull_work checks this before dispatching.
4. **APScheduler job cleanup on delete** — When deleting a workflow, explicitly remove its APScheduler jobs.
5. **Workflow state in DB** — Track workflow status = {ACTIVE, PAUSED, ARCHIVED}. Only active workflows dispatch.

**Detection:**
- Alert on multiple workflows with same definition executing simultaneously
- Log when APScheduler job fires: include workflow ID + version
- Audit: flag workflows where pause event is missing but "save as new" event exists

---

### Pitfall 7: Backward Compatibility with Non-Workflow Scheduled Jobs

**What goes wrong:**
Existing ScheduledJob records (cron-scheduled jobs, no workflows) will coexist with new Workflow records. A database migration or schema change breaks backward compatibility:

1. Phase 1 adds Workflow table
2. Phase 2 modifies ScheduledJob to add `workflow_id` foreign key (nullable)
3. Existing ScheduledJobs have `workflow_id = NULL`
4. Code path: `if job.workflow_id: execute_as_workflow() else: execute_as_legacy_job()`
5. During migration, developer forgets the `else` branch; legacy jobs silently don't execute
6. Or: new code assumes all ScheduledJobs are workflows, crashes on NULL workflow_id

**Why it happens:**
- Migration window where old + new coexist is a footgun
- Two execution paths need explicit guards
- Test coverage gaps: tests assume all jobs are workflows
- Rollback risk: if Phase 2 is rolled back, workflow jobs are lost

**Consequences:**
- Scheduled jobs vanish (silently don't run) after upgrade
- No alarm: job didn't run, but no error log
- Data pipeline interruption: jobs that should have run never execute
- Operator discovers issue days later when downstream systems fail

**Prevention:**
1. **Explicit dual-path tests** — Integration tests covering both legacy ScheduledJob execution AND new Workflow execution in same test run.
2. **Feature flag for workflow execution** — Add `ENABLE_WORKFLOW_ENGINE=false` env var. Phase 1: workflows ignored, only legacy. Phase 2: flips to true.
3. **Gradual migration strategy** — Add separate table `ScheduledWorkflow` with same schedule semantics. Operator manually migrates ScheduledJobs to workflows.
4. **Sanity check on startup** — At lifespan startup, count ScheduledJobs with workflow_id = NULL. If count > 100, log WARNING with explicit migration instructions.
5. **Audit logging on execution** — Log explicitly which code path was taken: legacy vs workflow.

**Detection:**
- Alert on zero scheduled jobs executed in 24 hours (if non-zero expected)
- Log job count mismatch: APScheduler N jobs, DB M ScheduledJob records
- Audit: count execution paths, ensure both legacy + workflow paths exercised

---

## Moderate Pitfalls

### Pitfall 8: IF Gate Expression Complexity → Undefined Behavior

Complex boolean logic in IF gates is hard to test: `if (A.status == "success" and B.output.count > 10) or (C retried < 3) then step D else step E`. Operator writes expression with unclear precedence; expected parse != actual parse.

**Prevention:**
1. Limit IF gate to single field comparison: `if A.output.status == "success" then B else C`. No AND/OR.
2. Validate expression syntax at workflow creation time.
3. Surface IF gate evaluation in logs: `IF expression: <expr>, inputs: <values>, result: <branch>`.

---

### Pitfall 9: Missing Result.json in Node Environment

Node runtime writes `/tmp/axiom/result.json`; if the job never creates this file, the IF gate parser crashes.

**Prevention:**
1. Default result.json: If job completes without writing result.json, node automatically writes `{"status": "success", "output": null}`.
2. IF gate guard on missing file: Check if result.json exists; if not, default to "no data" branch.

---

### Pitfall 10: Cron Trigger Misalignment with Workflow Duration

Workflow scheduled daily, but previous run takes 25 hours. APScheduler fires next run while previous still executes.

**Prevention:**
1. `max_instances=1` on APScheduler job.
2. Dispatch timeout: Cancel workflow if it exceeds expected duration.

---

## Minor Pitfalls

### Pitfall 11: Job Template Versioning + Workflows

Workflows reference job templates. If template is modified, old workflows using it might break.

**Prevention:** Store template version on workflow step definition. When step executes, use that specific template version.

### Pitfall 12: Webhook Secret Rotation

Webhook HMAC secret is rotated; old webhooks are rejected; integration partners' webhooks fail.

**Prevention:** Support multiple active secrets during rotation window. Include secret version in X-Webhook-Signature header.

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|--------------|-----------|
| **Phase 1: Core DAG Model** | Concurrency in completion | Race condition in _unblock_dependents (Pitfall 1) | SELECT...FOR UPDATE atomicity; concurrent completion test |
| **Phase 1** | Job status states | VALIDATION_FAILED missing (Pitfall 2) | Add VALIDATION_FAILED state; single unblock task |
| **Phase 2: Result Validation** | Output validation | Validation too late (Pitfall 2, 5) | Validate result.json at job completion, before unblock |
| **Phase 2** | IF gate evaluation | Structured output injection (Pitfall 5) | JSON schema enforcement; sandboxed expression language |
| **Phase 2** | Depth limit | Bypass via conditional deps (Pitfall 3) | Transitive depth check for all depends_on |
| **Phase 3: Backward Compatibility** | ScheduledJob coexistence | Ghost execution + migration gaps (Pitfalls 6, 7) | Feature-flag engine; dual execution paths with tests |
| **Phase 3** | APScheduler integration | Pause/resume missing (Pitfall 6) | Explicit pause/resume API; cascade to APScheduler |
| **Phase 4: Webhooks** | External events | Replay attacks (Pitfall 4) | Nonce tracking + timestamp validation; idempotency |
| **Phase 4** | Secrets | Secret rotation (Pitfall 12) | Multiple active secrets during rotation |
| **All phases** | Testing | Concurrency gaps | Concurrent completion, parallel steps, replay tests |

---

## Integration-Specific Risks

### Risk: Ed25519 Signature Validation + Workflows

Workflows contain multiple jobs. If workflow serialization includes job payloads, modifying a single job breaks the workflow signature.

**Mitigation:** Workflows don't have Ed25519 signatures; only individual job steps do. Workflow definition is immutable; steps reference job templates by ID + version. Each job executed by a step must pass full signature verification.

### Risk: Node Resource Limits + Parallel Steps

Workflow with 10 parallel steps, each needing 2GB RAM. Node has 4GB total. First 5 steps assigned; step 6 stuck PENDING indefinitely.

**Mitigation:** Workflow DAG includes resource reservation: sum memory of all **concurrent** steps; reject if exceeds node capacity. Calculate critical path and peak parallelism at dispatch time.

### Risk: Audit Trail Ambiguity in Workflows

Audit log shows job A executed, but doesn't indicate it was step 3 of workflow W1 v2. Operator can't trace back.

**Mitigation:** Add `workflow_id`, `workflow_version`, `step_name` fields to Job. Audit log includes full context.

---

## Summary: Prevention Checklist for Each Phase

### Phase 1: Core DAG Model
- [ ] SELECT...FOR UPDATE atomicity on job status transitions
- [ ] Concurrent completion test: 3 jobs complete within 10ms, no double-unblock
- [ ] Add VALIDATION_FAILED status
- [ ] Transitive depth check for all depends_on (limit 12)
- [ ] BFS unblock batch size limit (circuit breaker at 1000)

### Phase 2: Result Validation + IF Gates
- [ ] Output validation schema in workflow definition
- [ ] Validate result.json in same transaction as job completion
- [ ] Sandboxed IF gate expression language
- [ ] JSON schema enforcement before IF gate evaluation
- [ ] Tests include valid + invalid result.json scenarios

### Phase 3: Backward Compatibility
- [ ] Feature flag for workflow engine (ENABLE_WORKFLOW_ENGINE)
- [ ] Dual-path tests: legacy ScheduledJob + Workflow in same test
- [ ] Sanity check: count legacy jobs on startup, warn if high
- [ ] APScheduler pause/resume API + workflow state column
- [ ] Manual migration path: ScheduledJob → Workflow documented

### Phase 4: Webhooks + External Events
- [ ] Nonce tracking table with 24h TTL
- [ ] Timestamp validation (±300s window)
- [ ] Webhook signature format validation (3 required headers)
- [ ] Database-backed idempotency check
- [ ] Replay attack test: same webhook 3 times, verify single execution

### All Phases
- [ ] Concurrent execution test matrix (2, 5, 10 simultaneous jobs)
- [ ] Partial failure scenarios (VALIDATION_FAILED, wrong IF branch)
- [ ] Audit trail verification: all critical paths logged with context
- [ ] Performance regression: 1000-job workflow DAG unblock latency <5s

---

## Sources

### Orchestration Architecture & Concurrency
- [Troubleshooting Apache Airflow](https://www.mindfulchase.com/explore/troubleshooting-tips/troubleshooting-apache-airflow-optimizing-dag-scheduling,-parallelism,-and-performance.html)
- [Building a DAG-Based Workflow Execution Engine](https://medium.com/@amit.anjani89/building-a-dag-based-workflow-execution-engine-in-java-with-spring-boot-ba4a5376713d)
- [Data Pipeline Orchestration Tools 2026](https://dagster.io/learn/data-pipeline-orchestration-tools)

### Webhook Security & Replay Prevention
- [Webhook Security Fundamentals 2026](https://www.hooklistener.com/learn/webhook-security-fundamentals)
- [Replay Prevention Best Practices](https://webhooks.fyi/security/replay-prevention)
- [Webhook Security Best Practices](https://hooque.io/guides/webhook-security/)
- [Preventing Replay Attacks](https://dohost.us/index.php/2026/02/15/preventing-replay-attacks-implementing-timestamps-and-nonces-in-webhook-handlers/)

### Structured Output Security
- [MCP Attack Vectors](https://unit42.paloaltonetworks.com/model-context-protocol-attack-vectors/)
- [Output Constraints as Attack Surface](https://arxiv.org/html/2503.24191v1)
- [PromptGuard: Injection-Resilient Models](https://www.nature.com/articles/s41598-025-31086-y)

### Backward Compatibility & Migration
- [API Backward Compatibility Best Practices](https://zuplo.com/learning-center/api-versioning-backward-compatibility-best-practices)
- [Database Migration Strategies for Zero-Downtime](https://www.deployhq.com/blog/database-migration-strategies-for-zero-downtime-deployments-a-step-by-step-guide)
- [Database Design for Backward Compatibility](https://www.pingcap.com/article/database-design-patterns-for-ensuring-backward-compatibility/)

### Denial of Service & Recursion Limits
- [CVE-2026-12345: GraphQL Depth Bypass](https://dailycve.com/mercurius-query-depth-bypass-cve-2026-12345-low/)
- [CVE-2026-24006: Deeply Nested Objects DoS](https://advisories.gitlab.com/pkg/npm/seroval/CVE-2026-24006/)
- [CVE-2026-27601: Unlimited Recursion](https://cvefeed.io/vuln/detail/CVE-2026-27601)

### Distributed Systems & State Management
- [Temporal Workflow Orchestration & Scalability](https://temporal.io/blog/how-modern-workflow-orchestration-solves-scalability-challenges)
- [AWS Step Functions: Orchestration & State Machine Design](https://middleware.io/blog/aws-step-functions/)
- [Workflow Orchestration Patterns](https://www.thedataops.org/workflow-orchestration/)

### Axiom Codebase References
- `puppeteer/agent_service/services/job_service.py` — BFS cascade, depth limits
- `puppeteer/agent_service/db.py` — Job model, depends_on schema
- `puppeteer/agent_service/services/scheduler_service.py` — APScheduler integration
- `mop_validation/reports/competitor_product_notes.md` — Workflow comparative analysis
