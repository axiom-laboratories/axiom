# Project Research Summary

**Project:** Master of Puppets v9.0 — Enterprise Documentation
**Domain:** Containerised static documentation site (MkDocs Material) integrated into existing Caddy + Docker Compose stack
**Researched:** 2026-03-16
**Confidence:** HIGH

## Executive Summary

Master of Puppets v9.0 adds a self-hosted, offline-capable MkDocs Material documentation site to an already mature orchestration platform. The recommended approach is a two-stage Docker build: a Python builder stage that imports the FastAPI app to generate `openapi.json` and runs `mkdocs build --strict`, followed by an `nginx:stable-alpine` serve stage that ships only the pre-built static HTML. The docs container slots into the existing Caddy routing layer at `/docs/*` as a new stateless service with no database, no secrets, and no runtime dependencies. This architecture is validated by official MkDocs documentation and community production patterns, and it integrates cleanly with the existing `compose.server.yaml`, Caddyfile, and Cloudflare Tunnel setup without touching any other service.

The recommended stack (mkdocs-material 9.7.5, mkdocs-swagger-ui-tag 0.8.0, nginx:stable-alpine) is straightforward and well-supported. The project benefits from Material 9.7.0's decision to open-source all previously Insider-only features, which means the privacy plugin (essential for air-gapped deployments), offline plugin, and social cards are all available in the free tier. The content work is the dominant effort — eight feature guide pages, a security and compliance guide, a getting-started walkthrough, runbooks, and an auto-generated API reference — all of which must be written to a standard that meets the enterprise expectations of MoP's target user base.

The primary risks are not technical but operational: Caddy path routing misconfiguration (the `handle_path` prefix-stripping trap that silently breaks all CSS/JS assets), OpenAPI snapshot drift if generation is not automated in the build pipeline, and docs served unauthenticated via the existing Cloudflare Tunnel. All three risks are preventable by addressing them in the infrastructure phase before writing a word of content. The security risk in particular must not be deferred — detailed mTLS architecture and token schema documentation should only be accessible behind the same Cloudflare Access policy that protects the dashboard.

## Key Findings

### Recommended Stack

The net-new stack additions for v9.0 are minimal and self-contained. MkDocs Material 9.7.5 is the Python-based static site generator with a comprehensive feature set that requires no Node runtime — a significant advantage for a Docker-native stack. The two-stage Dockerfile uses `squidfunk/mkdocs-material:9` as the builder base and `nginx:stable-alpine` as the production serve stage, producing a ~12-25 MB final image with zero Python attack surface. The `mkdocs-swagger-ui-tag` plugin (0.8.0) is the only externally hosted Swagger plugin that bundles its own UI assets locally, making it the only viable choice for air-gapped deployments. All existing Puppeteer infrastructure (FastAPI, Caddy, Postgres, Docker Compose) is unchanged.

**Core technologies:**
- `mkdocs-material 9.7.5`: Static site generator + theme — industry standard, all Insider features now free, Python-native, Docker-friendly
- `nginx:stable-alpine`: Production static file server — ~10 MB, zero-config, correct MIME types and cache headers; `mkdocs serve` is explicitly not production-safe per official docs (issue #1825)
- `mkdocs-swagger-ui-tag 0.8.0`: Interactive API reference from `openapi.json` — the only actively maintained option that bundles Swagger UI assets locally (air-gap safe)
- `mkdocs-git-revision-date-localized-plugin >=1.2`: "Last updated" dates from git history — requires full clone and `git` binary in builder stage
- `mkdocs-minify-plugin >=0.8`: Build-time HTML/CSS/JS minification — 20-30% size reduction, no configuration

### Expected Features

The feature set divides cleanly into infrastructure (container + routing + toolchain — all done once in Phase 1) and content (guides and reference material — the bulk of the work across subsequent phases). Navigation must be audience/task-oriented from the start, not component-oriented; this is the single most common structural failure mode in infrastructure tool documentation.

**Must have (table stakes for enterprise-credible docs):**
- Full-text client-side search with offline support — built-in, critical for air-gapped deployments
- Navigation tabs separating audiences (Getting Started / Feature Guides / Security and Compliance / Developer / API Reference)
- Code blocks with syntax highlighting and copy-to-clipboard — built-in
- Admonitions (warning/danger callouts) — critical for security documentation
- Dark/light mode with OS preference detection — built-in
- Getting started guide: Install → enroll node → sign job → dispatch job (single linear walkthrough, no section-jumping)
- Feature guides for all v7/v8 features: Foundry, Smelter, mop-push CLI, job scheduling, RBAC, OAuth device flow, Staging view, node management
- Security and compliance guide: mTLS setup, cert rotation, Ed25519 signing, RBAC config, audit log, air-gap deployment
- Runbooks and troubleshooting organised by symptom, not by component
- Auto-generated API reference from static `openapi.json` via Swagger UI
- Privacy + offline plugins to ensure zero external CDN calls (non-negotiable for air-gap)
- Dashboard integration: replace `Docs.tsx` inline renderer with external link to `/docs/`

**Should have (differentiators vs. generic project README):**
- Mermaid diagrams for architecture (version-controlled, rendered client-side — no PNG drift)
- Annotated code blocks for Dockerfile and compose file examples
- Page-level "last updated" dates (git revision plugin)
- "Edit this page" links to source repo
- Instant loading (SPA-like navigation, built-in)
- Content tabs for multi-platform instructions (Docker vs bare-metal)

**Defer to v10+:**
- Versioned docs via `mike` — only meaningful once multiple released versions are in active use
- SLSA provenance documentation — awaits the feature itself
- CI/CD integration guide — awaits the CI/CD API endpoints milestone
- PDF export — fragile with Material theme CSS, not worth the maintenance cost

### Architecture Approach

The docs container is inserted as a new stateless service into the existing Caddy routing layer. Caddy receives all requests, routes `/docs/*` to the docs container (nginx:80), and continues routing `/api/*`, `/auth/*`, `/ws`, and `/system/*` to the agent as before. The critical architectural detail is that `site_url` in `mkdocs.yml` must be set to `https://dev.master-of-puppets.work/docs/` so MkDocs bakes the `/docs/` subpath into every asset reference — and Caddy must use `handle /docs/*` without prefix stripping, matched by an nginx `alias` directive inside the container. Using Caddy's `handle_path` with prefix stripping silently breaks all CSS/JS assets (they reference `/docs/assets/...` in the HTML but would be requested without the prefix from the serve root).

**Major components:**
1. `puppeteer/docs-container/Dockerfile` — multi-stage: `python:3.12-slim` builder (installs MkDocs + agent deps, generates openapi.json via `app.openapi()`, runs `mkdocs build --strict`) + `nginx:alpine` serve stage
2. `puppeteer/docs-container/nginx.conf` — `alias`-based static file serving mapping `/docs/` URL prefix to the static site root
3. `docs/mkdocs.yml` — MkDocs configuration: Material theme, nav structure, privacy/offline/search plugins, `site_url` set to deployment path
4. `scripts/export_openapi.py` — imports `agent_service.main.app` and calls `app.openapi()` without starting an HTTP server; writes `docs/api-reference/openapi.json`
5. `puppeteer/cert-manager/Caddyfile` — add `handle /docs/*` block before the dashboard fallback in both `:443` and `:80` server blocks
6. Dashboard modifications — remove `Docs.tsx`, remove `/docs` Route from `AppRoutes.tsx`, add `<a href="/docs/" target="_blank">` with `BookOpen` icon to `MainLayout.tsx` sidebar

### Critical Pitfalls

1. **`mkdocs serve` in production** — Use a two-stage Docker build with `nginx:alpine` as the serve stage. The MkDocs dev server is explicitly documented as unsuitable for production (no concurrency, no security hardening, no caching). Never use `CMD ["mkdocs", "serve"]` in the docs Containerfile.

2. **Caddy prefix routing breaking asset URLs** — Always set `site_url: https://dev.master-of-puppets.work/docs/` in `mkdocs.yml` and use `handle /docs/*` (not `handle_path`) in the Caddyfile. Configure nginx with an `alias` directive, not `root`. Failing to do this causes all CSS/JS to silently 404 while pages appear to load.

3. **OpenAPI snapshot drift** — Generate `openapi.json` in the Dockerfile builder stage by importing `app.openapi()` directly — never commit a static snapshot or rely on a running server. If the export fails (broken import), the Docker build fails loudly before stale docs can be deployed.

4. **Docs served unauthenticated via Cloudflare Tunnel** — The security and compliance guide contains mTLS architecture details, token schemas, and cert formats that constitute material intelligence for an attacker. Verify that `/docs*` is covered by the existing Cloudflare Access policy before the container goes live. Test from an unauthenticated private browser window.

5. **Navigation structured by component instead of task** — The top-level nav must be audience/task-oriented from day one (Getting Started / Feature Guides / Security / Developer / API Reference). Reorganising nav after content is written requires updating internal links across all pages. Establish the nav structure in Phase 1 before any content is written.

## Implications for Roadmap

Based on the research, the milestone has a clear natural phase order driven by hard dependencies: infrastructure must be working before API reference can be validated, API reference validation confirms the full build pipeline before dashboard integration makes sense, and content phases can only be accurate if the system they describe is fully operational.

### Phase 1: Container Infrastructure and Routing

**Rationale:** Everything else depends on this. The docs container, Caddy routing, nginx config, multi-stage Dockerfile, and `site_url` / `alias` configuration must be correct before any content is written. Three of the five critical pitfalls are addressed here: `mkdocs serve` in production, Caddy prefix routing, and unauthenticated access. Getting the routing right now avoids the silent asset-404 failure mode that only manifests when content pages exist.

**Delivers:** A working docs container at `/docs/` behind the existing Cloudflare Tunnel + Caddy stack, with correct asset routing, Cloudflare Access policy covering `/docs*`, and `mkdocs build --strict` running in the Docker builder stage. Placeholder `index.md` only — no content yet.

**Addresses:** Container setup (FEATURES P1), offline + privacy plugins (FEATURES P1), `--strict` build enforcement

**Avoids:** Pitfall 1 (mkdocs serve), Pitfall 3 (Caddy routing), Pitfall 6 (unpinned dependencies), Pitfall 9 (unauthenticated docs)

### Phase 2: API Reference Pipeline

**Rationale:** The `scripts/export_openapi.py` → `mkdocs-swagger-ui-tag` → Swagger UI pipeline is a non-trivial integration with its own failure modes (import-time side effects from SQLAlchemy models, `site_url` interaction with the swagger iframe). Validating it early confirms the full build pipeline end-to-end and produces a high-value deliverable (the API reference) with low content-writing effort.

**Delivers:** Auto-generated, always-in-sync API reference page at `/docs/api-reference/` with interactive Swagger UI rendered from `app.openapi()`. The generated `openapi.json` is excluded from git and produced fresh on every image build.

**Addresses:** API reference (FEATURES P1), OpenAPI drift prevention

**Avoids:** Pitfall 2 (OpenAPI snapshot drift)

### Phase 3: Dashboard Integration

**Rationale:** Once the docs container is stable enough to not show a blank page, the in-app `Docs.tsx` can be replaced. This is a small change (three files: delete `Docs.tsx`, update `AppRoutes.tsx`, update `MainLayout.tsx`) but it depends on Phase 1 existing so the link target resolves. The `VITE_DOCS_URL` env var defaulting to `/docs/` must be used — no hardcoded localhost URLs.

**Delivers:** Dashboard sidebar "Documentation" link opens `/docs/` in a new tab. `Docs.tsx` deleted. Old in-app markdown rendering removed.

**Addresses:** Dashboard integration (FEATURES P1)

**Avoids:** Pitfall 8 (hardcoded docs URL)

### Phase 4: Getting Started Guide and Navigation Architecture

**Rationale:** The getting-started guide is the highest-value content page and must establish the navigation architecture for all subsequent content. Nav must be task/audience-oriented (not component-oriented) before other guides are written, otherwise internal links will need mass-updating later. The getting-started guide is a single linear walkthrough that must be tested on a fresh machine (using the existing `manage-test-nodes` LXC skill) before it is considered complete.

**Delivers:** Task-oriented navigation structure in `mkdocs.yml`, landing page (`index.md`), and a complete end-to-end getting-started walkthrough (Install → deploy stack → install Root CA → enroll first node → sign first job → dispatch first job).

**Addresses:** Getting started (FEATURES P1), navigation architecture (FEATURES P1 — navigation tabs)

**Avoids:** Pitfall 7 (component-oriented nav), Pitfall 4 (stale docs — guide must be tested against live system)

### Phase 5: Security and Compliance Guide

**Rationale:** Security documentation is the primary enterprise differentiator and the highest-risk content to get wrong. It must cover mTLS prerequisites, CA installation (Linux/macOS/Windows/NSS), join token behaviour, Ed25519 key generation and why the private key must never be uploaded, cert rotation procedure, and failure diagnosis. Each procedure must follow the Prerequisites → Operation → Verify → Diagnose failure pattern. This phase also requires the most careful review for what must not appear in publicly accessible docs (CA fingerprint examples, full JOIN_TOKEN schema with example values, internal hostnames).

**Delivers:** Dedicated security and compliance section: mTLS setup, cert rotation, Ed25519 signing, RBAC configuration, audit log, air-gap deployment guide. Each procedure tested on a fresh environment.

**Addresses:** Security and compliance guide (FEATURES P1), security differentiation vs. Rundeck/Prefect

**Avoids:** Pitfall 5 (missing security prerequisites), Pitfall 9 (security-sensitive content in public docs)

### Phase 6: Feature Guides

**Rationale:** Feature guides are high-effort content but follow a predictable pattern (what it does → prerequisites → step-by-step usage → common errors). With the nav structure already established in Phase 4, each guide slots into the existing structure. Guides must be reviewed against the live codebase on the same day they are merged — not when they were written.

**Delivers:** One guide page per major system feature: Foundry image builder, Smelter Registry, mop-push CLI, job scheduling / job definitions, RBAC and user management, OAuth device flow, job staging and lifecycle, node management.

**Addresses:** Feature guides (FEATURES P1 — 8 pages)

**Avoids:** Pitfall 4 (stale docs at launch — "review against live code" gate on every guide PR)

### Phase 7: Runbooks and Troubleshooting

**Rationale:** Runbooks are the deliverable ops teams look for first when something breaks. They must be organised by symptom/error message (not by component), and each runbook must open with a 2-sentence root cause explanation before recovery steps. Common failures documented in the existing validation scripts and gap reports (`core-pipeline-gaps.md`) should be the primary source material.

**Delivers:** Runbooks and troubleshooting section organised by symptom: node stops enrolling, cert expiry, common job failures, mop-push auth errors, mTLS handshake failures, FAQ.

**Addresses:** Runbooks (FEATURES P1)

**Avoids:** UX pitfall of troubleshooting organised by feature rather than symptom

### Phase 8: Developer Reference and Polish

**Rationale:** Developer-facing content (architecture guide with Mermaid diagrams, setup and development guide, contributing guide, changelog) and P2 enhancements (Mermaid diagrams for additional flows, annotated code blocks, page last-updated dates, instant loading, "edit this page" links) round out the milestone. Mermaid architecture diagrams belong here rather than in earlier phases — the content must be stable before investing in diagrams.

**Delivers:** Developer section (architecture diagram, setup guide, contributing guide, changelog). P2 feature enhancements (Mermaid, annotations, git revision dates). Changelog page with v7/v8/v9 entries.

**Addresses:** Architecture guide (FEATURES P1), developer setup guide (FEATURES P2), Mermaid diagrams (FEATURES P2), annotated code blocks (FEATURES P2)

### Phase Ordering Rationale

- Phases 1-3 are infrastructure-first: the routing, build pipeline, and dashboard integration must be correct before content is written, or content will be written against a broken system
- Phase 2 (API reference) precedes content phases because it validates the full Dockerfile build pipeline end-to-end with a real deliverable
- Phase 4 (getting started + nav architecture) must precede Phases 5-7 (content) because nav structure established late requires mass link updates
- Phase 5 (security guide) is prioritised before feature guides because it is the primary enterprise differentiator and requires the most careful external review
- Phases 6-7 (feature guides + runbooks) are parallelisable but runbooks benefit from feature guides existing to link to
- Phase 8 (polish) is deliberately last — Mermaid diagrams added to stable content, not to content that may still change

### Research Flags

Phases likely needing additional investigation during planning:

- **Phase 1:** The `site_url` + nginx `alias` interaction should be verified with an actual `docker compose build docs && curl /docs/assets/stylesheets/main.css` test immediately after the first working build — don't assume the routing is correct without a deep-asset URL test
- **Phase 2:** The `app.openapi()` import may trigger SQLAlchemy model imports that require environment variables (`DATABASE_URL`, `ENCRYPTION_KEY`). The export script will need to either mock these or set dummy values in the builder stage. This is a known FastAPI pattern (confirmed in GitHub Discussion #1490) but needs verification against this specific codebase's import chain.
- **Phase 5:** Before writing the security guide, audit which content details must be restricted to authenticated users only vs. which can be public-facing. The Cloudflare Access policy decision (all of `/docs/*` restricted, or only `/docs/security/*`) affects both the Caddyfile routing and the nav structure.

Phases with well-documented patterns (no additional research needed):

- **Phase 3:** Dashboard integration is a three-file change with no novel patterns
- **Phase 6:** Feature guide content follows a well-established template; no new infrastructure work
- **Phase 7:** Runbook structure follows the Prerequisites → Operation → Verify → Diagnose pattern established in Phase 5
- **Phase 8:** All P2 features are built-in Material capabilities with documented configuration

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified against PyPI and official changelogs; Docker image patterns confirmed by codebase inspection of existing Caddyfile and compose.server.yaml; MkDocs official docs reviewed |
| Features | HIGH | MkDocs Material official docs verified; enterprise doc structures cross-checked against HashiCorp Terraform, Dapr, and Kubernetes documentation; plugin availability verified post-9.7.0 open-sourcing |
| Architecture | HIGH | Based on direct codebase analysis of existing Caddyfile, compose.server.yaml, MainLayout.tsx, AppRoutes.tsx, and Docs.tsx; Caddy and nginx routing patterns confirmed against official docs |
| Pitfalls | HIGH | Codebase directly inspected; MkDocs GitHub issues #1825 and #2168 confirmed; Caddy directive behaviour verified; pitfalls derived from both official documentation and community post-mortems |

**Overall confidence:** HIGH

### Gaps to Address

- **OpenAPI import side effects:** The `scripts/export_openapi.py` approach (calling `app.openapi()` without starting the server) is well-documented in principle but this specific codebase's import chain should be tested early in Phase 2. SQLAlchemy async engine initialisation and environment variable requirements could cause the import to fail or require dummy env vars in the builder stage. Mitigation: run the export script locally against a clean Python env as the first task in Phase 2 before writing any other code.

- **Cloudflare Access policy scope:** Research confirms that `/docs*` must be behind Cloudflare Access, but whether to gate all docs or only the security section requires a product decision. If the getting-started guide is intended to be publicly accessible (to reduce friction for evaluators), a split policy is needed. This decision affects Phase 1 Caddyfile design and should be made before Phase 1 begins.

- **`mike` versioning trigger:** Research recommends deferring `mike` versioning to v10+, but the trigger condition ("multiple released versions users are actively running") should be made explicit in the roadmap so it doesn't remain perpetually deferred. Suggest flagging it as a Phase 8 stretch goal if Phase 1-7 complete ahead of schedule.

## Sources

### Primary (HIGH confidence)
- [mkdocs-material PyPI page](https://pypi.org/project/mkdocs-material/) — version 9.7.5 confirmed, Python >=3.8 requirement
- [mkdocs-material changelog](https://squidfunk.github.io/mkdocs-material/changelog/) — 9.7.5 released 2026-03-10, mkdocs <2 cap
- [mkdocs-material installation docs](https://squidfunk.github.io/mkdocs-material/getting-started/) — Docker image `squidfunk/mkdocs-material:9` confirmed
- [MkDocs GitHub issue #1825](https://github.com/squidfunk/mkdocs-material/issues/1825) — official confirmation that `mkdocs serve` is not production-safe
- [MkDocs GitHub issue #2168](https://github.com/squidfunk/mkdocs-material/issues/2168) — Docker serve limitations
- [mkdocs-swagger-ui-tag GitHub](https://github.com/blueswen/mkdocs-swagger-ui-tag) — v0.8.0, bundles Swagger UI locally, air-gap safe
- [FastAPI — Extending OpenAPI](https://fastapi.tiangolo.com/how-to/extending-openapi/) — official `app.openapi()` method documentation
- [Caddy — handle_path directive](https://caddyserver.com/docs/caddyfile/directives/handle_path) — prefix stripping behaviour
- [Material for MkDocs — Insiders now free (9.7.0)](https://squidfunk.github.io/mkdocs-material/blog/2025/11/11/insiders-now-free-for-everyone/) — privacy plugin, offline plugin now in free tier
- Direct codebase inspection: `puppeteer/cert-manager/Caddyfile`, `puppeteer/compose.server.yaml`, `puppeteer/dashboard/src/layouts/MainLayout.tsx`, `puppeteer/dashboard/src/AppRoutes.tsx`, `puppeteer/dashboard/src/views/Docs.tsx`, `docs/` tree

### Secondary (MEDIUM confidence)
- [FastAPI Discussion #1490](https://github.com/fastapi/fastapi/issues/1490) — `app.openapi()` without running server, community-verified pattern
- [mkdocs-render-swagger-plugin GitHub](https://github.com/bharel/mkdocs-render-swagger-plugin) — `!!swagger FILENAME!!` syntax; used to inform alternative plugin comparison
- [docker-nginx-mkdocs-material (nwesterhausen)](https://github.com/nwesterhausen/docker-nginx-mkdocs-material) — multi-stage build pattern (Python builder + nginx)
- [HashiCorp Terraform documentation structure](https://developer.hashicorp.com/terraform/docs) — enterprise docs nav structure reference
- [Dapr documentation](https://docs.dapr.io/operations/security/mtls/) — security-focused docs structure reference

### Tertiary (LOW confidence)
- [neoteroi-mkdocs OpenAPI Docs](https://www.neoteroi.dev/mkdocs-plugins/web/oad/) — renders as styled Markdown without interactive Swagger UI; referenced to rule out as an option

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*
