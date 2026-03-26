# Project Research Summary

**Project:** Axiom v14.2 — Docs on GitHub Pages
**Domain:** GitHub Pages deployment of existing MkDocs Material documentation site
**Researched:** 2026-03-26
**Confidence:** HIGH

## Executive Summary

This milestone adds public GitHub Pages hosting to an MkDocs Material documentation site that already exists, builds cleanly, and passes `mkdocs build --strict` in CI. The task is not building a docs site from scratch — it is wiring a deployment path onto an already-correct static site build. The recommended approach is a new `docs-deploy.yml` GitHub Actions workflow that runs `mkdocs gh-deploy --force` on every push to `main`. This approach is simpler than the alternative `actions/deploy-pages` artifact chain, requires fewer permissions (`contents: write` vs `pages: write` + `id-token: write`), is the official MkDocs Material recommendation, and requires zero changes to `docs/requirements.txt`.

Two configuration changes are mandatory before the first deploy: (1) `site_url` in `docs/mkdocs.yml` must be updated from the current self-hosted nginx URL (`https://dev.master-of-puppets.work/docs/`) to the GitHub Pages URL, and (2) the `offline` plugin must be made conditional via `enabled: !ENV [OFFLINE_BUILD, false]` so it does not force `use_directory_urls: false` for the hosted build. Both fixes are targeted one-liner changes but each has significant downstream impact if missed. Wrong `site_url` breaks canonical URLs, sitemaps, and 404-page asset paths. An active `offline` plugin changes the entire URL structure from `/page/` to `page.html`, breaking all existing deep links. A pre-deploy cleanup step should also remove `docs/site/` from git tracking — it is currently committed and will become a source of noisy diffs and repo bloat once GH Pages is live.

The key risk is a cluster of pitfalls that are individually easy to fix but hard to diagnose after the fact. All nine documented pitfalls are preventable by testing `mkdocs build --strict` locally against the updated config before pushing. The work is low-complexity: one new workflow file, two targeted config changes, one git-tracking cleanup, and one one-time repository settings step. No new Python dependencies are needed.

---

## Key Findings

### Recommended Stack

The existing stack (`mkdocs-material==9.7.5` + `mkdocs-swagger-ui-tag==0.8.0`) needs no additions to `docs/requirements.txt`. The deployment method is `mkdocs gh-deploy --force` over the more complex `actions/upload-pages-artifact` + `actions/deploy-pages` chain. The simpler approach has identical output, is the official MkDocs Material recommendation, and requires only `permissions: contents: write` rather than `pages: write` + `id-token: write`.

**Core technologies:**
- `mkdocs-material==9.7.5`: Site build — already pinned, no change needed
- `mkdocs-swagger-ui-tag==0.8.0`: API reference rendering — already pinned; bundles Swagger UI statically (no CDN calls on GH Pages)
- `actions/checkout@v4` with `fetch-depth: 0`: Required — git history is used by `mkdocs gh-deploy` for the `gh-pages` branch commit
- `actions/setup-python@v5` with `cache: pip`: Python environment + pip dependency caching for faster repeated deploys
- `mkdocs gh-deploy --force`: Single deploy command that handles `.nojekyll` creation, branch management, and idempotent force-push automatically

### Expected Features

**Must have (table stakes — v14.2 launch blockers):**
- Automated deploy on push to `main` — docs update automatically when content merges
- `site_url` set to GH Pages URL — required for correct sitemap, canonical links, and asset resolution
- `offline` plugin made conditional via `!ENV [OFFLINE_BUILD, false]` — prevents URL structure breakage on GH Pages
- `permissions: contents: write` on the deploy workflow job — `mkdocs gh-deploy` pushes to `gh-pages` branch
- `docs/site/` removed from git tracking — currently committed; becomes noisy drift once CI manages the build
- `openapi.json` regeneration script for maintainers — documents the manual update process; `openapi.json` already committed to repo
- GitHub Pages source configured in repository settings (manual, one-time operator step)

**Should have (differentiators — v14.2 stretch or v14.3):**
- `docs/docs/CNAME` file — only if a custom domain is chosen; prevents domain wipeout on every `gh-deploy`
- `docs/docs/robots.txt` — explicit crawler directive with sitemap pointer
- Deploy trigger scoped to `paths: ['docs/**', '.github/workflows/docs-deploy.yml']` — avoids redeploys on unrelated code changes
- Protective comment in `.gitignore` explaining why `docs/.cache/` must stay committed

**Defer (v15+):**
- `mike` versioned docs — adds significant branch management complexity; no use case until multiple major versions coexist
- Google Search Console / Bing Webmaster submission — post-launch SEO step, not a code change
- Migration to `actions/deploy-pages` artifact chain — only if GitHub deprecates branch-based Pages (no indication this is planned)

### Architecture Approach

The deployment architecture is a two-branch model: `main` holds source; `gh-pages` holds built output managed exclusively by `mkdocs gh-deploy`. The new `docs-deploy.yml` workflow is kept separate from `ci.yml` to prevent deploying in-progress PR content and to scope `contents: write` only to the deploy context. The existing `ci.yml` `docs` job remains the PR validation gate — the deploy workflow fires only on push to `main`. No changes are needed to the Docker deployment path (two-stage Dockerfile with nginx). Both deployment paths remain live: GH Pages for public docs, Docker/nginx for the self-hosted internal instance.

**Major components:**
1. `docs/mkdocs.yml` — modified: `site_url` updated to GH Pages URL; `offline` plugin made conditional
2. `.github/workflows/docs-deploy.yml` — new: triggers on push to main, runs `mkdocs gh-deploy --force` from `working-directory: docs`
3. `gh-pages` branch — auto-managed by `mkdocs gh-deploy`; created on first workflow run; never hand-edited
4. `docs/docs/` source files — unchanged: all markdown, committed `openapi.json`, privacy plugin cache in `docs/.cache/`
5. `docs/site/` — removed from git tracking: generated at deploy time; `.gitignore` updated before first deploy

### Critical Pitfalls

1. **Wrong `site_url` (nginx URL baked into GH Pages build)** — Update `site_url` in `docs/mkdocs.yml` to the GitHub Pages URL before the first deploy. The current value (`https://dev.master-of-puppets.work/docs/`) appears in every canonical link tag and the sitemap; the 404 page loads with broken asset paths pointing to the internal nginx server.

2. **`offline` plugin forces `use_directory_urls: false`** — Add `enabled: !ENV [OFFLINE_BUILD, false]` to the offline plugin config. Without this, all page URLs on GitHub Pages become `page.html` instead of `page/`, breaking every existing deep link. The Dockerfile builder stage should set `OFFLINE_BUILD=true` to maintain air-gapped container behavior.

3. **`docs/site/` tracked in git** — Run `git rm -r --cached docs/site/` and add `docs/site/` to `.gitignore` before the first `gh-deploy`. Both the Dockerfile and the deploy workflow regenerate `site/` — the committed copy creates noisy diffs on every local `mkdocs build`.

4. **`working-directory: docs` missing from deploy workflow** — `mkdocs.yml` is at `docs/mkdocs.yml`, not the repo root. Every `mkdocs` command in the workflow must use `working-directory: docs`, matching the existing `ci.yml` pattern. Omitting this causes an immediate "Config file 'mkdocs.yml' does not exist" failure.

5. **GitHub Pages source not configured in repository settings** — After the first `gh-deploy` run creates the `gh-pages` branch, an operator must manually set Settings > Pages > Source to "Deploy from a branch" -> `gh-pages` -> `/`. The site returns 404 until this one-time step is completed. Document this in the workflow file comments.

---

## Implications for Roadmap

All four research areas converge on a minimal two-phase structure. Phase 1 is the full deployment implementation shipped atomically. Phase 2 is deferred polish that does not block the site from being live.

### Phase 1: Foundation and Deploy

**Rationale:** All changes are tightly interdependent and must ship together. The `site_url` change must precede the deploy workflow commit — a wrong URL baked into a live deploy is harder to recover from than never deploying with a wrong URL. The `offline` plugin fix and `docs/site/` cleanup are pre-conditions for Phase 1, not follow-ons.

**Delivers:** Live public documentation at the GitHub Pages URL, auto-deploying on every push to `main`.

**Addresses:**
- All P1 features: deploy workflow, `site_url`, `offline` plugin fix, git tracking cleanup, operator settings step
- Pitfall avoidance: site_url (P1), offline plugin URL rewrite (P2), git bloat from `docs/site/` (P3), working-directory misconfiguration (P4), Pages source configuration (P5)
- `.nojekyll` (Pitfall 4) handled automatically by `mkdocs gh-deploy` — no manual step needed

**Implementation order within the phase:**
1. `git rm -r --cached docs/site/` and add `docs/site/` to `.gitignore` (cleanup before any deploy)
2. Update `site_url` in `docs/mkdocs.yml` to the GH Pages URL
3. Add `enabled: !ENV [OFFLINE_BUILD, false]` to the offline plugin in `docs/mkdocs.yml`
4. Run `mkdocs build --strict` locally against updated config — verify zero warnings and correct URL structure in `site/`
5. Create `.github/workflows/docs-deploy.yml` with `fetch-depth: 0`, `working-directory: docs`, `permissions: contents: write`
6. Add protective comment to `.gitignore` about `docs/.cache/`
7. Open PR; CI gate validates via `ci.yml`; merge to `main` triggers first deploy
8. Operator step: Settings > Pages > Source = `gh-pages` branch (documented in workflow comments)

**Avoids:** All nine documented pitfalls — site_url mismatch (P1), offline plugin URL rewrite (P2), privacy cache loss (P3), Jekyll interference via `.nojekyll` (P4, auto-handled), subdirectory misconfiguration (P5), CNAME wipeout (P6, no custom domain in v14.2 — documented), git bloat from `docs/site/` (P7), strict mode regressions (P8), Pages source not configured (P9)

### Phase 2: Polish

**Rationale:** These are low-effort improvements that add correctness and SEO value but do not block the site from being live. Defer until Phase 1 is validated live.

**Delivers:** Custom domain support readiness (CNAME file), explicit crawler directives (robots.txt), path-scoped deploy triggers.

**Implements:**
- `docs/docs/CNAME` file (if a custom domain is chosen)
- `docs/docs/robots.txt` with `Allow: /` and sitemap pointer
- Deploy trigger `paths` filter to avoid unnecessary redeploys on unrelated code changes

### Phase Ordering Rationale

- Phase 1 must ship as an atomic unit: `site_url`, `offline` plugin fix, and the deploy workflow are tightly coupled — deploying any one without the others produces a broken or misleading live site.
- Phase 2 requires Phase 1 to be live and validated — adding a custom domain or path-scoped trigger before confirming the base deploy works adds unnecessary debugging complexity.
- `mike` versioned docs is explicitly deferred — migration from plain `gh-deploy` to `mike` cannot be done incrementally; it requires a full branch restructure. No current use case justifies the complexity.

### Research Flags

Phases with standard, well-documented patterns (no `/gsd:research-phase` needed):
- **Phase 1:** Fully documented in official MkDocs Material and GitHub Pages docs, corroborated by direct codebase inspection. All commands, config changes, and permission models are verified. Implementation can proceed directly.
- **Phase 2:** All items are one-liner additions with zero ambiguity. Implementation can proceed directly.

No phases require additional research before planning.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official MkDocs Material docs + direct inspection of `docs/requirements.txt`, `docs/mkdocs.yml`, `ci.yml`. No new deps required; confirmed against the deprecated v2/v3 action versions that must be avoided. |
| Features | HIGH | MkDocs official docs + GitHub Pages official docs. MVP feature set is minimal and well-understood. Prioritization matrix is definitive. |
| Architecture | HIGH | Direct codebase inspection confirmed all file paths, plugin behavior, and `git ls-files` state of `docs/.cache/` and `docs/site/`. Component responsibilities and data flow are fully mapped. |
| Pitfalls | HIGH | Nine pitfalls documented from official MkDocs issue tracker, GitHub docs, and direct inspection of the existing config state. All pitfalls are specific to this codebase's actual configuration, not generic warnings. |

**Overall confidence:** HIGH

### Gaps to Address

- **GitHub Pages URL (org/repo slug):** The exact GH Pages URL (`https://<org>.github.io/<repo>/`) depends on which GitHub organization and repository name the project uses. This must be confirmed before updating `site_url`. If a custom domain is intended for v14.2 (not indicated in research), that domain should be the `site_url` value instead. Confirm the target URL with the project owner before writing `docs/mkdocs.yml`.

- **`offline` plugin in Dockerfile after the `!ENV` change:** The Dockerfile builder stage should set `OFFLINE_BUILD=true` to maintain air-gapped behavior. Verify whether the Dockerfile currently sets this env var or relies on the plugin always being active. If the Dockerfile does not set `OFFLINE_BUILD=true` after the mkdocs.yml change, the container build will produce a non-offline build — likely acceptable since the container is served via nginx over HTTPS, but should be verified and documented.

- **`docs/.cache/` privacy plugin cache completeness:** The cache is currently untracked (git status shows it as untracked additions). Confirm the cache contains all required assets (Google Fonts, Mermaid, iframe-worker) so the GH Actions deploy workflow does not depend on outbound CDN access. If assets are missing, the workflow will download them from CDN on GitHub-hosted runners — which works but is non-deterministic and contradicts the air-gapped design intent.

---

## Sources

### Primary (HIGH confidence)
- [MkDocs Material — Publishing your site](https://squidfunk.github.io/mkdocs-material/publishing-your-site/) — deploy workflow pattern, `mkdocs gh-deploy` vs `actions/deploy-pages`, pip caching recommendation
- [MkDocs Material — Offline plugin](https://squidfunk.github.io/mkdocs-material/plugins/offline/) — `use_directory_urls: false` override behavior, `!ENV` conditional pattern
- [MkDocs Material — Privacy plugin](https://squidfunk.github.io/mkdocs-material/plugins/privacy/) — cache behavior, CDN asset inlining, air-gapped build support
- [MkDocs — Deploying your docs](https://www.mkdocs.org/user-guide/deploying-your-docs/) — `gh-deploy` mechanics, CNAME file placement, `.nojekyll` handling
- [GitHub Docs — Configuring a publishing source for GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) — branch vs Actions source, repo settings one-time step
- [GitHub Changelog — Dec 2024 deprecation notice](https://github.blog/changelog/2024-12-05-deprecation-notice-github-pages-actions-to-require-artifacts-actions-v4-on-github-com/) — v3/v4 pairing requirement (relevant if `actions/deploy-pages` approach is ever adopted)
- Direct codebase inspection: `docs/mkdocs.yml`, `docs/requirements.txt`, `docs/Dockerfile`, `.github/workflows/ci.yml`, `git ls-files docs/.cache/`, `git ls-files docs/site/`, `docs/docs/api-reference/openapi.json`

### Secondary (MEDIUM confidence)
- [mkdocs-swagger-ui-tag README](https://github.com/blueswen/mkdocs-swagger-ui-tag) — `oauth2RedirectUrl` derives from `site_url`; subpath trailing slash requirement
- [MkDocs Material — Issue #4678](https://github.com/squidfunk/mkdocs-material/issues/4678) — asset loading failures on GH Pages caused by wrong `site_url`
- [MkDocs Material — Issue #2520](https://github.com/squidfunk/mkdocs-material/issues/2520) — `site_url` documentation gap
- [MkDocs — Issue #1257](https://github.com/mkdocs/mkdocs/issues/1257) — `gh-deploy` removes custom domain CNAME on every push
- [MkDocs Material — Issue #8040](https://github.com/squidfunk/mkdocs-material/issues/8040) — Privacy plugin partial replacement failures (9.6.5)

### Tertiary (LOW confidence)
- WebSearch — offline plugin + GitHub Pages `use_directory_urls` interaction in 2025 community reports; consistent with official plugin docs

---

*Research completed: 2026-03-26*
*Ready for roadmap: yes*
