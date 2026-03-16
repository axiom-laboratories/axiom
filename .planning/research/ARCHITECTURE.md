# Architecture Research

**Domain:** MkDocs Material documentation container integrated into existing Caddy + Docker Compose stack (v9.0 Enterprise Documentation)
**Researched:** 2026-03-16
**Confidence:** HIGH — based on direct codebase analysis, official MkDocs/Caddy documentation, and verified community patterns

---

## Standard Architecture

### System Overview

```
                        Cloudflare Tunnel
                               |
                        cert-manager (Caddy)
                        :80 / :443  ← MODIFIED: add /docs/* handler
                               |
          ┌────────────────────┼──────────────────────┐
          |                    |                       |
     /api/*             /docs/*                  (fallback)
     /auth/*            /docs/assets/*           /
     /ws                /docs/...                     |
     /system/*               |                   dashboard
          |                docs                  (nginx:80)
        agent           (nginx:80)               [unchanged]
     (FastAPI :8001)    [NEW SERVICE]
     [unchanged]
          |
      ┌───┴───┐
      db     model
 (Postgres)  (uvicorn :8000)
 [unchanged] [unchanged]
```

The docs container is a **new service** inserted into the existing Caddy routing layer. It is fully stateless — no DB, no secrets, no runtime dependencies. It serves pre-built static HTML generated at image build time from git-backed markdown.

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| cert-manager (Caddy) | TLS termination, path-based routing, Cloudflare ingress | MODIFIED — add /docs/* routing block |
| docs | Serve pre-built MkDocs Material static site | NEW — nginx:alpine, baked static HTML |
| agent (FastAPI) | REST API + OpenAPI schema source | UNCHANGED |
| dashboard (React) | App UI — links out to /docs/ for documentation | MODIFIED — replace inline Docs view with external link |
| Build stage (Docker) | Generates openapi.json + runs mkdocs build | NEW — Dockerfile builder stage only, not a runtime service |

---

## Recommended Project Structure

```
master_of_puppets/
├── docs/                            # Source markdown — git-backed, ALREADY EXISTS
│   ├── mkdocs.yml                   # NEW: MkDocs configuration (lives with content)
│   ├── index.md                     # Landing page
│   ├── getting-started/
│   │   └── index.md                 # End-to-end first-run walkthrough
│   ├── user-guide/
│   │   ├── jobs.md
│   │   ├── scheduling.md
│   │   ├── foundry.md
│   │   ├── smelter.md
│   │   ├── mop-push.md
│   │   ├── staging.md
│   │   ├── rbac.md
│   │   └── oauth.md
│   ├── developer/
│   │   ├── architecture.md          # Migrated from docs/architecture.md
│   │   ├── setup.md                 # Migrated from docs/INSTALL.md
│   │   ├── deployment.md            # Migrated from docs/deployment_guide.md
│   │   └── contributing.md
│   ├── security/
│   │   ├── overview.md              # Migrated from docs/security.md
│   │   ├── mtls.md                  # Migrated from docs/ssl_guide.md
│   │   ├── signatures.md            # Migrated from docs/security_signatures.md
│   │   └── audit-log.md
│   ├── api-reference/
│   │   ├── index.md                 # Contains !!swagger openapi.json!! directive
│   │   └── openapi.json             # GENERATED at build time — not committed to git
│   ├── runbooks/
│   │   └── troubleshooting.md
│   └── assets/
│       └── images/
├── puppeteer/
│   ├── cert-manager/
│   │   └── Caddyfile                # MODIFIED: add /docs/* handle blocks
│   ├── docs-container/
│   │   ├── Dockerfile               # NEW: multi-stage build
│   │   ├── nginx.conf               # NEW: nginx config for static file serving
│   │   └── requirements-docs.txt    # NEW: mkdocs-material + plugins
│   └── compose.server.yaml          # MODIFIED: add docs service
├── scripts/
│   └── export_openapi.py            # NEW: dumps app.openapi() to openapi.json
└── puppeteer/dashboard/src/
    ├── layouts/MainLayout.tsx        # MODIFIED: replace /docs NavItem with <a> external link
    ├── views/Docs.tsx                # DELETED: replaced by external link
    └── AppRoutes.tsx                 # MODIFIED: remove /docs Route entry
```

### Structure Rationale

- **docs/ at repo root:** Already exists with real markdown files. MkDocs is configured from here. The git-backed source is the single source of truth — no content duplication.
- **mkdocs.yml lives inside docs/:** Co-located with content. Run as `mkdocs build -f docs/mkdocs.yml` from repo root, or just `mkdocs build` from inside `docs/`.
- **docs/api-reference/openapi.json is generated, not committed:** Produced at container image build time by importing the FastAPI app and calling `app.openapi()`. Committing it creates drift; generating it means the docs always match the code. A failing export script fails the Docker build — loud and early.
- **puppeteer/docs-container/Dockerfile:** Isolated from the main server Containerfile. Build context is the repo root so the Dockerfile can COPY both `docs/` and `puppeteer/agent_service/` (needed for the openapi export step).
- **scripts/export_openapi.py:** Thin script — imports `app` from `agent_service.main`, calls `app.openapi()`, writes JSON to `docs/api-reference/openapi.json`. No HTTP server started.

---

## Architectural Patterns

### Pattern 1: Multi-Stage Docker Build for Static Docs

**What:** Stage 1 runs Python, installs MkDocs + plugins + the agent's requirements (for import), exports openapi.json, and runs `mkdocs build`. Stage 2 is `nginx:alpine` and only copies the generated `site/` directory. The final image has no Python, no MkDocs, no source markdown — only pre-built HTML/CSS/JS.

**When to use:** Always for production. The `squidfunk/mkdocs-material` Docker image's built-in dev server is explicitly not production-safe. Their documentation states: "The image is intended for local preview purposes and is not suitable for deployment because the web server used by MkDocs for live previews is not designed for production use and may have security vulnerabilities." Nginx serving static files is the correct pattern.

**Trade-offs:** Adds ~60s to image build time (pip install + mkdocs build). No live-reload (not needed in production). The resulting image is ~25MB vs ~400MB for the Python+MkDocs image. Zero Python attack surface in the running container.

**Dockerfile (puppeteer/docs-container/Dockerfile):**

```dockerfile
# Stage 1: builder — generates openapi.json and builds static site
FROM python:3.12-slim AS builder
WORKDIR /build

# Install MkDocs Material + plugins + agent dependencies (for openapi export)
COPY puppeteer/docs-container/requirements-docs.txt .
COPY puppeteer/requirements.txt ./requirements-agent.txt
RUN pip install --no-cache-dir -r requirements-docs.txt -r requirements-agent.txt

# Copy agent source (needed for app.openapi() call)
COPY puppeteer/agent_service/ ./agent_service/

# Copy documentation source
COPY docs/ ./docs/

# Copy openapi export script
COPY scripts/export_openapi.py .

# Generate openapi.json from live app definition (no server started)
RUN python export_openapi.py

# Build static site
RUN mkdocs build -f docs/mkdocs.yml --site-dir /build/site

# Stage 2: server — only the built HTML
FROM nginx:alpine
COPY --from=builder /build/site /usr/share/nginx/html
COPY puppeteer/docs-container/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**requirements-docs.txt:**

```
mkdocs-material>=9.5
mkdocs-render-swagger-plugin>=0.1.1
```

### Pattern 2: `site_url` Configuration for Sub-Path Routing

**What:** Set `site_url: https://dev.master-of-puppets.work/docs/` in `mkdocs.yml`. This makes MkDocs generate absolute asset references like `/docs/assets/stylesheets/main.css` throughout the built HTML. Caddy then uses a plain `handle /docs/*` block (no prefix stripping) to forward requests to the docs container.

**Why this matters:** If you use Caddy's `handle_path /docs/*` (which strips the prefix), requests reach the container as `GET /assets/css/main.css` — and nginx serves them correctly. But the browser fetches page-relative assets using the full URL, meaning a request to `https://example.com/docs/foundry/` causes the browser to request `/assets/css/main.css` (not `/docs/assets/css/main.css`). This falls through to the dashboard fallback in Caddy, not the docs container. Caddy returns a 404 or the dashboard's index.html. The result: every page loads but all CSS and JS is broken.

**The correct approach:** Set `site_url` so MkDocs bakes `/docs/` into every asset reference. Use `handle /docs/*` without prefix stripping. Configure nginx to serve from root regardless of the `/docs/` prefix in incoming requests.

**Trade-offs:**
- `site_url` couples the MkDocs config to the deployment URL. If the path changes from `/docs/` to something else, `mkdocs.yml` must be updated and the image rebuilt. This is acceptable — the path will not change.
- No prefix stripping means nginx receives `GET /docs/foundry/` and must map that back to `site/foundry/index.html`. This is handled cleanly with an nginx `alias` directive.

**Alternative considered and rejected:** `handle_path` with prefix stripping + relative asset paths. MkDocs Material's generated HTML uses absolute paths for many assets (search index, service worker manifest). Relative paths cannot be forced globally without forking theme templates. The `site_url` approach is the documented, supported path.

### Pattern 3: OpenAPI Export at Build Time via `app.openapi()`

**What:** FastAPI's `app.openapi()` method generates the full OpenAPI schema dict without starting an HTTP server. Import the `app` object, call the method, write JSON. This runs in the builder stage of the Dockerfile.

**When to use:** Always. The alternatives are: (a) call the live `/openapi.json` endpoint at build time — requires the app to be running, creates a circular build dependency; (b) commit a static `openapi.json` — becomes stale as routes change and is silently wrong.

**Trade-offs:** The export script must be able to `import agent_service.main` without triggering DB connections or startup side effects. FastAPI's lifespan events (startup/shutdown) only fire when uvicorn starts — not on import. The `app` object can be imported safely. However, the `agent_service` may import SQLAlchemy models at module level, which requires SQLAlchemy to be installed (it will be, via requirements-agent.txt).

**Export script (scripts/export_openapi.py):**

```python
import json
import sys
import os

# Add repo root to path so agent_service is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..') if '__file__' in dir() else '.')

from agent_service.main import app

schema = app.openapi()
output_path = 'docs/api-reference/openapi.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w') as f:
    json.dump(schema, f, indent=2)

print(f"Exported {len(schema.get('paths', {}))} paths to {output_path}")
```

**Dependency consideration:** `agent_service.main` imports SQLAlchemy, Pydantic, jose, cryptography, and other packages. The builder stage must install `puppeteer/requirements.txt` alongside the MkDocs requirements. The builder stage image will be ~400MB (not a concern — it is discarded after the build).

### Pattern 4: Caddy Path Routing with nginx Alias

**What:** Use `handle /docs/*` in both Caddyfile server blocks to forward requests to the docs container without stripping the prefix. Configure nginx in the docs container to use `alias` to serve the correct files even though the URL path starts with `/docs/`.

**Caddyfile change (both `:443` and `:80` blocks — before the fallback `handle {}`):**

```caddyfile
handle /docs/* {
    reverse_proxy docs:80
}
```

**nginx.conf (puppeteer/docs-container/nginx.conf):**

```nginx
server {
    listen 80;
    index index.html;

    location /docs/ {
        alias /usr/share/nginx/html/;
        try_files $uri $uri/ $uri.html =404;
    }

    # Health check endpoint for compose healthcheck if needed
    location /health {
        return 200 'ok';
        add_header Content-Type text/plain;
    }
}
```

The `alias` directive maps `/docs/` in the URL to the root of the static site directory. A request for `/docs/foundry/index.html` becomes a filesystem read of `/usr/share/nginx/html/foundry/index.html`.

**Why `alias` not `root`:** `root` prepends the path to every lookup — `GET /docs/foundry/` would look for `/usr/share/nginx/html/docs/foundry/`. `alias` replaces the location prefix — `GET /docs/foundry/` looks for `/usr/share/nginx/html/foundry/`. This is the correct behaviour for sub-path mounting.

### Pattern 5: Dashboard Docs Link as External Navigation

**What:** Remove the in-app `Docs.tsx` React component (which renders a single bundled markdown file) and replace the sidebar nav entry with a plain `<a>` tag that opens `/docs/` in a new browser tab.

**Changes required:**
1. `MainLayout.tsx` — replace `NavItem to="/docs"` with an `<a href="/docs/" target="_blank">` styled identically, using `BookOpen` from lucide-react.
2. `AppRoutes.tsx` — remove the `<Route path="docs" element={<Docs />} />` entry.
3. `Docs.tsx` — can be deleted (it imports a single bundled `UserGuide.md` — all of that content moves to the MkDocs site).

**Why new tab:** A same-tab redirect breaks the browser back button — the user expects Back to return to the dashboard. Opening in a new tab is the standard pattern for linking out of an SPA to an external resource. At the network level `/docs/` and `/` are the same origin (both served from dev.master-of-puppets.work), so browsers allow the tab to be opened without popup blockers.

**Sidebar change in `MainLayout.tsx`:**

```tsx
// Add BookOpen to the lucide-react import at the top of the file

// Replace the existing NavItem for docs (currently missing from sidebar — add it here)
// in SidebarContent, under a "Resources" or "System" section:
<a
    href="/docs/"
    target="_blank"
    rel="noreferrer"
    className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium
               transition-all hover:bg-zinc-800 hover:text-white text-zinc-400"
>
    <BookOpen className="h-4 w-4 shrink-0" />
    <span>Documentation</span>
</a>
```

Note: the current sidebar has no "Docs" entry — the route exists in `AppRoutes.tsx` but `MainLayout.tsx` never added it to the nav. This change adds it for the first time with the new external-link behaviour.

---

## Data Flow

### OpenAPI Reference Generation Flow

```
docker compose build docs
    |
    v
Stage 1: python:3.12-slim (builder)
    |
    ├── pip install requirements-docs.txt + requirements.txt
    |       (mkdocs-material, render-swagger-plugin, fastapi,
    |        sqlalchemy, pydantic, etc.)
    |
    ├── COPY docs/ → /build/docs/
    |   COPY agent_service/ → /build/agent_service/
    |   COPY scripts/export_openapi.py → /build/
    |
    ├── python export_openapi.py
    |       sys.path.insert(0, '.')
    |       from agent_service.main import app
    |       app.openapi() → dict with all routes + schemas
    |       json.dump() → docs/api-reference/openapi.json
    |
    └── mkdocs build -f docs/mkdocs.yml --site-dir /build/site
            reads docs/api-reference/openapi.json
            render_swagger plugin injects SwaggerUI HTML
            outputs /build/site/ (static HTML/CSS/JS)
    |
    v
Stage 2: nginx:alpine
    COPY /build/site → /usr/share/nginx/html
    COPY nginx.conf → /etc/nginx/conf.d/default.conf
    |
    v
Runtime: nginx at :80
    serves /usr/share/nginx/html via /docs/ location alias
    no Python, no MkDocs, no source files in the running container
```

### Request Routing Flow

```
Browser: GET https://dev.master-of-puppets.work/docs/foundry/

Cloudflare Tunnel → cert-manager (Caddy :443)

Caddy evaluates handlers in order (first match wins):
    1. handle /api/*         ← no match
    2. handle /auth/*        ← no match
    3. handle /ws            ← no match
    4. handle /system/root-ca*  ← no match
    5. handle /docs/*        ← MATCHES
           reverse_proxy docs:80
           forwards: GET /docs/foundry/

docs container (nginx:80)
    location /docs/ matches
    alias maps to /usr/share/nginx/html/
    try_files: /usr/share/nginx/html/foundry/index.html → 200
    returns: MkDocs Material HTML page
```

### Asset Request Flow

```
Browser receives HTML for /docs/foundry/
HTML contains: <link href="/docs/assets/stylesheets/main.css">
                (set by mkdocs.yml site_url: https://...work/docs/)

Browser: GET https://dev.master-of-puppets.work/docs/assets/stylesheets/main.css

Caddy: handle /docs/* matches → docs:80
nginx: /docs/ alias → /usr/share/nginx/html/assets/stylesheets/main.css → 200

CSS loaded correctly.
```

### Dashboard Navigation Flow

```
User clicks "Documentation" in sidebar
    |
    v
<a href="/docs/" target="_blank"> fires
    |
    v
New browser tab: GET https://dev.master-of-puppets.work/docs/
    |
Caddy → docs:80 → nginx → /usr/share/nginx/html/index.html
    |
MkDocs Material landing page loads in new tab
Dashboard remains open in original tab
```

---

## Integration Points

### New vs Modified Components

| Component | Status | Change |
|-----------|--------|--------|
| `puppeteer/compose.server.yaml` | MODIFIED | Add `docs` service |
| `puppeteer/cert-manager/Caddyfile` | MODIFIED | Add `handle /docs/*` in both `:443` and `:80` blocks, before fallback |
| `puppeteer/docs-container/Dockerfile` | NEW | Multi-stage: python:3.12-slim builder + nginx:alpine |
| `puppeteer/docs-container/nginx.conf` | NEW | `alias`-based static file serving for /docs/ prefix |
| `puppeteer/docs-container/requirements-docs.txt` | NEW | mkdocs-material, mkdocs-render-swagger-plugin |
| `docs/mkdocs.yml` | NEW | MkDocs config with Material theme, nav structure, site_url |
| `docs/api-reference/index.md` | NEW | Contains `!!swagger openapi.json!!` directive |
| `scripts/export_openapi.py` | NEW | Generates openapi.json without starting a server |
| `puppeteer/dashboard/src/layouts/MainLayout.tsx` | MODIFIED | Add `<a href="/docs/">` with BookOpen icon in sidebar |
| `puppeteer/dashboard/src/views/Docs.tsx` | DELETED | No longer rendered — content moves to MkDocs site |
| `puppeteer/dashboard/src/AppRoutes.tsx` | MODIFIED | Remove `/docs` Route entry |
| All existing `docs/*.md` files | MIGRATED | Reorganised into mkdocs nav structure (not deleted) |

### Compose Service Definition

```yaml
# Add to compose.server.yaml under services:
docs:
  image: localhost/master-of-puppets-docs:v1
  build:
    context: ..                            # repo root — needs docs/ and agent_service/
    dockerfile: puppeteer/docs-container/Dockerfile
  restart: always
  # No ports exposed — Caddy proxies internally via Docker network
  # No volumes — fully baked static site, zero runtime dependencies
  # No depends_on — does not depend on db, agent, or any other service
```

The `docs` service has no `depends_on` because it is a pure static file server. It can start before or after any other service without consequence.

### MkDocs Configuration (`docs/mkdocs.yml`)

```yaml
site_name: Master of Puppets
site_description: Secure distributed job orchestration platform
# site_url MUST match the deployment path — controls asset URL generation
site_url: https://dev.master-of-puppets.work/docs/
docs_dir: .        # mkdocs.yml lives inside docs/, so content is at docs_dir root
site_dir: ../build/site   # relative to docs/ — or use --site-dir in build command

theme:
  name: material
  palette:
    - scheme: slate
      primary: indigo
      accent: indigo
  features:
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.highlight
    - content.code.copy
    - content.code.annotate

plugins:
  - search
  - render_swagger

nav:
  - Home: index.md
  - Getting Started: getting-started/index.md
  - User Guide:
      - Job Dispatch: user-guide/jobs.md
      - Scheduling: user-guide/scheduling.md
      - Foundry: user-guide/foundry.md
      - Smelter Registry: user-guide/smelter.md
      - mop-push CLI: user-guide/mop-push.md
      - Staging Workflow: user-guide/staging.md
      - RBAC & Users: user-guide/rbac.md
      - OAuth Device Flow: user-guide/oauth.md
  - Developer:
      - Architecture: developer/architecture.md
      - Setup & Installation: developer/setup.md
      - Deployment: developer/deployment.md
      - Contributing: developer/contributing.md
  - Security:
      - Overview: security/overview.md
      - mTLS Setup: security/mtls.md
      - Job Signing: security/signatures.md
      - Audit Log: security/audit-log.md
  - API Reference: api-reference/index.md
  - Runbooks & Troubleshooting: runbooks/troubleshooting.md
```

### API Reference Page (`docs/api-reference/index.md`)

```markdown
# API Reference

This reference is auto-generated from the FastAPI OpenAPI schema at build time.
It reflects the exact routes and models in the running server.

!!swagger openapi.json!!
```

The `!!swagger openapi.json!!` directive is resolved by `mkdocs-render-swagger-plugin`. It looks for `openapi.json` relative to the markdown file — which is `docs/api-reference/openapi.json`, exactly where `export_openapi.py` writes it. No `allow_arbitrary_locations` configuration is required.

---

## Scaling Considerations

| Scale | Adjustment |
|-------|------------|
| Current (single server, internal use) | One docs container, nginx static files — no changes needed at any realistic traffic level for internal docs |
| Content updates | Rebuild the docs image and redeploy: `docker compose build docs && docker compose up -d --no-build docs`. Takes ~60s. No migration, no state, no downtime for other services. |
| Multiple deployment environments | Set `site_url` per environment in `mkdocs.yml`. Build environment-specific images. Or: parametrize `site_url` via a build ARG and pass at `docker build` time. |

### Content Update Model

Docs are baked into the image at build time. This is intentional:

- **Pro:** Atomic deploys. A broken build (bad markdown, failing openapi export) leaves the old image running. No stale drift.
- **Pro:** The running container has zero runtime dependencies. It cannot be broken by a failing database, agent restart, or network partition.
- **Pro:** Image content is immutable and auditable.
- **Con:** Docs do not update without a rebuild. For a project of this size and documentation change frequency, rebuilding the docs image on commit is acceptable overhead.
- **Con rejected:** Volume-mounting `docs/` and running `mkdocs serve` — the dev server is explicitly not production-safe per the project's own documentation.

---

## Anti-Patterns

### Anti-Pattern 1: Running `mkdocs serve` in Production

**What people do:** Use `squidfunk/mkdocs-material` as the runtime image with `mkdocs serve` or `mkdocs serve --dev-addr 0.0.0.0:8000` as the container entrypoint.

**Why it's wrong:** The MkDocs development server is not designed for production. The official documentation states the Docker image is for local preview only and may have security vulnerabilities. The dev server has no connection handling, no graceful shutdown, no security hardening, and no static file caching.

**Do this instead:** Multi-stage build — Python builder stage produces `site/` then nginx:alpine serves it.

### Anti-Pattern 2: Using `handle_path` Without Setting `site_url`

**What people do:** Use `handle_path /docs/*` in Caddy (which strips the prefix) without setting `site_url` in `mkdocs.yml`.

**Why it's wrong:** MkDocs Material generates absolute asset URLs (`/assets/stylesheets/main.css`). After prefix stripping, the container receives root-relative requests and serves pages correctly. But those pages contain links to `/assets/stylesheets/main.css` — not `/docs/assets/stylesheets/main.css`. The browser fetches `/assets/css/main.css`, which Caddy routes to the dashboard fallback, not the docs container. The page loads with broken CSS and JS.

**Do this instead:** Set `site_url: https://your-domain.com/docs/` in `mkdocs.yml`. Use `handle /docs/*` (no stripping) in Caddy. Configure nginx with `alias` to map `/docs/` to the static root. Asset references become `/docs/assets/...`, which Caddy correctly routes to the docs container.

### Anti-Pattern 3: Committing `openapi.json`

**What people do:** Run the export script locally, commit `docs/api-reference/openapi.json`, update it manually when routes change.

**Why it's wrong:** The committed file will drift from the code. PRs adding routes won't update the spec. The docs silently lie about the API. CI cannot catch the drift because it has no authoritative source to compare against.

**Do this instead:** Generate it in the Dockerfile builder stage from `app.openapi()`. Never commit it (add it to `.gitignore`). If the export fails (e.g., import error from a broken code change), the Docker build fails loudly before broken docs can be deployed.

### Anti-Pattern 4: Embedding an iframe for the Docs Container

**What people do:** Keep the in-app Docs view but replace the markdown renderer with `<iframe src="/docs/">`.

**Why it's wrong:** MkDocs Material's navigation uses `window.history.pushState`. Inside an iframe, navigation changes the iframe's URL but not the parent frame — breaking browser navigation, bookmarks, and direct links. The search sidebar, sticky nav bar, and other Material features assume full viewport control. The result is a cramped, broken UX.

**Do this instead:** Open `/docs/` in a new tab. The docs site is a full SPA-equivalent and should be treated as one.

### Anti-Pattern 5: Separate `docs` Network for the Docs Container

**What people do:** Put the docs container on a separate Docker network, isolated from the main stack.

**Why it's wrong:** Caddy (cert-manager) needs to reach `docs:80` via Docker's internal network. Caddy is on the default compose network. If `docs` is on a separate network, Caddy cannot resolve the hostname.

**Do this instead:** The docs container shares the default compose network (implicit in Docker Compose). No explicit network configuration is needed.

---

## Build Order Recommendation

Four phases with explicit dependencies between them:

**Phase 1 — Infrastructure (docs container + routing):**
Dockerfile, nginx.conf, compose service definition, Caddyfile routing update, `scripts/export_openapi.py`, minimal `docs/mkdocs.yml`, placeholder `docs/index.md`. Validate with `docker compose build docs && docker compose up -d docs`. Confirm `/docs/` returns a page via browser. This gate must pass before writing content.

**Phase 2 — API Reference integration:**
`docs/api-reference/index.md` with `!!swagger openapi.json!!`. Verify the Swagger UI renders correctly in the built site. This is a high-value, low-effort win that validates the build pipeline end-to-end.

**Phase 3 — Dashboard integration:**
Remove `Docs.tsx`, update `AppRoutes.tsx`, add `<a href="/docs/">` to `MainLayout.tsx` sidebar. Small change, but requires Phase 1 so the link target exists.

**Phase 4 — Content:**
Migrate existing `docs/*.md` files into the MkDocs nav structure. Write new user guides, developer docs, security guide, runbooks. Content can be iterated indefinitely after Phase 1-3 ship — each rebuild refreshes the deployed site.

---

## Sources

- [MkDocs Material — Docker Hub (squidfunk/mkdocs-material)](https://hub.docker.com/r/squidfunk/mkdocs-material) — confirms Docker image is for local preview only, not production; HIGH confidence
- [MkDocs Material — Creating your site](https://squidfunk.github.io/mkdocs-material/creating-your-site/) — site_url and build configuration; HIGH confidence
- [mkdocs-render-swagger-plugin — GitHub (bharel)](https://github.com/bharel/mkdocs-render-swagger-plugin) — `!!swagger FILENAME!!` syntax, file-relative resolution; HIGH confidence
- [FastAPI — Extending OpenAPI](https://fastapi.tiangolo.com/how-to/extending-openapi/) — official `app.openapi()` method documentation; HIGH confidence
- [FastAPI — Generate openapi schema without running server (Discussion #1490)](https://github.com/fastapi/fastapi/issues/1490) — confirmed pattern, multiple community verifications; MEDIUM confidence
- [Caddy — handle_path directive](https://caddyserver.com/docs/caddyfile/directives/handle_path) — prefix stripping behaviour confirmed; HIGH confidence
- [Caddy — Common Caddyfile Patterns](https://caddyserver.com/docs/caddyfile/patterns) — path-based routing; HIGH confidence
- [docker-nginx-mkdocs-material (nwesterhausen)](https://github.com/nwesterhausen/docker-nginx-mkdocs-material) — multi-stage build pattern (Python builder + nginx); MEDIUM confidence
- Codebase analysis: `puppeteer/cert-manager/Caddyfile`, `puppeteer/compose.server.yaml`, `puppeteer/dashboard/src/layouts/MainLayout.tsx`, `puppeteer/dashboard/src/AppRoutes.tsx`, `puppeteer/dashboard/src/views/Docs.tsx` (direct read; HIGH confidence)

---

*Architecture research for: MkDocs Material docs container integrated into existing Caddy + Docker Compose stack*
*Researched: 2026-03-16*
