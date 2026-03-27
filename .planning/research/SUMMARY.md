# Project Research Summary

**Project:** Axiom v14.4 — Go-to-Market Polish
**Domain:** Developer tool GTM: marketing homepage, licence UX, install friction reduction, CLI onboarding
**Researched:** 2026-03-27
**Confidence:** HIGH

## Executive Summary

This milestone polishes the go-to-market surface of a fully functional job orchestration platform (Axiom). The backend, dashboard, CLI, and documentation infrastructure are all in production at v14.3. The work is entirely about reducing first-user friction and establishing a conversion surface — not building net-new features. Research confirmed that all four target areas (marketing homepage, licence state banner, compose cleanup, signing UX) can be addressed with additive or subtractive changes to existing files. No new backend APIs, no new frontend libraries, and no new pip packages are required for any of the four work streams.

The recommended approach is to treat the four sub-domains as largely independent parallel tracks with one hard dependency chain: the compose cleanup and signing UX improvement must land before the install docs are rewritten, and the install docs must be accurate before the marketing homepage makes specific claims (e.g., "up and running in 30 minutes"). The licence banner is the lowest-risk item with zero blocking dependencies and is already 80% implemented in `MainLayout.tsx` — it needs smoke testing and a session-scoped dismiss pattern more than it needs new code.

The primary risk in this milestone is deployment workflow interference: two separate GitHub Actions workflows writing to the same `gh-pages` branch can silently overwrite each other's output. The safe solution is `ghp-import --dest-dir docs` for the MkDocs workflow (scoping it to the `/docs/` subtree) and a separate homepage workflow targeting the branch root. The `peaceiris/actions-gh-pages@v4` action with `keep_files: true` is the cleanest mechanism. All other risks (orphan Docker volumes, banner shown to non-admin roles, CLI backward compatibility) are well-understood and have clear, low-effort mitigations.

## Key Findings

### Recommended Stack

The existing stack (FastAPI + React/Vite + Tailwind + shadcn/ui + `cryptography` lib) requires no additions for this milestone. The only new tooling is `peaceiris/actions-gh-pages@v4` (a GitHub Actions workflow action, not a local dependency) for the split-deploy pattern. `ghp-import` is already a transitive dependency of MkDocs. The marketing homepage should be plain HTML with the Tailwind CDN play script — no bundler, no framework, zero CI build time.

**Core technologies:**
- `peaceiris/actions-gh-pages@v4`: Split GitHub Pages deploy with `destination_dir` + `keep_files: true` — the only clean way to coexist a marketing homepage at `/` and docs at `/docs/` in the same branch without manual branch surgery
- `ghp-import` (already installed as mkdocs transitive dep): Direct subdirectory deploy alternative to the peaceiris action; `--dest-dir docs` scopes MkDocs output to `/docs/` on the branch
- Tailwind CDN (play.tailwindcss.com): Marketing homepage styling via `<script>` tag — zero build step, consistent with dashboard visual language; switch to bundled Tailwind only if homepage grows beyond one page
- `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey`: CLI key generation — already in `pyproject.toml`; eliminates the openssl ceremony for new users
- `sessionStorage`: Session-scoped banner dismiss state — correct choice over `localStorage` because licence expiry warnings should reappear each new login session

**Critical version/compatibility notes:**
- `mkdocs gh-deploy` (MkDocs 1.6.1) has NO `--dest-dir` flag — confirmed by direct CLI invocation. Must use `ghp-import` directly or `peaceiris/actions-gh-pages@v4`.
- Web Crypto Ed25519 (`subtle.generateKey`) requires Chrome 113+/Firefox 130+/Safari 17+ — viable for a future dashboard-based signing flow but defer to v2; the CLI `axiom-push key generate` is the P1 fix for this milestone.

### Expected Features

**Must have (table stakes — this milestone):**
- Licence state banner (amber GRACE, red EXPIRED/DEGRADED_CE) — backend ready, banner code already in `MainLayout.tsx` lines 211-223; needs smoke test, admin-only role guard, and session-scoped dismiss UX
- `axiom-push key generate` subcommand — removes the openssl ceremony that blocks new users at step 3 of the signing flow; uses `cryptography` lib already in `pyproject.toml`
- `MOP_URL` → `AXIOM_URL` env var fix in `cli.py` line 51 — one-line change; silently breaks all users following the published docs verbatim
- Clean `compose.cold-start.yaml` — remove `puppet-node-1`, `puppet-node-2`, `node1-secrets`, `node2-secrets` services and volume declarations in one atomic commit
- Updated install docs (`install.md`, `enroll-node.md`) matching the node-free cold start — must ship in same PR as compose change
- Marketing homepage — static `index.html` on GitHub Pages with hero, security positioning, CE/EE comparison table, GitHub stars badge, docs link; unblocked only after clean install path is verified

**Should have (add when P1 items are stable):**
- `axiom-push status` command — "am I set up correctly?" health check; reduces first-user support noise
- `axiom-push sign-and-push` combined command — daily-use convenience wrapper over existing sign + push
- Troubleshooting accordion in install docs — populate based on observed post-launch first-user failures
- Empty-state guidance panel on the Nodes page when zero nodes are enrolled

**Defer (v2+):**
- OS keychain credential storage in `axiom-push`
- Animated terminal demo on marketing homepage
- Video walkthrough
- Homepage testimonials section (only when 2+ real attributed quotes exist)
- Browser-based signing via Web Crypto API in the dashboard

### Architecture Approach

All four work streams operate on existing files with no new components crossing service boundaries. The most structurally significant change is the GitHub Pages deploy split: a new `homepage/` source directory, a new `homepage-deploy.yml` workflow, and modifying `docs-deploy.yml` to use `ghp-import --dest-dir docs` instead of `mkdocs gh-deploy --force`. The `mkdocs.yml` `site_url` must be updated to match the new subdirectory location to avoid broken canonical links and sitemap URLs.

**Major components and their changes:**

1. `homepage/index.html` (NEW) — static marketing page; deployed to `gh-pages` root by `homepage-deploy.yml`
2. `.github/workflows/homepage-deploy.yml` (NEW) — triggers on `homepage/**` path changes; pushes to `gh-pages` root
3. `.github/workflows/docs-deploy.yml` (MODIFIED) — replace `mkdocs gh-deploy --force` with `ghp-import --dest-dir docs docs/site`
4. `docs/mkdocs.yml` `site_url` (MODIFIED) — update to `https://axiom-laboratories.github.io/axiom/docs/`
5. `MainLayout.tsx` lines 211-223 (ALREADY DONE) — banner exists; add dismiss button, `sessionStorage` keyed to `licence.status`, and `currentUser.role === 'admin'` guard
6. `compose.cold-start.yaml` (MODIFIED) — delete `puppet-node-1`, `puppet-node-2`, and their volume declarations
7. `mop_sdk/cli.py` + `mop_sdk/signer.py` (MODIFIED) — add `key generate` subcommand calling a new `Signer.generate_keypair()` method; fix `MOP_URL` → `AXIOM_URL` env var
8. `docs/getting-started/first-job.md` + `docs/feature-guides/axiom-push.md` (MODIFIED) — promote CLI tab, fix env var reference, add key generation step

### Critical Pitfalls

1. **`mkdocs gh-deploy --force` wipes marketing homepage on every docs push** — switch to `ghp-import --dest-dir docs` for the MkDocs workflow so it scopes output to the `/docs/` subtree only; homepage workflow targets branch root separately. The `--force` flag replaces the entire `gh-pages` branch root with no subdirectory option.

2. **`.nojekyll` not propagated when two workflows write to the same branch** — the homepage workflow must include `.nojekyll` in its output (or use the `--no-jekyll` flag); GitHub Pages Jekyll suppression is a branch-level flag, not per-directory. A second deploy step can overwrite the root `.nojekyll` placed by the first.

3. **Licence banner shown to non-admin roles causes banner blindness** — gate banner render on `currentUser.role === 'admin'`; viewers cannot renew the licence and will start ignoring all banners if they see an unactionable red alert on every page load.

4. **Orphan Docker volumes after node service removal** — remove `node1-secrets`/`node2-secrets` from both `services:` and `volumes:` blocks in the same commit; include `docker compose down --remove-orphans && docker volume rm` instructions in release notes. `--remove-orphans` stops the containers but does NOT remove volumes.

5. **Signing UX changes must be strictly additive** — new `axiom-push key generate` must not remove or rename any existing subcommands; `mop_validation/scripts/run_signed_job.py` must continue to work unchanged. Removing a CLI subcommand without a deprecation cycle is a semver-breaking change.

6. **Banner stacking — GRACE + other notifications visible simultaneously** — implement a single banner slot in `MainLayout.tsx` with priority ordering (DEGRADED_CE > GRACE > contextual warnings); GRACE should be session-dismissible, DEGRADED_CE should not be. Multiple simultaneous banners lead to operators ignoring all of them.

## Implications for Roadmap

The dependency graph from FEATURES.md, confirmed by ARCHITECTURE.md and PITFALLS.md, suggests four parallel initial phases collapsing into one final phase:

### Phase 1: Licence Banner Polish
**Rationale:** Zero blocking dependencies. Backend is ready, component is 80% implemented. Delivers immediate operator value on any running instance. Lowest-risk item in the milestone — a banner rendering bug fails safe (banner just doesn't show; no functionality blocked).
**Delivers:** Dismissible amber/red licence state banner; admin-only role guard; `sessionStorage` dismiss keyed to `licence.status`; deep-link CTA to Admin > Licence; DEGRADED_CE as a non-dismissible red variant; single-banner-slot priority ordering in `MainLayout.tsx`.
**Addresses:** Sub-Domain B table stakes + differentiators from FEATURES.md.
**Avoids:** Pitfall 4 (non-admin banner noise) and Pitfall 6 (banner stacking).
**Research flag:** Skip. Pattern is well-documented; component already exists. Begin with a smoke test against a GRACE-state licence — if it renders correctly, scope may shrink to adding dismiss + role guard only.

### Phase 2: Compose Cleanup (atomic with doc update)
**Rationale:** Lowest-risk code change in the milestone — pure YAML deletion. Must ship atomically with the corresponding doc updates to avoid a window where compose is fixed but docs still reference dead JOIN_TOKEN env vars.
**Delivers:** `compose.cold-start.yaml` without bundled test nodes; updated `install.md` and `enroll-node.md` removing JOIN_TOKEN_1/2 references; `.env.example` cleaned up; migration/upgrade instructions for existing evaluators.
**Addresses:** Sub-Domain C table stakes from FEATURES.md.
**Avoids:** Pitfall 5 (orphan volumes) and Pitfall 7 (stale JOIN_TOKEN docs).
**Research flag:** Skip. Changes are purely subtractive and well-understood.

### Phase 3: axiom-push CLI Signing UX
**Rationale:** The install docs rewrite (Phase 2 extension) and the marketing homepage "30-minute" claim both depend on this working. The `MOP_URL` env var fix is a one-liner that should ship in the same PR to prevent compounding the existing silent failure mode.
**Delivers:** `axiom-push key generate` subcommand (new `Signer.generate_keypair()` method in `signer.py`); `MOP_URL` → `AXIOM_URL` env var fix in `cli.py`; updated `first-job.md` with CLI tab promoted to primary; updated `axiom-push.md` adding key generation step.
**Addresses:** Sub-Domain D table stakes from FEATURES.md; P1 items from the Feature Prioritization Matrix.
**Avoids:** Pitfall 8 (backward compatibility — additive only) and Pitfall 9 (private key never transmitted to server).
**Research flag:** Skip. `cryptography` lib API is stable; CLI extension pattern is established in the existing codebase.

### Phase 4: GitHub Pages Deploy Split
**Rationale:** Technical prerequisite for the marketing homepage. Can run in parallel with Phases 1-3 since it only touches the CI workflow and `mkdocs.yml`. Must be validated (MkDocs docs render correctly at the new `/docs/` subdirectory URL) before the homepage goes live.
**Delivers:** Modified `docs-deploy.yml` using `ghp-import --dest-dir docs`; updated `mkdocs.yml` `site_url`; new `homepage-deploy.yml` workflow stub; verified docs rendering at `...github.io/axiom/docs/`.
**Addresses:** Stack recommendation from STACK.md; Architecture Pattern 1 from ARCHITECTURE.md.
**Avoids:** Pitfall 1 (CNAME wipe by gh-deploy), Pitfall 2 (URL collision), and Pitfall 3 (.nojekyll propagation).
**Research flag:** Low-effort verification spike recommended before implementation: run `ghp-import --help` in the docs virtualenv to confirm the `--dest-dir` flag is available in the transitively-installed version. Fallback to `peaceiris/actions-gh-pages@v4` is fully documented and ready.

### Phase 5: Marketing Homepage
**Rationale:** External-facing deliverable unblocked only after Phase 3 (CLI in place, enabling honest "30-minute" claim) and Phase 4 (deploy infrastructure validated). All other phases enable this one.
**Delivers:** `homepage/index.html` with hero, above-fold value prop, security positioning block ("Scripts never run unsigned. Nodes never expose ports."), CE/EE comparison table, GitHub stars badge, architecture overview, docs link; deployed to `gh-pages` root via `homepage-deploy.yml`.
**Addresses:** Sub-Domain A table stakes + differentiators from FEATURES.md.
**Avoids:** Anti-features flagged in FEATURES.md — no animated demos, no testimonials, no auto-pulled README, no more than 6 sections.
**Research flag:** Skip. Static HTML + Tailwind CDN is a well-established pattern. No framework decisions needed.

### Phase Ordering Rationale

- **Phases 1, 2, 3, and 4 are independent and can run in parallel** — they share no code dependencies with each other. Assign to parallel tracks or sequence based on implementer availability.
- **Phase 5 depends on Phases 3 and 4 being complete and validated** — do not publish "up and running in 30 minutes" until the path works end-to-end; do not deploy the homepage until the subdirectory docs deploy is confirmed stable.
- **Phase 2 compose change and doc update must be a single atomic PR** — enforces no-stale-docs rule; prevents a JOIN_TOKEN doc/code mismatch window.
- **Phase 3 CLI fix ships before the docs reference the new command** — if docs update is part of Phase 2, the `MOP_URL` fix and `key generate` command must exist first, or the doc update must be deferred to Phase 3's PR.

### Research Flags

Phases needing a verification spike during planning:
- **Phase 4:** Confirm `ghp-import --dest-dir` flag availability in the mkdocs transitive install with `pip show ghp-import && ghp-import --help`. If the flag is absent in the pinned version, use `peaceiris/actions-gh-pages@v4` instead (documented in STACK.md, HIGH confidence).

Phases with well-established patterns (skip research-phase):
- **Phase 1:** Existing React component, existing hook, sessionStorage pattern — all well-documented, no unknowns.
- **Phase 2:** Pure YAML deletion and prose doc update — no integration risk.
- **Phase 3:** `cryptography` Ed25519 API is stable; CLI argparse extension pattern mirrors existing subcommands.
- **Phase 5:** Single-page static HTML with Tailwind CDN — no moving parts.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings verified against live codebase + official docs. `peaceiris/actions-gh-pages@v4` is the de-facto standard GH Pages action (100k+ stars, used in mkdocs-material's own CI). Zero new pip packages required. |
| Features | HIGH (banner, compose, CLI) / MEDIUM (homepage) | Banner/compose/CLI findings grounded in live codebase analysis. Homepage section ordering and content informed by devtool landing page research (single secondary source); structure is conventional enough that MEDIUM confidence is not a risk. |
| Architecture | HIGH | All component boundaries verified by reading live source files. One MEDIUM-confidence item: `ghp-import --dest-dir` flag availability — easily resolved with a one-line CLI check before implementation starts. |
| Pitfalls | HIGH | Critical pitfalls (CNAME wipe, orphan volumes, `MOP_URL` mismatch, banner shown to non-admins) corroborated by official GitHub docs, docker/compose issue tracker, and direct inspection of live source files. |

**Overall confidence:** HIGH

### Gaps to Address

- **`ghp-import --dest-dir` flag availability:** Verify with `ghp-import --help` in the docs virtualenv before committing to this approach in Phase 4. If unavailable, switch to `peaceiris/actions-gh-pages@v4` — fully documented fallback.
- **Banner smoke test against GRACE state:** The banner code exists but has not been validated against a live GRACE-state licence. Phase 1 should begin with this verification step. If the banner renders correctly, the scope may shrink to adding dismiss logic and the admin role guard only.
- **`axiom-push` version in CI/CD pipelines:** Before Phase 3 ships, confirm whether `mop_validation/scripts/run_signed_job.py` calls `axiom-push` subcommands directly as subprocess (requires backward compat check) or via the Python SDK API (less brittle). PITFALLS.md flags this as a high-cost recovery if broken.
- **`mkdocs.yml` internal link impact:** Changing `site_url` from `/axiom/` to `/axiom/docs/` will cause any hardcoded absolute doc links in the README, dashboard sidebar, and other files to return 404. Audit these before Phase 4 ships.

## Sources

### Primary (HIGH confidence)
- Live codebase: `puppeteer/dashboard/src/layouts/MainLayout.tsx` (banner at lines 211-223)
- Live codebase: `puppeteer/dashboard/src/hooks/useLicence.ts`
- Live codebase: `puppeteer/compose.cold-start.yaml`
- Live codebase: `mop_sdk/cli.py` (env var at line 51: `MOP_URL`)
- Live codebase: `mop_sdk/signer.py`
- Live codebase: `.github/workflows/docs-deploy.yml`
- Live codebase: `docs/mkdocs.yml` (`site_url: https://axiom-laboratories.github.io/axiom/`)
- `mkdocs gh-deploy --help` (MkDocs 1.6.1) — confirmed no `--dest-dir` flag
- [peaceiris/actions-gh-pages README](https://github.com/peaceiris/actions-gh-pages) — `destination_dir` and `keep_files: true` flags
- [cryptography.io Ed25519 docs](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) — `Ed25519PrivateKey.generate()` API
- [MDN sessionStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage)
- [GitHub Docs: Troubleshooting custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages)
- [docker/compose: --remove-orphans does not remove volumes](https://github.com/docker/compose/issues/9718)
- [Carbon Design System: Notification Pattern](https://carbondesignsystem.com/patterns/notification-pattern/)

### Secondary (MEDIUM confidence)
- [mkdocs/mkdocs issue #2534](https://github.com/mkdocs/mkdocs/issues/2534) — `ghp-import -x` subdirectory flag workaround; community-confirmed
- [MkDocs with existing GitHub Pages discussion #3402](https://github.com/mkdocs/mkdocs/discussions/3402) — subdirectory deploy patterns
- [shadcn/ui Banner component](https://www.shadcn.ui/components/layout/banner) — controlled visibility + sessionStorage persistence pattern
- Evil Martians: "We studied 100 dev tool landing pages — here's what actually works in 2025" — homepage structure recommendations (hero + security positioning + CE/EE table)
- Lucas F. Costa: "UX patterns for CLI tools" — `init` as the standard onboarding entry point pattern
- [LogRocket: Avoiding banner blindness in UX](https://blog.logrocket.com/ux-design/avoiding-banner-blindness-designing-attention/)
- `mop_validation/cold_start_friction_report.md` — first-user signing friction baseline (5-step flow identified as blocker)

### Tertiary (LOW confidence)
- Docker Compose project-name prefix behaviour on volume names — prefix may vary based on `COMPOSE_PROJECT_NAME` setting; verify exact `docker volume rm` command against the live stack before documenting it in release notes.

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*
