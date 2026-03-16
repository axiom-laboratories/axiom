# Phase 20: Container Infrastructure & Routing - Research

**Researched:** 2026-03-16
**Domain:** MkDocs Material, Docker multi-stage builds, nginx subpath routing, Caddy handle semantics, Cloudflare Access path policy
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CF Access scope:**
- Gate all of `/docs/*` — not just security-sensitive subdirectories
- CF Access at the Cloudflare edge is the sole gate; Caddy does not add secondary JWT validation
- Same allowlist/policy as the dashboard — any operator who can access the dashboard can access docs
- One policy, one Caddyfile block — no conditional routing

**Content source location:**
- New `docs/` directory at the repo root (alongside `puppeteer/`, `puppets/`, etc.)
- Existing `puppeteer/docs/` markdown files are left in place and ignored in Phase 20
- No migration or deletion of existing files in this phase

**MkDocs skeleton:**
- Minimal viable `mkdocs.yml`: `theme: material`, `site_url`, and plugins only — no nav defined yet
- Include both the `privacy` plugin (self-hosts Google Fonts and external assets) and the `offline` plugin (bundles JS/CSS into the static build) to fully satisfy INFRA-06
- Single placeholder `docs/index.md` with "Documentation coming soon" — enough to pass `--strict` without creating misleading content
- Nav structure is deferred to content phases (Phase 23 locks it per STATE.md decision)

**Dockerfile & build:**
- Two-stage Dockerfile: `python:3.12-slim` builder stage + `nginx:alpine` serve stage
- Builder stage runs `RUN mkdocs build --strict` directly — no wrapper script
- Build failure = `docker compose build docs` fails; the rest of the stack is unaffected
- Serve stage uses a custom nginx.conf with `location /docs/ { alias /usr/share/nginx/html/; }` — required for correct asset routing (default nginx config causes 404s on all CSS/JS under the subpath)

**Routing (confirmed in STATE.md):**
- Caddy uses `handle /docs/*` (NOT `handle_path`) to preserve the `/docs/` prefix when proxying to nginx
- `site_url: https://dev.master-of-puppets.work/docs/` baked into mkdocs.yml so all asset references are absolute with the subpath

### Claude's Discretion
- nginx port choice inside the container (80 is fine)
- Docker service name for the docs container in compose.server.yaml
- Exact MkDocs Material theme palette/colour settings for the skeleton
- Pin versions for mkdocs and mkdocs-material in requirements.txt

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Operator can run `docker compose up` and have the docs container serve the MkDocs site at `/docs/` | Two-stage Dockerfile + compose.server.yaml service definition + Caddy handle block |
| INFRA-02 | Docs container is a separate service in `compose.server.yaml` (portable, no coupling to agent or dashboard) | Service follows existing `dashboard` pattern: local build context, no exposed ports, Caddy proxies |
| INFRA-03 | Docs site builds with `--strict` flag (warnings treated as errors) | `RUN mkdocs build --strict` in builder stage; any MkDocs warning becomes a Docker build failure |
| INFRA-04 | Caddy routes `/docs/*` to the docs container with correct asset URL handling (`site_url` aligned) | `handle /docs/*` (not handle_path) + nginx `alias` + `site_url` in mkdocs.yml all three must align |
| INFRA-05 | `/docs/*` path is protected by Cloudflare Access policy (not publicly exposed) | New CF Access application for `dev.master-of-puppets.work/docs/*` — same policy as dashboard |
| INFRA-06 | Docs site works offline / air-gapped (no external CDN assets at runtime) | `privacy` plugin downloads all external assets at build time; `offline` plugin converts search index to JS file |
</phase_requirements>

---

## Summary

Phase 20 is a pure infrastructure phase with no content. It creates the container, wires up routing, and locks down access — so the site is live and protected before a single real page is written.

The most critical technical constraint is the three-way alignment between MkDocs, nginx, and Caddy. MkDocs must have `site_url: https://dev.master-of-puppets.work/docs/` so it generates absolute asset paths. nginx must use `location /docs/ { alias /usr/share/nginx/html/; }` to serve those absolute paths correctly without stripping the prefix. Caddy must use `handle /docs/*` (not `handle_path /docs/*`) to forward the full `/docs/...` URI to nginx unchanged. Breaking any one of these three produces silent CSS/JS 404s.

The offline/air-gap requirement (INFRA-06) is satisfied by enabling both the `privacy` plugin (downloads all Google Fonts and external assets at build time) and the `offline` plugin (converts the search index to a bundled JS file, eliminating runtime Fetch API calls). Both are built into `mkdocs-material` 9.x at no additional install cost. CF Access protection (INFRA-05) requires creating a new path-scoped application in the Cloudflare Zero Trust dashboard pointing to `dev.master-of-puppets.work/docs/*` with the same allow policy as the dashboard application.

**Primary recommendation:** Wire up all three routing layers (mkdocs.yml `site_url` → nginx `alias` → Caddy `handle`) in one atomic task; testing any one layer in isolation will give false confidence.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs-material | 9.7.5 (latest stable as of 2026-03-10) | MkDocs theme + built-in plugins | Locked by STATE.md; privacy + offline plugins included; all Insider features free since 9.7.0 |
| mkdocs | Ships as mkdocs-material dependency | Static site generator | Pulled automatically; no separate pin needed |
| nginx:alpine | latest stable alpine variant | Static file server in serve stage | Established pattern in this repo (dashboard Containerfile) |
| python:3.12-slim | 3.12-slim | Builder stage base image | Locked by STATE.md; slim keeps image small |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mkdocs-material[recommended] | same | Enables image optimization extras | If optimize plugin needed (not required in Phase 20) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nginx:alpine serve stage | python:3.12-slim running `mkdocs serve` | `mkdocs serve` is not production-safe (GitHub issue #1825 — file descriptor exhaustion under load); nginx is correct |
| `handle /docs/*` (Caddy) | `handle_path /docs/*` | `handle_path` strips the prefix before proxying; nginx would receive `/assets/…` not `/docs/assets/…`; this breaks routing |
| `alias` in nginx | `root` directive | `root` appends the URI to the path — a request for `/docs/assets/main.css` would resolve to `/usr/share/nginx/html/docs/assets/main.css` (missing the `docs/` level); `alias` replaces the location prefix correctly |

**Installation (builder stage requirements.txt):**
```
mkdocs-material==9.7.5
```
`mkdocs`, `jinja2`, and all other dependencies are pulled transitively.

---

## Architecture Patterns

### Recommended File Structure

```
docs/                        # repo root — new directory
├── mkdocs.yml               # MkDocs configuration
├── requirements.txt         # mkdocs-material==9.7.5
├── Dockerfile               # two-stage build
├── nginx.conf               # custom nginx config (subpath alias)
└── docs/                    # MkDocs source files
    └── index.md             # placeholder: "Documentation coming soon"

puppeteer/
├── cert-manager/
│   └── Caddyfile            # add handle /docs/* block before fallback
└── compose.server.yaml      # add docs service
```

### Pattern 1: Two-Stage Dockerfile

**What:** Builder stage installs Python deps + runs `mkdocs build --strict`, emitting static HTML to `/site`. Serve stage copies only `/site` into nginx image — no Python runtime in production.

**When to use:** Always for MkDocs. `mkdocs serve` is unsafe in production; static files served by nginx have correct caching semantics and no file-descriptor leaks.

```dockerfile
# Source: STATE.md + established dashboard Containerfile pattern
FROM python:3.12-slim AS builder
WORKDIR /docs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdocs build --strict

FROM nginx:alpine
COPY --from=builder /docs/site /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Pattern 2: nginx Custom Config for Subpath Serving

**What:** nginx's default config serves at `/`. For a subpath like `/docs/`, requests arrive with the full `/docs/assets/stylesheets/main.css` URI. The `alias` directive replaces the `/docs/` prefix with the document root, mapping `/docs/foo` → `/usr/share/nginx/html/foo`.

**Critical rule:** trailing slash on both `location` and `alias` — omitting either causes nginx to miss path separator and return 404.

```nginx
# Source: nginx official docs + verified against alias directive semantics
server {
    listen 80;
    location /docs/ {
        alias /usr/share/nginx/html/;
        index index.html;
        try_files $uri $uri/ $uri.html =404;
    }
}
```

### Pattern 3: Caddy `handle /docs/*` Routing

**What:** `handle` forwards the request URI unchanged to the upstream. The upstream (nginx) receives `/docs/assets/…` and uses `alias` to map it correctly. `handle_path` would strip the `/docs/` prefix, causing nginx to look for `/assets/…` which doesn't exist under its document root.

**Insert before the dashboard fallback `handle` block** — Caddy evaluates handles in order; the catch-all must come last.

```caddyfile
# Source: Caddy official docs, handle vs handle_path distinction
handle /docs/* {
    reverse_proxy docs:80
}

# Dashboard fallback — must remain LAST
handle {
    reverse_proxy dashboard:80
}
```

### Pattern 4: Minimal mkdocs.yml Skeleton

**What:** Bare minimum to pass `--strict` with both required plugins enabled.

```yaml
# Source: MkDocs Material official docs
site_name: Master of Puppets
site_url: https://dev.master-of-puppets.work/docs/
theme:
  name: material
plugins:
  - search
  - privacy
  - offline
```

**Notes:**
- `search` must be listed explicitly when `plugins:` key is defined — Material enables it by default only when no `plugins:` key exists.
- `privacy` plugin requires network access during `docker build` to download external assets (Google Fonts). Build environment must have internet access, or pre-caching is needed. In this project's compose setup the builder runs with internet access.
- `offline` plugin sets `use_directory_urls: false` automatically, which is fine for the subpath serve pattern.

### Pattern 5: compose.server.yaml Service Entry

**What:** Follows the established `dashboard` service pattern — local build, no exposed ports, Caddy proxies via service name.

```yaml
# Source: existing compose.server.yaml dashboard service pattern
docs:
  image: localhost/master-of-puppets-docs:v1
  build:
    context: ../docs
    dockerfile: Dockerfile
  restart: always
```

No volumes needed — static files are baked into the image. No `depends_on` needed — docs has no runtime dependency on the agent or DB.

### Anti-Patterns to Avoid

- **Using `handle_path /docs/*` in Caddy:** Strips the prefix before proxying. nginx receives `/assets/…` which doesn't match its `location /docs/` block → all CSS/JS return 404. The site appears to load (HTML is served) but renders unstyled.
- **Using `root` directive in nginx instead of `alias`:** `root` appends the full URI to the path. `/docs/assets/main.css` resolves to `/usr/share/nginx/html/docs/assets/main.css` — the nested `docs/` directory doesn't exist in the image.
- **Omitting `site_url` from mkdocs.yml:** MkDocs generates relative asset paths, which resolve correctly from `https://…/docs/` but break at any deeper URL (e.g., `https://…/docs/guide/setup/`) because `../../assets/` math fails when the depth is wrong.
- **Omitting `search` from the plugins list:** When `plugins:` key is defined, MkDocs does not auto-include search. The `--strict` build will warn about an empty search index, causing the build to fail.
- **Using `mkdocs serve` in production:** Known file-descriptor exhaustion issue (mkdocs #1825). Always use nginx for the serve stage.
- **Missing trailing slash on nginx `alias`:** `location /docs/ { alias /usr/share/nginx/html; }` (no trailing slash on alias) causes path concatenation to become `/usr/share/nginx/htmlassets/main.css` → 404.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| External asset self-hosting | Custom download script in Dockerfile | `privacy` plugin in mkdocs.yml | Plugin handles recursive scanning, CSS font references, caching, and GDPR compliance |
| Offline search bundling | Custom webpack/rollup step | `offline` plugin in mkdocs.yml | Plugin handles search worker shim, iframe-worker, and `use_directory_urls` adjustment |
| Subpath asset rewriting | nginx `sub_filter` or lua | `site_url` in mkdocs.yml + `alias` in nginx | MkDocs bakes absolute paths at build time; no runtime rewriting needed |

**Key insight:** MkDocs Material's built-in plugins eliminate all the complexity of air-gap compliance. The `privacy` plugin recursively downloads and rewrites every external reference (including assets inside CSS files like Google Fonts). Combined with `offline`, the resulting static site has zero external dependencies — without any custom tooling.

---

## Common Pitfalls

### Pitfall 1: The "prefix stripping triangle" silently breaks assets

**What goes wrong:** The site HTML loads (Caddy returns 200 for the HTML), but all CSS, JS, and fonts return 404. The site renders as unstyled text.

**Why it happens:** One of three things is misaligned:
1. Caddy uses `handle_path` — strips `/docs/` before sending to nginx
2. nginx uses `root` instead of `alias` — constructs wrong filesystem path
3. `site_url` missing or wrong — MkDocs generates relative paths that break at non-root depth

**How to avoid:** Set all three together, test with a deep URL like `/docs/assets/stylesheets/main.css` in the browser network tab, not just `/docs/`.

**Warning signs:** HTML returns 200, CSS/JS return 404. Browser DevTools shows mixed absolute/relative asset URLs.

### Pitfall 2: `--strict` fails due to missing `search` plugin

**What goes wrong:** `docker compose build docs` fails with "search plugin not found" or a warning about no search index.

**Why it happens:** When the `plugins:` key is defined in mkdocs.yml, MkDocs disables all default plugins including `search`. If `search` is not explicitly listed, and `--strict` is set, the warning becomes a fatal error.

**How to avoid:** Always list `search` first in the plugins block when defining `plugins:`.

**Warning signs:** Build fails immediately with a plugin-related warning rather than a content warning.

### Pitfall 3: Privacy plugin requires internet access during build

**What goes wrong:** `docker compose build docs` hangs or fails trying to download Google Fonts from `fonts.googleapis.com`.

**Why it happens:** The `privacy` plugin fetches external assets during the MkDocs build, which runs in the Docker builder stage. If the build environment is firewalled (unlikely for local dev, possible in CI), downloads fail.

**How to avoid:** For local dev this is fine. For CI pipelines (future), either pre-seed the `.cache/plugin/privacy` cache or configure `assets_fetch: false` in CI.

**Warning signs:** Build hangs at "Collecting external assets" step, or fails with connection timeout.

### Pitfall 4: CF Access path `/docs/*` does not cover `/docs` (no trailing slash)

**What goes wrong:** A direct request to `https://dev.master-of-puppets.work/docs` (without trailing slash) bypasses CF Access.

**Why it happens:** Cloudflare Access path matching: `/docs/*` covers `/docs/anything` but not the bare `/docs` path.

**How to avoid:** Also add `/docs` (no wildcard) as a second path on the same CF Access application, or rely on nginx to redirect `/docs` → `/docs/` (nginx serves index.html on directory requests with `alias`). Verify by hitting the bare path in an incognito window.

**Warning signs:** `/docs/` requires auth challenge; `/docs` loads without challenge.

### Pitfall 5: `offline` plugin sets `use_directory_urls: false`

**What goes wrong:** URL structure changes between a build with and without `offline` plugin enabled.

**Why it happens:** The offline plugin disables directory URLs so pages work as flat `file://` paths. With directory URLs: `/docs/guide/` → `guide/index.html`. Without: `/docs/guide/` → `guide.html`.

**How to avoid:** In Phase 20 with a single `index.md`, this is irrelevant. Document for Phase 22+ content phases: the URL structure used in content phases must account for `use_directory_urls: false` if offline remains enabled. Since this site is served over HTTP (not `file://`), consider whether to keep or disable the offline plugin after content phases are complete.

**Warning signs:** Internal links in content phases produce 404s.

---

## Code Examples

### Verified: Minimal mkdocs.yml with both plugins

```yaml
# Source: https://squidfunk.github.io/mkdocs-material/plugins/offline/
#         https://squidfunk.github.io/mkdocs-material/plugins/privacy/
site_name: Master of Puppets
site_url: https://dev.master-of-puppets.work/docs/
theme:
  name: material
plugins:
  - search
  - privacy
  - offline
```

### Verified: nginx alias for subpath (trailing slash critical)

```nginx
# Source: nginx official docs — alias directive
server {
    listen 80;
    location /docs/ {
        alias /usr/share/nginx/html/;
        index index.html;
        try_files $uri $uri/ $uri.html =404;
    }
}
```

### Verified: Caddy `handle` (not `handle_path`) pattern

```caddyfile
# Source: https://caddyserver.com/docs/caddyfile/directives/handle
# Insert BEFORE the final `handle` fallback block
handle /docs/* {
    reverse_proxy docs:80
}
```

### Verified: Two-stage Dockerfile pattern (from project's own dashboard Containerfile)

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /docs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdocs build --strict

FROM nginx:alpine
COPY --from=builder /docs/site /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Verified: compose.server.yaml docs service (follows dashboard pattern)

```yaml
docs:
  image: localhost/master-of-puppets-docs:v1
  build:
    context: ../docs
    dockerfile: Dockerfile
  restart: always
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MkDocs Material "Insiders" (paid) for privacy + offline plugins | All plugins free in 9.7.0+ | 2024 | No sponsorship required; privacy and offline plugins available to everyone |
| `mkdocs serve` in production | nginx:alpine serve stage | Long-standing recommendation | Eliminates file-descriptor exhaustion (issue #1825) |
| Manual external asset handling | Built-in `privacy` plugin | Material 8.x+ | Zero custom tooling needed for air-gap compliance |

**Deprecated/outdated:**
- Separate `mkdocs-material-insiders` package: Insider features merged into public package as of 9.x. Do not attempt to install a separate insiders wheel.

---

## Open Questions

1. **CF Access `/docs` (no trailing slash) coverage**
   - What we know: Cloudflare Access `/docs/*` covers subpaths but not the bare `/docs` path per official docs
   - What's unclear: Whether nginx's `alias` + `index index.html` causes an automatic redirect from `/docs` to `/docs/` at the nginx level (before CF Access applies) — if Caddy receives `/docs` and nginx 301s to `/docs/`, the redirect itself may not be protected
   - Recommendation: Add both `/docs` and `/docs/*` as paths on the CF Access application, OR test the bare path explicitly as a verification step

2. **`offline` plugin and `use_directory_urls: false` impact on future content**
   - What we know: Offline plugin disables directory URLs; in Phase 20 this doesn't matter (single placeholder page)
   - What's unclear: Whether content phases 22–25 need `use_directory_urls: true` (natural URL structure) which would conflict with offline plugin
   - Recommendation: Defer to Phase 22 — document as a known decision point. The offline plugin can be disabled for server-hosted sites once content is stable.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` or inline / `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `docker compose build docs` (validates INFRA-01/02/03 in one step) |
| Full suite command | `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `docker compose up` starts docs container; site reachable at `/docs/` | smoke | `curl -sf http://localhost/docs/ \| grep -q "Documentation"` (after compose up) | Wave 0 |
| INFRA-02 | docs is a separate service, no coupling to agent/db | structural | `docker compose config --services \| grep docs` | Wave 0 (compose file) |
| INFRA-03 | `mkdocs build --strict` fails loudly on warnings | build | `docker compose build docs` (fails non-zero on strict violations) | Wave 0 (Dockerfile) |
| INFRA-04 | Deep asset URL `/docs/assets/stylesheets/main.css` returns 200 | smoke | `curl -sf http://localhost/docs/assets/stylesheets/main.css -o /dev/null -w "%{http_code}"` | Wave 0 |
| INFRA-05 | `/docs/*` returns CF Access challenge without valid session | manual | Private window navigation to `https://dev.master-of-puppets.work/docs/` | Manual only — CF Access operates at edge, not testable locally |
| INFRA-06 | No external CDN requests at runtime | manual | Browser network tab, offline mode, or `mkdocs build` output showing "Downloaded N external assets" | Semi-manual (build log) |

### Sampling Rate

- **Per task commit:** `docker compose build docs` (fail-fast on build errors)
- **Per wave merge:** `docker compose up -d && curl -sf http://localhost/docs/ && curl -sf "http://localhost/docs/assets/stylesheets/main.css" -o /dev/null -w "%{http_code}"`
- **Phase gate:** Full routing smoke test + manual CF Access verification before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `docs/mkdocs.yml` — main config file (create in Wave 0)
- [ ] `docs/requirements.txt` — mkdocs-material pin (create in Wave 0)
- [ ] `docs/Dockerfile` — two-stage build (create in Wave 0)
- [ ] `docs/nginx.conf` — custom nginx config with alias (create in Wave 0)
- [ ] `docs/docs/index.md` — placeholder content (create in Wave 0)
- [ ] CF Access application for `/docs/*` path — configured in Cloudflare Zero Trust dashboard (manual step, Wave 0)

---

## Sources

### Primary (HIGH confidence)
- MkDocs Material official docs — privacy plugin: https://squidfunk.github.io/mkdocs-material/plugins/privacy/
- MkDocs Material official docs — offline plugin: https://squidfunk.github.io/mkdocs-material/plugins/offline/
- MkDocs Material official docs — building for offline usage: https://squidfunk.github.io/mkdocs-material/setup/building-for-offline-usage/
- PyPI mkdocs-material — version 9.7.5 confirmed as latest stable (2026-03-10): https://pypi.org/project/mkdocs-material/
- Caddy official docs — handle directive: https://caddyserver.com/docs/caddyfile/directives/handle
- Caddy official docs — handle_path directive: https://caddyserver.com/docs/caddyfile/directives/handle_path
- nginx official docs — serving static content / alias: https://docs.nginx.com/nginx/admin-guide/web-server/serving-static-content/
- Cloudflare One docs — application paths: https://developers.cloudflare.com/cloudflare-one/access-controls/policies/app-paths/
- Existing project files: `puppeteer/cert-manager/Caddyfile`, `puppeteer/compose.server.yaml`, `puppeteer/dashboard/Containerfile` — direct inspection

### Secondary (MEDIUM confidence)
- STATE.md decision record — Caddy `handle` vs `handle_path`, nginx alias, site_url requirement — confirmed from prior project research
- CONTEXT.md implementation decisions — confirmed locked choices align with research findings

### Tertiary (LOW confidence)
- mkdocs issue #1825 (mkdocs serve file-descriptor exhaustion) — referenced in STATE.md, not independently re-verified in this research session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against PyPI (9.7.5), pattern confirmed against existing project Containerfiles
- Architecture: HIGH — all three routing layers verified against official Caddy, nginx, and MkDocs docs; existing project Caddyfile and compose.server.yaml inspected directly
- Pitfalls: HIGH — prefix-stripping triangle documented in STATE.md and confirmed by official docs; plugin interaction verified against MkDocs Material official docs
- CF Access path: MEDIUM — official docs confirm `/docs/*` scope and the bare `/docs` gap; actual CF dashboard UI steps not verified in this session

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable tools; mkdocs-material version should be re-pinned if > 30 days pass)
