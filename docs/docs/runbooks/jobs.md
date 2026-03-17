# Job Execution Troubleshooting

This runbook covers failures that occur from job submission through execution and result reporting. Use it when a job is stuck, rejected, or disappears from the queue — match the dashboard status badge or log line you observe to the symptom below and follow the recovery steps.

## Quick Reference

| Symptom | Section |
|---------|---------|
| Job stuck in `PENDING` or `QUEUED` indefinitely | [Job stuck in Queued / PENDING indefinitely](#job-stuck-in-queued-pending-indefinitely) |
| Job status is `BLOCKED` | [Job status is BLOCKED](#job-status-is-blocked) |
| Job status is `CANCELLED` with "cancelled because upstream failed" | [Job status is CANCELLED — upstream dependency failed](#job-status-is-cancelled-upstream-dependency-failed) |
| Job status is `DEAD_LETTER` | [Job status is DEAD_LETTER](#job-status-is-dead_letter) |
| Job status is `ZOMBIE_REAPED` | [Job status is ZOMBIE_REAPED](#job-status-is-zombie_reaped) |
| Job status is `SECURITY_REJECTED` — Signature Verification FAILED | [SECURITY_REJECTED — Signature Verification FAILED](#security_rejected-signature-verification-failed) |
| Job status is `SECURITY_REJECTED` — Verification Key missing | [SECURITY_REJECTED — Verification Key missing](#security_rejected-verification-key-missing) |
| Job status is `SECURITY_REJECTED` — Missing script or signature | [SECURITY_REJECTED — Missing script or signature](#security_rejected-missing-script-or-signature) |
| Job moves from `ASSIGNED` to `FAILED` or `ZOMBIE_REAPED` after ~30 minutes | [Job reaped after ~30 minutes](#job-reaped-after-30-minutes) |
| Node never reports job result — job stays `ASSIGNED` indefinitely | [Job stays ASSIGNED indefinitely](#job-stays-assigned-indefinitely) |

---

## Dispatch Failures

### Job stuck in Queued / PENDING indefinitely

The orchestrator found no node with matching tags, required capabilities, and sufficient memory budget. Jobs remain `PENDING` until a matching node checks in — they are never dropped silently.

**Recovery steps:**

1. Open **Jobs** view and note the job's `capability_requirements` and `target_tags`.
2. Open **Nodes** view and confirm at least one node with `Online` status has the required capabilities. Select a node and check its capabilities panel.
3. If no node qualifies, either reduce the job's requirements or enroll a node with the needed capabilities.
4. If the job has a `memory_limit` set, check that at least one online node has sufficient free memory headroom — nodes with insufficient memory are skipped by the selection loop.

**Verify it worked:**

Watch the job status in the **Jobs** view. After a matching node checks in (within its next poll interval), the status should change from `PENDING` to `ASSIGNED`.

Expected: job status badge transitions to `ASSIGNED` within 30 seconds of a matching node coming online.

If the issue persists after a node with matching capabilities is Online, check orchestrator logs for node selection output — look for lines indicating why each candidate node was skipped.

---

### Job status is BLOCKED

The job has a `depends_on` dependency that has not yet reached `COMPLETED` status. `BLOCKED` is expected behaviour — the job will unblock automatically when its dependency completes.

**Recovery steps:**

1. Open the **Jobs** view and identify the dependency job listed under `depends_on`.
2. Check the dependency job's current status.
   - If it is `RUNNING` or `ASSIGNED`: no action needed — wait for it to complete.
   - If it is `FAILED` or `DEAD_LETTER`: the dependent job will be `CANCELLED` (see [Job status is CANCELLED](#job-status-is-cancelled-upstream-dependency-failed)). Investigate the dependency failure first.
   - If it is `PENDING` or `QUEUED`: the dependency itself may be blocked — repeat this process for it.

**Verify it worked:**

Observe the dependency job reaching `COMPLETED`. The dependent job should automatically move to `QUEUED` within one poll cycle.

If the dependent job remains `BLOCKED` after the dependency has `COMPLETED`, check orchestrator logs for errors in the dependency resolution loop.

---

### Job status is CANCELLED — upstream dependency failed

The upstream dependency job failed, and the orchestrator propagated cancellation to all downstream dependents. The following log line appears in the orchestrator logs:

```
🚫 Job <guid> cancelled because upstream <guid> failed
```

The dependent job cannot be recovered in place — it must be resubmitted once the underlying problem is fixed.

**Recovery steps:**

1. Identify the upstream dependency job (the second `<guid>` in the log line above).
2. Open the upstream job's execution record and check its output for the failure reason.
3. Fix the root cause of the upstream failure (script error, missing resource, or signing problem).
4. Resubmit the upstream job. If it completes successfully, resubmit the originally-cancelled downstream job.

**Verify it worked:**

Resubmit both jobs and confirm the upstream job reaches `COMPLETED`. The downstream job should then reach `COMPLETED` (or `ASSIGNED`) without being `CANCELLED`.

If the issue persists, check that the `depends_on` chain is correct and that the upstream job's fix addresses the original failure cause.

---

### Job status is DEAD_LETTER

The job failed on every retry attempt up to its `max_retries` limit. The orchestrator marks it `DEAD_LETTER` and creates an alert. The following log line appears in the orchestrator logs:

```
Job <guid> exhausted all <N> retries and failed terminally.
```

!!! danger "DEAD_LETTER jobs cannot be retried"
    A job in `DEAD_LETTER` status is permanently terminal. You cannot retry it — you must fix the underlying issue and submit a new job.

**Recovery steps:**

1. Open the job's execution record in the **Jobs** view and read the output or error message from the final attempt.
2. Identify the root cause: script error, missing dependency, resource constraint, or signing problem.
3. Fix the underlying issue in your script or job configuration.
4. Submit a new job with the corrected script (re-signed via `axiom-push` if the script was changed).

**Verify it worked:**

The new job should progress past `QUEUED` to `COMPLETED` without reaching `FAILED`.

If the new job also fails, compare its output with the original — look for environment differences, node capability gaps, or persistent resource constraints.

---

### Job status is ZOMBIE_REAPED

The job was `ASSIGNED` to a node, but the node stopped sending execution updates (crash, OOM kill, or network partition). The zombie reaper reclaims the job after `zombie_timeout_minutes` elapses (default: 30 minutes, configurable via **Admin → Configuration**).

**Recovery steps:**

1. Check whether the assigned node is still `Online` in the **Nodes** view.
2. If the node went `Offline`, run `docker logs <node-container>` to check for OOM kill messages or runtime errors.
3. If the node was OOM killed, increase the node's `job_memory_limit` or reduce the job's `memory_limit`.
4. If retries remain, the reaped job is automatically returned to `QUEUED` for reassignment. If retries are exhausted, it moves to `FAILED` — resubmit a new job.

**Verify it worked:**

Confirm the node returns to `Online` status. If retries remain, watch the job move back to `ASSIGNED` on the next healthy node.

If the node keeps crashing on the same job, the job's memory or CPU requirements likely exceed what the node can provide — adjust limits before resubmitting.

---

## Signing Errors

### SECURITY_REJECTED — Signature Verification FAILED

The node verified the job's signature against the registered Ed25519 public key and the check failed. Either the script was signed with a different key than the one registered in **Signatures**, or the script content was modified after signing. The following log line appears in the node's container output:

```
[node-abc12345] ❌ Signature Verification FAILED for Job <guid>: <exception detail>
```

**Recovery steps:**

1. Check which Ed25519 key was used to sign the script. The `axiom-push` tool shows the key fingerprint at signing time.
2. Open **Signatures** in the dashboard and confirm the matching public key is registered.
3. If the key is missing, register it: see [Ed25519 Key Setup](../feature-guides/axiom-push.md#ed25519-key-setup).
4. If the script was modified after signing, re-sign it with `axiom-push` and resubmit.

!!! warning "Do not manually edit signed scripts"
    Any modification to a script after signing — including whitespace changes — invalidates the signature. Always re-sign after any edit.

**Verify it worked:**

Resubmit the job and confirm it reaches `ASSIGNED` rather than `SECURITY_REJECTED`. Check the node logs for the absence of the `❌ Signature Verification FAILED` line.

If the issue persists, confirm the public key in **Signatures** is the exact hex or PEM of the key that signed the script — a key registered under the wrong name is a common cause of repeat failures.

---

### SECURITY_REJECTED — Verification Key missing

The node could not fetch the verification public key from the orchestrator's `/verification-key` endpoint at startup — usually a transient connectivity issue or the node started before the orchestrator was ready. The following log line appears in the node's container output:

```
[node-abc12345] ❌ CRITICAL: Verification Key missing. Cannot verify signature.
```

Until the verification key is loaded, the node rejects every job with `SECURITY_REJECTED`.

**Recovery steps:**

1. Restart the node container. On restart, the node re-fetches the verification key from the orchestrator.
2. If the error persists after restart, confirm the orchestrator is reachable at `AGENT_URL` from within the node's network. Run `docker exec <node-container> curl -k <AGENT_URL>/api/verification-key` to test connectivity.
3. If the orchestrator is unreachable, check `AGENT_URL` in the node's environment variables and verify no firewall or DNS issue blocks the connection.

**Verify it worked:**

Check the node startup logs for `[node-abc12345] 🔑 Verification Key updated.` — this line confirms the key was fetched successfully.

If the verification key line is missing and the CRITICAL error persists, the orchestrator endpoint may be unhealthy — check orchestrator logs for startup errors.

---

### SECURITY_REJECTED — Missing script or signature

The job payload reached the node without a `signature` field. This happens when a job is submitted directly via the API without using `axiom-push`, or when the signing step was skipped. The node returns the following string in the execution result:

```
Missing script or signature
```

!!! danger "Bypassing signing is not supported"
    Signature verification is enforced at the node before any script executes. There is no configuration flag to disable it. Every job must be signed with a registered Ed25519 key.

**Recovery steps:**

1. Resubmit the job using `axiom-push`, which handles signing automatically. See [Ed25519 Key Setup](../feature-guides/axiom-push.md#ed25519-key-setup) for setup instructions.
2. If submitting via the API directly, ensure the job payload includes a valid `signature` field. The signature must cover the exact script content and be produced by a key registered in **Signatures**.

**Verify it worked:**

Resubmit via `axiom-push` and confirm the job reaches `ASSIGNED` (or `COMPLETED`) without `SECURITY_REJECTED` status.

If the issue persists, confirm that `axiom-push` is configured with a key whose public half is registered in the dashboard **Signatures** view.

---

## Timeout Patterns

### Job reaped after ~30 minutes

The zombie reaper fires after `zombie_timeout_minutes` elapses (default: 30 minutes). This is the effective operator-visible timeout for job execution. If the executing node stopped reporting progress within this window — whether due to a crash, OOM kill, or network partition — the orchestrator reclaims the job and marks it `ZOMBIE_REAPED` or `FAILED`.

!!! tip "The 30-minute limit is configurable"
    To increase the timeout for long-running jobs, go to **Admin → Configuration** and set `zombie_timeout_minutes` to a higher value. This applies globally to all jobs.

**Recovery steps:**

1. If the job genuinely requires more than 30 minutes to complete, increase `zombie_timeout_minutes` via **Admin → Configuration**.
2. If the node crashed mid-execution, run `docker logs <node-container>` to check for OOM messages or unhandled exceptions.
3. If the node was OOM killed, increase the node's `job_memory_limit` or reduce the job's `memory_limit`.
4. Once the node is stable and the timeout is adjusted, resubmit the job (if retries are exhausted) or let the queue reassign it (if retries remain).

**Verify it worked:**

Watch the resubmitted job progress through `ASSIGNED` → `RUNNING` → `COMPLETED` without being reaped again.

If the job is still being reaped after raising the timeout, the node may be crashing for a reason unrelated to timeout — check node logs for fatal errors during script execution.

---

### Job stays ASSIGNED indefinitely

The node container was OOM killed (memory limit hit) or suffered a network partition. The heartbeat stops, but the zombie reaper has not yet fired — the job appears stuck in `ASSIGNED` with no progress.

**Recovery steps:**

1. Open the **Nodes** view and check whether the assigned node is `Online` or `Offline`. An OOM-killed node typically goes `Offline` within a few seconds of the kill.
2. Run `docker stats <node-container>` to check current memory usage against the container's limit. If the container is gone, check `docker inspect` for the last exit code — exit code `137` indicates OOM kill.
3. Increase `job_memory_limit` on the node template or reduce the job's `memory_limit`.
4. The zombie reaper will reclaim the job within `zombie_timeout_minutes` (default: 30 minutes) and return it to `QUEUED` if retries remain.

**Verify it worked:**

After the zombie reaper fires, confirm the job moves back to `QUEUED` and is successfully reassigned to a node with adequate memory. Watch for `COMPLETED` status on the next execution.

If the job is repeatedly stuck in `ASSIGNED` across multiple nodes, the script itself may be consuming unbounded memory — profile the script and add explicit memory limits.

---

## See Also

- [axiom-push: Signing and publishing jobs](../feature-guides/axiom-push.md)
- [Ed25519 Key Setup](../feature-guides/axiom-push.md#ed25519-key-setup)
- [FAQ](faq.md)
