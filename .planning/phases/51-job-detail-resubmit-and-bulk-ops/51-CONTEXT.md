# Phase 51: Job Detail, Resubmit and Bulk Ops - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich the existing job detail drawer with inline execution output and resubmit actions. Add one-click resubmit (new GUID, same payload) and edit-then-resubmit (pre-populate GuidedDispatchCard) for retries-exhausted FAILED jobs. Add multi-select checkboxes and a floating bulk action bar for cancel / resubmit / delete operations across multiple jobs.

</domain>

<decisions>
## Implementation Decisions

### Detail drawer content (JOB-04)
- **stdout/stderr inline in the drawer** — no separate modal. The existing "View Output" button that opens `ExecutionLogModal` is removed from the drawer; output is embedded directly. `ExecutionLogModal` may be retained for the History view.
- **Content hierarchy**: Output section first (that's what operators check on failure), then metadata (status/node/timing), then payload in a collapsible section at the bottom.
- **Node health snapshot**: show CPU/RAM from `NodeStats` at the time of execution — not current node health. Gives post-mortem context ("node was at 95% CPU when it failed").
- **SECURITY_REJECTED reason**: one-liner actionable format — e.g. "Script signature did not match registered key — re-sign and resubmit." Surfaced as an amber callout in the drawer when `security_rejected: true`.

### Resubmit UX (JOB-05 + JOB-06)
- **Two distinct buttons** in the drawer, shown only when job is FAILED with retries exhausted:
  - **"Resubmit"** — one-click, same payload/signature, new GUID
  - **"Edit & Resubmit"** — opens GuidedDispatchCard pre-populated
- **One-click resubmit confirmation**: inline in the drawer — button transforms to "Confirm resubmit? [Cancel] [Confirm]". No modal.
- **After one-click resubmit**: close drawer, scroll the new job into view in the list with a brief highlight ring.
- **Originating GUID traceability**: stored on the new job; surfaced in the new job's detail drawer only ("Resubmitted from: [original GUID]"). Not shown as a badge in the job list.

### Edit-then-resubmit mechanics (JOB-06)
- **Location**: close the detail drawer, scroll to the GuidedDispatchCard at the top of the Jobs view, pre-populate it with the failed job's values.
- **Fields carried over**: name, runtime, script content, targeting (node + target tags + capability chips). Signature fields are blank with an amber inline warning "Re-signing required — script payload has changed or job was resubmitted."
- **After successful dispatch**: form resets to blank guided mode (same as a normal dispatch). Toast: "Job resubmitted — [new GUID]".

### Bulk selection UI (BULK-01–04)
- **Checkboxes**: always visible as the first column in the job table. Clicking any checkbox immediately activates selection mode.
- **Select-all**: checkbox in the table header selects all currently loaded jobs (respects current filter state).
- **Floating action bar**: appears at the **top of the table, replacing the filter bar** when selection mode is active. Shows "[N] selected" count + applicable bulk action buttons + "Clear selection" × button to exit selection mode.
- **Context-sensitive actions** — only valid actions are shown (not greyed, fully hidden if not applicable):
  - **Cancel**: shown if ≥1 selected job is PENDING or RUNNING
  - **Resubmit**: shown if ≥1 selected job is FAILED with retries exhausted
  - **Delete**: shown if ≥1 selected job is in terminal state (COMPLETED/FAILED/CANCELLED)
- **Confirmation dialog**: count + skipped count — e.g. "Cancel 3 jobs? (2 PENDING, 1 RUNNING — 4 selected jobs are already terminal and will be skipped)". Standard Radix Dialog.

### Claude's Discretion
- Exact inline confirmation animation when the Resubmit button transforms (fade, replace, etc.)
- Whether the highlight ring on the newly resubmitted job in the list uses a CSS transition or a brief timeout
- Exact layout of the node health snapshot section (table vs grid vs prose)
- Select-all behaviour for partially-loaded lists (cursor pagination): select visible rows only or offer "select all matching" (like Gmail) — Claude decides based on implementation complexity

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `JobDetailPanel` (Jobs.tsx lines ~133–343): existing right-side Sheet drawer — extend this component with inline output, node health, and resubmit buttons. Currently has cancel + retry + "View Output" buttons.
- `ExecutionLogModal` (`src/components/ExecutionLogModal.tsx`): fetches execution records by `job_guid`; renders stdout/stderr with stream colouring. Extract the output rendering logic for reuse inline in the drawer.
- `GuidedDispatchCard` (`src/components/GuidedDispatchCard.tsx`): Phase 50 component. Add a `initialValues` prop (or similar) to accept pre-populated field values from a failed job.
- `NodeStats` table: CPU/RAM stored per heartbeat. Backend already returns `stats_history` on `GET /nodes` — a targeted query for stats near `job.started_at` will give the execution-time snapshot.
- Radix Dialog: already used for ADV mode confirmation in GuidedDispatchCard — reuse for bulk action confirmations.
- Amber inline warning pattern: used in Phase 48 DRAFT warning and Phase 50 stale-signature warning — reuse for "Re-signing required" in pre-populated form.

### Established Patterns
- Sheet (right-side drawer): established pattern for detail panels (JobDetailPanel, MoreFiltersSheet)
- Inline confirm pattern: button → "Confirm? [Cancel] [Confirm]" — used in Foundry view for destructive actions
- Toast notifications: `sonner` toast used throughout (Jobs.tsx uses `toast.error`)
- Cursor pagination "load more": established in Phase 49 — select-all operates on currently loaded rows
- Filter bar replacing with action bar: similar to how MoreFiltersSheet controls appear when active

### Integration Points
- `JobDetailPanel` in `Jobs.tsx`: add `onResubmit` and `onEditResubmit` callbacks alongside existing `onCancel` / `onRetry` / `onViewOutput`
- `GuidedDispatchCard`: add `initialValues` prop; parent (`Jobs.tsx`) sets this when "Edit & Resubmit" fires; scroll to card after setting
- Backend: `POST /jobs/{guid}/resubmit` new endpoint — creates new job with same payload/signature, sets `originating_guid` on new job
- `JobResponse` / `JobCreate` models: add `originating_guid` (nullable) field
- `GET /nodes/{node_id}/stats?at={timestamp}`: may need a new backend endpoint or query-by-time param to fetch historical NodeStats near execution time
- Checkbox column: add to the jobs table in `Jobs.tsx`; floating bulk bar replaces filter bar when `selectedJobs.size > 0`

</code_context>

<specifics>
## Specific Ideas

- The floating action bar replaces the filter bar (not a separate floating overlay) — this keeps the layout stable and avoids z-index layering on top of the dispatch card or open drawers
- Resubmit buttons only appear for FAILED + retries-exhausted — not for FAILED jobs that still have retries remaining (those use the existing retry mechanism)
- "Edit & Resubmit" pre-populates all fields except signature — operator should never be able to dispatch a resubmitted job with a stale signature; the amber warning enforces this without blocking the form

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 51-job-detail-resubmit-and-bulk-ops*
*Context gathered: 2026-03-23*
