# Pitfalls Research

**Domain:** Go-to-market polish on an existing developer tool / job scheduler — marketing homepage on GitHub Pages alongside MkDocs docs, licence state banner (GRACE / DEGRADED_CE), Docker Compose test-node removal, and signing UX reduction
**Researched:** 2026-03-27
**Confidence:** HIGH (GitHub Pages behaviour from official docs + confirmed community issues; banner UX from Carbon Design System and LogRocket; Docker Compose orphan behaviour from docker/compose issue tracker; signing UX from first-user cold-start friction report in this repo)

---

## Critical Pitfalls

### Pitfall 1: CNAME File Wiped on Every `gh-deploy` Run

**What goes wrong:**
`mkdocs gh-deploy --force` rebuilds the `gh-pages` branch from scratch. If the marketing homepage lives in the same `gh-pages` branch and sets a custom domain via a `CNAME` file, that file is silently deleted every time the docs deploy workflow runs. The custom domain field in GitHub Pages settings resets, Pages falls back to the default `axiom-laboratories.github.io` URL, and external links to the marketing site break.

**Why it happens:**
`mkdocs gh-deploy` deletes and recreates the `gh-pages` branch root with the built docs tree. Unless `CNAME` is placed inside the MkDocs `docs/` source directory (so it gets copied into `site/` on build), it never makes it into the deployed tree. Developers set the custom domain once through the GitHub UI, see it work, then lose it on the next deploy without understanding why.

**How to avoid:**
Place a `CNAME` file directly in `docs/docs/` (the MkDocs `docs_dir`) with the custom domain. MkDocs copies it verbatim into `site/` and `gh-deploy` will push it. Alternatively, if marketing and docs share different subdirectories under the same Pages site (no custom domain), CNAME is irrelevant — but you must then set `site_url` correctly in `mkdocs.yml` so all generated URLs use the subdirectory prefix.

The marketing homepage should live in the same source repo, in a directory like `homepage/`, and the `docs-deploy.yml` GitHub Actions workflow must copy the built homepage into `site/` (or a parallel `homepage/` directory) before running `gh-deploy`. Alternatively, use a separate `homepage-deploy.yml` that deploys to a different target path or branch than `gh-pages`.

**Warning signs:**
- GitHub Pages custom domain disappears after merging a docs PR
- `curl -I https://axiom-laboratories.github.io/axiom/` returns 200 but marketing root returns 404
- CI logs show `mkdocs gh-deploy --force` running without copying `CNAME`

**Phase to address:** Phase 1 — GitHub Pages marketing homepage

---

### Pitfall 2: Subdirectory vs Root-Level URL Collision Between Marketing and Docs

**What goes wrong:**
Axiom's existing docs are deployed to `https://axiom-laboratories.github.io/axiom/` (a project-level Pages subdirectory). A new marketing homepage placed at root (`/`) of the same `gh-pages` branch will conflict with the `index.html` that MkDocs generates at `site/index.html` and places at the subdirectory root. If the marketing page is deployed as `site/index.html` (the repo root), they do not conflict — but if someone naively puts `index.html` in the MkDocs `docs/` directory thinking it will become the homepage, MkDocs overwrites it with its own generated index.

Conversely: if the marketing homepage is meant to be at `https://axiom-laboratories.github.io/axiom/` (same URL as docs), there is no clean separation — both will try to own that `index.html`.

**Why it happens:**
The distinction between a user/org Pages site (`username.github.io`) and a project Pages site (`username.github.io/repo`) is easy to conflate. The marketing homepage should be at the org-level URL (`axiom-laboratories.github.io`) while docs live at the project-level (`axiom-laboratories.github.io/axiom`). This requires the marketing homepage to deploy to the `axiom-laboratories.github.io` org repository (a separate repo), not into `axiom-laboratories.github.io/axiom`.

If the marketing homepage must live in the same repository, it should deploy to a `gh-pages` path that does not collide with the MkDocs-generated `index.html`. The cleanest split: marketing deploys to `gh-pages` root, MkDocs deploys to `gh-pages/docs/` sub-path, and `mkdocs.yml` sets `site_url: https://axiom-laboratories.github.io/axiom/docs/`.

**How to avoid:**
Decide on the URL ownership before writing any deployment workflow:
- Option A (recommended): Marketing homepage → `axiom-laboratories.github.io` (org repo). Docs → `axiom-laboratories.github.io/axiom/` (project repo, existing). No collision, independent deploy cycles.
- Option B: Marketing homepage → `axiom-laboratories.github.io/axiom/` root, docs → `axiom-laboratories.github.io/axiom/docs/`. Requires `mkdocs.yml` `site_url` update and all internal links in docs to use `/axiom/docs/` prefix. Risk: breaks any existing bookmarks to docs pages.

Never put the marketing homepage in the `docs/docs/` source directory expecting MkDocs to pass it through unmolested — MkDocs will generate its own `index.html` from the `nav` configuration.

**Warning signs:**
- `mkdocs build --strict` fails because a manually placed `index.html` in `docs/` conflicts with the generated one
- The docs welcome page shows marketing content after a mistaken commit
- `404` on `/axiom/` after the marketing homepage deploy overwrites the MkDocs `index.html`

**Phase to address:** Phase 1 — GitHub Pages marketing homepage

---

### Pitfall 3: `.nojekyll` Not Propagated Into Marketing Homepage Build Output

**What goes wrong:**
Axiom already has `.nojekyll` in the MkDocs source root (validated in v14.2) so GitHub Pages does not strip MkDocs underscore-prefixed assets. However, the marketing homepage is a separate static build. If that build deploys to the same `gh-pages` branch in a separate GitHub Actions step, and that step does not also place `.nojekyll` in the output, GitHub Pages Jekyll processing is not toggled per-directory — it is a branch-level flag. The risk: the second deploy step may overwrite or not include the root `.nojekyll`, causing Jekyll to strip `_assets/` directories from the marketing homepage.

**Why it happens:**
GitHub Pages applies Jekyll to the entire published branch. `.nojekyll` in the branch root suppresses Jekyll globally. If the marketing homepage deploy step uses a tool like `JamesIves/github-pages-deploy-action` pointed at a subfolder, that action by default performs a "clean" deploy that replaces the target folder's contents — it does not preserve files it did not write, including root-level `.nojekyll`.

**How to avoid:**
The `docs-deploy.yml` workflow already uses `mkdocs gh-deploy --force`. The marketing homepage deploy step should either:
1. Also include a `.nojekyll` file in its output directory, and
2. Use `--no-clobber` / `clean: false` if using `JamesIves/github-pages-deploy-action` for the marketing homepage, so it does not delete files written by the MkDocs step.

The safest pattern: run both builds in the same workflow job, combine outputs into a single directory, then deploy once.

**Warning signs:**
- Marketing homepage CSS/JS (in `_assets/` or `_next/`) returns 404 on GitHub Pages while working locally
- `_assets/` directory is present in the local build but absent in the deployed branch

**Phase to address:** Phase 1 — GitHub Pages marketing homepage

---

### Pitfall 4: Licence Banner Shown to Operators Who Cannot Act on It

**What goes wrong:**
The licence state banner (amber for GRACE, red for DEGRADED_CE) is displayed to all authenticated users including `viewer` role. Viewers cannot renew the licence — they have no access to Admin pages. Showing a persistent amber banner to a viewer role every login creates noise, degrades trust in the UI, and trains operators to dismiss banners. When a genuinely critical banner appears (e.g., node cert near expiry) it will be ignored.

**Why it happens:**
Banners are usually implemented as "show if condition X" without restricting by role. The GRACE state is operationally important to the admin but irrelevant and confusing to a viewer. Banner implementations often read from a global app context (e.g., `useLicence()` hook returning licence state) and render without a role check.

**How to avoid:**
Gate the GRACE and DEGRADED_CE banners on `user.role === 'admin'`. Operators (`operator` role) may also benefit from a softer notification ("Your administrator should check the licence status") but should not see the same actionable admin banner. The banner should link directly to Admin > Licence for admin users. For viewers: suppress entirely.

**Warning signs:**
- `useLicence()` hook used in `MainLayout.tsx` without a `currentUser.role` guard
- The banner links to `/admin/licence` which viewers cannot access — a 403 redirect on click

**Phase to address:** Phase 2 — licence state banner

---

### Pitfall 5: Banner Stacking — Licence Banner + Other Banners Competing for Attention

**What goes wrong:**
The dashboard already has notification patterns: DRAFT scheduled job warnings, inline error toasts, the `must_change_password` force-change modal. Adding a persistent licence banner at the top of every page creates a second always-visible banner that competes with contextual notifications. When a GRACE banner is displayed at the same time as a DRAFT job warning, operators read neither. Banner blindness sets in within days of deployment.

**Why it happens:**
Each feature team adds their own banner in isolation. The GRACE banner is added to `MainLayout.tsx`, the DRAFT warning is added to `JobDefinitions.tsx`, and no coordination prevents simultaneous display.

**How to avoid:**
Implement a single banner slot in `MainLayout.tsx` with priority ordering: `must_change_password` modal beats all; DEGRADED_CE banner (red) beats GRACE banner; GRACE banner beats contextual warnings. Only the highest-priority item renders. Do not stack banners. The GRACE banner should be dismissible per session (stored in `sessionStorage`) — it does not need to be shown on every page load once the operator has acknowledged it, as long as it reappears on a new session.

Additionally: the DEGRADED_CE state is more urgent than GRACE. DEGRADED_CE should be non-dismissible (EE features are actively broken) while GRACE should be dismissible.

**Warning signs:**
- Multiple `<div className="banner ...">` elements visible simultaneously in the DOM
- Operator feedback: "I stopped reading the top of the page"

**Phase to address:** Phase 2 — licence state banner

---

### Pitfall 6: Removing `puppet-node-1` / `puppet-node-2` From `compose.cold-start.yaml` Creates Orphan Volumes

**What goes wrong:**
The current `compose.cold-start.yaml` declares two named volumes: `node1-secrets` and `node2-secrets`. These are attached to `puppet-node-1` and `puppet-node-2`. When those services are removed from the file, existing users who run `docker compose -f compose.cold-start.yaml up -d` after pulling the update will see:

```
WARN[0000] Found orphan containers (axiom-puppet-node-1, axiom-puppet-node-2)
```

The containers are stopped and orphaned, but the named volumes `node1-secrets` and `node2-secrets` remain on disk consuming space. More importantly: if the services are re-added later (e.g., in a rollback), Docker Compose will reattach to the existing volumes with old node certificates — causing the nodes to attempt enrollment with stale certs against a new PKI, failing silently with mTLS errors.

**Why it happens:**
Docker Compose volume lifecycle is separate from service lifecycle. Removing a service from the compose file does not remove its volumes. This is by design (to protect data), but it creates confusion when test nodes are removed as part of a simplification exercise.

**How to avoid:**
Add a migration note to the release's `CHANGELOG.md` and `install.md` instructing users upgrading from a previous cold-start setup to run:

```bash
docker compose -f compose.cold-start.yaml down --remove-orphans
docker volume rm axiom_node1-secrets axiom_node2-secrets 2>/dev/null || true
```

Also: remove the `node1-secrets` and `node2-secrets` entries from the `volumes:` block at the bottom of `compose.cold-start.yaml` in the same commit as the service removal. Leaving dangling volume declarations with no associated service is valid YAML that Compose will silently create empty volumes for on next `up`, wasting space.

The volume names use Docker Compose project-name prefixing (`axiom_node1-secrets` if `COMPOSE_PROJECT_NAME=axiom`). Document the exact `docker volume rm` command based on the actual project name in use.

**Warning signs:**
- `docker volume ls` shows `axiom_node1-secrets` and `axiom_node2-secrets` after removing the services
- Users report "duplicate node" errors after restoring the services from a rollback
- CI cold-start tests fail because orphan containers from a previous run hold port bindings

**Phase to address:** Phase 3 — compose.cold-start.yaml cleanup

---

### Pitfall 7: JOIN_TOKEN Instructions Become Confusing Without Demo Nodes

**What goes wrong:**
The current `compose.cold-start.yaml` includes two bundled nodes with `JOIN_TOKEN_1` and `JOIN_TOKEN_2` variables. The install documentation tells users to "set JOIN_TOKEN_1 and JOIN_TOKEN_2 in your .env file." When those nodes are removed, that instruction is dead. First-time users following any version of the install docs that still references JOIN_TOKEN variables will be confused when those variables have no effect — or worse, will set them and wonder why no node appears.

The existing `install.md` already has tab-pair (CLI / Cold-Start) layouts. The cold-start tab will need updating to remove JOIN_TOKEN_1/JOIN_TOKEN_2 references and replace with "you must deploy a node separately using `enroll-node.md`". If the docs update does not land in the same PR as the compose change, there is a window where the compose is fixed but the docs are stale.

**Why it happens:**
Compose changes and documentation updates are often separate tasks. The compose file is code; the docs are prose. They go in different PRs or get assigned to different milestones.

**How to avoid:**
Treat the compose change and the install.md / enroll-node.md documentation update as a single atomic phase. Enforce this with a checklist in the PR description. The `install.md` cold-start tab should be updated to explicitly state that no nodes are included and link to `enroll-node.md`. The `.env.example` should remove the `JOIN_TOKEN_1` and `JOIN_TOKEN_2` example lines in the same commit.

**Warning signs:**
- `install.md` still references `JOIN_TOKEN_1` after the compose change is merged
- `.env.example` still has `# JOIN_TOKEN_1=` placeholder lines
- The cold-start smoke test tries to set `JOIN_TOKEN_1` in `.env` and reports a 200 but no node appears in the dashboard

**Phase to address:** Phase 3 — compose.cold-start.yaml cleanup

---

### Pitfall 8: Signing UX Shortcut Breaks Existing Automation Scripts

**What goes wrong:**
The current `axiom-push` CLI workflow requires explicit steps: generate key, register public key, sign script, submit. If the UX improvement introduces a new flag like `--auto-sign` or a new `axiom-push dispatch` subcommand that combines signing + dispatch, existing CI scripts that call `axiom-push sign` then `axiom-push submit` as separate steps will either get an error (command removed) or silently create duplicate dispatch calls (command now does both steps, old script does the second step again).

Similarly, if the dashboard guided dispatch form's step count or step names change, existing user documentation screenshots or runbooks pointing users to "Step 3: Paste your signature" become stale and confusing.

**Why it happens:**
UX simplification changes often remove steps that were previously required. When the removed step was previously invoked as a distinct CLI command or a named form field, anything referencing that step by name breaks.

**How to avoid:**
Any new combined command must be additive, not replacement. The old sequence (`sign` then `submit`) must continue to work unchanged. The new shortcut (`dispatch --auto-sign`) is an alternative, not a replacement. The CLI help text should show both paths.

For the dashboard guided form: if form steps are consolidated (e.g., signing happens automatically on "Submit" rather than a separate "Sign" step), ensure the `axiom-push` CLI equivalent path uses the same behaviour so CLI and dashboard are not diverged in their mental model.

Specifically: the `axiom-push` CLI is installed on user machines and in CI pipelines. Breaking a subcommand signature is a semver-breaking change requiring a major version bump. Do not remove or rename existing subcommands without a deprecation cycle.

**Warning signs:**
- A test in `mop_validation/scripts/` calls `axiom-push sign` or `axiom-push submit` as a subprocess and fails after the UX change
- `axiom-push --help` output no longer includes a subcommand that the docs still reference
- Dashboard guided form loses the "Script" field in a step consolidation — existing users can't find it

**Phase to address:** Phase 4 — signing UX improvement

---

### Pitfall 9: Auto-Signing Shortcut Exposes Private Key Path to Dashboard or API

**What goes wrong:**
A signing UX improvement that reduces friction by accepting "sign on my behalf" or "remember my key" functionality must never move private key material to the server. If the dashboard provides a "one-click sign" feature by prompting for a private key file path or having the user paste a private key, that private key travels over HTTPS to the server where it could be logged, stored in the DB, or leaked in an audit log entry.

The existing design (`axiom-push` CLI) is correct: the private key never leaves the operator's machine. The signature is computed locally and only the signature bytes + payload are transmitted. Any UX simplification must preserve this boundary.

**Why it happens:**
"Reduce steps to first signed job" can be misinterpreted as "allow the server to sign on the user's behalf" rather than "make the local signing workflow faster." A naive implementation of a "quick sign" button in the dashboard might prompt for a private key upload.

**How to avoid:**
The UX simplification should target the CLI workflow (reducing commands from 4 to 2, e.g., `axiom-push dispatch script.py`) and the dashboard workflow (make the signature paste box more prominent, add copy-paste hints from CLI output). The dashboard should never handle private key material. If a browser-based signing flow is considered (WebCrypto API), the key must be generated in-browser and never transmitted — this is out of scope for this milestone.

Document the security boundary explicitly in the signing UX PR description.

**Warning signs:**
- A new API endpoint accepts a `private_key` field in any request body
- The dashboard guided form adds a file upload for `.key` files
- `axiom-push` generates a keypair on a remote server rather than locally

**Phase to address:** Phase 4 — signing UX improvement

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Deploy marketing homepage inline in MkDocs `docs/docs/` | Single workflow, no extra repo | MkDocs overwrites `index.html`; homepage assets mix with doc assets | Never — use a separate directory or org repo |
| Show GRACE banner to all roles | Simpler rendering logic | Viewer-role banner blindness; confusing UX for non-admins | Never |
| Leave `node1-secrets` / `node2-secrets` volumes in `volumes:` block after removing services | No Compose error | Compose silently creates empty volumes on next `up`; upgrade notes become misleading | Never — remove in same commit as service removal |
| Add `axiom-push dispatch-and-sign` as alias that calls old sign+submit sequence | Fast UX win | CLI surface grows; two mental models coexist; docs must cover both | Acceptable short-term if old commands are preserved |
| Dismissible GRACE banner stored in `localStorage` (persists across sessions) | User only sees it once | Operator forgets about expiring licence; misses renewal window | Never — use `sessionStorage` so it reappears each new session |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GitHub Pages + MkDocs `gh-deploy` | CNAME not in MkDocs source | Place `CNAME` in `docs/docs/` so it's copied into `site/` on every build |
| GitHub Pages + two deploy steps | Second step clobbers `.nojekyll` from first | Run both builds in same job, merge outputs, deploy once with `.nojekyll` in root |
| `useLicence()` hook in React | Returning licence state to all components without role check | Guard banner render on `currentUser.role === 'admin'`; viewers see nothing |
| Docker Compose volumes block | Leaving declared volumes with no associated service | Remove volume declaration in same commit as service removal |
| `axiom-push` CLI versioning | Removing subcommand without deprecation | Mark old subcommand as deprecated in `--help`, keep it functional for at least one minor version cycle |
| Dashboard signing UX | Adding "quick sign" that transmits private key | Signing must remain local; only signature bytes go to server |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Licence state polled from API on every page render | 50-100ms added to every navigation, excessive `/api/licence` calls | Cache in React context (`useLicence()`) with a 5-minute TTL; do not re-fetch on every mount | Immediately visible in browser network tab |
| Marketing homepage bundle includes MkDocs Material theme assets | Page weight bloat, doubled asset downloads | Keep marketing homepage as plain HTML/CSS or a separate lightweight build; do not import MkDocs theme CSS | Any visitor with slow connection |
| `docs-deploy.yml` rebuilds entire MkDocs site on every push to `main` including non-doc changes | Slow CI, wasted GitHub Actions minutes | Path filter on `docs/**` — already implemented in v14.2; marketing homepage deploy should use its own path filter on `homepage/**` | Every push to main without path filter |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Marketing homepage form ("get early access") posts to the Axiom API | User email/data collected via unintended endpoint; CORS misconfiguration | Marketing forms must use a third-party form service (Formspark, Formspree) or a dedicated marketing backend — never the Axiom agent service |
| GRACE/DEGRADED_CE banner renders licence expiry date from client-side JWT decode | Expiry visible in JWT; easy to forge client-side if JWT validation is weak | Render from `GET /api/licence` response, not decoded JWT fields |
| Removing bundled test nodes exposes `JOIN_TOKEN_1` / `JOIN_TOKEN_2` env vars as unused in compose | No direct security risk, but stale env var examples in docs may mislead users into generating unnecessary tokens | Remove from `.env.example` in same PR |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| GRACE banner shows "expires in X days" without a CTA link | Admin sees the warning but doesn't know where to renew | Banner includes "View licence details" link to Admin > Licence section |
| DEGRADED_CE banner blocks access to the dashboard with a full-page overlay | Operators in degraded mode cannot investigate what happened | DEGRADED_CE is a top-bar banner, not a modal or page blocker — operators must still be able to view jobs and nodes |
| Signing UX adds a "copy command" button that copies the wrong CLI version | Users paste an `axiom-push` command that doesn't match their installed version | Copy buttons should show the canonical command without a pinned version; link to docs for version-specific variants |
| Removing demo nodes leaves the "Nodes" page empty with no guidance | First-time user installs cold-start, sees zero nodes, thinks the install failed | When Nodes list is empty, show an empty-state panel with a link to "Enroll your first node" guide |
| Marketing homepage does not link back to the docs site | Users find the homepage but cannot discover documentation | Every page of the marketing homepage has a prominent "Documentation" link pointing to the GitHub Pages docs URL |

---

## "Looks Done But Isn't" Checklist

- [ ] **Marketing homepage deploy:** CNAME file present in `site/` after `mkdocs gh-deploy` runs — verify with `git show gh-pages:CNAME`
- [ ] **Marketing homepage deploy:** `.nojekyll` present at `gh-pages` branch root after both deploy steps run — verify with `git show gh-pages:.nojekyll`
- [ ] **Licence banner — GRACE:** Banner visible when `app.state.licence_status == "GRACE"` in a logged-in admin session only — verify by checking `localStorage` for `mop_auth_token` with an admin JWT and a viewer JWT
- [ ] **Licence banner — DEGRADED_CE:** Banner is non-dismissible and links to Admin > Licence — verify banner persists across page navigation in the same session
- [ ] **Licence banner — CE mode:** No banner shown when `app.state.licence_status == "CE"` — verify no banner element present in DOM on fresh CE install
- [ ] **Compose node removal:** `node1-secrets` and `node2-secrets` removed from both `services:` and `volumes:` blocks — verify with `grep -c "node1-secrets" puppeteer/compose.cold-start.yaml` returning 0
- [ ] **Compose node removal:** `install.md` and `enroll-node.md` cold-start tabs contain no references to `JOIN_TOKEN_1` or `JOIN_TOKEN_2` — verify with `grep -r "JOIN_TOKEN_1" docs/`
- [ ] **Signing UX:** Existing `axiom-push sign` + `axiom-push submit` two-step flow still works unchanged — verify by running `mop_validation/scripts/run_signed_job.py` without modification
- [ ] **Signing UX:** No API endpoint accepts a `private_key` field — verify with `grep -r "private_key" puppeteer/agent_service/`
- [ ] **Empty nodes state:** Nodes page shows an enroll-guidance empty state when zero nodes are enrolled — verify by wiping the DB and loading the Nodes view

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| CNAME wiped by gh-deploy | LOW | Add `CNAME` file to `docs/docs/`; re-run `docs-deploy.yml` workflow; custom domain reappears within minutes |
| Marketing homepage URL collision with docs index | MEDIUM | Update `mkdocs.yml` `site_url` to new path; rebuild and redeploy docs; update any external links in README |
| Orphan volumes after node removal | LOW | `docker compose down --remove-orphans && docker volume rm axiom_node1-secrets axiom_node2-secrets`; user data in those volumes is only test node certs — no production data |
| GRACE banner shown to all roles causing user complaints | LOW | Add `currentUser.role === 'admin'` guard to banner render condition; no backend change needed |
| `axiom-push` subcommand broken by UX change | HIGH | Restore the old subcommand as a deprecated alias; release a patch version; update CHANGELOG |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| CNAME wiped by gh-deploy (Pitfall 1) | Phase 1: Marketing homepage | `git show gh-pages:CNAME` returns the correct domain after CI deploy |
| URL collision marketing vs docs (Pitfall 2) | Phase 1: Marketing homepage | Both `/axiom-labs.io/` and `/axiom-labs.io/axiom/` return 200; neither 404s the other |
| `.nojekyll` not propagated (Pitfall 3) | Phase 1: Marketing homepage | `git show gh-pages:.nojekyll` exists; marketing CSS/JS assets load without 404 |
| Banner shown to non-admin roles (Pitfall 4) | Phase 2: Licence banner | Login as `viewer` role; verify no licence banner in DOM |
| Banner stacking (Pitfall 5) | Phase 2: Licence banner | Simulate GRACE state + DRAFT job warning simultaneously; only one banner renders |
| Orphan volumes on node removal (Pitfall 6) | Phase 3: Compose cleanup | `docker volume ls` shows no `axiom_node1-secrets` after running upgraded compose |
| JOIN_TOKEN docs staleness (Pitfall 7) | Phase 3: Compose cleanup | `grep -r "JOIN_TOKEN_1" docs/` returns zero results |
| Signing UX breaks existing automation (Pitfall 8) | Phase 4: Signing UX | Run existing `mop_validation/scripts/run_signed_job.py` unchanged; job completes COMPLETED |
| Private key transmitted to server (Pitfall 9) | Phase 4: Signing UX | Code review confirms no API endpoint accepts private key material; security checklist item in PR |

---

## Sources

- [GitHub Docs: Troubleshooting custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages) — CNAME uniqueness constraint and domain revert behaviour
- [GitHub community discussion: Custom domain deleted after Pages workflow push](https://github.com/orgs/community/discussions/159544) — confirmed CNAME deletion by gh-deploy
- [GitHub issue: gh-pages package deletes CNAME on deploy](https://github.com/tschaub/gh-pages/issues/213) — root cause of CNAME wipe pattern
- [GitHub community discussion: Sub-directory routing 404](https://github.com/orgs/community/discussions/22296) — project Pages subdirectory path behaviour
- [GitHub issue: User/org pages CNAME affects all project pages URLs](https://github.com/isaacs/github/issues/547) — org-level custom domain impacts project Pages routing
- [Carbon Design System: Notification Pattern](https://carbondesignsystem.com/patterns/notification-pattern/) — one banner at a time; confine notifications to relevant workflow scope
- [LogRocket: Avoiding banner blindness in UX](https://blog.logrocket.com/ux-design/avoiding-banner-blindness-designing-attention/) — banner fatigue and dismissal behaviour
- [Medium: Banner Blindness in UX](https://medium.com/design-bootcamp/banner-blindness-in-ux-68f4d1e7dd74) — volume and persistence as fatigue drivers
- [Medium: Docker Compose orphan containers](https://medium.com/@almatins/how-to-resolve-docker-compose-warning-warn0000-found-orphan-containers-container-name-for-33f7de678d54) — orphan container + volume lifecycle on service removal
- [docker/compose GitHub: --remove-orphans does not remove volumes](https://github.com/docker/compose/issues/9718) — confirmed volumes persist independently
- [docker/compose: resource naming breaking change with dash vs underscore](https://docs.docker.com/reference/cli/docker/compose/up/) — project name prefix on volume names
- `puppeteer/compose.cold-start.yaml` — confirmed `puppet-node-1`, `puppet-node-2`, `node1-secrets`, `node2-secrets` present in current file
- `docs/docs/install.md` — JOIN_TOKEN_1 / JOIN_TOKEN_2 reference in cold-start install tab (requires update)
- `.planning/PROJECT.md` v14.0/v14.1/v14.2 validated items — existing Pages deploy, .nojekyll, offline plugin, CNAME context
- `mop_validation/cold_start_friction_report.md` — first-user signing friction baseline (5-step signing flow identified as BLOCKER)

---
*Pitfalls research for: Go-to-market polish milestone (marketing homepage, licence banner, compose cleanup, signing UX)*
*Researched: 2026-03-27*
