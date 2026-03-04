# Pitfalls Research

**Domain:** Distributed job scheduler — output capture, retry policies, DAG dependencies, CI/CD integration, environment promotion
**Researched:** 2026-03-04
**Confidence:** HIGH (codebase directly inspected; pitfalls verified against real Airflow/Celery issues, OWASP CI/CD guidance, and APScheduler docs)

---

## Critical Pitfalls

### Pitfall 1: Zombie Jobs — ASSIGNED State That Never Resolves

**What goes wrong:**
A node picks up a job (status → `ASSIGNED`), crashes, loses network, or is revoked mid-execution. The job stays in `ASSIGNED` forever. No other node will pick it up (the selector filters for `PENDING` only). The job queue silently fills with stuck jobs. Retry counts are never triggered because the job never transitions to `FAILED`.

**Why it happens:**
The pull model (`/work/pull` → `ASSIGNED`) sets status before the node has done any work. If the node disappears before reporting a result, there is no mechanism to reclaim the job. The current `job_service.py` has no timeout or reaper logic. APScheduler will re-fire the *definition* on schedule, but the stuck *instance* remains zombie.

**How to avoid:**
Implement a reaper task (run on a scheduler interval, e.g., every 60 seconds) that queries:
```sql
SELECT * FROM jobs
WHERE status = 'ASSIGNED'
AND started_at < NOW() - INTERVAL '<timeout>'
```
Transition those back to `PENDING` or `FAILED` (depending on retry policy). Timeout should be configurable per job or globally. Add `max_runtime_seconds` to the `Job` model.

**Warning signs:**
- Dashboard shows jobs stuck in ASSIGNED for minutes/hours
- Node count drops but ASSIGNED count does not decrease
- Revoked node still has ASSIGNED jobs in the DB

**Phase to address:** Output capture / retry policy phase (these are co-dependent — you can't implement retry without knowing when a job has truly failed)

**Security impact:** LOW (zombies are availability not confidentiality), but HIGH if a revoked node's jobs stay ASSIGNED — a revoked node's work must be immediately reclaimed and re-queued.

---

### Pitfall 2: Job Output Bloat Kills the Database

**What goes wrong:**
The `Job.result` column is `Text` (unbounded). When output capture stores raw `stdout`/`stderr` in this column, a script that prints 50 MB of output (or a runaway logging loop) fills the column with megabytes. In Postgres, Text uses TOAST (transparent overflow storage), so queries stay fast *until* many rows overflow. In SQLite, a 50 MB text value in a row causes query plan thrashing. At scale, `SELECT * FROM jobs` in `list_jobs` fetches full result blobs for every row — one large job brings the endpoint to its knees.

**Why it happens:**
Developers capture `result.stdout` fully (as done in `node.py`'s `run_python_script`) and store it verbatim in the result JSON. No size cap is applied. The current `list_jobs` query already does `SELECT *` with `LIMIT 50` but loads `job.result` for every row to build the response.

**How to avoid:**
- Cap output at the node side before reporting: truncate `stdout`/`stderr` at a configurable limit (default: 64 KB per stream). Store a `truncated: true` flag in the result.
- Split the schema: store a `Job.output_preview` column (first 2 KB) for the list view, and a separate `JobOutput` table or external blob reference for the full output.
- Never include full `result` in `list_jobs` — only include it in `GET /jobs/{guid}`.

**Warning signs:**
- `list_jobs` response latency climbs as job count grows
- DB file size grows disproportionately vs. number of jobs
- SQLite WAL file exceeds hundreds of MB

**Phase to address:** Output capture phase — design the schema correctly before any output is stored

**Security impact:** MEDIUM — oversized output could be used as a denial-of-service vector by a compromised node reporting gigabytes of data to exhaust disk.

---

### Pitfall 3: CI/CD Service Principals With Overly Broad Permissions Silently Undermine Zero-Trust

**What goes wrong:**
A CI/CD pipeline needs to dispatch jobs. A service principal is created with `operator` role, giving it `jobs:write` — but `operator` in the current seed also grants `foundry:write` and `signatures:write`. The pipeline's service principal can now *register new signing keys*, upload new blueprints, and build new Foundry images. If the pipeline is compromised (e.g., via a dependency injection attack or environment variable leak), the attacker can register their own Ed25519 public key, sign arbitrary scripts with the corresponding private key, and execute them on all nodes. The zero-trust model is fully bypassed without any mTLS attack.

**Why it happens:**
The `operator` role is seeded as a broad "trusted automation" role. CI/CD integrations are added quickly and inherit this role without thinking through the blast radius. OWASP CICD-SEC-5 (Insufficient Pipeline-Based Access Controls) identifies this as one of the top CI/CD risks — pipelines routinely receive more permissions than they need.

**How to avoid:**
- Create a dedicated `ci` role (or `dispatcher` role) with *only* `jobs:write` and `jobs:read`. No `signatures:write`, no `foundry:write`, no `users:read`.
- Document this in the CI/CD integration guide with a warning: "Do not give the dispatch service principal operator role."
- Consider making signature registration an admin-only permission, removing it from operator entirely.
- API keys used by CI/CD should have expiry dates (`expires_at` is already supported on `UserApiKey`).

**Warning signs:**
- CI/CD service principals have `operator` role
- No separate role exists for dispatch-only access
- Service principal API keys have no expiry

**Phase to address:** CI/CD integration phase — define the `ci` role *before* documenting the integration pattern

**Security impact:** CRITICAL — this is the single most likely path to compromising the zero-trust signing model.

---

### Pitfall 4: Retry Logic That Retries Non-Retriable Failures

**What goes wrong:**
A retry policy is added with `max_retries: 3`. A job fails because its Ed25519 signature is invalid (`Signature Verification Failed`). The scheduler retries it 3 times. All 3 attempts fail identically. This wastes node resources and clutters the audit log. Worse: if a job fails because it was dispatched to a revoked node (403 from `/work/pull`), automatic retry re-queues it to the same revoked node, which fails again — a tight failure loop that looks like a thundering herd.

**Why it happens:**
Retry policies are typically implemented as simple counters on failure, without distinguishing between *retriable* errors (network timeout, node crash, transient resource exhaustion) and *non-retriable* errors (signature verification failure, permission denied, script syntax error, explicit non-zero exit codes from the script itself).

**How to avoid:**
- Define a `retry_policy` with explicit `retriable_failures` classification.
- Non-retriable: signature failure, security rejection, explicit script exit codes > 1 for "bad input" (e.g., exit 2 for "invalid arguments").
- Retriable: node crash (job never reported result + reaper triggered), timeout exceeded, resource limit exceeded.
- Add jitter to retry delays to prevent thundering herd when many jobs fail simultaneously after a node outage: `delay = base_delay * 2^attempt + random(0, base_delay)`.
- Implement a circuit breaker: if a node fails 5 consecutive jobs, stop assigning to it.

**Warning signs:**
- Same job GUID appears in audit log failing identically multiple times
- `ASSIGNED` → `FAILED` → `PENDING` cycle repeating rapidly
- Node shows as ONLINE but has high failure rate

**Phase to address:** Retry policy phase

**Security impact:** MEDIUM — repeated signature failures being retried should generate alerts, not silent retries (could indicate a replay attack or key compromise).

---

### Pitfall 5: DAG Cycle Introduced by Editing Dependencies on Live Jobs

**What goes wrong:**
Job dependency graphs are configured at creation time, but editing a running DAG (changing which jobs depend on which) can introduce a cycle: Job A → B → C, then an operator edits C to depend on A. The system now has a circular dependency that will deadlock — all three jobs wait for their upstream job, which is waiting for them. The scheduler loop hangs without progressing.

**Why it happens:**
Cycle detection is only enforced at *creation* time if the implementation is naive. Editing a dependency mid-flight bypasses the initial check. Apache Airflow has had exactly this class of bug (issue #25765 — deadlock in scheduler loop from circular DAG run state).

**How to avoid:**
- Run cycle detection (topological sort) on every dependency *update*, not just creation. Reject the update if a cycle is detected.
- Store the DAG as an adjacency list and run DFS cycle detection on every mutation: O(V+E), negligible for homelab-scale graphs.
- Prohibit editing dependencies on jobs that are currently in an active run (status `PENDING` or `ASSIGNED`).

**Warning signs:**
- A job definition update changes `depends_on` field
- Jobs enter PENDING state but are never picked up by any node
- Scheduler loop shows no progress for > 2× the poll interval

**Phase to address:** DAG dependency phase

**Security impact:** LOW (availability), MEDIUM if deadlock causes signed jobs to never execute but their completion is assumed by downstream processes.

---

### Pitfall 6: Fan-in Race Condition — Multiple Upstream Jobs Completing Simultaneously

**What goes wrong:**
Job C depends on Jobs A and B completing. A and B finish at nearly the same time. Two concurrent `/work/{guid}/result` calls both check "are all predecessors done?" at the same time, both see the other has not yet been written to DB (race between commits), and both decide C is not ready. C never gets queued.

**Why it happens:**
Status propagation in a fan-in pattern requires a read-then-write check that is not atomic under concurrent updates. Dask distributed has documented exactly this race (issue #8576 — race condition in scatter/dereference). The pull model means nodes report results concurrently.

**How to avoid:**
- Use a database-level check: when reporting a result for job X, use a single atomic query to check if ALL predecessors of any waiting job are COMPLETED, then insert the newly-ready jobs in the same transaction.
- Alternatively: use a dedicated scheduler tick (every N seconds) that evaluates all `WAITING` jobs against their dependency graph. This trades latency for simplicity and avoids the race entirely.
- The scheduled-tick approach fits naturally with the existing APScheduler infrastructure and pull model.

**Warning signs:**
- Jobs with `depends_on` never transition out of `WAITING` even though their dependencies show `COMPLETED` in the DB
- Fan-in joins silently fail under load but work fine in sequential tests

**Phase to address:** DAG dependency phase — design before implementation

**Security impact:** LOW (correctness not security).

---

### Pitfall 7: Environment Tags Applied to Nodes But Not Enforced at Execution Time

**What goes wrong:**
`DEV`, `TEST`, `PROD` tags are added to nodes. A CI/CD pipeline dispatches a deployment job with `target_tags: ["prod"]`. The job is correctly routed to a PROD node. But: a separate service principal with `jobs:write` dispatches the same job with `target_tags: []` (empty), and it runs on any available node, including PROD. Or, an operator manually dispatches a "dev job" that lands on a PROD node because both have matching capability requirements and neither has tags enforced as exclusive.

**Why it happens:**
Tags in the current system are *additive* (a node can match any tag) but not *exclusive*. A node tagged `["prod"]` will also accept jobs with no tags. There is no concept of "this node only accepts jobs that explicitly carry the matching environment tag."

**How to avoid:**
- Add a node-level `require_tag_match: bool` config: if true, the node *only* accepts jobs that include at least one of the node's own tags.
- Document the promotion model explicitly: prod nodes should have `require_tag_match: true` so they reject untagged ad-hoc jobs.
- Environment tag check should happen at the node's secondary admission step in `node.py`, not just on the orchestrator side — defense in depth.

**Warning signs:**
- PROD-tagged nodes show jobs from ad-hoc dispatch (no tags) in their job history
- Untagged jobs end up on nodes they should not be on

**Phase to address:** Environment tags phase — before CI/CD integration is documented

**Security impact:** HIGH — this is a structural risk. If PROD nodes run unverified ad-hoc jobs, the isolation that environment promotion provides is illusory.

---

### Pitfall 8: Verification Key Fetched Without Signature — TOCTOU on Bootstrap

**What goes wrong:**
During node bootstrap, `fetch_verification_key()` fetches the Ed25519 public key from `/verification-key` over HTTPS and writes it to `secrets/verification.key`. If the orchestrator is compromised *at the moment a new node enrolls*, the attacker can serve a rogue public key. All subsequent signature verifications on that node will use the attacker's key, accepting scripts signed by the attacker's private key.

**Why it happens:**
The verification key endpoint is unauthenticated (intentionally, for bootstrap). The node trusts whatever the orchestrator serves. There is no mechanism for the node to verify that the verification key itself is correct (a bootstrapping problem, but one that needs a documented answer).

**How to avoid:**
- Pin the verification key hash in the `JOIN_TOKEN` payload alongside the CA cert. The node compares the fetched key's fingerprint against the pinned value and refuses to proceed if they don't match.
- Alternatively: include the verification key PEM directly in the `JOIN_TOKEN` (which is already base64 JSON). Eliminates the network fetch entirely.
- At minimum: log the verification key fingerprint on enrollment so it can be audited against the expected value.

**Warning signs:**
- Verification key content differs between nodes enrolled at different times (legitimate if the key was rotated, concerning if unintentional)
- Node accepts a job with a signature that the orchestrator did not issue

**Phase to address:** CI/CD integration phase (when bootstrap security is documented for automated enrollment)

**Security impact:** CRITICAL — this is an attack on the signing chain, the project's core security guarantee.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store full stdout in `Job.result` JSON column | Simple — no new table | DB bloat; slow list queries; DOS vector | Never — cap at node side and separate the schema before first output lands |
| Use `operator` role for CI/CD service principals | Fast to set up | Blast radius of a compromised pipeline includes key registration | Never — create `ci` role first |
| No retry classification (retry all failures) | Simple counter | Retry storms on non-retriable errors; security events silently retried | Only in MVP before any real security-classified failures exist |
| DAG dependencies checked only at creation | Simple insert logic | Edit-time cycles cause scheduler deadlock | Never — enforce on every mutation |
| Environment tags advisory-only (not exclusive) | Flexible routing | PROD nodes run dev jobs | Never — must be enforced at node level for isolation guarantee |
| Single `verification.key` file, updated on each fetch | Simple | TOCTOU on bootstrap; key rotation silently changes trust anchor | Never — pin in JOIN_TOKEN |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GitHub Actions / GitLab CI | Use a long-lived API key stored as a CI secret | Create a service principal with `ci` role, set `expires_at`, rotate on every deploy |
| GitHub Actions / GitLab CI | Give CI principal `operator` role for convenience | Create a minimal `ci` role with only `jobs:write` + `jobs:read` |
| GitHub Actions / GitLab CI | Expose `stdout` of dispatched job in CI logs by polling `GET /jobs/{guid}` | Filter/redact output before logging; treat job output as potentially sensitive |
| Script signing in CI | Sign scripts in CI using a key stored as a CI environment variable | The signing private key being in CI means CI compromise = code execution. Prefer signing scripts offline, committing signatures to the repo, and verifying the commit signature instead. |
| APScheduler on multiple processes | Run scheduler in multiple replicas behind a load balancer | APScheduler with in-memory or SQLite job store does not support multi-process coordination — jobs will fire multiple times. Use a single scheduler process or a DB-backed job store with process locks. |
| Retry + APScheduler | Re-queue failed scheduled jobs inside APScheduler's job function | Re-queuing inside APScheduler creates a separate one-time job that APScheduler doesn't track. Use the `Job` table retry counter instead, managed by the reaper/poll loop. |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `SELECT * FROM jobs` loads full `result` blobs for list view | List endpoint latency grows with job result size | Select only metadata columns for list; fetch full result only in detail endpoint | ~1000 jobs with large outputs |
| `NodeStats` pruning uses subquery with `IN (SELECT id ...)` — SQLite compat issue (MIN-6) | SQLite raises error on correlated subquery form; stats pruning silently fails; table grows unbounded | Use a keyset approach: `DELETE WHERE id NOT IN (SELECT id ... ORDER BY ... LIMIT 60)` or use a raw SQL string for SQLite compat | Immediately on SQLite dev environments |
| Capability matching scans all PENDING jobs in a loop (up to `LIMIT 50`) per poll | Poll endpoint latency grows with queue depth | Add DB index on `(status, created_at)`; consider a separate indexed `ready_queue` table | ~5000 pending jobs |
| Job output streamed from node in a single POST body | Large output causes connection timeout; result lost | Cap output size at node, or implement chunked output upload | Jobs with >10 MB output |
| APScheduler `misfire_grace_time` defaults to 1 second | Short-lived scheduled tasks that can't fire exactly on time are silently skipped | Set `misfire_grace_time` to a reasonable value (e.g., 5 minutes for typical jobs); log missed fires | Any schedule under moderate system load |

---

## Security Mistakes

| Mistake | Risk | Prevention | Security Impact |
|---------|------|------------|-----------------|
| CI/CD principal has `signatures:write` | Attacker can register their own Ed25519 key, sign arbitrary scripts, execute on all nodes | Separate `ci` role without `signatures:write`; make key registration admin-only | CRITICAL |
| Verification key fetched over network without pinning | Bootstrap TOCTOU: compromised orchestrator at enroll time serves rogue key | Pin key hash or PEM in `JOIN_TOKEN` | CRITICAL |
| Retry on signature verification failure | Security rejection silently retried, masking a potential attack signal | Classify signature failures as non-retriable; generate an alert/audit entry | HIGH |
| Environment tags not enforced at node (advisory-only) | PROD nodes accept untagged ad-hoc jobs from any authorized user | Enforce `require_tag_match` at node secondary admission | HIGH |
| Job output logged to CI stdout without filtering | Secrets injected into job environment appear in CI logs if script prints them | Node must strip `secrets` dict values from stdout before reporting | HIGH |
| Long-lived CI API keys with no expiry | Compromised key has indefinite access | Enforce `expires_at` on all CI service principal keys; document rotation procedure | MEDIUM |
| DAG dependency editing not audited | Changes to job dependencies not traceable if an incident occurs | Audit log every `PATCH /jobs/definitions/{id}` that modifies `depends_on` | MEDIUM |
| Failed/ASSIGNED jobs from revoked nodes not immediately reclaimed | Revoked node's pending work stays in ASSIGNED, blocking queue; if node somehow re-enrolls it resumes work | Reaper queries `nodes.status = REVOKED` and reclaims ASSIGNED jobs immediately on revocation | HIGH |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Show full stdout in job detail with no truncation UI | A job that printed 1 MB of output freezes the browser tab | Paginate output display; show first 100 lines with "load more"; never render the full blob at once |
| Retry count displayed but not retry history | Operator can't tell *which* retries failed and *why* | Show a per-attempt history: attempt 1 → FAILED (timeout), attempt 2 → FAILED (signature), attempt 3 → COMPLETED |
| DAG dependency graph shown as adjacency list only | Operator cannot visualize a 10-job pipeline | Provide a simple ASCII DAG or a react-flow visualization in the job detail pane |
| Environment tag filter not on job dispatch form | Operator must know tag names from memory | Show available environment tags as a dropdown populated from nodes' current tags |
| No distinction between "job failed" and "job timed out (zombie)" | Operator can't tell if a node crashed or the script had a bug | Report `FAILED (timeout/reclaimed)` vs. `FAILED (exit code N)` as separate status labels |

---

## "Looks Done But Isn't" Checklist

- [ ] **Output capture:** Verify output is capped at the node — a script that runs `print("x" * 100_000_000)` should NOT fill the `result` column with 100 MB.
- [ ] **Retry policy:** Verify that signature verification failures are classified non-retriable — run a job with a bad signature and confirm it goes to FAILED without retrying.
- [ ] **Zombie reaper:** Verify that killing a node mid-job causes the job to return to PENDING (or FAILED) within the configured timeout — not stay ASSIGNED forever.
- [ ] **DAG cycle detection:** Verify that creating a cycle via an edit is rejected — create A→B, then try to add A as a dependency of B and confirm a 400 error.
- [ ] **Fan-in correctness:** Verify that a 3-way fan-in (A, B, C all must complete before D) reliably queues D when all three complete near-simultaneously, not just when they complete sequentially.
- [ ] **PROD tag exclusivity:** Verify that a job dispatched with no tags does NOT land on a node tagged `["prod"]` when `require_tag_match: true` is set on that node.
- [ ] **CI principal blast radius:** Verify that a service principal with `ci` role cannot call `POST /admin/signatures` — confirm it gets 403.
- [ ] **APScheduler misfire:** Verify that a job scheduled for a time in the past (simulated by setting `misfire_grace_time` low and pausing the process) either fires or is logged as missed — not silently skipped.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Zombie jobs fill queue | MEDIUM | Run manual SQL: `UPDATE jobs SET status='FAILED' WHERE status='ASSIGNED' AND started_at < <cutoff>`. Add reaper before next deploy. |
| DB bloated with large outputs | HIGH | Export job GUIDs, truncate `result` column values above threshold, migrate to `JobOutput` table. Consider pg_dump + selective restore. |
| CI principal registered rogue signing key | CRITICAL | Immediately: revoke the signing key (`DELETE FROM signatures WHERE id=...`), revoke all nodes and force re-enrollment (so stale verification keys are replaced), rotate the compromised service principal. Audit all jobs run since the key was registered. |
| Zombie reaper mis-fires and reclaims a legitimate long-running job | MEDIUM | Add `max_runtime_seconds` to `Job` model; reaper only reclaims jobs exceeding their declared max. For jobs without a declared max, use a conservative global default (e.g., 10 minutes). |
| DAG deadlock (circular dependency reaches production) | MEDIUM | Identify the cycle via topological sort query on the dependency table. Break the cycle by removing one edge (update the `depends_on` list). Force-fail any WAITING jobs in the cycle so they can be re-queued once the cycle is fixed. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Zombie ASSIGNED jobs | Output capture + retry policy phase | Test: kill node mid-job, wait for reaper interval, confirm job returns to PENDING |
| Output bloat in DB | Output capture phase (schema design before first output lands) | Test: submit job that prints 100 MB, verify DB column stays under cap |
| CI principal over-privileges | CI/CD integration phase (before integration is documented) | Test: CI principal cannot call `POST /admin/signatures` |
| Retry on non-retriable failures | Retry policy phase | Test: signature verification failure does not retry |
| DAG cycle via edit | DAG dependency phase | Test: edit that creates cycle returns 422 |
| Fan-in race condition | DAG dependency phase | Test: concurrent fan-in under load, confirm downstream job queued exactly once |
| PROD tag not exclusive | Environment tags phase | Test: untagged job does not land on `require_tag_match` PROD node |
| Verification key TOCTOU | CI/CD integration phase (bootstrap docs) | Test: pin key in JOIN_TOKEN, verify node rejects non-matching key |
| Thundering herd on retry | Retry policy phase | Test: 50 jobs fail simultaneously, verify retries spread over time with jitter |
| APScheduler misfire | Cron/scheduling phase (always use UTC; set misfire_grace_time) | Test: schedule a job at a past time, verify it fires or is logged as missed |

---

## Sources

- OWASP CI/CD Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html
- OWASP Top 10 CI/CD Security Risks — CICD-SEC-5 (Insufficient PBAC): https://owasp.org/www-project-top-10-ci-cd-security-risks/CICD-SEC-05-Insufficient-PBAC
- APScheduler FAQ — missed jobs, shared job stores, DST: https://apscheduler.readthedocs.io/en/3.x/faq.html
- APScheduler User Guide — misfire_grace_time: https://apscheduler.readthedocs.io/en/3.x/userguide.html
- Apache Airflow issue #25765 — deadlock in scheduler loop from circular DAG: https://github.com/apache/airflow/issues/25765
- Apache Airflow issue #23824 — race condition between Triggerer and Scheduler: https://github.com/apache/airflow/issues/23824
- Dask distributed issue #8576 — race condition in scatter/dereference (fan-in pattern): https://github.com/dask/distributed/issues/8576
- Airflow 2.6.0 — fixing stuck queued tasks: https://medium.com/apache-airflow/unsticking-airflow-stuck-queued-tasks-are-no-more-in-2-6-0-6f40a1a22835
- Better Stack — exponential backoff + thundering herd: https://betterstack.com/community/guides/monitoring/exponential-backoff/
- DevOps.com — why CI/CD pipelines break zero-trust: https://devops.com/why-ci-cd-pipelines-break-zero-trust-a-hidden-risk-in-enterprise-automation/
- OWASP CICD-SEC-5 — Pipeline-Based Access Controls: https://owasp.org/www-project-top-10-ci-cd-security-risks/CICD-SEC-05-Insufficient-PBAC
- System Design Handbook — distributed job scheduler: https://www.systemdesignhandbook.com/guides/design-a-distributed-job-scheduler/
- Direct codebase inspection: `puppeteer/agent_service/db.py`, `job_service.py`, `puppets/environment_service/node.py`
- Known deferred issues: `.agent/reports/core-pipeline-gaps.md` (MIN-6, MIN-7, MIN-8, WARN-8)

---
*Pitfalls research for: Master of Puppets — milestone adding output capture, retry policies, DAG dependencies, environment tags, CI/CD integration*
*Researched: 2026-03-04*
