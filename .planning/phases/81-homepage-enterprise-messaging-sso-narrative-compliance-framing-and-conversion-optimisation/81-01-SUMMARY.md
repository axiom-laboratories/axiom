---
phase: 81-homepage-enterprise-messaging-sso-narrative-compliance-framing-and-conversion-optimisation
plan: "01"
subsystem: ui
tags: [homepage, marketing, css, html, sso, enterprise, conversion]

requires: []
provides:
  - Security posture section with 4-card 2x2 grid (cryptographic audit, RBAC, air-gapped, mTLS identity)
  - Early-access EE card with indigo badge, design-partner intro, readable feature list, SAML 2.0/OIDC line
  - All enterprise CTAs pointing to GOOGLE_FORM_URL_PLACEHOLDER with target="_blank"
  - .security-grid, .security-card, .badge-early-access CSS classes
affects: [homepage-deploy, phase-80]

tech-stack:
  added: []
  patterns:
    - "Security section uses .section-alt + .security-grid (2-col) with .security-card using --axiom-bg for contrast against surface background"
    - "Enterprise CTAs use GOOGLE_FORM_URL_PLACEHOLDER sentinel value with TODO comment above nav link for easy URL swap"
    - "Early-access badge uses indigo palette (rgba 99,102,241) distinct from coming-soon crimson and free green"

key-files:
  created: []
  modified:
    - homepage/style.css
    - homepage/index.html

key-decisions:
  - "Security cards use var(--axiom-bg) background (not --axiom-surface) because the section itself uses .section-alt (surface bg) — cards need contrast"
  - "GOOGLE_FORM_URL_PLACEHOLDER used as sentinel (not empty href or # anchor) so broken links fail visibly until replaced"
  - "One TODO comment placed above nav link only — sufficient single marker for the URL swap"
  - "EE section retains .section-alt class (same as security section) creating back-to-back alt sections — acceptable for current page length"

patterns-established:
  - "Enterprise CTAs: href=GOOGLE_FORM_URL_PLACEHOLDER target=_blank rel=noopener noreferrer on all four touch points"

requirements-completed: []

duration: 3min
completed: "2026-03-28"
---

# Phase 81 Plan 01: Homepage Enterprise Messaging Summary

**Security posture section, SAML 2.0/OIDC SSO line, indigo early-access badge, and fixed enterprise CTA conversion path replacing broken self-referencing anchors**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-27T23:18:53Z
- **Completed:** 2026-03-28
- **Tasks:** 3 of 3
- **Files modified:** 2

## Accomplishments

- Added "Security that satisfies your infosec team" section with 4-card 2x2 grid positioned between pain-points and editions
- Updated EE card: indigo "Early access" badge, design-partner intro sentence, fully readable feature list, "SAML 2.0 / OIDC SSO integration" line
- Fixed all 4 self-referencing `#enterprise-interest` anchors — all enterprise CTAs now point to `GOOGLE_FORM_URL_PLACEHOLDER` with `target="_blank"`
- Updated dual-CTA enterprise block: "Get early access" headline with updated supporting copy
- Added `.security-grid`, `.security-card`, `.badge-early-access` CSS with responsive stacking at 640px

## Task Commits

Each task was committed atomically:

1. **Task 1: Add security grid and early-access badge CSS** - `c1263e2` (feat)
2. **Task 2: Update index.html — security section, EE card, and CTA anchor fixes** - `2c784ac` (feat)
3. **Task 3: Spacing fix — CE code snippet to CTA button** - `9539b8f` (fix)
4. **Task 3: Human-verify checkpoint** — approved by user

## Files Created/Modified

- `homepage/style.css` — Added .security-grid (2-col grid), .security-card, .badge-early-access (indigo), responsive .security-grid rule in @media block
- `homepage/index.html` — New security posture section, updated EE card (badge, intro, feature list, SSO), all enterprise CTAs fixed

## Decisions Made

- Security cards use `var(--axiom-bg)` (not `--axiom-surface`) because `.section-alt` already sets the section background to surface — cards need contrast
- `GOOGLE_FORM_URL_PLACEHOLDER` sentinel used instead of empty href so broken links are visually obvious before launch
- Single TODO comment placed above nav link — sufficient marker for URL replacement
- EE section retains `.section-alt` (same as new security section) — back-to-back alt sections are acceptable at current page length

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing spacing between CE code snippet and CTA button**
- **Found during:** Task 3 human-verify (user-reported)
- **Issue:** `pre` element was `display: inline-block` so `margin-bottom` had no effect in the inline formatting context; the docker-compose snippet butted directly against the "Read the install guide" link
- **Fix:** Added `.dual-cta-block pre { display: block; margin-bottom: 1.5rem; }` to scope the block display and margin to that context only
- **Files modified:** `homepage/style.css`
- **Commit:** `9539b8f`

## Issues Encountered

None.

## User Setup Required

Before launch: Replace all 4 instances of `GOOGLE_FORM_URL_PLACEHOLDER` in `homepage/index.html` with the real Google Form URL. The TODO comment on line 21 marks the first instance.

## Next Phase Readiness

- Homepage code changes complete — ready for deployment via Phase 80 homepage-deploy workflow
- One URL swap required before launch: `GOOGLE_FORM_URL_PLACEHOLDER` → real Google Form URL (5 occurrences in index.html)
- Human-verify checkpoint approved — plan fully complete

---
*Phase: 81-homepage-enterprise-messaging-sso-narrative-compliance-framing-and-conversion-optimisation*
*Completed: 2026-03-27*

## Self-Check: PASSED

- FOUND: homepage/style.css
- FOUND: homepage/index.html
- FOUND: c1263e2 (CSS task commit)
- FOUND: 2c784ac (HTML task commit)
- FOUND: 9539b8f (spacing fix commit)
- VERIFIED: zero href="#enterprise-interest" self-references
- VERIFIED: 5 GOOGLE_FORM_URL_PLACEHOLDER occurrences in index.html
- VERIFIED: .security-grid and .badge-early-access present in style.css
