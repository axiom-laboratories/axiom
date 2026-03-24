# Phase 59: Documentation - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Update the Axiom docs site to accurately reflect the v12.0 feature set, align it visually with the dashboard, create a complete `.env.example` for new operators, and add a dedicated "Running with Docker" deployment page. No new features — documentation and branding updates only.

</domain>

<decisions>
## Implementation Decisions

### .env.example
- Lives at repo root (replacing the outdated existing file)
- Covers puppeteer service only — node env vars are per-node and set in node-compose.yaml
- Grouped sections with `# === Section ===` headers: Required / Database / Optional / Tunnel
- Required vars are uncommented with empty values + a generation command in the comment
- Optional vars are commented-out with `#` to show format without accidentally being used
- Use correct key names: `SECRET_KEY` (not `JWT_SECRET`), `DATABASE_URL` (not `DB_PASSWORD`)
- Include all production vars: `SECRET_KEY`, `ENCRYPTION_KEY`, `API_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`, `CLOUDFLARE_TUNNEL_TOKEN`

### Docker deployment section (DOCS-02)
- New standalone page: `docs/docs/getting-started/docker-deployment.md`
- Added to nav under Getting Started, after Install (Prerequisites → Install → Running with Docker → Enroll a Node)
- Covers all four gap areas:
  1. PostgreSQL / DATABASE_URL setup (connection string, docker-compose postgres service)
  2. Production readiness checklist (secret generation, key rotation, HTTPS/TLS)
  3. Optional service toggles (Foundry, Webhooks, CE vs EE mode)
  4. Upgrade / re-deploy flow (rebuild image, apply migration SQL, roll-forward safely)

### Branding alignment (DOCS-03)
- Scope: Fira Sans font + primary color adjustment only (not a full theme override)
- Add `@import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap')` to `docs/docs/stylesheets/extra.css`
- Override Material font vars to use Fira Sans for body and Fira Code for code
- Keep Material `slate` scheme — zinc-exact background override is too brittle against Material updates
- Add a simple geometric icon SVG (network node / cube motif) as the docs nav logo
- SVG lives at `docs/docs/assets/logo.svg`, referenced in `mkdocs.yml` via `logo:` key

### v12.0 content updates (DOCS-04)
- Strategy: new sections within existing feature guide pages (not new top-level pages)
- Old task type references (`python_script`, `bash_script`, `powershell_script`) replaced throughout — no migration callout note needed
- All references updated to unified `script` task type with runtime selector (Python / Bash / PowerShell)

**Specific content additions:**
- **Jobs feature guide** (`feature-guides/jobs.md` — create if missing): Add sections for:
  - Guided dispatch form (selecting runtime, target node/tags, capability requirements)
  - Advanced (JSON) dispatch mode toggle
  - Bulk operations (cancel/resubmit/delete selected jobs)
  - DRAFT lifecycle: new jobs start as DRAFT, must be published before nodes receive them
  - Queue view: new section covering live WebSocket job visibility, per-node drawer, DRAINING node state
- **Scheduling feature guide** (`feature-guides/job-scheduling.md`): Add sections for:
  - Scheduling Health view (fire logs, LATE/MISSED detection)
  - Retention config (how long job history is kept, where to configure)
- **Nodes feature guide** (`feature-guides/nodes.md` — create if missing or expand existing): Add:
  - DRAINING node state (what it means, how to set it, how it affects job assignment)
  - Cross-link from Queue view section in Jobs guide

### Claude's Discretion
- Exact prose and depth of each new section
- Whether to create a `feature-guides/jobs.md` as a new file or expand existing Jobs runbook
- SVG logo design details (geometric motif, exact proportions)
- Which specific UI label renames to call out (research current dashboard labels vs old names)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/docs/stylesheets/extra.css`: Already has enterprise admonition styles — add font + color overrides here, don't create a new file
- `docs/mkdocs.yml`: Full nav already structured — insert new pages and logo reference here
- `docs/docs/feature-guides/job-scheduling.md`: Already documents DRAFT lifecycle — extend with Scheduling Health and retention sections
- `docs/docs/feature-guides/axiom-push.md`: References DRAFT workflow — consistent with decisions above
- `docs/docs/feature-guides/foundry.md`: References guided form toggle — consistent terminology to reuse

### Established Patterns
- Material `slate` scheme + `indigo` primary is set in mkdocs.yml — adjust primary hex value in extra.css rather than changing mkdocs.yml scheme
- Admonition boxes (`!!! warning`, `!!! danger`, `!!! enterprise`) used throughout — use same pattern for new content
- All pages use `---` horizontal rules between major sections — maintain this style

### Integration Points
- `docs/mkdocs.yml` nav: insert `Running with Docker: getting-started/docker-deployment.md` between Install and Enroll a Node
- `docs/docs/getting-started/install.md`: References `secrets.env` — the new `.env.example` and Docker deployment page should cross-reference this file
- `docs/Dockerfile`: Runs `mkdocs build --strict` — any new pages added to nav must have corresponding files, or the build fails

</code_context>

<specifics>
## Specific Ideas

- `.env.example` grouped sections format: `# === Required ===`, `# === Database ===`, `# === Tunnel ===`, `# === Optional ===`
- Generation commands included as comments above each cryptographic key var
- Queue view section in Jobs guide — covers live WebSocket updates and per-node drawer
- DRAINING state documented alongside Queue view (cross-link from Nodes guide)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 59-documentation*
*Context gathered: 2026-03-24*
