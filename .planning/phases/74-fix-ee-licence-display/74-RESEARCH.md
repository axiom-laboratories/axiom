# Phase 74: Fix EE Licence Display - Research

**Researched:** 2026-03-27
**Domain:** React/TypeScript frontend — hook interface alignment, conditional rendering, date computation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fix lives in the frontend: update `useLicence.ts` to map the backend response correctly
- Adopt backend field names everywhere (`tier`, `status`, `days_until_expiry`, `node_limit`) — rename the `LicenceInfo` interface and update all callers (Admin.tsx, MainLayout.tsx)
- Expose `status` as a union string: `'valid' | 'grace' | 'expired' | 'ce'`
- Add a computed `isEnterprise: boolean` getter in the hook (true when `status !== 'ce'`) so callers don't repeat the check
- Compute an absolute date string from `days_until_expiry` (today + N days) and display as e.g. "Expires 27 Jun 2026"
- Colour-code: amber text when under 30 days remaining, red text when `status === 'expired'`
- When expired: show "Expired" (not a date) in the expiry row
- Admin licence section: show a status badge alongside tier — green "Active" (`valid`), amber "Grace Period" (`grace`), red "Expired" (`expired`), grey "Community" (`ce`)
- Sidebar EE badge: simple "EE" or "CE" by default, but colour shifts — amber when `grace`, red when `expired`
- Non-dismissible top banner when status is `grace` or `expired`, visible to all authenticated users (not admin-only)
- Remove features chip list from Admin.tsx — replace with a "Node limit" row showing the `node_limit` value
- Hide the Node limit row entirely for CE installs (`node_limit === 0` / `status === 'ce'`)

### Claude's Discretion
- Exact Tailwind classes for badge colours
- Banner copy/wording for grace vs expired states
- Whether banner has an icon (e.g. warning triangle)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIC-06 | Operator can query `GET /api/licence` and receive `status` (valid/grace/expired), `days_until_expiry`, `node_limit`, and `tier` fields in the response | Backend already returns all four fields. Frontend hook `useLicence.ts` uses wrong interface (`edition`, `expires`, `features`) — must be rewritten to map backend fields correctly. Admin.tsx and MainLayout.tsx are the two callers that need updating. |
</phase_requirements>

## Summary

The backend `/api/licence` endpoint (implemented in Phase 73) returns `{ status, tier, days_until_expiry, node_limit, customer_id, grace_days }`. The frontend `useLicence.ts` hook was written against a different imagined interface (`edition`, `expires`, `features`). This mismatch means `licence.edition === 'enterprise'` is always false against the real response — the CE fallback always wins. No fields in the current `LicenceInfo` interface match the actual backend JSON keys.

The fix is entirely in three frontend files: `useLicence.ts` (rewrite the interface and mapping), `Admin.tsx` (update `LicenceSection` component), and `MainLayout.tsx` (update sidebar EE badge, add grace/expired banner). No backend changes are needed. The backend shape is stable and fully confirmed from source.

**Primary recommendation:** Rewrite `useLicence.ts` to match backend field names exactly, move `isEnterprise` computation into the hook, then update the two callers (`Admin.tsx`, `MainLayout.tsx`) to consume the corrected interface.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.x | Component rendering | Project stack |
| TypeScript | 5.x | Type safety for interface contract | Project stack |
| @tanstack/react-query | 5.x | Data fetching + caching in `useLicence` | Already used by hook |
| Tailwind CSS | 3.x | All styling — badges, banner, colour classes | Project standard — no CSS modules |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | current | Warning triangle icon for banner | Already imported in MainLayout.tsx |

## Architecture Patterns

### Recommended Project Structure
No new files needed. All changes are in-place edits:
```
puppeteer/dashboard/src/
├── hooks/useLicence.ts          # Rewrite interface + mapping
├── views/Admin.tsx              # Update LicenceSection sub-component
└── layouts/MainLayout.tsx       # Update EE badge + add banner
```

### Pattern 1: Hook Interface Rewrite
**What:** Replace `LicenceInfo` interface fields to match backend JSON shape exactly. Computed `isEnterprise` lives in the hook return value.
**When to use:** Single source of truth — callers never re-derive the boolean.

```typescript
// Correct interface matching backend /api/licence response
export interface LicenceInfo {
  status: 'valid' | 'grace' | 'expired' | 'ce';
  tier: string;           // "ce" or "enterprise"
  days_until_expiry: number;
  node_limit: number;     // 0 = unlimited/CE
  customer_id: string | null;
  grace_days: number;
  isEnterprise: boolean;  // computed: status !== 'ce'
}

const CE_DEFAULTS: LicenceInfo = {
  status: 'ce',
  tier: 'ce',
  days_until_expiry: 0,
  node_limit: 0,
  customer_id: null,
  grace_days: 0,
  isEnterprise: false,
};
```

### Pattern 2: Date Computation from days_until_expiry
**What:** Compute absolute expiry date from `days_until_expiry` relative to today at render time.
**When to use:** Backend only provides relative integer — must reconstruct display date client-side.

```typescript
// In Admin.tsx LicenceSection or a helper
function formatExpiryDate(daysUntilExpiry: number): string {
  const expiry = new Date();
  expiry.setDate(expiry.getDate() + daysUntilExpiry);
  return expiry.toLocaleDateString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric'
  });
}
// Shows "27 Jun 2026" format (locale-dependent but readable)
```

**Important:** When `status === 'expired'`, show the string "Expired" directly instead of calling this function — the `days_until_expiry` will be negative (past), which would render a past date that is confusing.

### Pattern 3: Status Badge Colours (Tailwind)
**What:** Map `status` string to Tailwind colour classes consistently across Admin.tsx badge and sidebar badge.

```typescript
// Badge colour map — reusable
const STATUS_BADGE: Record<string, string> = {
  valid:   'bg-emerald-500/20 text-emerald-400',
  grace:   'bg-amber-500/20  text-amber-400',
  expired: 'bg-red-500/20    text-red-400',
  ce:      'bg-zinc-700/50   text-zinc-400',
};

const STATUS_LABEL: Record<string, string> = {
  valid:   'Active',
  grace:   'Grace Period',
  expired: 'Expired',
  ce:      'Community',
};
```

### Pattern 4: Non-Dismissible Top Banner in MainLayout.tsx
**What:** Full-width banner rendered above `<main>` inside the flex column, visible on every page.
**When to use:** Only when `status === 'grace'` or `status === 'expired'`.

```typescript
// In MainLayout return, before <main>
{(licence.status === 'grace' || licence.status === 'expired') && (
  <div className={`flex items-center gap-2 px-4 py-2 text-sm font-medium ${
    licence.status === 'expired'
      ? 'bg-red-900/40 text-red-300 border-b border-red-800'
      : 'bg-amber-900/40 text-amber-300 border-b border-amber-800'
  }`}>
    <AlertTriangle className="h-4 w-4 shrink-0" />
    {licence.status === 'expired'
      ? 'Your EE licence has expired. The system is running in Community Edition mode.'
      : `Your EE licence expires in ${licence.days_until_expiry} day${licence.days_until_expiry === 1 ? '' : 's'}. Please renew.`
    }
  </div>
)}
```

`AlertTriangle` is available from `lucide-react` — already imported in MainLayout.tsx via other icons.

### Pattern 5: Sidebar EE Badge Colour State
**What:** The existing badge at line 134–140 of MainLayout.tsx checks `licence.edition === 'enterprise'` — update to use `licence.isEnterprise` and layer in grace/expired colouring.

```typescript
// Replace the existing badge span
<span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
  licence.status === 'expired' ? 'bg-red-500/20 text-red-400'
  : licence.status === 'grace'  ? 'bg-amber-500/20 text-amber-400'
  : licence.isEnterprise        ? 'bg-indigo-500/20 text-indigo-400'
  :                               'bg-zinc-700/50 text-zinc-400'
}`}>
  {licence.isEnterprise ? 'EE' : 'CE'}
</span>
```

### Anti-Patterns to Avoid
- **Keeping `edition` field:** Callers checking `licence.edition === 'enterprise'` will always get `false` because the backend never returns an `edition` key. Remove it from the interface entirely.
- **Parsing backend ISO date string:** The backend does NOT return a datetime string for expiry — it only provides `days_until_expiry` as an integer. Do not try to parse a date field that does not exist.
- **Dismissible banner:** The spec calls for non-dismissible — no close button, no useState toggle for the banner.
- **Admin-only banner:** The banner must render for all authenticated users — place it in MainLayout.tsx, not Admin.tsx.
- **Showing features chip list:** Decided out — remove entirely and replace with Node limit row.
- **Node limit row for CE:** Hide when `node_limit === 0` or `status === 'ce'`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Locale-aware date formatting | Custom date format function | `Date.toLocaleDateString()` with options | Standard browser API, handles locale |
| Icon for warning | SVG inline | `AlertTriangle` from lucide-react | Already bundled in project |
| Status → colour mapping | Switch statement in JSX | Lookup object pattern (see Pattern 3) | Eliminates repetition across badge + banner |

## Common Pitfalls

### Pitfall 1: days_until_expiry Negative When Expired
**What goes wrong:** If the planner renders `formatExpiryDate(days_until_expiry)` unconditionally, expired licences show a past date string (e.g. "12 Jan 2026") rather than "Expired".
**Why it happens:** `days_until_expiry` is negative for expired licences — the backend computes `int((exp - now) / 86400)`.
**How to avoid:** Always branch on `status === 'expired'` first; only call `formatExpiryDate` when status is `valid` or `grace`.
**Warning signs:** Expiry row shows a date in the past.

### Pitfall 2: Stale Cache After Hook Rewrite
**What goes wrong:** React Query caches under key `['licence']` with the old interface shape. During development, stale cached CE_DEFAULTS from the old code may persist.
**Why it happens:** Query key is the same before and after the rewrite; react-query's 5-minute staleTime means old data may linger.
**How to avoid:** Not a production issue (new deployments have no cache). In dev, clear browser localStorage/cache or add a cache-busting query key suffix temporarily.

### Pitfall 3: `tier` vs `isEnterprise` Confusion
**What goes wrong:** Using `tier === 'enterprise'` instead of `isEnterprise` to gate EE display.
**Why it happens:** The backend returns `tier: "ce"` even in grace/expired states — tier reflects the licence tier, status reflects the runtime state.
**How to avoid:** Use `isEnterprise` (derived from `status !== 'ce'`) for all EE feature display; reserve `tier` display for the raw label in the Admin section.

### Pitfall 4: TypeScript Interface Mismatch at Import Sites
**What goes wrong:** After renaming `LicenceInfo` fields, other callers (or test mocks) still reference `licence.edition` — TypeScript compilation fails.
**Why it happens:** Two callers (Admin.tsx line 79, MainLayout.tsx lines 135, 139) directly access old field names.
**How to avoid:** TypeScript will flag these immediately — grep for `licence.edition` and `licence.expires` and `licence.features` after the hook rewrite.

## Code Examples

### useLicence.ts — Corrected Return Shape
```typescript
// Source: direct inspection of /api/licence handler in main.py (lines 772-793)
export function useLicence(): LicenceInfo {
  const { data } = useQuery<Omit<LicenceInfo, 'isEnterprise'>>({
    queryKey: ['licence'],
    queryFn: async () => {
      const res = await authenticatedFetch('/api/licence');
      if (!res.ok) return CE_DEFAULTS;
      return res.json();
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const raw = data ?? CE_DEFAULTS;
  return {
    ...raw,
    isEnterprise: raw.status !== 'ce',
  };
}
```

### Admin.tsx — LicenceSection Expiry Row
```typescript
// Branch on status before computing display date
const expiryDisplay = licence.status === 'expired'
  ? 'Expired'
  : licence.days_until_expiry > 0
    ? `Expires ${formatExpiryDate(licence.days_until_expiry)}`
    : 'Expired';

const expiryClass = licence.status === 'expired'
  ? 'text-red-400'
  : licence.days_until_expiry < 30
    ? 'text-amber-400'
    : 'text-white';
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `LicenceInfo.edition: 'community' \| 'enterprise'` | `LicenceInfo.status: 'valid' \| 'grace' \| 'expired' \| 'ce'` + `tier: string` | Phase 74 | Matches backend; enables grace/expired colour states |
| `licence.expires` (ISO string) | `days_until_expiry` (integer) computed to date | Phase 74 | Backend never returned a date string |
| Features chip list | Node limit row | Phase 74 | EE is all-or-nothing; chip list was misleading |

**Deprecated/outdated:**
- `LicenceInfo.edition`: Remove — backend has no `edition` field
- `LicenceInfo.expires`: Remove — backend has no `expires` field; use `days_until_expiry`
- `LicenceInfo.features`: Remove from interface — features chip list dropped per CONTEXT.md decisions

## Open Questions

None — the backend is fully implemented and the response shape is confirmed from source inspection. The plan can proceed directly to implementation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest + @testing-library/react |
| Config file | `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer/dashboard && npx vitest run src/hooks` |
| Full suite command | `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIC-06 | `useLicence` maps `status`/`tier`/`days_until_expiry`/`node_limit` from backend response | unit | `cd puppeteer/dashboard && npx vitest run src/hooks` | ❌ Wave 0 |
| LIC-06 | `isEnterprise` is `true` when `status` is `valid` or `grace`, `false` when `ce` | unit | `cd puppeteer/dashboard && npx vitest run src/hooks` | ❌ Wave 0 |
| LIC-06 | Admin.tsx shows "Enterprise" tier and correct expiry date for EE licence | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Admin` | ❌ Wave 0 |
| LIC-06 | Admin.tsx shows "Community" tier and hides node limit row for CE | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Admin` | ❌ Wave 0 |
| LIC-06 | MainLayout.tsx EE badge shows "EE" for enterprise, "CE" for community | unit | `cd puppeteer/dashboard && npx vitest run src/layouts` | ❌ Wave 0 |
| LIC-06 | MainLayout.tsx banner appears for `grace` and `expired` status, absent for `valid`/`ce` | unit | `cd puppeteer/dashboard && npx vitest run src/layouts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer/dashboard && npx vitest run src/hooks src/views/__tests__/Admin.test.tsx`
- **Per wave merge:** `cd puppeteer/dashboard && npm run test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/dashboard/src/hooks/__tests__/useLicence.test.ts` — covers LIC-06 hook mapping + `isEnterprise` computed field
- [ ] `puppeteer/dashboard/src/views/__tests__/Admin.test.tsx` — covers LIC-06 LicenceSection rendering for valid/grace/expired/ce states
- [ ] `puppeteer/dashboard/src/layouts/__tests__/MainLayout.test.tsx` — covers LIC-06 EE badge and grace/expired banner

## Sources

### Primary (HIGH confidence)
- Direct source read: `puppeteer/agent_service/main.py` lines 772-793 — confirmed backend response shape (`status`, `tier`, `days_until_expiry`, `node_limit`, `customer_id`, `grace_days`)
- Direct source read: `puppeteer/agent_service/services/licence_service.py` lines 51-66 — confirmed `LicenceStatus` enum values (`valid`, `grace`, `expired`, `ce`) and `LicenceState` dataclass fields
- Direct source read: `puppeteer/dashboard/src/hooks/useLicence.ts` — confirmed current mismatched interface (`edition`, `expires`, `features`)
- Direct source read: `puppeteer/dashboard/src/views/Admin.tsx` lines 77-131 — confirmed `LicenceSection` component accessing `licence.edition`, `licence.expires`, `licence.features`
- Direct source read: `puppeteer/dashboard/src/layouts/MainLayout.tsx` lines 134-140 — confirmed EE badge checking `licence.edition === 'enterprise'`

### Secondary (MEDIUM confidence)
- `puppeteer/dashboard/vitest.config.ts` — test framework and environment confirmed (jsdom, vitest globals)
- Existing test pattern from `src/views/__tests__/Jobs.test.tsx` — `vi.mock` hook pattern for `authenticatedFetch`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies needed
- Architecture: HIGH — backend response shape confirmed from source; all three files to change identified with exact line numbers
- Pitfalls: HIGH — identified from code inspection (negative days_until_expiry, old field names at two call sites)

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain — no fast-moving library concerns)
