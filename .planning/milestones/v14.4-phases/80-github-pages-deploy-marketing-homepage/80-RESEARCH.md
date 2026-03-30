# Phase 80: GitHub Pages Deploy + Marketing Homepage - Research

**Researched:** 2026-03-27
**Domain:** GitHub Actions CI/CD, ghp-import, static marketing HTML, GitHub Pages branch management
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Docs deploy mechanism**
- Replace `mkdocs gh-deploy --force` in `docs-deploy.yml` with a two-step: `mkdocs build` then `ghp-import -n -p -f -x docs` (using the correct `-x` prefix flag — see Critical Finding below)
- `ghp-import -x docs` only deletes and rewrites the `docs/` subtree on the `gh-pages` branch — root files are untouched
- `-n` flag writes `.nojekyll` inside `docs/` automatically
- `ghp-import` is already installed transitively by mkdocs-material — no new dependency needed

**mkdocs.yml site_url update**
- Change `site_url` from `https://axiom-laboratories.github.io/axiom/` to `https://axiom-laboratories.github.io/axiom/docs/`
- Audit docs source files for hardcoded absolute links before changing

**Homepage deploy mechanism**
- New `homepage-deploy.yml` workflow: checks out the `gh-pages` branch, copies `homepage/index.html` and `homepage/style.css` into the root, creates `.nojekyll` if absent, commits and pushes
- No marketplace actions — plain git operations only
- homepage-deploy never writes to `docs/` — scoped to root files only

**Coexistence guard**
- `ghp-import -x docs` guards docs: deletes only `docs/` subtree, leaves root alone
- Homepage deploy guards homepage: only copies specific named files into root, never touches `docs/`

**Homepage content sections (in order):** Hero → Security positioning → CE vs EE comparison → Quick install snippet
- Hero tagline: "Distributed job execution you can trust" (security-first angle)
- Security section: mTLS node auth + Ed25519 job signing
- CE/EE comparison: Table or two-column layout — free vs enterprise features
- Quick install snippet: `docker compose -f compose.cold-start.yaml up -d`
- CTA on hero: Button linking to `./docs/`

**Homepage visual style**
- Dark theme matching MkDocs Material slate (dark background, crimson accent matching dashboard `hsl(346.8, 77.2%, 49.8%)`)
- Font: Fira Sans (body) / Fira Code (mono) — matching docs
- File structure: `homepage/index.html` + `homepage/style.css` (separate files, not inline)

**Workflow trigger scoping**
- `docs-deploy.yml`: triggers on `docs/**` and `.github/workflows/docs-deploy.yml`
- `homepage-deploy.yml`: triggers on `homepage/**` and `.github/workflows/homepage-deploy.yml`
- Homepage source lives in `homepage/` directory at repo root

### Claude's Discretion
- Exact hero copy beyond the tagline direction
- CSS design details (spacing, font choices, card/section layout)
- Whether the CE/EE comparison is a table or card grid
- Exact content of the security positioning section prose

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MKTG-01 | `docs-deploy.yml` deploys MkDocs output to `/docs/` subdirectory so the repo root is available for the homepage | Confirmed via `ghp-import -x docs` prefix flag: deletes only `docs/` subtree, preserves root. `ghp-import 2.1.0` is installed transitively by mkdocs-material. |
| MKTG-02 | Marketing homepage (`index.html`) deployed to root of GitHub Pages at `axiom-laboratories.github.io/axiom/` | Confirmed via plain git checkout + copy approach on `gh-pages` branch. No marketplace action required. |
</phase_requirements>

---

## Summary

Phase 80 requires two independent GitHub Actions workflows writing to different subdirectories of the `gh-pages` branch. The docs workflow (`docs-deploy.yml`) must be updated to deploy MkDocs output into the `docs/` subtree only, using `ghp-import`'s prefix flag to leave the root untouched. A new `homepage-deploy.yml` writes static marketing HTML to the branch root without touching `docs/`.

The critical implementation detail is that `ghp-import`'s flag for subdirectory deployment is `-x`/`--prefix`, NOT `--dest-dir` as referenced in CONTEXT.md. The installed version (2.1.0, installed transitively by mkdocs-material on the CI runner) uses `-x docs` to: (1) delete only the `docs/` tree in the prior commit, (2) write all new files under `docs/`, and (3) preserve all other root-level files. This is verified by inspecting the `ghp_import` source: with a prefix, `start_commit()` emits `D docs` (delete subtree only) rather than `deleteall`.

The `gh-pages` branch currently has MkDocs output at root (deployed by `mkdocs gh-deploy --force`). After the first `ghp-import -x docs` run, MkDocs output moves to `docs/` and the root becomes available for the homepage. The homepage workflow then safely writes `index.html` and `style.css` into that root.

**Primary recommendation:** Use `ghp-import -n -p -f -x docs site` for docs deployment and plain git operations (checkout gh-pages, copy files, commit+push) for homepage deployment. Both workflows are independent and safe to run in any order.

---

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| ghp-import | 2.1.0 (transitive via mkdocs-material) | Push a local directory to a git branch with optional prefix | Already present in CI runner; `-x` flag provides clean subtree isolation |
| actions/checkout@v4 | v4 | Checkout repo in CI | Project standard — used in existing `docs-deploy.yml` |
| actions/setup-python@v5 | v5 | Python runtime for MkDocs build | Project standard |
| actions/cache@v4 | v4 | Cache pip packages | Project standard |
| mkdocs-material | 9.7.5 | MkDocs theme (builds docs site) | Locked in `docs/requirements.txt` |

### Supporting

| Tool | Purpose | When to Use |
|---|---|---|
| `peaceiris/actions-gh-pages@v4` | Marketplace action for GitHub Pages deployment with `destination_dir` and `keep_files` options | Fallback ONLY if `ghp-import -x` behaves unexpectedly in CI — not needed given source verification |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| `ghp-import -x docs` | `peaceiris/actions-gh-pages@v4` with `destination_dir: docs` + `keep_files: true` | Marketplace action adds external dependency and requires PAT or GITHUB_TOKEN with write perms; ghp-import is already present |
| Plain git in homepage workflow | Custom `actions/deploy-pages` | Plain git is simpler and explicit; no action pinning risk |

**Installation:** No new dependencies needed. `ghp-import` is transitively installed via `pip install -r docs/requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
.github/workflows/
├── docs-deploy.yml          # Updated: mkdocs build + ghp-import -x docs
└── homepage-deploy.yml      # New: checkout gh-pages, copy homepage/, push

homepage/
├── index.html               # Marketing page (standalone, no build step)
└── style.css                # Extracted styles

docs/
└── mkdocs.yml               # site_url updated to .../axiom/docs/
```

### gh-pages Branch Layout (after phase)

```
gh-pages branch root/
├── .nojekyll                # Created by homepage-deploy (and by ghp-import -n inside docs/)
├── index.html               # Marketing homepage
├── style.css                # Homepage styles
└── docs/
    ├── .nojekyll            # Created by ghp-import -n flag
    ├── index.html           # MkDocs home
    ├── 404.html
    ├── assets/
    ├── getting-started/
    └── ... (all MkDocs output)
```

### Pattern 1: ghp-import Prefix Deployment

**What:** Use `ghp-import -n -p -f -x docs site` to push the `site/` directory contents into the `docs/` subtree of the `gh-pages` branch.

**When to use:** Any time MkDocs output must coexist with other content on the same GitHub Pages branch.

**How it works (source-verified):** With `-x docs`, `start_commit()` emits `D docs\n` (deletes only the `docs/` tree from the prior commit), then writes all files under `docs/` prefix. Without `-x`, it emits `deleteall\n`, wiping the entire branch. Root files survive because only `docs/` is deleted.

**Example:**
```yaml
# Source: ghp-import source inspection (ghp_import/__init__.py line 138-141)
- name: Build docs
  working-directory: docs
  run: mkdocs build

- name: Deploy docs to gh-pages/docs/
  working-directory: docs
  run: ghp-import -n -p -f -x docs site
```

**Flag reference:**
- `-n` — write `.nojekyll` (inside `docs/` when used with `-x docs`)
- `-p` — push to origin after committing
- `-f` — force push (equivalent to `--force`)
- `-x docs` — prefix: delete only `docs/` tree, write all files under `docs/`
- `site` — positional: local directory to push

### Pattern 2: Homepage Deploy via Plain Git

**What:** Checkout `gh-pages` branch in CI, copy static files into root, commit and push.

**When to use:** Deploying a small number of named files (not a whole directory tree) to the branch root.

**Example:**
```yaml
- name: Checkout gh-pages
  run: |
    git fetch origin gh-pages
    git checkout gh-pages

- name: Copy homepage files
  run: |
    cp homepage/index.html index.html
    cp homepage/style.css style.css
    touch .nojekyll

- name: Commit and push
  run: |
    git add index.html style.css .nojekyll
    git diff --cached --quiet || git commit -m "Deploy homepage from ${{ github.sha }}"
    git push origin gh-pages
```

**Key detail:** `git diff --cached --quiet || git commit` prevents a no-op commit when files haven't changed (avoids empty commit errors).

### Pattern 3: Workflow Trigger Scoping

**What:** Use `paths:` filter so each workflow only fires when its source files change.

**Example:**
```yaml
# docs-deploy.yml
on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - '.github/workflows/docs-deploy.yml'

# homepage-deploy.yml
on:
  push:
    branches: [main]
    paths:
      - 'homepage/**'
      - '.github/workflows/homepage-deploy.yml'
```

### Anti-Patterns to Avoid

- **Using `mkdocs gh-deploy --force` without `-x`:** This runs `deleteall` internally, wiping everything on `gh-pages` including any homepage at root.
- **Using `ghp-import` without `-x` prefix:** Same as above — `deleteall` destroys root content.
- **Writing to `docs/` in homepage-deploy:** Breaks isolation guarantee. Homepage workflow must only copy specific root files.
- **Hardcoding `site_url` in markdown source:** The only hardcoded URL is in `mkdocs.yml` itself; source markdown uses relative links. Changing `site_url` only affects sitemap and canonical `<link>` tags.
- **Empty commits in homepage-deploy:** Always guard commit with `git diff --cached --quiet ||` — GitHub Actions will error on empty commits.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Prefix-scoped branch write | Custom Python script to manipulate git-fast-import | `ghp-import -x docs` | ghp-import already implements the `D prefix\n` vs `deleteall\n` fast-import protocol correctly |
| Branch coexistence | Full branch checkout + rsync logic | Combination of `ghp-import -x` for docs and plain git copy for homepage | Each tool is scoped to its own files; neither can interfere with the other |

**Key insight:** The coexistence problem is solved entirely by `ghp-import`'s `-x` prefix flag. Do not implement custom git-fast-import logic.

---

## Common Pitfalls

### Pitfall 1: Wrong Flag Name for ghp-import Prefix

**What goes wrong:** CONTEXT.md references `--dest-dir docs` but this flag does not exist in ghp-import 2.1.0. Using it causes a `unrecognized arguments` error and the deploy step fails.

**Why it happens:** The flag is `-x`/`--prefix`. The `--dest-dir` name may come from `peaceiris/actions-gh-pages` which uses different option naming.

**How to avoid:** Use `ghp-import -n -p -f -x docs site`. Verified against installed version 2.1.0 on this machine and visible in source: `(('-x', '--prefix'), ...)`.

**Warning signs:** CI step exits non-zero with `error: unrecognized arguments: --dest-dir`

### Pitfall 2: Root .nojekyll Location

**What goes wrong:** MkDocs Material uses `_static`, `assets/`, and other underscore-prefixed dirs. GitHub Pages (Jekyll mode) ignores these by default. `.nojekyll` at the branch root disables Jekyll.

**Why it happens:** `ghp-import -n -x docs` writes `.nojekyll` inside `docs/`, not at the branch root. The homepage deploy step must also create `.nojekyll` at root.

**How to avoid:** Homepage workflow does `touch .nojekyll && git add .nojekyll` — this ensures the root `.nojekyll` is always present. Since `ghp-import -x docs` preserves root files, once homepage-deploy runs first (or at least once), `.nojekyll` is persistent.

**Warning signs:** Docs assets (JS, CSS in `docs/assets/`) return 404 after first docs-only deploy without a prior homepage deploy.

**Mitigation:** docs-deploy can also `touch .nojekyll` at root and commit it to gh-pages before the ghp-import step, or homepage-deploy should run at least once before relying on docs-only deploys. Alternatively, use a bootstrap step in docs-deploy that ensures root `.nojekyll` exists.

### Pitfall 3: Existing gh-pages Root Content Collision

**What goes wrong:** The current `gh-pages` branch has MkDocs output at root (including `index.html`, `404.html`, `sitemap.xml`, etc.). After switching to `ghp-import -x docs`, the first deploy will delete and recreate `docs/` but leave the old `index.html` (MkDocs) at root. Until homepage-deploy runs, visitors see the old MkDocs index instead of the marketing page.

**Why it happens:** `ghp-import -x docs` only touches the `docs/` tree; it leaves existing root files untouched.

**How to avoid:** Ensure homepage-deploy runs at or before the first docs-deploy. Either trigger homepage-deploy manually first, or add a root cleanup step to docs-deploy that removes old MkDocs root artifacts on first migration. The cleanest approach: run homepage-deploy first (manually trigger on new workflow creation).

**Warning signs:** `axiom-laboratories.github.io/axiom/` shows old MkDocs index after docs-deploy but before homepage-deploy.

### Pitfall 4: site_url Canonical Link Impact

**What goes wrong:** Changing `site_url` from `/axiom/` to `/axiom/docs/` updates the `<link rel="canonical">` and sitemap URLs in all MkDocs-generated pages. Old bookmarks to `axiom-laboratories.github.io/axiom/getting-started/` will become 404s (content moves to `/axiom/docs/getting-started/`).

**Why it happens:** `site_url` in mkdocs.yml drives canonical URL generation. MkDocs uses it for all internal absolute URL construction.

**How to avoid:** This is expected and intentional — the URL schema is changing. No 301 redirect mechanism exists on GitHub Pages without a separate redirect page. Add a root-level 404.html or redirect snippet if needed (out of scope for this phase). The only non-generated files that reference the old URL are in `docs/mkdocs.yml` and `.planning/` files (not public-facing).

**Warning signs:** None during phase — this is an intended behaviour change.

### Pitfall 5: Concurrent Workflow Race

**What goes wrong:** If both workflows trigger simultaneously (e.g., a commit touches both `docs/**` and `homepage/**`), they both checkout `gh-pages` and push — one will fail with a non-fast-forward push error.

**Why it happens:** Two independent CI jobs writing to the same branch without coordination.

**How to avoid:** The `paths:` scoping prevents both triggering on the same commit in normal usage. For safety, the homepage-deploy step should use `git pull --rebase origin gh-pages` before pushing. This is low risk given separate trigger paths.

**Warning signs:** CI job for one workflow fails with `rejected: non-fast-forward`.

---

## Code Examples

### Updated docs-deploy.yml (final deploy step only)

```yaml
# Source: ghp-import 2.1.0 flag reference (verified locally)
- name: Build docs
  working-directory: docs
  run: mkdocs build

- name: Deploy docs to gh-pages/docs/
  working-directory: docs
  run: ghp-import -n -p -f -x docs site
```

### homepage-deploy.yml (full workflow)

```yaml
# Source: GitHub Actions docs + project pattern (actions/checkout@v4)
name: homepage-deploy

on:
  push:
    branches: [main]
    paths:
      - 'homepage/**'
      - '.github/workflows/homepage-deploy.yml'

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

      - name: Deploy homepage to gh-pages root
        run: |
          git fetch origin gh-pages
          git checkout gh-pages
          cp homepage/index.html index.html
          cp homepage/style.css style.css
          touch .nojekyll
          git add index.html style.css .nojekyll
          git diff --cached --quiet || git commit -m "Deploy homepage from ${{ github.sha }}"
          git push origin gh-pages
```

### Homepage Brand Colours (from docs/docs/stylesheets/extra.css)

```css
/* Match existing Axiom brand identity */
:root {
  /* Crimson accent — matches dashboard and MkDocs theme */
  --axiom-primary: hsl(346.8, 77.2%, 49.8%);
  --axiom-primary-light: hsl(346.8, 77.2%, 65%);

  /* Slate dark background — matches Material slate scheme */
  --axiom-bg: #0d1117;
  --axiom-surface: #161b22;
  --axiom-border: #30363d;
  --axiom-text: #e6edf3;
  --axiom-text-muted: #8b949e;

  /* Fonts — same as docs */
  font-family: 'Fira Sans', sans-serif;
}
code, pre {
  font-family: 'Fira Code', monospace;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `mkdocs gh-deploy --force` | `mkdocs build` + `ghp-import -x docs site` | Phase 80 | Docs now live at `/axiom/docs/` instead of `/axiom/`; root available for marketing page |
| MkDocs at `gh-pages` root | Marketing page at root, MkDocs at `docs/` subtree | Phase 80 | `axiom-laboratories.github.io/axiom/` is now the marketing homepage |

**Deprecated/outdated:**
- `mkdocs gh-deploy --force`: replaced — it calls `ghp-import` internally without `-x`, which nukes the whole branch root.
- `site_url: https://axiom-laboratories.github.io/axiom/`: replaced with `https://axiom-laboratories.github.io/axiom/docs/`

---

## Open Questions

1. **Root .nojekyll bootstrap order**
   - What we know: `ghp-import -x docs` writes `.nojekyll` only inside `docs/`, not at root. Root `.nojekyll` is needed for GitHub Pages to serve `docs/assets/` correctly (no Jekyll filtering).
   - What's unclear: On the very first docs-deploy run (before any homepage-deploy), will `docs/assets/` be served correctly without a root `.nojekyll`?
   - Recommendation: Homepage-deploy should run first (manual trigger on workflow creation). Alternatively, docs-deploy can add a step to ensure root `.nojekyll` exists using a git-on-gh-pages approach, or accept that the first docs-only deploy may have asset issues until homepage-deploy runs.

2. **Concurrent deploy race condition**
   - What we know: Both workflows target the same `gh-pages` branch. If triggered simultaneously, one push will fail.
   - What's unclear: In practice, `docs/**` and `homepage/**` changes never land in the same commit in this project.
   - Recommendation: Add `git pull --rebase origin gh-pages` before the push in homepage-deploy as a defensive measure. Accept the race as low-probability given separate trigger paths.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None (CI-only validation — no local test runner applicable) |
| Config file | `.github/workflows/docs-deploy.yml`, `.github/workflows/homepage-deploy.yml` |
| Quick run command | `act push --workflows .github/workflows/docs-deploy.yml` (if `act` installed) |
| Full suite command | Push to `main` and verify GitHub Pages URLs respond correctly |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MKTG-01 | `axiom-laboratories.github.io/axiom/docs/` serves MkDocs output without touching root | smoke | `curl -sf https://axiom-laboratories.github.io/axiom/docs/ | grep -q "Axiom"` | ❌ Wave 0 |
| MKTG-01 | `axiom-laboratories.github.io/axiom/` root still serves homepage after docs deploy | smoke | `curl -sf https://axiom-laboratories.github.io/axiom/ | grep -q "Distributed job execution"` | ❌ Wave 0 |
| MKTG-02 | `axiom-laboratories.github.io/axiom/` serves marketing homepage | smoke | `curl -sf https://axiom-laboratories.github.io/axiom/ | grep -q "Distributed job execution"` | ❌ Wave 0 |
| MKTG-02 | Marketing page contains hero, security section, CE/EE comparison, install snippet | manual | Visual inspection via browser | N/A — manual only |

### Sampling Rate

- **Per task commit:** N/A — workflow validation requires a live push
- **Per wave merge:** Verify `gh-pages` branch tree structure with `git ls-tree --name-only origin/gh-pages` and `git ls-tree --name-only origin/gh-pages docs`
- **Phase gate:** Both curl smoke tests pass before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Smoke test script `mop_validation/scripts/test_pages_deploy.sh` — covers MKTG-01 and MKTG-02 (curl checks)
- [ ] `homepage/index.html` — does not exist yet (source file for MKTG-02)
- [ ] `homepage/style.css` — does not exist yet (source file for MKTG-02)

---

## Sources

### Primary (HIGH confidence)

- `ghp_import` source inspection (installed version 2.1.0) — `-x`/`--prefix` flag behaviour, `start_commit()` `D prefix` vs `deleteall` logic
- `git ls-tree origin/gh-pages` — current branch root structure confirmed
- `.github/workflows/docs-deploy.yml` (local file) — existing workflow structure, action versions
- `docs/mkdocs.yml` (local file) — current `site_url`, theme palette
- `docs/docs/stylesheets/extra.css` (local file) — brand colour palette and font stack
- `docs/requirements.txt` (local file) — `mkdocs-material==9.7.5` (confirms ghp-import is transitive)

### Secondary (MEDIUM confidence)

- ghp-import PyPI page (v2.1.0) — flag listing cross-references local source inspection
- GitHub Actions documentation patterns — `paths:` trigger scoping, `permissions: contents: write`

### Tertiary (LOW confidence)

- None required — all critical claims verified via source inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ghp-import source inspected locally; action versions match existing workflow
- Architecture: HIGH — current gh-pages branch state confirmed via `git ls-tree`; ghp-import logic verified in source
- Pitfalls: HIGH — critical flag name mismatch (`-x` vs `--dest-dir`) verified against installed source; other pitfalls derived from documented ghp-import behaviour

**Research date:** 2026-03-27
**Valid until:** 2026-06-27 (ghp-import 2.1.0 stable; GitHub Actions versions stable)
