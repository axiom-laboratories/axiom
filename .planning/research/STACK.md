# Stack Research

**Domain:** Enterprise documentation container — MkDocs Material on FastAPI + Docker Compose stack
**Researched:** 2026-03-16
**Confidence:** HIGH (versions verified against PyPI + official changelog + GitHub releases)

---

## Scope

This file covers ONLY the net-new additions for v9.0 Enterprise Documentation. The existing stack
(FastAPI, React/Vite, Postgres, Caddy, Cloudflare tunnel, APScheduler, SQLAlchemy) is already
validated and not repeated here.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| mkdocs-material | 9.7.5 | Docs site generator and theme | Industry standard for project docs; built-in search, dark mode, navigation tabs, admonitions, code highlighting. Python-based, Docker-native, no Node runtime required. Latest stable version verified on PyPI (released 2026-03-10). |
| Python | 3.12 (build stage only) | Runtime for mkdocs-material in the builder stage | mkdocs-material requires >=3.8; Python 3.12 is the current stable. Used only in the multi-stage build — no Python in the final image. |
| nginx:stable-alpine | current stable-alpine | Production static file server | MkDocs' built-in dev server is explicitly documented as not production-safe (per official GitHub issue #1825). nginx:stable-alpine is ~10 MB, zero-config static file serving, correct cache headers, range requests. |
| mkdocs-swagger-ui-tag | 0.8.0 | Embed interactive Swagger UI from OpenAPI JSON | Bundles its own Swagger UI assets locally — no CDN dependency. Critical for air-gapped deployments (MoP targets hostile/isolated environments). Renders `<swagger-ui src="...">` tags in markdown. v0.8.0 released 2026-02-22. Most actively maintained of the three Swagger-in-MkDocs options. |

### Supporting Libraries (pip-installed in builder stage only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mkdocs-git-revision-date-localized-plugin | >=1.2,<2 | Shows "last updated" date on each page from git history | Install when the docs directory is a git checkout with history. Skip if docs are COPY'd in without `.git/`. |
| mkdocs-minify-plugin | >=0.8,<1 | Minifies HTML/JS/CSS output | Reduces static site size by 20-30%. No configuration required; worthwhile in production at negligible build-time cost. |
| pymdown-extensions | (transitive dep of mkdocs-material) | Admonitions, code tabs, tasklists, superfences | Already required by mkdocs-material; no separate pin needed. Listed for clarity. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `squidfunk/mkdocs-material:9` (local preview only) | Live-reload preview during docs authoring | `docker run --rm -p 8000:8000 -v $(pwd)/docs:/docs squidfunk/mkdocs-material serve` — for local use only. Never run `serve` in production. |
| FastAPI `/openapi.json` | Source of truth for API reference | Fetch at build time via `curl http://agent:8001/openapi.json > docs/reference/openapi.json` in the builder stage. Commit a fallback copy for CI builds without a running stack. |

---

## Docker Container Architecture

### Recommended: Two-Stage Dockerfile

```
Stage 1 — Builder  (FROM squidfunk/mkdocs-material:9)
  - pip install mkdocs plugins
  - Optionally curl openapi.json from agent (fallback to committed copy)
  - mkdocs build --strict  →  outputs to /docs/site/

Stage 2 — Serve  (FROM nginx:stable-alpine)
  - COPY --from=builder /docs/site /usr/share/nginx/html
  - Expose :80
  - Final image: ~12 MB, no Python, no MkDocs runtime
```

**Why two stages:** The official mkdocs-material Docker image ships Python, pip, and all build tools. The built output is a self-contained directory of HTML/CSS/JS. Serving it with nginx:alpine is the established production pattern confirmed by multiple community projects. The final image is an order of magnitude smaller than keeping the build tools present.

**Why not run `mkdocs serve` in production:** MkDocs' own documentation and GitHub issue #1825 confirm the built-in HTTP server is intended for preview only, with no keepalive, range requests, or production-grade security.

### Compose Service Snippet

```yaml
# In compose.server.yaml — add alongside existing services
docs:
  build:
    context: ../docs
    dockerfile: Containerfile
  image: localhost/master-of-puppets-docs:v1
  restart: always
  # No direct port exposure — Caddy proxies /docs/* to this container
  depends_on:
    - agent
```

The `docs` service is stateless. No volumes, no database, no secrets. Rebuild the image to update content.

### Caddy Routing Addition

Add to both `:443` and `:80` blocks in `cert-manager/Caddyfile`, before the `handle` fallback:

```
handle /docs* {
    reverse_proxy docs:80
}
```

The `*` glob matches `/docs`, `/docs/`, and `/docs/anything`. Because nginx serves from its root `/usr/share/nginx/html`, `mkdocs.yml` must set `site_url` to include the `/docs` subpath so all internal links and assets resolve correctly:

```yaml
# docs/mkdocs.yml
site_url: https://your-host/docs/
use_directory_urls: true
```

The docs container itself does not need TLS — Caddy terminates TLS and proxies plain HTTP internally, consistent with how `dashboard:80` is already handled.

---

## OpenAPI Integration

### Recommended Approach: Static Fetch at Build Time

1. In `docs/Containerfile` builder stage, after `mkdocs build`:
   ```dockerfile
   ARG AGENT_URL=""
   RUN if [ -n "$AGENT_URL" ]; then \
         curl -sf ${AGENT_URL}/openapi.json -o docs/reference/openapi.json 2>/dev/null || true; \
       fi
   RUN mkdocs build --strict
   ```
2. Commit a reference copy of `docs/reference/openapi.json` in the repo. This ensures CI builds succeed without a running agent. The live fetch overrides it if the agent is available.
3. Reference in a markdown page (e.g., `docs/docs/reference/api.md`):
   ```markdown
   # API Reference

   Interactive API documentation generated from the live OpenAPI schema.

   <swagger-ui src="../openapi.json"/>
   ```
   `mkdocs-swagger-ui-tag` processes this tag and embeds a self-hosted Swagger UI iframe.

### Why mkdocs-swagger-ui-tag over the alternatives

| Plugin | Latest Release | Air-gap Safe | Interactive | Verdict |
|--------|---------------|-------------|-------------|---------|
| mkdocs-swagger-ui-tag | 0.8.0 (Feb 2026) | Yes — bundles assets | Yes — full Swagger UI | **Use this** |
| mkdocs-render-swagger-plugin (bharel) | 0.1.2 (May 2024) | Requires CDN by default | Yes | Not recommended — low activity |
| neoteroi-mkdocs (OpenAPI Docs) | unknown | Yes | No — styled Markdown only | Use if interactive testing not needed |

The air-gap constraint is non-negotiable: MoP targets enterprise and hostile-network environments where CDN access cannot be assumed. mkdocs-swagger-ui-tag is the only option that bundles Swagger UI assets locally while also being actively maintained.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| mkdocs-material 9.7.5 | Docusaurus (React/Node) | If the team prefers MDX and React components in docs. Heavier image (requires Node 18+ runtime), more configuration. Not worth the complexity for this project. |
| mkdocs-swagger-ui-tag | neoteroi-mkdocs | If interactive API testing is not needed and a styled Markdown representation is preferred. Neoteroi renders cleaner prose output but no "Try it out" button. |
| nginx:stable-alpine (serve stage) | Caddy in the docs container | Caddy is already handling TLS termination upstream. Using Caddy inside the docs container would be redundant. nginx:alpine is simpler and smaller for static file serving. |
| Two-stage Dockerfile | Single image with mkdocs serve | No valid production use case. The final image is 15x smaller with two stages. |
| Static openapi.json fetch at build | Runtime JS fetch from `/openapi.json` | Runtime fetch requires cross-origin configuration and fails under strict CSP. Static file is deterministic, cacheable, and works offline. |
| Subpath `/docs` via existing Caddy | Separate subdomain for docs | Separate subdomain adds TLS cert complexity and would require Cloudflare tunnel reconfiguration. Subpath routing is free via the existing Caddy config. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mkdocs serve` in production | Explicitly documented as insecure and unsuitable for production by the MkDocs project (GitHub issue #1825). No keepalive, no cache headers, no range requests. | nginx:stable-alpine as the serve stage |
| CDN-dependent Swagger plugins | Breaks air-gapped deployments. MoP explicitly targets isolated environments. | mkdocs-swagger-ui-tag which bundles Swagger UI assets locally |
| Database in the docs container | Docs are a static site. No state belongs here. Adding a DB would be an architectural error. | Keep the docs container stateless. All content is baked into the image at build time. |
| mkdocs-material Insider (paid features) | Adds Stripe subscription + key management complexity. All features needed for this project (search, navigation, dark mode, code blocks, admonitions) are in the free tier. | mkdocs-material free tier 9.7.5 |
| Pinning to `mkdocs-material:latest` in the build stage | `latest` is a moving target. A minor version bump in mkdocs-material could change plugin compatibility silently. | Pin to `squidfunk/mkdocs-material:9` (major-version pin is stable) and pin plugin versions in `requirements.txt`. |
| Shallow git clone for git-revision-date plugin | The `mkdocs-git-revision-date-localized-plugin` requires full git history to compute last-modified dates. Shallow clones produce incorrect or missing dates. | Use full clone (`--depth 0` or no `--depth` flag) if this plugin is enabled. |

---

## Stack Patterns by Variant

**If docs are built into the image (standard production pattern):**
- COPY the `docs/` directory in the builder stage
- Rebuild the image whenever docs content changes
- `docker compose up -d --build docs` to deploy updates

**If docs use live git-backed content with automatic rebuild:**
- Not recommended for this stack. The compose pattern does not support live volume + live rebuild.
- For a live-editing workflow, use `mkdocs serve` locally against a mounted volume during authoring, then commit and rebuild the image.

**If the agent is not reachable during build (CI, cold start, air-gap):**
- The committed `docs/reference/openapi.json` file is used as fallback
- CI pipelines do not need a running stack to produce a valid docs image
- The fallback file should be regenerated on each agent deployment: `curl https://host/openapi.json > docs/reference/openapi.json && git commit -m "chore: update openapi.json snapshot"`

**If docs need to be published externally (beyond Cloudflare tunnel):**
- The same nginx:alpine container can be published to any CDN or object storage by running `mkdocs build` and uploading the `site/` directory
- No changes to the container architecture needed

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| mkdocs-material 9.7.5 | Python >=3.8; mkdocs <2 | Release notes explicitly cap mkdocs to <2 (confirmed in changelog). Target mkdocs 1.6.x. |
| mkdocs-swagger-ui-tag 0.8.0 | mkdocs-material 9.x | Tested against 9.x series; no known incompatibility. |
| mkdocs-git-revision-date-localized >=1.2 | mkdocs >=1.5 | Requires full git history in build context. |
| nginx:stable-alpine | n/a | Static file serving only; no version coupling to MkDocs output format. |

---

## Installation (requirements for docs/Containerfile builder stage)

```text
# docs/requirements.txt
mkdocs-material==9.7.5
mkdocs-swagger-ui-tag==0.8.0
mkdocs-git-revision-date-localized-plugin>=1.2,<2
mkdocs-minify-plugin>=0.8,<1
```

```dockerfile
# docs/Containerfile
FROM squidfunk/mkdocs-material:9 AS builder
WORKDIR /docs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Attempt live openapi.json fetch; fall back to committed file silently
ARG AGENT_URL=""
RUN if [ -n "$AGENT_URL" ]; then \
      curl -sf ${AGENT_URL}/openapi.json -o docs/reference/openapi.json 2>/dev/null || true; \
    fi
RUN mkdocs build --strict

FROM nginx:stable-alpine AS serve
COPY --from=builder /docs/site /usr/share/nginx/html
EXPOSE 80
```

No new dependencies are added to the main `puppeteer/requirements.txt`. The docs container is entirely self-contained.

---

## Sources

- [mkdocs-material PyPI page](https://pypi.org/project/mkdocs-material/) — version 9.7.5 confirmed, Python >=3.8 requirement (HIGH confidence)
- [mkdocs-material changelog](https://squidfunk.github.io/mkdocs-material/changelog/) — 9.7.5 released 2026-03-10, mkdocs <2 cap confirmed (HIGH confidence)
- [mkdocs-material installation docs](https://squidfunk.github.io/mkdocs-material/getting-started/) — Docker image `squidfunk/mkdocs-material:9` confirmed (HIGH confidence)
- [mkdocs-swagger-ui-tag GitHub](https://github.com/blueswen/mkdocs-swagger-ui-tag) — v0.8.0 released 2026-02-22, bundles Swagger UI assets locally, air-gap safe (HIGH confidence)
- [mkdocs-render-swagger-plugin GitHub](https://github.com/bharel/mkdocs-render-swagger-plugin) — v0.1.2 last release May 2024, lower maintenance activity (HIGH confidence — used to rule out)
- [neoteroi-mkdocs OpenAPI Docs](https://www.neoteroi.dev/mkdocs-plugins/web/oad/) — renders as styled Markdown, not interactive Swagger UI (MEDIUM confidence)
- [MkDocs production Docker issue #1825](https://github.com/squidfunk/mkdocs-material/issues/1825) — official confirmation that `mkdocs serve` is not production-safe (HIGH confidence)
- Existing `puppeteer/cert-manager/Caddyfile` — current routing structure reviewed directly, `/docs*` routing pattern derived from existing `handle /api/*` pattern (HIGH confidence)
- Existing `puppeteer/compose.server.yaml` — service naming, network topology, port conventions reviewed directly (HIGH confidence)

---

*Stack research for: Master of Puppets v9.0 — Enterprise Documentation container*
*Researched: 2026-03-16*
