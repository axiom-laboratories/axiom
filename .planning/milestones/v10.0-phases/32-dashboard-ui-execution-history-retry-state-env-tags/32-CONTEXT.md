# Phase 32: Dashboard UI — Execution History, Retry State, Env Tags - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Pure frontend work: add execution history to the JobDefinitions view, extend the ExecutionLogModal with retry attempt navigation and attestation display, and add environment tag badges + filter to the Nodes view. No backend changes — depends on Phase 29 (output capture), Phase 30 (attestation_verified), and Phase 31 (env_tag on NodeResponse) being complete first.

</domain>

<decisions>
## Implementation Decisions

### History panel placement
- Execution history lives in the **JobDefinitions view**, not the Jobs view — clicking a definition expands a history section below the definitions table (master-detail split: top = definitions list, bottom = history for selected definition)
- Clicking a run row in the history section opens the existing **ExecutionLogModal** (reuse, not new component)
- The standalone **History.tsx page also gets a job definition selector** — a filter/dropdown to drill down to a specific definition from the global history page

### Retry attempt grouping in history list
- History list shows **one row per job_run_id** (grouped, not flat per-attempt)
- "Attempt N of M" badge appears **only when relevant** — when max_retries > 1 and the run has > 1 attempt. Single-attempt completions show no badge
- Badge colours: **amber** for RETRYING (in-progress retries), **red** for FAILED after exhausting retries (e.g. "Failed 3/3")

### ExecutionLogModal extensions
- **Extend the existing ExecutionLogModal** — do not build a new component
- When a run has multiple attempts: **tabs across the top** of the modal for switching between attempts (e.g. "Attempt 1 | Attempt 2 | Attempt 3 (final)")
- **Attestation status in the modal header** alongside the status badge: "Execution #123  COMPLETED  ✔ VERIFIED" — visible without scrolling
- **stdout/stderr displayed interleaved** with [OUT] / [ERR] stream labels — preserves execution sequence
- **Colour coding**: stderr lines in red/amber text, stdout lines normal white; exit code shown in the header as green (exit 0) or red (non-zero exit)

### Env tag display in Nodes view
- **Colour-coded badge near the hostname** on each node card: DEV = blue, TEST = amber, PROD = red/rose, custom = zinc
- Nodes with **no env_tag set show no badge** — not "UNTAGGED", just absent
- **Dropdown above the node cards**: "Filter by environment: [All ▾]"
- Filter options are **dynamically derived** from the unique env_tags present in the current node list — handles custom tags automatically; "All" always appears

### Claude's Discretion
- Exact pixel layout of the master-detail split in JobDefinitions (proportion, divider style)
- Whether the "selected definition" row in the table is highlighted or just tracked in state
- Pagination or scroll approach for the history section (likely match History.tsx's existing 25-item limit)
- Exact wording for empty history state ("No runs yet for this definition")
- Attestation badge icon choice (shield, check circle, etc.) — consistent with existing attestation UI patterns

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ExecutionLogModal.tsx`: existing interleaved terminal renderer — extend with attempt tabs, attestation header, colour-coded exit status
- `History.tsx`: standalone execution history page with `/api/executions` query — add job definition selector dropdown to it
- `JobDefinitions.tsx` + `JobDefinitionList.tsx` + `JobDefinitionModal.tsx`: existing definitions management — add history panel below definitions table in `JobDefinitions.tsx`
- `Jobs.tsx`: already imports and uses `ExecutionLogModal` — no changes needed here
- `Nodes.tsx`: card-based layout, recharts sparklines, existing node search input — add env_tag badge to Node interface and node card, add env filter dropdown above cards
- `Badge` component: already used throughout with `success`/`destructive`/`warning`/`outline` variants
- `Sheet` component: already used in `Jobs.tsx` for detail panel — can inform drawer patterns if needed
- `@tanstack/react-query`: used in History.tsx and Nodes.tsx — use same pattern for execution history queries

### Established Patterns
- Status badges: `getStatusVariant()` helper pattern exists in both `Jobs.tsx` and `History.tsx` — follow the same mapping approach for attestation badges
- Node filter: existing `useState` text filter in Nodes.tsx — env dropdown follows the same pattern
- History pagination: History.tsx uses `page * limit` offset pattern — reuse in definition history panel
- `authenticatedFetch` for all API calls — no exceptions

### Integration Points
- `GET /jobs/definitions/{id}/executions` or `GET /api/executions?job_definition_id=X` — execution history for a definition (need to confirm API shape from Phase 29 output)
- `GET /api/executions` with optional `job_definition_id` filter — for History.tsx selector
- `ExecutionRecord` interface in `ExecutionLogModal.tsx`: will gain `attestation_verified`, `attempt_number`, `job_run_id` fields from Phase 29/30 — extend the interface
- `Node` interface in `Nodes.tsx`: gains `env_tag?: string` from Phase 31 — extend the interface

</code_context>

<specifics>
## Specific Ideas

- The master-detail in JobDefinitions mirrors the pattern used in other admin tools — top table stays visible, bottom section shows context for whatever row is selected
- "Attempt N of M" tabs in the modal should label the final attempt as "(final)" or show it as the default selected tab
- The attestation badge colours should be consistent with Phase 30's implementation if it already introduced any badge styling — check before adding new variants

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 32-dashboard-ui-execution-history-retry-state-env-tags*
*Context gathered: 2026-03-18*
