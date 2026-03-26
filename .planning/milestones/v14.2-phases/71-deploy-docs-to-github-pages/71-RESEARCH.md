# Phase 71: Deploy Docs to GitHub Pages - Research

**Researched:** 2026-03-26
**Domain:** MkDocs Material + GitHub Actions + GitHub Pages
**Confidence:** HIGH

## Summary

This phase wires the existing `docs/` MkDocs Material site (already building clean under `mkdocs build --strict`) to GitHub Pages via a new `docs-deploy.yml` workflow. The approach is `mkdocs gh-deploy --force` rather than the `actions/deploy-pages` artifact chain — this is the official Material for MkDocs recommendation and requires only `permissions: contents: write`. No new libraries are needed; the stack is already correct at `mkdocs-material==9.7.5`.

The two meaningful changes to `mkdocs.yml` are: (1) updating `site_url` to the GH Pages URL, and (2) making the `offline` plugin conditional via `!ENV [OFFLINE_BUILD, false]`. The Dockerfile already sets this env var during its build step, so air-gap container behaviour is fully preserved. The privacy plugin cache (`docs/.cache/`) is already partially tracked in git (34 files), which means the GH Actions build will not need to download fonts from CDNs on every run.

The only housekeeping prerequisites are adding `docs/site/` to `.gitignore` (166 files currently tracked there — they must be untracked before the workflow runs) and adding a `.nojekyll` marker file to `docs/docs/` so GitHub does not mangle MkDocs-generated filenames beginning with underscores.

**Primary recommendation:** Use `mkdocs gh-deploy --force` from `working-directory: docs` with `--config-file mkdocs.yml` to handle the subdirectory layout. Enable GH Pages on the `gh-pages` branch in the repo settings after the first deploy.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEPLOY-01 | Docs site auto-deploys to GH Pages on every push to `main` via `docs-deploy.yml` | New workflow triggers `on: push: branches: [main]`, calls `mkdocs gh-deploy --force` |
| DEPLOY-02 | Deploy workflow is standalone, separate from `ci.yml` | New `.github/workflows/docs-deploy.yml` file; `ci.yml` keeps its `docs:` job as a lint-only check |
| CONFIG-01 | `site_url` updated to `https://axiom-laboratories.github.io/axiom/` | Verified GitHub repo is `axiom-laboratories/axiom`; Pages URL is `https://axiom-laboratories.github.io/axiom/` |
| CONFIG-02 | `offline` plugin made conditional via `!ENV [OFFLINE_BUILD, false]` | Confirmed syntax: `enabled: !ENV [OFFLINE_BUILD, false]` — documented in MkDocs Material |
| CONFIG-03 | Dockerfile sets `OFFLINE_BUILD=true` in `mkdocs build` step | Already does `RUN mkdocs build --strict`; needs `ENV OFFLINE_BUILD=true` or inline export |
| HOUSE-01 | `docs/site/` added to `.gitignore` and removed from git tracking | 166 tracked files need `git rm -r --cached docs/site/`; `.gitignore` entry missing today |
| HOUSE-02 | `.nojekyll` added to `docs/docs/` | File does not exist yet; prevents Jekyll from processing MkDocs `_` prefixed assets |
| MAINT-01 | Local script to regenerate `openapi.json` | `puppeteer/scripts/export_openapi.py` already exists; need a thin shell wrapper `docs/scripts/regen_openapi.sh` with the correct env and output path |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs-material | 9.7.5 (pinned in `docs/requirements.txt`) | Site generator + theme | Already in use; `gh-deploy` is the official deploy command |
| actions/checkout | v4 | Checkout repo in CI | Standard; needs `fetch-depth: 0` for git history used by gh-deploy |
| actions/setup-python | v5 | Python for mkdocs | Already used in `ci.yml` |
| actions/cache | v4 | Cache pip + privacy plugin downloads | Official MkDocs Material recommendation; cache key rotates weekly |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mkdocs-swagger-ui-tag | 0.8.0 | Render OpenAPI spec in docs | Already in `requirements.txt`; no changes needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mkdocs gh-deploy --force` | `actions/deploy-pages` artifact chain | Artifact chain needs `pages: write` + `id-token: write` permissions + separate `configure-pages` action; more complex, no benefit here |
| Pre-committed `openapi.json` | CI-regenerated `openapi.json` | CI regeneration requires FastAPI app import in Actions — already done in Dockerfile but would need dependencies in deploy job; decided to keep pre-committed (per STATE.md decision) |

**Installation:** No new packages needed. Existing `docs/requirements.txt` is sufficient.

## Architecture Patterns

### Recommended Project Structure
```
.github/workflows/
├── ci.yml                    # existing — keeps docs build check
└── docs-deploy.yml           # NEW — deploys to gh-pages branch on push to main

docs/
├── mkdocs.yml                # MODIFY: site_url + offline plugin conditional
├── requirements.txt          # no change
├── Dockerfile                # MODIFY: add OFFLINE_BUILD=true to mkdocs build step
├── docs/
│   ├── .nojekyll             # NEW — prevents Jekyll interference
│   └── ...                   # existing source files
├── .cache/                   # privacy plugin cache (already partially tracked)
└── site/                     # BUILD OUTPUT — add to .gitignore, untrack
```

### Pattern 1: mkdocs gh-deploy with subdirectory config

**What:** Run `mkdocs gh-deploy --force` pointing at `docs/mkdocs.yml` from the repo root, or use `working-directory: docs` in the workflow step.

**When to use:** When `mkdocs.yml` lives in a subdirectory (`docs/`) rather than repo root.

**Example:**
```yaml
# Source: https://squidfunk.github.io/mkdocs-material/publishing-your-site/
- name: Deploy to GitHub Pages
  working-directory: docs
  run: mkdocs gh-deploy --force
```

### Pattern 2: Conditional plugin via `!ENV`

**What:** Use MkDocs YAML env variable syntax to enable/disable a plugin based on an environment variable.

**When to use:** Any plugin that must behave differently between local/Docker offline builds and GitHub Pages online builds.

**Example:**
```yaml
# Source: https://squidfunk.github.io/mkdocs-material/plugins/offline/
plugins:
  - search
  - privacy
  - offline:
      enabled: !ENV [OFFLINE_BUILD, false]
  - swagger-ui-tag
```

### Pattern 3: Privacy plugin cache in CI

**What:** Commit `docs/.cache/plugin/privacy/` to the repository so CI never needs to fetch external fonts/assets.

**When to use:** When the privacy plugin downloads external assets that you want to version-control for reproducible builds without network access.

**Key insight:** The cache is already partially committed (34 files tracked). The workflow should also use `actions/cache` keyed on `~/.cache` for any uncached assets. The `OFFLINE_BUILD` flag only disables the `offline` plugin, not `privacy` — so the privacy plugin still runs on GH Pages and will use the committed cache files.

### Pattern 4: workflow-level permissions for gh-deploy

**What:** Set `permissions: contents: write` at workflow level so `mkdocs gh-deploy` can push to `gh-pages` branch.

**When to use:** Any workflow calling `mkdocs gh-deploy`.

```yaml
permissions:
  contents: write
```

### Anti-Patterns to Avoid

- **Running `mkdocs gh-deploy` without `fetch-depth: 0`:** gh-deploy uses git history for revision dates; shallow clone (default) causes incorrect "last updated" dates or warnings.
- **Deploying without first configuring GH Pages source in repo settings:** The `gh-pages` branch is created by gh-deploy but GH Pages must be enabled via Settings > Pages to serve it.
- **Leaving `docs/site/` tracked in git:** MkDocs `--strict` won't fail on this, but it bloats every commit and conflicts with the gh-deploy branch strategy.
- **Using plain `offline:` without `enabled:` key:** Disables the plugin globally; use `enabled: !ENV [OFFLINE_BUILD, false]` instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deploy to gh-pages branch | Custom git push script | `mkdocs gh-deploy --force` | Handles branch creation, commit message, force push, and working-directory correctly |
| Conditional plugin disable | Jinja templates or CI `sed` | `!ENV [OFFLINE_BUILD, false]` in mkdocs.yml | Native MkDocs YAML feature; avoids maintaining two mkdocs.yml files |
| External asset bundling | Manual font download scripts | MkDocs privacy plugin (already in use) | Already downloads and caches; committing `.cache/` gives reproducibility |

## Common Pitfalls

### Pitfall 1: `docs/site/` still tracked when workflow runs
**What goes wrong:** gh-deploy builds site into `docs/site/`, git detects conflicts with tracked files, or the branch contains stale build artifacts.
**Why it happens:** `docs/site/` is currently tracked (166 files). `.gitignore` does not cover it yet.
**How to avoid:** Before merging the workflow, run `git rm -r --cached docs/site/` and add `docs/site/` to `.gitignore`. Commit this cleanup first.
**Warning signs:** `git status` after a local build shows `docs/site/` as modified tracked files.

### Pitfall 2: Jekyll processing MkDocs `_` prefixed assets
**What goes wrong:** GitHub Pages Jekyll processor ignores directories/files beginning with `_` (e.g., `_static/`). MkDocs Material generates `_` prefixed assets.
**Why it happens:** GH Pages enables Jekyll by default unless told otherwise.
**How to avoid:** Add an empty `.nojekyll` file to `docs/docs/` (the MkDocs source docs dir). `mkdocs gh-deploy` will include it in the deployed site.
**Warning signs:** CSS/JS assets 404 after deploy; page loads but is unstyled.

### Pitfall 3: `offline` plugin disabling directory URLs
**What goes wrong:** When `offline` plugin is active, it forces `use_directory_urls: false`, producing `page.html` URLs instead of `/page/`. On GitHub Pages this breaks navigation.
**Why it happens:** The offline plugin modifies URL generation to support file:// browsing.
**How to avoid:** Making `offline` conditional via `!ENV [OFFLINE_BUILD, false]` ensures it only activates in the Docker/container build where file:// access is intended.
**Warning signs:** `mkdocs build --strict` locally (without `OFFLINE_BUILD=true`) produces `page.html` paths.

### Pitfall 4: Privacy plugin fetching at CI time despite cache
**What goes wrong:** Build fails or is slow because privacy plugin tries to re-download fonts.
**Why it happens:** `docs/.cache/` is checked in but `~/.cache` (MkDocs Material's additional cache path) is not.
**How to avoid:** Add `actions/cache` step keyed on `~/.cache` in the workflow. The privacy plugin cache in `docs/.cache/` is committed so it will always be available after checkout.
**Warning signs:** GH Actions build step for privacy plugin shows CDN download requests.

### Pitfall 5: `site_url` trailing slash mismatch
**What goes wrong:** Internal links or canonical URLs broken after deploy.
**Why it happens:** `site_url` must end with `/` for MkDocs Material to generate correct relative URLs for a subpath deploy (`/axiom/`).
**How to avoid:** Use `https://axiom-laboratories.github.io/axiom/` (with trailing slash).
**Warning signs:** `mkdocs build --strict` produces warnings about absolute URL path resolution.

### Pitfall 6: openapi.json has 0 paths (pre-committed stale copy)
**What goes wrong:** API reference page renders with empty spec.
**Why it happens:** `docs/docs/api-reference/openapi.json` currently shows 0 paths — it is a placeholder. The Dockerfile regenerates it at build time, but the pre-committed version is empty.
**How to avoid:** The MAINT-01 script (`docs/scripts/regen_openapi.sh`) must be run and the output committed before Phase 71 goes live. This is a one-time local action, not CI automation.
**Warning signs:** API reference page in docs shows no endpoints.

## Code Examples

### docs-deploy.yml (complete workflow)
```yaml
# Source: https://squidfunk.github.io/mkdocs-material/publishing-your-site/
name: docs-deploy

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - '.github/workflows/docs-deploy.yml'

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Configure Git Credentials
        run: |
          git config user.name github-actions[bot]
          git config user.email 41898282+github-actions[bot]@users.noreply.github.com

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: docs/requirements.txt

      - run: echo "cache_id=$(date --utc '+%V')" >> $GITHUB_ENV

      - uses: actions/cache@v4
        with:
          key: mkdocs-material-${{ env.cache_id }}
          path: ~/.cache
          restore-keys: |
            mkdocs-material-

      - name: Install docs dependencies
        run: pip install -r docs/requirements.txt

      - name: Deploy to GitHub Pages
        working-directory: docs
        run: mkdocs gh-deploy --force
```

### mkdocs.yml offline plugin change
```yaml
# Before:
plugins:
  - search
  - privacy
  - offline
  - swagger-ui-tag

# After (CONFIG-02):
plugins:
  - search
  - privacy
  - offline:
      enabled: !ENV [OFFLINE_BUILD, false]
  - swagger-ui-tag
```

### Dockerfile mkdocs build step change (CONFIG-03)
```dockerfile
# Before:
RUN mkdocs build --strict

# After:
RUN OFFLINE_BUILD=true mkdocs build --strict
```

### .gitignore addition (HOUSE-01)
```
# MkDocs generated site (build output — not tracked)
docs/site/
```

### Remove tracked docs/site/ files (HOUSE-01 — run once locally)
```bash
git rm -r --cached docs/site/
git commit -m "chore: untrack docs/site/ build output"
```

### regen_openapi.sh (MAINT-01)
```bash
#!/usr/bin/env bash
# Regenerates docs/docs/api-reference/openapi.json from the live FastAPI app.
# Run from repo root whenever the API schema changes, then commit the result.
set -euo pipefail
DATABASE_URL=sqlite+aiosqlite:///./dummy.db \
ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
API_KEY=dummy-build-key \
PYTHONPATH=puppeteer \
  python puppeteer/scripts/export_openapi.py \
    docs/docs/api-reference/openapi.json
echo "Done. Review changes and commit: git add docs/docs/api-reference/openapi.json"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mhausenblas/mkdocs-deploy-gh-pages` Action | `mkdocs gh-deploy --force` directly | MkDocs 1.x+ | Fewer moving parts; official; no third-party action pin needed |
| `actions/deploy-pages` artifact chain | `mkdocs gh-deploy --force` | N/A — both valid | gh-deploy approach is simpler; needs only `contents: write` not `pages: write + id-token: write` |

**Deprecated/outdated:**
- `use_directory_urls: false` globally: was a workaround for offline; now handled by the `offline` plugin's internal override — only activates when the plugin is enabled.

## Open Questions

1. **GH Pages must be enabled manually after first deploy**
   - What we know: GitHub API confirms `has_pages: false` — Pages is not yet enabled for `axiom-laboratories/axiom`.
   - What's unclear: Whether the repo owner can enable it before the first `gh-pages` branch push, or must wait for gh-deploy to create the branch first.
   - Recommendation: Plan should note this as a one-time manual step: after the first successful workflow run creates the `gh-pages` branch, go to Settings > Pages > Source = `gh-pages` branch, `/ (root)`. Document this in the wave summary.

2. **`paths:` filter on the workflow trigger**
   - What we know: Adding `paths: ['docs/**']` avoids unnecessary deploys on backend-only changes.
   - What's unclear: Whether the planner wants this optimization or prefers simplicity (always deploy on push to main).
   - Recommendation: Include the `paths` filter — docs rarely change with backend commits and the optimisation is low-risk.

3. **`docs/.cache/` completeness for GH Actions**
   - What we know: 34 files tracked; these cover fonts.googleapis.com and fonts.gstatic.com assets.
   - What's unclear: Whether all assets the privacy plugin needs are in the committed cache or if new pages added in future could introduce new external assets.
   - Recommendation: The `actions/cache` step (keyed to `~/.cache`) handles this gracefully — on cache miss the plugin downloads and re-caches. Not a blocker.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend); no dedicated docs test framework |
| Config file | `puppeteer/pytest.ini` (backend only) |
| Quick run command | `cd docs && mkdocs build --strict` |
| Full suite command | `cd docs && mkdocs build --strict && cd ../puppeteer && pytest -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEPLOY-01 | Workflow file exists and has correct trigger | smoke | `test -f .github/workflows/docs-deploy.yml` | ❌ Wave 0 |
| DEPLOY-02 | `docs-deploy.yml` is a separate file from `ci.yml` | smoke | `test -f .github/workflows/docs-deploy.yml && test -f .github/workflows/ci.yml` | ❌ Wave 0 |
| CONFIG-01 | `site_url` in mkdocs.yml is correct GH Pages URL | unit | `grep 'axiom-laboratories.github.io/axiom/' docs/mkdocs.yml` | ❌ Wave 0 |
| CONFIG-02 | `offline` plugin uses `!ENV [OFFLINE_BUILD, false]` | unit | `grep 'OFFLINE_BUILD' docs/mkdocs.yml` | ❌ Wave 0 |
| CONFIG-03 | Dockerfile sets `OFFLINE_BUILD=true` | unit | `grep 'OFFLINE_BUILD=true' docs/Dockerfile` | ❌ Wave 0 |
| CONFIG-02+03 combined | `mkdocs build --strict` passes without `OFFLINE_BUILD` | integration | `cd docs && mkdocs build --strict` | ❌ Wave 0 (file changes needed first) |
| HOUSE-01 | `docs/site/` not tracked in git | smoke | `git ls-files docs/site/ \| wc -l` (expect 0) | ❌ Wave 0 |
| HOUSE-02 | `.nojekyll` exists in `docs/docs/` | smoke | `test -f docs/docs/.nojekyll` | ❌ Wave 0 |
| MAINT-01 | `regen_openapi.sh` script exists and is executable | smoke | `test -x docs/scripts/regen_openapi.sh` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **Per wave merge:** Full `mkdocs build --strict` + all smoke checks above
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `docs/scripts/regen_openapi.sh` — covers MAINT-01
- [ ] `docs/docs/.nojekyll` — covers HOUSE-02
- [ ] `.github/workflows/docs-deploy.yml` — covers DEPLOY-01, DEPLOY-02

*(All changes in this phase are new files or modifications, not test files — the "tests" are the smoke/grep checks above.)*

## Sources

### Primary (HIGH confidence)
- [Publishing your site — Material for MkDocs](https://squidfunk.github.io/mkdocs-material/publishing-your-site/) — exact workflow YAML, permissions, cache strategy
- [Built-in offline plugin — Material for MkDocs](https://squidfunk.github.io/mkdocs-material/plugins/offline/) — `!ENV [OFFLINE_BUILD, false]` syntax confirmed
- [Built-in privacy plugin — Material for MkDocs](https://squidfunk.github.io/mkdocs-material/plugins/privacy/) — cache behaviour at `.cache/plugin/privacy`
- GitHub API (`api.github.com/repos/axiom-laboratories/axiom`) — confirmed repo is public, `has_pages: false`

### Secondary (MEDIUM confidence)
- [Deploying Your Docs — MkDocs](https://www.mkdocs.org/user-guide/deploying-your-docs/) — `--config-file` flag for subdirectory layouts
- Codebase inspection: `docs/mkdocs.yml`, `docs/Dockerfile`, `docs/requirements.txt`, `.github/workflows/ci.yml`, `puppeteer/scripts/export_openapi.py` — all read directly

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against `docs/requirements.txt` and official Material docs
- Architecture: HIGH — based on direct codebase inspection and official MkDocs Material deployment guide
- Pitfalls: HIGH — most derived from direct inspection of current tracked state (`docs/site/` has 166 tracked files, `openapi.json` has 0 paths, `.nojekyll` absent, `site_url` points to old URL)

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable ecosystem — MkDocs Material releases infrequently)
