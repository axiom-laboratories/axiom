# Workflow Concepts

Learn the fundamental building blocks of workflows: steps, edges, and gates that compose directed acyclic graphs (DAGs).

## Data Model

A Workflow is a directed acyclic graph (DAG) of Steps connected by Edges. Each Step is either a SCRIPT (executes a ScheduledJob) or a GATE (controls flow based on conditions or topology).

**Example workflow:** Extract Data → [IF quality_check=PASS: Transform | IF quality_check=FAIL: Rollback] → Load

Each step has inputs (from upstream edges), execution logic, and outputs (result.json for gates to branch on). For the full seven-table entity relationship diagram (Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter, WorkflowWebhook, WorkflowRun, WorkflowStepRun), see [Developer Guide](developer-guide.md).

## Step Node Types

Steps are the action nodes of a workflow. They execute ScheduledJobs and produce structured output.

### SCRIPT

Executes a ScheduledJob. The most common step type. When any upstream dependency completes, the job is dispatched to an available node.

**When to use:** Any time you need to run a job — data extraction, transformation, cleanup, API call, validation, or any other automated task.

**Example:** Extract data from a source database, validate its structure, load it into a data warehouse.

## Gate Node Types

Gates control flow within the workflow DAG. They route, merge, fan-out, or pause execution based on conditions or topology.

### IF_GATE

Routes execution to one of two branches based on conditions evaluated from the previous step's output (`result.json`).

**When to use:** When you need to branch on a condition — success/failure detection, validation results, threshold checks, feature flags, or error recovery.

**Example:** If the quality check passes, transform the data; otherwise, send an alert and roll back.

**Monitoring note:** In the DAG, you'll see either the left branch OR the right branch execute (not both). The non-taken branch appears crossed-out/CANCELLED.

### AND_JOIN

Merges multiple incoming branches. Waits for ALL upstream branches to complete before proceeding.

**When to use:** When you have parallel branches that all must succeed before proceeding — synchronization points, aggregation, final validation, or dependent steps.

**Example:** Multiple validation steps run in parallel; only proceed to the final step after all validations pass.

### OR_GATE

Merges multiple incoming branches. Releases as soon as ANY upstream branch completes (others are cancelled).

**When to use:** When you need the first-to-complete semantics — failover logic, trying multiple approaches, or choosing the fastest alternative.

**Example:** Try primary API endpoint; if it times out, use backup endpoint. Whichever responds first proceeds.

### PARALLEL

Fans out to multiple independent branches. All execute concurrently without waiting for each other.

**When to use:** When you have independent tasks that can run in parallel — distributed processing, batch operations, or multiple side-effects.

**Example:** Fetch data from three sources in parallel, then merge results in a downstream step.

### SIGNAL_WAIT

Pauses execution until an external signal is posted via the Signal mechanism (HTTP endpoint).

**When to use:** When you need to pause for external input, manual approval, webhook callback, or inter-process synchronization.

**Example:** Run validation, pause for manual approval, then proceed to deployment if approved.

## Execution Lifecycle

Workflows transition through a series of statuses as they execute:

- **RUNNING** — At least one step is pending, assigned, or running. The workflow is in progress.
- **COMPLETED** — All steps succeeded. No failures occurred; all branches completed normally.
- **PARTIAL** — Some branches failed, but failures were isolated by gates. Downstream steps continued successfully. Example: an IF gate's failure branch ran but didn't block the success branch.
- **FAILED** — Critical failure. One or more steps failed in a way that blocks downstream execution. Downstream steps are cancelled.
- **CANCELLED** — User explicitly cancelled the run via the dashboard or API.

The key distinction: **PARTIAL** workflows fail gracefully (gates isolated the failure), while **FAILED** workflows indicate a blocking error that prevented full completion.

See [Operator Guide](operator-guide.md) for detailed state transitions and edge cases.

## DAG Constraints

Workflows must satisfy these constraints:

- **No cycles** — Workflows are acyclic. The system detects cycles at save time and rejects invalid DAGs.
- **Maximum depth** — Up to 30 levels of nesting (deeper than typical job pipelines, which max at 10).
- **Validation** — All constraints are checked when you save or update a workflow definition.

## Related Concepts

- **Steps vs. Jobs** — Each SCRIPT step wraps a ScheduledJob. The job defines what runs; the step defines where in the DAG it fits.
- **Parameter Injection** — Workflows accept input parameters at trigger time, which are injected into steps via environment variables.
- **Webhook Triggers** — Workflows can be triggered externally via HMAC-signed webhook endpoints.
- **Cron Scheduling** — Workflows can run on schedules defined by cron expressions.
