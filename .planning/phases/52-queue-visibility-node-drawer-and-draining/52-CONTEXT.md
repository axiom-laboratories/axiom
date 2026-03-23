# Phase 52: Queue Visibility, Node Drawer and DRAINING - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Operators can diagnose why a PENDING job is stuck, see the full live queue in one dedicated view, inspect per-node state in a detail drawer, and safely drain a node without forcefully terminating jobs. No new job capabilities or dispatch mechanics — this is an operational visibility and control improvement.

</domain>

<decisions>
## Implementation Decisions

### Queue view (VIS-02)
- **New /queue route** with its own sidebar nav entry (positioned after Jobs in the nav)
- **Read-only monitoring layout** — no GuidedDispatchCard, focused on queue state
- Shows **PENDING + ASSIGNED + RUNNING + recently terminal jobs** (COMPLETED/FAILED/CANCELLED)
- **Adjustable recency window** for terminal jobs: dropdown with 1h / 6h / 24h options
- PENDING jobs in the queue show a diagnosis callout inline (see VIS-01 below)
- DRAINING node status visible as a badge on affected jobs
- Live updates via WebSocket (same `useWebSocket` hook already in Jobs.tsx and Nodes.tsx)

### PENDING diagnosis (VIS-01)
- **Location**: callout section at the top of the existing job detail drawer (Phase 51's enhanced `JobDetailPanel`) when job is PENDING
- **Backend endpoint**: `GET /jobs/{guid}/dispatch-diagnosis` — backend computes with full node state + queue position; frontend just displays the result
- **Diagnosis cases surfaced**:
  - No nodes currently ONLINE
  - Capability mismatch — nodes are online but none match the job's required capabilities (show which capability is missing)
  - All eligible nodes busy — capable nodes exist but all are at concurrency limit; show queue position ("Queue position: 3")
  - Target node offline or DRAINING — job targets a specific node that is unavailable
- **Live refresh**: diagnosis updates via WebSocket when node state changes (node comes online, running job completes, etc.). No polling.

### Node detail drawer (VIS-03)
- **Trigger**: click anywhere on a node row in the Nodes view (consistent with Jobs.tsx's job row click pattern)
- **Sheet drawer** (right-side), following established Phase 51 / Jobs.tsx pattern
- **Contents**:
  - Currently running job (link to job detail)
  - Jobs eligible for this node — all PENDING jobs that match this node's capabilities + targeting (full eligibility check, not just explicit target_node_id)
  - Recent execution history — all jobs that ran on this node in the past 24 hours
  - Node's reported capabilities displayed as chip/badge list (reuses existing chip pattern)
  - Drain / Un-drain action button (admin only — see DRAINING section)

### DRAINING mechanics (VIS-04)
- **Who can drain**: admin only (`nodes:write` permission, admin bypass)
- **Enforcement**: `job_service.py` node selection loop skips DRAINING nodes — same filter that skips OFFLINE/REVOKED nodes. Clean, no new dispatch mechanism.
- **Auto-transition**: when the last running job on a DRAINING node completes, the node automatically transitions to OFFLINE
- **Un-drain**: admin can return a DRAINING node to ONLINE via an Un-drain action in the same node detail drawer (Drain button becomes Un-drain when node is DRAINING)
- **Backend endpoints needed**: `PATCH /nodes/{id}/drain` and `PATCH /nodes/{id}/undrain`
- **Visibility**: DRAINING status shows as a badge in both the Nodes view and Queue view

### Claude's Discretion
- Exact wording of diagnosis messages (plain English — e.g. "No nodes online" vs "All nodes offline")
- Queue view column layout and density (similar to Jobs.tsx table or a more compact monitoring layout)
- Whether the `dispatch-diagnosis` endpoint is polled once on drawer open and then patched via WebSocket, or fetched fresh on each WebSocket event
- Exact animation/transition when the Drain button transforms to Un-drain
- Whether the node drawer's "eligible jobs" list links back to the Queue view or opens the job detail drawer inline

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `JobDetailPanel` (Jobs.tsx ~line 155): existing right-side Sheet drawer — add PENDING diagnosis callout section at the top when `job.status === 'PENDING'`
- `useWebSocket` hook (`src/hooks/useWebSocket.ts`): already wired in both Jobs.tsx and Nodes.tsx — reuse the same subscription pattern for live diagnosis refresh and queue updates
- Chip/badge pattern: established in Phase 49 filter chips and Phase 51 capability chips — reuse for node capabilities display in the drawer
- Radix `Sheet` component: already used for `JobDetailPanel` and `MoreFiltersSheet` in Jobs.tsx — use the same for the node detail drawer in Nodes.tsx
- Amber callout pattern: used in Phase 48 DRAFT warning and Phase 51 SECURITY_REJECTED callout — reuse for PENDING diagnosis callout
- Node status rendering: Nodes.tsx already handles ONLINE/OFFLINE/BUSY/REVOKED/TAMPERED — add DRAINING to the same status dot/icon logic

### Established Patterns
- Sheet (right-side drawer): `JobDetailPanel` in Jobs.tsx — exact same pattern for node drawer in Nodes.tsx
- Row-click to open drawer: Jobs.tsx job row click pattern — replicate in Nodes.tsx
- WebSocket live patch: Jobs.tsx uses `useWebSocket` to patch job list in-place — same pattern for queue view updates
- Status filtering in `job_service.py`: node selection already filters by status — add `DRAINING` to the exclusion list

### Integration Points
- `job_service.py` node selection loop: add `DRAINING` to the excluded statuses (alongside OFFLINE/REVOKED)
- `Node` DB model (`db.py` line ~108): `status` column currently holds ONLINE/OFFLINE/TAMPERED — add DRAINING as a valid value
- `AppRoutes.tsx`: add `/queue` route pointing to new `Queue.tsx` view
- Main sidebar nav: add Queue nav item after Jobs
- `Nodes.tsx`: add Sheet drawer state + click handler on node rows; add drain/undrain action buttons (admin-only gated)
- `GET /nodes` response: DRAINING status already flows through if DB value is set — verify `NodeResponse` doesn't restrict status values
- New backend endpoint: `GET /jobs/{guid}/dispatch-diagnosis` — queries node table, job requirements, queue position

</code_context>

<specifics>
## Specific Ideas

- The Queue view is intentionally read-only — operators who need to dispatch go to the Jobs view. This keeps the Queue view focused on "what's happening" rather than "what to do next."
- The adjustable time window for terminal jobs in the Queue view (1h/6h/24h) lets operators tune the signal-to-noise ratio during incident response vs normal monitoring
- "All eligible nodes busy — queue position 3" is the most actionable diagnosis — it tells the operator the job WILL run, just needs to wait, so they don't cancel it unnecessarily
- Auto-transition DRAINING → OFFLINE (when last job completes) means the node exits the fleet cleanly without an extra admin action; the admin still controls re-entry via Un-drain

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 52-queue-visibility-node-drawer-and-draining*
*Context gathered: 2026-03-23*
