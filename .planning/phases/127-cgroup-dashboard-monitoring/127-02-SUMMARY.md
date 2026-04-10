---
phase: 127
plan: 02
subsystem: cgroup-dashboard-monitoring
tags: [frontend, react, dashboard, cgroup, monitoring]
duration: 2 min
completed_date: 2026-04-10
status: complete
task_count: 2
test_count: 8
files_modified:
  - puppeteer/dashboard/src/views/Admin.tsx
  - puppeteer/dashboard/src/views/__tests__/Admin.test.tsx
commits:
  - e8d263f: test(127-02) - add failing tests for cgroup fleet summary calculations
  - c58e499: feat(127-02) - implement System Health tab with cgroup fleet summary
---

# Phase 127 Plan 02: Admin System Health Tab — SUMMARY

**Objective:** Implement the System Health tab in Admin.tsx with a cgroup compatibility stacked-bar visualization showing fleet-wide cgroup version breakdown.

**One-liner:** System Health tab displays a fleet-wide cgroup version breakdown (v2, v1, unsupported, unknown) via stacked-bar visualization with count/percentage legend.

## Completed Tasks

### Task 1: Unit Tests for Cgroup Fleet Summary Calculations (RED→GREEN)

**Status:** COMPLETE ✓

Created `src/views/__tests__/Admin.test.tsx` with 8 unit test cases covering:

1. **Mixed cgroup versions:** getCgroupSegmentCounts() returns correct counts for {v2: 3, v1: 1, unsupported: 1, unknown: 0}
2. **Offline node filtering:** Excludes offline nodes (5 online + 2 offline = only counts 5)
3. **Revoked node filtering:** Excludes revoked nodes from counts
4. **Null/undefined handling:** Counts null/undefined detected_cgroup_version as 'unknown'
5. **All unknown edge case:** {v2: 0, v1: 0, unsupported: 0, unknown: 5} when all nodes have null
6. **Percentage calculation:** calculateSegmentPercentages({v2: 3, v1: 1, unsupported: 1, unknown: 0}, 5) = {v2: 60, v1: 20, unsupported: 20, unknown: 0}
7. **Single node edge case:** {v2: 1, others: 0} → {v2: 100, others: 0}
8. **Zero nodes edge case:** Handles gracefully without division by zero

**Test Framework:** Vitest (existing)
**Test Status:** 8/8 passing (GREEN)

### Task 2: Implement System Health Tab and Cgroup Compatibility Card (GREEN)

**Status:** COMPLETE ✓

#### Helper Functions Exported

Added two helper functions to `Admin.tsx` (lines 111-173):

```typescript
export const getCgroupSegmentCounts(nodes: NodeForCgroup[]): CgroupSegmentCounts
- Filters to ONLINE nodes only
- Counts by detected_cgroup_version (v2, v1, unsupported, unknown)
- Returns {v2: number, v1: number, unsupported: number, unknown: number}

export const calculateSegmentPercentages(counts: CgroupSegmentCounts, total: number): CgroupSegmentPercentages
- Converts counts to percentages (0-100)
- Handles zero total gracefully (returns all zeros)
- Returns {v2: %, v1: %, unsupported: %, unknown: %}
```

#### System Health Tab Integration

1. **Tab Trigger:** Added "System Health" trigger to TabsList (line ~1844)
   - Peer tab with "Licence", "Data", "Mirrors"
   - Uses consistent button styling: `px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold`

2. **Tab Content:** Implemented System Health TabsContent (lines 1980-2065)
   - Card layout: CardHeader + CardTitle + CardDescription + CardContent
   - Title: "Cgroup Compatibility"
   - Subtitle: "Fleet-wide cgroup version support across online nodes"

3. **Stacked-Bar Visualization:**
   - Horizontal flex container with percentage-based widths
   - 4 color-coded segments (emerald v2, amber v1, red unsupported, gray unknown)
   - Segment heights: 8px (`h-8`)
   - Segment labels: text-[10px], font-bold, color-matched, truncated if needed
   - Segment widths: `(count / total) * 100%`

4. **Legend Grid:**
   - 4-column grid layout below stacked bar
   - Each column shows: version name (bold, color-matched) + count + percentage
   - Example: `v2  3 (60%)`

5. **Edge Case Handling:**
   - **No online nodes:** Shows "No online nodes" message
   - **Empty bar:** Only renders segments with count > 0
   - **Single segment:** Bar fills 100% width
   - **Mixed versions:** All segments render proportionally

#### Nodes Data Fetching

Added to Admin component (lines 1618-1631):
```typescript
const { data: nodes = [] } = useQuery({
    queryKey: ['nodes'],
    queryFn: async () => {
        const res = await authenticatedFetch('/nodes');
        if (!res.ok) throw new Error('Failed to fetch nodes');
        const data = await res.json();
        // Handle both paginated and bare array responses
        return Array.isArray(data) ? data : (data.items || []);
    },
});
```

## Verification

### Unit Tests: 8/8 PASS

```
✓ Test 1: getCgroupSegmentCounts returns correct counts for mixed cgroup versions
✓ Test 2: getCgroupSegmentCounts excludes offline nodes from counts
✓ Test 3: getCgroupSegmentCounts excludes revoked nodes from counts
✓ Test 4: getCgroupSegmentCounts counts null/undefined as unknown
✓ Test 5: All null versions → {v2: 0, v1: 0, unsupported: 0, unknown: 5}
✓ Test 6: calculateSegmentPercentages converts counts to percentages correctly
✓ Test 7: Single online node → {v2: 100, others: 0}
✓ Test 8: Zero online nodes handled gracefully
```

### Linting: PASS

No TypeScript errors, no eslint warnings.

### Code Quality

- **Files modified:** 2
  - `puppeteer/dashboard/src/views/Admin.tsx` (178 lines added)
  - `puppeteer/dashboard/src/views/__tests__/Admin.test.tsx` (215 lines added)
- **Commits:** 2
  - e8d263f: Test framework setup (RED state)
  - c58e499: Implementation + exported helpers (GREEN state)

## Design Decisions

### Color Scheme (from CONTEXT.md)
- **v2:** `bg-emerald-500/10 text-emerald-500` — green, fully supported
- **v1:** `bg-amber-500/10 text-amber-500` — amber, degraded
- **unsupported:** `bg-red-500/10 text-red-500` — red, no enforcement
- **unknown:** `bg-muted text-muted-foreground` — gray, not reported

### Online-Only Counting
- Filters to `status === 'ONLINE'` before counting
- Excludes OFFLINE, REVOKED, TAMPERED, DRAINING, BUSY nodes
- Ensures fleet health summary reflects actual operational capacity

### No Charting Library
- Used CSS divs with percentage widths instead of recharts
- Simpler, lighter dependency footprint
- Sufficient for static, read-only visualization

### Data Format
- Reuses existing `/nodes` endpoint (NodeResponse from Phase 123)
- `detected_cgroup_version?: Optional[str]` field already populated by backend
- No new API endpoints needed

## Success Criteria

All success criteria from plan met:

- ✅ Unit tests in Admin.test.tsx all PASS (8/8 tests green)
- ✅ System Health tab visible in Admin.tsx (peer with other tabs)
- ✅ Cgroup Compatibility card renders in System Health tab
- ✅ Stacked-bar visualization shows all 4 segments (v2, v1, unsupported, unknown)
- ✅ Segment widths proportional to node counts (percentages calculated correctly)
- ✅ Segment colors match CONTEXT.md spec (emerald v2, amber v1, red unsupported, gray unknown)
- ✅ Legend shows count + percentage for each version
- ✅ Only online nodes counted in fleet summary
- ✅ Card displays "No online nodes" message gracefully when no nodes present
- ✅ No TypeScript build errors, lint passes
- ✅ REQUIREMENTS CGRP-04 (operator warning on degradation) fully satisfied (combined with Plan 01 Nodes.tsx banner)

## Integration Points

### Dependency on Phase 127 Plan 01

Plan 01 implemented:
- `detected_cgroup_version` field in Node interface
- `getCgroupBadgeClass()`, `getCgroupTooltip()`, `getCgroupDisplayText()` helpers
- Cgroup badges in node rows (Nodes.tsx)
- Degradation warning banner on Nodes page

Plan 02 (this) reuses:
- Node interface (with detected_cgroup_version)
- Backend `/nodes` endpoint (populates detected_cgroup_version)
- Similar color scheme and UX patterns

### No Backend Changes Required

- Phase 123 already exposes `detected_cgroup_version` in NodeResponse
- Reuses existing `/nodes` endpoint
- No new database columns, migrations, or API routes needed

## Deviations from Plan

None — plan executed exactly as written. No auto-fixes or architectural changes required.

## Next Steps

Phase 127 complete. Both plans delivered:
- Plan 01: Cgroup badges + degradation banner (complete)
- Plan 02: System Health tab (complete)

Operator now has:
1. Per-node cgroup version badges (with tooltips)
2. Fleet-level degradation warning banner
3. Fleet-wide cgroup compatibility summary in Admin panel

Ready for Phase 128 (Concurrent Isolation Verification).

---

**Execution Time:** 2 minutes
**Completed:** 2026-04-10 15:39 UTC
**Executor:** Claude Sonnet 4.6
