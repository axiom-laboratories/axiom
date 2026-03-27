# Phase 81: Homepage enterprise messaging — SSO narrative, compliance framing, and conversion optimisation - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance the existing `homepage/index.html` and `homepage/style.css` (produced in Phase 80) to strengthen enterprise messaging: expand the SSO feature line, add a new compliance/security posture section, and fix the enterprise conversion path. The page structure, dark theme (slate + indigo), Fira Sans/Code fonts, and CE/EE two-column card layout are fixed baseline — this phase adds to them, not replaces them.

</domain>

<decisions>
## Implementation Decisions

### Enterprise CTA / conversion path
- The "Register your interest" button (and the "Enterprise" nav link) should open a Google Form in a new tab
- Form fields: Name, Work email, Company, Use case / message
- A Google Form URL placeholder should be inserted — user will create the form separately and swap in the real URL
- The broken self-referencing anchor (`href="#enterprise-interest"` pointing to its own section) must be fixed

### SSO narrative
- Keep SSO as an enhanced EE feature line only — no dedicated section (SSO isn't shipped, a section would overclaim)
- Update the current vague "Organisation SSO readiness" line to: "SAML 2.0 / OIDC SSO integration" or similar specific phrasing
- No named IdPs — generic SAML 2.0 / OIDC framing only

### Compliance / security posture section
- Add a new section between the pain-points section and the CE/EE editions section
- Section headline: "Security that satisfies your infosec team"
- No certification claims — security posture framing only (honest for pre-certification product)
- Four capabilities to highlight:
  1. Cryptographic audit trail — every job execution is attributable and verifiable (Ed25519 signatures + audit log)
  2. Least-privilege RBAC — admin, operator, viewer roles; no shared accounts
  3. Air-gapped / on-premise deployment — no data leaves your network; fully self-hosted
  4. Certificate-based node identity — each node has a unique mTLS cert; revocation is cryptographic, not password-based

### Enterprise edition tone
- Replace "Coming soon" badge on the EE card with "Early access"
- Add one sentence above the EE feature list (hybrid approach): something like "Built with early design partners — shaped by real enterprise deployments."
- Dual-CTA button text: change from "Register your interest →" to "Get early access →"
- Nav "Enterprise" button and the EE card link should both point to the Google Form (new tab)

### Claude's Discretion
- Exact copy for the security posture section prose and capability descriptions — must stay factual, no puffery
- Visual treatment of the new security section (icon row, card grid, or prose with callout boxes) — should match the existing pain-points card grid style for consistency
- Exact badge colour/styling for "Early access" — should be distinct from both the green "Free" badge and the previous amber "Coming soon"

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `homepage/index.html`: Baseline from Phase 80. Key sections to modify:
  - `<section class="section section-alt">` (CE/EE editions) — insert new security section before this
  - `.card.card-ee` — update badge text, add intro sentence above feature list
  - `#enterprise-interest` dual-CTA block — fix the broken anchor, update button text and href
  - `.btn-nav-enterprise` in nav — update href to Google Form URL (placeholder)
- `homepage/style.css`: All styling lives here. New section should reuse `.section`, `.section-label`, `.pain-grid`/`.pain-card` patterns (or create `.security-grid`/`.security-card` in the same style).

### Established Patterns
- Pain-points section uses: `.pain-card` with `.pain-icon` (emoji), `<h3>`, `<p>` — new security capability cards should follow the same structure
- `.section-label` (small all-caps eyebrow text above h2) — use for "Enterprise-grade security" eyebrow in new section
- `.badge` pattern: `.badge-free` (green) and `.badge-coming-soon` (existing) — add `.badge-early-access` in a distinct colour (e.g. indigo or teal)

### Integration Points
- `homepage-deploy.yml` workflow: triggers on `homepage/**` changes — no workflow changes needed for this phase
- No JS in the current homepage — Google Form link is a plain `<a target="_blank">`, no JS required

</code_context>

<specifics>
## Specific Ideas

- The Google Form placeholder should be a clearly marked TODO comment in the HTML: `<!-- TODO: replace with real Google Form URL -->` so it's easy to find and swap
- The "Get early access" button in the dual-CTA section should be the primary action; the install guide link is the secondary action — button hierarchy should reflect this
- The new security section should feel like a trust signal, not a feature list — prose or icon cards, not bullet points

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 81-homepage-enterprise-messaging-sso-narrative-compliance-framing-and-conversion-optimisation*
*Context gathered: 2026-03-27*
