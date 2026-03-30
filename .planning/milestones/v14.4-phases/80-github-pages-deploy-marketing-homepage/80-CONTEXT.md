# Phase 80: GitHub Pages Deploy + Marketing Homepage - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Update `docs-deploy.yml` to deploy MkDocs output into the `/docs/` subdirectory of the `gh-pages` branch (not the root), then add a new `homepage-deploy.yml` that deploys a static marketing page to the root. Both workflows write to `gh-pages` independently — neither may overwrite the other's territory. A visitor to `axiom-laboratories.github.io/axiom/` sees the marketing homepage; a visitor to `axiom-laboratories.github.io/axiom/docs/` sees the MkDocs site.

</domain>

<decisions>
## Implementation Decisions

### Docs deploy mechanism
- Replace `mkdocs gh-deploy --force` in `docs-deploy.yml` with a two-step: `mkdocs build` (outputs to `docs/site/`) then `ghp-import -n -p -f -d site --dest-dir docs`
- `ghp-import --dest-dir docs` only writes to `docs/` on the `gh-pages` branch — root files are untouched
- `-n` flag writes `.nojekyll` automatically (required for MkDocs asset dirs like `_static`)
- `ghp-import` is already installed transitively by mkdocs-material — no new dependency needed

### mkdocs.yml site_url update
- Change `site_url` from `https://axiom-laboratories.github.io/axiom/` to `https://axiom-laboratories.github.io/axiom/docs/`
- Audit docs source files for hardcoded `/axiom/` absolute links before changing — grep for `axiom-laboratories.github.io/axiom/` and `site_url` refs in markdown and mkdocs.yml

### Homepage deploy mechanism
- New `homepage-deploy.yml` workflow: checks out the `gh-pages` branch, copies `homepage/index.html` and `homepage/style.css` into the root, creates `.nojekyll` if absent, commits and pushes
- No marketplace actions — plain git operations only
- homepage-deploy never writes to `docs/` — fully scoped to root files

### Coexistence guard
- `ghp-import --dest-dir docs` is the docs guard: only touches `docs/` subtree, leaves root alone
- Homepage deploy is the homepage guard: only copies specific named files into root, never touches `docs/`
- `.nojekyll` is maintained by homepage-deploy (creates if absent) — docs-deploy also sets it via ghp-import `-n` flag, so it's doubly covered

### Homepage content
- **Sections (in order):** Hero → Security positioning → CE vs EE comparison → Quick install snippet
- **Hero tagline:** "Distributed job execution you can trust" (security-first angle)
- **Security section:** Brief prose on mTLS node auth + Ed25519 job signing — what makes Axiom trustworthy
- **CE/EE comparison:** Table or two-column layout — free vs enterprise features
- **Quick install snippet:** `docker compose -f compose.cold-start.yaml up -d` snippet with a brief context line
- **CTA on hero:** Button linking to `./docs/` (the MkDocs site)

### Homepage visual style
- Dark theme matching MkDocs Material slate (dark background, indigo accent)
- Consistent brand across homepage and docs
- File structure: `homepage/index.html` + `homepage/style.css` (separate files, not inline)

### Workflow trigger scoping
- `docs-deploy.yml`: triggers on `docs/**` and `.github/workflows/docs-deploy.yml` (existing paths — no change)
- `homepage-deploy.yml`: triggers on `homepage/**` and `.github/workflows/homepage-deploy.yml`
- Homepage source lives in `homepage/` directory at repo root

### Claude's Discretion
- Exact hero copy beyond the tagline direction
- CSS design details (spacing, font choices, card/section layout)
- Whether the CE/EE comparison is a table or card grid
- Exact content of the security positioning section prose

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/docs-deploy.yml`: existing workflow to update — replace deploy step only, keep checkout/python/cache steps
- `docs/mkdocs.yml`: has `site_url: https://axiom-laboratories.github.io/axiom/` — update to `/axiom/docs/`
- `docs/requirements.txt`: already includes mkdocs-material (which pulls in ghp-import transitively)

### Established Patterns
- Existing `docs-deploy.yml` uses `actions/checkout@v4`, `actions/setup-python@v5`, `actions/cache@v4` — homepage-deploy should use same action versions for consistency
- MkDocs build runs from `working-directory: docs` — keep this pattern

### Integration Points
- `gh-pages` branch: both workflows write here independently — docs-deploy to `docs/` subtree, homepage-deploy to root
- `mkdocs.yml` `site_url` change may affect the MkDocs sitemap and canonical `<link>` tags — no other known downstream consumers

</code_context>

<specifics>
## Specific Ideas

- STATE.md blocker note: verify `ghp-import --dest-dir` flag availability with `ghp-import --help` before relying on it — fallback is `peaceiris/actions-gh-pages@v4` with `destination_dir: docs` + `keep_files: true`
- STATE.md blocker note: audit hardcoded absolute doc links in README, dashboard sidebar, and other files before changing `site_url`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 80-github-pages-deploy-marketing-homepage*
*Context gathered: 2026-03-27*
