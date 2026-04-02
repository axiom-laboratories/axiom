# Phase 117: Implement light mode with a light mode/dark mode toggle, whilst keeping the brand identity - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a complete light theme to the React dashboard and a user-facing toggle to switch between dark and light modes. The existing dark theme remains the default. Brand identity (pink/magenta primary color, Fira Sans/Code fonts) is preserved across both modes.

</domain>

<decisions>
## Implementation Decisions

### Light mode palette
- Warm off-white base using Tailwind's `stone` palette (stone-50 page bg, stone-100 sidebar/card bg, white for card bodies and inputs)
- Primary pink (HSL 346.8 77.2% 49.8%) stays identical in both modes — no adaptation
- Status badges: softer backgrounds in light mode (emerald-50/text-emerald-700, red-50/text-red-700, amber-50/text-amber-700) instead of the dark mode's transparent-on-dark pattern
- Code/script blocks: light themed (stone-100 bg, dark text) — NOT dark blocks on light pages
- Table rows: subtle alternating stripes (stone-50/white rows) for data-heavy views
- Input fields: white background, stone-300 borders, stone-900 text, stone-400 placeholder, pink focus ring
- Shadows: soft stone-tinted shadows on cards and elevated elements in light mode (replacing the border-only elevation used in dark mode)
- Charts: same hue families, adjusted for light backgrounds — grid lines become stone-200, axis labels stone-500, area fills use softer opacity, tooltip bg white + shadow
- Scrollbar: custom styled — stone-300 thumb on stone-100 track in light mode
- Hover states: darken on hover (stone-100 → stone-200, white → stone-50) — inverse of dark mode's lighten pattern

### Toggle placement & behavior
- Segmented sun/moon slider toggle in the sidebar footer, near the user/logout area
- Pink slider dot (brand primary) on neutral track (stone track in light, zinc track in dark)
- Sun and moon icons rotate subtly (180°) when the slider moves
- Persistence: localStorage only, key `mop_theme`, values `'dark'` | `'light'`
- Default: always dark on first visit — does NOT detect OS `prefers-color-scheme`
- No keyboard shortcut for toggling
- Login page stays dark always — toggle only appears post-authentication in the sidebar

### Transition & polish
- 200ms CSS transition on background-color, color, and border-color when toggling — smooth crossfade, no jarring flash
- Flash-of-wrong-theme prevention: inline `<script>` in index.html `<head>` reads localStorage and sets class on `<html>` before React hydrates
- Modal/overlay backdrops: theme-aware — black/60 in dark mode, black/30 in light mode; modal body follows theme
- Toast notifications: theme-aware — white bg + stone border + shadow in light mode, zinc-900 bg + zinc-800 border in dark mode
- Recharts tooltips: theme-aware — white bg + shadow in light mode, dark bg in dark mode
- WebSocket connection indicator: same green/red dots, background pill adapts to theme (stone-100 in light, zinc-800 in dark)
- Favicon: no change between modes — stays the same

### Brand identity invariants (must NOT change between modes)
- Logo pill: always pink background, both modes
- Primary action buttons (Create, Save, Submit): always bg-primary with white text
- Focus rings: always pink (--ring stays the same)
- Active navigation item: pink left border accent, both modes
- Fira Sans / Fira Code fonts: unchanged

### Claude's Discretion
- Exact CSS variable values for the light theme `:root` scope (as long as they follow the stone palette decisions above)
- How to restructure existing hardcoded Tailwind classes (bg-zinc-925, text-zinc-400, etc.) to use theme-aware alternatives
- Whether to use `dark:` prefix classes or restructure the CSS variable layer
- Transition timing function and exact duration tuning
- Exact shadow values for light mode cards/modals

</decisions>

<specifics>
## Specific Ideas

- Segmented toggle should feel like a physical switch — pink dot slides smoothly between sun and moon positions
- The warm stone palette was chosen specifically to complement the pink brand color (cool whites would clash)
- Login page staying dark preserves the "first impression" brand experience
- The inline head script pattern for FOWT prevention is critical — React mount delay would cause visible flash

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- Tailwind config already has `darkMode: ["class"]` — infrastructure exists, just needs `.dark` scoping
- CSS variables in `index.css` `:root` — can add a second set under `.dark` scope (or restructure so `:root` = light, `.dark` = dark)
- CVA (Class Variance Authority) + `cn()` utility — component variants can be extended for theme awareness
- Lucide icons (already in project) — has `Sun` and `Moon` icons for the toggle
- `recharts` — supports custom tooltip/grid/axis styling via props

### Established Patterns
- Components use a mix of CSS variables (`bg-primary`, `text-foreground`) AND hardcoded Tailwind classes (`bg-zinc-925`, `text-zinc-400`, `bg-zinc-975`)
- The hardcoded classes are the main migration challenge — they won't respond to theme switching without being replaced
- Custom zinc shades defined in tailwind.config.js: `zinc.925` (#121214), `zinc.975` (#09090b)
- Status badges use custom CSS classes with status color variables in `index.css`
- `MainLayout.tsx` is the root layout — applies `bg-zinc-975 text-white` at the top level

### Integration Points
- `index.html` — needs inline script for FOWT prevention
- `MainLayout.tsx` — sidebar footer needs the toggle component
- `index.css` — CSS variable layer needs light/dark scoping
- `tailwind.config.js` — may need stone palette extension or custom theme values
- All view files (Dashboard, Nodes, Jobs, etc.) — hardcoded dark classes need theme-aware replacements
- `src/components/ui/` — shared components need theme-aware styling

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 117-implement-light-mode-with-a-light-mode-dark-mode-toggle-whilst-keeping-the-brand-identity*
*Context gathered: 2026-04-02*
