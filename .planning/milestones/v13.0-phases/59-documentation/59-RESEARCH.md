# Phase 59: Documentation - Research

**Researched:** 2026-03-24
**Domain:** MkDocs Material docs site authoring, technical writing, CSS theming, env var documentation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**.env.example**
- Lives at repo root (replacing the outdated existing file)
- Covers puppeteer service only — node env vars are per-node and set in node-compose.yaml
- Grouped sections with `# === Section ===` headers: Required / Database / Optional / Tunnel
- Required vars are uncommented with empty values + a generation command in the comment
- Optional vars are commented-out with `#` to show format without accidentally being used
- Use correct key names: `SECRET_KEY` (not `JWT_SECRET`), `DATABASE_URL` (not `DB_PASSWORD`)
- Include all production vars: `SECRET_KEY`, `ENCRYPTION_KEY`, `API_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`, `CLOUDFLARE_TUNNEL_TOKEN`

**Docker deployment section (DOCS-02)**
- New standalone page: `docs/docs/getting-started/docker-deployment.md`
- Added to nav under Getting Started, after Install (Prerequisites → Install → Running with Docker → Enroll a Node)
- Covers all four gap areas:
  1. PostgreSQL / DATABASE_URL setup (connection string, docker-compose postgres service)
  2. Production readiness checklist (secret generation, key rotation, HTTPS/TLS)
  3. Optional service toggles (Foundry, Webhooks, CE vs EE mode)
  4. Upgrade / re-deploy flow (rebuild image, apply migration SQL, roll-forward safely)

**Branding alignment (DOCS-03)**
- Scope: Fira Sans font + primary color adjustment only (not a full theme override)
- Add `@import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap')` to `docs/docs/stylesheets/extra.css`
- Override Material font vars to use Fira Sans for body and Fira Code for code
- Keep Material `slate` scheme — zinc-exact background override is too brittle against Material updates
- Add a simple geometric icon SVG (network node / cube motif) as the docs nav logo
- SVG lives at `docs/docs/assets/logo.svg`, referenced in `mkdocs.yml` via `logo:` key

**v12.0 content updates (DOCS-04)**
- Strategy: new sections within existing feature guide pages (not new top-level pages)
- Old task type references (`python_script`, `bash_script`, `powershell_script`) replaced throughout — no migration callout note needed
- All references updated to unified `script` task type with runtime selector (Python / Bash / PowerShell)
- Jobs feature guide (`feature-guides/jobs.md` — create if missing): guided dispatch form, advanced mode toggle, bulk operations, DRAFT lifecycle, Queue view
- Scheduling feature guide (`feature-guides/job-scheduling.md`): Scheduling Health view, retention config
- Nodes feature guide (`feature-guides/nodes.md` — create if missing): DRAINING state, cross-link

### Claude's Discretion
- Exact prose and depth of each new section
- Whether to create a `feature-guides/jobs.md` as a new file or expand existing Jobs runbook
- SVG logo design details (geometric motif, exact proportions)
- Which specific UI label renames to call out (research current dashboard labels vs old names)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCS-01 | `.env.example` created listing all required and optional env vars with descriptions for the release container | Complete env var inventory compiled from source — see Standard Stack section |
| DOCS-02 | "Running with Docker" deployment section added to docs covering env var requirements | Compose file and existing install.md patterns confirm content gaps and what to cover |
| DOCS-03 | Docs/wiki branding aligned with dashboard visual identity | Dashboard CSS confirms Fira Sans + Fira Code fonts; primary HSL color identified; MkDocs Material logo key confirmed |
| DOCS-04 | Existing docs updated for v12.0 changes | Source audit confirms: old task types already validated-away in models.py (no raw old-type refs in existing docs); new features (DRAINING, bulk ops, Queue Monitor, Scheduling Health, retention) confirmed in source but absent from docs |
</phase_requirements>

---

## Summary

Phase 59 is a pure documentation phase: no backend or frontend code changes. All work is in four areas: (1) a new `.env.example` at repo root, (2) a new MkDocs page for Docker deployment, (3) CSS/logo branding alignment, and (4) new content sections in existing feature guide pages.

The existing docs site uses MkDocs Material 9.7.5 with the `slate` dark scheme. The dashboard uses Fira Sans (body) and Fira Code (mono) loaded from Google Fonts via the HTML `<head>`. The docs site currently uses Material's default system fonts. Adding the same Google Fonts import to `extra.css` brings the typography into alignment; the `privacy` plugin will download these at Docker build time so air-gap deployments remain offline-capable.

The source code audit confirms the full inventory of env vars (13 vars across 4 services), the DRAINING node state mechanics, Scheduling Health endpoint structure, retention config API, bulk job operations, guided dispatch form, and Queue Monitor — all confirmed present in source but absent or incomplete in existing docs.

**Primary recommendation:** Work as four independent plans mapped to the four requirements. No plan has a dependency on another; they can be written, reviewed, and committed in any order.

---

## Standard Stack

### Core Documentation Infrastructure
| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| MkDocs Material | 9.7.5 (pinned in `docs/requirements.txt`) | Docs site framework | Already deployed |
| mkdocs-swagger-ui-tag | 0.8.0 | API reference rendering | Already deployed |
| `privacy` plugin | bundled with Material | Downloads external assets at build time for air-gap | Already active |
| `offline` plugin | bundled with Material | Enables offline browsing of built site | Already active |
| nginx | alpine (Dockerfile) | Serves `site/` directory in production | Already deployed |

### Dashboard Visual Identity (confirmed from source)
| Property | Value | Source |
|----------|-------|--------|
| Body font | `Fira Sans` (weights 300/400/500/600/700) | `puppeteer/dashboard/src/index.css`, `tailwind.config.js` |
| Mono font | `Fira Code` (weights 400/500/600/700) | `puppeteer/dashboard/tailwind.config.js` |
| Primary color | `hsl(346.8, 77.2%, 49.8%)` — deep red/crimson | `puppeteer/dashboard/src/index.css` |
| Background | `hsl(240, 10%, 3.9%)` — near-black zinc | `puppeteer/dashboard/src/index.css` |
| Google Fonts import URL | `https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap` | `puppeteer/dashboard/index.html` |

### Env Var Inventory (all puppeteer service vars — confirmed from source)

**Required (crash or security failure if absent):**
| Variable | Source file | Behaviour if absent |
|----------|-------------|---------------------|
| `SECRET_KEY` | `auth.py` | Falls back to weak dev default `"super-secret-jwt-key-change-me"` — tokens insecure |
| `ENCRYPTION_KEY` | `security.py` | Auto-generates an ephemeral key — secrets lost on restart |
| `API_KEY` | `security.py` | `os.environ["API_KEY"]` — **process crash at import time** (no default) |
| `ADMIN_PASSWORD` | `main.py` | Falls back to `uuid4().hex` random — admin password unknown |

**Database:**
| Variable | Source file | Default |
|----------|-------------|---------|
| `DATABASE_URL` | `db.py` | `sqlite+aiosqlite:///./jobs.db` (SQLite dev default) |

**Optional / Deployment:**
| Variable | Source file | Default |
|----------|-------------|---------|
| `AGENT_URL` | `main.py` | `https://localhost:8001` |
| `PUBLIC_URL` | `main.py` | Derived from request base URL |
| `NODE_IMAGE` | `main.py` | `192.168.50.148:5000/puppet-node:latest` (must override in prod) |
| `NODE_EXECUTION_MODE` | `main.py` | `auto` |
| `AXIOM_LICENCE_KEY` | `main.py` | `""` (CE mode) |

**Tunnel (Caddy / cert-manager service):**
| Variable | Source file | Default |
|----------|-------------|---------|
| `CLOUDFLARE_TUNNEL_TOKEN` | `compose.server.yaml` | (none — tunnel service inactive if blank) |
| `SERVER_HOSTNAME` | `compose.server.yaml` | `""` (no extra SAN in TLS cert) |
| `DUCKDNS_TOKEN` | `compose.server.yaml` | (none — DDNS inactive) |

**EE / Mirror (smelter / air-gap):**
| Variable | Source file | Default |
|----------|-------------|---------|
| `MIRROR_DATA_PATH` | `smelter_router.py`, `mirror_service.py` | `/app/mirror_data` |
| `PYPI_MIRROR_URL` | `smelter_router.py`, `mirror_service.py` | `http://pypi:8080/simple` |
| `APT_MIRROR_URL` | `smelter_router.py`, `mirror_service.py` | `http://mirror/apt` |

---

## Architecture Patterns

### MkDocs Material Configuration Pattern

The `mkdocs.yml` uses `scheme: slate` + `primary: indigo`. The locked decision is to keep `slate` and override the primary color via `extra.css` rather than changing the palette key in `mkdocs.yml`. This is because `primary: custom` requires full color variable overrides, while patching `--md-primary-fg-color` in CSS is a single-line change.

The correct approach for Material color override in CSS:

```css
/* Source: mkdocs-material color system */
[data-md-color-scheme="slate"] {
  --md-primary-fg-color: hsl(346.8, 77.2%, 49.8%);
  --md-primary-fg-color--light: hsl(346.8, 77.2%, 65%);
  --md-primary-fg-color--dark: hsl(346.8, 77.2%, 38%);
}
```

### Logo in MkDocs Material

To add a logo via `mkdocs.yml`:

```yaml
theme:
  name: material
  logo: assets/logo.svg
```

The `logo:` key is a path relative to `docs/docs/`. The file must exist at `docs/docs/assets/logo.svg`. Material resizes the SVG to fit the nav bar automatically (typically 24px tall).

### Privacy Plugin and Google Fonts

The `privacy` plugin intercepts external asset references in the built HTML and downloads them at build time. This means:
- The `@import url(...)` for Google Fonts in `extra.css` will be downloaded during `mkdocs build`
- The resulting site has no outbound font CDN calls at runtime
- This is already documented in `docs/docs/security/air-gap.md` as working
- No additional plugin configuration is needed beyond adding the `@import`

### MkDocs Strict Build Constraint

The `docs/Dockerfile` runs `mkdocs build --strict`. Any warning is a build failure. This means:
- Every page listed in the `nav:` in `mkdocs.yml` **must** have a corresponding `.md` file
- Dead links in nav = build failure
- The new `docker-deployment.md` file must be created AND added to nav in the same change
- Similarly, `feature-guides/jobs.md` and `feature-guides/nodes.md` must be created if referenced in nav

### Existing Page Inventory

Current `docs/docs/feature-guides/` contents:
- `axiom-push.md` — axiom-push CLI guide (has guided form toggle reference in Foundry)
- `foundry.md` — Foundry guide (complete)
- `job-scheduling.md` — Scheduled jobs guide (DRAFT lifecycle already documented here)
- `oauth.md` — OAuth guide
- `rbac.md` — RBAC guide
- `rbac-reference.md` — RBAC permission reference

**Missing feature guide files** (must be created for DOCS-04):
- `feature-guides/jobs.md` — Jobs feature guide (currently only runbooks/jobs.md exists for troubleshooting)
- `feature-guides/nodes.md` — Nodes feature guide (currently only runbooks/nodes.md exists for troubleshooting)

### Existing Content to Extend

`docs/docs/feature-guides/job-scheduling.md` already covers:
- Creating job definitions (full field table)
- Cron syntax
- Node targeting
- DRAFT lifecycle (already documented with warning box)
- Retry configuration
- Staging Review section (cross-links to axiom-push.md)

**What it does NOT cover (DOCS-04 additions needed):**
- Scheduling Health view (fire/skipped/failed/missed counts, LATE detection)
- Retention config (`execution_retention_days`, 14-day default, where to configure)

### v12.0 Feature Status (confirmed in source)

| Feature | Source Confirmed | Currently in Docs |
|---------|-----------------|-------------------|
| Unified `script` task type | `models.py` line 28–35 (validator rejects old types) | Not explicitly documented as a type — first-job.md doesn't specify `task_type` field |
| DRAFT lifecycle | `models.py`, `job-scheduling.md` (already documented) | Partially — scheduling guide has it, axiom-push guide has it |
| Bulk operations | `models.py` `BulkJobRequest`, `Jobs.tsx` bulk handlers | Not documented |
| Guided dispatch form | `Jobs.tsx` `GuidedForm`, `guidedCardRef` | Not documented |
| Queue Monitor view | `Jobs.tsx` "Queue Monitor" card, WebSocket updates | Not documented |
| DRAINING node state | `main.py` drain/undrain endpoints, `job_service.py` exclusion | Not documented |
| Scheduling Health | `GET /api/health/scheduling`, `SchedulingHealthResponse` model | Not documented |
| Retention config | `GET/PATCH /api/admin/retention`, `Admin.tsx` | Not documented |

### Node States (confirmed in source)

DRAINING is a reversible administrative state:
- Set via `PATCH /nodes/{node_id}/drain` (requires `nodes:write`)
- Unset via `PATCH /nodes/{node_id}/undrain`
- Effect: node excluded from job assignment (`job_service.py` checks `status == "DRAINING"`)
- Heartbeat does NOT revert DRAINING to ONLINE (test confirms: `test_heartbeat_preserves_draining_status`)
- Node continues to complete already-assigned jobs while draining

### Scheduling Health Model

```python
# Source: puppeteer/agent_service/models.py
class DefinitionHealthRow(BaseModel):
    id: str
    name: str
    fired: int
    skipped: int
    failed: int
    missed: int
    health: str  # "ok" | "warning" | "error"

class SchedulingHealthResponse(BaseModel):
    window: str
    aggregate: Dict[str, int]  # {fired, skipped, failed, late, missed}
    definitions: List[DefinitionHealthRow]
```

Endpoint: `GET /api/health/scheduling?window=<1h|6h|24h|7d>`

### Existing .env.example at Repo Root

The current `.env.example` at `/home/thomas/Development/master_of_puppets/.env.example` uses outdated key names:
- Uses `JWT_SECRET` — correct name is `SECRET_KEY`
- Missing `DATABASE_URL`
- Missing `CLOUDFLARE_TUNNEL_TOKEN`
- Missing `SECRET_KEY`
- Includes `PYPI_MIRROR_URL` and `APT_MIRROR_URL` in the main template (these are EE/optional)

This file must be replaced in full.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font download for air-gap | Manual font embedding | MkDocs `privacy` plugin | Already configured, handles `@import` URLs automatically at `mkdocs build` time |
| Color theming | Full Material theme fork | CSS variable overrides in `extra.css` | Material exposes `--md-primary-fg-color` and family; 3-line CSS change achieves alignment |
| SVG logo sizing | Explicit width/height in SVG | Let Material handle it | Material's nav bar CSS controls logo dimensions automatically |
| Strict build validation | Manual page-exists checks | `mkdocs build --strict` in Dockerfile | Already runs on every Docker build — catches missing pages |

---

## Common Pitfalls

### Pitfall 1: Missing file after nav insertion
**What goes wrong:** Adding a page to the `nav:` in `mkdocs.yml` without creating the corresponding `.md` file causes `mkdocs build --strict` to fail with a file-not-found warning treated as error.
**How to avoid:** Always create the `.md` file and the `nav:` entry in the same commit/plan.
**Warning signs:** Docker build fails with `WARNING - Config value: 'docs_dir'. Error: Documentation file ... does not exist.`

### Pitfall 2: Font import not downloaded by privacy plugin
**What goes wrong:** Adding font CSS via JavaScript or an HTML template override (rather than `extra.css`) may not be intercepted by the `privacy` plugin.
**How to avoid:** Use `@import url(...)` in `extra.css` — the privacy plugin processes CSS imports during build.
**Warning signs:** Air-gap doc validates but requests to fonts.googleapis.com still occur at runtime.

### Pitfall 3: Wrong .env key names
**What goes wrong:** Documenting `JWT_SECRET` instead of `SECRET_KEY` misleads operators who get no error for the wrong name — the old var just gets silently ignored while auth uses the default weak key.
**How to avoid:** Cross-reference against `auth.py` (`SECRET_KEY`), `security.py` (`API_KEY`, `ENCRYPTION_KEY`), `db.py` (`DATABASE_URL`).
**Warning signs:** Stack runs but JWT tokens are signed with `super-secret-jwt-key-change-me`.

### Pitfall 4: Documenting features as if they exist in the nav without a feature guide page
**What goes wrong:** `runbooks/jobs.md` is a troubleshooting doc, not a feature guide. Adding docs for guided form, bulk ops etc. to the runbook buries them in the wrong section.
**How to avoid:** Create `feature-guides/jobs.md` and `feature-guides/nodes.md` as new files. Add them to nav under Feature Guides, not Runbooks.
**Warning signs:** Operators can't find "how to use bulk ops" because it's under Runbooks.

### Pitfall 5: Material logo key uses wrong path
**What goes wrong:** `logo: docs/assets/logo.svg` (absolute-looking path) instead of `logo: assets/logo.svg` (relative to docs dir).
**How to avoid:** The `logo:` key in `mkdocs.yml` is relative to the `docs_dir` (default: `docs/`). File must live at `docs/docs/assets/logo.svg`.

---

## Code Examples

### extra.css font + color additions

```css
/* Source: mkdocs-material documentation on theme customization */

/* Google Fonts — downloaded at build time by the privacy plugin */
@import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap');

/* Font overrides — match dashboard Fira Sans/Fira Code */
:root {
  --md-text-font: "Fira Sans";
  --md-code-font: "Fira Code";
}

/* Primary color override — match dashboard hsl(346.8, 77.2%, 49.8%) */
[data-md-color-scheme="slate"] {
  --md-primary-fg-color: hsl(346.8, 77.2%, 49.8%);
  --md-primary-fg-color--light: hsl(346.8, 77.2%, 65%);
  --md-primary-fg-color--dark: hsl(346.8, 77.2%, 38%);
}
```

### mkdocs.yml logo addition

```yaml
# Source: mkdocs-material docs — logo key under theme:
theme:
  name: material
  logo: assets/logo.svg   # relative to docs_dir (docs/docs/)
  palette:
    scheme: slate
    primary: indigo         # kept — color overridden in extra.css
    accent: indigo
```

### .env.example structure

```bash
# === Required ===

# JWT signing secret — generate with:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=

# Fernet key for encrypting secrets at rest — generate with:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=

# Shared API key — required; the agent service crashes at import if absent
API_KEY=

# Initial admin password — only read on first start (user does not yet exist in DB)
ADMIN_PASSWORD=

# === Database ===

# PostgreSQL connection string (required for production)
# Default: sqlite+aiosqlite:///./jobs.db (dev only — not suitable for production)
DATABASE_URL=postgresql+asyncpg://puppet:password@db/puppet_db

# === Optional ===

# Public URL used in generated join tokens — set to your server's accessible address
# AGENT_URL=https://your-host

# Node image reference for Foundry-generated compose files
# NODE_IMAGE=your-registry/puppet-node:latest

# Node execution mode: auto | direct | docker | podman
# NODE_EXECUTION_MODE=auto

# Axiom licence key — leave blank for Community Edition
# AXIOM_LICENCE_KEY=

# === Tunnel ===

# Cloudflare Tunnel token — required only if using the tunnel service
# CLOUDFLARE_TUNNEL_TOKEN=
```

### Nav insertion for docker-deployment.md

```yaml
# Source: docs/mkdocs.yml — Getting Started section
nav:
  - Getting Started:
    - Prerequisites: getting-started/prerequisites.md
    - Install: getting-started/install.md
    - Running with Docker: getting-started/docker-deployment.md   # NEW
    - Enroll a Node: getting-started/enroll-node.md
    - First Job: getting-started/first-job.md
```

### Nav insertion for feature guides jobs and nodes

```yaml
# Source: docs/mkdocs.yml — Feature Guides section
  - Feature Guides:
    - Operator Tools:
      - axiom-push CLI: feature-guides/axiom-push.md
    - Platform Config:
      - Jobs: feature-guides/jobs.md                     # NEW
      - Nodes: feature-guides/nodes.md                   # NEW
      - Foundry: feature-guides/foundry.md
      - Job Scheduling: feature-guides/job-scheduling.md
      - RBAC: feature-guides/rbac.md
      - OAuth & Authentication: feature-guides/oauth.md
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `task_type: python_script` / `bash_script` | `task_type: script` + `runtime: python/bash/powershell` | v12.0 | Old types rejected by validator in `models.py` — docs must use new form |
| Manual JSON dispatch form only | Guided dispatch form + Advanced (JSON) toggle | v12.0 | Documentation gap — guided form not documented anywhere |
| Jobs only visible as a list | Queue Monitor with WebSocket live updates + per-node drawer | v12.0 | Not documented |
| Nodes: online/offline/revoked/tampered | Added DRAINING state | v12.0 | Not documented |

---

## Open Questions

1. **Feature guide nav placement for Jobs and Nodes**
   - What we know: no `feature-guides/jobs.md` or `feature-guides/nodes.md` exists currently
   - What's unclear: whether to insert before or after Foundry in the nav; whether to create a separate subsection "Core Workflows"
   - Recommendation: Claude's discretion per CONTEXT.md — place under Platform Config, before Foundry (jobs and nodes are core, Foundry is advanced)

2. **Exact DATABASE_URL value in .env.example**
   - What we know: `compose.server.yaml` uses `postgresql+asyncpg://puppet:masterpassword@db/puppet_db` with env var expansion
   - What's unclear: whether to show the actual Compose service names (`db`) or a generic placeholder (`your-postgres-host`)
   - Recommendation: show `postgresql+asyncpg://puppet:password@db/puppet_db` matching the Compose service name, with a comment explaining `db` is the Compose service name

3. **Scheduling Health "LATE" vs "missed" terminology**
   - What we know: `SchedulingHealthResponse.aggregate` has both `late` and `missed` keys; `DefinitionHealthRow` has `missed` but not `late`
   - What's unclear: what "late" means vs "missed" at the per-definition level
   - Recommendation: document `aggregate.late` as "fired but started late relative to scheduled time" and `missed` as "scheduled fire did not occur at all" — verify against `scheduler_service.get_scheduling_health()` if needed

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (puppeteer), vitest (dashboard) |
| Config file | `puppeteer/pytest.ini` (or `pyproject.toml`), `puppeteer/dashboard/vite.config.ts` |
| Quick run command | `docker compose -f puppeteer/compose.server.yaml exec agent mkdocs build --strict` (for docs), `cd docs && mkdocs build --strict` (local) |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 | `.env.example` exists at repo root with all required vars | smoke | `test -f .env.example && grep -q SECRET_KEY .env.example && grep -q ENCRYPTION_KEY .env.example && grep -q API_KEY .env.example` | ❌ Wave 0 |
| DOCS-02 | `docs/docs/getting-started/docker-deployment.md` exists and is in nav | smoke | `mkdocs build --strict` (strict mode catches missing files) | ❌ Wave 0 |
| DOCS-03 | Docs site builds with branding CSS | smoke | `mkdocs build --strict` (build fails if CSS syntax error) | ❌ Wave 0 |
| DOCS-04 | Feature guide pages exist and build cleanly | smoke | `mkdocs build --strict` | ❌ Wave 0 |

The primary validation gate for all DOCS-XX requirements is `mkdocs build --strict`. If the build passes, nav references are satisfied, files exist, and CSS/markdown syntax is valid.

### Sampling Rate
- **Per task commit:** `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict 2>&1 | tail -5`
- **Per wave merge:** Full `mkdocs build --strict`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `docs/docs/assets/` directory — must exist before `logo.svg` is referenced in mkdocs.yml
- [ ] `docs/docs/getting-started/docker-deployment.md` — new file for DOCS-02
- [ ] `docs/docs/feature-guides/jobs.md` — new file for DOCS-04
- [ ] `docs/docs/feature-guides/nodes.md` — new file for DOCS-04

*(All gaps are content files, not test infrastructure — created during plan execution)*

---

## Sources

### Primary (HIGH confidence)
- Direct source code reads — `puppeteer/agent_service/auth.py`, `security.py`, `db.py`, `main.py`, `models.py` — env var inventory
- Direct source code reads — `puppeteer/dashboard/src/index.css`, `tailwind.config.js`, `index.html` — visual identity
- Direct file reads — `docs/mkdocs.yml`, `docs/requirements.txt`, `docs/Dockerfile` — docs infrastructure
- Direct file reads — `docs/docs/feature-guides/job-scheduling.md`, `axiom-push.md`, `foundry.md` — existing content

### Secondary (MEDIUM confidence)
- MkDocs Material documentation (font var names `--md-text-font`, `--md-code-font`) — standard Material theming API, confirmed against mkdocs-material 9.x
- MkDocs Material `logo:` key behavior — documented in official Material docs

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Env var inventory: HIGH — read directly from source files
- Visual identity: HIGH — read directly from dashboard CSS and Tailwind config
- MkDocs patterns: HIGH — confirmed from existing mkdocs.yml and Dockerfile
- Content gaps: HIGH — confirmed by grepping existing docs for feature names
- Pitfalls: HIGH — derived from confirmed constraints (strict build, privacy plugin)

**Research date:** 2026-03-24
**Valid until:** 2026-06-24 (stable — MkDocs Material pinned at 9.7.5, no fast-moving dependencies)
