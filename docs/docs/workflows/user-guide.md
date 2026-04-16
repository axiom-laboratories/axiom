# Workflow User Guide

This guide covers monitoring and inspecting workflows via the dashboard. For information on creating workflows, see Phase 151 (Visual DAG Editor) — coming soon.

## Dashboard Monitoring

The dashboard provides three main views for monitoring workflows, arranged in a hierarchy: Workflows list → Workflow detail → Workflow run detail.

### Workflows List

Navigate to **Monitoring → Workflows** to see all workflow definitions in your system.

![Workflows list](../../assets/screenshots/workflows-list.png)

The list shows:

- **Name** — The workflow's display name
- **Steps** — Total number of steps in the DAG
- **Last Run** — Most recent run's status (color-coded badge) and timestamp
- **Next Run** — Scheduled time for the next cron-based run, if applicable

Click a row to view that workflow's detail page and run history.

### Workflow Detail

Click a workflow name to view its definition and historical run data.

![Workflow detail with run history](../../assets/screenshots/workflow-detail.png)

The Workflow Detail page includes:

- **Workflow summary** — Name, step count, creation date, last modified date
- **Run History** — A table of all past and current WorkflowRuns with columns:
  - **Trigger Type** — How the run was started (MANUAL, CRON, or WEBHOOK)
  - **Status** — Current status (RUNNING, COMPLETED, PARTIAL, FAILED, or CANCELLED) with color badges
  - **Started** — When the run began
  - **Completed** — When the run finished (or in-progress if still running)
  - **Duration** — Total time from start to finish

Click any row in the Run History to drill into the live execution detail and DAG visualization.

### Workflow Run Detail with DAG Overlay

Click a run to see the live execution status overlaid on the DAG visualization.

![WorkflowRunDetail with DAG and status overlay](../../assets/screenshots/workflow-run-detail-dag.png)

The Workflow Run Detail page displays:

- **DAG Canvas** — A visual representation of your workflow's directed acyclic graph
  - Each box is a step
  - Colors represent status:
    - Gray — PENDING (awaiting dispatch)
    - Blue — ASSIGNED or RUNNING (job is executing on a node)
    - Green — SUCCEEDED (step completed successfully)
    - Red — FAILED (step failed)
    - Crossed-out/strikethrough — CANCELLED (step was skipped)
  - Lines between boxes are edges (dependencies)

- **Real-time updates** — The DAG updates automatically as steps complete (WebSocket-driven; refresh not required)

- **Navigation** — Scroll horizontally/vertically, use zoom controls, or pan to navigate large DAGs

## Viewing Step Results & Logs

### Step Drawer

Click any step in the DAG to open the **Step Drawer** on the right side.

![Step drawer with logs](../../assets/screenshots/step-drawer.png)

The drawer shows:

- **Job output** — stdout and stderr logs from the step's job execution (read-only, streamed in real-time as the job runs)
- **result.json** — Structured output from the step, used by downstream IF gates to evaluate branching conditions
- **Execution metadata** — Start time, end time, duration, and final status of the step

All logs are read-only (no editing). If a step is still running, logs stream in real-time; completed steps show the full output.

## Status Meanings

Understanding workflow statuses helps you diagnose runs and understand completion behavior:

| Status | Meaning | Color |
|--------|---------|-------|
| RUNNING | Workflow is executing; at least one step is pending, assigned, or running | Blue |
| COMPLETED | All steps succeeded; no failures occurred | Green |
| PARTIAL | Some branches failed, but failures were isolated by gates and did not block other branches | Amber/Orange |
| FAILED | Critical failure; one or more steps failed in a way that blocks downstream execution | Red |
| CANCELLED | User cancelled the run via the dashboard or API | Gray |

### Understanding PARTIAL Status

A workflow is PARTIAL (not FAILED) when conditional gates isolate failures. For example:

1. Step A (data validation) fails
2. Step A routes to an IF gate's failure branch
3. Step B (failure handler / fallback) runs successfully on the failure branch
4. Downstream steps C and D run normally
5. Result: **PARTIAL** (not FAILED), because the IF gate contained the failure

This is a feature, not a bug: gates allow workflows to recover gracefully from expected failures.

## Understanding Gate Types in Action

When monitoring workflows, each gate type behaves distinctly in the DAG:

### IF_GATE in Action

You'll see either the left branch OR the right branch execute (not both). The non-taken branch appears crossed-out/CANCELLED in the DAG. Look for the branch condition in the step's result.json.

### AND_JOIN in Action

Multiple incoming branches merge. All must complete before the next step proceeds. Wait for all incoming edges to turn green before the merged step executes.

### OR_GATE in Action

Multiple incoming branches merge. The first one to complete triggers the next step; other incoming branches are cancelled (crossed-out). Look for which incoming branch completed first.

### PARALLEL in Action

A single incoming step fans out to multiple branches that execute concurrently. All branches will eventually reach green (unless cancelled or failed). No waiting between parallel branches.

### SIGNAL_WAIT in Action

Execution pauses at this step. The DAG shows the step in RUNNING state, but no logs are being produced. Execution resumes when an external system posts a signal via the `/api/workflows/{id}/runs/{run_id}/signal` endpoint (or via the UI when implemented).

## Triggering Workflows

Workflows can be triggered in three ways:

- **MANUAL** — Click a "Trigger Run" button on the workflow page (coming in Phase 151)
- **CRON** — Scheduled via cron expression at the time of definition (see Phase 149 for setup details)
- **WEBHOOK** — External systems POST to a webhook endpoint (see Phase 149 for setup details)

> TODO: This section will be completed when the workflow trigger configuration UI ships (Phase 151).

## Common Tasks

### Viewing a workflow's execution history

1. Navigate to **Monitoring → Workflows**
2. Click the workflow name
3. The Run History table shows all past runs with status and timestamps

### Inspecting a failed step's output

1. Open the workflow run detail (click any run from the Run History)
2. Click the red step in the DAG
3. The Step Drawer opens on the right side, showing logs and result.json

### Understanding why a workflow is PARTIAL

1. Open the workflow run detail
2. Look for crossed-out/CANCELLED steps in the DAG — these indicate gate-isolated failures
3. Click the non-cancelled step that preceded the cancelled ones to inspect its failure details and the gate's logic

### Monitoring a long-running workflow

1. Open the workflow run detail
2. The DAG updates in real-time via WebSocket
3. Refresh not required — steps change color as they progress (gray → blue → green/red)
