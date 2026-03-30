# Phase 77: Licence Banner Polish - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin-only licence state banners in MainLayout — add role guard, session-scoped dismiss for GRACE (amber), and enforce non-dismissible DEGRADED_CE (red). The banner component already exists; this phase wires in the missing behaviour only. No new API endpoints, no changes to useLicence hook shape.

</domain>

<decisions>
## Implementation Decisions

### Role guard
- Inline check: `const isAdmin = getUser()?.role === 'admin'` in MainLayout
- No new hook — `getUser()` already decodes JWT synchronously; one-liner is sufficient
- Fail closed: missing/undefined role treated as non-admin → no banner shown
- Operator and viewer users see no banner regardless of licence state (BNR-05)

### Dismiss UX
- X button right-aligned inline in the amber GRACE banner (same row as message text)
- DEGRADED_CE (red) banner has no dismiss control — must remain visible
- Session-scoped via `sessionStorage` key: `axiom_licence_grace_dismissed`
- On dismiss: set `sessionStorage.setItem('axiom_licence_grace_dismissed', '1')` — banner hidden for the tab's lifetime
- If licence transitions to DEGRADED_CE in the same session after dismissal, the red banner still appears — dismiss state is GRACE-specific, DEGRADED_CE is independent

### Banner copy
- GRACE (amber): "Your EE licence expires in N days. Please renew." — keep current text, N from `licence.days_until_expiry`
- DEGRADED_CE (red): "Your EE licence has expired. The system is running in Community Edition mode." — keep current text
- No links added to either banner

### Tests
- Extend `MainLayout.test.tsx` to cover role-specific banner visibility
- Add tests: operator role → no banner even in GRACE state; viewer role → no banner even in DEGRADED_CE state
- Existing admin mock already set to `role: 'admin'` — keep and extend

### Claude's Discretion
- Exact X button styling (size, opacity, hover state) — keep consistent with existing icon usage in the file
- Whether to extract a `LicenceBanner` sub-component or keep inline in MainLayout

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MainLayout.tsx:175-188`: Banner already renders for `grace` and `expired` states — extend in place rather than rewrite
- `useLicence()`: Returns `status: 'valid' | 'grace' | 'expired' | 'ce'` and `days_until_expiry` — `expired` = DEGRADED_CE in requirements
- `getUser()` from `auth.ts`: Synchronous JWT decode, returns `{ username, role? }` — role available immediately, no async needed
- `AlertTriangle` from lucide-react already imported in MainLayout
- `X` (or `XIcon`) from lucide-react — import for dismiss button

### Established Patterns
- Feature flags checked inline in MainLayout via `useFeatures()` hook — role guard follows the same inline pattern
- No session/local storage currently used in this file — introduce it minimally for the dismiss key

### Integration Points
- Banner sits between `<header>` and `<main>` in MainLayout — existing DOM position is correct, no layout changes needed
- `MainLayout.test.tsx` already mocks `useLicence`, `getUser`, and `useFeatures` — tests extend cleanly

</code_context>

<specifics>
## Specific Ideas

No specific references — standard implementation of the existing banner pattern.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 77-licence-banner-polish*
*Context gathered: 2026-03-27*
