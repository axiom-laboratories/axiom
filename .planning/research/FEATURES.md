# Feature Research

**Domain:** Enterprise documentation system — MkDocs Material for a security-focused infrastructure tool
**Researched:** 2026-03-16
**Confidence:** HIGH (MkDocs Material official docs verified; API reference plugin options verified via PyPI and GitHub; enterprise doc patterns cross-checked against HashiCorp/Dapr/Kubernetes documentation structures)

---

## Context: What This Milestone Covers

This research is scoped to **v9.0 Enterprise Documentation** — adding a containerised MkDocs Material
docs site to an existing, functional orchestration platform. The platform already has:

- mTLS node enrollment, Ed25519 job signing, container-isolated execution
- RBAC (admin/operator/viewer), audit log, service principals, OAuth device flow
- Foundry image builder, Smelter Registry, Package Mirroring
- `mop-push` CLI, job lifecycle (DRAFT→ACTIVE→DEPRECATED→REVOKED), Staging dashboard
- An in-app Docs view (`Docs.tsx`) that currently renders markdown inline — this will be replaced

The audience is **two distinct user groups**:
- **Operators / developers**: deploy and maintain the system (architecture, setup, security config)
- **End users**: run jobs, use the CLI, manage nodes and templates via the dashboard

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that enterprise infrastructure documentation must have. Missing any of these means the
docs feel like an afterthought or internal wiki, not a production product.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Full-text client-side search** | Every modern docs site has search. Without it, users give up and ask in Slack instead. | LOW | Built into MkDocs Material — lunr.js, enabled by default, no external service. Configure search suggestions (`search.suggest`) and highlighting (`search.highlight`) in `mkdocs.yml` via theme features. No plugin install needed. |
| **Navigation sidebar with hierarchy** | Deep technical docs require multi-level navigation. Flat structure fails at >20 pages. | LOW | Built-in. Configure via `nav:` in `mkdocs.yml`. Enable `navigation.sections` + `navigation.expand` for sidebar groups. Use `navigation.tabs` for top-level sections (Infrastructure / User Guide / API Reference / Developer Guide). |
| **Light and dark mode** | Enterprise users often read docs in dark mode; missing it means eyes-on-screen complaints. | LOW | Built-in. Two palettes: `default` (light) and `slate` (dark). Add both with `media:` queries so OS preference is respected automatically. CSS variable theming for brand colors. |
| **Mobile-responsive layout** | Operators often check docs from phones during incidents. | LOW | Built-in (Material design is responsive by default). No configuration needed. |
| **Code blocks with syntax highlighting** | Security and infrastructure docs are code-heavy. Unformatted code is unreadable. | LOW | Built-in via Pygments. Supports copy-to-clipboard (`content.code.copy`), line numbers (`linenums`), line highlighting. Configure in `mkdocs.yml` theme features. |
| **Admonitions (note/warning/danger callouts)** | Critical for security documentation — "WARNING: this disables mTLS" must be visually distinct. | LOW | Built-in via PyMdown Extensions (`admonition` + `pymdownx.superfences`). Types: note, tip, warning, danger, info, success. No extra install beyond PyMdown. |
| **Per-page table of contents** | Long pages (architecture guides, security guides) need in-page navigation. | LOW | Built-in. TOC generated automatically from headings. Control depth with `toc_depth`. `toc.follow` scrolls the sidebar TOC to track active heading. |
| **Getting started / quickstart guide** | The first thing any new user looks for. Missing = high abandonment rate. | MEDIUM | Content work, not a platform feature. Structure: Install → Enroll first node → Sign first job → Dispatch first job. Maps to existing system capabilities. |
| **Feature guides (one per major feature)** | Users expect dedicated pages for Foundry, Smelter, mop-push, RBAC, etc. | MEDIUM | Content work. Each guide: what it does, prerequisites, step-by-step usage, common errors. One page per major system feature (8 planned). |
| **API reference** | Any REST API product is expected to have a reference. Without it, users write support requests asking "what parameters does POST /jobs accept?" | MEDIUM | Use third-party plugin (`mkdocs-swagger-ui-tag` or `mkdocs-render-swagger-plugin`). FastAPI already serves `/openapi.json` — reference this from the docs container. See anti-features for why live embedding is risky. |
| **Runbook / troubleshooting section** | Ops teams expect documented failure procedures. "What do I do if a node stops enrolling?" | MEDIUM | Content work. Minimum: node recovery, cert expiry, database issues, common job failures, mop-push auth errors. Structured as symptom → cause → fix. |
| **Search that works offline / air-gapped** | MoP is explicitly designed for air-gapped deployments. Docs that phone home for search would be a security and usability failure. | LOW | Built-in offline plugin (`offline`). Bundles the search index into the static build. No external CDN calls. Combine with `privacy` plugin to download and self-host all external assets at build time. |
| **Copy-to-clipboard for commands** | Infrastructure docs are useless if users have to manually type every shell command. | LOW | Built-in: `content.code.copy` in theme features. Works on all fenced code blocks. |
| **"Edit this page" link** | Operators who find errors need a low-friction way to contribute fixes. | LOW | Built-in when `repo_url` + `repo_name` are set and `content.action.edit` feature is enabled. Links to the source file in the git repo. |
| **Changelog / version notes** | Enterprise users track what changed between releases before upgrading. | LOW | One page, manually maintained. Structure: version → date → breaking changes → new features → bug fixes. Keep separate from the feature guides. |

### Differentiators (Competitive Advantage)

Features that elevate MoP docs above generic project READMEs and into enterprise-grade
reference documentation territory.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Auto-generated API reference (always in sync)** | API reference that drifts from the actual implementation is worse than no reference. Generated from `/openapi.json` = zero drift. | MEDIUM | Use `mkdocs-swagger-ui-tag` plugin. Point at `/openapi.json` served by the running FastAPI container. Build-time: fetch the spec file and embed — or deploy as a static reference via `mkdocs-render-swagger-plugin`. Confidence: MEDIUM — plugin works well but iframe-based embedding can have display quirks with Material theme; test early. |
| **Security & compliance guide (dedicated section)** | Security-first positioning requires documenting the security model explicitly. Competitors (Rundeck, Prefect) bury this; making it a first-class section signals enterprise intent. | MEDIUM | Covers: mTLS architecture, cert lifecycle + rotation intervals, Ed25519 signing model, RBAC config, audit log usage, air-gap deployment, `EXECUTION_MODE` trade-offs. No platform features needed — pure content, high value. |
| **Navigation tabs (section-per-audience)** | Security tools have two distinct audiences: operators deploying the system and users running jobs. One navigation tree for both creates cognitive overload. | LOW | Built-in: `navigation.tabs`. Structure tabs as: Getting Started / Feature Guides / Security & Compliance / Developer Reference / API Reference. Tabs visible on desktop, collapsed to sidebar sections on mobile. |
| **Instant loading (SPA-like navigation)** | Docs that reload the full page on every click feel slow in 2026. Instant loading makes large docs sets feel responsive. | LOW | Built-in: `navigation.instant` + `navigation.instant.prefetch` in theme features. Works by intercepting internal link clicks, dispatching via XHR, and injecting only the changed content. Zero extra plugins. |
| **Versioned documentation (mike plugin)** | As MoP ships v9, v10, etc., operators on older versions need docs that match what they deployed. | MEDIUM | Requires `mike` third-party tool (separate install: `pip install mike`). Configure in `mkdocs.yml`: `extra.version.provider: mike`. Mike manages `versions.json` in the `gh-pages` branch. Version selector appears in the header. This is important for enterprise credibility — skip it and operators assume docs only cover head. |
| **Page-level "last updated" date** | Shows docs are maintained, not stale. Enterprise buyers look for this. | LOW | Requires `mkdocs-git-revision-date-localized-plugin` (third-party, separate install). Adds "Last updated: date" at the bottom of each page derived from git history. Only works if the docs directory is in a git repo with history — which the planned `docs/` git-backed markdown structure satisfies. |
| **Annotated code blocks** | For security and architecture documentation, the ability to add inline explanations to code without breaking the code block is uniquely useful. MoP's Dockerfile examples, mTLS config, and compose files all benefit from this. | LOW | Built-in via PyMdown `pymdownx.superfences` + Material annotations. The `(1)` syntax places numbered callouts on specific lines; explanations appear as popups. No extra plugins. |
| **Mermaid diagram support** | Architecture diagrams in the docs that are version-controlled as text, not uploaded PNGs that drift. The three-component diagram (Puppeteer ↔ mTLS ↔ Puppet) belongs in the architecture guide as a living diagram. | LOW | Built-in via `pymdownx.superfences` custom_fences for `mermaid`. Material renders Mermaid diagrams client-side. No external plugin needed — just configure the superfence extension. |
| **Content tabs for multi-platform instructions** | Setup and deployment instructions often differ by OS (Linux/macOS/Windows) or deployment method (Docker/bare metal). Content tabs let one page show all variants cleanly. | LOW | Built-in via `pymdownx.tabbed`. Example: Docker vs bare-metal install instructions on the same page as linked tabs. No extra install — PyMdown extensions are already required for admonitions anyway. |
| **Privacy plugin (self-hosted assets)** | Air-gapped deployments cannot load Google Fonts or external CDN assets. The privacy plugin downloads all external assets at build time and rewrites links to use local copies. | LOW | Built-in privacy plugin (`privacy`). Previously Insiders-only, now free in 9.7.0. Just add `plugins: - privacy:` to `mkdocs.yml`. Critical for MoP's air-gap deployment story. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Live API reference (proxied from running stack)** | "The docs always show the current API" sounds ideal. | Requires the MkDocs container to proxy to a live FastAPI instance at render time. This creates an infrastructure dependency: docs break if the API is down, and the docs container must have network access to the agent container. In air-gapped or offline builds, this fails entirely. Also creates a security surface: docs container → API container with credentials. | Build-time static generation: run `curl https://localhost:8001/openapi.json > docs/api/openapi.json` as part of the build step, commit the spec file to the repo, and render from the static file. Update whenever the API changes via CI or a manual step. Zero runtime dependency. |
| **Full-text search via Algolia DocSearch** | Algolia search is faster and supports analytics | Algolia requires an external network call for every search query — incompatible with air-gapped operation. It also requires a third-party service account and terms agreement. MkDocs Material's built-in lunr-based search is offline-capable and sufficient for docs of this scale. | Built-in search plugin with suggestions and highlighting enabled. No external service. |
| **Wiki-style collaborative editing** | "Operators should be able to edit docs in-browser" | Turns a static documentation system into a web application (requires auth, edit backend, conflict resolution, versioning). This is not what MkDocs is. In-browser editing also bypasses the review workflow that keeps docs accurate. | Git-backed `docs/` directory + "Edit this page" links (built-in Material feature). Operators edit via pull requests. Git history provides change tracking. |
| **Automatic doc generation from code docstrings (MkDocstrings)** | "Docs should auto-update when code changes" | Python docstrings in this codebase are minimal — there is no existing convention of documentation-quality docstrings. MkDocstrings would generate skeleton pages from sparse comments, creating the illusion of documentation without substance. The FastAPI route handlers in `main.py` are well-commented but not docstring-documented. | Manual developer reference pages written to explain architecture, not just function signatures. Auto-generate the API reference (OpenAPI/Swagger) which is already structured data. |
| **Versioning for every minor release** | "We should version docs for every patch" | Mike versioning requires maintaining separate builds per version. Patch releases that don't change behaviour create noise without value. Enterprise tools typically version major releases only. | Version docs for major milestones (v8, v9, v10...). Maintain a single "latest" alias + a "stable" alias. Use the changelog page for patch-level change notes. |
| **PDF export** | "We want to give customers a PDF manual" | MkDocs PDF export plugins (`mkdocs-with-pdf`) are fragile, poorly maintained, and produce inconsistent output with Material theme's complex CSS. The resulting PDFs require ongoing maintenance and rarely match the web experience. | The docs are already self-hostable and accessible offline via the offline plugin. For compliance document requests, export individual pages from the browser. |
| **Internationalisation (i18n) / translation** | "We should support multiple languages" | MkDocs Material supports i18n but maintaining translated docs for a v1 enterprise product is a significant ongoing cost. No customer base has been established yet to justify the investment. Translation frameworks also increase the complexity of the docs build pipeline. | Ship English-only. Material's built-in language selector is available when/if translation contributors appear. |

---

## Feature Dependencies

```
[MkDocs Material container (compose.server.yaml)]
    └──enables──> [All other docs features] (nothing works without this)
                      └──requires──> [docs/ directory in git with mkdocs.yml]

[Built-in search plugin]
    └──enables──> [Offline search] (offline plugin wraps the search index)
    └──enhances──> [Search suggestions + highlighting] (optional theme features)

[Privacy plugin]
    └──requires──> [MkDocs Material 9.7.0+] (previously Insiders-only, now free)
    └──enables──> [Air-gapped deployment of docs] (no external CDN calls)

[OpenAPI spec file (openapi.json)]
    └──requires──> [FastAPI /openapi.json endpoint accessible at build time]
    └──enables──> [Swagger UI API reference page]

[mkdocs-swagger-ui-tag plugin]
    └──requires──> [openapi.json present in docs/ directory]
    └──conflicts──> [Live proxy to API] (choose static file vs live — static recommended)

[mike versioning plugin]
    └──requires──> [git repository with history]
    └──requires──> [docs container serves from versioned subdirectory structure]
    └──conflicts──> [Simple single-version deployment] (adds deploy complexity — implement last)

[mkdocs-git-revision-date-localized-plugin]
    └──requires──> [docs/ directory inside a git repo with full history]
    └──requires──> [git binary available in the docs container image]

[Navigation tabs]
    └──requires──> [nav: structure in mkdocs.yml with section-level organisation]
    └──requires──> [enough content to justify tab-level sections (>5 pages per section)]

[Mermaid diagrams]
    └──requires──> [pymdownx.superfences with mermaid custom_fence configured]
    └──conflicts──> [nothing] (purely additive)

[Dashboard integration (replace Docs.tsx)]
    └──requires──> [MkDocs container running and accessible]
    └──requires──> [Caddy routing: /docs/* → docs container]
```

### Dependency Notes

- **Privacy plugin is free since 9.7.0:** Previously required Insiders sponsor tier. As of November
  2025, Material for MkDocs 9.7.0 made all 20 previously-Insiders features free. Install with
  `pip install mkdocs-material==9.7.0` or later. The project is entering maintenance mode post-9.7.0
  — no new features will be added, but critical bugs and security fixes continue for 12 months.

- **OpenAPI spec must be static at build time:** The `mkdocs-swagger-ui-tag` plugin embeds a Swagger
  UI rendering of a spec file. Fetch the spec from the running FastAPI at container build time and
  commit it to `docs/api/openapi.json`. Update this file whenever API contracts change. Do not proxy
  to a live API endpoint — this creates a runtime dependency.

- **Mike versioning adds deployment complexity:** Mike manages a `versions.json` file and deploys
  each version into a subdirectory. This changes the docs container serve structure. Implement
  navigation, content, and basic container setup first (phases 1–3), then add mike versioning last
  to avoid restructuring an already-working setup.

- **git binary required in docs container for date plugin:** The
  `mkdocs-git-revision-date-localized-plugin` reads git history to extract commit dates. The docs
  Docker image must include git (`apt-get install git` in Dockerfile). The build must also mount or
  clone the repo with full history (not a shallow clone — `git clone --depth 1` breaks the plugin).

- **Dashboard integration depends on routing, not on docs content:** Replacing `Docs.tsx` with a
  redirect to the docs container is a routing concern (Caddy config + React `<a>` link). It can
  happen independently of how much content is in the docs, but should wait until the docs container
  is stable enough to not show a blank page.

---

## MVP Definition

This is a subsequent milestone on a mature system, not a greenfield product. MVP here means
"the minimum docs set that constitutes an enterprise-credible documentation site for MoP v9.0."

### Launch With (Milestone v9.0)

Must-have for the milestone to be declared complete:

- [ ] **MkDocs Material container** — `docs` service in `compose.server.yaml`, git-backed markdown in `docs/`, `mkdocs.yml` configured with nav tabs, privacy plugin, offline plugin, built-in search — essential infrastructure
- [ ] **Dashboard integration** — replace `Docs.tsx` in-app view with link/redirect to docs container — removes the stale in-app docs
- [ ] **Getting started guide** — Install → enroll first node → sign first job → dispatch first job — the most important user journey
- [ ] **Architecture guide** — three-component diagram (Mermaid), pull model explanation, security model overview — required for developer onboarding
- [ ] **Feature guides** — one page per major feature: Foundry, Smelter, mop-push CLI, job scheduling, RBAC, OAuth device flow, Staging view, node management — covers all v7/v8 features
- [ ] **Security & compliance guide** — mTLS setup, cert rotation, Ed25519 signing, RBAC config, audit log, air-gap deployment — enterprise differentiation
- [ ] **Runbooks & troubleshooting** — node recovery, cert expiry, common job failures, mop-push auth errors, FAQ — ops team expectation
- [ ] **Auto-generated API reference** — Swagger UI from static `openapi.json` — removes API ambiguity

### Add After Core Content (v9.x)

- [ ] **Page-level "last updated" date** (`mkdocs-git-revision-date-localized-plugin`) — once docs have been through a few edit cycles and git history is meaningful
- [ ] **Mermaid diagrams for additional flows** — node enrollment sequence, job lifecycle state machine, Foundry build pipeline — add as content matures
- [ ] **Setup & deployment guide for ops** — production Postgres setup, Cloudflare tunnel config, secrets management — add after getting-started is stable

### Future Consideration (v10+)

- [ ] **Versioned docs (mike)** — meaningful only once there are multiple released versions users are actively running
- [ ] **SLSA provenance documentation** — deferred until the feature itself ships
- [ ] **CI/CD integration guide** — deferred until the CI/CD API endpoints milestone ships

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| MkDocs container + compose integration | HIGH | LOW | P1 |
| Built-in search (suggestions + highlighting) | HIGH | LOW | P1 |
| Navigation tabs (audience separation) | HIGH | LOW | P1 |
| Dark/light mode | MEDIUM | LOW | P1 |
| Admonitions (warning/danger callouts) | HIGH | LOW | P1 |
| Code blocks (copy + syntax highlight) | HIGH | LOW | P1 |
| Offline + privacy plugins | HIGH | LOW | P1 |
| Getting started guide (content) | HIGH | MEDIUM | P1 |
| Feature guides — 8 pages (content) | HIGH | HIGH | P1 |
| Security & compliance guide (content) | HIGH | MEDIUM | P1 |
| Runbooks & troubleshooting (content) | HIGH | MEDIUM | P1 |
| API reference (Swagger UI from openapi.json) | HIGH | MEDIUM | P1 |
| Dashboard integration (replace Docs.tsx) | MEDIUM | LOW | P1 |
| Mermaid architecture diagrams | MEDIUM | LOW | P2 |
| Annotated code blocks | MEDIUM | LOW | P2 |
| "Edit this page" links | LOW | LOW | P2 |
| Page last-updated dates (git plugin) | MEDIUM | LOW | P2 |
| Instant loading (navigation.instant) | LOW | LOW | P2 |
| Developer setup guide (content) | MEDIUM | MEDIUM | P2 |
| Versioned docs (mike) | MEDIUM | MEDIUM | P3 |
| PDF export | LOW | HIGH | NEVER |
| Algolia search | LOW | MEDIUM | NEVER |
| Wiki-style in-browser editing | LOW | HIGH | NEVER |

**Priority key:**
- P1: Must have for v9.0 milestone to deliver enterprise-grade docs
- P2: Should have — add when P1 content is complete
- P3: Deferred to future milestone when triggers are met
- NEVER: Anti-features documented above

---

## Competitor Feature Analysis

How comparable infrastructure tools structure their documentation:

| Feature | HashiCorp Terraform | Dapr | Kubernetes | MoP v9.0 Approach |
|---------|--------------------|----|------------|-------------------|
| Nav structure | Tutorial / CLI / Language / API | Concepts / Getting started / Operations / Reference | Docs / Tasks / Reference / Concepts | Getting started / Feature guides / Security / Developer / API Reference |
| API reference | Full REST API docs, versioned | Auto-gen from OpenAPI | Versioned REST API reference | Swagger UI from openapi.json, static |
| Code examples | Inline, copy-to-clipboard | Inline, multi-language tabs | Inline, YAML-heavy | Inline, copy-to-clipboard, content tabs for Docker vs bare-metal |
| Security docs | Dedicated "Security" section with compliance guidance | "Operations > Security" section | Multiple security hardening guides | Dedicated "Security & Compliance" section |
| Versioning | Full versioned docs (each major/minor) | Versioned by release | Versioned per k8s release | v9.0: single latest; add mike versioning in future |
| Runbooks / troubleshooting | Separate "Troubleshooting" section | "Troubleshooting" per component | "Troubleshooting" section in docs | Dedicated section: node recovery, cert expiry, FAQ |
| Diagrams | Architecture diagrams (static PNG/SVG) | Mermaid + static diagrams | Static architecture diagrams | Mermaid (version-controlled, rendered client-side) |
| Offline support | No (hosted only) | No (hosted only) | No (hosted only) | Yes (offline plugin, critical for air-gapped MoP deployments) |
| Self-hostable | No | No | No | Yes (containerised, git-backed) |

**Key differentiator vs peers:** MoP's docs are self-hostable, offline-capable, and containerised
within the same stack the user is deploying. No other docs system in this category ships as a
first-class component of the tool itself.

---

## MkDocs Material Plugin / Feature Classification

Quick reference for implementors — what requires a plugin install vs what is built-in:

### Built-in (theme features, zero extra installs)
- Search with suggestions, highlighting, sharing, boosting, exclusion
- Navigation: tabs, sections, instant loading, prefetch, breadcrumbs, back-to-top, TOC follow
- Code blocks: copy button, line numbers, line highlighting
- Dark/light mode with OS preference detection
- Admonitions (requires PyMdown Extensions — standard install)
- Content tabs (requires `pymdownx.tabbed`)
- Annotations on code blocks (requires `pymdownx.superfences`)
- Mermaid diagrams (requires `pymdownx.superfences` custom_fences config)
- Social cards, offline plugin, privacy plugin, tags plugin, blog plugin, typeset plugin
  (all were Insiders-only before 9.7.0, now free — included in `pip install mkdocs-material`)

### Third-party (separate `pip install`)
- `mkdocs-swagger-ui-tag` — Swagger UI rendering from openapi.json
- `mkdocs-git-revision-date-localized-plugin` — "last updated" from git history
- `mike` — versioned documentation deployment

### Anti-pattern (do not install)
- `mkdocs-with-pdf` — fragile, breaks with Material theme CSS
- `mkdocs-mkdocstrings` — generates skeleton pages from sparse docstrings; not useful here
- Any plugin requiring external API calls (Algolia) — breaks air-gapped deployments

---

## Implementation Notes for This Codebase

### Container Architecture

The docs container sits alongside the existing `agent`, `model`, `db`, and `caddy` containers
in `compose.server.yaml`. Recommended setup:

```
docs container (mkdocs-material + mike):
  - Volume mount: ./docs:/docs (git-backed markdown)
  - Volume mount: ./mkdocs.yml:/docs/mkdocs.yml
  - Caddy routes /docs/* → docs:8000
  - Build step: fetch openapi.json from agent container, commit to docs/api/
  - Image: squidfunk/mkdocs-material:9.7.0 (pin the version — maintenance mode means no breaking changes expected)
```

### OpenAPI Spec Workflow

FastAPI already exposes `GET /openapi.json`. Fetch it once and commit:

```bash
curl -k https://localhost:8001/openapi.json -o docs/api/openapi.json
```

Add `mkdocs-swagger-ui-tag` to the docs container's pip dependencies. Reference the spec from
a docs page as a Swagger UI embed. Regenerate whenever API contracts change (gate on PR review).

### Content Structure (Recommended nav:)

```yaml
nav:
  - Getting Started:
      - Overview: index.md
      - Install & Deploy: getting-started/install.md
      - Enroll First Node: getting-started/first-node.md
      - Sign & Run First Job: getting-started/first-job.md
  - Feature Guides:
      - Node Management: features/nodes.md
      - Job Scheduling: features/scheduling.md
      - Foundry Image Builder: features/foundry.md
      - Smelter Registry: features/smelter.md
      - mop-push CLI: features/mop-push.md
      - RBAC & Users: features/rbac.md
      - OAuth Device Flow: features/oauth.md
      - Job Staging & Lifecycle: features/staging.md
  - Security & Compliance:
      - Security Model: security/model.md
      - mTLS Setup & Cert Rotation: security/mtls.md
      - Ed25519 Job Signing: security/signing.md
      - RBAC Configuration: security/rbac.md
      - Audit Log: security/audit.md
      - Air-Gap Deployment: security/air-gap.md
  - Developer Reference:
      - Architecture: developer/architecture.md
      - Setup & Development: developer/setup.md
      - Runbooks & Troubleshooting: developer/runbooks.md
      - Changelog: developer/changelog.md
  - API Reference:
      - REST API: api/reference.md
```

---

## Sources

- [Material for MkDocs — Plugins overview](https://squidfunk.github.io/mkdocs-material/plugins/)
- [Material for MkDocs — Reference (admonitions, code blocks, tabs, etc.)](https://squidfunk.github.io/mkdocs-material/reference/)
- [Material for MkDocs — Navigation setup](https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/)
- [Material for MkDocs — Search setup](https://squidfunk.github.io/mkdocs-material/setup/setting-up-site-search/)
- [Material for MkDocs — Git repository integration](https://squidfunk.github.io/mkdocs-material/setup/adding-a-git-repository/)
- [Material for MkDocs — Versioning (mike)](https://squidfunk.github.io/mkdocs-material/setup/setting-up-versioning/)
- [Material for MkDocs — Insiders now free for everyone (9.7.0 announcement)](https://squidfunk.github.io/mkdocs-material/blog/2025/11/11/insiders-now-free-for-everyone/)
- [mkdocs-swagger-ui-tag — PyPI + GitHub](https://github.com/blueswen/mkdocs-swagger-ui-tag)
- [mkdocs-render-swagger-plugin — GitHub](https://github.com/bharel/mkdocs-render-swagger-plugin)
- [mike versioning tool — GitHub](https://github.com/jimporter/mike)
- [mkdocs-git-revision-date-localized-plugin documentation](https://squidfunk.github.io/mkdocs-material/setup/adding-a-git-repository/)
- [HashiCorp Terraform documentation structure](https://developer.hashicorp.com/terraform/docs) — enterprise docs structure reference
- [Dapr documentation](https://docs.dapr.io/operations/security/mtls/) — security-focused docs structure reference

---

*Feature research for: enterprise documentation system (MkDocs Material) for security-focused infrastructure tool*
*Researched: 2026-03-16*
