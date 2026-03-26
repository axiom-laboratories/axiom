# Feature Research

**Domain:** GitHub Pages deployment of MkDocs Material documentation site
**Researched:** 2026-03-26
**Confidence:** HIGH (MkDocs official docs + GitHub Pages official docs + Material for MkDocs publishing guide verified)

---

## Context: What v14.2 Is Adding

v14.2 is a deployment infrastructure milestone. The MkDocs site already exists, builds cleanly, and passes
`mkdocs --strict` in CI. The goal is to publish the CE documentation to GitHub Pages with automated
deployment on every push to `main`.

**What already exists (do not re-implement):**
- MkDocs Material site in `docs/` — `mkdocs.yml`, all markdown, `requirements.txt`
- `docs/docs/api-reference/openapi.json` — pre-committed static file (already in repo)
- Privacy plugin + offline plugin — makes site CDN-free, all assets local
- `mkdocs --strict` CI gate in `ci.yml` — runs on every PR and push to main
- `docs/Dockerfile` — two-stage Docker build (builder + nginx) for self-hosted container
- `site_url: https://dev.master-of-puppets.work/docs/` — currently set to the self-hosted deployment

**What needs to be added:**
- A new GitHub Actions workflow that runs `mkdocs build --strict` then deploys to GitHub Pages
- A `site_url` update in `mkdocs.yml` (or env-var override in the deploy workflow) pointing to the GH Pages URL
- A pre-committed `openapi.json` regeneration script (for maintainers to run locally before committing)
- (Optional) `CNAME` file in `docs/docs/` if a custom domain is used

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any project docs site on GitHub Pages must have. Missing these = broken or invisible site.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Automated deploy on push to main** | Docs update automatically when content changes; manual deploy is error-prone and forgotten | LOW | GitHub Actions workflow: `mkdocs gh-deploy --force` or `actions/deploy-pages`. Triggers on `push: branches: [main]` |
| **Deploy to `gh-pages` branch** | GitHub Pages serves from a dedicated branch; project pages (not user pages) deploy to `gh-pages` | LOW | `mkdocs gh-deploy --force` handles this entirely — builds, commits, pushes. No separate action needed. |
| **`site_url` set to GH Pages URL** | MkDocs uses `site_url` for sitemap, canonical URLs, and asset resolution. Wrong URL = broken sitemap, wrong canonical tags | LOW | Must match the actual GH Pages URL: `https://<org>.github.io/<repo>/` for project pages, or custom domain if configured. The current value (`https://dev.master-of-puppets.work/docs/`) must change. |
| **`contents: write` permission on the workflow** | `mkdocs gh-deploy` pushes to `gh-pages` branch — requires write access | LOW | Add `permissions: contents: write` to the workflow job. Without it, the push fails with a 403. |
| **`openapi.json` available at build time** | The `mkdocs build` step in CI needs `docs/docs/api-reference/openapi.json` to exist; without it, the swagger-ui-tag plugin fails | LOW | Already solved: `openapi.json` is committed to the repo. The GH Actions build can use it directly without regenerating. Add a local regeneration script for maintainer use. |
| **Auto-generated 404 page** | GitHub Pages serves `404.html` automatically for missing routes — only works with a custom domain | LOW | MkDocs generates `404.html` by default. No action needed — it is included in the build output automatically. NOTE: GitHub Pages only serves the custom `404.html` when a custom domain is set; on `*.github.io` subdomains the 404 is GitHub's generic page. |
| **Sitemap** | Search engines need a sitemap to index docs pages | LOW | MkDocs Material generates `sitemap.xml` automatically when `site_url` is set correctly. No additional config needed. |

### Differentiators (Competitive Advantage)

Features that go beyond minimum and improve the experience for readers or maintainers.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Custom domain (`CNAME` file)** | `docs.axiom.example.com` instead of `org.github.io/repo/` — more professional, stable URL for users to bookmark | LOW | Place a `CNAME` file in `docs/docs/` (the MkDocs `docs_dir`). MkDocs copies it to the build output on every deploy, preventing GitHub's auto-generated CNAME from being wiped. File contains one line: the bare domain (e.g., `docs.axiom.sh`). **Critical**: must be in `docs_dir`, not the gh-pages branch root — the branch is overwritten on every deploy. |
| **`robots.txt`** | Tells crawlers which pages to index. MkDocs does not generate one by default — without it, crawlers use their default behaviour (index everything). For a public docs site this is fine, but explicit `Allow: /` with `Sitemap:` pointer is cleaner | LOW | Create `docs/docs/robots.txt` with `User-agent: *`, `Allow: /`, and `Sitemap: <site_url>sitemap.xml`. MkDocs copies static files from `docs_dir` to the build output. |
| **Weekly pip cache in the deploy workflow** | Speeds up repeated workflow runs; MkDocs Material's plugins use caching | LOW | Use `cache_id=$(date --utc '+%V')` and cache `~/.cache/pip`. Material for MkDocs explicitly recommends this pattern in their publishing guide. |
| **Deploy only on push to main (not on PRs)** | Avoids deploying unreviewed content; PRs already get the `mkdocs build --strict` CI gate | LOW | Use separate `ci.yml` (build check on PRs) vs `deploy.yml` (deploy on push to main). The existing `ci.yml` docs job already does the build check — the new workflow only needs to handle the deploy. |
| **Strict build gate before deploy** | Prevents deploying a broken site; any MkDocs warning fails the build | LOW | Already in place via `ci.yml`. The deploy workflow should also run `mkdocs build --strict` (not just deploy) to catch any environment-specific issues in the deploy runner. |
| **Pre-committed `openapi.json` regeneration script** | Maintainers need a clear workflow for updating the API reference when the FastAPI schema changes. Without a script they will forget the process. | LOW | A small shell script or Python script that runs `export_openapi.py` with the correct env vars and writes to `docs/docs/api-reference/openapi.json`. Commit the output. The Docker build already does this — extract the relevant `RUN` command into a `scripts/regenerate_openapi.sh`. |
| **Docs deploy separated from CI workflow** | Cleaner separation of concerns; deploy has different permissions than test/lint; `permissions: contents: write` should not be on the main CI job | LOW | Create `.github/workflows/docs-deploy.yml` separate from `ci.yml`. `ci.yml` keeps `permissions: contents: read` (default). |

### Anti-Features (Explicitly Avoid)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **`mike` versioned docs** | Seems like best practice for a versioned product | Requires clearing the existing `gh-pages` branch and starting over with a versioned structure; `mike delete --all` would wipe any existing non-versioned deploy. For a single-branch docs site with no intention of hosting previous versions, `mike` adds complexity without value. The milestone spec does not require version selectors. | Use standard `mkdocs gh-deploy`. If versioned docs become needed in the future, `mike` can be adopted then — but it cannot be grafted onto an existing plain `gh-deploy` branch without a migration. |
| **`actions/deploy-pages` artifact approach** | GitHub officially recommends this for new projects | Requires switching Pages source from "gh-pages branch" to "GitHub Actions" in repo settings — a repository configuration change that is harder to document and audit. `mkdocs gh-deploy` produces identical output and is the MkDocs-idiomatic approach, explicitly recommended in MkDocs Material's publishing guide. | Stick with `mkdocs gh-deploy --force`. It is simpler, well-documented, and universally understood by MkDocs users. |
| **Rebuilding openapi.json in the deploy workflow** | Keeps the API reference always up to date without manual commits | Requires installing ALL FastAPI dependencies in the docs workflow (adds ~2 minutes, breaks if deps conflict), importing `agent_service` which pulls in PostgreSQL drivers that need build tools. The Docker builder stage does this correctly with full dependency isolation. | Commit `openapi.json` to the repo (already done). Provide a local regeneration script for maintainers to run after API changes. This is the explicit pattern the PROJECT.md milestone spec calls out. |
| **Deploying the nginx container to GitHub Pages** | "Use the same artifact as self-hosted" | GitHub Pages serves static files only — no nginx, no container runtime. The MkDocs `site/` directory output is what gets deployed, not the Docker image. | Build the static site with `mkdocs build` in the workflow, deploy the `site/` directory to `gh-pages`. The nginx container remains for the self-hosted `compose.server.yaml` deployment. |
| **Privacy plugin asset downloads in CI** | Ensures all external assets are bundled | Privacy plugin downloads external fonts/scripts at build time. On GitHub Pages, the site is already CDN-free (all fonts self-hosted). Running the privacy plugin in CI with network access is redundant and slows builds. The assets are already committed to the repo via the privacy plugin cache (`.cache/plugin/privacy/`). | The privacy plugin cache in `docs/.cache/` should be committed or restored from cache between runs. Alternatively, since the site is already CDN-free, the privacy plugin's download step is a no-op on subsequent builds. |
| **Separate docs repository** | "Cleaner separation" | Splits the docs lifecycle from the code lifecycle. When API changes, docs updates and code changes must be coordinated across two repos. PRs that change both code and docs cannot be reviewed atomically. | Deploy from the same repo. The `docs/` directory is already well-isolated. A `push: paths: ['docs/**']` filter on the deploy workflow is a sufficient trigger scoping mechanism if desired. |

---

## Feature Dependencies

```
[openapi.json in repo]
    └──required-by──> [mkdocs build --strict in deploy workflow]
    └──required-by──> [Swagger UI in API reference page]

[site_url updated to GH Pages URL]
    └──required-by──> [sitemap.xml correctness]
    └──required-by──> [canonical URL tags]
    └──required-by──> [CNAME / custom domain routing]

[gh-pages branch created by first deploy]
    └──required-by──> [GitHub Pages source configured in repo settings]

[deploy workflow with contents: write permission]
    └──required-by──> [mkdocs gh-deploy push to gh-pages]

[CNAME file in docs/docs/]
    └──required-by──> [custom domain routing]
    └──required-by──> [GitHub HTTPS enforcement for custom domain]
    (independent of all other features — only needed if custom domain is used)
```

### Dependency Notes

- **`site_url` must be updated before first deploy**: MkDocs bakes `site_url` into the sitemap and all
  canonical link tags at build time. A wrong `site_url` persists in every page until rebuilt. If the GH
  Pages URL is not known at the start (e.g., waiting on custom domain DNS), use the `*.github.io/repo/`
  URL first and update when the custom domain resolves.
- **`openapi.json` is already in the repo**: The Docker build generates it but it is also committed
  (`docs/docs/api-reference/openapi.json` confirmed present). The deploy workflow does NOT need to regenerate
  it — just run `mkdocs build`. The regeneration script is a maintainer tool only.
- **Privacy plugin cache**: The `docs/.cache/` directory contains already-downloaded font assets. If this
  cache is committed to the repo (gitignore check needed), the deploy workflow builds offline correctly.
  If not committed, the privacy plugin will attempt to download fonts from Google on every workflow run —
  which works but makes the build non-deterministic and slower. Check `.gitignore` for `docs/.cache/`.
- **`mkdocs gh-deploy` overwrites gh-pages branch root**: Any files placed manually in the `gh-pages`
  branch (e.g., via GitHub UI "Add custom domain" button) will be wiped on next deploy. The only safe
  way to persist files (CNAME, robots.txt) is to include them in `docs/docs/` (the `docs_dir`).

---

## MVP Definition

### Launch With (v14.2)

Minimum viable deployment — what's needed to have the docs on GitHub Pages.

- [ ] Updated `site_url` in `mkdocs.yml` pointing to GH Pages URL — required for sitemap and canonical URLs
- [ ] `.github/workflows/docs-deploy.yml` — triggers on push to main, runs `mkdocs build --strict` then `mkdocs gh-deploy --force`
- [ ] `permissions: contents: write` on the deploy job
- [ ] GitHub Pages source set to `gh-pages` branch (repo settings — documented as a manual step)
- [ ] `openapi.json` regeneration script (shell or Python) committed to `scripts/` — maintainer tool

### Add After Validation (v14.2 stretch or v14.3)

- [ ] `docs/docs/CNAME` file — only if a custom domain is chosen; DNS setup documented as a manual step
- [ ] `docs/docs/robots.txt` — trivial to add, improves SEO discoverability
- [ ] Deploy trigger scoped to `paths: ['docs/**', '.github/workflows/docs-deploy.yml']` — avoids unnecessary redeploys on unrelated code changes

### Future Consideration (v15+)

- [ ] `mike` versioned docs — only if maintaining old version docs alongside new releases becomes a need;
  requires migration from plain `gh-deploy` and adds ongoing branch management complexity
- [ ] Google Search Console + Bing Webmaster Tools submission — post-launch SEO step once the site is live
  and indexed; not a code change
- [ ] `actions/deploy-pages` migration — only if GitHub deprecates the `gh-pages` branch approach (no
  indication this is planned)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Deploy workflow (docs-deploy.yml) | HIGH — without it, nothing is on GH Pages | LOW | P1 |
| site_url update | HIGH — broken sitemap and canonicals without it | LOW | P1 |
| openapi.json regeneration script | MEDIUM — maintainer DX; docs build already works | LOW | P1 |
| CNAME file + custom domain | MEDIUM — cleaner URL, but `*.github.io` works fine | LOW | P2 |
| robots.txt | LOW — search engines index without it; cleaner with it | LOW | P2 |
| Path-scoped deploy trigger | LOW — saves CI minutes, not user-facing | LOW | P2 |
| mike versioned docs | LOW — no use case until v2.x releases exist | HIGH | P3 |
| Search Console submission | LOW — SEO benefit post-launch | LOW | P3 |

**Priority key:**
- P1: Must have for GH Pages to be live and correct
- P2: Should add in v14.2 if low-effort; otherwise v14.3
- P3: Future consideration only

---

## Key Technical Constraints From Existing Setup

### Privacy Plugin + Offline Plugin Interaction

The existing `mkdocs.yml` uses both `privacy` and `offline` plugins. The privacy plugin downloads external
assets and rewrites references to point to local copies. On the first `mkdocs build` after the privacy
plugin cache (`docs/.cache/`) is populated, subsequent builds use the cache.

**GH Actions implication**: If `docs/.cache/` is not committed to the repo, the privacy plugin will attempt
outbound HTTP requests to `fonts.googleapis.com` during the CI build. This works on GitHub-hosted runners
(they have internet access) but is non-deterministic. Check whether `docs/.cache/` is in `.gitignore`.

From git status output: `docs/.cache/plugin/privacy/assets/external/` files are showing as untracked,
which means they are NOT currently committed. The deploy workflow will need either:
(a) internet access (GitHub-hosted runners have it — this is fine), or
(b) the privacy plugin cache directories committed to the repo

Option (a) is simpler and correct for a public GitHub Pages deployment (not air-gapped).

### openapi.json Is Already Pre-Committed

Confirmed: `docs/docs/api-reference/openapi.json` exists in the repo. The Docker Dockerfile generates it
at container build time, but it is also tracked in git. The GH Actions deploy workflow just needs to run
`mkdocs build` — no FastAPI dependency installation required in the docs job.

The regeneration script (P1) is needed so maintainers know HOW to update it. Extract from Dockerfile:
```bash
DATABASE_URL=postgresql+asyncpg://dummy:dummy@localhost/dummy \
ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
API_KEY=dummy-build-key \
PYTHONPATH=puppeteer \
python puppeteer/scripts/export_openapi.py docs/docs/api-reference/openapi.json
```

### `site_url` Currently Points to Self-Hosted Instance

`mkdocs.yml` line 2: `site_url: https://dev.master-of-puppets.work/docs/`

This must be updated to the GitHub Pages URL. For a project page under the `axiom-laboratories` org:
`https://axiom-laboratories.github.io/master_of_puppets/` (or the repo slug, depending on the actual repo name).

If the GH Pages URL is not known yet (e.g., depends on which org/repo name is used), it can be passed
as an override: `mkdocs build --strict -e "site_url=https://..."` — but this is fragile. Better to update
`mkdocs.yml` directly with the correct URL as part of v14.2.

---

## Deployment Flow (Verified Pattern)

The canonical MkDocs Material + GitHub Pages flow is:

```
Push to main
    → docs-deploy.yml triggers
        → checkout (fetch-depth: 0 — needed for git history)
        → pip install -r docs/requirements.txt
        → cd docs && mkdocs build --strict      # validates site
        → cd docs && mkdocs gh-deploy --force   # builds + commits to gh-pages + pushes
    → GitHub detects gh-pages branch update
        → serves static site at <org>.github.io/<repo>/
```

**`fetch-depth: 0` is important**: `mkdocs gh-deploy` uses git to commit to gh-pages. Shallow clones
(`fetch-depth: 1`, the default) can cause issues with git operations. Use `fetch-depth: 0` in checkout.

**Git config required**: The workflow needs `git config user.name` and `git config user.email` set before
`mkdocs gh-deploy`, or the git commit in the gh-pages branch will fail. Use:
```yaml
- run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
```

---

## Sources

- [Publishing your site — Material for MkDocs](https://squidfunk.github.io/mkdocs-material/publishing-your-site/) — PRIMARY: complete workflow, permissions, caching — HIGH confidence
- [Deploying Your Docs — MkDocs](https://www.mkdocs.org/user-guide/deploying-your-docs/) — gh-pages branch strategy, CNAME file placement, 404 behavior — HIGH confidence
- [Configuring a publishing source — GitHub Docs](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) — branch vs Actions source, repo settings — HIGH confidence
- [Troubleshooting custom domains — GitHub Docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages) — CNAME overwrite issue, HTTPS enforcement — HIGH confidence
- [mkdocs.yml — master_of_puppets repo](docs/mkdocs.yml) — current site_url, plugins, requirements — HIGH confidence (direct inspection)
- [ci.yml — master_of_puppets repo](.github/workflows/ci.yml) — existing docs build job — HIGH confidence (direct inspection)
- [Dockerfile — docs/](docs/Dockerfile) — openapi.json generation command — HIGH confidence (direct inspection)
- [jimporter/mike](https://github.com/jimporter/mike) — versioned docs tool; reviewed and ruled out for v14.2 — MEDIUM confidence

---

*Feature research for: Axiom v14.2 — GitHub Pages deployment of MkDocs docs site*
*Researched: 2026-03-26*
