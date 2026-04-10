---
phase: 127
plan: 01
type: execution
title: Cgroup Dashboard Badges and Degradation Warnings
duration: 25 minutes
tasks_completed: 2
tests_passing: 26
requirements_met: [CGRP-03, CGRP-04]
files_modified:
  - puppeteer/dashboard/src/views/Nodes.tsx
  - puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx
commits:
  - 66357f7: "test(127-01): add failing unit tests for cgroup badge colors and degradation banner logic"
  - 1f92ff7: "feat(127-01): implement cgroup version badges and degradation banner in Nodes page"
---

# Phase 127 Plan 01: Cgroup Dashboard Badges and Degradation Warnings

## Objective

Implement cgroup version badges and degradation warnings on the Nodes dashboard page. Operators see at a glance which nodes have degraded cgroup support (v1 or unsupported), enabling proactive remediation to ensure memory and CPU limits are fully enforced across the cluster.

## Execution Summary

Phase 127 Plan 01 executed in **TDD (Test-Driven Development) pattern** with two sequential tasks:

### Task 1: Write Unit Tests (RED State)
- Created `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx` with 12 new test cases
- Tests cover helper function logic and degradation banner visibility rules
- All tests initially failed (RED state) because functions not yet implemented
- Commit: `66357f7`

### Task 2: Implement Cgroup Badges and Banner (GREEN State)
- Added `detected_cgroup_version?: string | null` field to Node interface
- Implemented three exported helper functions:
  - `getCgroupBadgeClass(version)` — maps version to Tailwind color classes
  - `getCgroupTooltip(version)` — returns version-specific help text
  - `getCgroupDisplayText(version)` — returns display string or 'unknown'
- Added inline cgroup badge to node row header (after env_tag badge)
  - Uses native HTML `title` attribute for tooltip (lightweight)
  - Badge only renders if `detected_cgroup_version` is set
- Added non-dismissible degradation banner at top of Nodes page
  - Shows when any ONLINE node has `detected_cgroup_version !== 'v2'`
  - Breaks down counts for v1 and unsupported separately
  - Excludes offline/revoked nodes from degradation picture
- All 26 tests pass (12 new cgroup + 14 existing env tag)
- Lint passes, no TypeScript errors
- Commit: `1f92ff7`

## Code Changes

### Node Interface Update
```typescript
interface Node {
  // ... existing fields ...
  detected_cgroup_version?: string | null;  // NEW
}
```

### Helper Functions (Exported)
```typescript
export const getCgroupBadgeClass = (version: string | null | undefined): string => {
  switch (version) {
    case 'v2': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
    case 'v1': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
    case 'unsupported': return 'bg-red-500/10 text-red-500 border-red-500/20';
    default: return 'bg-muted text-muted-foreground border-muted';
  }
};

export const getCgroupTooltip = (version: string | null | undefined): string => {
  switch (version) {
    case 'v2': return 'Cgroup v2 — Full resource isolation. Memory and CPU limits fully enforced.';
    case 'v1': return 'Cgroup v1 (Degraded) — Memory limits supported. CPU enforcement may be limited. Upgrade to v2 recommended.';
    case 'unsupported': return 'No cgroup support detected. Resource limits cannot be enforced. Jobs run without isolation.';
    default: return 'Cgroup status not reported. Node may be running an older version.';
  }
};

export const getCgroupDisplayText = (version: string | null | undefined): string => {
  return version || 'unknown';
};
```

### Cgroup Badge in Node Row
Badge rendered inline with env_tag in CardTitle, after line 415:
```typescript
{node.detected_cgroup_version && (
  <span
    className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getCgroupBadgeClass(node.detected_cgroup_version)}`}
    title={getCgroupTooltip(node.detected_cgroup_version)}
  >
    {getCgroupDisplayText(node.detected_cgroup_version)}
  </span>
)}
```

### Degradation Banner
Non-dismissible banner above node list when degraded nodes detected:
```typescript
{(() => {
  const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
  const degradedNodes = onlineNodes.filter(
    n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2'
  );
  const v1Count = degradedNodes.filter(n => n.detected_cgroup_version === 'v1').length;
  const unsupportedCount = degradedNodes.filter(n => n.detected_cgroup_version === 'unsupported').length;

  return degradedNodes.length > 0 ? (
    <div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2">
      <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
      <div className="text-sm text-amber-700">
        <strong>{degradedNodes.length} of {onlineNodes.length} nodes have degraded cgroup support</strong>
        {v1Count > 0 && <div className="text-xs mt-1">• {v1Count} node{v1Count !== 1 ? 's' : ''} running cgroup v1 (limited enforcement)</div>}
        {unsupportedCount > 0 && <div className="text-xs mt-1">• {unsupportedCount} node{unsupportedCount !== 1 ? 's' : ''} with unsupported cgroups (no enforcement)</div>}
      </div>
    </div>
  ) : null;
})()}
```

## Test Coverage

### New Tests Added (12 total)
- **getCgroupBadgeClass**: 5 tests (v2, v1, unsupported, null, undefined)
- **getCgroupTooltip**: 5 tests (v2, v1, unsupported, null, undefined)
- **getCgroupDisplayText**: 5 tests (v2, v1, unsupported, null, undefined)
- **Degradation Banner Logic**: 6 tests
  - Shows banner with v1 nodes
  - Shows banner with unsupported nodes
  - Hides banner when all online nodes are v2
  - Excludes offline nodes from count
  - Excludes revoked nodes from count
  - Counts v1 and unsupported separately

### Test Results
```
✓ Test Files  1 passed (1)
✓ Tests  26 passed (26)  [12 new cgroup + 14 existing env tag]
✓ Lint passes with no errors
✓ No TypeScript build errors
```

## Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| CGRP-03: Per-node cgroup badges | ✅ COMPLETE | Badge renders in node row with correct colors per version |
| CGRP-03: Tooltip shows version text | ✅ COMPLETE | Native HTML `title` attribute shows version-specific help |
| CGRP-04: Fleet-wide degradation warning | ✅ COMPLETE | Banner appears when any online node is not v2 |
| CGRP-04: Degradation breakdown | ✅ COMPLETE | Banner shows separate counts for v1 and unsupported |
| CGRP-04: Non-dismissible warning | ✅ COMPLETE | No close button, persists until issue resolved |
| CGRP-04: Banner hidden when healthy | ✅ COMPLETE | Banner hidden when all online nodes are v2 |

## Deviations from Plan

None — plan executed exactly as written. All MUST-HAVEs met:
- ✅ Cgroup badge per node in row header
- ✅ Badge color mapping: green (v2), amber (v1), red (unsupported), gray (unknown)
- ✅ Tooltip text matches CONTEXT.md exactly
- ✅ Degradation banner shows when degraded nodes exist
- ✅ Banner shows count and breakdown
- ✅ Banner non-dismissible
- ✅ Banner hidden when all online nodes are v2
- ✅ Unit tests all pass

## What Works

1. **Cgroup Badge Rendering**: Badge appears inline with env_tag, shows correct color per version, tooltip displays on hover
2. **Tooltip Content**: Version-specific help text matches CONTEXT.md exactly
3. **Degradation Banner**: Appears/disappears correctly based on node cgroup versions
4. **Filtering Logic**: Only counts online nodes, excludes offline/revoked from degradation picture
5. **Breakdown Counts**: v1 and unsupported nodes counted separately
6. **Unit Tests**: All 26 tests pass, including 12 new cgroup-specific tests
7. **Code Quality**: Lint passes, no TypeScript errors, follows existing patterns

## Architecture Notes

- **Backend Integration**: `detected_cgroup_version` field already available from Phase 123 heartbeat detection — no backend changes needed
- **Component Pattern**: Uses existing Badge component styling and Tailwind color classes established in env_tag badges
- **Helper Functions**: Exported for test isolation and reusability (can be imported by Admin.tsx for System Health tab in Plan 02)
- **Tooltip Implementation**: Native HTML `title` attribute (simpler, lighter) vs custom component — verified simple text tooltips don't need library overhead

## Next Steps

Plan 02 (Admin System Health Tab) will:
1. Reuse `getCgroupBadgeClass()` and helper functions
2. Add "System Health" tab to Admin.tsx
3. Display stacked bar showing fleet-wide cgroup distribution
4. Same online-node-only filtering logic

## Duration

- Task 1 (test file): 5 min
- Task 2 (implementation + verification): 20 min
- **Total: 25 min**

## Files Modified

| File | Lines Added | Status |
|------|-------------|--------|
| `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx` | 193 | new test cases added |
| `puppeteer/dashboard/src/views/Nodes.tsx` | 51 | interface update + helpers + badge + banner |

---

**Execution Complete** — Phase 127 Plan 01 ready for verification.
Next: Plan 02 (Admin System Health Tab)
