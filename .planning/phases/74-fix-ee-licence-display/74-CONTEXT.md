# Phase 74: Fix EE Licence Display - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Align `useLicence.ts` hook field mapping with the actual `/api/licence` backend response, then update all callers (Admin.tsx, MainLayout.tsx) so the EE badge and Admin licence section render correctly. No backend changes — this is a frontend fix only.

</domain>

<decisions>
## Implementation Decisions

### Fix location
- Fix lives in the frontend: update `useLicence.ts` to map the backend response correctly
- Adopt backend field names everywhere (`tier`, `status`, `days_until_expiry`, `node_limit`) — rename the `LicenceInfo` interface and update all callers (Admin.tsx, MainLayout.tsx)
- Expose `status` as a union string: `'valid' | 'grace' | 'expired' | 'ce'`
- Add a computed `isEnterprise: boolean` getter in the hook (true when `status !== 'ce'`) so callers don't repeat the check

### Expiry display
- Compute an absolute date string from `days_until_expiry` (today + N days) and display as e.g. "Expires 27 Jun 2026"
- Colour-code: amber text when under 30 days remaining, red text when `status === 'expired'`
- When expired: show "Expired" (not a date) in the expiry row

### Status indicator
- Admin licence section: show a status badge alongside tier — green "Active" (`valid`), amber "Grace Period" (`grace`), red "Expired" (`expired`), grey "Community" (`ce`)
- Sidebar EE badge: simple "EE" or "CE" by default, but colour shifts — amber when `grace`, red when `expired`
- Non-dismissible top banner when status is `grace` or `expired`, visible to all authenticated users (not admin-only)

### Features field
- Remove the features chip list from Admin.tsx — EE is all-or-nothing, the chip list is misleading
- Replace with a "Node limit" row showing the `node_limit` value from the API
- Hide the Node limit row entirely for CE installs (`node_limit === 0` / `status === 'ce'`) — not applicable

### Claude's Discretion
- Exact Tailwind classes for badge colours
- Banner copy/wording for grace vs expired states
- Whether banner has an icon (e.g. warning triangle)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useLicence.ts` (puppeteer/dashboard/src/hooks/useLicence.ts): Hook to update — maps `/api/licence` response, exposes typed `LicenceInfo` and computed `isEnterprise`
- `Admin.tsx` (puppeteer/dashboard/src/views/Admin.tsx): Uses `useLicence()` — update licence section to use new field names, replace features chips with node_limit row, add status badge
- `MainLayout.tsx` (puppeteer/dashboard/src/layouts/MainLayout.tsx): Uses `useLicence()` — update EE badge to use new fields, add colour state for grace/expired
- `authenticatedFetch` in `src/auth.ts`: Already used by `useLicence` — no change needed

### Established Patterns
- All `useQuery`-based hooks follow the same `authenticatedFetch` + fallback-to-defaults pattern — `useLicence` already matches this
- Tailwind CSS for all styling — no CSS modules

### Integration Points
- `/api/licence` backend endpoint already stable (returns `status`, `tier`, `days_until_expiry`, `node_limit`, `customer_id`, `grace_days`)
- Hook is called in exactly 2 places: `Admin.tsx` and `MainLayout.tsx` — both need field name updates after interface rename

</code_context>

<specifics>
## Specific Ideas

- Banner for grace/expired should appear in MainLayout.tsx, wrapping the main content area, so it shows on every page
- Sidebar EE badge colour change (amber on grace, red on expired) is a low-effort persistent signal

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 74-fix-ee-licence-display*
*Context gathered: 2026-03-27*
