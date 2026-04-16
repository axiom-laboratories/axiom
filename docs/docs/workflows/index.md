# Workflow Documentation

Workflows enable you to compose ScheduledJobs into directed acyclic graphs (DAGs) with conditional branching, parallel fan-out, and signal waits. This section documents the full lifecycle, from concepts through monitoring and operations.

## Quick Start

Workflows are JSON-defined DAGs composed of two types of nodes:

- **Steps** execute ScheduledJobs and produce output (`result.json`)
- **Gates** control flow: branching on conditions (IF_GATE), merging branches (AND_JOIN, OR_GATE), parallel fan-out (PARALLEL), or pausing for signals (SIGNAL_WAIT)

All workflows follow the workflow lifecycle: RUNNING → COMPLETED, PARTIAL, FAILED, or CANCELLED. Conditional gates isolate failures, allowing downstream steps to continue even if earlier branches fail.

For detailed step and gate types, see [Concepts](concepts.md). For dashboard monitoring examples, see [User Guide](user-guide.md).

## Pages in This Section

| Page | Description |
|------|-------------|
| [Concepts](concepts.md) | Step types, gate types, DAG model, execution lifecycle |
| [User Guide](user-guide.md) | Dashboard monitoring: viewing workflows, runs, and step logs |
| [Operator Guide](operator-guide.md) | Observable behaviour, status transitions, monitoring via API |
| [Developer Guide](developer-guide.md) | Internals: BFS dispatch, CAS guards, cascade cancellation, ERD |

## Related Topics

- **[Jobs](../feature-guides/jobs.md)** — ScheduledJobs are the unit of execution within workflow steps
- **[Scheduling](../runbooks/jobs.md)** — APScheduler integration for cron-based workflow triggers
- **[API Reference](../api-reference/index.md#workflows)** — Full REST API endpoint documentation

## Next Steps

- New to workflows? Start with [Concepts](concepts.md) to understand step and gate types
- Using the dashboard? Check [User Guide](user-guide.md) for walkthroughs of each view
- Operating workflows at scale? See [Operator Guide](operator-guide.md) for monitoring and troubleshooting
- Contributing to the workflow engine? Read [Developer Guide](developer-guide.md) for internals and concurrency patterns
