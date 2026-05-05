---
created: 2026-04-11T12:00:00.000Z
title: Review DAG/Workflow design doc and create milestone
area: api
files:
  - puppeteer/agent_service/services/job_service.py
  - puppeteer/agent_service/services/scheduler_service.py
  - puppeteer/agent_service/db.py
  - puppeteer/agent_service/main.py
  - puppeteer/dashboard/src/views/JobDefinitions.tsx
---

## Source Documents

- `~/Development/mop_validation/docs/DAG design process.md` — primary design doc
- `~/Development/mop_validation/docs/DAG design process - antigravity adversarial review.md` — adversarial review (exists)
- `~/Development/mop_validation/docs/DAG design process gemini cli adversarial review.md` — adversarial review (exists)

Read both adversarial reviews alongside the main design doc before accepting any architectural
decision as settled. Adversarial reviews surface load-bearing assumptions, edge cases, and
failure modes that the primary doc glosses over. Treat any concerns raised as additional open
decisions requiring resolution before the milestone is created.

## Summary of What's Designed

A workflow orchestration layer built on top of the **existing** job dependency engine. Key insight:
the existing `depends_on`, `BLOCKED`/`COMPLETED`/`FAILED` status model, cascade cancellation, and
`ScheduledJob` as a script library are all retained and reused. The workflow engine is a second
trigger mechanism alongside cron — not a replacement.

### What exists today (no build needed)
- `depends_on` with `COMPLETED`, `FAILED`, `ANY` condition types
- Signal-based dependencies (`dep_type: "signal"`)
- `_cancel_dependents` cascade BFS on terminal failure
- `_unblock_dependents` transitive unblocking on completion
- `ScheduledJob` as the script reference layer (already a script library)
- `trigger_service.py` instantiation pattern (`ScheduledJob` → `Job`)
- STDOUT/STDERR/exit code attestation on every job completion

### Build phases (from the doc)

```
Phase 1a — WorkflowRun entity          Phase 1b — {{ }} param substitution
(WorkflowRun + WorkflowRunStep tables)  (single-pass, no external deps)
            │                                       │
            └──────────────┬────────────────────────┘
                           │
                  Phase 2 — Workflow template
                  (workflow table, steps JSONB, trigger_config,
                   params_schema, schedule ownership)
                           │
                  Phase 3a — Read-only DAG visualiser
                  (Dagre layout, status colours, job detail drawer)
                           │
                  Phase 3b — Authoring canvas
                  (drag-and-drop, edge drawing, condition editor)
```

Phase 1a and 1b can be executed in parallel.

### New DB tables required
- `workflow_run` — one record per trigger of a Workflow
- `workflow_run_step` — links each step in a run to its instantiated Job
- `workflow` — template: steps JSONB, params_schema, trigger_config

### Key design decisions already made
- `ScheduledJob` IS the script library — no new `TEMPLATE` job status needed
- Workflow owns its own schedule — not attached to a starter ScheduledJob
- Signatures carry forward from `ScheduledJob` to instantiated `Job` — no new signing logic
- `{{ }}` param substitution is purpose-built — no Jinja2, no external template engine
- Signature covers the raw template text, not the rendered version — params are data, not code
- WorkflowRun status: `RUNNING`, `COMPLETED`, `PARTIAL`, `FAILED`, `CANCELLED`
- `PARTIAL` ≠ failure — it means failures were anticipated and handled by FAILED-condition branches
- DAG visualiser uses [Dagre](https://github.com/dagrejs/dagre) for layout
- Nested parallel groups: limit to one level in first release
- ScheduledJob mutability: warning on edit (names specific affected workflows), not immutability

## Open Decisions — Must Resolve Before Build

These combine the original §10 open decisions with issues raised by both adversarial reviews.
Decisions marked **BLOCKING** must be resolved before the relevant phase begins.

---

### 1. [BLOCKING — Phase 1b] Parameter passing mechanism

**The primary design doc's `{{ }}` substitution approach cannot be built as designed.**

Both adversarial reviews independently identified the same fatal flaw: nodes verify the Ed25519
signature against the exact script content they receive. If the orchestrator renders
`{{ target_date }}` → `"2026-04-11"` before dispatch, the signature covers the template text but
the node receives rendered text — 100% of parameterised workflow jobs are `SECURITY_REJECTED`.

Additionally (Gemini review): string substitution into script content is a code injection vector.
A malicious param value from a webhook or user trigger can break out of string literals and
execute arbitrary code on the node. The env var approach fixes both problems simultaneously.

**Decision: Phase 1b must be redesigned as env var injection:**
- `ScheduledJob` script content is never mutated — signature always valid
- Workflow params are passed as a JSON dict in `job.payload` under a `workflow_params` key
- The node maps `workflow_params` to env vars (`AXIOM_PARAM_TARGET_DATE="2026-04-11"`) before execution
- Scripts read params from env at runtime — no orchestrator-side rendering
- This is less build work than the `{{ }}` engine, not more

**Decision:** _[ pending sign-off ]_

---

### 2. [BLOCKING — Phase 3+] Structured output convention (blocks IF gate build)

Option A (last line of STDOUT as JSON) is rejected by both adversarial reviews as too brittle.
Third-party libraries routinely emit warnings, deprecation notices, or debug output to STDOUT on
exit. Any such output after the "final" JSON line breaks the parser and crashes IF gate routing —
silently and intermittently.

**Mandate Option B from the start:**
- Node result schema includes a dedicated `structured_output` field
- Scripts write structured output to a designated file (e.g. `/tmp/axiom/result.json`) which the
  node captures and returns as `result.structured_output`
- Clean contract, not affected by logging frameworks or library output
- Move this to Phase 1 as a foundational requirement — it is needed before IF gates, not after

**Decision:** _[ pending sign-off ]_

---

### 3. [BLOCKING — Phase 1b] Depth limit for workflow-instantiated jobs

The existing 10-level dependency depth cap is a DoS protection for raw job submission. It is too
shallow for real workflow use: a straight ETL pipeline (Extract → Decrypt → Validate → Cleanse →
Format → Enrich → Aggregate → Push → Audit → Notify) already hits 10. Adding an IF gate or
manual approval step immediately exceeds it.

Pick ONE:
- **Option A:** Workflow-instantiated jobs bypass the depth cap (trusted `WorkflowRun` flag)
- **Option B:** Workflow engine performs cycle detection + depth validation at *authoring time*
  and compiles a flat job list with a system flag that bypasses the runtime cap

**Doc recommendation from Antigravity review:** Option B is cleaner — catch depth violations at
save time, not mid-run.

**Decision:** _[ pending sign-off ]_

---

### 4. [BLOCKING — Phase 2] Cancellation teardown behaviour

The design defines `CANCELLED` as a WorkflowRun state reachable by manual action at any time,
but never defines what happens to jobs that are already `ASSIGNED` or `RUNNING` when cancellation
is triggered.

Define explicitly:
- All `PENDING` and `BLOCKED` jobs in the run → marked `CANCELLED`, BFS runner drops them ✓
- Jobs currently `ASSIGNED` or `RUNNING` → does the orchestrator actively signal the worker node
  to abort, or does it let them run to completion and ignore the result?

**Decision:** _[ pending sign-off ]_

---

### 5. [BLOCKING — Phase 2] ScheduledJob mutability enforcement

The primary doc's "warning on edit" approach is pragmatic but the adversarial reviews differ on
how strong the enforcement should be:

- **Antigravity:** Auto-disable the old cron schedule when "Save as New" occurs, rather than
  prompting. Leaving it active risks ghost executions of the buggy script in the background.
- **Gemini:** Go further — implement immutable job versioning. Workflows reference a specific
  `version_id` or `content_hash`. Edits create a new version; workflows require an explicit
  "upgrade" action to adopt it. Prevents silent regressions in regulated BPO environments.

Pick ONE:
- **Option A (primary doc):** Warning on edit, "Save as New" with prompt to disable old schedule
- **Option B (Antigravity):** Warning on edit, auto-disable old cron on "Save as New"
- **Option C (Gemini):** Immutable versioning — workflows pin to a `version_id`, edits create
  new versions, upgrade is explicit

**Decision:** _[ pending sign-off ]_

---

### 6. [Phase 2] DAG integrity validation at save time

Gemini review raises: cycle detection should run at the API layer when a Workflow is saved, not
at execution time. A workflow definition containing A → B → A should be rejected immediately,
not left to fail mid-run. Also: concurrency limits per WorkflowRun to prevent large parallel
fan-outs from triggering a thundering herd of high-memory jobs simultaneously.

Required additions to the Workflow save/validation path:
- BFS/DFS cycle detection — reject cyclic definitions at the API layer
- Max step count per workflow (e.g. 50 steps) — reject oversized definitions
- Max concurrent jobs per WorkflowRun — configurable, prevent thundering herd

**Decision:** _[ pending sign-off — determine limits ]_

---

### 7. [Phase 3+] Unmatched IF gate behaviour

Pick ONE:
- **Option A:** Treat as `FAILED` — cascade cancellation applies to all downstream steps
- **Option B:** Enter `WARNING` state — alert fires, run pauses, operator manually chooses branch

**Recommendation (both reviews + primary doc):** Option B. An unmatched gate is an authoring
error. Cascade-cancelling downstream steps the operator did not intend to cancel is worse than
pausing for intervention.

**Decision:** _[ pending sign-off ]_

---

### 8. Webhook trigger scoping

`webhook` is listed as a supported `trigger_config.type` but explicitly out of scope for the
current build plan. Confirm: does webhook land in Phase 2 (with the Workflow template entity)
or as a follow-on milestone?

**Decision:** _[ pending sign-off ]_

## Engineering Review Checklist

Before creating the milestone, verify these against current codebase state:

- [ ] Confirm `depends_on` field exists on `Job` model with all three condition types
- [ ] Confirm `_cancel_dependents` BFS cascade is in `job_service.py`
- [ ] Confirm `_unblock_dependents` is in `job_service.py`
- [ ] Confirm max dependency depth (10) is enforced at dispatch time
- [ ] Confirm `trigger_service.py` instantiation pattern is intact and reusable
- [ ] Confirm `ScheduledJob` has `signature_id`, `signature_payload`, `capability_requirements`
- [ ] Confirm `scheduler_service.py` can be extended with a second query target (Workflow cron)
- [ ] Confirm Dagre is acceptable as a frontend dependency (check with frontend team)
- [ ] Confirm `gen_random_uuid()` is available in the Postgres version in use (needed for new tables)

## Milestone Deliverable

Create a new milestone in `.planning/roadmap/` covering the full 8-sprint implementation sequence
from the design doc. Suggested structure:

**Milestone: v22.0 — Workflow & DAG Orchestration**

| Phase | Sprints | Deliverable |
|-------|---------|-------------|
| 1a | 1 | WorkflowRun + WorkflowRunStep tables, status rollup, API endpoints |
| 1b | 2 | `{{ }}` parameter substitution engine + schema validation |
| 2 | 3–4 | Workflow template entity, trigger engine, cron schedule support, unified schedule view |
| 3a | 5–6 | Read-only DAG visualiser, ScheduledJob edit warning |
| 3b | 7–8 | IF gate + AND/OR gates, authoring canvas |

Resolve the three open decisions in §10 before the milestone is created and before any phase
begins that depends on them.
