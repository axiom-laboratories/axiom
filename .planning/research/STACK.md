# Stack Research

**Domain:** Go-to-market polish — marketing homepage, licence state banner, install doc fixes, signing UX
**Researched:** 2026-03-27
**Confidence:** HIGH

## Context: What Already Exists (Do Not Re-research)

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI backend | In production | `GET /api/licence` returns `status/tier/node_limit/expiry/grace_days/is_enterprise` |
| React/Vite dashboard | In production | Tailwind + shadcn/ui + lucide-react + `useLicence()` hook |
| `MainLayout.tsx` | In production | Already has a licence banner block (lines 211–223) for `grace`/`expired` states — renders inline below the header |
| `useLicence()` hook | In production | `@tanstack/react-query`, 5-min stale time, falls back to CE defaults on non-200 |
| MkDocs Material docs | In production | `docs-deploy.yml` runs `mkdocs gh-deploy --force` from `docs/` on `main` push; deploys to `gh-pages` branch root |
| `axiom-push` CLI | In production | `mop_sdk/cli.py` — argparse, OAuth device flow, `job push/create`; no `key` subcommand |
| `compose.cold-start.yaml` | In production | Includes `puppet-node-1` and `puppet-node-2` services with bundled test nodes |

---

## Feature 1: Marketing Homepage on GitHub Pages

### Problem

`mkdocs gh-deploy --force` deploys the built MkDocs site to the **root** of the `gh-pages` branch, overwriting everything. The current `site_url` in `mkdocs.yml` is `https://axiom-laboratories.github.io/axiom/`, which means MkDocs places its output at the branch root. There is no room for a separate root `index.html` landing page.

### Recommended Approach: Split Deploy via `ghp-import`

**Do not use `mkdocs gh-deploy` for the final push.** Instead, split the workflow into two steps:

1. `mkdocs build` — generates `docs/site/` as before
2. `ghp-import -n -p -f -r origin -b gh-pages -x docs docs/site/` — pushes MkDocs output into the `docs/` subdirectory of the `gh-pages` branch

Then a separate step copies the marketing `index.html` (from `homepage/` in the repo) to the branch root using the same `ghp-import` approach or direct git commit to `gh-pages`.

**Result:** `axiom-laboratories.github.io/axiom/` serves the marketing page; `axiom-laboratories.github.io/axiom/docs/` serves MkDocs.

Update `mkdocs.yml` `site_url` to `https://axiom-laboratories.github.io/axiom/docs/` to match the new location.

### ghp-import `-x` flag (MEDIUM confidence — verified via mkdocs/mkdocs issue #2534)

`ghp-import` is already installed as a transitive dependency of `mkdocs`. The `-x DEST_DIR` flag deploys output to a subdirectory of the target branch rather than the root. The `mkdocs gh-deploy` wrapper does not expose this flag, so call `ghp-import` directly.

```bash
# In docs-deploy.yml — replace the mkdocs gh-deploy step with:
mkdocs build --config-file docs/mkdocs.yml
ghp-import -n -p -f -b gh-pages -x docs docs/site/
```

`-n` adds `.nojekyll` (already needed). `-p` pushes. `-f` forces. `-x docs` places MkDocs output at `/docs/` on the branch.

### Marketing Homepage: Pure Static HTML + Tailwind CDN

**No build step required.** A single `homepage/index.html` using the Tailwind CDN play CDN is sufficient. This is a public marketing page, not an app — no bundler, no framework.

Why Tailwind CDN (not a full Vite build):
- Zero toolchain for a static HTML page
- GitHub Actions just copies the file — no `npm install`, no build artifacts
- The dashboard already uses Tailwind; visual language is consistent

The homepage deploy step in `docs-deploy.yml` is a single `ghp-import` or `git commit` that places `homepage/index.html` at the branch root as `index.html`.

**Recommended structure in repo:**

```
homepage/
  index.html       # marketing landing page (self-contained, Tailwind CDN)
  assets/
    logo.svg       # reuse docs/docs/assets/logo.svg
```

### Workflow Change Summary

Replace the `docs-deploy.yml` single-step `mkdocs gh-deploy --force` with:

```yaml
- name: Build MkDocs
  working-directory: docs
  run: mkdocs build

- name: Deploy docs to /docs/ subfolder
  run: ghp-import -n -p -f -b gh-pages -x docs docs/site/

- name: Deploy homepage to root
  run: |
    # ghp-import preserves existing branch content when not using --force on root
    # Copy homepage/index.html to gh-pages root via a second ghp-import with no -x
    # Use a temp dir to avoid overwriting /docs/
    mkdir -p /tmp/homepage-deploy
    cp homepage/index.html /tmp/homepage-deploy/index.html
    cp -r homepage/assets /tmp/homepage-deploy/assets 2>/dev/null || true
    ghp-import -n -p -b gh-pages /tmp/homepage-deploy/
```

**Caution:** `ghp-import` by default replaces the entire branch. Use `-x` to scope to subdirectory. For the root landing page step, use a temp dir containing only the homepage files to avoid clobbering `/docs/`.

A cleaner alternative is the `peaceiris/actions-gh-pages` GitHub Action (v4), which supports `destination_dir` and `keep_files: true` — this eliminates the manual temp-dir dance.

### Recommended: `peaceiris/actions-gh-pages@v4`

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `peaceiris/actions-gh-pages` | v4 | Deploy to GitHub Pages with `destination_dir` | Supports deploying MkDocs to `/docs/` and homepage to root in separate steps with `keep_files: true` — no manual branch manipulation needed |

```yaml
- uses: peaceiris/actions-gh-pages@v4
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./docs/site
    destination_dir: docs
    keep_files: true

- uses: peaceiris/actions-gh-pages@v4
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./homepage
    keep_files: true
```

`keep_files: true` preserves files already on the branch from prior deploys. This is the critical flag that prevents the docs deploy from wiping the homepage and vice versa.

**Confidence:** HIGH — peaceiris/actions-gh-pages is the standard GH Pages action (100k+ stars, used in mkdocs-material's own CI docs).

---

## Feature 2: Dashboard Licence State Banner (GRACE/DEGRADED_CE)

### Current State

`MainLayout.tsx` lines 211–223 already contain a banner for `grace` and `expired` states. It is a non-dismissible inline `<div>` below the header. The banner already reads from `useLicence()` and renders amber (grace) or red (expired) text with an `AlertTriangle` icon.

**What is missing:**
- No dismiss capability (banner is always visible if licence is in grace/expired)
- No `DEGRADED_CE` state handling (the API returns `status: 'ce'` but this also covers the case where an EE licence has fully expired and fallen back; the banner currently only fires on `grace`/`expired`)
- The banner has no CTA link ("Renew" or "Contact us")

### Recommended Pattern: Dismissible Banner with Session State

The existing banner is already in the right location and the right structure. The change is:

1. Add a dismiss button (X icon) to the existing banner `<div>`
2. Store dismissed state in `sessionStorage` keyed to `axiom-licence-banner-dismissed-{status}` — this way the banner reappears if status changes (e.g. from grace to expired), but not on every page navigation within the same session
3. Do **not** use `localStorage` — operators need to see the warning again on next login
4. Add a `DEGRADED_CE` display: when `status === 'ce'` AND `isEnterprise` was previously true (i.e. EE features are now locked), show a red banner. The API already surfaces this via `status: 'ce'` after licence expiry.

**No new libraries needed.** The pattern uses:
- `useState` to track dismissed state (already imported in MainLayout)
- `sessionStorage` (browser stdlib) for persistence within the session
- Existing `AlertTriangle` from lucide-react (already imported)
- The existing Tailwind classes already in the banner

**Pattern:**

```tsx
const BANNER_KEY = `axiom-licence-banner-v1-${licence.status}`;
const [dismissed, setDismissed] = useState(
  () => sessionStorage.getItem(BANNER_KEY) === '1'
);

const handleDismiss = () => {
  sessionStorage.setItem(BANNER_KEY, '1');
  setDismissed(true);
};
```

The key includes `licence.status` so the banner re-shows if the status changes between sessions (e.g. grace→expired after 14 days). The `v1` prefix allows forced re-show after a code change if needed.

### No New shadcn Components Required

The existing inline `<div>` is the correct pattern for a global layout banner — it does not need a shadcn Alert or Dialog wrapper. Keep it as a `<div>` with Tailwind classes. The only addition is an `<button>` (or `<Button variant="ghost">`) for dismiss.

---

## Feature 3: Fix Golden Path Install Docs (Remove Bundled Test Nodes)

### Problem

`compose.cold-start.yaml` includes `puppet-node-1` and `puppet-node-2` services. New users run this compose file and immediately have nodes enrolled — but those nodes need `JOIN_TOKEN_1` / `JOIN_TOKEN_2` set in `.env` before they work, and the tokens require a running server to generate. This creates a chicken-and-egg UX problem and obscures the actual node enrollment workflow.

The `install.md` and `enroll-node.md` docs rely on this compose file but the bundled nodes make the first-run experience unclear.

### Recommended Fix

**Remove `puppet-node-1` and `puppet-node-2` from `compose.cold-start.yaml`** entirely. The cold-start compose should spin up: `db`, `cert-manager`, `agent`, `dashboard`, `docs`. Nothing else.

This is a **pure YAML deletion** — no new libraries, no new code. The node enrollment flow then follows the documented manual steps in `enroll-node.md`.

Update the comment block at the top of `compose.cold-start.yaml` to remove the JOIN_TOKEN instructions (Steps 3–4 in the current comment). Remove the `node1-secrets`, `node2-secrets` volumes from the `volumes:` block.

**No stack changes required.**

---

## Feature 4: Signing UX Improvement (Hello-World Under 30 Minutes)

### Problem

The current first-job flow requires:
1. `openssl genpkey -algorithm ed25519 -out signing.key` (raw CLI)
2. `openssl pkey -in signing.key -pubout -out verification.key`
3. Manual paste of `verification.key` into the dashboard Signatures UI
4. Note the returned Key ID
5. Pass `--key signing.key --key-id <id>` to `axiom-push job push`

Steps 1–4 are the friction. Three separate shell commands + a dashboard UI round-trip before the operator can push their first job.

### Recommended Fix: `axiom-push key` Subcommand

Add a `key` subcommand to `mop_sdk/cli.py` that handles the entire keygen + register flow:

```
axiom-push key generate            # generates signing.key + verification.key locally
axiom-push key register --name X   # reads verification.key, POST /signatures, prints Key ID
axiom-push key setup --name X      # generate + register in one step
```

**Implementation:** Pure Python using the `cryptography` library (already a dependency in `pyproject.toml`):

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption
)

# Generate
private_key = Ed25519PrivateKey.generate()
signing_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
verification_pem = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

# Write
Path("signing.key").write_bytes(signing_pem)
Path("signing.key").chmod(0o600)
Path("verification.key").write_bytes(verification_pem)
```

`cryptography` is already in `pyproject.toml` dependencies for `mop_sdk`. Zero new imports required beyond what's already available.

The `register` sub-step calls `POST /api/signing-keys` (or the existing signatures endpoint) via the existing `MOPClient`, reads `verification.key`, and prints the returned Key ID so the operator can copy-paste it.

**The `setup` sub-step** is the happy path — one command generates the keys, registers the public key with a provided name, and prints the Key ID. The first-job doc can then be:

```bash
axiom-push login
axiom-push key setup --name my-first-key   # prints: Key ID: abc123
axiom-push job push --script hello.py --key signing.key --key-id abc123
```

This reduces the keygen friction from 4 steps to 1.

### Dashboard Signing UX (Optional Parallel Improvement)

The Signatures view (`Signatures.tsx`) could display a "Generate & Download" button that uses `window.crypto.subtle.generateKey` (Web Crypto API) in the browser to generate an Ed25519 keypair, download the private key as `signing.key`, and auto-register the public key via the API. This eliminates even the CLI keygen step.

**However:** Web Crypto Ed25519 support landed in Chrome 113 / Firefox 130 / Safari 17. Given the target audience (homelab/enterprise operators, likely on modern browsers), this is viable but optional. The `axiom-push key setup` CLI approach is the higher-priority fix and covers the CI/CD use case that dashboards cannot.

**No new frontend libraries required** — Web Crypto is a browser stdlib API.

---

## Recommended Stack Additions (New)

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `peaceiris/actions-gh-pages` | v4 | GitHub Pages deploy with subdirectory support | `keep_files: true` + `destination_dir` enable split homepage/docs deploy without manual branch manipulation; official GH Actions approach |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ghp-import` | already installed (mkdocs transitive dep) | Deploy MkDocs to `/docs/` subdirectory of gh-pages | Only needed if NOT using peaceiris/actions-gh-pages; already available in the docs venv |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Tailwind CDN (play.tailwindcss.com) | Styling for the marketing homepage | Use CDN script tag in `homepage/index.html`; no build step. Switch to bundled Tailwind only if homepage grows beyond a single page. |

---

## Installation

```bash
# No new Python packages required for any of the 4 features.
# All backend changes are code-only (YAML deletion, Python stdlib).

# No new npm packages required for the banner fix.
# All React changes use existing: useState, sessionStorage, lucide-react.

# For homepage:
# No npm install needed — Tailwind CDN in a <script> tag.

# For docs-deploy.yml change:
# peaceiris/actions-gh-pages@v4 is a GitHub Action, not a local package.
# Add it to .github/workflows/docs-deploy.yml.
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `peaceiris/actions-gh-pages@v4` for split deploy | Manual `ghp-import -x` in bash | Use `ghp-import -x` if you want to avoid the Actions dependency. More fragile (temp dir dance), but no external action required. |
| Static HTML + Tailwind CDN for homepage | Astro static site generator | Use Astro only if the marketing homepage needs multiple pages, blog, or MDX content. For a single landing page with a hero, features, and CTA, Astro adds unnecessary complexity. |
| `sessionStorage` for banner dismiss | `localStorage` | Use `localStorage` if you want the banner to stay dismissed across logins. Rejected: operators need to see the warning on each new session until the licence is renewed. |
| `axiom-push key setup` CLI command | Dashboard "Generate & Download" button | Use the dashboard Web Crypto approach if you want zero-CLI UX. The CLI is higher priority because it covers CI/CD and headless operators who never open the dashboard. |
| Remove nodes from cold-start compose | Keep nodes, improve token generation docs | Removing is cleaner. Bundled nodes cannot self-enroll without pre-generated tokens; the circular dependency makes first-run confusing regardless of how the docs explain it. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mkdocs gh-deploy --force` for the combined homepage+docs deploy | `--force` replaces the entire gh-pages branch root; no way to scope to a subdirectory | `peaceiris/actions-gh-pages@v4` with `destination_dir: docs` + `keep_files: true` |
| React framework (Next.js, Astro) for the homepage | Single-page marketing site does not need server-side rendering or a component framework; adds CI build time | Plain HTML + Tailwind CDN |
| `localStorage` for banner dismiss key | Makes the banner permanently hidden; operators on grace period need to see the renewal warning on every login | `sessionStorage` keyed to `licence.status` |
| New pip dependency for CLI keygen | `cryptography` is already in `pyproject.toml`; adding `PyNaCl` or `PyOpenSSL` for the same operation is redundant | `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey` |
| shadcn Alert component to replace the existing licence banner div | The existing `<div>` in `MainLayout.tsx` is already correctly positioned as a full-width layout element. Wrapping it in shadcn Alert adds unnecessary component nesting for no visual benefit | Keep the existing `<div>` structure; add only the dismiss button and sessionStorage logic |

---

## Stack Patterns by Variant

**If the marketing homepage stays a single page (likely):**
- Use plain HTML + Tailwind CDN
- Deploy via `peaceiris/actions-gh-pages@v4`
- Zero build step

**If the marketing homepage grows to multiple pages (future):**
- Migrate to Astro with Tailwind integration
- Build in CI, deploy output directory

**If the docs site URL must change (from root to /docs/):**
- Update `site_url` in `mkdocs.yml` to `https://axiom-laboratories.github.io/axiom/docs/`
- Update any hardcoded doc links in README, dashboard sidebar, and `install.md`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `peaceiris/actions-gh-pages@v4` | `actions/checkout@v4`, GitHub Actions `ubuntu-latest` | v4 requires `GITHUB_TOKEN` or `deploy_key`. Already using `contents: write` permission in `docs-deploy.yml`. |
| `cryptography` (already in `pyproject.toml`) | Python 3.10+ | `Ed25519PrivateKey.generate()` available since cryptography 2.6. No version bump needed. |
| Tailwind CDN (play CDN) | All modern browsers | Use `https://cdn.tailwindcss.com` script tag. Not for production apps (runtime JIT), but fine for a static marketing page. |
| `sessionStorage` | All modern browsers | Available since IE8. No polyfill needed. |
| Web Crypto `subtle.generateKey` with Ed25519 | Chrome 113+, Firefox 130+, Safari 17+ | August 2025 baseline is fine for this audience. Flag as optional enhancement, not MVP. |

---

## Sources

- Direct codebase analysis: `MainLayout.tsx`, `useLicence.ts`, `mop_sdk/cli.py`, `docs/mkdocs.yml`, `.github/workflows/docs-deploy.yml`, `compose.cold-start.yaml`, `pyproject.toml` — current state (HIGH confidence — source of truth)
- [mkdocs/mkdocs issue #2534 — Publish to subdirectory with gh_deploy](https://github.com/mkdocs/mkdocs/issues/2534) — `ghp-import -x` prefix flag confirmed (MEDIUM confidence — official issue tracker, community workaround)
- [peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages) — `destination_dir` and `keep_files: true` flags (HIGH confidence — official README, widely deployed)
- `mkdocs gh-deploy --help` — no `--dest-dir` or subdirectory flag exists (HIGH confidence — direct tool invocation)
- [shadcn/ui Banner component](https://www.shadcn.io/components/layout/banner) — controlled visibility pattern, localStorage persistence approach (MEDIUM confidence — official shadcn docs)
- [cryptography.io — Ed25519 key generation](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) — `Ed25519PrivateKey.generate()` API (HIGH confidence — official library docs)
- [MDN — sessionStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage) — session-scoped persistence (HIGH confidence — MDN)

---

*Stack research for: Go-to-market polish (homepage, licence banner, install docs, signing UX) — post-v14.3 milestone*
*Researched: 2026-03-27*
