# Phase 127: Cgroup Dashboard & Monitoring - Research

**Researched:** 2026-04-10
**Domain:** React Dashboard UI patterns, Cgroup monitoring & visualization
**Confidence:** HIGH

## Summary

Phase 127 is a pure frontend/UI phase with zero backend API changes required. The `detected_cgroup_version` field is already exposed in `NodeResponse` (confirmed in Phase 123). Dashboard work involves:

1. **Nodes.tsx**: Add cgroup version badge inline with env_tag in node row header, add fleet-level degradation warning banner
2. **Admin.tsx**: Add "System Health" tab with cgroup compatibility stacked-bar visualization
3. **Badge system**: Use existing Badge component + inline color classes (emerald/amber/red/gray) to match env_tag pattern

No backend routes needed. No database changes. Purely UI implementation on top of existing node data. All design decisions locked via CONTEXT.md discussion.

**Primary recommendation:** Follow the badge and color system established in Nodes.tsx for env_tag (pattern: `bg-{color}-500/10 text-{color}-500 border-{color}-500/20`). Use `detected_cgroup_version` from existing `NodeResponse` payload without adding any new API endpoints.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Badge placement & style**: Inline with system metadata (env_tag, capabilities) in node row
- **Color scheme**: green (v2), amber (v1), red (unsupported), gray (null/unknown) using Tailwind classes
- **Badge text**: Raw version text only (`v2`, `v1`, `unsupported`, `unknown`)
- **Warning threshold**: Both v1 and unsupported trigger degraded warnings
- **Fleet summary**: Banner at top of Nodes page + card in Admin.tsx "System Health" tab
- **Banner dismissibility**: NOT dismissible — persists until issue resolved
- **Tooltip content**: Provided verbatim in CONTEXT.md for each variant
- **Admin visualization**: Color-coded stacked bar + count/percentage per version
- **Fleet scope**: Online nodes only (excludes offline/revoked)

### Claude's Discretion
- Tooltip implementation (native `title` attribute vs custom component)
- Exact banner component design and icon choice
- Admin "System Health" tab placement in tab list
- CSS bar animation or transition effects
- Node data fetch strategy in Admin (reuse nodes query or separate endpoint)

### Deferred Ideas
None — all scope is in-phase.

## Standard Stack

### Core UI Libraries
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | ^18.x | Component framework | Existing dashboard stack |
| TypeScript | ^5.0 | Type safety | Standard in puppeteer/dashboard |
| Tailwind CSS | ^3.x | Styling (colors, layout) | Existing utility classes, color system |
| Radix UI (via shadcn) | Latest | Accessible Badge, Tabs, Card components | Established pattern in codebase |
| recharts | ^2.x | Optional (for future metrics) | Used in Nodes.tsx for sparklines; NOT needed for stacked bar |

### Component Library
| Component | File | Purpose | Already Exists |
|-----------|------|---------|-----------------|
| Badge | `@/components/ui/badge` | Status badges | ✅ Yes |
| Card | `@/components/ui/card` | Container card | ✅ Yes |
| Tabs | `@/components/ui/tabs` | Tab navigation | ✅ Yes |
| Button | `@/components/ui/button` | Interactive buttons | ✅ Yes |
| Tooltip (optional) | `@/components/ui/tooltip` | Hover tooltips | May exist, check |

### Styling Approach
All color classes follow **existing Nodes.tsx pattern**:
- Health status: `bg-emerald-500/10 text-emerald-500 border-emerald-500/20`
- Warning status: `bg-amber-500/10 text-amber-500 border-amber-500/20`
- Error status: `bg-red-500/10 text-red-500 border-red-500/20`
- Muted/unknown: `bg-muted text-muted-foreground border-muted`

This approach is consistent across Nodes.tsx (env_tag, drift warnings, capability status) and Admin.tsx (status badges).

**Installation:**
No new packages needed. All required components and styles already in project.

## Architecture Patterns

### Recommended Project Structure

Frontend changes confined to two files:

```
puppeteer/dashboard/src/views/
├── Nodes.tsx          # Add cgroup badge + degradation banner
└── Admin.tsx          # Add System Health tab with stacked-bar chart
```

No new files needed. Changes are additive to existing views.

### Pattern 1: Badge Color Mapping (Cgroup Version)

**What:** Map cgroup version string to Badge color class + tooltip text

**When to use:** Rendering per-node cgroup status in Nodes.tsx row header

**Example:**
```typescript
const getCgroupBadgeClass = (version: string | null | undefined): string => {
  switch (version) {
    case 'v2': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
    case 'v1': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
    case 'unsupported': return 'bg-red-500/10 text-red-500 border-red-500/20';
    default: return 'bg-muted text-muted-foreground border-muted';
  }
};

const getCgroupTooltip = (version: string | null | undefined): string => {
  switch (version) {
    case 'v2': return 'Cgroup v2 — Full resource isolation. Memory and CPU limits fully enforced.';
    case 'v1': return 'Cgroup v1 (Degraded) — Memory limits supported. CPU enforcement may be limited. Upgrade to v2 recommended.';
    case 'unsupported': return 'No cgroup support detected. Resource limits cannot be enforced. Jobs run without isolation.';
    default: return 'Cgroup status not reported. Node may be running an older version.';
  }
};
```

**Source:** CONTEXT.md design decisions, Nodes.tsx existing badge patterns

### Pattern 2: Fleet Degradation Banner

**What:** Warning banner shown at top of Nodes page when any node has v1 or unsupported cgroup

**When to use:** Nodes.tsx page-level, above node list

**Placement:** After title but before pagination/search controls

**Visibility rule:**
- Show if: `any node (online only) has version !== 'v2'`
- Hide if: `all online nodes are 'v2'` or `no nodes at all`

**Banner content example:**
```
⚠ 2 of 5 nodes have degraded cgroup support • 1 node running cgroup v1 (limited enforcement) • 1 node with unsupported cgroups (no enforcement)
```

**Non-dismissible:** No close button, banner persists until issue resolved

**Source:** CONTEXT.md § "Warning presentation", Nodes.tsx existing amber-warning patterns

### Pattern 3: Admin System Health Tab — Stacked Bar

**What:** Visualization showing node count breakdown by cgroup version at fleet level

**When to use:** Admin.tsx, new "System Health" tab (adjacent to existing tabs)

**Visualization:**
- Horizontal stacked bar using CSS divs (no recharts needed)
- Segment widths: `(count / total) * 100%`
- Segment colors: match badge colors (emerald v2, amber v1, red unsupported, gray unknown/none)
- Labels: count + percentage below bar (e.g., "3 nodes • 60%")
- Only count online nodes (exclude offline/revoked)

**Example CSS:**
```tsx
<div className="flex h-8 w-full rounded-lg overflow-hidden border border-muted">
  <div className="bg-emerald-500/10" style={{ width: '60%' }}>
    <div className="text-[10px] font-bold text-emerald-500 px-2 py-1">3 nodes</div>
  </div>
  <div className="bg-amber-500/10" style={{ width: '20%' }}>
    <div className="text-[10px] font-bold text-amber-500 px-2 py-1">1 node</div>
  </div>
  <div className="bg-red-500/10" style={{ width: '20%' }}>
    <div className="text-[10px] font-bold text-red-500 px-2 py-1">1 node</div>
  </div>
</div>
```

**Data aggregation:** Loop through nodes array, count by `detected_cgroup_version`, filter online status

**Source:** CONTEXT.md § "Fleet summary in Admin", Nodes.tsx existing Card+Tabs patterns in Admin.tsx

### Anti-Patterns to Avoid

- **Using a charting library for stacked bar:** recharts overkill for single static visualization; plain CSS divs sufficient
- **Fetching node data separately in Admin:** Reuse existing `/nodes` query already used elsewhere; no separate endpoint
- **Hardcoding node version counts:** Compute counts dynamically from current response payload each render
- **Dismissible banner:** User can't close it — forces attention to actual problem
- **Including raw `cgroup_raw` field in tooltip:** Keep tooltip clean and operator-focused; debug data is for logs not UI

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Custom badge colors for status | Your own color picker / class generator | Tailwind color utilities + pre-defined function | Consistency with existing badges; colors already chosen in CONTEXT.md |
| Tooltip display | Custom tooltip library | Native HTML `title` attribute OR existing `@/components/ui/tooltip` | Simple text tooltips don't need library; native is lighter |
| Stacked bar chart | Custom SVG/Canvas visualization | CSS divs with `flex` + percentage widths | CSS layout sufficient for static bar; no animation needed |
| Node filtering (online-only) | Manual loop + conditional | Reuse node list query; filter with `.filter(n => n.status === 'ONLINE')` | Already returned by API, just filter locally |
| Responsive badge sizing | Manual media queries per badge | Existing Badge component + Tailwind responsive classes | Badge component handles defaults; only override if needed |

**Key insight:** All UI needs are in React + Tailwind + existing Radix UI components. No custom libraries or hand-rolled solutions needed. Focus on composition and conditional rendering.

## Common Pitfalls

### Pitfall 1: Forgetting to Update Node Interface

**What goes wrong:** TypeScript expects `detected_cgroup_version` on Node interface but it's missing, causing build errors when rendering badge.

**Why it happens:** Node interface defined locally in Nodes.tsx; easy to forget backend model changes propagate to frontend types.

**How to avoid:** Add `detected_cgroup_version?: string | null;` to Node interface at top of Nodes.tsx alongside other optional fields (env_tag, execution_mode)

**Warning signs:** TypeScript build errors like "Property 'detected_cgroup_version' does not exist on type 'Node'"

**Source:** Inspection of Nodes.tsx interface (line 69), NodeResponse model in agent_service/models.py confirmed field exists

### Pitfall 2: Banner Shows Even When All Nodes Are v2

**What goes wrong:** Banner appears even after upgrades complete because logic checks for `null` without filtering to online-only

**Why it happens:** Easy to include offline/revoked nodes in degradation count; includes nodes with `version = null` as degraded

**How to avoid:** Filter to `nodes.filter(n => n.status === 'ONLINE' && n.detected_cgroup_version)` before counting degraded versions

**Warning signs:** Banner persists after all online nodes are v2; count in banner doesn't match actual online node count

**Source:** CONTEXT.md § "Fleet summary in Admin" specifies "Only counts online nodes"

### Pitfall 3: Tooltip Text Truncation or Wrapping Issues

**What goes wrong:** Long tooltip text wraps awkwardly or gets clipped by browser default tooltip styling

**Why it happens:** Native `title` attribute has browser-default styling; custom component allows full control

**How to avoid:** Use custom tooltip component (check if `@/components/ui/tooltip` exists) OR constrain tooltip width with Tailwind (`max-w-xs`) if using custom render

**Warning signs:** Tooltip text overflows, renders in weird places, or disappears on hover

**Source:** CONTEXT.md notes tooltip as "Claude's Discretion" — native title OR custom component both valid

### Pitfall 4: Color Opacity Inconsistency

**What goes wrong:** Cgroup badge uses `bg-emerald-500/10` but env_tag badge uses `bg-emerald-500/20`, looking mismatched

**Why it happens:** Copy-pasting from different badge examples in codebase with different opacity levels

**How to avoid:** Use EXACT class pattern from CONTEXT.md: `bg-{color}-500/10 text-{color}-500 border-{color}-500/20` for all cgroup badges; verify matches env_tag pattern in code

**Warning signs:** Cgroup badges look visually lighter/darker than other badges; opacity values differ

**Source:** CONTEXT.md explicitly specifies color scheme, Nodes.tsx shows env_tag pattern at line 127 (`bg-amber-500/10`)

### Pitfall 5: Offline Nodes Included in Fleet Count

**What goes wrong:** Admin System Health card shows "5 nodes total" but there are 3 online + 2 offline; offline ones shouldn't be in degradation picture

**Why it happens:** Forgot to filter `n.status === 'ONLINE'` when iterating for stats

**How to avoid:** Always apply filter before aggregation: `const onlineNodes = nodes.filter(n => n.status === 'ONLINE')` then count by cgroup_version on filtered list

**Warning signs:** Node count in Admin doesn't match "currently online" count on Nodes page; includes REVOKED/OFFLINE in bar

**Source:** CONTEXT.md explicitly states "Only counts online nodes — offline/revoked nodes excluded"

## Code Examples

Verified patterns from codebase:

### Add Cgroup Version to Node Interface

```typescript
// In Nodes.tsx, update interface Node (around line 69)
interface Node {
    node_id: string;
    hostname: string;
    ip: string;
    status: 'ONLINE' | 'OFFLINE' | 'BUSY' | 'REVOKED' | 'TAMPERED' | 'DRAINING';
    last_seen: string;
    base_os_family?: string;
    stats?: NodeStats;
    version?: string;
    tags?: string[];
    capabilities?: Record<string, string>;
    expected_capabilities?: Record<string, string>;
    tamper_details?: string;
    concurrency_limit?: number;
    job_memory_limit?: string;
    stats_history?: StatPoint[];
    env_tag?: string;
    detected_cgroup_version?: string | null;  // NEW: Phase 127
}
```

**Source:** NodeResponse model in puppeteer/agent_service/models.py line 216 confirms field exists

### Cgroup Badge Color & Tooltip Functions

```typescript
// Add near top of Nodes.tsx, below existing helper functions (getEnvBadgeColor, etc.)

const getCgroupBadgeClass = (version: string | null | undefined): string => {
  switch (version) {
    case 'v2': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
    case 'v1': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
    case 'unsupported': return 'bg-red-500/10 text-red-500 border-red-500/20';
    default: return 'bg-muted text-muted-foreground border-muted';
  }
};

const getCgroupTooltip = (version: string | null | undefined): string => {
  switch (version) {
    case 'v2': return 'Cgroup v2 — Full resource isolation. Memory and CPU limits fully enforced.';
    case 'v1': return 'Cgroup v1 (Degraded) — Memory limits supported. CPU enforcement may be limited. Upgrade to v2 recommended.';
    case 'unsupported': return 'No cgroup support detected. Resource limits cannot be enforced. Jobs run without isolation.';
    default: return 'Cgroup status not reported. Node may be running an older version.';
  }
};

const getCgroupDisplayText = (version: string | null | undefined): string => {
  return version || 'unknown';
};
```

**Source:** CONTEXT.md § tooltip content, Nodes.tsx existing pattern at lines 122-144 (getEnvTagBadgeClass, getEnvBadgeColor)

### Degradation Banner Component (Nodes.tsx)

```typescript
// Add above node list in Nodes.tsx render, after title but before search/pagination
// Calculate degraded node count and create banner conditionally

const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
const degradedNodes = onlineNodes.filter(n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2');

const v1Count = degradedNodes.filter(n => n.detected_cgroup_version === 'v1').length;
const unsupportedCount = degradedNodes.filter(n => n.detected_cgroup_version === 'unsupported').length;

{degradedNodes.length > 0 && (
  <div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2">
    <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
    <div className="text-sm text-amber-700">
      <strong>{degradedNodes.length} of {onlineNodes.length} nodes have degraded cgroup support</strong>
      {v1Count > 0 && <div className="text-xs mt-1">• {v1Count} node{v1Count !== 1 ? 's' : ''} running cgroup v1 (limited enforcement)</div>}
      {unsupportedCount > 0 && <div className="text-xs mt-1">• {unsupportedCount} node{unsupportedCount !== 1 ? 's' : ''} with unsupported cgroups (no enforcement)</div>}
    </div>
  </div>
)}
```

**Source:** Nodes.tsx existing warning patterns at lines 412-419 (tamper alert), context-aware badge logic from lines 390-395

### Cgroup Badge in Node Row Header (Nodes.tsx)

```typescript
// In NodeCard component, add after env_tag badge rendering (after line 396)
// Within the CardTitle flex container alongside env_tag and status badges

{node.detected_cgroup_version && (
  <span
    className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getCgroupBadgeClass(node.detected_cgroup_version)}`}
    title={getCgroupTooltip(node.detected_cgroup_version)}
  >
    {getCgroupDisplayText(node.detected_cgroup_version)}
  </span>
)}
```

**Source:** Nodes.tsx node row header pattern at lines 392-396 (env_tag badge), Tailwind title attribute for native tooltip

### System Health Tab in Admin.tsx

```typescript
// Add to TabsTrigger list in Admin.tsx (around line 1765, adjacent to existing tabs)

<TabsTrigger value="system-health" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">
  System Health
</TabsTrigger>

// Add to TabsContent section (after other tab contents)

<TabsContent value="system-health" className="space-y-6">
  <Card>
    <CardHeader>
      <CardTitle>Cgroup Compatibility</CardTitle>
      <CardDescription>Fleet-wide cgroup version support across online nodes</CardDescription>
    </CardHeader>
    <CardContent className="space-y-4">
      {(() => {
        const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
        if (onlineNodes.length === 0) {
          return <p className="text-sm text-muted-foreground">No online nodes</p>;
        }

        const counts = {
          v2: onlineNodes.filter(n => n.detected_cgroup_version === 'v2').length,
          v1: onlineNodes.filter(n => n.detected_cgroup_version === 'v1').length,
          unsupported: onlineNodes.filter(n => n.detected_cgroup_version === 'unsupported').length,
          unknown: onlineNodes.filter(n => !n.detected_cgroup_version).length,
        };
        const total = onlineNodes.length;

        return (
          <div className="space-y-3">
            <div className="flex h-8 w-full rounded-lg overflow-hidden border border-muted">
              {counts.v2 > 0 && (
                <div
                  className="bg-emerald-500/10 flex items-center justify-center"
                  style={{ width: `${(counts.v2 / total) * 100}%` }}
                >
                  <span className="text-[10px] font-bold text-emerald-500 px-1 truncate">
                    {counts.v2} {counts.v2 === 1 ? 'node' : 'nodes'}
                  </span>
                </div>
              )}
              {counts.v1 > 0 && (
                <div
                  className="bg-amber-500/10 flex items-center justify-center"
                  style={{ width: `${(counts.v1 / total) * 100}%` }}
                >
                  <span className="text-[10px] font-bold text-amber-500 px-1 truncate">
                    {counts.v1} {counts.v1 === 1 ? 'node' : 'nodes'}
                  </span>
                </div>
              )}
              {counts.unsupported > 0 && (
                <div
                  className="bg-red-500/10 flex items-center justify-center"
                  style={{ width: `${(counts.unsupported / total) * 100}%` }}
                >
                  <span className="text-[10px] font-bold text-red-500 px-1 truncate">
                    {counts.unsupported} {counts.unsupported === 1 ? 'node' : 'nodes'}
                  </span>
                </div>
              )}
              {counts.unknown > 0 && (
                <div
                  className="bg-muted flex items-center justify-center"
                  style={{ width: `${(counts.unknown / total) * 100}%` }}
                >
                  <span className="text-[10px] font-bold text-muted-foreground px-1 truncate">
                    {counts.unknown} unknown
                  </span>
                </div>
              )}
            </div>
            <div className="grid grid-cols-4 gap-2 text-xs">
              <div>
                <span className="font-bold text-emerald-500">v2</span>
                <div className="text-muted-foreground">{counts.v2} ({Math.round((counts.v2 / total) * 100)}%)</div>
              </div>
              <div>
                <span className="font-bold text-amber-500">v1</span>
                <div className="text-muted-foreground">{counts.v1} ({Math.round((counts.v1 / total) * 100)}%)</div>
              </div>
              <div>
                <span className="font-bold text-red-500">Unsupported</span>
                <div className="text-muted-foreground">{counts.unsupported} ({Math.round((counts.unsupported / total) * 100)}%)</div>
              </div>
              <div>
                <span className="font-bold text-muted-foreground">Unknown</span>
                <div className="text-muted-foreground">{counts.unknown} ({Math.round((counts.unknown / total) * 100)}%)</div>
              </div>
            </div>
          </div>
        );
      })()}
    </CardContent>
  </Card>
</TabsContent>
```

**Source:** Admin.tsx existing Tab pattern (lines 1737-1772), Card component usage, Nodes.tsx grid pattern for metadata display

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No cgroup monitoring | Dashboard badges + fleet summary | Phase 127 (v20.0) | Operators see degraded cgroup support at a glance |
| Manual node health inspection | Warning banner + tooltips | Phase 127 | Proactive alerting — no need to click each node |
| No fleet-level health view | Admin System Health tab | Phase 127 | Cluster-wide picture in one place |
| Cgroup version never reported to UI | Phase 123 added heartbeat field | Phase 123 → Phase 127 | UI phase consumes detection from backend |

**Not deprecated:**
- Badge component remains standard across all status indicators
- Tailwind color system unchanged
- Tab-based Admin layout is established pattern

## Open Questions

1. **Tooltip implementation uncertainty**
   - What we know: CONTEXT.md lists both native `title` and custom component as acceptable
   - What's unclear: Performance impact of tooltip component vs native; accessibility requirements
   - Recommendation: Start with native `title` attribute (simpler, lighter); switch to component if UX testing shows gaps

2. **Admin tab placement preference**
   - What we know: Tabs exist in Admin.tsx with "Licence", "Data", "Mirrors" sections
   - What's unclear: Should "System Health" be a top-level tab or nested under "Data"?
   - Recommendation: Add as peer tab next to "Data" for visibility; can be reorganized later if tab list gets too long

3. **Stacked bar segment sizing with very small percentages**
   - What we know: Simple flex layout works for most cases
   - What's unclear: How to handle edge cases (1 node out of 100 = 1% width, label won't fit)
   - Recommendation: Use CSS `min-width` on segments + `truncate` on label text; accept label ellipsis for very small segments

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (existing) |
| Config file | `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `npm run test -- src/views/__tests__/Nodes.test.tsx` |
| Full suite command | `npm run test` (from puppeteer/dashboard) |

### Phase Requirements → Test Map

No explicit phase requirement IDs provided. Testing maps to CGRP-03 and CGRP-04 from REQUIREMENTS.md:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CGRP-03 | Nodes view shows cgroup v2/v1/unsupported badges per node | component | `npm run test -- Nodes.test.tsx -t "cgroup badge"` | ❌ Wave 0 |
| CGRP-03 | Tooltip shows version-specific help text on hover | component | `npm run test -- Nodes.test.tsx -t "cgroup tooltip"` | ❌ Wave 0 |
| CGRP-04 | Degradation banner appears when any online node is non-v2 | component | `npm run test -- Nodes.test.tsx -t "degradation banner"` | ❌ Wave 0 |
| CGRP-04 | Banner hidden when all online nodes are v2 | component | `npm run test -- Nodes.test.tsx -t "degradation banner hidden"` | ❌ Wave 0 |
| CGRP-04 | Admin System Health tab shows stacked bar with correct percentages | component | `npm run test -- Admin.test.tsx -t "system health bar"` | ❌ Wave 0 |
| Manual | E2E: Dashboard renders cgroup badges correctly in live Docker stack | e2e | `python ~/Development/mop_validation/scripts/test_playwright.py` | ✅ Exists |

### Sampling Rate
- **Per task commit:** `npm run test -- src/views/__tests__/Nodes.test.tsx src/views/__tests__/Admin.test.tsx -x`
- **Per wave merge:** `npm run test` (full suite from puppeteer/dashboard)
- **Phase gate:** Full suite green + E2E Playwright check of Nodes/Admin cgroup UI before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/views/__tests__/Nodes.test.tsx` — Component tests for cgroup badge rendering, tooltip, degradation banner visibility
- [ ] `src/views/__tests__/Admin.test.tsx` — Component tests for System Health tab stacked bar calculation and rendering
- [ ] Playwright snapshot test for cgroup badges in live Docker node row (optional, low priority)

*(If gaps exist: Create before implementation tasks. New test files follow existing Vitest patterns in puppeteer/dashboard.)*

## Sources

### Primary (HIGH confidence)
- NodeResponse model in `puppeteer/agent_service/models.py` line 216 — confirmed `detected_cgroup_version?: Optional[str]` field exists
- Nodes.tsx existing badge/color patterns (lines 122-144, 390-396) — established Tailwind color convention `bg-{color}-500/10`
- Admin.tsx Tabs pattern (lines 1737-1772) — Card + TabsList + TabsTrigger + TabsContent structure
- CONTEXT.md (127-CONTEXT.md) — all design decisions and color scheme locked

### Secondary (MEDIUM confidence)
- Badge component in `puppeteer/dashboard/src/components/ui/badge.tsx` — confirmed exists with variant system
- Nodes.tsx sparkline pattern (StatsSparkline, line 146+) — shows recharts optional for advanced viz; simple CSS sufficient for stacked bar
- CLAUDE.md Architecture section — confirms three-component system; no backend work needed for Phase 127

### Tertiary (LOW confidence)
- None — all critical facts verified via code inspection or CONTEXT.md

## Metadata

**Confidence breakdown:**
- **Standard Stack**: HIGH - React/TypeScript/Tailwind all confirmed in code, Badge component exists, no new deps needed
- **Architecture**: HIGH - Nodes.tsx and Admin.tsx patterns fully documented and inspected; no backend changes required
- **Pitfalls**: HIGH - Color opacity, filter for online nodes, tooltip text, badge interface update all identified from code
- **Validation**: MEDIUM - Existing Vitest infrastructure exists; specific test gaps identified for Wave 0 setup

**Research date:** 2026-04-10
**Valid until:** 2026-04-17 (7 days — stable phase, no external dependencies)

---

*Phase 127: Cgroup Dashboard & Monitoring*
*Research complete. Ready for planning.*
