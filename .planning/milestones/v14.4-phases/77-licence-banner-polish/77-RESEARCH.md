# Phase 77: Licence Banner Polish - Research

**Researched:** 2026-03-27
**Domain:** React / TypeScript — MainLayout component surgery (role guard + sessionStorage dismiss)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Role guard**: Inline check `const isAdmin = getUser()?.role === 'admin'` in MainLayout — no new hook
- **Fail closed**: missing/undefined role treated as non-admin — no banner shown
- **Dismiss storage key**: `sessionStorage` key `axiom_licence_grace_dismissed` — tab lifetime only
- **Dismiss control**: X button right-aligned inline in amber GRACE banner only — DEGRADED_CE has no dismiss
- **DEGRADED_CE dismiss independence**: if licence transitions to DEGRADED_CE after GRACE dismissed, red banner still shows
- **Banner copy**: keep current text exactly — GRACE shows `days_until_expiry`, expired shows CE mode message
- **No links** added to either banner
- **Tests**: extend `MainLayout.test.tsx` — add operator/viewer role tests, keep existing admin mock

### Claude's Discretion
- Exact X button styling (size, opacity, hover state) — keep consistent with existing icon usage in the file
- Whether to extract a `LicenceBanner` sub-component or keep inline in MainLayout

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BNR-01 | Admin user sees amber banner when licence is in GRACE state | Existing `licence.status === 'grace'` branch in MainLayout lines 211-223; add isAdmin guard |
| BNR-02 | Admin user sees red banner when licence is in DEGRADED_CE state | Existing `licence.status === 'expired'` branch; add isAdmin guard |
| BNR-03 | Admin user can dismiss the GRACE banner (dismissal persists for the session) | sessionStorage key `axiom_licence_grace_dismissed`; useState to track dismissed state |
| BNR-04 | DEGRADED_CE banner cannot be dismissed | No dismiss control rendered for `expired` status; confirmed by omitting X button from that branch |
| BNR-05 | Licence state banners not visible to operator or viewer roles | `const isAdmin = getUser()?.role === 'admin'` guard wrapping entire banner block |
</phase_requirements>

## Summary

Phase 77 is a surgical edit to a single component — `MainLayout.tsx` (lines 211-223). The banner already renders correctly for `grace` and `expired` states. Three behaviours are missing: (1) the banner shows for all roles, not just admin; (2) the GRACE banner has no dismiss control; (3) the DEGRADED_CE banner is not prevented from being dismissed.

All required building blocks are already present in the file: `getUser()` from `auth.ts` returns the decoded JWT synchronously, `lucide-react` exports both `AlertTriangle` (already imported) and `X` (needs importing), and `sessionStorage` is the browser-native API for tab-lifetime persistence. No new hooks, no new API calls, no new files are strictly required.

The test file at `src/layouts/__tests__/MainLayout.test.tsx` already mocks `useLicence`, `getUser`, and `useFeatures`, and all 56 existing tests pass cleanly. New tests need to vary the `getUser` mock per test rather than using the module-level mock, using `vi.mocked` or per-test `mockReturnValue` overrides.

**Primary recommendation:** Edit `MainLayout.tsx` in place — add `isAdmin` guard, `dismissed` state initialised from `sessionStorage`, X button for GRACE only. Extend `MainLayout.test.tsx` with four new cases (operator+GRACE, viewer+DEGRADED_CE, admin+dismiss behaviour, post-dismiss DEGRADED_CE still shows).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | (project) | Component state (`useState`) | Already in use |
| lucide-react | ^0.562.0 | `X` icon for dismiss button | Already imported in MainLayout; `X` and `XIcon` both confirmed present at this version |
| sessionStorage | Browser API | Tab-lifetime dismiss persistence | Native, no dependency needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @testing-library/react | (project) | `render`, `screen`, `fireEvent` | Extend existing MainLayout.test.tsx |
| vitest | (project) | `vi.fn()`, `mockReturnValue` | Per-test mock overrides for `getUser` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sessionStorage | localStorage | localStorage persists across tabs/restarts — requirement says session-scoped only; sessionStorage is correct |
| sessionStorage | React context/state | State resets on full page reload; sessionStorage survives same-tab navigation — requirement says "for the rest of that browser session" which maps to sessionStorage |
| Inline check | Custom hook | Hook adds file/indirection for a one-liner; locked decision says no new hook |

**No installation required** — all dependencies are already present.

## Architecture Patterns

### Recommended Change Structure

No new files strictly required. All changes land in two existing files:

```
src/
├── layouts/
│   └── MainLayout.tsx          ← primary edit (role guard + dismiss state + X button)
└── layouts/__tests__/
    └── MainLayout.test.tsx     ← extend with 4 new test cases
```

Extracting a `LicenceBanner` sub-component is at Claude's discretion. If chosen, it stays in the same file (inline component, not a new file) since the banner is only used in one place. The component structure mirrors `NavItem` and `NavItemEE` which are defined inline.

### Pattern 1: Admin Role Guard
**What:** Compute `isAdmin` once at component top, gate entire banner block
**When to use:** Any place a UI element should be role-restricted
```typescript
// Pattern already used for features — mirror the inline style
const user = getUser();           // already called at line 149
const isAdmin = user?.role === 'admin';   // add this alongside existing user line
```

Note: `user` is already declared at line 149. The `isAdmin` derivation can be a single additional line right after it. No duplication.

### Pattern 2: sessionStorage Dismiss State
**What:** `useState` initialised from `sessionStorage`, setter writes back to `sessionStorage`
**When to use:** Tab-lifetime UI state that survives SPA route navigation but resets on new tab/session
```typescript
// Source: standard React + browser API pattern
const GRACE_DISMISSED_KEY = 'axiom_licence_grace_dismissed';

const [graceDismissed, setGraceDismissed] = useState<boolean>(
    () => sessionStorage.getItem(GRACE_DISMISSED_KEY) === '1'
);

const handleDismissGrace = () => {
    sessionStorage.setItem(GRACE_DISMISSED_KEY, '1');
    setGraceDismissed(true);
};
```

The lazy initialiser `() => sessionStorage.getItem(...)` reads storage once on mount. Subsequent renders use React state — no repeated storage reads.

### Pattern 3: Conditional Dismiss Button
**What:** X button rendered only in GRACE banner, not in DEGRADED_CE
**When to use:** Banners with asymmetric dismiss behaviour
```typescript
// In the GRACE branch only:
<button
    onClick={handleDismissGrace}
    className="ml-auto p-1 rounded hover:bg-amber-800/50 text-amber-300 hover:text-amber-100"
    aria-label="Dismiss licence warning"
>
    <X className="h-4 w-4" />
</button>
```

Exact styling is at Claude's discretion — match the opacity/hover pattern of other icon buttons in the file.

### Pattern 4: Per-Test getUser Mock Override
**What:** Override the module-level `getUser` mock on a per-test basis for role tests
**When to use:** Tests that need different user contexts within the same describe block
```typescript
// Source: vitest vi.mocked() pattern
import * as auth from '../../auth';
// ... after the vi.mock('../../auth', ...) call ...

it('operator sees no banner in grace state', () => {
    vi.mocked(auth.getUser).mockReturnValue({ username: 'op1', role: 'operator', sub: 'op1', exp: 9999999999 });
    mockUseLicence.mockReturnValue({ status: 'grace', days_until_expiry: 5, ...rest });
    renderLayout();
    expect(screen.queryByText(/expires in/i)).toBeNull();
});
```

The existing mock uses `vi.mock('../../auth', () => ({ getUser: () => ({...}) }))` which returns a plain function, not a `vi.fn()`. To allow per-test overrides, the mock factory must return `vi.fn()`:
```typescript
const mockGetUser = vi.fn();
vi.mock('../../auth', () => ({
    getUser: (...args: any[]) => mockGetUser(...args),
    logout: vi.fn(),
    authenticatedFetch: vi.fn(),
}));
```
Then `mockGetUser.mockReturnValue(...)` per test. This is the same pattern already used for `mockUseLicence`.

### Anti-Patterns to Avoid
- **Reading sessionStorage inside render body (not lazy init):** Causes read on every render. Use lazy `useState(() => ...)` initialiser.
- **Putting the role check inside the banner JSX expression:** Makes the outer condition complex. Compute `isAdmin` at component top, use it cleanly.
- **Using `localStorage` instead of `sessionStorage`:** Would persist dismissal across browser restarts — requirement says session-scoped only.
- **Wrapping the DEGRADED_CE branch in the `graceDismissed` check:** DEGRADED_CE and GRACE are separate states; dismissal of GRACE must not suppress DEGRADED_CE.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab-lifetime persistence | Custom event bus / context | `sessionStorage` | Browser-native, exactly session-scoped |
| Role check | Permission service call | `getUser().role` (sync, JWT) | Role is already in the token; async check adds latency and complexity for a read-only guard |
| Icon for dismiss | Custom SVG | `X` from lucide-react | Project already uses lucide-react; consistency maintained |

## Common Pitfalls

### Pitfall 1: Module-level mock blocks per-test `getUser` override
**What goes wrong:** The current `vi.mock('../../auth', ...)` returns a plain arrow function `() => ({ username: 'admin', role: 'admin' })`. You cannot call `vi.mocked(auth.getUser).mockReturnValue(...)` on a plain function.
**Why it happens:** The mock factory hardcodes the return rather than using a `vi.fn()`.
**How to avoid:** Change the mock to use `const mockGetUser = vi.fn()` (outer scope) and `getUser: (...args: any[]) => mockGetUser(...args)` in the factory. Set `mockGetUser.mockReturnValue(...)` in `beforeEach` for the default admin case, then override per test.
**Warning signs:** TypeScript error "Property 'mockReturnValue' does not exist" or test assertions unexpectedly returning admin user for operator tests.

### Pitfall 2: sessionStorage not cleared between tests
**What goes wrong:** A test that triggers the dismiss sets `sessionStorage.axiom_licence_grace_dismissed = '1'`. If `afterEach` or `beforeEach` does not clear it, subsequent tests will see the banner as already dismissed.
**Why it happens:** jsdom persists sessionStorage across test cases within the same file by default.
**How to avoid:** Add `sessionStorage.clear()` (or `sessionStorage.removeItem(GRACE_DISMISSED_KEY)`) in `beforeEach` in the test file.
**Warning signs:** Test 13 (banner present for grace) fails intermittently depending on test execution order.

### Pitfall 3: Wrapping banner render condition incorrectly
**What goes wrong:** Writing `isAdmin && (licence.status === 'grace' || licence.status === 'expired') && !graceDismissed` as a single outer condition collapses both banners under the dismiss flag.
**Why it happens:** Logical shortcut that conflates GRACE-dismissed check with DEGRADED_CE.
**How to avoid:** Keep GRACE and DEGRADED_CE as separate branches inside the `isAdmin` guard:
```typescript
{isAdmin && licence.status === 'grace' && !graceDismissed && (<amber banner with X />)}
{isAdmin && licence.status === 'expired' && (<red banner, no X />)}
```

### Pitfall 4: `user` already declared — don't redeclare
**What goes wrong:** Adding `const user = getUser()` again inside the return (or at a different scope) causes a "already declared" TypeScript error.
**Why it happens:** `user` is already declared at line 149 of MainLayout.tsx.
**How to avoid:** Derive `isAdmin` from the existing `user` variable — no second `getUser()` call needed.

## Code Examples

Verified patterns from the actual codebase:

### Existing banner block (lines 211-223 of MainLayout.tsx)
```typescript
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
This block replaces entirely with the two separate conditional branches described in Pitfall 3.

### getUser return shape (from auth.ts)
```typescript
export interface UserJwt {
    sub: string;
    exp: number;
    username: string;
    role?: string;   // optional — undefined for tokens without role claim
}
// getUser() returns UserJwt | null
```
The `role` field is optional — `user?.role === 'admin'` correctly returns `false` (not undefined) when role is absent.

### Existing mockUseLicence pattern (from MainLayout.test.tsx) — X button tests follow same shape
```typescript
const mockUseLicence = vi.fn();
vi.mock('../../hooks/useLicence', () => ({
    useLicence: (...args: any[]) => mockUseLicence(...args),
}));
// Per test:
mockUseLicence.mockReturnValue({ status: 'grace', days_until_expiry: 10, ... });
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Banner shows for all users | Banner gated to admin only | Phase 77 | Non-admin users no longer see unactionable warnings |
| No dismiss | GRACE dismissible via sessionStorage | Phase 77 | Reduces alert fatigue for admins who have seen the warning |
| Single combined conditional | Two separate branches | Phase 77 | DEGRADED_CE never suppressed by GRACE dismiss state |

## Open Questions

1. **Sub-component extraction vs inline**
   - What we know: NavItem and NavItemEE are inline components in the same file — that's the established pattern
   - What's unclear: Whether the banner logic (with state + handler) becomes unwieldy inline
   - Recommendation: Keep inline unless the result exceeds ~20 lines; the pattern is consistent with the file's style

2. **X button accessibility: `<button>` vs Radix `Button` component**
   - What we know: The project uses shadcn `Button` component for header controls, but plain `<button>` elements also appear in other views
   - What's unclear: Whether using plain `<button>` vs `Button variant="ghost"` matters for consistency
   - Recommendation: Use `Button variant="ghost" size="icon"` from `@/components/ui/button` for full style consistency with other icon buttons (e.g., the mobile menu trigger at line 168)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (project dependency) |
| Config file | `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx` |
| Full suite command | `cd puppeteer/dashboard && npm run test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BNR-01 | Admin sees amber banner in GRACE state | unit | `npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | Test 13 exists — extend |
| BNR-02 | Admin sees red banner in DEGRADED_CE state | unit | `npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | Test 14 exists — extend |
| BNR-03 | Admin can dismiss GRACE banner; does not reappear in session | unit | `npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | New test needed |
| BNR-04 | DEGRADED_CE banner has no dismiss control | unit | `npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | New test needed |
| BNR-05 | Operator/viewer see no banner regardless of state | unit | `npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | New tests needed (2) |

### Sampling Rate
- **Per task commit:** `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx`
- **Per wave merge:** `cd puppeteer/dashboard && npm run test -- --run`
- **Phase gate:** Full suite green (currently 56 pass) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/layouts/__tests__/MainLayout.test.tsx` — needs `mockGetUser` refactor + 4 new test cases (BNR-03, BNR-04, BNR-05 x2), `sessionStorage.clear()` in beforeEach

*(All test infrastructure exists — framework, config, setup, and the target test file are present. Only new cases and a mock refactor are needed.)*

## Sources

### Primary (HIGH confidence)
- Direct read of `puppeteer/dashboard/src/layouts/MainLayout.tsx` — confirmed existing banner at lines 211-223, existing imports, `user` declaration at line 149
- Direct read of `puppeteer/dashboard/src/layouts/__tests__/MainLayout.test.tsx` — confirmed mock patterns, existing test numbers, `mockUseLicence` shape
- Direct read of `puppeteer/dashboard/src/auth.ts` — confirmed `getUser()` signature, `UserJwt.role?: string`
- Direct read of `puppeteer/dashboard/src/hooks/useLicence.ts` — confirmed `status: 'valid' | 'grace' | 'expired' | 'ce'` (expired = DEGRADED_CE)
- Direct read of `puppeteer/dashboard/vitest.config.ts` — confirmed jsdom environment, setup file
- `node -e` check — confirmed `X` and `XIcon` both exported by lucide-react ^0.562.0
- `npm run test -- --run` — confirmed all 56 tests pass on current codebase

### Secondary (MEDIUM confidence)
None needed — all findings are from direct codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from package.json and node_modules
- Architecture: HIGH — verified from direct file reads of all affected files
- Pitfalls: HIGH — identified from actual mock patterns in test file and jsdom sessionStorage behaviour
- Test map: HIGH — verified from running the test suite and inspecting existing test IDs

**Research date:** 2026-03-27
**Valid until:** Stable — these are internal implementation details that don't change without explicit code edits
