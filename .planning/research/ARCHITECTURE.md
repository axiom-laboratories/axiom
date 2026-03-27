# Architecture Research

**Domain:** Go-to-market polish for existing Axiom orchestration platform
**Researched:** 2026-03-27
**Confidence:** HIGH (all findings verified against live codebase)

---

## Standard Architecture

### System Overview — v14.4 Feature Integration

```
GitHub Pages (axiom-laboratories.github.io/axiom/)
  ├── / (root)           <- NEW: Marketing homepage (plain HTML/CSS)
  └── /docs/             <- EXISTING: MkDocs Material site (gh-deploy target)
       ├── /docs/index.html
       └── /docs/...

Axiom Dashboard (React/Vite)
  ├── MainLayout.tsx
  │   ├── <header>
  │   │   └── sticky top-0 z-10
  │   ├── <LicenceBanner>  <- ALREADY EXISTS (lines 211-223 in MainLayout.tsx)
  │   └── <main>
  │       └── <Outlet />
  └── hooks/useLicence.ts  <- ALREADY EXISTS, returns LicenceInfo

compose.cold-start.yaml (Axiom evaluation stack)
  ├── db (postgres)
  ├── cert-manager (Caddy)
  ├── agent (FastAPI)
  ├── dashboard (React)
  ├── docs (MkDocs container)
  ├── puppet-node-1       <- REMOVE: bundled test node
  └── puppet-node-2       <- REMOVE: bundled test node

axiom-push CLI (mop_sdk/cli.py)
  ├── login               -> OAuth device flow (needs AXIOM_URL env var)
  ├── job push            -> --script, --key (path), --key-id (required)
  └── job create          -> --script, --key (path), --key-id (required)
```

### Component Responsibilities

| Component | Responsibility | Integration Touch |
|-----------|----------------|-------------------|
| GitHub Pages root `/` | Marketing landing page | NEW: separate workflow or manual deploy |
| GitHub Pages `/docs/` | MkDocs Material documentation site | MODIFIED: mkdocs `site_url` adjusted |
| `MainLayout.tsx` | App shell wrapping all dashboard views | ALREADY DONE: banner at lines 211-223 |
| `useLicence.ts` | Polls `GET /api/licence`, exposes `LicenceInfo` | NO CHANGE NEEDED |
| `compose.cold-start.yaml` | Cold-start evaluation stack | MODIFIED: remove `puppet-node-1/2` services + volumes |
| `mop_sdk/cli.py` | axiom-push CLI entry point | MODIFIED: add `generate-keypair` subcommand |
| `docs/getting-started/first-job.md` | First-job walkthrough | MODIFIED: promote CLI path, reduce openssl ceremony |

---

## Recommended Project Structure

```
(repo root)
├── docs/                    # MkDocs project (existing)
│   ├── mkdocs.yml           # MODIFIED: site_url -> /axiom/docs/ if using subdirectory
│   ├── docs/                # Source markdown
│   └── ...
├── homepage/                # NEW: marketing homepage source
│   ├── index.html           # Static HTML
│   ├── assets/              # CSS, images, logo.svg
│   └── ...
├── .github/workflows/
│   ├── docs-deploy.yml      # EXISTING: modified to use ghp-import --dest-dir
│   └── homepage-deploy.yml  # NEW: deploys homepage to gh-pages root
├── puppeteer/
│   ├── compose.cold-start.yaml  # MODIFIED: bundled nodes removed
│   └── ...
└── mop_sdk/
    ├── cli.py               # MODIFIED: add key generate command
    └── signer.py            # MODIFIED: add generate_keypair() static method
```

### Structure Rationale

- **homepage/**: Isolated from `docs/` so the two GitHub Actions workflows operate independently without conflicting paths. Static HTML avoids any build tool dependency.
- **Two-workflow GitHub Actions**: Each workflow commits only to its own path in `gh-pages` branch; neither clobbers the other's output.

---

## Architectural Patterns

### Pattern 1: Two-Workflow GitHub Pages Coexistence

**What:** Marketing homepage lives at `gh-pages` branch root (`/`); MkDocs docs live at `gh-pages:/docs/`. Two separate GitHub Actions workflows manage them. Neither overwrites the other because each uses `ghp-import` with different destination scopes.

**When to use:** Any repo publishing two distinct sites (landing + docs) to the same GitHub Pages domain.

**Trade-offs:** `mkdocs gh-deploy --force` by default overwrites the entire `gh-pages` branch. Must switch to `ghp-import` directly to scope the docs deployment to a subdirectory.

**Verified constraint (HIGH confidence):** `mkdocs gh-deploy` (MkDocs 1.6.1 installed locally) has NO `--dest-dir` flag. Running `mkdocs gh-deploy --help` confirms only: `-d/--site-dir` (local build output, not remote destination), `--force`, `--remote-branch`, `--remote-name`. The `--force` push replaces the entire branch root with no subdirectory option.

**Implementation — use `ghp-import` directly:**

```yaml
# .github/workflows/docs-deploy.yml  (MODIFIED)
- name: Build MkDocs
  working-directory: docs
  run: mkdocs build --strict

- name: Deploy docs to /docs/ subtree only
  run: |
    pip install ghp-import
    ghp-import --no-jekyll --push --force --dest-dir docs docs/site
```

`ghp-import --dest-dir docs` deploys only to the `/docs/` directory inside `gh-pages`, leaving the root (marketing homepage) untouched.

```yaml
# .github/workflows/homepage-deploy.yml  (NEW)
on:
  push:
    branches: [main]
    paths: ['homepage/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - name: Deploy homepage to gh-pages root
        run: |
          pip install ghp-import
          ghp-import --no-jekyll --push --force homepage/
```

Both workflows use `ghp-import`. The docs workflow targets `--dest-dir docs`; the homepage workflow targets root (no `--dest-dir`). Execution order does not matter since each is scoped to a different path.

**mkdocs.yml `site_url` must be updated to match:**
```yaml
site_url: https://axiom-laboratories.github.io/axiom/docs/
```
Without this change, MkDocs generates incorrect relative URLs (e.g., canonical links, sitemap) assuming the site is at `/axiom/` root.

---

### Pattern 2: Licence Banner Already Implemented

**What:** The licence banner is already present in `MainLayout.tsx` at lines 211-223. It renders conditionally on `licence.status === 'grace' || licence.status === 'expired'`, inserting a full-width amber/red bar between the sticky `<header>` and `<main>`.

**Confirmed implementation (HIGH confidence, from live source):**

```tsx
// MainLayout.tsx lines 211-223 — already in production
{(licence.status === 'grace' || licence.status === 'expired') && (
    <div className={`flex items-center gap-2 px-4 py-2 text-sm font-medium ${
        licence.status === 'expired'
            ? 'bg-red-900/40 text-red-300 border-b border-red-800'
            : 'bg-amber-900/40 text-amber-300 border-b border-amber-800'
    }`}>
        <AlertTriangle className="h-4 w-4 shrink-0" />
        {licence.status === 'expired'
            ? 'Your EE licence has expired. The system is running in Community Edition mode.'
            : `Your EE licence expires in ${licence.days_until_expiry} day${licence.days_until_expiry === 1 ? '' : 's'}. Please renew.`
        }
    </div>
)}
```

**Action required:** Validate against a running GRACE-state licence. The banner code is implemented — the v14.4 task is complete unless smoke testing reveals a rendering issue.

**useLicence.ts data flow:**

```
GET /api/licence (5-min stale, no retry on failure)
    |
LicenceInfo { status, tier, days_until_expiry, node_limit, customer_id, grace_days }
    | (computed)
isEnterprise = status !== 'ce'
    |
MainLayout:
  - sidebar badge: CE / EE (coloured by status — lines 135-143)
  - banner: shown on grace | expired (lines 211-223)
Admin.tsx:
  - LicenceSection: detailed display
```

No state management changes needed. If a `DEGRADED_CE` status is added to the backend state machine in a future milestone, adding it to the banner means: (1) extend `LicenceInfo.status` type in `useLicence.ts`, and (2) add a branch to the banner JSX.

---

### Pattern 3: compose.cold-start.yaml Node Removal

**What:** Remove `puppet-node-1` and `puppet-node-2` services and their named volumes. The evaluation stack becomes infrastructure-only (db, cert-manager, agent, dashboard, docs). Users enroll nodes manually following `enroll-node.md`.

**Why bundled nodes are a problem:** They require `JOIN_TOKEN_1`/`JOIN_TOKEN_2` env vars before first stack start — a bootstrap deadlock. The tokens can only be generated after the stack is running. Empty tokens (`JOIN_TOKEN_1:-`) cause both node containers to crash-loop with enrollment failures, polluting `docker compose logs` output and misleading evaluators into thinking the stack is broken.

**Minimal changes (exact lines to remove from compose.cold-start.yaml):**

```
Remove services:
  puppet-node-1: (lines 105-126, inclusive)
  puppet-node-2: (lines 127-148, inclusive)

Remove from volumes block (lines 154-155):
  node1-secrets:
  node2-secrets:

Update header comment (lines 13-14):
  Remove steps 3 and 4 referencing JOIN_TOKEN_1/JOIN_TOKEN_2.
  Replace with: "3. Follow docs/getting-started/enroll-node.md to enroll your first node."
```

No other compose changes required. The `secrets-data` volume for `boot.log`/`licence.key` stays. The `AXIOM_LICENCE_KEY` env passthrough in the `agent` service stays. The `depends_on` chain (db -> cert-manager -> agent) is unaffected.

---

### Pattern 4: axiom-push First-Job Friction Reduction

**What:** Reduce the number of distinct commands and manual steps between "I have axiom-push installed" and "my first job ran successfully."

**Current CLI friction points (HIGH confidence, from mop_sdk/cli.py and signer.py source):**

1. **No `key generate` command** — user must use raw `openssl genpkey` + `openssl pkey` commands. The CLI has `login`, `job push`, `job create` but no key generation subcommand. `mop_sdk/signer.py` has `load_private_key()` and `sign_payload()` but no `generate_keypair()` method.

2. **`--key` requires a file path** — private key must exist on disk before running any `job` subcommand. No stdin or env var alternative.

3. **`--key-id` is required with no lookup helper** — user must manually retrieve the UUID of the registered public key from the dashboard. There is no `axiom-push key register` or `axiom-push key list` command.

4. **`MOP_URL` vs `AXIOM_URL` inconsistency** — `cli.py` line 51 reads `os.getenv("MOP_URL")`. The docs (`axiom-push.md`) say `export AXIOM_URL=https://your-host`. This mismatch means the env var silently does nothing for users following the documentation.

**Minimal changes to reduce time-to-first-job:**

```
Priority 1 (cli.py + signer.py):
  Add `axiom-push key generate` subcommand
  - Calls Signer.generate_keypair() (new method in signer.py)
  - Uses cryptography lib Ed25519PrivateKey.generate() — already a dependency
  - Writes signing.key + verification.key to current directory (or --output-dir)
  - Prints next-step instructions: "Upload verification.key to Signatures in the dashboard"
  - Eliminates openssl dependency entirely for new users

Priority 2 (cli.py):
  Fix env var: os.getenv("MOP_URL") -> os.getenv("AXIOM_URL")
  - One-line change, unblocks users following the docs verbatim

Priority 3 (docs):
  first-job.md: reorder steps to put CLI tab first
  - Move CLI tab to primary position in Step 3 (sign) and Step 4 (dispatch)
  - CE curl path moves to collapsible block (already a pattern in the file)
  - Add "Step 0: Install axiom-push" before Step 1
  axiom-push.md: add key generation step to the documented workflow
```

**Data flow for reduced-friction path (post-changes):**

```
axiom-push key generate
    -> writes signing.key + verification.key to ./

[Manual: Dashboard -> Signatures -> Add -> paste verification.key -> note Key ID]

axiom-push login
    -> OAuth device flow -> saves token to ~/.axiom/credentials.json

axiom-push job push --script hello.py --key signing.key --key-id <uuid>
    -> loads key -> signs script -> POST /jobs -> prints job ID
```

The manual Signatures step cannot be eliminated without adding a `key register` CLI command (a larger change). For v14.4, the priority is removing the openssl ceremony and fixing the env var.

---

## Data Flow

### Licence Banner Flow

```
App mount
    |
useLicence() -> GET /api/licence (React Query, 5min stale, retry: false)
    |
MainLayout render
    |
licence.status === 'grace'   -> amber banner (days_until_expiry countdown)
licence.status === 'expired' -> red banner (CE fallback message)
licence.status === 'valid'   -> no banner
licence.status === 'ce'      -> no banner (CE badge in sidebar only)
```

### GitHub Pages Deploy Flow (proposed)

```
Push to main (docs/** changed)
    |
docs-deploy.yml
    -> mkdocs build --strict (working-directory: docs)
    -> ghp-import --no-jekyll --push --force --dest-dir docs docs/site
    -> gh-pages branch: /docs/** updated, root untouched

Push to main (homepage/** changed)
    |
homepage-deploy.yml (NEW)
    -> ghp-import --no-jekyll --push --force homepage/
    -> gh-pages branch: root index.html, assets/ updated, /docs/ untouched
```

---

## Integration Points

### New vs Modified Components

| Component | Status | Change |
|-----------|--------|--------|
| `homepage/index.html` | NEW | Marketing landing page (standalone HTML) |
| `homepage-deploy.yml` | NEW | GitHub Actions workflow for homepage |
| `docs-deploy.yml` | MODIFIED | Switch from `mkdocs gh-deploy --force` to `ghp-import --dest-dir docs` |
| `docs/mkdocs.yml` `site_url` | MODIFIED | Update to `.../axiom/docs/` if using subdirectory deploy |
| `MainLayout.tsx` lines 211-223 | ALREADY DONE | Banner implemented — validate only |
| `useLicence.ts` | NO CHANGE | Hook is complete |
| `compose.cold-start.yaml` | MODIFIED | Remove puppet-node-1, puppet-node-2, node1-secrets, node2-secrets |
| `mop_sdk/cli.py` | MODIFIED | Add `key generate` subcommand; fix `MOP_URL` -> `AXIOM_URL` |
| `mop_sdk/signer.py` | MODIFIED | Add `generate_keypair()` static method |
| `docs/getting-started/first-job.md` | MODIFIED | Reorder steps, promote CLI tab, fix env var name |
| `docs/feature-guides/axiom-push.md` | MODIFIED | Add key generation step to documented workflow |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `useLicence` <-> `MainLayout` | React hook in component tree | Already wired at line 41 in MainLayout.tsx |
| `MainLayout` banner <-> `Admin.tsx` LicenceSection | Both consume `useLicence()` independently | No shared state; both update when React Query cache refreshes |
| `homepage/` <-> `docs/` on gh-pages | `ghp-import` path scoping | Each workflow owns its path; no interference |
| `axiom-push key generate` <-> dashboard Signatures | Manual out-of-band step | No API automation for v14.4 |

---

## Build Order

Dependencies determine the order. Items with no cross-dependency can be done in parallel.

1. **compose.cold-start.yaml cleanup** — zero-risk, no code dependencies, immediately unblocks clean install documentation
2. **Licence banner smoke test** — verify existing code against GRACE licence state; close the task if it renders correctly; diagnose if it doesn't
3. **axiom-push CLI: fix MOP_URL -> AXIOM_URL** — one-line change, no test impact, unblocks users following docs
4. **axiom-push CLI: add `key generate` subcommand** — requires signer.py extension; test with `axiom-push key generate && axiom-push job push --key signing.key ...`
5. **first-job.md and axiom-push.md docs update** — depends on (3) and (4) being done; reorder steps, fix env var, promote CLI tab
6. **docs-deploy.yml: switch to ghp-import --dest-dir docs** — can be done in parallel with (1)-(5); must be in place before homepage goes live
7. **Marketing homepage HTML** — depends on (6) validated; final deliverable

---

## Anti-Patterns

### Anti-Pattern 1: Running `mkdocs gh-deploy --force` with a root homepage

**What people do:** Add a marketing homepage to the repo root and run the existing `mkdocs gh-deploy --force` workflow unchanged.
**Why it's wrong:** `gh-deploy --force` replaces the entire `gh-pages` branch with MkDocs output. The marketing homepage is deleted on every docs push.
**Do this instead:** Switch to `ghp-import --dest-dir docs` for the MkDocs workflow so it only writes to `/docs/` on the branch.

### Anti-Pattern 2: Keying the banner on undocumented status values

**What people do:** Add a `DEGRADED_CE` branch to the banner before confirming the backend emits that value.
**Why it's wrong:** The `GET /api/licence` response (v14.3) emits only `status: 'valid' | 'grace' | 'expired' | 'ce'`. A dead branch causes confusion and TypeScript type drift.
**Do this instead:** Validate against the live `GET /api/licence` response. If `DEGRADED_CE` is needed, extend both `licence_service.py` and `useLicence.ts` LicenceInfo type simultaneously.

### Anti-Pattern 3: Bundling test nodes in an evaluation compose file

**What people do:** Include pre-wired test nodes in `compose.cold-start.yaml` to give evaluators "something to see."
**Why it's wrong:** The nodes require JOIN tokens that can only be generated after the stack is running — a bootstrap deadlock. Empty tokens cause crash-loop restarts that flood `docker compose logs` and make evaluators think the stack is broken.
**Do this instead:** Remove bundled nodes. Document the manual enroll flow. Evaluators can follow `enroll-node.md` immediately after the core stack is up.

### Anti-Pattern 4: Adding a CLI subcommand without fixing the env var mismatch first

**What people do:** Add `key generate` to the CLI while leaving `MOP_URL` in `cli.py` line 51.
**Why it's wrong:** The env var mismatch means documentation-following users cannot set the server URL without using `--url`, making the login flow harder than it should be. New subcommands compound the confusion.
**Do this instead:** Fix `MOP_URL` -> `AXIOM_URL` in the same PR that adds `key generate`.

---

## Scaling Considerations

These features are purely user-experience concerns (deploy workflow, UI banner, compose cleanup, CLI command). No runtime scaling changes required. Not applicable.

---

## Sources

- Live codebase: `puppeteer/dashboard/src/layouts/MainLayout.tsx` (banner at lines 211-223)
- Live codebase: `puppeteer/dashboard/src/hooks/useLicence.ts`
- Live codebase: `puppeteer/compose.cold-start.yaml`
- Live codebase: `mop_sdk/cli.py` (env var at line 51: `MOP_URL`)
- Live codebase: `mop_sdk/signer.py`
- Live codebase: `docs/docs/getting-started/first-job.md`
- Live codebase: `.github/workflows/docs-deploy.yml`
- Live codebase: `docs/mkdocs.yml` (`site_url: https://axiom-laboratories.github.io/axiom/`)
- `mkdocs gh-deploy --help` (MkDocs 1.6.1 installed) — confirmed no `--dest-dir` flag (HIGH confidence)
- [MkDocs deploying docs](https://www.mkdocs.org/user-guide/deploying-your-docs/) — MEDIUM confidence
- [MkDocs with existing GitHub Pages discussion](https://github.com/mkdocs/mkdocs/discussions/3402) — MEDIUM confidence

---
*Architecture research for: Axiom v14.4 go-to-market polish*
*Researched: 2026-03-27*
