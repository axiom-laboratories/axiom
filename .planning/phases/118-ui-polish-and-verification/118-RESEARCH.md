# Phase 118: UI Polish and Verification - Research

**Researched:** 2026-04-04
**Domain:** React dashboard theme consistency, visual polish, component standardization, Playwright verification automation
**Confidence:** HIGH

## Summary

Phase 118 follows the theme migration completed in Phase 117 with a comprehensive visual polish pass across all 15 dashboard views. The work focuses on enforcing theme consistency for newly added components (CVEBadge, DependencyTreeModal, MirrorHealthBanner), standardizing component usage across views, fixing three critical backend/frontend bugs (GH #20, #21, #22), and building a reusable Playwright verification script that auto-screenshots all routes in both themes with quality checks.

The existing infrastructure is solid: CSS variables fully support light/dark theming, 15 shadcn/ui components provide consistent patterns, Vitest is configured with jsdom, and Playwright test infrastructure is established. The primary work is systematic auditing and fixing.

**Primary recommendation:** Execute in three waves: (Wave 1) audit and fix theme compliance for all components added post-Phase 117, including Recharts tooltip/legend/axis styling; (Wave 2) standardize density, spacing, and button states across all 15 views; (Wave 3) build and validate the Playwright verification script with automated regression testing.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Audit + fix ALL components for CSS variable compliance — CVEBadge, DependencyTreeModal, MirrorHealthBanner, Admin Smelter Registry integration must all use theme-aware variables
- WCAG AA minimum contrast enforced (4.5:1 body text, 3:1 large text/UI elements) in light mode
- Status badge colors are context-sensitive (same base hues, varied intensity per context)
- Full Recharts theming audit required — tooltips, grids, axis labels, area fills, line colors, legend text in both modes
- Playwright verification script outputs to `~/Development/mop_validation/reports/ui-polish-118/` with screenshots and report
- Permanent reusable script saved to `~/Development/mop_validation/scripts/test_ui_polish.py` for future regression testing
- Fix GitHub issues: GH #20 (Queue page 500 error), GH #21 (Node count mismatch), GH #22 (Active nodes red status + Recharts dimensions)
- Login page stays dark always (no theme audit needed)
- Pink primary buttons, pink focus rings, Fira Sans/Code fonts, pink nav accent are non-negotiable brand invariants

### Claude's Discretion
- Table standardization approach (shared Table component vs view-specific tweaks) — normalize based on what each view needs
- Toast/notification patterns — standardize based on current patterns
- Console error filter allowlist — set reasonable filters based on what the stack emits
- Exact skeleton loader shapes per view
- Specific responsive breakpoint behavior details
- Which inline-styled elements to extract into shared components

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core UI Framework
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.0 | Component framework | Latest stable, paired with TypeScript 5.9.3 |
| TypeScript | 5.9.3 | Type safety | Full codebase typed |
| Vite | 7.2.4 | Build tool | Fast HMR, modern bundler for React |
| Tailwind CSS | 3.4.17 | Utility CSS | Paired with CSS variables via @layer @apply |
| Class Variance Authority (CVA) | 0.7.1 | Component variants | Reusable button/badge/card variants |
| clsx/tailwind-merge | 2.1.1 / 3.4.0 | Utility functions | Safe class merging for overrides |

### Component Library
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Radix UI (15 packages) | 1.1.x–2.2.6 | Headless components | Provides accessibility base (dialog, select, tabs, dropdown, etc.) |
| Lucide Icons | 0.562.0 | Icons | 700+ icons, Tailwind-friendly |
| shadcn/ui styled components | 15 files | Consistent UI | Button, Card, Badge, Table, Dialog, Input, Select, Tabs, Textarea, Alert Dialog, Label, Separator, Checkbox, Sheet, Dropdown Menu |
| Sonner | 2.0.7 | Toast notifications | Dark mode aware via dynamic theme prop |

### Data & State
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TanStack React Query | 5.90.19 | Server state + caching | API data sync, invalidation patterns |
| React Router DOM | 7.12.0 | Routing | 15 views + nested routes |
| jwt-decode | 4.0.0 | JWT parsing | Decode auth tokens |

### Charts & Visualization
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Recharts | 3.6.0 | Data visualization | Dashboard, Nodes stats, Job metrics |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-markdown | 10.1.0 | Markdown rendering | Docs view |
| remark-gfm | 4.0.1 | GitHub Flavored Markdown | Links, tables in markdown |
| date-fns | 4.1.0 | Date utilities | Formatting job timestamps |

### Testing Stack
| Tool | Version | Purpose | Config |
|------|---------|---------|--------|
| Vitest | 3.0.5 | Unit/component tests | jsdom environment, setupFiles |
| @testing-library/react | 16.2.0 | React component testing | Standard patterns |
| @testing-library/dom | 10.4.0 | DOM queries | Accessibility-first |
| @testing-library/jest-dom | 6.6.3 | Matchers | toBeInTheDocument, toHaveClass, etc. |
| jsdom | 26.0.0 | DOM environment | Headless testing |
| Playwright | 1.40+ | E2E testing | Used in mop_validation scripts |

**Installation:** All dependencies already in package.json. Run `npm install` to update.

## Architecture Patterns

### Theme Infrastructure (Established in Phase 117)
CSS variables with `.dark` class pattern for light/dark switching.

**CSS variables location:** `src/index.css` (lines 15–88)

```css
:root {
  /* Light mode (default) */
  --background: 280 5% 97%;
  --foreground: 280 2% 9%;
  --primary: 346.8 77.2% 49.8%;  /* pink */
  --card: 0 0% 100%;
  --border: 280 2% 92%;
  --status-pending/assigned/completed/failed: hsl variants
  ...
}

.dark {
  /* Dark mode overrides */
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  ...
}
```

**Theme hook:** `src/hooks/useTheme.ts` — exports `{ theme, setTheme }` with localStorage persistence (key: `'mop_theme'`).

**ThemeProvider:** Wraps app in Context, safe for hydration via `mounted` state check.

**Switching:** `.dark` class on `document.documentElement`; Tailwind's `darkMode: ["class"]` config in `tailwind.config.js`.

### Theme-Aware Components — Expected Pattern
All new components should follow this pattern for theme consistency:

```tsx
// Light mode: use CSS variables or hardcoded light colors
// Dark mode: use CSS variables or hardcoded dark colors

// WRONG (hardcoded, theme-blind):
<div className="bg-red-100 text-red-900">CVE Badge</div>

// RIGHT (theme-aware):
<div className="bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100">CVE Badge</div>

// BEST (CSS variable, scales across whole app):
<div className="bg-[hsl(var(--status-failed))] text-foreground">...</div>
```

### Component Organization
```
src/
├── components/
│   ├── ui/                  # 15 shadcn/ui styled components (reusable, no logic)
│   ├── foundry/             # CVEBadge, DependencyTreeModal, BlueprintWizard
│   ├── job-definitions/     # JobDefinitionModal, JobDefinitionList, HealthTab
│   ├── MainLayout.tsx       # Root layout (sidebar, header, theme toggle in footer)
│   ├── ThemeToggle.tsx      # Sun/Moon icon slider
│   └── ...                  # Feature components (NotificationBell, MirrorHealthBanner, etc.)
├── views/                   # 15 full-page views (Jobs, Nodes, Dashboard, Templates, etc.)
├── hooks/
│   ├── useTheme.ts          # Theme state management
│   ├── useWebSocket.ts      # Live updates
│   └── ...
├── layouts/                 # Page layouts
├── auth.ts                  # authenticatedFetch() + JWT helpers
└── index.css                # CSS variables, @tailwind directives
```

### Recharts Theming Pattern — Currently Incomplete
**Current state:** Hardcoded colors in StatsSparkline (Nodes.tsx):
```tsx
<Area dataKey="cpu" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.1} />
<Area dataKey="ram" stroke="#10b981" fill="#10b981" fillOpacity={0.1} />
```

**Issue:** Colors don't adapt to dark mode. Fix via:
1. **Option A (CSS variable injection):** Read theme from localStorage, compute CSS vars, pass to Recharts
2. **Option B (useTheme hook):** Consume `theme` hook, compute colors dynamically based on `theme === 'dark'`
3. **Option C (Tailwind extend):** Define chart colors in Tailwind config, apply via computed class names

**Recommended:** Option B (useTheme hook) — integrates with existing pattern, no extra config needed.

```tsx
const StatsSparkline = ({ history }: { history: StatPoint[] }) => {
  const { theme } = useTheme();
  const cpuStroke = theme === 'dark' ? '#a78bfa' : '#8b5cf6';
  const ramStroke = theme === 'dark' ? '#34d399' : '#10b981';

  return (
    <div className="h-10 w-full mt-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={history} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <Area dataKey="cpu" stroke={cpuStroke} fill={cpuStroke} fillOpacity={0.1} />
          <Area dataKey="ram" stroke={ramStroke} fill={ramStroke} fillOpacity={0.1} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
```

### Skeleton Loader Pattern — To Be Established
Create a reusable `<Skeleton />` component for all loading states (currently replaced with raw "Loading..." text).

```tsx
// src/components/ui/skeleton.tsx
import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
      {...props}
    />
  );
}

// Usage in views:
<div className="space-y-2">
  <Skeleton className="h-12 w-full" />
  <Skeleton className="h-4 w-3/4" />
</div>
```

Animation: CSS animation in Tailwind (already available via `tailwindcss-animate` v1.0.7):
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### Button State Pattern — To Be Standardized
Establish consistent hover/focus behavior across all views:

```tsx
// Primary action button: gets hover background + focus ring
<Button className="hover:opacity-90 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
  Submit
</Button>

// Secondary/table actions: subtle, no background change
<button className="text-muted-foreground hover:text-foreground">
  Edit
</button>
```

Focus ring always uses `--ring` color (pink, 346.8 77.2% 49.8%).

### Dialog Sizing — To Be Standardized
Three standard sizes for all dialogs:
- **Small (400px):** Confirmations (delete, reset, confirm action)
- **Medium (550px):** Forms (create job, edit settings)
- **Large (700px):** Complex editors (template editor, policy form)

Applied via Dialog wrapper with `data-size` attribute or className:
```tsx
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent className="max-w-md">  {/* Small: 400px */}
    <form>...</form>
  </DialogContent>
</Dialog>
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accessible dialogs with backdrop | Custom modal div + z-index | Radix `<Dialog>` (already in ui/dialog.tsx) | Handles focus trap, keyboard close, accessibility attributes |
| Data table with sorting/filtering | Inline styled table | shadcn `<Table>` + TanStack hooks | Responsive, sortable columns, consistent look |
| Dropdown menus with submenus | Nested divs + hover states | Radix `<DropdownMenu>` (ui/dropdown-menu.tsx) | Handles keyboard nav, submenu positioning, keyboard focus |
| Multi-select inputs | Custom checkbox lists | Radix `<Select>` or checkbox `<Checkbox>` in ui/ | Accessible, keyboard navigable |
| Theme toggle | Manual localStorage + CSS class switching | Existing `ThemeProvider` + `useTheme` hook | Already working, hydration-safe, persisted |
| Toast notifications | Alert divs + setTimeout | Sonner library (already integrated) | Built-in dismiss, action buttons, dark mode aware via theme prop |
| Form validation | Manual onChange handlers | Built-in HTML5 validation + Pydantic on backend | Server-side validation is source of truth |
| Skeleton loaders | Spinner SVG or "Loading..." text | Reusable `<Skeleton>` component | Polished, respects theme, matches expected layout |
| Date formatting | Manual string manipulation | date-fns (already in package.json) | Timezone safe, locale aware |

**Key insight:** All core UI elements have shadcn/ui equivalents ready. Avoid building bespoke components when established patterns exist.

## Common Pitfalls

### Pitfall 1: Hardcoded Colors in Recharts
**What goes wrong:** Charts display wrong colors in dark mode, tooltips have poor contrast.

**Why it happens:** Recharts doesn't auto-detect CSS variables; colors must be passed as props. Hardcoding `"#8b5cf6"` works in one theme only.

**How to avoid:** Use `useTheme()` hook + computed colors based on `theme` state. Test both light/dark modes after every Recharts change.

**Warning signs:** Chart colors don't change when theme toggle is clicked; tooltips become unreadable in dark mode.

**Fix pattern:**
```tsx
const { theme } = useTheme();
const colors = {
  cpu: theme === 'dark' ? '#a78bfa' : '#8b5cf6',
  ram: theme === 'dark' ? '#34d399' : '#10b981',
};
```

### Pitfall 2: Gradient/Shadow Inconsistency Across Light/Dark Modes
**What goes wrong:** Shadows on cards disappear in dark mode (too dark), gradients look washed out.

**Why it happens:** Shadow colors use hardcoded `rgba(0,0,0,...)` which only works for light surfaces. Dark mode needs lighter shadows.

**How to avoid:** Use CSS variables for shadows — already defined in `index.css` as `--shadow-sm`, `--shadow`, `--shadow-md` with light/dark overrides.

**Warning signs:** Card drop-shadows invisible on dark backgrounds; text unreadable over backgrounds.

### Pitfall 3: Badge Color Aliasing Across Contexts
**What goes wrong:** Same status (e.g., PENDING) looks different in job badges vs node badges due to context-specific intensity.

**Why it happens:** Status colors need semantic meaning (pending=amber) but different intensity per context (job badge lighter, health indicator bolder).

**How to avoid:** Define separate CSS variables per context: `--status-pending` (light), `--status-pending-badge` (saturated), `--status-pending-indicator` (bold). Or use CVA variants.

**Warning signs:** Badge colors look inconsistent across different pages.

### Pitfall 4: Contrast Ratio Failures in Light Mode
**What goes wrong:** Secondary text in light mode falls below WCAG AA (4.5:1 body, 3:1 large).

**Why it happens:** Light stone palette has low contrast between `--foreground` (280 2% 9%) and muted text (280 4% 38%).

**How to avoid:** Test all text colors in light mode with a contrast checker. Use `--foreground` (dark stone) for body text, `--muted-foreground` only for subtle hints. Body text should never use muted color.

**Warning signs:** Text hard to read on light background; WCAG checker flags violations.

### Pitfall 5: Inline Styles Bypassing Tailwind/CSS Variables
**What goes wrong:** One-off `style={{ color: '#333' }}` or `inline className="text-blue-500"` breaks theme consistency.

**Why it happens:** Quick fix during development, forgotten during polish.

**How to avoid:** Search codebase for `style=` and hardcoded Tailwind colors (`text-blue-500`, `bg-red-100`). Extract to CSS variables or use `cn()` utility with Tailwind classes.

**Warning signs:** Some interactive elements change color on theme toggle, others don't; multiple shades of blue/red scattered across views.

### Pitfall 6: Recharts Chart Dimensions Invalid (GH #22)
**What goes wrong:** Charts render at width/height "-1" due to bug in Recharts responsive container calculation.

**Why it happens:** Container width is undefined or resolves to a negative value during initial render.

**How to avoid:** Explicitly set parent container height + width, or use `width="100%" height={400}` on ResponsiveContainer instead of relying on implicit sizing. Test that chart renders on page load (no console errors).

**Warning signs:** Chart placeholder appears but actual lines/bars don't render; console error about invalid dimensions.

### Pitfall 7: Missing Theme Awareness in New Components
**What goes wrong:** CVEBadge, DependencyTreeModal added after Phase 117 still use hardcoded colors (red-100, orange-900, etc.).

**Why it happens:** Copy-paste from old code or unaware of theme infrastructure.

**How to avoid:** Every new component must be audited: grep for hardcoded color classes (`text-red-900`, `bg-blue-100`), convert to CSS variables or theme-safe Tailwind + dark: modifier.

**Warning signs:** New component looks good in dark mode but breaks in light (or vice versa); colors don't match other badges/cards.

### Pitfall 8: Dialog Backdrop Opacity Inconsistency
**What goes wrong:** Dialog backdrop looks different in light vs dark mode.

**Why it happens:** Hardcoded `bg-black/60` doesn't adjust for theme.

**How to avoid:** Use theme-aware backdrop: `dark:bg-black/80 bg-black/60` or CSS variable.

**Warning signs:** Backdrop feels too transparent in dark mode or too opaque in light.

## Code Examples

Verified patterns from official sources and established codebase:

### Theme-Aware Component
```tsx
// Source: Phase 117 completed pattern (MirrorHealthBanner.tsx lines 20–31)
export function MirrorHealthBanner({
  isEE,
  mirrorsAvailable
}: MirrorHealthBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (!isEE || mirrorsAvailable || dismissed) {
    return null;
  }

  return (
    <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded p-4 flex items-start gap-3 mb-4">
      <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <h3 className="font-semibold text-amber-900 dark:text-amber-100">
          Mirror services not running
        </h3>
        {/* ... */}
      </div>
    </div>
  );
}
```

**Key patterns:**
- Light mode color: `bg-amber-50`, `text-amber-900`
- Dark mode color: `dark:bg-amber-950`, `dark:text-amber-100`
- Same semantic intent, varied intensity (darker bg in dark mode, lighter text)

### CVE Badge Component (Needs Theme Audit)
```tsx
// Source: Phase 110 (CVEBadge.tsx lines 21–26)
// STATUS: Uses hardcoded colors, needs conversion to CSS variables

const severityColors = {
  CRITICAL: "bg-red-100 text-red-900 dark:bg-red-900 dark:text-red-100",
  HIGH: "bg-orange-100 text-orange-900 dark:bg-orange-900 dark:text-orange-100",
  MEDIUM: "bg-yellow-100 text-yellow-900 dark:bg-yellow-900 dark:text-yellow-100",
  LOW: "bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-100",
};
```

**Good:** Dark mode overrides are present.
**Issue:** Should be CSS variables (e.g., `--cve-critical-bg`, `--cve-critical-text`) so severity colors can be adjusted project-wide.

### Recharts with Theme (Needs Implementation)
```tsx
// Source: Nodes.tsx StatsSparkline (lines ~300)
// STATUS: Hardcoded colors #8b5cf6, #10b981 — doesn't adapt to theme

const StatsSparkline = ({ history }: { history: StatPoint[] }) => {
  const { theme } = useTheme();

  // Compute colors based on theme
  const colors = {
    cpu: theme === 'dark'
      ? '#a78bfa' /* light purple in dark mode */
      : '#8b5cf6' /* dark purple in light mode */,
    ram: theme === 'dark'
      ? '#34d399' /* light green in dark mode */
      : '#10b981' /* dark green in light mode */,
  };

  return (
    <div className="h-10 w-full mt-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={history} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <Area
            type="monotone"
            dataKey="cpu"
            stroke={colors.cpu}
            fill={colors.cpu}
            fillOpacity={0.1}
            dot={false}
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="ram"
            stroke={colors.ram}
            fill={colors.ram}
            fillOpacity={0.1}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
```

### Skeleton Loader Component (To Be Created)
```tsx
// Source: Tailwind + @testing-library pattern
// Location: src/components/ui/skeleton.tsx (new file)

import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
      {...props}
    />
  );
}

// Usage in a view:
export function NodesViewLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
```

### useTheme Hook (Established Pattern)
```tsx
// Source: Phase 117 (src/hooks/useTheme.ts)
import { useContext } from 'react';
import { ThemeContext } from '@/ThemeProvider';

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}

// Usage:
const { theme, setTheme } = useTheme();
```

### Playwright Test Pattern (Established)
```python
# Source: mop_validation/scripts/test_playwright.py (lines 64–100)
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1400, "height": 900}
    )
    page = context.new_page()

    # Navigate
    page.goto(f"{BASE_URL}", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=10000)

    # Login via localStorage (React controlled inputs don't respond to fill())
    token = "eyJ..."  # from API login endpoint
    page.evaluate(f"localStorage.setItem('mop_auth_token', '{token}')")
    page.reload()

    # Assert page loaded
    expect(page.locator("h1")).to_contain_text("Dashboard")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded dark classes (`dark:bg-gray-900`) | CSS variables with light/dark scopes | Phase 117 (2026-03-02) | Centralized color changes, consistent theme across app |
| Manual localStorage theme switching | Context API + useTheme hook | Phase 117 | Hydration-safe, composable in components |
| Separate dark mode component files | Single component + conditional className | Phase 117 | DRY, fewer files to maintain |
| Inline `<Loading>` text | (To be implemented) Skeleton loaders | Phase 118 | Polished UX, matches expected layout |
| Form validation on frontend only | Server-side Pydantic validation | Phase 6+ | Single source of truth, better UX |

**Deprecated/outdated:**
- Custom modal implementations → Use Radix `<Dialog>`
- Manual table sorting → Use TanStack hooks (React Query handles caching)
- Hardcoded Tailwind color classes (e.g., `text-blue-500`) → Convert to CSS variables or theme-safe utilities
- Spinner SVGs for loading → Replace with Skeleton components

## Open Questions

1. **CVE Badge severity color intensity — should it be darker/more saturated in dark mode?**
   - What we know: Current colors use standard Tailwind palette (red-100/red-900, etc.)
   - What's unclear: Whether severity should feel more "alarming" (more saturated red) in dark mode for safety-critical contexts
   - Recommendation: Keep current intensity mapping (red-100→red-900 pair). If UX feedback indicates badges aren't prominent enough, introduce a `--cve-critical-bg-dark-intense` variable rather than changing base palette

2. **Recharts Tooltip styling — should it match card styling or stay minimal?**
   - What we know: Tooltips currently use default Recharts styling (white bg, black text)
   - What's unclear: Whether tooltips should match card background + border styling or remain minimal
   - Recommendation: Match card styling (use `--card` and `--foreground` variables) for visual consistency, but test readability — tooltips should have 4.5:1 contrast minimum

3. **Responsive breakpoint for tablet collapse — should sidebar collapse at 768px or 1024px?**
   - What we know: Context says "work well down to ~768px (iPad)"
   - What's unclear: Whether to collapse sidebar at 768px or keep it visible with narrower width
   - Recommendation: Collapse to hamburger menu at 768px (Tailwind `md:` breakpoint), with full sidebar back at 1024px (`lg:`)

4. **Table row hover state — should all tables have hover background or only sortable tables?**
   - What we know: Users expect tables to feel interactive
   - What's unclear: Whether subtle hover (light background shift) or no hover is better for read-only tables
   - Recommendation: All tables get subtle hover (opacity change or border shift), primary actions (click row to edit) get stronger hover (background change)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 3.0.5 (unit/component), Playwright 1.40+ (E2E) |
| Config file | puppeteer/dashboard/vitest.config.ts |
| Quick run command | `npm run test` (vitest in watch mode) |
| Full suite command | `npm run test -- run` (single run, exit on completion) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POL-01 | CVEBadge, DependencyTreeModal, MirrorHealthBanner render with theme CSS variables in light mode | component | `npx vitest run src/components/foundry/CVEBadge.test.tsx` | ✅ (stubs only, Wave 0) |
| POL-02 | All components render correctly in dark mode (toggle theme, check color contrast) | component + E2E | `npm run test -- run` + Playwright | ✅ theme tests, ❌ E2E coverage |
| POL-03 | WCAG AA contrast: body text 4.5:1, large text 3:1 in light mode | manual + automated | Axe-core in Playwright (to implement) | ❌ Wave 1 |
| POL-04 | Recharts charts (StatsSparkline, Dashboard bar charts) theme-aware colors in both modes | component | `npx vitest run src/views/Nodes.test.tsx::StatsSparkline` | ❌ Wave 1 |
| POL-05 | Button hover/focus states: primary buttons change background, secondary stay subtle | component + visual | `npx vitest run` + Playwright screenshot comparison | ❌ Wave 2 |
| POL-06 | All 15 views render without console errors (filtered allowlist) in both themes | E2E | Playwright script with error capture | ❌ Wave 3 |
| POL-07 | Skeleton loaders render for all data-loading states (replace "Loading..." text) | component | `npx vitest run src/components/ui/skeleton.test.tsx` | ❌ Wave 1 |
| GH-20 | Queue page /api/jobs endpoint handles status=COMPLETED,FAILED,CANCELLED without 500 error | integration | `pytest puppeteer/tests/test_jobs.py::test_queue_status_filter -x` | ✅ backend (check if exists) |
| GH-21 | Node count consistent across Dashboard (card count) and Nodes page (header) | E2E | Playwright: visit Dashboard, count nodes; visit Nodes, compare header count | ❌ Wave 3 |
| GH-22 | Active nodes show green status, Recharts charts render at valid dimensions (not -1) | E2E + component | Playwright: check node status color, verify chart rendered; component test for chart dimensions | ❌ Wave 3 |

### Sampling Rate
- **Per task commit:** `npm run test` (watch mode, fast feedback)
- **Per wave merge:** `npm run test -- run` (full suite single run) + `npx vitest run src/views/__tests__/**/*.test.tsx` (all view tests)
- **Phase gate:** Full Playwright verification script passing + no console errors + contrast audit passing before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/components/ui/skeleton.tsx` — new Skeleton component + skeleton.test.tsx (covers POL-07)
- [ ] `src/components/foundry/CVEBadge.test.tsx` — convert stubs to real tests for theme compliance (covers POL-01)
- [ ] `src/views/Nodes.test.tsx` — test StatsSparkline theme colors (covers POL-04)
- [ ] `src/test/axe-core-integration.ts` — Playwright plugin for automated WCAG AA checking (covers POL-03)
- [ ] `mop_validation/scripts/test_ui_polish.py` — new reusable Playwright verification script (covers POL-06, GH-21, GH-22)
- [ ] Backend: validate `GET /jobs?status=COMPLETED,FAILED,CANCELLED` endpoint (covers GH-20)

*(If no other gaps: above list completes Wave 0 test infrastructure setup)*

## Sources

### Primary (HIGH confidence)
- **Phase 117 implementation** (master_of_puppets repo) — Theme infrastructure confirmed working: CSS variables in index.css, useTheme hook, ThemeProvider context, Recharts needing manual color adaptation
- **Official Tailwind CSS docs** — CSS variable syntax with light/dark scopes, darkMode: ["class"] configuration pattern
- **Established codebase patterns** — Button, Card, Badge, Dialog, Table components in src/components/ui/ provide standardized, theme-aware implementations
- **CLAUDE.md project instructions** — Testing patterns: Playwright with --no-sandbox, mop_auth_token localStorage key, authenticated API calls, mop_validation test infrastructure location
- **CONTEXT.md (Phase 118)** — User constraints, GitHub issue descriptions, verification script location, theme audit scope locked

### Secondary (MEDIUM confidence)
- **Recharts documentation** — Tooltip, Legend, and axis theming require manual color props (no built-in CSS variable support)
- **Sonner toast library** — Dynamic theme prop for dark mode awareness verified in Phase 117 implementation
- **CVA (Class Variance Authority)** — Variant patterns for shadcn/ui components, currently used across button/badge implementations

### Tertiary (LOW confidence, marked for validation)
- *(No unverified claims in scope — all patterns validated against established codebase or official docs)*

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries verified in package.json with versions, used in established code
- Architecture patterns: HIGH — Phase 117 fully implemented, CSS variables working, theme switching proven in QA
- Theming approach: HIGH — CONTEXT.md specifies exact requirements (WCAG AA, status badge intensity, Recharts scope)
- Recharts theming: MEDIUM — Approach documented but requires implementation validation during Wave 1
- Skeleton component: HIGH — Pattern standard across React ecosystem, Tailwind animate plugin available
- Validation approach: MEDIUM — Playwright infrastructure exists; axe-core integration needs design during Wave 1
- GitHub issue fixes: HIGH — GH #20 (backend endpoint scoping), GH #21 (counting logic), GH #22 (chart dimensions) all actionable from code inspection

**Research date:** 2026-04-04
**Valid until:** 2026-04-18 (14 days — theme stack is stable, Recharts approach solid, but specific UI decisions may shift during execution)
**Dependent on:** No external blockers; backend `/api/jobs` endpoint ready for testing
