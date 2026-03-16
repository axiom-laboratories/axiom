# Phase 20: Container Infrastructure & Routing - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the MkDocs docs container, configure Caddy routing to serve the site at `/docs/`, and apply Cloudflare Access protection — enough for the site to be live and locked down. No content yet; that's phases 22–25.

</domain>

<decisions>
## Implementation Decisions

### CF Access scope
- Gate all of `/docs/*` — not just security-sensitive subdirectories
- CF Access at the Cloudflare edge is the sole gate; Caddy does not add secondary JWT validation
- Same allowlist/policy as the dashboard — any operator who can access the dashboard can access docs
- One policy, one Caddyfile block — no conditional routing

### Content source location
- New `docs/` directory at the **repo root** (alongside `puppeteer/`, `puppets/`, etc.) — documentation is a top-level concern, not a server implementation detail
- Existing `puppeteer/docs/` markdown files are left in place and ignored in Phase 20 — content phases (22–25) decide what to keep, rewrite, or discard
- No migration or deletion of existing files in this phase

### MkDocs skeleton
- Minimal viable `mkdocs.yml`: `theme: material`, `site_url`, and plugins only — no nav defined yet
- Include **both** the `privacy` plugin (self-hosts Google Fonts and external assets) and the `offline` plugin (bundles JS/CSS into the static build) to fully satisfy INFRA-06
- Single placeholder `docs/index.md` with "Documentation coming soon" — enough to pass `--strict` without creating misleading content
- Nav structure is deferred to content phases (Phase 23 locks it per STATE.md decision)

### Dockerfile & build
- Two-stage Dockerfile: `python:3.12-slim` builder stage + `nginx:alpine` serve stage (already decided in STATE.md)
- Builder stage runs `RUN mkdocs build --strict` directly — no wrapper script
- Build failure = `docker compose build docs` fails; the rest of the stack (agent, dashboard, db) is unaffected
- Serve stage uses a **custom nginx.conf** with `location /docs/ { alias /usr/share/nginx/html/; }` — required for correct asset routing (default nginx config causes 404s on all CSS/JS under the subpath)

### Routing (already decided in STATE.md — confirmed)
- Caddy uses `handle /docs/*` (NOT `handle_path`) to preserve the `/docs/` prefix when proxying to nginx
- `site_url: https://dev.master-of-puppets.work/docs/` baked into mkdocs.yml so all asset references are absolute with the subpath

### Claude's Discretion
- nginx port choice inside the container (80 is fine)
- Docker service name for the docs container in compose.server.yaml
- Exact MkDocs Material theme palette/colour settings for the skeleton
- Pin versions for mkdocs and mkdocs-material in requirements.txt

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `puppeteer/cert-manager/Caddyfile`: The new `handle /docs/*` block must be inserted **before** the final `handle` fallback (which proxies to `dashboard:80`) — Caddy evaluates handles in order
- `puppeteer/compose.server.yaml`: docs service follows the `dashboard` service pattern (build from local Dockerfile, no exposed ports — Caddy proxies it via service name)

### Established Patterns
- Services in `compose.server.yaml` use `image: localhost/...` naming and local build contexts
- No ports exposed on internal services — Caddy is the single ingress point
- Volumes are declared at the bottom of compose.server.yaml (docs needs no persistent volume — static files baked into the image)

### Integration Points
- `cert-manager/Caddyfile`: add `handle /docs/*` block proxying to the docs container
- `compose.server.yaml`: add `docs` service with build context pointing to the Dockerfile location
- `docs/` new directory at repo root: `mkdocs.yml` + `docs/index.md` placeholder

</code_context>

<specifics>
## Specific Ideas

- STATE.md explicitly notes: "Caddy must use `handle /docs/*` (NOT handle_path) + nginx `alias` — prefix stripping silently breaks all CSS/JS assets" — this is the single most critical implementation detail for this phase
- The blocker in STATE.md ("CF Access policy scope decision needed") is resolved: gate all `/docs/*`, same policy as dashboard

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 20-container-infrastructure-routing*
*Context gathered: 2026-03-16*
