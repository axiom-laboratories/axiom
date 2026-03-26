# Architecture Research

**Domain:** GitHub Pages deployment of MkDocs docs site — v14.2 milestone
**Researched:** 2026-03-26
**Confidence:** HIGH (MkDocs Material official docs + direct codebase inspection)

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Source (main branch)                          │
│                                                                      │
│  docs/docs/          docs/mkdocs.yml    docs/requirements.txt        │
│  (markdown source)   (config)           (mkdocs-material + swagger)  │
│                                                                      │
│  docs/docs/api-reference/openapi.json   ← pre-committed, not         │
│                                            generated in CI           │
└──────────────────────────────────────────────────────────────────────┘
                              │
                    push to main branch
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│               .github/workflows/docs-deploy.yml (NEW)                │
│                                                                      │
│   1. checkout (fetch-depth: 0)                                       │
│   2. python setup + pip install docs/requirements.txt                │
│   3. mkdocs gh-deploy --force  (cwd: docs/)                          │
│      └── ghp-import commits site/ → gh-pages branch                 │
│                                                                      │
│   permissions: contents: write                                       │
└──────────────────────────────────────────────────────────────────────┘
                              │
                    ghp-import pushes to gh-pages
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     gh-pages branch (auto-managed)                   │
│                     docs/site/ contents committed here               │
│                     never hand-edited                                │
└──────────────────────────────────────────────────────────────────────┘
                              │
                    GitHub Pages serves
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│    https://axiom-laboratories.github.io/master_of_puppets/           │
│    (or custom domain if CNAME added later)                           │
└──────────────────────────────────────────────────────────────────────┘

EXISTING DOCKER DEPLOYMENT (unchanged, parallel path):
┌──────────────────────────────────────────────────────────────────────┐
│  docs/Dockerfile (two-stage: python:3.12-slim builder → nginx:alpine)│
│  builder stage regenerates openapi.json from FastAPI at image build  │
│  nginx serves at /docs/ path inside compose.server.yaml stack        │
│  site_url in mkdocs.yml will be updated → affects canonical URLs     │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `docs/docs/` | Markdown source, committed assets, committed `openapi.json` | Existing — no change |
| `docs/mkdocs.yml` | Build config, `site_url`, plugin declarations | Modify: update `site_url` |
| `docs/requirements.txt` | Python deps for CI/deploy (`mkdocs-material`, `mkdocs-swagger-ui-tag`) | Existing — no change |
| `.github/workflows/ci.yml` `docs` job | Gate: `mkdocs build --strict` on PRs and pushes | Existing — no change needed |
| `.github/workflows/docs-deploy.yml` | Deploy: build + push to `gh-pages` on push to main | New file |
| `gh-pages` branch | Auto-managed by `mkdocs gh-deploy`; build output only | Created by first workflow run |

---

## Recommended Project Structure

```
.github/workflows/
├── ci.yml                     # existing — docs build gate unchanged
├── release.yml                # existing — GHCR + PyPI, unchanged
└── docs-deploy.yml            # NEW — deploys to GitHub Pages on push to main

docs/
├── mkdocs.yml                 # MODIFY: update site_url to GH Pages URL
├── requirements.txt           # unchanged
├── Dockerfile                 # unchanged (Docker deployment path)
├── nginx.conf                 # unchanged (Docker deployment path)
└── docs/
    ├── api-reference/
    │   ├── index.md           # unchanged — swagger-ui-tag reads openapi.json
    │   └── openapi.json       # already committed — used as-is by both paths
    └── ...                    # all other markdown unchanged
```

### Structure Rationale

- **Separate `docs-deploy.yml`:** Deployment concerns are separate from CI validation. `ci.yml` runs on PRs to validate; `docs-deploy.yml` runs only on `push: main` to deploy. This prevents deploying in-progress PR docs to production and avoids granting `contents: write` to PR workflows.
- **`gh-pages` branch auto-managed:** `mkdocs gh-deploy` creates and maintains the branch automatically via `ghp-import`. No manual branch setup required.
- **Pre-committed `openapi.json`:** The deploy workflow only needs `docs/requirements.txt` — no FastAPI stack, asyncpg, Fernet setup, or dummy env vars. Simpler, faster, no import-time failure risk.

---

## Architectural Patterns

### Pattern 1: Separate Deployment Workflow (Recommended)

**What:** A dedicated `docs-deploy.yml` file handles only the deployment step, triggered on `push: branches: [main]` only (not PRs). `ci.yml` continues to handle the `mkdocs build --strict` validation gate.

**When to use:** Any time deployment has different trigger conditions, permissions, or side-effects than CI validation.

**Trade-offs:**
- Pro: CI gate runs on PRs without accidentally deploying; deploy only fires on merged commits.
- Pro: Permissions are scoped — `contents: write` only on the deploy workflow, not on CI matrix jobs.
- Pro: A failed deploy does not block a PR merge (validation is the gate, not deployment).
- Con: Two workflow files to maintain (minor, low overhead).

**Example:**
```yaml
# .github/workflows/docs-deploy.yml
name: Deploy Docs

on:
  push:
    branches: [main]

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0       # required: git history used by mkdocs for revision dates

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: docs/requirements.txt

      - name: Install docs dependencies
        working-directory: docs
        run: pip install -r requirements.txt

      - name: Deploy to GitHub Pages
        working-directory: docs
        run: mkdocs gh-deploy --force
```

### Pattern 2: `mkdocs gh-deploy` over `actions/deploy-pages`

**What:** Use `mkdocs gh-deploy --force` rather than the two-step `actions/upload-pages-artifact` + `actions/deploy-pages` approach.

**When to use:** MkDocs projects where simplicity is preferred and the advanced GitHub Pages environment protections are not required.

**Trade-offs:**
- Pro: Single command; no artifact upload/download round-trip; no GitHub Pages "environment" needed in repo settings.
- Pro: Official MkDocs Material recommendation (HIGH confidence — squidfunk.github.io/mkdocs-material/publishing-your-site/).
- Pro: `contents: write` is the only permission required — simpler than `pages: write` + `id-token: write`.
- Pro: No GitHub Pages source setting change required — branch-based deployment is the default mode.
- Con: No deployment protection rules (only matters for regulated environments).
- Con: `gh-pages` branch appears in repo branch list.

### Pattern 3: Pre-committed `openapi.json`

**What:** `openapi.json` is committed to `docs/docs/api-reference/openapi.json` in source control and updated locally via `puppeteer/scripts/export_openapi.py`. CI and GH Pages deploy do not regenerate it.

**When to use:** When the source application's dependencies are too heavy for a docs-only CI context, or when schema changes should be a deliberate, reviewed commit.

**Trade-offs:**
- Pro: Deploy workflow needs only `docs/requirements.txt` — no FastAPI stack, no dummy env vars.
- Pro: `openapi.json` diff is visible in PRs — schema changes are explicit and reviewable.
- Con: `openapi.json` can drift from the actual API if the regeneration script is not run after API changes. Convention required: "regenerate `openapi.json` in the same PR as API route changes."

**Current state:** `openapi.json` is confirmed committed at `docs/docs/api-reference/openapi.json` (verified via `git ls-files`). The Dockerfile builder stage that regenerates it at container build time remains correct for the Docker deployment path and is unchanged.

---

## Data Flow

### GitHub Pages Deploy Flow

```
Developer merges PR to main
        │
        ▼
docs-deploy.yml triggered (on: push: branches: [main])
        │
        ├── actions/checkout@v4 (fetch-depth: 0)
        │
        ├── pip install docs/requirements.txt
        │   └── mkdocs-material==9.7.5
        │       mkdocs-swagger-ui-tag==0.8.0
        │
        ├── mkdocs gh-deploy --force  (cwd: docs/)
        │   ├── reads docs/mkdocs.yml (site_url → GH Pages URL)
        │   ├── reads docs/docs/**/*.md
        │   ├── reads docs/docs/api-reference/openapi.json (pre-committed)
        │   ├── runs: privacy plugin (inlines fonts → local assets)
        │   ├── runs: offline plugin  ← see CRITICAL NOTE below
        │   ├── runs: swagger-ui-tag (embeds Swagger UI from openapi.json)
        │   ├── builds site/ directory
        │   └── ghp-import: commits site/ → gh-pages branch, force-pushes
        │
        └── GitHub Pages serves gh-pages branch at:
            https://axiom-laboratories.github.io/master_of_puppets/
```

### openapi.json Update Flow (manual, triggered by API changes)

```
Developer modifies FastAPI routes
        │
        ▼
Run locally (from project root):
  DATABASE_URL=postgresql+asyncpg://dummy:dummy@localhost/dummy \
  ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
  API_KEY=dummy-build-key \
  PYTHONPATH=puppeteer \
  python puppeteer/scripts/export_openapi.py docs/docs/api-reference/openapi.json
        │
        ▼
git add docs/docs/api-reference/openapi.json
git commit -m "docs: regenerate openapi.json for [change description]"
        │
        ▼
PR review → merge → docs-deploy.yml fires → updated schema live on GH Pages
```

---

## Integration Points

### Existing CI Integration

| Workflow | Change Required | Reason |
|----------|----------------|--------|
| `ci.yml` `docs` job | None | Already runs `mkdocs build --strict`; continues as PR validation gate |
| `ci.yml` backend/frontend/docker jobs | None | Unchanged |
| `release.yml` | None | GHCR/PyPI release workflow unchanged |
| `docs-deploy.yml` | New file | Deploys on push to main only |

### mkdocs.yml Changes Required

**`site_url` must be updated.** The current value is `https://dev.master-of-puppets.work/docs/` (the self-hosted Docker deployment URL). For GitHub Pages this must be the GH Pages URL so that the sitemap, canonical link tags, and search index URLs are correct.

```yaml
# Current (self-hosted Docker deployment URL):
site_url: https://dev.master-of-puppets.work/docs/

# Required for GitHub Pages (project repo under axiom-laboratories org):
site_url: https://axiom-laboratories.github.io/master_of_puppets/
```

**Note on the Docker deployment path:** After this change, the Docker-built docs image will embed the GH Pages URL as canonical. For the self-hosted deployment this means canonical tags point to GH Pages, not the local instance. This is acceptable — GH Pages is the canonical public URL. The self-hosted instance is an internal tool.

If a custom domain is configured on GH Pages later, update `site_url` to the custom domain at that point.

**`use_directory_urls` — do not change.** The default (`true`) is correct for GitHub Pages (HTTP-served). The `offline` plugin automatically sets `use_directory_urls: false` when building for local file access, but this does not affect HTTP deployments. For GH Pages, `use_directory_urls: true` gives clean `/page-name/` URLs.

MEDIUM confidence caveat: the official offline plugin docs confirm it overrides `use_directory_urls`, but do not explicitly state the scope is limited to file:// access. Verify after first deploy that internal page links resolve correctly. If links break, the fix is `use_directory_urls: true` explicitly set in `mkdocs.yml` to override the plugin.

### Permissions Model

```yaml
# Required permissions for docs-deploy.yml
permissions:
  contents: write   # mkdocs gh-deploy pushes commits to the gh-pages branch
```

No additional permissions required. The `pages: write` and `id-token: write` permissions are only needed for the `actions/deploy-pages` approach, which is not used here.

**Important:** The `GITHUB_TOKEN` default permission in many repositories is `contents: read`. The explicit `permissions: contents: write` declaration in `docs-deploy.yml` is mandatory — do not rely on repository-level default permission settings.

### GitHub Repository Settings (one-time manual step)

After the first successful `docs-deploy.yml` run creates the `gh-pages` branch:
1. Settings → Pages → Source: "Deploy from a branch"
2. Branch: `gh-pages`, folder: `/` (root)
3. Save

This is a one-time operator step — it cannot be automated from within the workflow.

---

## New vs Modified: Explicit List

### New (create from scratch)

| File | Purpose |
|------|---------|
| `.github/workflows/docs-deploy.yml` | Deploy MkDocs to GitHub Pages on push to main |

### Modified (targeted change to existing file)

| File | Change | Impact |
|------|--------|--------|
| `docs/mkdocs.yml` | Update `site_url` from self-hosted URL to GH Pages URL | Fixes canonical URLs, sitemap entries, search index URLs |

### Unchanged (explicitly confirmed — do not touch)

| File | Reason |
|------|--------|
| `.github/workflows/ci.yml` | `docs` job already runs `mkdocs build --strict`; no change needed |
| `.github/workflows/release.yml` | Release workflow for GHCR/PyPI; unrelated to docs |
| `docs/requirements.txt` | No new deps needed; `mkdocs-material` + `mkdocs-swagger-ui-tag` are sufficient |
| `docs/Dockerfile` | Docker deployment path unchanged; builder stage continues to regenerate `openapi.json` |
| `docs/nginx.conf` | Docker deployment nginx config unchanged |
| `docs/docs/api-reference/openapi.json` | Already committed; used as-is by both deploy paths |
| All markdown source files | No content changes required for GH Pages |

---

## Build Order (Phase Dependencies)

```
Phase 1: mkdocs.yml site_url update
    → No dependencies; safe to do first
    → Change: single line in docs/mkdocs.yml
    → Validation: ci.yml docs job runs mkdocs build --strict on the PR
    → Risk: LOW — single line change

Phase 2: docs-deploy.yml workflow creation
    → Depends on: Phase 1 merged (correct site_url in place before first deploy)
    → Triggers: first deploy fires on merge to main
    → Validation: check GH Actions run succeeds; check gh-pages branch created
    → Risk: LOW — mkdocs gh-deploy is idempotent; --force overwrites on every run

Phase 3: GitHub repository settings (manual operator step)
    → Depends on: Phase 2 having run successfully at least once (gh-pages branch must exist)
    → Action: Settings → Pages → source = gh-pages branch
    → Risk: NONE (read-only settings change, no code impact)
```

---

## Anti-Patterns

### Anti-Pattern 1: Adding the Deploy Step to ci.yml

**What people do:** Append `mkdocs gh-deploy` to the existing `docs` job inside `ci.yml`.

**Why it's wrong:** `ci.yml` runs on PRs (not just `main` pushes). Adding deploy there would push every PR branch's docs to the `gh-pages` branch, overwriting production docs with in-progress work. PRs from forks would also fail with permission errors since fork-originated workflows cannot write to `contents`.

**Do this instead:** New `docs-deploy.yml` with `on: push: branches: [main]` only. `ci.yml` `docs` job remains as the validation-only gate.

### Anti-Pattern 2: Regenerating openapi.json in the Deploy Workflow

**What people do:** Mirror the Dockerfile builder stage — install `puppeteer/requirements.txt` and run `export_openapi.py` in the deploy workflow.

**Why it's wrong:** Requires installing asyncpg, cryptography, FastAPI, SQLAlchemy, and related deps plus setting dummy env vars in a docs-only workflow. Adds 60-90s to deploy time. Any import-time error in `agent_service` breaks docs deployment. The pre-committed strategy is the explicit choice for this milestone.

**Do this instead:** Commit `openapi.json` alongside API changes. The Dockerfile builder stage continues to regenerate it for Docker deployments. For GH Pages, the committed file is the source of truth.

### Anti-Pattern 3: Leaving `site_url` Pointing to the Self-Hosted URL

**What people do:** Leave `site_url: https://dev.master-of-puppets.work/docs/` and deploy to GH Pages without updating it.

**Why it's wrong:** The sitemap.xml will contain self-hosted URLs. Canonical `<link>` tags in each page's `<head>` will point to the self-hosted domain. The search index will embed self-hosted URLs. Users bookmarking pages from GH Pages will see canonical tags pointing elsewhere, confusing search engines and any internal link resolver.

**Do this instead:** Set `site_url` to the GitHub Pages URL before the first deploy. The Docker deployment's image will embed the GH Pages URL as canonical — acceptable since GH Pages is the authoritative public URL.

### Anti-Pattern 4: Committing `docs/site/` to the Main Branch

**What people do:** Run `mkdocs build` locally and commit the `docs/site/` directory to the main branch as a way to "deploy."

**Why it's wrong:** The `site/` directory is hundreds of HTML/JS/CSS files. It bloats the repo, creates pointless merge conflicts, and is meaningless in code review. `mkdocs gh-deploy` handles this correctly by committing only to the separate `gh-pages` branch.

**Do this instead:** Ensure `docs/site/` is in `.gitignore`. Let `mkdocs gh-deploy` manage the `gh-pages` branch exclusively. Check: the existing git status shows `docs/site` appearing to exist — verify it is gitignored before the first deploy.

---

## Scaling Considerations

GitHub Pages is a static file host. No server-side scaling concerns apply to the docs site. The only concern is build time:

| Docs Size | Build Time | Notes |
|-----------|-----------|-------|
| Current (~30 pages) | < 30s | Negligible — privacy plugin asset inlining is the slow step |
| 200+ pages | 60-90s | Still fast for CI; worth caching pip dependencies |
| 1000+ pages | Consider versioning (mike plugin) | Out of scope for v14.2 |

GitHub Pages bandwidth: 100 GB/month soft limit. At the current docs size this is not a constraint.

---

## Sources

- [Publishing your site - Material for MkDocs](https://squidfunk.github.io/mkdocs-material/publishing-your-site/) — HIGH confidence (official workflow recommendation)
- [Built-in offline plugin - Material for MkDocs](https://squidfunk.github.io/mkdocs-material/plugins/offline/) — HIGH confidence (offline plugin behaviour with `use_directory_urls`)
- [Configuration - MkDocs](https://www.mkdocs.org/user-guide/configuration/) — HIGH confidence (`site_url`, `use_directory_urls` semantics)
- [Deploying Your Docs - MkDocs](https://www.mkdocs.org/user-guide/deploying-your-docs/) — HIGH confidence (`mkdocs gh-deploy` mechanics)
- Direct codebase inspection: `docs/mkdocs.yml`, `docs/requirements.txt`, `docs/Dockerfile`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `docs/docs/api-reference/openapi.json` status via `git ls-files` — HIGH confidence

---

*Architecture research for: GitHub Pages deployment of MkDocs docs site (v14.2)*
*Researched: 2026-03-26*
