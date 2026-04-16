# Workflow Operations Runbook

This runbook covers common workflow operations and troubleshooting. Use it when a workflow is stuck, fails unexpectedly, or behaves incorrectly — match the status or symptom you observe to the section below and follow the recovery steps.

## Quick Reference

| Task | Endpoint / Dashboard Path | Command |
|------|--------------------------|---------|
| List all workflows | GET /api/workflows | `curl -H "Authorization: Bearer $TOKEN" https://api.example.com/api/workflows` |
| Trigger a workflow manually | POST /api/workflow-runs | Dashboard: Workflows → select workflow → Trigger Run button |
| View workflow run status | GET /api/workflows/{id}/runs/{run_id} | Dashboard: Workflows → select workflow → click run |
| Cancel a running workflow run | DELETE /api/workflows/{id}/runs/{run_id} | Dashboard: WorkflowRunDetail → Cancel button |
| View step logs and output | GET /api/executions/{job_guid}/logs | Dashboard: WorkflowRunDetail → click step → open drawer |
| Create a webhook trigger | POST /api/workflows/{id}/webhooks | API only (Phase 151 UI coming) |
| Test webhook trigger | POST /api/webhooks/{webhook_id}/trigger | Use Python example from API docs |
| Monitor live updates | WebSocket /ws?token={jwt} | Dashboard auto-connects; subscribe to `workflow_run_updated` events |

## Common Operator Tasks

### Checking if a workflow is stuck

A workflow run may appear stuck if it remains in `RUNNING` status for an unusually long time without progressing through steps.

**Steps to check:**

1. Open the **Workflows** view in the dashboard and click on the workflow to view its run history.
2. Click the relevant run to open **WorkflowRunDetail**.
3. Check the `status` field and `started_at` timestamp. If the run has been in `RUNNING` for > 1 hour with no recent step completion, it may be stuck.
4. Click on individual steps in the DAG to check their status and logs.
5. Look for a step with status `RUNNING` or `ASSIGNED` that hasn't progressed in > 30 minutes.

**Solution:**

If you identify a hung step, cancel the entire workflow run:

```
DELETE /api/workflows/{workflow_id}/runs/{run_id}
```

Or via the dashboard: **WorkflowRunDetail → Cancel button**. This aborts all `ASSIGNED` and `RUNNING` steps, marks `PENDING` steps as `CANCELLED`, and sets the workflow status to `CANCELLED`.

**Investigate the cause:**

- Open the hung step's logs (click step → open drawer) to see the last output.
- Check if the step's job definition is valid and the referenced job exists.
- Verify that the node assigned to the job was `Online` at the time.

### Viewing a failed step's output

When a workflow run completes with status `FAILED` or `PARTIAL`, identify which step failed and inspect its logs.

**Steps:**

1. Open **WorkflowRunDetail** for the failed run.
2. The DAG canvas shows each step with a status badge (green = `COMPLETED`, red = `FAILED`, orange = `RUNNING`, etc.).
3. Click on the red (failed) step to open the **Step Drawer**.
4. The drawer shows:
   - `job_guid`: UUID of the underlying job execution
   - `status`: the step's final status
   - `result_json`: output from the step's job
   - `error_message`: (if failed) the error that caused failure
   - **Logs** tab: raw stdout/stderr from the job
5. Review the logs and result to identify the root cause.

### Understanding PARTIAL status

`PARTIAL` status is not an error — it is expected when an `IF_GATE` isolates a failure, allowing downstream branches to run independently.

**Example scenario:**

```
Step A (SCRIPT) → [IF_GATE] → Step B (failure handler)
                ↓
            Step C (normal handler)

If Step A fails:
- IF_GATE evaluates the failure condition and routes to Step B
- Step B (failure handler) executes successfully
- Step C is marked CANCELLED (not executed)
- Workflow status: PARTIAL (not FAILED)
```

In this case, `PARTIAL` means "the workflow ran, but not all paths were taken due to gate isolation."

**To verify:**

1. Open **WorkflowRunDetail** and examine the DAG.
2. Look for `IF_GATE` nodes with colored edges. A blue edge represents the "taken" branch; grayed edges represent branches not executed.
3. Check the gate's config to confirm the condition logic.

### Monitoring cron schedules (Phase 149)

Workflows can be scheduled to run automatically via cron expression.

**Check the schedule:**

1. Open **Workflows** list and look for the `schedule_cron` field.
2. The next run time is computed from the current time and the cron expression.
3. Each scheduled run will trigger automatically at the specified time.

**Verify a cron ran:**

Check the workflow's run history:

```
GET /api/workflows/{workflow_id}/runs
```

Look for runs with `trigger_type: "CRON"` and a recent `created_at` timestamp. If a scheduled time has passed but no cron-triggered run appears, check the orchestrator logs for scheduler errors.

### Testing a webhook trigger

Webhooks allow external systems to trigger workflow runs via HTTP POST with HMAC-SHA256 signature validation.

**Steps:**

1. Create a webhook endpoint:
   ```
   POST /api/workflows/{workflow_id}/webhooks
   ```
   Response includes `webhook_id` and `secret` (revealed once only).

2. Use the Python example from the **API Reference** to send a signed webhook trigger:
   ```
   POST /api/webhooks/{webhook_id}/trigger
   ```
   with headers: `X-Webhook-Signature`, `X-Webhook-Timestamp`, `X-Webhook-Nonce`

3. Verify the run was created:
   ```
   GET /api/workflows/{workflow_id}/runs
   ```
   Look for a new run with `trigger_type: "WEBHOOK"`.

4. Monitor the run's progress in **WorkflowRunDetail**.

## Troubleshooting

### Symptom: Workflow never progresses (stuck in RUNNING)

A workflow run remains in `RUNNING` status for an extended period without stepping through any new step nodes.

**Likely cause:**

A step is hung waiting for its underlying job to complete. The node executing the job may have crashed, gone offline, or is blocked on I/O.

**Debug steps:**

1. Fetch the run details:
   ```
   GET /api/workflows/{workflow_id}/runs/{run_id}
   ```

2. Examine the `steps` array and look for a step with status `RUNNING` or `ASSIGNED`.

3. Check the node status:
   - Open the **Nodes** view in the dashboard.
   - Find the node that was assigned to this step.
   - Confirm the node is `Online`.

4. View the step's logs:
   - Open **WorkflowRunDetail** in the dashboard.
   - Click the hung step in the DAG.
   - Open the **Step Drawer** and check the **Logs** tab.

**Fix:**

Cancel the entire run:

```
DELETE /api/workflows/{workflow_id}/runs/{run_id}
```

Then investigate the root cause:
- Check node container logs: `docker logs <node-container>`
- Verify the job definition referenced by the step is valid.
- Confirm network connectivity between the node and orchestrator.

---

### Symptom: Workflow marked FAILED when expected PARTIAL

A workflow run ended with status `FAILED` when you expected `PARTIAL` (an IF gate isolating a failure branch).

**Likely cause:**

- The IF gate's failure branch is not properly configured.
- Step edges are missing or incorrect, so the gate can't route to the failure handler.
- Gate condition logic is evaluating incorrectly.

**Debug steps:**

1. Open **WorkflowRunDetail** and visually inspect the DAG.
2. Identify the failed step (red badge).
3. Trace the edges from that step forward. Does the DAG show a path to an IF gate?
4. Click the IF gate node and check its `config_json`:
   - Is the `conditions` array non-empty?
   - Do the `path` and `value` fields match the failed step's output structure?
5. Check the failed step's `result_json` to confirm the condition would match.

**Fix:**

- If the gate has no failure branch configured, update the workflow to add edges from the gate to a failure handler step.
- If the condition logic is wrong, update the `config_json` to match your step's output structure.
- Test by manually triggering the workflow again.

---

### Symptom: Webhook events rejected (400 Bad Request)

Webhook trigger requests return HTTP 400 with an error message indicating signature verification failure.

**Likely cause:**

- X-Webhook-Signature header does not match HMAC-SHA256(secret, payload + timestamp)
- X-Webhook-Timestamp is too old (outside ±5 minute tolerance)
- X-Webhook-Nonce was already used recently (within 24-hour replay window)

**Debug steps:**

1. Verify the webhook secret is correct (from the webhook creation response).
2. Check your signature computation:
   ```python
   import hmac, hashlib
   
   secret = "whsec_ABC..."
   payload = '{"parameters": {...}}'
   timestamp = str(int(time.time()))
   message = payload + timestamp
   
   # Compute signature
   sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
   print(f"Expected header: X-Webhook-Signature: {sig}")
   ```
3. Verify the timestamp is recent (within 5 minutes of server time).
4. Ensure the nonce is unique and has not been used in the past 24 hours.

**Fix:**

- Re-compute the signature with the correct secret and fresh timestamp.
- If the secret was lost, delete the webhook and create a new one:
  ```
  DELETE /api/workflows/{workflow_id}/webhooks/{webhook_id}
  POST /api/workflows/{workflow_id}/webhooks
  ```
- Test the corrected request.

---

### Symptom: Parameters not injected into step jobs

Step jobs are not receiving expected workflow parameter values (e.g., `WORKFLOW_PARAM_target_environment`).

**Likely cause:**

- The workflow definition does not include a `parameters` array, so parameters are not defined.
- The manual trigger request did not include `parameters` dict in the body.
- The step job's script is not looking for `WORKFLOW_PARAM_*` environment variables.

**Debug steps:**

1. Check the workflow definition:
   ```
   GET /api/workflows/{workflow_id}
   ```
   Look for a `definition.parameters` array. If empty, no parameters are defined.

2. Check the manual trigger request body:
   ```
   POST /api/workflow-runs
   {
     "workflow_id": "...",
     "parameters": { "target_environment": "staging" }
   }
   ```
   Ensure the `parameters` dict includes all expected keys.

3. Check the step job's script to confirm it reads from `WORKFLOW_PARAM_*` environment variables:
   ```bash
   echo $WORKFLOW_PARAM_target_environment
   ```

**Fix:**

- If parameters are not defined, update the workflow:
  ```
  PATCH /api/workflows/{workflow_id}
  {
    "definition": {
      ...
      "parameters": [
        { "name": "target_environment", "type": "string", "default_value": "production" }
      ]
    }
  }
  ```
- When triggering, ensure the parameters dict is passed:
  ```
  POST /api/workflow-runs
  {
    "workflow_id": "...",
    "parameters": { "target_environment": "staging" }
  }
  ```
- Update the step job script to read from the environment variables.

---

### Symptom: IF gate took wrong branch

An IF gate evaluated a condition and took the wrong branch (executed the failure handler when it should have executed the success handler, or vice versa).

**Likely cause:**

- Condition logic error: the `path`, `operator`, or `value` fields don't match the upstream step's actual output.
- Result structure mismatch: the upstream step's output doesn't contain the expected field.
- Operator precedence or logic error in compound conditions.

**Debug steps:**

1. Open **WorkflowRunDetail** and click the IF gate to inspect its `config_json`:
   ```json
   {
     "conditions": [
       {
         "path": "status",
         "operator": "equals",
         "value": "PASS"
       }
     ]
   }
   ```

2. Click the upstream step (the one that feeds into this gate) and open the **Step Drawer**.

3. Check the step's `result_json`. Does it contain a `status` field? Is it equal to `"PASS"`?

4. If the path is nested (e.g., `"data.status"`), confirm the output has that structure.

**Fix:**

Update the gate's condition to match the upstream step's actual output:

```
PATCH /api/workflows/{workflow_id}
{
  "definition": {
    ...
    "steps": [
      ...
      {
        "step_id": "2",
        "node_type": "IF_GATE",
        "config": {
          "conditions": [
            {
              "path": "actual_field_name",
              "operator": "equals",
              "value": "expected_value"
            }
          ]
        }
      }
    ]
  }
}
```

Test the updated workflow by triggering it manually.

## Recovery Procedures

### Restarting a failed workflow

A workflow run failed and you want to re-execute it.

**Current approach:**

Manually trigger a new run via:

```
POST /api/workflow-runs
{
  "workflow_id": "workflow-123",
  "parameters": { ... }
}
```

Or via the dashboard: **Workflows → select workflow → Trigger Run button**

**Planned (Phase 151+):**

Future versions will support "rerun from failure point" — restarting from the first failed step rather than from the beginning.

### Clearing stuck steps

If a workflow run is stuck with ASSIGNED or RUNNING steps that won't progress, cancel the entire run:

```
DELETE /api/workflows/{workflow_id}/runs/{run_id}
```

This:
- Aborts all `ASSIGNED` and `RUNNING` steps
- Marks all `PENDING` steps as `CANCELLED`
- Sets the workflow status to `CANCELLED`

Once cancelled, you can trigger a fresh run via **Trigger Run** button.

### Resetting a webhook secret

Webhook secrets are revealed only once during creation. If the secret is lost, delete and recreate the webhook:

```
DELETE /api/workflows/{workflow_id}/webhooks/{webhook_id}
POST /api/workflows/{workflow_id}/webhooks
```

The new webhook will have a different `webhook_id` and `secret`. Update your external system to use the new secret.

## Monitoring Best Practices

**Real-time monitoring:**

Use the dashboard **Workflows** view for real-time updates:
- Workflows list shows all defined workflows with cron schedule (if any).
- Click a workflow to see its recent run history.
- Click a run to open **WorkflowRunDetail** with live DAG status overlay.

**WebSocket events:**

For programmatic monitoring, subscribe to WebSocket events:

```
WebSocket /ws?token={jwt}
```

Listen for events:
- `workflow_run_updated` — fired when a run's overall status changes
- `workflow_step_updated` — fired when a step completes

**Polling:**

For systems without WebSocket support, poll the API:

```
GET /api/workflows/{workflow_id}/runs?limit=20
```

Poll every 10–30 seconds to check for new runs or status updates.

**Alerting:**

Set up alerts on:
- Workflows with status `FAILED` (requires investigation)
- Workflows with status `RUNNING` > 1 hour old (potential hang)
- Cron-scheduled workflows not running at expected times (scheduler issue)

## See Also

- [Workflows API Reference](../api-reference/index.md#workflows)
- [Workflow Concepts](../workflows/concepts.md)
- [Workflow User Guide](../workflows/user-guide.md)
