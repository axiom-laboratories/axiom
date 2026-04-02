---
phase: 117-implement-light-mode-with-a-light-mode-dark-mode-toggle-whilst-keeping-the-brand-identity
plan: 00
subsystem: dashboard-frontend
tags:
  - tdd
  - test-infrastructure
  - theme-system
dependency_graph:
  requires: []
  provides:
    - test-foundation-for-theme-system
    - unit-test-specs-for-hooks
    - component-test-specs
    - integration-test-specs
    - e2e-test-specs
  affects:
    - wave-01-useTheme-hook-implementation
    - wave-02-theme-provider-and-css-variables
    - wave-03-ui-component-migration
tech_stack:
  added: []
  patterns:
    - tdd-red-green-refactor
    - vitest-unit-tests
    - react-testing-library
    - playwright-e2e-testing
key_files:
  created:
    - puppeteer/dashboard/src/hooks/__tests__/useTheme.test.ts
    - puppeteer/dashboard/src/components/__tests__/ThemeToggle.test.tsx
    - puppeteer/dashboard/src/__tests__/theme.integration.test.ts
    - puppeteer/dashboard/src/ThemeProvider.test.tsx
  modified:
    - mop_validation/scripts/test_playwright.py
decisions:
  - Structured all tests in RED (failing) state per TDD methodology to define expected behavior upfront
  - Split test coverage into unit (useTheme hook), component (ThemeToggle), integration (CSS variables), context (ThemeProvider), and E2E (Playwright)
  - Tests verify localStorage persistence with key 'mop_theme' (dark|light values)
  - Tests verify DOM class updates to document.documentElement for .dark class management
  - FOWT prevention tested via inline script that runs before React hydration
  - Tests include accessibility checks (aria-labels), hydration safety (mounted state), and SSR compatibility (undefined window)
metrics:
  tasks_completed: 5
  tests_created: 28
  test_files: 5
  test_summary:
    - useTheme unit tests: 7 tests
    - ThemeToggle component tests: 7 tests
    - Theme CSS integration tests: 9 tests
    - ThemeProvider context tests: 5 tests
    - Playwright E2E tests: 1 comprehensive test (Test 9 in suite)
  duration_minutes: 15
  completion_time: "2026-04-02T22:45:00Z"
---

# Phase 117, Plan 00: Wave 0 Test Infrastructure

**Objective:** Establish comprehensive test coverage for the light/dark theme infrastructure BEFORE implementation begins. This wave creates unit tests, component tests, integration tests, and E2E tests that subsequent waves (01-03) will reference in their verify sections.

**Status:** COMPLETE

## Summary

Wave 0 successfully created 28 unit, component, integration, and E2E test cases across five test files. All tests are in RED (failing) state per TDD methodology, defining expected behavior for the light/dark theme system. These tests establish the foundation for Waves 1-3 implementation and prevent FOWT (Flash of Wrong Theme) bugs, localStorage edge cases, and CSS variable scoping issues.

## Completed Tasks

### Task 1: Unit Tests for useTheme Hook
**File:** `puppeteer/dashboard/src/hooks/__tests__/useTheme.test.ts`
**Status:** ✓ Created (RED)
**Tests:** 7 test cases
- Default theme defaults to 'dark' when localStorage empty
- Reads stored theme from localStorage.getItem('mop_theme') on init
- setTheme() updates state immediately
- setTheme() persists to localStorage
- setTheme() updates document.documentElement.classList (add/remove 'dark')
- Multiple rapid setTheme() calls update DOM correctly
- SSR safety: defaults to 'dark' when window undefined

**Commit:** 4e9a92d

### Task 2: Component Tests for ThemeToggle
**File:** `puppeteer/dashboard/src/components/__tests__/ThemeToggle.test.tsx`
**Status:** ✓ Created (RED)
**Tests:** 7 test cases
- Component renders sun and moon icons
- Component visible and accessible
- Toggles to light mode when clicked in dark mode
- Toggles to dark mode when clicked in light mode
- Has aria-label for accessibility
- Hydration safety (mounted state prevents mismatch)
- Icons rotate 180° when theme changes

**Commit:** 8b46bfc

### Task 3: Integration Tests for CSS Variables
**File:** `puppeteer/dashboard/src/__tests__/theme.integration.test.ts`
**Status:** ✓ Created (RED)
**Tests:** 9 test cases
- Light mode CSS variables in :root scope
- Dark mode CSS variables in .dark scope
- Light background color applied in light mode
- Dark background color applied in dark mode
- Primary color unchanged in both themes
- Status badge colors defined (success, error, warning)
- Shadow CSS variables defined
- Different text colors based on theme
- Focus ring color defined (pink in both modes)

**Commit:** 6f1e525

### Task 4: Context Provider Tests
**File:** `puppeteer/dashboard/src/ThemeProvider.test.tsx`
**Status:** ✓ Created (RED)
**Tests:** 5 test cases
- ThemeProvider wraps children without crashing
- useTheme hook receives theme context inside provider
- Hydration matches localStorage on first render
- Multiple children can consume same context
- Theme state syncs across multiple consumers

**Commit:** 9092b92

### Task 5: Playwright E2E Tests
**File:** `mop_validation/scripts/test_playwright.py` (modified)
**Status:** ✓ Created (RED)
**Tests:** Added Test 9 comprehensive E2E test
- FOWT prevention: inline script prevents flash on reload
- Theme toggle visible in sidebar footer after login
- Clicking toggle switches between light/dark modes
- Theme persists to localStorage on toggle
- Page reload restores last selected theme (no flash)
- Light mode colors render correctly
- Dark mode remains unchanged (no regressions)
- Login page always stays dark

**Commit:** a06868a (mop_validation repo)

## Deviations from Plan

None — plan executed exactly as written. All tests created in RED state, ready for Wave 1-3 implementation.

## Architecture Insights

### Test Organization
- **Unit tests** (`useTheme.test.ts`): Hook logic, state management, localStorage sync
- **Component tests** (`ThemeToggle.test.tsx`): UI rendering, click handlers, hydration safety
- **Integration tests** (`theme.integration.test.ts`): CSS variables, light/dark scoping, computed styles
- **Context tests** (`ThemeProvider.test.tsx`): Provider hydration, context injection
- **E2E tests** (`test_playwright.py`): Full user workflow, persistence, FOWT prevention

### Key Design Decisions Captured in Tests
1. **localStorage key:** `mop_theme` with values `'dark'` | `'light'`
2. **DOM class:** `.dark` class on `document.documentElement` (Tailwind convention)
3. **Default:** Always dark on first visit (no OS `prefers-color-scheme`)
4. **FOWT prevention:** Inline script in index.html reads localStorage before React hydrates
5. **Theme toggle placement:** Sidebar footer (post-authentication only)
6. **Brand identity:** Pink primary color stays unchanged across both modes
7. **CSS variables:** Scoped to `:root` (light) and `.dark` (dark overrides)
8. **Accessibility:** aria-labels required on toggle button
9. **Hydration safety:** Component checks `mounted` state to prevent mismatches
10. **Multi-consumer pattern:** ThemeProvider must support multiple `useTheme()` consumers

## Wave References

These tests are explicitly referenced in Wave 1-3 verify sections:

- **Wave 1-01:** CSS variables and index.html FOWT script
  - References: `theme.integration.test.ts` (CSS variables), `test_playwright.py` FOWT test
- **Wave 1-02:** useTheme hook + ThemeProvider context
  - References: `useTheme.test.ts`, `ThemeProvider.test.tsx`
- **Wave 1-03:** ThemeToggle component + UI integration
  - References: `ThemeToggle.test.tsx`, `test_playwright.py` toggle test

## Next Steps

Wave 1-01 (CSS Variables & FOWT Prevention) will implement the infrastructure to make these tests pass. Implementation follows TDD GREEN phase: write minimal code to pass all 28 tests, then REFACTOR for code quality.

## Self-Check: PASSED

✓ All 5 test files created
✓ Total 28 test cases across all files
✓ Tests in RED state (failing) — ready for implementation
✓ Test naming matches Wave 1-3 verify references
✓ No implementation code written (TDD RED phase only)
✓ All commits created with proper format

---

*Execution completed: 2026-04-02 22:45:00Z*
*Plan type: TDD Wave 0 Test Infrastructure*
*Next plan: 117-01-PLAN.md (Wave 1-01: CSS Variables & FOWT Prevention)*
