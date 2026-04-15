# Domain Pitfalls: DAG Workflow Orchestration

**Domain:** Multi-job orchestration systems
**Researched:** 2026-04-15

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Depth Limit DoS

**What goes wrong:**
You keep the existing `_get_dependency_depth()` limit (max 10) for all jobs. A workflow with 15 sequential stages is rejected with "DAG too deep" error.

**Why it happens:**
The limit was designed to prevent user-submitted job chains from spiraling into deep recursion. But workflows are admin-controlled (not user input), so they need higher limits.

**Consequences:**
- Operators can't deploy multi-stage workflows (e.g., 20-step CI/CD pipeline)
- Workaround: split into multiple workflows (operationally messy)
- Re-architecting BFS to support variable depth requires careful testing

**Prevention:**
- Make `_get_dependency_depth()` accept optional `max_depth` parameter
- Pass `max_depth=30` when WorkflowRun dispatches jobs
- Validate in Phase 2 unit tests with synthetic 20-step DAG

**Detection:**
- Test harness fails on workflow with >10 steps
- Operator complaints about workflow depth limits

---

### Pitfall 2: Gate Condition Code Injection

**What goes wrong:**
You use `eval()` to evaluate gate conditions. Operator pastes `__import__("os").system("rm -rf /")` into condition editor. Condition executes on server, deletes data.

**Why it happens:**
eval() is tempting for "just let users write expressions"; hard to restrict without a parser.

**Consequences:**
- Data loss, downtime, security incident
- Requires DB restore
- Operator blames system; reputational damage

**Prevention:**
- Use Jinja2 template engine with sandboxed environment
- Restrict context to {result, exit_code, stdout, stderr}
- No access to Python builtins or imports
- Test: try to break out of sandbox with malicious condition; verify failure

**Detection:**
- Security audit: grep code for `eval(`, `exec(`, `compile(`
- Unit test: `_evaluate_gate_condition("{{ result.__class__ }}")` must return false/error, not class name

---

### Pitfall 3: Workflow Run Partial Failure (Orphaned Steps)

**What goes wrong:**
WorkflowRun dispatch creates Job A, Job B, Job C. Job A completes successfully; Job B is assigned. Then Agent crashes during Job B execution. WorkflowRun is left in "RUNNING" state forever; no cleanup.

**Why it happens:**
BFS dispatch doesn't have a timeout or watchdog for stalled workflows. Job retry logic (existing) will retry Job B, but WorkflowRun status is never updated.

**Consequences:**
- Orphaned WorkflowRun records accumulate in DB
- Operators confused about workflow status
- Manual intervention needed to mark run as FAILED

**Prevention:**
- Add workflow timeout (e.g., max 24h per run)
- Implement RunWatchdog: query WorkflowRuns in RUNNING state, check if any step is ASSIGNED but job is DEAD_LETTER for >30 min
- Mark workflow FAILED if watchdog detects stall
- Test: simulate node crash mid-workflow; verify watchdog marks it FAILED

**Detection:**
- Dashboard: filter WorkflowRuns by (status=RUNNING and age>24h)
- Watchdog logs: "Marked run X FAILED: step Y assigned to dead job Z"

---

### Pitfall 4: Gate Evaluation Race on Concurrent Upstreams

**What goes wrong:**
DAG has two upstream jobs (A, B) that fan-out to gate node G. Both A and B complete concurrently. First completion notification evaluates G with only A's result loaded; second completion re-evaluates G with both A and B. Gate condition sees inconsistent state.

**Why it happens:**
BFS unblock handler (`_unblock_workflow_steps_after_job`) doesn't acquire lock on WorkflowRun; concurrent completion notifications race.

**Consequences:**
- Gate evaluates incorrectly (e.g., passes when should fail)
- Downstream jobs dispatch when they shouldn't
- Silent failure (condition passed but upstream was incomplete)

**Prevention:**
- Acquire lock on WorkflowRun at start of `_unblock_workflow_steps_after_job()`
- Verify **all** upstream steps are COMPLETED/SKIPPED before evaluating gate
- Test: simulate concurrent job completion with synthetic race condition; verify gate only fires once all upstreams complete

**Detection:**
- Unit test: dispatch DAG with parallel upstreams + gate; verify gate fires exactly once
- Log: trace gate evaluation and confirm all upstreams are checked

---

### Pitfall 5: Webhook Signature Verification Missing

**What goes wrong:**
You implement `/api/workflows/{id}/trigger` endpoint but forget HMAC verification. Any caller can trigger workflows without authentication.

**Why it happens:**
Rushing to expose webhook endpoint; assuming JWT auth applies (it doesn't; webhook is unauthenticated by design).

**Consequences:**
- Attacker triggers expensive workflows repeatedly (DoS)
- Sensitive data in workflow outputs leaks if attacker runs with specific parameters
- Reputational damage

**Prevention:**
- Require HMAC signature in all webhook endpoint code
- Test: call endpoint without signature header; verify 401 rejection
- Test: call with tampered signature; verify rejection
- Test: call with valid signature; verify 200 (only path that works)

**Detection:**
- Unit test: webhook endpoint rejection tests mandatory
- Code review: all webhook endpoints checked for signature verification

---

## Moderate Pitfalls

### Pitfall 1: DAG Cycles

**What goes wrong:**
Operator creates workflow with edge: A → B → C → A (cycle). dispatch_workflow_run() topological sort fails silently or crashes with cryptic error.

**Why it happens:**
Topological sort (Kahn's algorithm) assumes DAG; cycles cause infinite loop or missed nodes.

**Consequences:**
- Workflow rejected but error message unclear
- If sort crashes, WorkflowRun created but dispatch fails midway (orphaned state)

**Prevention:**
- Validate DAG acyclicity before dispatch (DFS cycle detection)
- Return HTTP 422 with clear error: "Cycle detected: A → B → C → A"
- Test: attempt to create workflow with cycle; verify rejection

**Detection:**
- Unit test: `dispatch_workflow_run(dag_with_cycle)` returns error (not crash)

---

### Pitfall 2: Gate Condition Timeout

**What goes wrong:**
Gate condition evaluates a complex Jinja2 expression that accesses a large job result (>10MB JSON). Evaluation takes 5 seconds. Job completion handler blocks waiting for gate eval, preventing other jobs from unblocking.

**Why it happens:**
Synchronous gate evaluation in critical path (job completion).

**Consequences:**
- Workflow stalls; downstream jobs don't dispatch for 5s
- Cascading delays in multi-stage workflows

**Prevention:**
- Profile gate evaluation with realistic job results (>1MB JSON)
- Add timeout to `_evaluate_gate_condition()` (e.g., 1s; raise exception if exceeded)
- If timeout, default gate to False (safe default; can be configurable)
- Pre-compile Jinja2 templates to cache

**Detection:**
- Performance test: measure gate eval time with 10MB result JSON
- Log: track gate eval latency; alert if >500ms

---

### Pitfall 3: Webhook Secret Rotation

**What goes wrong:**
Webhook secret is compromised (e.g., accidentally committed to GitHub). You rotate the secret (generate new one), but old CI/CD pipelines still use old secret. All webhook requests fail 401; pipelines break.

**Why it happens:**
No gradual migration path; instant secret rotation breaks existing callers.

**Consequences:**
- Immediate operational impact (CI/CD stops)
- Manual coordination needed to update all callers (GitHub, GitLab, Jenkins, etc.)

**Prevention:**
- Design secret rotation with grace period (e.g., accept old secret for 7 days after rotation)
- Store `secret_hash` + `previous_secret_hash` in database
- Accept signature from either current or previous secret
- Test: rotate secret; verify old signature still works for 7 days

**Detection:**
- Operational runbook: "Secret Rotation" step-by-step with timeline

---

### Pitfall 4: Timestamp Validation Window Too Narrow

**What goes wrong:**
Webhook endpoint validates timestamp with ±5 min window (standard). But operator's CI/CD server has clock skew (5+ min ahead). All webhook requests fail with "Request expired" even though signature is valid.

**Why it happens:**
5 min window is tight for global deployments; clock skew is common in VMs.

**Consequences:**
- Legitimate webhook requests rejected
- Operator spends hours debugging "why are my webhooks failing"

**Prevention:**
- Use ±10 min window (or configurable; default 5 min)
- Log rejected requests with timestamp delta (help operators diagnose clock skew)
- Document clock sync requirement in webhook runbook

**Detection:**
- Testing: simulate client clock ±7 min ahead; verify requests fail (if window is 5) or pass (if 10)

---

## Minor Pitfalls

### Pitfall 1: NULL Result Handling in Gate Evaluation

**What goes wrong:**
Job completes but `job.result` is NULL (e.g., job outputs nothing, only exit code). Gate condition `{{ result.exit_code }}` crashes with "NoneType has no attribute".

**Why it happens:**
Job with no structured output (just success/failure); gate assumes result exists.

**Prevention:**
- Default empty result to `{"exit_code": 0, "stdout": "", "stderr": ""}`
- Test gate with NULL result; verify graceful handling

**Detection:**
- Unit test: gate evaluation with NULL result must not crash

---

### Pitfall 2: Step Status Enum Inconsistency

**What goes wrong:**
Different parts of code use different status strings: "COMPLETED" vs "DONE", "SKIPPED" vs "SKIP", etc. Status checks like `if step.status == "COMPLETED"` fail silently.

**Prevention:**
- Define WorkflowRunStep.Status enum with canonical values
- Use enum in all comparisons (IDE autocomplete helps)

**Detection:**
- Code review: no string literals in status checks (use enum)

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|---------|-----------|
| 1 | Data Model | FK constraint validation | Test migrations on existing DB; use `IF NOT EXISTS` |
| 2 | BFS Runner | Topological sort | Unit test with cyclic DAG; verify rejection |
| 2 | Gate Evaluation | Code injection | Use Jinja2 sandbox; restrict context; unit test malicious conditions |
| 2 | Concurrent Unblock | Race condition | Lock WorkflowRun during unblock; test concurrent completion |
| 3 | Webhook Signature | Missing verification | Test 401 rejection without sig; test with tampered sig |
| 3 | Timestamp Validation | Clock skew | Test with ±10 min offset; configurable window |
| 4 | Workflow State | Orphaned runs | Implement watchdog for stalled runs; test node crash scenario |
| 5 | Canvas UI | Cycle creation | Prevent edges that form cycles; validate at save time |

---

## Prevention Checklist

- [ ] Depth limit overridable for workflow jobs (pass `max_depth=30` in Phase 2)
- [ ] Jinja2 sandbox tested with malicious conditions (Phase 2)
- [ ] Topological sort rejects cycles (Phase 2)
- [ ] Concurrent job completion race tested (Phase 2)
- [ ] Webhook signature verification mandatory (Phase 3)
- [ ] Timestamp validation with ±10 min window (Phase 3)
- [ ] WorkflowRunStep.Status enum (Phase 1)
- [ ] Workflow timeout watchdog (Phase 2 or 4)
- [ ] NULL result handling in gate eval (Phase 2)
- [ ] Migration script for existing DBs (Phase 1)

---

## Related Issues

This research updates `.agent/reports/core-pipeline-gaps.md` with workflow-specific risks. Recommend adding new gap entries:
- WF-1: Depth limit override for workflow jobs (Phase 2)
- WF-2: Gate condition sandbox validation (Phase 2, security-critical)
- WF-3: Workflow timeout watchdog (Phase 2 or 4)
- WF-4: Secret rotation grace period (Phase 3, operational)
