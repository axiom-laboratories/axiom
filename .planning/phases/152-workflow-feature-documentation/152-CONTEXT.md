# Phase 152: Workflow Feature Documentation - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Developer docs (API reference, architecture, data model) and user-facing docs (how-to guides, UI walkthroughs) for all workflow features built in Phases 146–150. Covers: workflow CRUD, DAG execution engine, gate node types, triggers/parameter injection (Phase 149), and the dashboard read-only views.

**Dependency:** Phase 149 (Triggers & Parameter Injection) must be complete before finalising cron/webhook/parameter-injection sections. This phase documents the intended full design — confirm Phase 149 has landed before shipping those sections.

</domain>

<decisions>
## Implementation Decisions

### Doc structure
- Dedicated `docs/docs/workflows/` directory with sub-pages (not a single flat file)
- Sub-pages (Claude's discretion to name/split):
  - `index.md` — overview and navigation hub
  - `concepts.md` — step types, gate types, DAG model, execution lifecycle diagram
  - `user-guide.md` — dashboard monitoring: Workflows list, WorkflowDetail, WorkflowRunDetail, step log drawer
  - `operator-guide.md` — observable behaviour, status transitions, cron/webhook setup via API
  - `developer-guide.md` — internals: BFS dispatch, CAS guards, state machine, cascade cancellation, mermaid ERD
- API docs go in `docs/docs/api-reference/index.md` — workflow API becomes the first real content there
- Runbook at `docs/docs/runbooks/workflows.md` — operational runbook (same pattern as `runbooks/jobs.md`)

### API reference depth
- `api-reference/index.md` gets real content — workflow API is the inaugural full section
- Per-endpoint: method + path + one-line description + key request fields; not exhaustive schema dumps
- One annotated example JSON per endpoint group (CRUD, management, webhooks, runs), not one per endpoint
- HMAC webhook signing: describe the mechanism (what it is, where to find the secret) — no worked curl example
- Complex request bodies (e.g. create workflow with steps + edges + parameters): include a realistic annotated example JSON

### User guide scope
- Focus on the **monitoring side only** — the visual DAG editor for *creating* workflows is Phase 151 (not yet built)
- Walk through: Workflows list → WorkflowDetail (run history) → WorkflowRunDetail (live overlay + step log drawer)
- Gate types: explain each with a "when to use this" rationale section (IF_GATE, AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT)
- Trigger setup (cron scheduling, webhook config): **skip for now** — mark with a TODO callout:
  `> TODO: This section will be completed when the workflow trigger configuration UI ships (Phase 151).`
- Screenshots: include placeholder callouts for each major view (`![Workflows list screenshot]`, `![DAG canvas with status overlay]`, `![Step log drawer]`); real screenshots to be dropped in post-build

### Developer vs. operator architecture
- Two separate files: `operator-guide.md` and `developer-guide.md`
- **Operator-guide** covers observable behaviour: what triggers a run, status state machine (6 statuses), how cancellation propagates, how to monitor via API/dashboard, Phase 149 parameter injection overview
- **Developer-guide** covers internals: BFS wave dispatch algorithm, compare-and-swap concurrency guards, cascade cancellation logic, lazy import pattern (circular dep avoidance), mermaid ERD of all 7 tables
- ERD: mermaid `erDiagram` block showing all 7 workflow tables and their FK relationships
- Document **full intended design** including Phase 149 in-progress features (cron, webhook HMAC, WORKFLOW_PARAM_* injection) — verify Phase 149 landed before publishing

### Claude's Discretion
- Exact heading/section names within each file
- Whether `concepts.md` or `developer-guide.md` carries the step-type shape descriptions
- Mermaid diagram style for ERD and lifecycle state machine
- Which example workflow to use for annotated JSON (suggest: 3-step linear script → IF gate → parallel fan-out)

</decisions>

<specifics>
## Specific Ideas

- The annotated JSON example should show a realistic workflow: a 3-step sequence with an IF gate branching to parallel steps — not a trivial 2-node hello-world
- Gate type "when to use this" sections should be practical, not just restate the type name (e.g. "Use AND_JOIN when you have parallel branches that all must succeed before proceeding")
- The developer guide should note the lazy import pattern in `workflow_service.py` (circular dep with `main.py` ConnectionManager) — this is non-obvious and will trip up contributors
- Screenshots are placeholder callouts for now; note in the runbook that screenshots should be regenerated after any dashboard UI changes

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/docs/feature-guides/jobs.md`: pattern to follow for feature guide structure (intro, concepts, UI walkthrough, API section)
- `docs/docs/runbooks/jobs.md`: pattern for runbook structure (common ops, troubleshooting, examples)
- `docs/docs/api-reference/index.md`: file to extend with workflow API content

### Established Patterns
- All docs use Markdown with MkDocs rendering (check `docs/mkdocs.yml` for nav structure — new pages must be registered there)
- Feature guides don't use OpenAPI auto-generation — all API docs are hand-written prose + examples
- Existing docs use fenced code blocks for JSON/curl examples

### Integration Points
- `puppeteer/agent_service/main.py`: source of truth for all 14 workflow API endpoints and their request/response shapes
- `puppeteer/agent_service/db.py`: source of truth for all 7 workflow DB tables (workflow, workflow_steps, workflow_edges, workflow_parameters, workflow_webhooks, workflow_runs, workflow_step_runs)
- `puppeteer/agent_service/services/workflow_service.py`: BFS dispatch, CAS guards, cascade cancellation — primary source for developer guide internals
- `puppeteer/dashboard/src/views/Workflows.tsx`, `WorkflowDetail.tsx`, `WorkflowRunDetail.tsx`: UI source for user guide walkthroughs
- `puppeteer/dashboard/src/components/WorkflowStepNode.tsx`: defines the 6 step node shapes/types — source for concepts.md

</code_context>

<deferred>
## Deferred Ideas

- Workflow trigger configuration UI guide — deferred to Phase 151 (Visual DAG Editor); TODO callout left in user-guide.md
- Workflow creation walkthrough (drag-and-drop DAG editor) — deferred to Phase 151
- Full OpenAPI/Swagger auto-generation for API reference — out of scope; hand-written docs are the pattern

</deferred>

---

*Phase: 152-workflow-feature-documentation*
*Context gathered: 2026-04-16*
