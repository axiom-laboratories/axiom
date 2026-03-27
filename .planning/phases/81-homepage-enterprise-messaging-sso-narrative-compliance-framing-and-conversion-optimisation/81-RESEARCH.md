# Phase 81: Homepage Enterprise Messaging — Research

**Researched:** 2026-03-27
**Domain:** Static HTML/CSS — marketing homepage content editing
**Confidence:** HIGH

## Summary

Phase 81 is a focused content and styling pass on two static files: `homepage/index.html` and `homepage/style.css`. No new libraries, no build tooling, no JavaScript, and no workflow changes are required. The Phase 80 baseline is the full context — every pattern needed already exists in those two files.

The work divides into four discrete areas: (1) fix the broken enterprise CTA anchor and replace it with a real Google Form link; (2) upgrade the SSO feature line to specific protocol names; (3) add a new "Security that satisfies your infosec team" section between pain-points and editions; (4) update the EE card badge and copy to reflect early-access framing.

**Primary recommendation:** Make all changes directly in `homepage/index.html` and `homepage/style.css`. Add only one new CSS component (`.security-grid` / `.security-card`) modelled verbatim on `.pain-grid` / `.pain-card`. No other files need to change. Pushing to `main` triggers the `gh-pages-deploy` workflow automatically.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Enterprise CTA / conversion path**
- The "Register your interest" button (and the "Enterprise" nav link) should open a Google Form in a new tab
- Form fields: Name, Work email, Company, Use case / message
- A Google Form URL placeholder should be inserted — user will create the form separately and swap in the real URL
- The broken self-referencing anchor (`href="#enterprise-interest"` pointing to its own section) must be fixed

**SSO narrative**
- Keep SSO as an enhanced EE feature line only — no dedicated section (SSO isn't shipped, a section would overclaim)
- Update the current vague "Organisation SSO readiness" line to: "SAML 2.0 / OIDC SSO integration" or similar specific phrasing
- No named IdPs — generic SAML 2.0 / OIDC framing only

**Compliance / security posture section**
- Add a new section between the pain-points section and the CE/EE editions section
- Section headline: "Security that satisfies your infosec team"
- No certification claims — security posture framing only (honest for pre-certification product)
- Four capabilities to highlight:
  1. Cryptographic audit trail — every job execution is attributable and verifiable (Ed25519 signatures + audit log)
  2. Least-privilege RBAC — admin, operator, viewer roles; no shared accounts
  3. Air-gapped / on-premise deployment — no data leaves your network; fully self-hosted
  4. Certificate-based node identity — each node has a unique mTLS cert; revocation is cryptographic, not password-based

**Enterprise edition tone**
- Replace "Coming soon" badge on the EE card with "Early access"
- Add one sentence above the EE feature list (hybrid approach): "Built with early design partners — shaped by real enterprise deployments."
- Dual-CTA button text: change from "Register your interest →" to "Get early access →"
- Nav "Enterprise" button and the EE card link should both point to the Google Form (new tab)

### Claude's Discretion
- Exact copy for the security posture section prose and capability descriptions — must stay factual, no puffery
- Visual treatment of the new security section (icon row, card grid, or prose with callout boxes) — should match the existing pain-points card grid style for consistency
- Exact badge colour/styling for "Early access" — should be distinct from both the green "Free" badge and the previous amber "Coming soon"

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Standard Stack

### Core (already present — no new installs)
| Asset | What it is | Role in this phase |
|-------|-----------|-------------------|
| `homepage/index.html` | Plain HTML5 | All content changes happen here |
| `homepage/style.css` | Plain CSS3 with custom properties | All style changes happen here |
| `gh-pages-deploy.yml` | GitHub Actions workflow | Deploys both files to gh-pages root on push to `main` — no changes needed |

### No new dependencies
This phase adds zero JavaScript, zero npm packages, zero Python packages, and zero new workflow steps. Everything is vanilla HTML + CSS.

---

## Architecture Patterns

### Existing File Structure
```
homepage/
├── index.html   # Full page markup — all sections in one file
└── style.css    # All styles — custom properties at :root, no imports
```

### Page Section Order (current → target)
```
current:
  nav → hero → mockup → pain-points → editions → dual-cta → footer

target (this phase inserts one section):
  nav → hero → mockup → pain-points → [security posture] → editions → dual-cta → footer
```

### Pattern 1: Pain-card grid (reuse for security section)
The pain-points section (`<section class="section">`) uses a `.pain-grid` / `.pain-card` / `.pain-icon` / `h3` / `p` structure. The security section must follow the same structure using class names `.security-grid` / `.security-card` so styles can be written as a thin override or copy of `.pain-grid`.

**HTML structure to replicate:**
```html
<!-- Source: homepage/index.html lines 81-103 -->
<section class="section">
  <div class="container">
    <p class="section-label">Enterprise-grade security</p>
    <h2>Security that satisfies your infosec team</h2>
    <div class="security-grid">
      <div class="security-card">
        <span class="pain-icon">🔏</span>
        <h3>Cryptographic audit trail</h3>
        <p>Every job execution is Ed25519-signed and logged. You know who ran what, and you can prove it.</p>
      </div>
      <!-- ...three more cards -->
    </div>
  </div>
</section>
```

**CSS to add (mirrors `.pain-grid` / `.pain-card` exactly):**
```css
/* Source: homepage/style.css lines 485-514 — replicate pattern */
.security-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin-top: 2rem;
}

.security-card {
  background-color: var(--axiom-surface);
  border: 1px solid var(--axiom-border);
  border-radius: var(--radius);
  padding: 1.25rem;
}

.security-card h3 {
  font-size: 1rem;
  margin-bottom: 0.4rem;
}

.security-card p {
  font-size: 0.875rem;
  color: var(--axiom-text-muted);
  line-height: 1.55;
}

/* Responsive: collapse to 1 column on mobile */
@media (max-width: 640px) {
  .security-grid {
    grid-template-columns: 1fr;
  }
}
```

Note: 4-column grid because there are exactly 4 capability cards. The pain-points section uses 3 columns. At 960px max-width and 1.25rem gaps, four 1fr columns gives ~220px per card — tight but workable. If it looks cramped, fall back to a 2×2 grid: `grid-template-columns: repeat(2, 1fr)`.

### Pattern 2: Badge — `.badge-early-access`
Current badge colours:
- `.badge-free`: green (`#3fb950`, rgba green background)
- `.badge-coming-soon`: crimson/primary (`var(--axiom-primary)`)

"Early access" should be distinct from both. Indigo/violet is the natural fit for a dark-slate dark theme — it reads as "active but pre-GA". The theme already uses indigo in the docs (MkDocs Material slate with indigo accent).

```css
/* Source: design decision — Claude's discretion per CONTEXT.md */
.badge-early-access {
  background-color: rgba(99, 102, 241, 0.15);   /* indigo-500 at low opacity */
  color: #818cf8;                                 /* indigo-400 — readable on dark bg */
  border: 1px solid rgba(99, 102, 241, 0.4);
}
```

This uses indigo-400/500 values from Tailwind's palette — a reliable reference point for a harmonious dark-theme colour. The pattern mirrors `.badge-free` and `.badge-coming-soon` exactly (rgba background, solid colour text, rgba border).

### Pattern 3: Google Form link — plain anchor with `target="_blank"`
No JS required. Both the nav button and the dual-CTA button are plain `<a>` tags. Change `href` to the placeholder URL and add `target="_blank" rel="noopener noreferrer"`.

```html
<!-- Nav Enterprise button -->
<a href="GOOGLE_FORM_URL_PLACEHOLDER" target="_blank" rel="noopener noreferrer" class="btn-nav-enterprise">Enterprise</a>

<!-- Dual-CTA primary button -->
<a href="GOOGLE_FORM_URL_PLACEHOLDER" target="_blank" rel="noopener noreferrer" class="btn btn-primary">Get early access &rarr;</a>

<!-- EE card internal link -->
<a href="GOOGLE_FORM_URL_PLACEHOLDER" target="_blank" rel="noopener noreferrer">Get in touch &rarr;</a>
```

The TODO comment placement:
```html
<!-- TODO: replace GOOGLE_FORM_URL_PLACEHOLDER with real Google Form URL -->
```
Place this comment once, immediately above the nav `<a>` tag, so the user finds it immediately when searching for "TODO".

### Anti-Patterns to Avoid
- **Anchor pointing to itself:** The current `href="#enterprise-interest"` in the dual-CTA block is the bug to fix — the section IS `#enterprise-interest`, so clicking the button scrolls nowhere. Replace the `href` with the Google Form URL.
- **Adding a dedicated SSO section:** Explicitly out of scope per locked decisions — SSO is an EE feature line only.
- **Certification language:** No SOC 2, ISO 27001, or GDPR compliance claims — security posture framing only.
- **Named IdPs:** No "Okta", "Azure AD", "Google Workspace" — "SAML 2.0 / OIDC SSO integration" only.
- **Overclaiming on EE:** "Early access" not "Generally available" — EE is in design-partner stage.
- **Modifying the workflow:** `gh-pages-deploy.yml` is correct and needs no changes for this phase.
- **Changing the dimmed feature list:** The EE feature list currently uses `.feature-list--dimmed` (faint text). With "Early access" framing replacing "Coming soon", the dimming may feel inconsistent — consider removing `--dimmed` modifier. This is Claude's discretion.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Colour for indigo badge | Custom colour picker exploration | Tailwind indigo-400/500 values (proven dark-theme readable) |
| New section layout | Novel CSS grid | Copy `.pain-grid` layout exactly, rename classes |
| External link handling | JS click handler | `target="_blank" rel="noopener noreferrer"` on the `<a>` tag |
| Google Form embed | Inline iframe | External link — user fills form in new tab, no embed needed |

---

## Common Pitfalls

### Pitfall 1: Broken anchor not fully fixed
**What goes wrong:** Developer fixes the dual-CTA button anchor but misses the `href="#enterprise-interest"` in the EE card `.ee-interest` block (line 141 in the current HTML). Three separate anchor references point to `#enterprise-interest` — all must be updated.
**Current occurrences:**
1. Nav: `<a href="#enterprise-interest" class="btn-nav-enterprise">` (line 21)
2. Hero secondary CTA: `<a href="#enterprise-interest" class="btn btn-secondary">` (line 37)
3. EE card internal link: `<a href="#enterprise-interest">` (line 141)
4. Dual-CTA primary button: `<a href="#enterprise-interest" class="btn btn-primary">` (line 168)

Items 1, 3, and 4 should point to the Google Form (new tab). Item 2 (hero "Talk to us about Enterprise") should also point to the Google Form — it's the same conversion intent.
**How to avoid:** Search for `#enterprise-interest` in the HTML file — there are 4 occurrences. Fix all four.

### Pitfall 2: `feature-list--dimmed` left on EE feature list
**What goes wrong:** "Early access" framing implies the features exist and are accessible to design partners. Keeping `.feature-list--dimmed` (near-invisible faint text) contradicts this — it reads as "not available yet".
**How to avoid:** Remove the `--dimmed` modifier from the EE feature list `<ul>` when updating the badge. The base `.feature-list` styling uses `var(--axiom-text-muted)` which is readable but not dominant.

### Pitfall 3: Section background alternation breaks
**What goes wrong:** The current alternation is: section (dark bg) → section-alt (surface bg) → section (dark bg). Inserting a new section before `section-alt` will create two consecutive dark sections.
**How to avoid:** The new security section should use `.section section-alt` (the surface background) to preserve the visual rhythm:
- Pain-points: `.section` (dark `--axiom-bg`)
- Security posture: `.section section-alt` (light `--axiom-surface`)
- Editions: `.section section-alt` (light `--axiom-surface`) — this becomes two consecutive `section-alt` rows

Actually, either arrangement works. The simplest approach: make the new security section plain `.section` (dark background) — this creates the rhythm: pain (dark) → security (dark) → editions (surface). That is slightly less ideal visually. Better: security section uses `.section section-alt`, editions keeps `.section section-alt`. Two consecutive surface sections is fine — the section border separates them clearly.

### Pitfall 4: 4-column grid too narrow on medium screens
**What goes wrong:** At 960px max-width with 4 columns and 1.25rem gaps, cards are ~220px wide. This works at desktop but collapses to nothing at ~700–800px before the 640px breakpoint fires.
**How to avoid:** Add a mid-size breakpoint or use a 2×2 grid from the start. Recommendation: use `grid-template-columns: repeat(2, 1fr)` for the security grid (4 cards in a 2×2 layout) — it's more readable at all sizes than 4 columns. This matches the 2-column edition-grid pattern already in the page.

---

## Code Examples

### Complete set of HTML changes (summary)

```html
<!-- 1. Nav Enterprise button — fix href, add target -->
<!-- Source: homepage/index.html line 21 -->
<a href="GOOGLE_FORM_URL_PLACEHOLDER" target="_blank" rel="noopener noreferrer" class="btn-nav-enterprise">Enterprise</a>

<!-- 2. Hero secondary CTA — fix href -->
<!-- Source: homepage/index.html line 37 -->
<a href="GOOGLE_FORM_URL_PLACEHOLDER" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">Talk to us about Enterprise</a>

<!-- 3. EE badge — replace Coming soon -->
<!-- Source: homepage/index.html line 128 -->
<span class="badge badge-early-access">Early access</span>

<!-- 4. EE intro sentence — replace card-intro -->
<!-- Source: homepage/index.html line 130 -->
<p class="card-intro">Built with early design partners — shaped by real enterprise deployments.</p>
<p class="card-intro">Everything in CE, plus:</p>

<!-- 5. SSO line update -->
<!-- Source: homepage/index.html line 138 -->
<li>SAML 2.0 / OIDC SSO integration</li>

<!-- 6. EE card internal link — fix href -->
<!-- Source: homepage/index.html line 141 -->
<a href="GOOGLE_FORM_URL_PLACEHOLDER" target="_blank" rel="noopener noreferrer">Get in touch →</a>

<!-- 7. Dual-CTA block — fix button text and href -->
<!-- Source: homepage/index.html lines 164-169 -->
<div class="dual-cta-block">
  <p class="section-label">Enterprise edition</p>
  <h3>Get early access to Enterprise?</h3>
  <p class="install-sub">We're working with design partners now. Tell us about your environment.</p>
  <a href="GOOGLE_FORM_URL_PLACEHOLDER" target="_blank" rel="noopener noreferrer" class="btn btn-primary">Get early access &rarr;</a>
</div>
```

### New security section (insert between pain-points and editions)

```html
<!-- Security posture section — insert after line 103, before line 105 -->
<section class="section section-alt">
  <div class="container">
    <p class="section-label">Enterprise-grade security</p>
    <h2>Security that satisfies your infosec team</h2>
    <div class="security-grid">
      <div class="security-card">
        <span class="pain-icon">🔏</span>
        <h3>Cryptographic audit trail</h3>
        <p>Every job execution is Ed25519-signed before it runs and logged with a full audit record. You know who ran what — and you can prove it.</p>
      </div>
      <div class="security-card">
        <span class="pain-icon">🛡️</span>
        <h3>Least-privilege RBAC</h3>
        <p>Three built-in roles: admin, operator, viewer. No shared accounts. Permissions are scoped and auditable from day one.</p>
      </div>
      <div class="security-card">
        <span class="pain-icon">🏢</span>
        <h3>Air-gapped deployment</h3>
        <p>Fully self-hosted. No telemetry, no cloud dependency, no data leaves your network. Runs on your infrastructure, under your control.</p>
      </div>
      <div class="security-card">
        <span class="pain-icon">🔐</span>
        <h3>Certificate-based node identity</h3>
        <p>Each node holds a unique mTLS client certificate. Revocation is cryptographic — not a password reset.</p>
      </div>
    </div>
  </div>
</section>
```

### New CSS additions

```css
/* Source: style decision — mirrors pain-grid pattern */

/* ----- Security posture grid ----- */
.security-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
  margin-top: 2rem;
}

.security-card {
  background-color: var(--axiom-bg);
  border: 1px solid var(--axiom-border);
  border-radius: var(--radius);
  padding: 1.25rem;
}

.security-card h3 {
  font-size: 1rem;
  margin-bottom: 0.4rem;
}

.security-card p {
  font-size: 0.875rem;
  color: var(--axiom-text-muted);
  line-height: 1.55;
}

/* ----- Early access badge ----- */
.badge-early-access {
  background-color: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  border: 1px solid rgba(99, 102, 241, 0.4);
}

/* Responsive addition (add inside existing @media max-width 640px block) */
.security-grid {
  grid-template-columns: 1fr;
}
```

Note on `.security-card` background: the security section uses `.section section-alt` (surface bg `#161b22`), so cards should use `var(--axiom-bg)` (`#0d1117`) for contrast — same as `.card` in the editions section. This mirrors how pain-cards use `var(--axiom-surface)` inside a plain `.section` (bg `#0d1117`).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None — static HTML/CSS, no test runner |
| Config file | N/A |
| Quick run command | Visual inspection in browser or `open homepage/index.html` |
| Full suite command | Push to `main` → GitHub Actions deploys → verify at `axiom-laboratories.github.io/axiom/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| (no formal IDs) | Google Form links open in new tab | manual | N/A — visual inspection | N/A |
| (no formal IDs) | "Early access" badge renders (indigo colour) | manual | N/A — visual inspection | N/A |
| (no formal IDs) | Security section appears between pain-points and editions | manual | N/A — visual inspection | N/A |
| (no formal IDs) | No `href="#enterprise-interest"` self-references remain | manual | `grep -n 'href="#enterprise-interest"' homepage/index.html` should return 0 lines | N/A |
| (no formal IDs) | SSO line reads "SAML 2.0 / OIDC" | manual | `grep -n 'SAML' homepage/index.html` should return 1 line | N/A |

### Sampling Rate
- **Per change:** Open `homepage/index.html` directly in a browser (file://) — all styling and layout is visible without a server
- **Phase gate:** Push to `main`, verify deployed page at `axiom-laboratories.github.io/axiom/` before marking complete

### Wave 0 Gaps
None — this phase has no automated tests. All verification is visual inspection + one `grep` sanity check.

---

## Open Questions

1. **Hero secondary CTA — update or leave?**
   - What we know: "Talk to us about Enterprise" (line 37) also links to `#enterprise-interest`. Logically it should go to the Google Form.
   - What's unclear: The CONTEXT.md locked decisions call out the nav button and the dual-CTA button explicitly, but not the hero secondary CTA.
   - Recommendation: Update it to the Google Form URL as well — it has the same conversion intent. If the user disagrees, it can be pointed at the security section anchor (`#security`) instead.

2. **EE feature list dimming — remove `.feature-list--dimmed`?**
   - What we know: "Coming soon" used faint text to signal unavailability. "Early access" signals active availability to design partners.
   - What's unclear: The CONTEXT.md doesn't explicitly address this class.
   - Recommendation: Remove `--dimmed` when changing the badge. Use standard `.feature-list` muted text (readable). If desired, the EE card border (already crimson) provides sufficient visual distinction.

3. **`card-intro` structure — one or two paragraphs?**
   - The current `.card-intro` says "Everything in CE, plus:". The decision adds a new sentence above it.
   - Recommendation: Two separate `<p class="card-intro">` tags (or one with `<br>`) — keep the "Everything in CE" line as-is so the feature list still has its intro label.

---

## Sources

### Primary (HIGH confidence)
- `homepage/index.html` (read directly) — full baseline markup, all existing anchors and class names catalogued
- `homepage/style.css` (read directly) — full CSS, all existing custom properties, badge colours, grid patterns
- `.github/workflows/gh-pages-deploy.yml` (read directly) — confirms no workflow changes needed, paths trigger correctly
- `.planning/phases/81-.../81-CONTEXT.md` (read directly) — all locked decisions

### Secondary (MEDIUM confidence)
- Tailwind CSS colour palette (indigo-400: `#818cf8`, indigo-500: `#6366f1`) — used for badge colour recommendation; these are well-established values for dark-theme indigo rendering

### Tertiary (LOW confidence — not needed for this phase)
- None required. All research is grounded in direct code inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; files read directly
- Architecture: HIGH — patterns copied verbatim from existing code in same files
- Pitfalls: HIGH — derived from direct inspection of the HTML (anchor count, CSS class structure)
- Colour choices: MEDIUM — indigo palette is industry-standard for dark themes, but visual outcome depends on rendering

**Research date:** 2026-03-27
**Valid until:** No expiry — static files, no dependency versions to track
