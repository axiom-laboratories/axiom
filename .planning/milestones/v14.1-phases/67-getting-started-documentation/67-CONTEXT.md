# Phase 67: Getting-Started Documentation - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 11 specific known issues in the getting-started documentation: `install.md`, `enroll-node.md`, `first-job.md`, and `mkdocs.yml`. Requirements DOCS-01 through DOCS-11 are pre-defined — this phase is targeted doc surgery, not greenfield writing. No new capabilities are added.

Sub-order locked: `mkdocs.yml` → `install.md` → `enroll-node.md` → `first-job.md`

</domain>

<decisions>
## Implementation Decisions

### Tab structure (pymdownx.tabbed)
- Add `pymdownx.tabbed: alternate_style: true` to `mkdocs.yml` first, before touching any guide
- Tab labels: **Dashboard** / **CLI** throughout (not UI/API or Browser/Terminal)
- Tab order: **Dashboard first** in every tab pair — getting-started guides are UI-first; CLI is the power-user alternative
- Four steps get CLI/Dashboard tab pairs:
  1. `install.md` Step 1 — Git Clone vs GHCR Pull
  2. `install.md` Step 2 — Server install (secrets.env) vs Cold-start install (.env)
  3. `enroll-node.md` Step 1 — Dashboard token generation vs CLI curl path
  4. `enroll-node.md` Step 3 — Option A (curl installer) vs Option B (manual compose) become tabs
  5. `first-job.md` Step 4 — Dashboard form vs CLI dispatch (axiom-push + raw curl)

### Offline install path (DOCS-08)
- No tarball release asset — install is container-based, so GHCR pull is the correct "no git needed" path
- GHCR Pull tab in `install.md` Step 1: `curl` the raw `compose.server.yaml` from GitHub, then `docker compose pull` + `docker compose up -d`
- `docker compose pull` handles all service images including the docs container — no need to list individual images
- GHCR image: `ghcr.io/axiom-laboratories/axiom` (already published via release.yml on version tag)

### install.md password setup (DOCS-01)
- Step 2 becomes a tab pair splitting by install method:
  - **Server install tab**: existing `secrets.env` content with all variables (SECRET_KEY, ENCRYPTION_KEY, API_KEY, ADMIN_PASSWORD)
  - **Cold-start tab**: `.env` file with `ADMIN_PASSWORD=<value>` and `ENCRYPTION_KEY=...` only — minimal, explicit, placed before the compose up instruction

### AGENT_URL table (DOCS-06)
- Reorganise by **install method** (not OS):
  | Scenario | AGENT_URL |
  |----------|-----------|
  | Cold-start compose (node in same compose network) | `https://agent:8001` |
  | Server compose, node on same host | `https://puppeteer-agent-1:8001` |
  | Remote host / separate machine | `https://<hostname-or-ip>:8001` |
  | Docker Desktop (Mac or Windows) | `https://host.docker.internal:8001` |
- Remove `172.17.0.1` from the main table; keep as a fallback note: "If your node is on a custom Linux bridge network, find the gateway with `ip route | awk '/default/ {print $3}'`"

### enroll-node.md CLI token path (DOCS-03)
- Step 1 becomes a tab pair: **Dashboard** tab (existing click-through steps) vs **CLI** tab (curl login + curl generate-token)
- CLI tab is a full primary path, not a secondary callout — users choose at the start of the step

### enroll-node.md node install (Option A/B)
- Step 3 becomes a tab pair: **Option A: curl installer** vs **Option B: Docker Compose** (same content, just reorganised as tabs instead of sub-headings)
- Docker socket volume mount note (DOCS-07) stays in Option B tab

### enroll-node.md EXECUTION_MODE (DOCS-05)
- Replace any remaining `EXECUTION_MODE=direct` references with `EXECUTION_MODE=docker`
- Currently enroll-node.md already uses `docker` — verify no `direct` references remain after edits

### first-job.md CLI dispatch (DOCS-10)
- Step 4 becomes a tab pair: **Dashboard** (existing form walkthrough) vs **CLI**
- CLI tab primary command: `axiom-push job submit hello.py` (official CLI)
- Collapsible `??? example "Raw API"` block inside the CLI tab shows the equivalent minimal curl: script content + base64 sig + key_id only (no optional fields)
- Keeps the getting-started guide focused; full payload documented in API reference

### first-job.md key registration callout (DOCS-11)
- Add `!!! danger "Register your signing key first"` immediately before Step 4 (dispatch)
- References Steps 1–2 as prerequisites for dispatch
- Format matches the existing `!!! danger "Register before dispatching"` callout in Step 2 — consistent tone

### Claude's Discretion
- Exact wording of tab content (match existing doc tone — direct, imperative)
- Whether to split enroll-node.md AGENT_URL step as its own tab pair or keep as a table with the new structure
- Exact anchor names after any heading changes (run `mkdocs build --strict` after each file)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pymdownx.superfences` and `pymdownx.details` already in `mkdocs.yml` — tabbed extension slots in alongside these
- Existing `!!! danger`, `!!! warning`, `!!! tip`, `!!! note` admonitions throughout guides — new callouts should match this style
- `compose.server.yaml` already includes all services (agent, caddy, postgres, docs) — GHCR pull tab can reference it directly

### Established Patterns
- Guides use imperative numbered steps (Step 1, Step 2...) — maintain this in all tab content
- Code blocks use explicit language tags (`bash`, `yaml`) — keep consistent
- Cross-links use relative paths (`enroll-node.md`, `../feature-guides/axiom-push.md`) — don't break these with heading renames

### Integration Points
- `mkdocs.yml` must have `pymdownx.tabbed` before any `=== "Tab"` syntax is used in guides — do this in the first plan task
- `docs/docs/getting-started/` contains all four files being edited
- Pitfall: heading renames silently break anchor cross-references — run `mkdocs build --strict` after each file edit

</code_context>

<specifics>
## Specific Ideas

- "If we're using compose as our preferred install method, the GHCR pull should just use docker compose pull — one compose script should include all dependencies" — no need to list individual images
- GHCR pull tab is not a tarball alternative; it's the same compose-based install without needing git installed
- `axiom-push` should be the hero command in the CLI dispatch tab, with raw curl as a secondary reference — drives adoption of the official CLI from the first interaction

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 67-getting-started-documentation*
*Context gathered: 2026-03-26*
