# Pitfalls Research

**Domain:** Adding GitHub Pages hosting to an existing MkDocs Material site (v14.2 — Docs on GitHub Pages)
**Researched:** 2026-03-26
**Confidence:** HIGH (based on direct codebase inspection of `docs/mkdocs.yml`, `docs/requirements.txt`, `docs/.cache/`, `docs/site/`, `.github/workflows/ci.yml`; supplemented by official MkDocs Material docs, known GitHub Issues, and MkDocs upstream issue tracker)

---

## Critical Pitfalls

### Pitfall 1: `site_url` Points to the Existing nginx Server — GitHub Pages Assets Load From the Wrong Origin

**What goes wrong:**
`docs/mkdocs.yml` currently has `site_url: https://dev.master-of-puppets.work/docs/`. MkDocs Material uses `site_url` to construct absolute URLs for the sitemap, canonical links, and (critically) the 404.html asset references. When the same build is deployed to GitHub Pages (e.g. `https://axiom-labs.github.io/axiom/`), all absolute URLs in `404.html` still point to `dev.master-of-puppets.work`. The 404 error page will load with no CSS or JS. The sitemap.xml will list the wrong domain, harming SEO and making the Pages site invisible to crawlers as a GitHub Pages URL.

Beyond the 404 page, with instant loading enabled (the Material default), the canonical `<link rel="canonical">` in every page head will point to the nginx server. Search engines will index the nginx version as canonical and treat the GitHub Pages version as a duplicate.

**Why it happens:**
`site_url` is not a "current host" setting — it's a "where this build will be served" declaration. Developers copy an existing `mkdocs.yml` and only update the URL when they remember to. The CI build passes regardless because `mkdocs build --strict` does not validate whether `site_url` matches the actual deployment target.

**How to avoid:**
Set `site_url` to the GitHub Pages URL before the deploy workflow runs. If the same `mkdocs.yml` is used for both the nginx Docker container and GitHub Pages, manage this with a CI environment variable override or maintain a separate `mkdocs-ghpages.yml`. The recommended single-source approach: set `site_url` to the permanent public URL (GitHub Pages URL), and update the nginx Docker build to also use that URL (or leave it empty and rely on relative paths).

**Warning signs:**
- `404.html` loads with unstyled HTML on GitHub Pages
- Browser DevTools shows assets loading from `dev.master-of-puppets.work` on the GitHub Pages domain
- `<link rel="canonical">` in page source points to the nginx server URL, not the Pages URL

**Phase to address:**
Phase 1 (mkdocs.yml + workflow setup). This must be resolved before the first deploy. The `site_url` change is a one-line fix but has downstream effects on the nginx Docker build if they share `mkdocs.yml`.

---

### Pitfall 2: The `offline` Plugin Forces `use_directory_urls: false` — Breaking All Pretty URLs on GitHub Pages

**What goes wrong:**
`docs/mkdocs.yml` currently includes the `offline` plugin. The offline plugin automatically overrides `use_directory_urls` to `false` at build time. This transforms `getting-started/install/` (pretty URL) into `getting-started/install.html` (file-based URL). On GitHub Pages, all existing deep links (from the README, from other documentation, from external references built against the Docker nginx URL) break because the URL structure changes from directory-style to file-extension-style.

Additionally, `use_directory_urls: false` is specifically designed for `file://` protocol access (opening HTML files directly from disk). GitHub Pages serves over `https://`, making the offline plugin's URL rewriting unnecessary and harmful. The blog pagination feature also has a known regression with `use_directory_urls: false`.

**Why it happens:**
The offline plugin is appropriate for distributing docs as a zip file to air-gapped users. It was added in v9.0 for exactly that purpose. When deploying the same source to a hosted URL, the plugin continues to apply its `file://`-friendly URL transformation even though the target is a live server.

**How to avoid:**
Disable the `offline` plugin for the GitHub Pages build. The recommended pattern from MkDocs Material docs is to use an environment variable:

```yaml
plugins:
  - offline:
      enabled: !ENV [OFFLINE_BUILD, false]
```

The GitHub Actions deploy workflow does not set `OFFLINE_BUILD`, so the plugin is inactive. The air-gap Docker build sets `OFFLINE_BUILD=true`.

Alternatively, maintain a separate `mkdocs-ghpages.yml` that omits the `offline` plugin entirely. Either approach prevents the URL rewrite.

**Warning signs:**
- All page URLs on GitHub Pages end in `.html` instead of `/`
- Navigation links from the sidebar go to `page.html` instead of `page/`
- Links from the README or external sites pointing to `docs/getting-started/install/` return 404
- `mkdocs build` output shows `use_directory_urls: False` in config summary even though it's not set in `mkdocs.yml`

**Phase to address:**
Phase 1 (mkdocs.yml + workflow setup). Must be resolved before the first deploy to prevent URL structure churn.

---

### Pitfall 3: Privacy Plugin Cache Not Committed to Git — CI Downloads Fonts on Every Build, Fails in Rate-Limited or Restricted Networks

**What goes wrong:**
The privacy plugin caches downloaded external assets (Google Fonts, Mermaid from unpkg.com, iframe-worker from unpkg.com) in `docs/.cache/plugin/privacy/`. Currently, `docs/.cache/` is tracked in git (confirmed: `git ls-files docs/.cache/` lists files). However, the root `.gitignore` does not list `docs/site/` as ignored (it is also tracked). When a GitHub Actions workflow runs `mkdocs build`, the privacy plugin checks whether the cache exists. If the cache files are present in the checkout, no network requests are made and the build is fast and air-gap safe.

The risk: if a future commit adds `docs/.cache/` to `.gitignore` (a common "cleanup" instinct), the cache is no longer committed. The next CI run will attempt to download external assets from Google Fonts, fonts.gstatic.com, and unpkg.com. These may succeed on GitHub-hosted runners, but will fail if:
- The runner has outbound network restrictions
- unpkg.com or Google Fonts rate-limits GitHub Actions IP ranges
- The privacy plugin bug (issue #8040, affecting 9.6.5) causes partial replacement failures

The build will still pass if downloads succeed, but will silently serve CDN-hosted fonts rather than self-hosted ones, breaking the air-gap compliance guarantee.

**Why it happens:**
Developers instinctively add build-time cache directories to `.gitignore`. The `.cache/` directory looks like generated content. The consequence — that the privacy plugin's self-hosted asset guarantee requires the cache to be available — is not visible from the directory name alone.

**How to avoid:**
Keep `docs/.cache/` committed to git (current state). Add a comment in the root `.gitignore` explicitly stating why it is NOT listed:

```
# docs/.cache is intentionally tracked — the MkDocs privacy plugin uses it
# to self-host external assets (fonts, JS) without CDN calls at build time.
# DO NOT add docs/.cache to .gitignore.
```

Alternatively, configure GitHub Actions to cache the `.cache/` directory using `actions/cache` and key it on `docs/requirements.txt`. This is the MkDocs Material team's recommended approach for CI when the cache is not committed.

**Warning signs:**
- `mkdocs build` output shows "Downloading asset from fonts.googleapis.com..." during CI
- CSS in the built site references `fonts.googleapis.com` instead of `/assets/external/`
- A new `docs/` `.gitignore` or edit to the root `.gitignore` adds `*.cache` or `.cache/`
- CI build time suddenly increases by 30–60 seconds (downloading fonts)

**Phase to address:**
Phase 1 (workflow setup). Add the protective comment to `.gitignore` at the same time as the deploy workflow is created.

---

### Pitfall 4: Jekyll Processing Interferes With Material Theme Assets on the `gh-pages` Branch

**What goes wrong:**
GitHub Pages, by default, runs Jekyll on any branch configured as the publishing source. MkDocs generates asset filenames that begin with underscores (e.g., `_assets/`, `search/search_index.json`) or are inside directories starting with underscores. Jekyll ignores files and directories prefixed with `_` and does not copy them to the served output. The built MkDocs site will appear to load (the HTML is served) but all CSS, JS, search, and image assets are missing.

The fix is a `.nojekyll` file at the root of the `gh-pages` branch, which tells GitHub Pages to serve files as-is without Jekyll processing.

`mkdocs gh-deploy` (the standard deployment command) automatically creates `.nojekyll` in the deployed branch. However, if a custom workflow uses `actions/upload-pages-artifact` + `actions/deploy-pages` (the modern GitHub Pages Actions approach), `.nojekyll` must be explicitly included in the artifact directory. If it is absent, Jekyll runs and strips the underscore-prefixed paths.

**Why it happens:**
The `.nojekyll` file is a non-obvious GitHub Pages requirement. It is not part of the MkDocs built site — it has to be added by the deployment step. Workflows that do `mkdocs build` then upload the `site/` directory directly (without going through `gh-deploy`) forget this file.

**How to avoid:**
Use `mkdocs gh-deploy --force` as the deploy command — it handles `.nojekyll` automatically. If using the `actions/deploy-pages` approach, create `.nojekyll` explicitly after the build:

```yaml
- name: Build docs
  run: mkdocs build --strict
  working-directory: docs

- name: Add .nojekyll
  run: touch docs/site/.nojekyll
```

Then upload `docs/site/` as the Pages artifact.

**Warning signs:**
- The deployed GitHub Pages site loads HTML but has no styling
- Browser DevTools shows 404s for `/assets/...` paths
- The `gh-pages` branch does not contain a `.nojekyll` file at its root
- `search/search_index.json` 404s and search is non-functional

**Phase to address:**
Phase 1 (workflow creation). Verify by inspecting the deployed `gh-pages` branch for the presence of `.nojekyll`.

---

### Pitfall 5: `docs/` Is a Subdirectory — `gh-deploy` Must Be Run With `--config-file`, Not From the Repo Root

**What goes wrong:**
`mkdocs.yml` lives at `docs/mkdocs.yml`, not at the repository root. `mkdocs gh-deploy` run from the repo root (`/`) will fail to find `mkdocs.yml` and error out. The CI workflow must either `cd docs` before running the deploy command or use `mkdocs gh-deploy --config-file docs/mkdocs.yml`. Omitting this detail is the most common first-run failure for non-root MkDocs projects.

Additionally, `mkdocs.yml` has relative `docs_dir` paths. Running `mkdocs build` from the wrong working directory will cause all docs paths to resolve incorrectly, producing a valid-looking but empty or wrong site.

**Why it happens:**
Most MkDocs tutorials assume `mkdocs.yml` is at the repo root. Copy-pasted workflow templates do not include `working-directory: docs` steps. The existing `ci.yml` correctly uses `working-directory: docs` for the build step — the deploy workflow must replicate this.

**How to avoid:**
In the deploy workflow, always use `working-directory: docs` for every `mkdocs` command, matching the existing `ci.yml` pattern:

```yaml
- name: Deploy to GitHub Pages
  working-directory: docs
  run: mkdocs gh-deploy --force
```

**Warning signs:**
- `Error: Config file 'mkdocs.yml' does not exist.` in workflow logs
- `mkdocs gh-deploy` exits 1 immediately without building
- The `ci.yml` docs job passes but the deploy workflow fails at the same `mkdocs` step

**Phase to address:**
Phase 1 (workflow creation). Caught immediately on first run but wastes a deploy cycle.

---

### Pitfall 6: CNAME File Deleted on Every Deploy — Custom Domain Reset

**What goes wrong:**
`mkdocs gh-deploy --force` completely replaces the `gh-pages` branch on every run. If a custom domain is configured in the GitHub Pages settings (which creates a `CNAME` file in the branch root), `gh-deploy` will delete it. GitHub Pages then shows "Domain removed" and falls back to `<username>.github.io/<repo>`. Any DNS CNAME records pointing to the custom domain continue working at the DNS level, but GitHub Pages no longer responds to the domain, causing a site outage after the first deploy.

**Why it happens:**
`mkdocs gh-deploy` replaces the entire branch. Unless `CNAME` is a tracked file in the MkDocs source (`docs/docs/CNAME` or in `extra_files`), it is lost on every deploy.

**How to avoid:**
If a custom domain is used for GitHub Pages, add a `CNAME` file to `docs/docs/` (the MkDocs `docs_dir`) containing the bare domain. MkDocs will copy it to `site/` and `gh-deploy` will include it in the branch. Current state has no custom domain configured (v14.2 targets the default `github.io` URL), so this is not an immediate issue — but the `mkdocs.yml` `site_url` must be set to the correct `github.io` URL, not a custom domain, before the first deploy.

**Warning signs:**
- GitHub Pages settings show "Custom domain: (none)" after a deploy that previously had a domain set
- `https://<custom-domain>` returns the `<username>.github.io` default page instead of the docs site
- The `gh-pages` branch has no `CNAME` file after a deploy

**Phase to address:**
Phase 1 (workflow creation). No action needed if no custom domain is used for GH Pages — but document it in the workflow comments to prevent future operators from setting a custom domain via the GitHub UI without also adding the CNAME file.

---

### Pitfall 7: Pre-Committed `openapi.json` and `docs/site/` Are Tracked in Git — `gh-deploy` Produces a Divergent Branch History

**What goes wrong:**
`docs/site/` is currently tracked in git (confirmed: `git ls-files docs/site/` returns results). `docs/docs/api-reference/openapi.json` is also committed. The `gh-pages` branch created by `mkdocs gh-deploy` is a separate orphan branch containing only the built site. The tracked `docs/site/` on `main` serves no purpose once GitHub Pages is live — it is a stale, redundant copy of the site that adds ~MB to the repository and causes confusion about which is authoritative.

There is a secondary risk: if `docs/site/` stays in `main` and someone runs `mkdocs build` locally without the privacy plugin cache, the regenerated `docs/site/` may differ from what GH Pages serves (different asset paths, different cache state). `git diff` becomes noisy and PRs include spurious site changes.

**Why it happens:**
`docs/site/` was likely committed when the nginx Docker build was set up (the Dockerfile does a `COPY docs/ .` which includes it). There was no `.gitignore` for `docs/site/` because the docker build needed everything. GitHub Pages introduces a second deployment path where the site is built in CI, making the committed `docs/site/` redundant.

**How to avoid:**
Add `docs/site/` to the root `.gitignore` before creating the deploy workflow. The nginx Docker build regenerates `docs/site/` during its own builder stage (via `RUN mkdocs build --strict`) and does not rely on the committed copy. The `gh-deploy` workflow also regenerates it. After removing from git tracking:

```bash
git rm -r --cached docs/site/
echo "docs/site/" >> .gitignore
```

The pre-committed `openapi.json` in `docs/docs/api-reference/` should remain tracked — it is the source file, not build output.

**Warning signs:**
- PRs include diffs in `docs/site/**` with no corresponding source change
- Repository size grows by several MB per deploy cycle as old site content accumulates in git history
- `git status` shows `docs/site/` as modified after running `mkdocs build` locally

**Phase to address:**
Phase 1 (pre-deploy cleanup). Remove `docs/site/` from git tracking before the first `gh-deploy` runs. If removed after the first deploy, history retains the bloat but future commits are clean.

---

### Pitfall 8: `mkdocs --strict` in the Deploy Workflow Fails on New Warnings Introduced by the `site_url` Change

**What goes wrong:**
When `site_url` is changed from the nginx URL to the GitHub Pages URL, MkDocs may generate new warnings about absolute links that are now cross-domain, or about anchor validation mismatches if the URL structure changes (e.g., due to the `offline` plugin's `use_directory_urls` override being removed). With `--strict` in the deploy workflow, any new warning becomes a build failure that blocks the deploy.

Specific known risk: `docs/docs/api-reference/index.md` contains `<swagger-ui src="openapi.json" validatorUrl="none"/>`. The `mkdocs-swagger-ui-tag` plugin (v0.8.0) embeds the Swagger UI JavaScript statically (not from CDN). However, the `validatorUrl="none"` attribute suppresses external validation calls. If any attribute or path handling in the plugin produces a warning under strict mode with the new `site_url`, the deploy blocks.

**Why it happens:**
`--strict` is a zero-tolerance gate. It was added to the CI build job in v14.1 specifically to prevent regressions — but it also means that changes to `site_url` or plugin configuration can surface new warnings that were previously suppressed or absent.

**How to avoid:**
Test the full `mkdocs build --strict` locally after making the `site_url` and plugin changes before the deploy workflow is committed. If warnings appear, resolve them before the first push. Do not lower `--strict` to unblock the deploy — fix the root cause of each warning. Common fixable warnings:
- `WARNING - Doc file '...' contains an absolute link '...', it was left as is.` — change to a relative link
- `WARNING - ... is not found in the documentation files` — update `nav:` or remove the reference

**Warning signs:**
- The `mkdocs build --strict` step in the deploy workflow exits non-zero after the `site_url` change
- Warnings appear in build output that do not appear with the current `site_url`
- The deploy workflow fails before the deploy step is even reached

**Phase to address:**
Phase 1 (mkdocs.yml changes). Run `mkdocs build --strict` locally against the updated config before pushing.

---

### Pitfall 9: GitHub Pages Source Must Be Set to Deploy From `gh-pages` Branch (or GitHub Pages Environment) — Not `main`

**What goes wrong:**
After the first `gh-deploy` push, the `gh-pages` branch exists but GitHub Pages is not automatically configured to serve from it. The repository's Pages settings (Settings > Pages > Source) default to "Deploy from a branch" with `main` (or no branch selected). Until the source is manually changed to the `gh-pages` branch (or the workflow is updated to use the GitHub Pages Actions deployment environment), the site is not live despite the branch existing and the workflow succeeding.

Additionally, if GitHub Actions workflow permissions are set to "Read" only (the default for new repositories), `git push` to `gh-pages` from the workflow fails with a `403 Permission denied` error. The workflow requires `permissions: contents: write` (for `gh-deploy` approach) or `permissions: pages: write` + `id-token: write` (for the `actions/deploy-pages` approach).

**Why it happens:**
GitHub Pages source configuration is a one-time manual step in repository settings that is easy to forget in automation-focused workflows. The deploy workflow succeeds (branch is pushed) but the site remains dark until the setting is changed.

**How to avoid:**
After the first successful `gh-deploy` run:
1. Go to repository Settings > Pages > Source
2. Set "Deploy from a branch" → `gh-pages` → `/ (root)`
3. Save

For the workflow, add explicit permissions:
```yaml
permissions:
  contents: write
```

Document this as a one-time setup step in the deploy workflow file's comments.

**Warning signs:**
- Workflow reports "Push to gh-pages: success" but `https://<user>.github.io/<repo>` returns 404
- Repository Settings > Pages shows "Source: None" or "Source: main"
- Workflow log shows `remote: Permission denied` on the git push step

**Phase to address:**
Phase 1 (workflow creation). The manual Pages settings step must be documented as a post-workflow-creation action, not assumed to auto-configure.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Committing `docs/site/` to `main` | No setup needed for local nginx Docker build | Every `mkdocs build` run creates noisy diffs; repo bloat; two authoritative copies | Never once GH Pages is live — add to `.gitignore` |
| Keeping `offline` plugin active for GH Pages build | No config change | All URLs change from `/page/` to `page.html`; breaks all existing deep links | Never — disable for GH Pages build |
| Using existing `site_url` (nginx URL) for GH Pages deploy | Zero config change needed | Canonical links and 404 assets point to wrong server; dual-serving causes SEO confusion | Never — update before first deploy |
| Skipping `--strict` in deploy workflow | Faster to set up; deploy never blocks | Regressions ship silently; `--strict` is already in CI and removing it creates inconsistency | Never — keep `--strict` in both CI and deploy |
| Not committing `docs/.cache/` to git | Clean-looking repo | Privacy plugin downloads fonts on every CI build; fragile if CDN throttles GitHub runner IPs | Only acceptable if GitHub Actions cache (`actions/cache`) is configured as a replacement |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `mkdocs gh-deploy` + non-root `mkdocs.yml` | Running from repo root without `--config-file` | Use `working-directory: docs` in the workflow step, matching `ci.yml` |
| GitHub Pages + MkDocs `offline` plugin | Leaving plugin active in the GH Pages build | Disable with `enabled: !ENV [OFFLINE_BUILD, false]`; set `OFFLINE_BUILD=true` in Dockerfile builder only |
| GitHub Pages + `site_url` | Keeping the nginx URL in `site_url` | Set `site_url` to the GitHub Pages URL; rebuild nginx Docker image to use the same URL or leave `site_url` empty |
| `gh-deploy --force` + custom domain CNAME | Configuring domain via GitHub UI without adding `CNAME` to `docs/docs/` | Add `CNAME` file to `docs_dir`; `gh-deploy` will include it in every push |
| `mkdocs-swagger-ui-tag` on GitHub Pages | Assuming CDN-hosted Swagger UI | The plugin bundles Swagger UI statically — no CDN calls; works fine on GH Pages |
| Privacy plugin cache in CI | Adding `docs/.cache/` to `.gitignore` | Keep cache committed OR add `actions/cache` step keyed on `docs/requirements.txt` |
| GitHub Pages write permissions | Default `GITHUB_TOKEN` is read-only | Add `permissions: contents: write` to the deploy job |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Privacy plugin cache not committed or cached | CI downloads Google Fonts + Mermaid + iframe-worker on every build: 30–60s per run | Commit `docs/.cache/` or use `actions/cache` in workflow | On every run if cache is absent |
| `docs/site/` tracked in git | Every deploy cycle adds MBs to git history; clone times grow | Add `docs/site/` to `.gitignore` and remove from tracking | Noticeable after 5–10 deploys |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Dual-serving docs (nginx + GH Pages) with different `site_url` | Search engines index nginx version as canonical; GH Pages version treated as duplicate; confuses users with two URLs | Set canonical `site_url` to one target; add `robots.txt` to the other to prevent dual-indexing |
| GitHub Pages source branch set to `main` by accident | Serves raw Markdown source (not the built site) if Pages processes it via Jekyll | Ensure source is `gh-pages` branch; verify `jekyll: false` or `.nojekyll` present |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| `site_url` pointing to nginx server | Users who find the GH Pages site via search or README link land on a page whose canonical URL redirects to the internal server (inaccessible externally) | Set `site_url` to the publicly accessible GH Pages URL |
| `offline` plugin active on GH Pages | All page URLs end in `.html`; ugly, inconsistent with Material docs conventions; links from other sites using `/page/` format 404 | Disable offline plugin for hosted builds |
| No Pages source configured after deploy | README link to GitHub Pages URL returns 404; users report docs are broken | Document the one-time manual Pages source configuration step prominently in the workflow file |

---

## "Looks Done But Isn't" Checklist

- [ ] **`site_url` updated:** Build succeeds — verify `site/sitemap.xml` and `site/404.html` contain the GitHub Pages URL, not the nginx URL
- [ ] **`offline` plugin disabled for GH Pages:** Build succeeds — verify `site/getting-started/install/index.html` exists (not `site/getting-started/install.html`); confirm `use_directory_urls` is `true` in build output
- [ ] **`.nojekyll` present in `gh-pages` branch:** Deploy succeeds — check `gh-pages` branch via `git show gh-pages:.nojekyll`; verify the deployed site shows correct CSS
- [ ] **GitHub Pages source configured:** Workflow pushes `gh-pages` — verify `https://<user>.github.io/<repo>` returns the docs site (not 404)
- [ ] **`docs/site/` removed from git tracking:** Add to `.gitignore` — verify `git status` after `mkdocs build` shows no `docs/site/` changes
- [ ] **Privacy plugin cache works in CI:** Deploy workflow succeeds — check workflow logs for absence of "Downloading asset from fonts.googleapis.com" lines; verify self-hosted fonts in built CSS
- [ ] **`mkdocs --strict` passes with new config:** All the above changes applied — run `mkdocs build --strict` locally before pushing; zero warnings

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong `site_url` shipped to GH Pages | LOW | Update `site_url` in `mkdocs.yml`, push to `main`, workflow redeploys |
| `offline` plugin active on GH Pages (all URLs are `.html`) | MEDIUM | Disable plugin, redeploy — all URLs change; any existing external links to `/page/` are now correct but links to `page.html` break; consider GH Pages redirect rules if external links exist |
| Missing `.nojekyll` (site loads with no CSS) | LOW | Add `touch site/.nojekyll` step to workflow, push, redeploy |
| GH Pages source not configured | LOW | One manual click in repository Settings > Pages; takes effect on next deploy |
| `docs/site/` accumulated in git history | MEDIUM | `git rm -r --cached docs/site/`, add to `.gitignore`, commit; history retains old size but future commits are clean; use `git filter-repo` only if repo size is a genuine problem |
| Privacy plugin downloads fonts in CI (cache missing) | LOW | Commit `docs/.cache/` to git or add `actions/cache` step; next run is fast again |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Wrong `site_url` (nginx URL on GH Pages) | Phase 1: mkdocs.yml update | Check `site/sitemap.xml` URLs and `site/404.html` asset paths after build |
| `offline` plugin breaks URL structure | Phase 1: mkdocs.yml update | Verify `use_directory_urls: true` in build output; check `site/` for `/page/index.html` structure |
| `.nojekyll` missing from deployed branch | Phase 1: workflow creation | Inspect `gh-pages` branch; verify styled page loads at GH Pages URL |
| GitHub Pages source not configured | Phase 1: workflow creation (document as manual step) | Navigate to GH Pages URL; confirm it serves the docs site |
| `docs/site/` tracked in git | Phase 1: pre-deploy cleanup | `git ls-files docs/site/` returns nothing after cleanup |
| Privacy plugin cache unprotected | Phase 1: `.gitignore` update | Workflow logs show no CDN download lines; `docs/.cache/` still present in checkout |
| `docs/` subdirectory misconfiguration in workflow | Phase 1: workflow creation | Workflow uses `working-directory: docs` matching `ci.yml` pattern |
| `--strict` failures from config changes | Phase 1: local testing gate | `mkdocs build --strict` passes locally before PR is created |
| CNAME deleted on deploy | Not applicable for v14.2 (no custom domain) — document for future | If custom domain added: `CNAME` file present in `docs/docs/`; survives a redeploy |

---

## Sources

- Direct codebase inspection: `docs/mkdocs.yml` (current `site_url`, plugin list including `offline` and `privacy`)
- Direct codebase inspection: `docs/requirements.txt` (`mkdocs-material==9.7.5`, `mkdocs-swagger-ui-tag==0.8.0`)
- Direct codebase inspection: `.github/workflows/ci.yml` (`working-directory: docs`, `mkdocs build --strict`)
- Direct codebase inspection: `git ls-files docs/.cache/` and `git ls-files docs/site/` (both currently tracked)
- Direct codebase inspection: `docs/docs/api-reference/index.md` (Swagger UI tag with pre-committed `openapi.json`)
- [MkDocs Material — Publishing your site (GitHub Pages)](https://squidfunk.github.io/mkdocs-material/publishing-your-site/)
- [MkDocs Material — Offline plugin](https://squidfunk.github.io/mkdocs-material/plugins/offline/)
- [MkDocs Material — Privacy plugin](https://squidfunk.github.io/mkdocs-material/plugins/privacy/)
- [MkDocs Material — Issue #4678: Problem loading assets on GitHub Pages](https://github.com/squidfunk/mkdocs-material/issues/4678)
- [MkDocs Material — Issue #2520: site_url documentation gap](https://github.com/squidfunk/mkdocs-material/issues/2520)
- [MkDocs Material — Issue #8040: Privacy plugin does not replace all external URLs (9.6.5)](https://github.com/squidfunk/mkdocs-material/issues/8040)
- [MkDocs — Issue #1257: gh-deploy removes custom domain CNAME](https://github.com/mkdocs/mkdocs/issues/1257)
- [MkDocs — Issue #1496: Document CNAME files for gh-pages custom domains](https://github.com/mkdocs/mkdocs/issues/1496)
- [GitHub Docs — Configuring a publishing source for GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [MkDocs upstream — deploying-your-docs.md](https://www.mkdocs.org/user-guide/deploying-your-docs/)
- [MkDocs Material — offline plugin source (use_directory_urls override)](https://github.com/squidfunk/mkdocs-material/blob/master/src/plugins/offline/plugin.py)

---
*Pitfalls research for: v14.2 — Docs on GitHub Pages (adding GH Pages to existing MkDocs Material site)*
*Researched: 2026-03-26*
