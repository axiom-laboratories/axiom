# Phase 127: Cgroup Dashboard & Monitoring - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Dashboard shows cgroup version badge per node in Nodes.tsx and operator warnings for degraded cgroup support. Admin.tsx gets a fleet-wide cgroup compatibility summary. This phase consumes `detected_cgroup_version` from NodeResponse (added in Phase 123) — no backend changes needed.

</domain>

<decisions>
## Implementation Decisions

### Badge placement & style
- Cgroup version badge appears inline with other system metadata (env_tag, capabilities) in the node row — consistent with existing badge placement pattern
- Color scheme: green (v2), amber (v1), red (unsupported), muted gray (null/unknown)
- Uses existing Tailwind color classes: `bg-emerald-500/10 text-emerald-500`, `bg-amber-500/10 text-amber-500`, `bg-red-500/10 text-red-500`, muted-foreground for null
- Badge shows raw version text: `v2`, `v1`, `unsupported`, `unknown` — concise, matches env_tag badge style
- Null (never reported) shows muted `unknown` badge — makes the gap visible to operators

### Warning presentation
- Both v1 and unsupported trigger operator warnings — any non-v2 is degraded
- Fleet-level summary banner at top of Nodes page when degraded nodes exist: "2 of 5 nodes have degraded cgroup support" with breakdown by version
- Banner is NOT dismissible — persists until underlying issue is resolved
- Banner hidden when all online nodes are v2 — no news is good news
- Per-node badges remain regardless of banner presence

### Cgroup detail depth
- Tooltip on badge hover — lightweight, no extra click needed
- Tooltip content per variant:
  - v2: "Cgroup v2 — Full resource isolation. Memory and CPU limits fully enforced."
  - v1: "Cgroup v1 (Degraded) — Memory limits supported. CPU enforcement may be limited. Upgrade to v2 recommended."
  - unsupported: "No cgroup support detected. Resource limits cannot be enforced. Jobs run without isolation."
  - unknown: "Cgroup status not reported. Node may be running an older version."
- No raw cgroup_raw debug data in tooltip — keep it clean and operator-focused

### Fleet summary in Admin
- Summary card titled "Cgroup Compatibility" in a new "System Health" tab/section in Admin.tsx
- Card shows: color-coded stacked bar + count per version with percentages
- Simple CSS stacked bar (div with percentage widths and background colors) — no recharts dependency for this
- Only counts online nodes — offline/revoked nodes excluded from fleet health picture
- Card uses same green/amber/red color scheme as node badges for consistency

### Claude's Discretion
- Tooltip implementation approach (native title vs custom tooltip component)
- Exact banner component design and icon choice
- Admin "System Health" tab placement relative to existing tabs
- CSS bar animation or transition effects
- How to fetch node data in Admin (reuse existing nodes query or separate endpoint)

</decisions>

<specifics>
## Specific Ideas

- Banner format example: "⚠ 2 of 5 nodes have degraded cgroup support • 1 node running cgroup v1 (limited enforcement) • 1 node with unsupported cgroups (no enforcement)"
- Admin card preview shows stacked bar with colored segments proportional to node counts per version
- Tooltip text is prescriptive — each variant has exact wording decided above

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Badge` component (`@/components/ui/badge`): already imported and used extensively in Nodes.tsx
- Amber warning patterns: Nodes.tsx uses `bg-amber-500/10 text-amber-500 border-amber-500/20` for drift/revoked/draining badges
- `Card` component: used in Admin.tsx for configuration sections
- `Tabs` component: used in Admin.tsx and Templates.tsx for tabbed layouts
- `authenticatedFetch()`: standard API call pattern for fetching node data

### Established Patterns
- Badge color classes follow `bg-{color}-500/10 text-{color}-500 border-{color}-500/20` convention
- Node metadata badges (env_tag, capabilities) appear inline in the node row header area
- Admin.tsx uses Card+Tabs layout for configuration sections
- No tooltip component exists yet — would be new addition (or native title attribute)

### Integration Points
- `Nodes.tsx` node row rendering: add cgroup badge next to env_tag badge
- `Nodes.tsx` top of page: add degraded-nodes warning banner (conditional)
- `Admin.tsx`: add "System Health" tab with cgroup compatibility card
- `NodeResponse.detected_cgroup_version` (Optional[str]) — already exposed by backend API
- GET `/nodes` endpoint returns `detected_cgroup_version` per node — no new endpoints needed

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 127-cgroup-dashboard-monitoring*
*Context gathered: 2026-04-10*
