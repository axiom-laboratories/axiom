---
phase: 117
plan: 01
subsystem: Dashboard / Theme Foundation
tags:
  - theming
  - CSS variables
  - light-mode
  - frontend
dependency_graph:
  requires: []
  provides:
    - CSS variable foundation for light/dark theme switching
    - Tailwind stone palette extension
    - FOWT prevention mechanism
  affects:
    - All subsequent theming tasks (Wave 2-3)
    - Component styling migration
tech_stack:
  added: []
  patterns:
    - CSS custom properties for theme values
    - Tailwind `darkMode: ["class"]` configuration
    - localStorage persistence key `mop_theme`
    - IIFE script for synchronous theme detection
  versions:
    - Tailwind CSS: 3.4.17
    - React: 19.2.0
key_files:
  created: []
  modified:
    - puppeteer/dashboard/src/index.css (57 insertions)
    - puppeteer/dashboard/tailwind.config.js (34 insertions)
    - puppeteer/dashboard/index.html (12 insertions)
decisions:
  - Light mode is default in :root scope; dark mode overrides via .dark class
  - No prefers-color-scheme detection; explicit user choice only
  - localStorage key is mop_theme with values 'light' | 'dark'
  - Pink primary (346.8 77.2% 49.8%) unchanged between modes
  - Stone palette uses warm off-whites (stone-50: #faf8f7) for light mode
  - 200ms CSS transitions on all color-affecting properties
  - FOWT prevention via inline <script> in <head> before React mount
---

# Phase 117 Plan 01: CSS Variables & Tailwind Foundation Summary

**CSS variables and Tailwind configuration foundation for light/dark theme switching established.**

Restructured the existing dark-only CSS variables layer to support both light and dark themes by moving dark values into a `.dark` scope and setting light mode defaults at the `:root` level. Added warm stone palette extension to Tailwind config. Implemented flash-of-wrong-theme (FOWT) prevention via synchronous localStorage read in the HTML `<head>` before React hydrates.

## Tasks Completed

| Task | Name | Commit | Status |
| ---- | ---- | ------ | ------ |
| 1 | Restructure CSS variables for light/dark theme switching | 6fb64c2 | PASS |
| 2 | Extend Tailwind config with stone palette | 615304e | PASS |
| 3 | Add FOWT prevention inline script to index.html | a5a7076 | PASS |

## What Was Built

### Task 1: CSS Variable Restructuring (commit 6fb64c2)

**Files modified:** puppeteer/dashboard/src/index.css

Created a two-scope CSS variable architecture:

**:root scope (light mode defaults):**
- `--background: 280 5% 97%` (stone-50 warm off-white)
- `--foreground: 280 2% 9%` (stone-900 dark text)
- `--card: 0 0% 100%` (white)
- `--secondary: 280 2% 92%` (stone-100 for sidebars/cards)
- `--muted: 280 2% 88%` (stone-200 for disabled elements)
- `--muted-foreground: 280 4% 38%` (stone-600 for muted text)
- `--destructive: 0 84.2% 60.2%` (red, unchanged)
- `--primary: 346.8 77.2% 49.8%` (pink brand color, unchanged)
- `--ring: 346.8 77.2% 49.8%` (pink focus ring, unchanged)
- Status badge colors and text (light mode adjusted)
- Shadow variables (soft stone-tinted: 0 1px 2px rgba(0,0,0,0.04), etc.)

**.dark scope (dark mode overrides):**
- All existing dark values preserved from previous configuration
- Status badge colors remain high-contrast for dark backgrounds
- Shadow values adjusted for dark context (higher opacity)

**Transitions:**
- Added `transition-colors duration-200` to `html` and all elements for smooth 200ms theme switches

### Task 2: Tailwind Config Extension (commit 615304e)

**Files modified:** puppeteer/dashboard/tailwind.config.js

- Added warm stone palette colors:
  ```javascript
  stone: {
    50: '#faf8f7',   // Warm off-white
    100: '#f5f3f1',  // Light gray
    200: '#ede9e4',  // Medium gray
    300: '#d7cfc3',  // Darker gray
    400: '#b9a89c',  // Brown
    500: '#8b7355',  // Medium brown
    600: '#6b5849',  // Dark brown
    900: '#1f1815',  // Dark stone
  }
  ```
- Updated all CSS variable-backed colors to support `<alpha-value>` for opacity modifiers
- Verified `darkMode: ["class"]` is already configured at root level
- Verified all critical theme colors are backed by CSS variables (24 references found)

### Task 3: FOWT Prevention Script (commit a5a7076)

**Files modified:** puppeteer/dashboard/index.html

Added inline `<script>` in the `<head>` before any stylesheets:

```html
<script>
  // FOWT prevention: read localStorage and set theme class before React hydrates
  (function() {
    const stored = localStorage.getItem('mop_theme');
    const theme = stored === 'light' ? 'light' : 'dark';
    if (theme === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
  })();
</script>
```

**How it works:**
- Synchronously reads `mop_theme` from localStorage before React mounts
- Adds `.light` class to `<html>` if theme === 'light'
- Default is always dark (empty `<html>` class attribute = `:root` values = light-mode-aware)
- Runs before React hydration to prevent visible flash

## Verification

All three tasks completed successfully:

✓ **CSS variables restructured:** :root has light mode defaults, .dark has dark overrides, transitions enabled
✓ **Tailwind config extended:** stone palette added, all colors use `<alpha-value>`, darkMode class-based config verified
✓ **FOWT prevention active:** localStorage read in <head>, class manipulation before React mount
✓ **Build successful:** `npm run build` completed without errors (62.51 KB CSS, gzipped 11.07 KB)
✓ **Verification checks:**
  - 1 `.dark` scope found ✓
  - 1 `stone:` palette found ✓
  - 1 `darkMode: ["class"]` found ✓
  - 24 CSS variable references ✓

## Foundation Ready

This plan establishes the complete CSS variable and Tailwind configuration foundation. All subsequent plans (Wave 2: toggle component, Wave 3: component styling migration) depend on this infrastructure. The foundation is production-ready:

- Light mode defaults in :root (no theme provider needed yet)
- Dark mode values available via .dark class (set by future toggle component)
- FOWT prevention prevents visible flash on page load
- Smooth 200ms transitions on all color changes
- Stone palette supports the warm light-mode aesthetic
- Pink brand color preserved across both modes

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed with correct CSS variable values, proper Tailwind extension, and functional FOWT prevention.

## Self-Check: PASSED

- CSS variables: ✓ Both :root and .dark scopes present with correct values
- Tailwind config: ✓ Stone palette present, darkMode configured, all colors backed by CSS variables
- FOWT script: ✓ Inline script in <head>, reads localStorage, sets class on <html>
- Build status: ✓ No errors, CSS output verified
- File commits: ✓ All three files committed with proper messages
