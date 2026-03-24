# Jobs

The Jobs view is the primary interface for dispatching scripts to nodes and monitoring execution in real time.

---

## Task Types

All jobs use the unified `script` task type with a `runtime` selector. The three supported runtimes are `python`, `bash`, and `powershell`.

Example job payload:

```json
{
  "task_type": "script",
  "runtime": "python",
  "script": "print('hello')",
  "target_node_id": "node-abc123"
}
```

!!! warning "Old task types are rejected"
    The task type values `python_script`, `bash_script`, and `powershell_script` were removed in v12.0. Jobs submitted with these types are rejected by the API with a 422 validation error. Use `task_type: "script"` with a `runtime` field instead.

---

## Dispatching a Job

### Guided Form

The guided form is the default dispatch interface. It walks through job configuration in structured steps:

1. **Runtime** — select Python, Bash, or PowerShell
2. **Script** — paste or type your script content
3. **Target** — choose a specific node, env tag, or capability requirements
4. **Signature** — select a signing key (required for script execution)

Click **Dispatch** to submit. The job appears immediately in the queue below.

### Advanced Mode

Click **[ADV]** to switch to the raw JSON dispatch form. This exposes every field in the job payload, including `memory_limit`, `cpu_limit`, and `retry_after`. Advanced mode is intended for power users and CI/CD pipelines. Click **[ADV]** again to return to the guided form.

---

## Bulk Operations

Select multiple jobs using the checkboxes in the job list to enable bulk actions:

| Action | Description |
|--------|-------------|
| **Cancel** | Cancels all selected pending jobs |
| **Resubmit** | Creates new jobs identical to each selected job |
| **Delete** | Permanently removes selected jobs from the queue |

Bulk actions apply only to jobs in compatible states — for example, bulk cancel only affects `PENDING` or `QUEUED` jobs.

---

## Queue Monitor

The Queue Monitor shows all pending and active jobs in real time via WebSocket updates. It displays per-node job counts and highlights nodes that are receiving work.

Click any node card in the Queue Monitor to open the node detail drawer, which shows current health metrics and a history of recently executed jobs.

!!! note "DRAINING nodes"
    A node in `DRAINING` state does not receive new job assignments. It continues to complete already-assigned jobs. See [Nodes](nodes.md) for how to set and clear the DRAINING state.

---

## DRAFT Lifecycle

Jobs dispatched via `axiom-push` start in `DRAFT` state and must be reviewed and published before nodes receive them. See [axiom-push CLI](axiom-push.md) and [Job Scheduling](job-scheduling.md) for DRAFT workflow details.

Jobs dispatched directly (via the dashboard or API) start in `QUEUED` state and are assigned to a node immediately.
