# Phase 117: Light Mode Implementation - Research

**Researched:** 2026-04-02
**Domain:** React/Tailwind theming with CSS variables, localStorage persistence, component styling migration
**Confidence:** HIGH

## Summary

Phase 117 requires implementing a complete light theme for the React dashboard while preserving the existing dark theme as the default. The decision document clearly specifies the light mode palette (warm stone colors), toggle placement (sidebar footer), persistence strategy (localStorage `mop_theme`), and brand identity invariants (pink primary color, fonts unchanged). The codebase already has Tailwind's `darkMode: ["class"]` configuration and CSS variable infrastructure in place; the primary challenge is migrating hardcoded dark-mode Tailwind classes (`bg-zinc-925`, `text-zinc-400`, etc.) to theme-aware alternatives and ensuring smooth transitions across 50+ components.

**Primary recommendation:** Restructure CSS variables to use a `.light` class at the `:root` scope (alongside existing `:root`), create a custom theme provider hook for hydration and localStorage sync, replace hardcoded dark classes with CSS variable-backed utilities throughout the codebase, and implement a theme toggle component using Lucide's Sun/Moon icons with 200ms transitions.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Light mode palette:** Warm stone base (stone-50 page bg, stone-100 sidebar/card, white inputs); pink primary unchanged
- **Status badges:** Softer colored backgrounds in light mode (emerald-50/text-emerald-700, red-50/text-red-700, amber-50/text-amber-700)
- **Code/script blocks:** Light themed (stone-100 bg, dark text) — NOT dark blocks
- **Table rows:** Subtle alternating stripes (stone-50/white)
- **Input fields:** White bg, stone-300 borders, stone-900 text, stone-400 placeholder, pink focus ring
- **Shadows:** Soft stone-tinted shadows in light mode (not border-only)
- **Charts:** Grid stone-200, axis labels stone-500, softer opacity fills, white tooltip bg
- **Scrollbar:** Custom styled (stone-300 thumb on stone-100 track in light mode)
- **Hover states:** Darken on hover (inverse of dark mode)
- **Toggle placement:** Sidebar footer, segmented sun/moon slider with pink dot, 200ms transitions
- **Persistence:** localStorage only, key `mop_theme`, values `'dark'` | `'light'`
- **Default:** Always dark on first visit (NOT OS `prefers-color-scheme`)
- **Login page:** Stays dark always; toggle only post-auth
- **Flash-of-wrong-theme prevention:** Inline `<script>` in `index.html` `<head>` reads localStorage before React hydrates
- **Modal/overlay backdrops:** Theme-aware (black/60 dark, black/30 light)
- **Toast notifications:** Theme-aware (white bg + stone border + shadow in light, zinc-900 in dark)
- **Recharts tooltips:** Theme-aware (white bg + shadow in light, dark in dark)
- **WebSocket indicator:** Same dots, background pill theme-aware
- **Brand invariants:** Logo always pink, primary buttons unchanged, focus rings pink, active nav pink left border, Fira Sans/Code fonts unchanged
- **No `prefers-color-scheme`:** Explicit user choice only

### Claude's Discretion
- Exact CSS variable values for light theme `:root` scope
- How to restructure hardcoded Tailwind classes (e.g., should `bg-zinc-925` become `bg-background`, or use `.dark:bg-zinc-925` pattern?)
- Whether to use `dark:` prefix classes or restructure CSS variable layer
- Transition timing function and exact duration (200ms locked, function TBD)
- Exact shadow values for light mode cards/modals

### Deferred Ideas
None — discussion stayed within phase scope.

---

## Standard Stack

### Core Theming Infrastructure
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tailwind CSS | 3.4.17 | CSS framework with class-based theming | Already in project, has `darkMode: ["class"]` config |
| CSS Custom Properties (CSS Variables) | Native | Root-level theme values | Lightweight, supported everywhere, already used in project (e.g., `--primary`, `--background`) |
| React Context + State | Native (React 19.2.0) | Theme state management + hydration | No external dependency needed; familiar pattern |
| localStorage API | Native | Client-side persistence | Works offline, no server round-trip, existing pattern in codebase |
| Lucide React | 0.562.0 | Icon library (Sun, Moon icons) | Already in project, comprehensive icon set |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Sonner | 2.0.7 | Toast notifications | Already in project; needs theme-aware toast callback |
| Recharts | 3.6.0 | Charts with tooltips | Already in project; tooltips need theme-aware styling |
| Radix UI Dialog | 1.1.15 | Modal dialogs | Already in project; backdrop colors theme-aware |
| `tailwind-merge` | 3.4.0 | Merge conflicting Tailwind classes | Already in project; useful for variant composition |
| `clsx` | 2.1.1 | Conditional class composition | Already in project; use for theme variants |

### No Alternative Considered
The locked decisions specify CSS variables + localStorage + class-based toggle. No exploration of alternatives (e.g., Styled Components, TailwindCSS `prefers-color-scheme`) is warranted — user decisions are firm.

**Installation:**
```bash
# All dependencies already installed; no new packages needed
npm list tailwindcss recharts sonner
```

---

## Architecture Patterns

### Existing Infrastructure (Ready to Extend)

**Tailwind Configuration:**
```typescript
// puppeteer/dashboard/tailwind.config.js (lines 4, 20-65)
export default {
  darkMode: ["class"],  // Already enabled — .dark class at <html>
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: 'hsl(var(--primary))',
        // ... more CSS variable-backed colors
      }
    }
  }
}
```

**CSS Variables (Current - Dark Only):**
```css
/* puppeteer/dashboard/src/index.css :root scope (lines 5-32) */
:root {
  --background: 240 10% 3.9%;  /* Dark blue-gray */
  --foreground: 0 0% 98%;       /* Near white */
  --primary: 346.8 77.2% 49.8%; /* Pink (brand) */
  --secondary: 240 3.7% 15.9%;  /* Dark gray */
  --muted: 240 3.7% 15.9%;      /* Dark gray */
  --border: 240 3.7% 15.9%;     /* Dark gray */
  --input: 240 3.7% 15.9%;      /* Dark gray */
  --ring: 346.8 77.2% 49.8%;    /* Pink (focus) */
  --radius: 0.5rem;
  --status-pending: 48 96% 89%;
  --status-assigned: 201 96% 32%;
  --status-completed: 142 71% 45%;
  --status-failed: 0 84% 60%;
}
```

**Hardcoded Dark Classes (Migration Target):**
Pattern observed in Admin.tsx, MainLayout.tsx, and other views:
```typescript
// Current (dark only):
className="bg-zinc-925 border-zinc-800/50 text-white"
className="hover:bg-zinc-800 text-zinc-400"
className="bg-zinc-975 text-white"  // Root backgrounds
className="border-zinc-900"          // Borders
```

### Pattern 1: CSS Variable Restructuring for Light/Dark Toggle

**What:** Move from a single dark-only `:root` scope to a theme-aware structure where `:root` defines light mode values and `.dark` scope overrides them.

**Current state:** `:root` has dark values; no `.dark` override exists.

**Approach:**

```css
/* BEFORE (current) - Dark only */
:root {
  --background: 240 10% 3.9%;       /* Dark blue-gray */
  --foreground: 0 0% 98%;            /* Near white */
  --primary: 346.8 77.2% 49.8%;     /* Pink (same both modes) */
  --secondary: 240 3.7% 15.9%;      /* Dark gray */
  --border: 240 3.7% 15.9%;         /* Dark gray */
  --input: 240 3.7% 15.9%;          /* Dark gray */
}

/* AFTER (light + dark) */
:root {
  /* Light mode values (new) */
  --background: 0 0% 97.3%;          /* stone-50 warm off-white */
  --foreground: 240 3.7% 12.2%;      /* stone-900 dark text */
  --card: 0 0% 100%;                 /* white card bodies */
  --card-foreground: 240 3.7% 12.2%; /* stone-900 dark text */
  --secondary: 0 0% 93%;             /* stone-100 sidebar/muted bg */
  --secondary-foreground: 240 3.7% 28.6%; /* stone-700 muted text */
  --muted: 0 0% 93%;                 /* stone-100 */
  --muted-foreground: 240 5% 44.9%;  /* stone-400 muted text */
  --border: 0 0% 87%;                /* stone-200 light borders */
  --input: 0 0% 100%;                /* white inputs */
  --primary: 346.8 77.2% 49.8%;      /* Pink (unchanged) */
  --ring: 346.8 77.2% 49.8%;         /* Pink focus (unchanged) */
}

.dark {
  /* Dark mode overrides (existing dark values) */
  --background: 240 10% 3.9%;        /* Dark blue-gray */
  --foreground: 0 0% 98%;             /* Near white */
  --card: 240 10% 3.9%;               /* Dark */
  --card-foreground: 0 0% 98%;        /* Near white */
  --secondary: 240 3.7% 15.9%;       /* Dark gray */
  --secondary-foreground: 240 5% 64.9%; /* Medium gray text */
  --muted: 240 3.7% 15.9%;           /* Dark gray */
  --muted-foreground: 240 5% 64.9%;  /* Gray text */
  --border: 240 3.7% 15.9%;          /* Dark gray */
  --input: 240 3.7% 15.9%;           /* Dark gray */
  --primary: 346.8 77.2% 49.8%;      /* Pink (unchanged) */
  --ring: 346.8 77.2% 49.8%;         /* Pink (unchanged) */
}
```

**Why this works:**
- Tailwind uses CSS variables (e.g., `bg-background` expands to `background-color: hsl(var(--background))`)
- When `:root` defines `--background`, all default styling is light mode
- When `.dark` class is applied to `<html>`, `.dark` CSS variables override `:root` values
- No need to rewrite Tailwind config or class names — CSS variables handle it

**Source:** Tailwind CSS documentation on [CSS Variables](https://tailwindcss.com/docs/customizing-colors) and [Dark Mode](https://tailwindcss.com/docs/dark-mode) (verified via official docs pattern).

---

### Pattern 2: Theme Provider Hook (Hydration + State Sync)

**What:** Custom React hook to manage theme state, localStorage sync, and `<html class="dark">` updates.

**When to use:** Wrap app root to provide theme context to all child components.

**Example (pseudocode — exact implementation in plan):**

```typescript
// src/hooks/useTheme.ts
export function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    // Hydration: read from localStorage, default to 'dark'
    if (typeof window === 'undefined') return 'dark';
    return (localStorage.getItem('mop_theme') as 'light' | 'dark') || 'dark';
  });

  useEffect(() => {
    // Sync state to DOM and localStorage
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('mop_theme', theme);
  }, [theme]);

  return { theme, setTheme };
}

// src/ThemeProvider.tsx (context wrapper)
const ThemeContext = createContext<{ theme: 'light' | 'dark'; setTheme: (t: 'light' | 'dark') => void } | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme, setTheme } = useTheme();
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemeContext() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useThemeContext must be used within ThemeProvider');
  return ctx;
}
```

**Hydration + FOWT Prevention:**
The CONTEXT.md specifies an inline `<script>` in `index.html` `<head>` to read localStorage BEFORE React mounts. This prevents the white flash.

```html
<!-- index.html <head> -->
<script>
  (function() {
    const theme = localStorage.getItem('mop_theme') || 'dark';
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    }
  })();
</script>
```

This runs synchronously before any DOM painting, so users never see the wrong theme.

---

### Pattern 3: Theme Toggle Component (Sidebar Footer)

**What:** Segmented sun/moon slider toggle that updates theme via context.

**Placement:** Sidebar footer, lines 132–147 of MainLayout.tsx (replace or extend the status/licence display area).

**Example (pseudocode):**

```typescript
// src/components/ThemeToggle.tsx
import { Sun, Moon } from 'lucide-react';
import { useThemeContext } from '../hooks/useTheme';

export function ThemeToggle() {
  const { theme, setTheme } = useThemeContext();
  const isDark = theme === 'dark';

  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-100/10 dark:bg-zinc-800/20">
      <button
        onClick={() => setTheme('light')}
        className={cn(
          'flex-1 flex items-center justify-center py-1 px-2 rounded transition-colors',
          !isDark ? 'bg-primary text-white' : 'text-zinc-400 hover:text-white'
        )}
        aria-label="Light mode"
      >
        <Sun className="h-4 w-4" />
      </button>
      <button
        onClick={() => setTheme('dark')}
        className={cn(
          'flex-1 flex items-center justify-center py-1 px-2 rounded transition-colors',
          isDark ? 'bg-primary text-white' : 'text-zinc-400 hover:text-white'
        )}
        aria-label="Dark mode"
      >
        <Moon className="h-4 w-4" />
      </button>
    </div>
  );
}
```

**Placement in MainLayout:**
```typescript
<div className="p-6 border-t border-zinc-900">
  <ThemeToggle />  {/* New toggle */}
  {/* Existing status/licence display below toggle */}
</div>
```

---

### Pattern 4: Component Class Restructuring (Hardcoded → CSS Variables)

**What:** Replace hardcoded dark classes with CSS variable-backed alternatives or CSS variable mixins.

**Current problem:** Classes like `bg-zinc-925` don't respond to `.dark` class toggle because they're hardcoded, not CSS variable-backed.

**Approach:**

Option A (Preferred): Use existing CSS variable infrastructure:
```typescript
// BEFORE (hardcoded)
<div className="bg-zinc-925 border-zinc-800 text-white">

// AFTER (CSS variable-backed)
<div className="bg-card border-border text-foreground">
```

Option B (If variable coverage insufficient): Add `dark:` prefix variants:
```typescript
// If no suitable variable exists:
<div className="bg-white dark:bg-zinc-925 border-stone-200 dark:border-zinc-800">
```

**Scope of migration:**
- MainLayout.tsx: ~15 hardcoded classes (bg-zinc-975, bg-zinc-900, border-zinc-900, text-zinc-400, hover:bg-zinc-800)
- Admin.tsx: ~30+ hardcoded classes
- All view files (Dashboard, Nodes, Jobs, etc.): ~50+ classes
- UI component library (Card, Dialog, etc.): Check existing class coverage

**Source code locations to scan:**
```bash
grep -r "bg-zinc-925\|bg-zinc-975\|text-zinc-400\|border-zinc-9\|hover:bg-zinc-8" \
  puppeteer/dashboard/src --include="*.tsx" | wc -l
# Expected: ~100+ matches
```

---

### Pattern 5: Theme-Aware Component Styling

**Charts (Recharts):**
Recharts tooltips and grid lines need theme-aware colors via props:
```typescript
// BEFORE (dark only)
<LineChart data={data}>
  <CartesianGrid stroke="#333" />
  <Tooltip contentStyle={{ backgroundColor: '#09090b', border: '1px solid #333' }} />
</LineChart>

// AFTER (theme-aware)
const { theme } = useThemeContext();
const isDark = theme === 'dark';
<LineChart data={data}>
  <CartesianGrid stroke={isDark ? '#333' : '#e4e4e7'} />
  <Tooltip contentStyle={{
    backgroundColor: isDark ? '#09090b' : '#ffffff',
    border: `1px solid ${isDark ? '#333' : '#e4e4e7'}`,
    color: isDark ? '#ffffff' : '#000000'
  }} />
</LineChart>
```

**Toasts (Sonner):**
```typescript
// App.tsx
const { theme } = useThemeContext();
<Toaster theme={theme} position="bottom-right" richColors />
// Sonner supports theme prop; just pass it
```

**Modals (Radix Dialog):**
Update className on DialogContent:
```typescript
<DialogContent className={cn(
  'bg-card border-border text-foreground',
  // Fallback for any missed variables:
  'dark:bg-zinc-925 dark:border-zinc-800'
)}>
```

**Status Badges:**
Currently hardcoded in index.css. Update to light mode variants:
```css
.badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
  transition: background-color 0.2s, color 0.2s;
}

.badge.pending {
  background-color: hsl(var(--status-pending));
  color: #000;
}
/* Dark mode overrides (new) */
.dark .badge.pending {
  background-color: hsl(48 96% 89% / 0.15);  /* Darker pending in dark mode */
  color: #fef3c7;
}

/* Add soft light mode variants */
@media (prefers-color-scheme: light) {
  .badge.pending {
    background-color: #f0fdf4;  /* emerald-50 */
    color: #065f46;             /* emerald-700 */
  }
}
```

---

### Anti-Patterns to Avoid

- **Hardcoding theme detection to `prefers-color-scheme`:** Decisions explicitly say "default dark, NOT OS preference". Never use `window.matchMedia('(prefers-color-scheme: dark)')`.
- **Theme toggle on login page:** Login stays dark always. Gate toggle behind `isAuthenticated` check.
- **Missing FOWT prevention:** If inline `<script>` is omitted, users see the default theme flash before JS loads. This is critical for perceived performance.
- **Incomplete variable coverage:** If some components still use hardcoded classes after migration, theme switching is inconsistent. Audit thoroughly.
- **Transition timing without smooth delay:** 200ms transitions are locked; anything faster (50ms) or slower (400ms) looks jarring on toggle.
- **Forgetting to update custom CSS classes (.badge, .nav-link, etc.):** These aren't Tailwind classes and won't respond to `.dark` scope auto-magically.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Theme state management | Custom context from scratch | React Context + useState hook | Avoids boilerplate, keeps logic centralized |
| localStorage sync | Manual useEffect chains | Custom hook (useTheme) with effect | Single source of truth, reusable across app |
| CSS variable fallback logic | Complex ternaries in every component | Tailwind CSS variable layer + dark: prefixes | Declarative, maintainable, follows Tailwind conventions |
| Icon rotation animation | CSS animation + state-based rotation | Lucide icons + CSS transition | Icons are simple; transition on container instead of icon |
| Recharts theme support | Manual color prop construction | Sonner `theme` prop + Recharts props object | Libraries handle specifics; cleaner code |

**Key insight:** Tailwind's `darkMode: ["class"]` already exists; leveraging CSS variables avoids reimplementing theme switching. Building custom CSS-in-JS or duplicating classes in every component introduces maintenance burden.

---

## Common Pitfalls

### Pitfall 1: Flash of Wrong Theme (FOWT) on Hard Refresh

**What goes wrong:** User refreshes page; React hasn't loaded yet; browser paints `:root` (light) before inline script runs → users see light mode flash before dark loads.

**Why it happens:** Inline `<script>` must run in `<head>` synchronously before body renders. If it's in a `useEffect` or lazy-loaded, it's too late.

**How to avoid:** Add synchronous inline script to `index.html` `<head>`:
```html
<head>
  <script>
    (function() {
      const theme = localStorage.getItem('mop_theme') || 'dark';
      if (theme === 'dark') {
        document.documentElement.classList.add('dark');
      }
    })();
  </script>
  <!-- ... rest of head ... -->
</head>
```

**Warning signs:** Users report seeing white flash on page load, even though site defaults to dark. Check `index.html` for script placement.

---

### Pitfall 2: Incomplete Migration of Hardcoded Classes

**What goes wrong:** Some components use `bg-zinc-925`, others use `bg-card`. When theme changes, some components update, others stay dark.

**Why it happens:** Grepping for `bg-zinc-925` misses patterns like `bg-zinc-800`, `bg-zinc-900`, or inline style objects in JS (e.g., `style={{ backgroundColor: '#09090b' }}`).

**How to avoid:** Use a comprehensive audit before finalizing:
```bash
# Find all hardcoded dark-specific Tailwind classes
grep -r "bg-zinc-9\|bg-slate-9\|text-zinc-3\|text-zinc-4\|border-zinc-8\|hover:bg-zinc-8" \
  puppeteer/dashboard/src --include="*.tsx" --include="*.ts" | tee /tmp/dark_audit.txt

# Find inline style objects (manually scan results):
grep -r "backgroundColor.*09090b\|backgroundColor.*121214\|backgroundColor.*1f2937" \
  puppeteer/dashboard/src --include="*.tsx"
```

**Warning signs:** Some views render in light mode, others don't. Check the dark_audit.txt log and cross-reference with files you've updated.

---

### Pitfall 3: Forgetting Custom CSS Classes

**What goes wrong:** Tailwind classes are updated, but custom CSS classes (`.badge`, `.nav-link`, `.progress-bar` in index.css) don't respond to theme toggle.

**Why it happens:** Tailwind scoping is automatic via CSS variables, but custom classes need explicit `.dark` scope overrides in CSS.

**How to avoid:** Audit index.css for all custom classes and add `.dark` variants:
```css
.nav-link {
  color: var(--text-muted);  /* Use CSS variable, not hardcoded #999 */
  background-color: transparent;
}

.dark .nav-link {
  /* Dark mode override (if needed) */
}
```

Or use CSS variables throughout:
```css
.nav-link {
  color: hsl(var(--muted-foreground));  /* Responds to .dark scope automatically */
}
```

**Warning signs:** Navigation links, badges, or custom components don't change color on theme toggle. Check index.css for hardcoded colors (e.g., `color: #999` instead of `color: var(--text-muted)`).

---

### Pitfall 4: Theme Toggle on Wrong Page (Login)

**What goes wrong:** User sees a theme toggle on the login page, clicks it, then logs in and sees dark mode anyway (because login always forces dark).

**Why it happens:** Toggle component wasn't gated on authentication state.

**How to avoid:** Render ThemeToggle only in authenticated layouts:
```typescript
// MainLayout.tsx (authenticated users only)
{isAuthenticated && <ThemeToggle />}

// Login.tsx (never show toggle)
// Don't import or render ThemeToggle here
```

**Warning signs:** Theme toggle appears before login or user can change theme on login page.

---

### Pitfall 5: Transition Timing Too Fast or Slow

**What goes wrong:** Theme toggle at 50ms feels snappy but jarring; at 800ms feels like lag. CONTEXT.md locks 200ms.

**Why it happens:** CSS transition timing was tuned elsewhere; inconsistent timing feels broken.

**How to avoid:** Lock the transition in a CSS class or CSS variable:
```css
:root {
  --theme-transition-duration: 200ms;
}

* {
  transition: background-color var(--theme-transition-duration), color var(--theme-transition-duration), border-color var(--theme-transition-duration);
}
```

Or in Tailwind:
```typescript
// tailwind.config.js
theme: {
  extend: {
    transitionDuration: {
      'theme': '200ms'
    }
  }
}
```

**Warning signs:** Theme toggle feels snappy or sluggish; different components transition at different speeds. Check CSS for hardcoded `transition: 0.3s` or `0.5s` values.

---

### Pitfall 6: Login Page Accidentally Gets Light Mode

**What goes wrong:** User logs in while in light mode, then logs out; login page is now light (breaking brand experience).

**Why it happens:** Theme state persists across logout, or logout didn't reset to dark.

**How to avoid:** Reset theme in logout handler:
```typescript
// auth.ts or MainLayout.tsx logout handler
function logout() {
  localStorage.setItem('mop_theme', 'dark');  // Reset to dark on logout
  document.documentElement.classList.add('dark');
  clearAuthToken();
  navigate('/login');
}
```

**Warning signs:** Logout, then visit login page — it's light instead of dark.

---

## Code Examples

Verified patterns from CONTEXT.md and existing infrastructure.

### Full Theme Provider Setup

```typescript
// src/hooks/useTheme.ts
import { useState, useEffect } from 'react';

export type Theme = 'light' | 'dark';

export function useTheme(): { theme: Theme; setTheme: (t: Theme) => void } {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'dark';
    return (localStorage.getItem('mop_theme') as Theme) || 'dark';
  });

  useEffect(() => {
    const root = document.documentElement;

    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    localStorage.setItem('mop_theme', theme);
  }, [theme]);

  return { theme, setTheme };
}
```

```typescript
// src/ThemeProvider.tsx
import React, { createContext, useContext } from 'react';
import { useTheme, type Theme } from './hooks/useTheme';

type ThemeContextType = {
  theme: Theme;
  setTheme: (t: Theme) => void;
};

const ThemeContext = createContext<ThemeContextType | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme, setTheme } = useTheme();

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemeContext(): ThemeContextType {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useThemeContext must be used within ThemeProvider');
  }
  return ctx;
}
```

---

### Theme Toggle Component

```typescript
// src/components/ThemeToggle.tsx
import { Sun, Moon } from 'lucide-react';
import { useThemeContext } from '@/ThemeProvider';
import { cn } from '@/lib/utils';

export function ThemeToggle() {
  const { theme, setTheme } = useThemeContext();
  const isDark = theme === 'dark';

  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/30 border border-border">
      <button
        onClick={() => setTheme('light')}
        className={cn(
          'flex items-center justify-center p-1.5 rounded transition-all duration-200',
          !isDark
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        )}
        aria-label="Switch to light mode"
        title="Light mode"
      >
        <Sun className="h-4 w-4" style={{ transform: isDark ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 200ms' }} />
      </button>
      <button
        onClick={() => setTheme('dark')}
        className={cn(
          'flex items-center justify-center p-1.5 rounded transition-all duration-200',
          isDark
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        )}
        aria-label="Switch to dark mode"
        title="Dark mode"
      >
        <Moon className="h-4 w-4" style={{ transform: isDark ? 'rotate(0deg)' : 'rotate(180deg)', transition: 'transform 200ms' }} />
      </button>
    </div>
  );
}
```

---

### CSS Variable Updates (index.css)

```css
/* Light theme (default :root, no .dark scope) */
@layer base {
  :root {
    /* Light mode: warm stone palette */
    --background: 0 0% 97.3%;           /* stone-50 */
    --foreground: 240 3.7% 12.2%;       /* stone-900 */
    --card: 0 0% 100%;                  /* white */
    --card-foreground: 240 3.7% 12.2%;  /* stone-900 */
    --popover: 0 0% 100%;               /* white */
    --popover-foreground: 240 3.7% 12.2%; /* stone-900 */
    --primary: 346.8 77.2% 49.8%;       /* pink (unchanged) */
    --primary-foreground: 355.7 100% 97.3%; /* light pink */
    --secondary: 0 0% 93%;              /* stone-100 */
    --secondary-foreground: 240 3.7% 28.6%; /* stone-700 */
    --muted: 0 0% 93%;                  /* stone-100 */
    --muted-foreground: 240 5% 44.9%;   /* stone-400 */
    --accent: 0 0% 93%;                 /* stone-100 */
    --accent-foreground: 240 3.7% 28.6%; /* stone-700 */
    --destructive: 0 72% 51%;           /* red */
    --destructive-foreground: 0 0% 98%; /* white */
    --border: 0 0% 87%;                 /* stone-200 */
    --input: 0 0% 100%;                 /* white */
    --ring: 346.8 77.2% 49.8%;          /* pink (unchanged) */
    --radius: 0.5rem;

    /* Light mode status badges (new) */
    --status-pending: 48 96% 89%;       /* amber-50 */
    --status-assigned: 201 96% 32%;     /* blue (unchanged for dark compat) */
    --status-completed: 142 71% 45%;    /* emerald (unchanged) */
    --status-failed: 0 84% 60%;         /* red (unchanged) */

    /* Transition timing */
    --theme-transition: background-color 200ms, color 200ms, border-color 200ms;
  }
}

/* Dark mode overrides */
@layer base {
  .dark {
    --background: 240 10% 3.9%;        /* Existing dark blue-gray */
    --foreground: 0 0% 98%;             /* Near white */
    --card: 240 10% 3.9%;               /* Dark */
    --card-foreground: 0 0% 98%;        /* Near white */
    --popover: 240 10% 3.9%;            /* Dark */
    --popover-foreground: 0 0% 98%;     /* Near white */
    --primary: 346.8 77.2% 49.8%;       /* Pink (unchanged) */
    --primary-foreground: 355.7 100% 97.3%;
    --secondary: 240 3.7% 15.9%;        /* Dark gray */
    --secondary-foreground: 0 0% 98%;   /* Near white */
    --muted: 240 3.7% 15.9%;            /* Dark gray */
    --muted-foreground: 240 5% 64.9%;   /* Medium gray */
    --accent: 240 3.7% 15.9%;           /* Dark gray */
    --accent-foreground: 0 0% 98%;      /* Near white */
    --destructive: 0 72% 51%;           /* Red */
    --destructive-foreground: 0 0% 98%; /* White */
    --border: 240 3.7% 15.9%;           /* Dark gray */
    --input: 240 3.7% 15.9%;            /* Dark gray */
    --ring: 346.8 77.2% 49.8%;          /* Pink (unchanged) */
  }
}

/* Global transition for theme changes */
@layer base {
  * {
    @apply border-border;
    transition: var(--theme-transition);
  }

  body {
    @apply bg-background text-foreground;
    font-family: 'Fira Sans', system-ui, sans-serif;
  }
}

/* Status badges with light mode variants */
.badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
}

.badge.pending {
  @apply bg-amber-50 text-amber-700;
}
.dark .badge.pending {
  @apply bg-amber-500/20 text-amber-300;
}

.badge.assigned {
  @apply bg-blue-50 text-blue-700;
}
.dark .badge.assigned {
  @apply bg-blue-500/20 text-blue-300;
}

.badge.completed {
  @apply bg-emerald-50 text-emerald-700;
}
.dark .badge.completed {
  @apply bg-emerald-500/20 text-emerald-300;
}

.badge.failed {
  @apply bg-red-50 text-red-700;
}
.dark .badge.failed {
  @apply bg-red-500/20 text-red-300;
}

.badge.online {
  @apply bg-emerald-50 text-emerald-700;
}
.dark .badge.online {
  @apply bg-emerald-500/20 text-emerald-300;
}

.badge.offline {
  @apply bg-red-50 text-red-700;
}
.dark .badge.offline {
  @apply bg-red-500/20 text-red-300;
}

.badge.tag {
  @apply bg-stone-100 text-stone-900 border border-stone-300;
}
.dark .badge.tag {
  @apply bg-zinc-800 text-zinc-100 border border-zinc-700;
}
```

---

### Updated index.html (FOWT Prevention)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <title>Puppeteer</title>

    <!-- Theme hydration script (prevents FOWT) -->
    <script>
      (function() {
        const theme = localStorage.getItem('mop_theme') || 'dark';
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        }
      })();
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

### Updated App.tsx (Theme Provider Wrapper)

```typescript
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import { Toaster } from 'sonner';
import AppRoutes from './AppRoutes';
import { ThemeProvider, useThemeContext } from './ThemeProvider';
import './index.css';

const queryClient = new QueryClient();

// Inner App that can use useThemeContext
function AppContent() {
  const { theme } = useThemeContext();

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </TooltipProvider>
      <Toaster theme={theme} position="bottom-right" richColors />
    </QueryClientProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
```

---

### Component Class Refactoring Example (MainLayout)

```typescript
// BEFORE (MainLayout.tsx line 212):
<div className="flex min-h-screen w-full bg-zinc-975 text-white">

// AFTER:
<div className="flex min-h-screen w-full bg-background text-foreground">

// BEFORE (line 214):
<aside className="hidden border-r border-zinc-900 w-64 shrink-0 md:block bg-zinc-975">

// AFTER:
<aside className="hidden border-r border-border w-64 shrink-0 md:block bg-background">

// BEFORE (line 220):
<header className="flex h-16 items-center gap-4 border-b border-zinc-900 bg-zinc-975 px-4 lg:px-6 sticky top-0 z-10">

// AFTER:
<header className="flex h-16 items-center gap-4 border-b border-border bg-background px-4 lg:px-6 sticky top-0 z-10">

// BEFORE (line 228):
<SheetContent side="left" className="flex flex-col p-4 bg-zinc-975 border-r-zinc-900 w-72">

// AFTER:
<SheetContent side="left" className="flex flex-col p-4 bg-background border-r-border w-72">

// BEFORE (line 50):
className={({ isActive }) =>
  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-zinc-800 hover:text-white ${isActive ? "bg-zinc-800 text-white shadow-sm" : "text-zinc-400"}`
}

// AFTER:
className={({ isActive }) =>
  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-secondary hover:text-foreground ${isActive ? "bg-secondary text-foreground shadow-sm" : "text-muted-foreground"}`
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded color values (`#09090b`, `#333`) | CSS variables + Tailwind layer | Tailwind v3 (2021) | Centralized theme values, easier to maintain |
| Media query `prefers-color-scheme` detection | Explicit user toggle + localStorage | User feedback (this phase) | Respects user choice, not OS preference |
| Dark mode only | Light + dark modes with user toggle | This phase (2026) | Better accessibility, works for all lighting conditions |
| Manual theme switching in every component | Context + hook pattern | This phase (2026) | Single source of truth, reduces boilerplate |
| No FOWT prevention | Inline `<script>` in `<head>` | This phase (2026) | Eliminates white flash on reload |

**Deprecated/Outdated:**
- **`prefers-color-scheme` auto-detection:** Explicitly deferred by user decision. App always starts dark, user chooses light if desired.
- **Separate CSS files for themes:** Replaced by CSS variable scoping (`:<root>` vs `.dark`).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 3.0.5 (React Testing Library) |
| Config file | `vitest.config.ts` (exists) |
| Quick run command | `npm run test` (runs all tests in watch mode) |
| Full suite command | `npm run test -- --run` (exits after completion) |

### Phase Requirements → Test Map

Phase 117 has no explicit requirement IDs in the phase context. Based on CONTEXT.md decisions, verify:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Theme persists to localStorage on toggle | Unit | `npx vitest run src/hooks/__tests__/useTheme.test.ts -t "persists"` | ❌ Wave 0 |
| Light mode CSS variables apply to :root | Integration | `npx vitest run src/__tests__/theme.integration.test.ts -t "light mode"` | ❌ Wave 0 |
| Dark mode .dark class applies correctly | Integration | `npx vitest run src/__tests__/theme.integration.test.ts -t "dark mode"` | ❌ Wave 0 |
| FOWT prevention script in index.html | Smoke (manual + Playwright) | `python mop_validation/scripts/test_playwright.py -k "theme_hydration"` | ❌ Wave 0 |
| Theme toggle renders in sidebar (post-auth) | Component | `npx vitest run src/components/__tests__/ThemeToggle.test.tsx` | ❌ Wave 0 |
| Theme toggle hidden on login page | Integration | `npx vitest run src/layouts/__tests__/MainLayout.test.tsx -t "login"` | ✅ Exists |
| Toast theme updates on toggle | Integration | `npx vitest run src/__tests__/theme.integration.test.ts -t "toast"` | ❌ Wave 0 |
| Recharts tooltips theme-aware | Integration | `npx vitest run src/__tests__/theme.integration.test.ts -t "recharts"` | ❌ Wave 0 |
| All hardcoded dark classes migrated | Smoke (grep audit) | `grep -r "bg-zinc-9\|text-zinc-4" puppeteer/dashboard/src --include="*.tsx" && echo "FAIL" \|\| echo "PASS"` | ❌ Manual audit |
| Light mode colors render correctly (E2E) | E2E (Playwright) | `python mop_validation/scripts/test_playwright.py -k "light_mode"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `npm run test` (watch mode, covers theme hook + component tests)
- **Per wave merge:** `npm run test -- --run` (full suite, exits after completion)
- **Phase gate:** Full suite green + Playwright E2E smoke test (`test_playwright.py -k "theme"`) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `src/hooks/__tests__/useTheme.test.ts` — covers theme state, localStorage sync, DOM class updates
- [ ] `src/components/__tests__/ThemeToggle.test.tsx` — covers toggle rendering, click handlers, icon rotation
- [ ] `src/__tests__/theme.integration.test.ts` — covers light/dark mode CSS variable scoping, toast theming, recharts theming
- [ ] `src/ThemeProvider.test.tsx` — covers provider hydration, context injection
- [ ] Playwright E2E test in `mop_validation/scripts/test_playwright.py` (new test case) — covers FOWT prevention, theme toggle behavior, persistence across page reload
- [ ] Manual audit script: `src/__tests__/audit-hardcoded-classes.sh` — scans for missed `bg-zinc-9*`, `text-zinc-*`, `border-zinc-*` patterns

*(These tests don't exist yet. Planner must create them before Wave 1 implementation begins.)*

---

## Sources

### Primary (HIGH confidence)
- **Tailwind CSS v3.4.17** — Official documentation: [Dark Mode](https://tailwindcss.com/docs/dark-mode), [Customizing Colors](https://tailwindcss.com/docs/customizing-colors), [CSS Variables](https://tailwindcss.com/docs/using-css-variables)
- **Project codebase** — `puppeteer/dashboard/tailwind.config.js` (darkMode: ["class"] confirmed), `src/index.css` (CSS variable structure verified), `package.json` (dependencies confirmed: Sonner 2.0.7, Recharts 3.6.0, Lucide React 0.562.0)
- **CONTEXT.md (Phase 117)** — Locked decisions verbatim (light palette, toggle placement, localStorage key, FOWT prevention script, brand invariants)

### Secondary (MEDIUM confidence)
- **Sonner Toast Library** — Supports `theme` prop (React Context pattern, verified in existing code `<Toaster theme="dark" />`; light theme support documented in library README)
- **Recharts** — Custom tooltip/grid styling via props (`contentStyle`, `stroke` props); theme-aware examples in official examples (cross-verified with existing project patterns)

### Tertiary (LOW confidence)
None — all recommendations are grounded in official Tailwind docs, CONTEXT.md decisions, or verified existing code patterns.

---

## Metadata

**Confidence breakdown:**
- **Standard Stack:** HIGH — Tailwind, React Context, localStorage are all standard; CSS variables are native browser APIs; Sonner/Recharts already in project.
- **Architecture:** HIGH — Tailwind's `darkMode: ["class"]` is proven pattern; CSS variable scoping is standard CSS; React Context + localStorage is idiomatic React.
- **Pitfalls:** MEDIUM-HIGH — FOWT prevention is well-documented; hardcoded class migration risks are based on grep audit of codebase; incomplete variable coverage is real risk based on existing mixed patterns.
- **Code Examples:** HIGH — All examples follow official Tailwind patterns and existing project structure.

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (30 days; Tailwind is stable, React Context is stable; no breaking changes expected)
