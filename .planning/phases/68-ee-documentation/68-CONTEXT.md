# Phase 68: EE Documentation - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand the EE getting-started section in `install.md` and add `GET /api/features` verification to `licensing.md`. Both success criteria are targeted fixes: no `/api/admin/features` references anywhere, and `AXIOM_LICENCE_KEY` used consistently (already satisfied — protect by not introducing the wrong variants). No new pages, no new capabilities.

</domain>

<decisions>
## Implementation Decisions

### EE page location
- Expand the existing "Enterprise Edition" section in `install.md` — no standalone `ee-install.md`
- The section stays at the end of `install.md`, after Step 4 (verify stack is up)

### EE section content
- **Key setting**: keep existing `AXIOM_LICENCE_KEY` env var block
- **Feature list**: add a list of EE feature flags as they appear in the API response: `foundry`, `rbac`, `webhooks`, `triggers`, `audit`
- **Verification step**: add a tab pair (Dashboard / CLI) showing how to confirm EE is active
  - **Dashboard tab**: point to the CE/EE badge in the sidebar — it flips to EE when the key is valid
  - **CLI tab**: full self-contained block — inline token acquisition (`TOKEN=$(curl login...)`) then `curl /api/features` with the token
- **Expected output**: show the full JSON response with all keys `true` so operators know exactly what success looks like

### Verification endpoint
- Use `GET /api/features` exclusively — never `GET /api/admin/features`
- EEDOC-01 is satisfied by always using the correct endpoint from the start

### licensing.md changes
- Add `GET /api/features` example to the existing "Checking your licence" section, alongside `GET /api/licence`
- Show the full response: `{"foundry": true, "rbac": true, "webhooks": true, "triggers": true, "audit": true}`
- `AXIOM_LICENCE_KEY` naming already correct throughout — no renames needed (EEDOC-02 already satisfied)

### Claude's Discretion
- Exact curl command formatting and flag choices
- Tab ordering within the verification step (Dashboard first per Phase 67 convention)
- Whether to add a "failure" example (key missing or expired) to the CLI tab

</decisions>

<specifics>
## Specific Ideas

- Feature flags in the list should match the exact API keys: `foundry`, `rbac`, `webhooks`, `triggers`, `audit` — not human-readable variants
- The dashboard tab in the verification step just needs to identify where the badge is (sidebar) — no screenshot needed
- licensing.md gets `GET /api/features` added to the existing "Checking your licence" section, not a new section

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pymdownx.tabbed` already configured in `mkdocs.yml` (Phase 67) — tab pairs work with `=== "Dashboard"` / `=== "CLI"` syntax
- Phase 67 established **Dashboard first** tab ordering convention — follow it here

### Established Patterns
- Getting-started guides use Dashboard-first tab pairs (Phase 67 decision)
- CLI curl blocks include inline token acquisition where self-contained blocks are needed (see `enroll-node.md` CLI tab)
- `!!! note` admonitions used for "what success looks like" clarifications

### Integration Points
- `install.md` EE section is the last section before the "Next" footer link
- `licensing.md` "Checking your licence" section currently has only `GET /api/licence` — append `GET /api/features` below it

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 68-ee-documentation*
*Context gathered: 2026-03-26*
