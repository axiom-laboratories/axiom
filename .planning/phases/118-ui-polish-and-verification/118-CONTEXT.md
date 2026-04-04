# Phase 118: UI Polish and Verification - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Comprehensive UI polish pass across the entire React dashboard, fixing visual inconsistencies from the Phase 117 theme migration, standardizing component usage, resolving 3 open GitHub issues (#20, #21, #22), and producing a reusable Playwright verification script that screenshots every route in both themes with automated quality checks.

</domain>

<decisions>
## Implementation Decisions

### Theme consistency audit
- Audit + fix ALL components — every component added after Phase 117 (CVEBadge, DependencyTreeModal, MirrorHealthBanner, Admin Smelter Registry integration) must be checked and converted to CSS variables
- WCAG AA minimum contrast (4.5:1 body text, 3:1 large text/UI elements) enforced in light mode
- Status badge colors are context-sensitive — same base hues (green/amber/red/blue) but varied intensity per context (e.g., CVE severity badges can be more alarming than job status badges)
- Full chart theming — audit all Recharts instances (tooltips, grids, axis labels, area fills, line colors, legend text) in both modes. Bundle chart sizing fix (width -1, height -1 from GH #22) into this work

### Visual polish targets
- Comfortable balanced density — moderate spacing (p-4), readable table text, clear section separation. Professional SaaS feel. Normalize across all 15 views
- Primary actions only get hover/focus states — buttons and main CTAs get hover state (background shift) and focus ring for keyboard nav. Table rows and inline links stay subtle
- Skeleton loaders everywhere — pulsing placeholder shapes matching expected content layout for all data-loading states. Replace any raw "Loading..." text
- Tablet-friendly responsive — work well down to ~768px (iPad). Sidebar collapses, tables become scrollable, cards stack. No phone optimization needed

### Component consistency
- Enforce shared ui/ components — replace all inline-styled duplicates with proper <Button>, <Card>, <Badge>, etc. No ad-hoc styling for core elements
- 3 standard dialog sizes: Small (400px, confirmations), Medium (550px, forms), Large (700px, complex editors). Every dialog picks one. Consistent backdrop and close behavior

### Verification approach
- Playwright screenshots in both themes — automated script visits every route in light and dark mode, captures screenshots
- Automated checks — no console errors (filtered for known benign messages, Claude decides filter), no layout overflow, accessible names on interactive elements
- Output: screenshots and report saved to `~/Development/mop_validation/reports/ui-polish-118/`
- Permanent reusable script saved to `~/Development/mop_validation/scripts/test_ui_polish.py` — becomes part of the test suite for future UI regression testing

### GitHub issue fixes
- **GH #20**: Queue page 500 error — fix the backend `GET /api/jobs?status=COMPLETED,FAILED,CANCELLED...` endpoint that returns 500
- **GH #21**: Node count mismatch — Dashboard says 1, Nodes page header says 7, list shows 3-4. Fix counting logic to be consistent
- **GH #22**: Active nodes show red status dots — fix health indicator logic so active nodes display correct green status. Fix Recharts invalid dimensions (bundled with chart theming)

### Claude's Discretion
- Table standardization approach (shared Table component vs view-specific tweaks) — normalize based on what each view needs
- Toast/notification patterns — standardize based on current patterns, aiming for consistency without forcing awkward patterns
- Console error filter allowlist — set reasonable filters based on what the stack actually emits
- Exact skeleton loader shapes per view
- Specific responsive breakpoint behavior details
- Which inline-styled elements to extract into shared components vs leave as-is

</decisions>

<specifics>
## Specific Ideas

- The warm stone palette (light mode) and zinc palette (dark mode) from Phase 117 must be preserved — all polish work follows these palettes
- Login page stays dark always — no theme audit needed there
- Brand invariants are non-negotiable: pink primary buttons, pink focus rings, Fira Sans/Code fonts, pink nav accent
- The Playwright verification script should use the established pattern: `--no-sandbox`, JWT auth via localStorage (`mop_auth_token`), form-encoded API login
- Skeleton loaders should feel responsive and polished — pulsing placeholders, not spinning wheels

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- 15 shadcn/ui-style components in `src/components/ui/` — button, card, dialog, table, badge, input, select, tabs, etc.
- `ThemeToggle.tsx` + `useTheme.tsx` hook + `ThemeProvider.tsx` — complete theme infrastructure from Phase 117
- CSS variables in `index.css` with light/dark scopes — `--background`, `--foreground`, `--card`, `--muted`, `--border`, `--input`
- CVA (Class Variance Authority) + `cn()` utility for component variants
- Sonner for toast notifications
- Recharts for charts (Dashboard sparklines, Node stats)
- Lucide icons throughout

### Established Patterns
- All views migrated to CSS variables in Phase 117 (35 files)
- `authenticatedFetch()` in `src/auth.ts` for API calls
- WebSocket live updates via `useWebSocket.ts` hook
- Existing Playwright test infrastructure in `mop_validation/scripts/test_playwright.py`

### Integration Points
- All 15 view files in `src/views/` — audit targets
- `src/components/` — 15+ feature components to check for theme compliance
- `src/components/ui/` — shared component library to enforce
- `MainLayout.tsx` — root layout, sidebar, responsive behavior
- `index.css` — CSS variable definitions, may need skeleton loader animations added
- `tailwind.config.js` — may need responsive breakpoint customization

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 118-ui-polish-and-verification*
*Context gathered: 2026-04-04*
