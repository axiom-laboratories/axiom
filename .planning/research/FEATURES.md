# Feature Research

**Domain:** Go-to-market polish — developer tool marketing homepage, licence state notifications, install documentation, CLI signing UX
**Researched:** 2026-03-27
**Confidence:** HIGH (homepage/banner patterns) / MEDIUM (CLI UX specifics)

---

## Scope

This milestone adds four go-to-market features to Axiom. They are treated as four distinct sub-domains below, each with its own table stakes, differentiators, and anti-features. A combined dependency map and MVP definition follow.

---

## Sub-Domain A: Marketing Homepage (GitHub Pages, standalone)

The product already has a MkDocs docs site at `axiom-laboratories.github.io/axiom/`. The marketing homepage is a **separate static page** — a conversion surface, not documentation. Its job is to answer "what is this and why should I try it?" in under 60 seconds.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Hero section: headline + one-line description + primary CTA | Every devtool homepage has one. Missing = no anchor for the eye. | LOW | CTA must be specific: "Get started in 5 minutes" not "Learn more". Secondary CTA to GitHub repo. |
| Above-the-fold value proposition | Developers decide in ~8s whether to keep reading. | LOW | Must answer: what it is, who it's for, key benefit. E.g. "Axiom — secure job orchestration for hostile environments." |
| GitHub stars badge / usage signal | Social proof for OSS. Missing = project feels dead. | LOW | Use `shields.io` badge or GitHub API widget. Even a low number is better than nothing. |
| Link to documentation | Developers will not try a tool without docs. | LOW | Single prominent link to existing MkDocs site. |
| Feature highlights (3–5 items) | Answers "what can it do?". Problem-oriented, not feature-list. | LOW | Format: icon + short title + one sentence. Focus on security model, pull architecture, signing. |
| Architecture/how-it-works diagram | Distributed systems tool — topology is not obvious. | MEDIUM | Single Mermaid-style or SVG diagram showing orchestrator + nodes + pull flow. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "Security-first" positioning block | Axiom's core differentiator is structural security (mTLS, Ed25519, container isolation). This is rare in homelab/OSS schedulers. | LOW | Dedicate a section to: "Scripts never run unsigned. Nodes never expose ports. Your private key never leaves your machine." Three concrete claims. |
| CE vs EE comparison table | Sets expectation for enterprise buyers. Signals commercial maturity. | LOW | Simple table: feature rows, CE checkmark/dash, EE checkmark. Link to licensing.md. |
| 30-minute quick-start callout | Reduces perceived barrier. "Up and running in 30 minutes" is a concrete promise. | LOW | Ties directly to the getting-started doc. Must be honest — only add if the doc genuinely supports this. |
| Changelog/release signal | Signals active project. Reduces "is this abandoned?" fear. | LOW | Latest release badge from GitHub, or a one-line "latest release" note. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-pulled GitHub README as homepage | Minimal effort, keeps docs in sync | README is for contributors, not prospects. Different audience, different framing. | Maintain separate `index.html` — 100 lines max. |
| Animated terminal demo | Looks impressive, signals sophistication | High maintenance (breaks on API changes), slow to load, often misleads about real UX | Static screenshot of dashboard + one-line install command |
| Full feature documentation embedded on homepage | "Comprehensive" feels thorough | Kills conversion. Readers leave before reaching CTA. | Keep homepage to 6 sections max. Link to docs for depth. |
| Testimonials section (if no real testimonials exist) | Social proof pattern | Fake or placeholder quotes destroy credibility with developers | Omit entirely until there are 2–3 real quotes from identifiable users |

---

## Sub-Domain B: Licence State Notification Banner

The backend already returns `VALID / GRACE / EXPIRED / DEGRADED_CE` via `GET /api/licence`. The dashboard has an EE badge in the sidebar. What is missing is a **top-of-dashboard banner** that communicates urgency to the operator when action is required.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Amber banner for GRACE state | Industry standard: warn before it breaks. Missing = operator discovers expiry only when features stop. | LOW | Amber/yellow. Persistent until dismissed. Shows days remaining. Includes "Renew licence" link. |
| Red banner for EXPIRED / DEGRADED_CE state | Critical state — EE features silently degraded. Must be unmissable. | LOW | Red. Non-dismissible (or re-appears on every page load). CTA: "Contact sales" or "Upgrade". |
| Days remaining in GRACE displayed in banner | Operators need to know urgency. "Licence expiring" is not enough. | LOW | Pull `expires_at` from licence API response and compute days. |
| Banner calls the existing `GET /api/licence` endpoint | Backend is ready. Frontend just needs to read and display. | LOW | Use existing `useLicence` hook already wired to the Admin page. |
| No banner for VALID state | Showing an "all good" banner is noise. | LOW | Conditional render: only show when state is not VALID. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Role-aware banner (admin-only) | Viewers/operators can't act on licence renewal. Showing them an alarm they can't fix is noise. | LOW | Check `current_user.role === 'admin'` before rendering banner. Viewer/operator sees nothing. |
| Deep-link CTA from banner | Reduces friction to action. "View licence details" takes admin straight to the Admin page licence section. | LOW | `href="/admin#licence"` — existing Admin.tsx already has a LicenceSection. |
| DEGRADED_CE-specific messaging | CE means EE features are silently off, not "expired". Different message than EXPIRED. | LOW | "Running in Community Edition mode — Enterprise features disabled." vs "Licence expired — renew to restore features." |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Modal dialog for licence expiry | High visibility | Blocks the entire UI. Operators can't work. Enterprise tools that do this get disabled in `localStorage`. | Banner at top of page. Persistent but non-blocking. |
| Countdown timer (live ticking clock) | Urgency | Anxiety-inducing. Distracts from actual work. | "X days remaining" static text, refreshed on page load. |
| Banner on every route including login page | Maximum visibility | Shows to all users, even those who cannot act. Causes support tickets from confused users. | Only render inside the authenticated layout, check admin role. |

---

## Sub-Domain C: Golden Path Install Docs

The existing `compose.cold-start.yaml` bundles pre-configured test nodes (`node_alpha`, `node_beta`, `node_gamma`) in the same compose file. First users start all of them, see nodes they did not create, and do not know what is real vs. example infrastructure. The goal is a clean first-user path: "start the server, then manually add your first node."

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Separate compose file for orchestrator-only cold start | Users expect "run this to get the server" without mystery pre-enrolled nodes. | LOW | New or updated `compose.cold-start.yaml` containing only: agent, model, postgres, caddy, docs. No test nodes. |
| Test nodes moved to a clearly-labelled optional override | Test nodes are useful for development — they should not disappear, just stop being default | LOW | `compose.test-nodes.yaml` as an optional extend or separate file. Comment in compose: "Test infrastructure — not needed for production." |
| Step-by-step getting-started doc matching the clean compose | Docs must match what the user actually runs. | MEDIUM | Update `install.md` + `enroll-node.md` to reflect the node-free cold start. Steps: 1) start server, 2) log in, 3) get JOIN_TOKEN, 4) start your own node. |
| Prerequisite callout at top of install doc | Users need to know what they need before they start. Missing = halfway-done installs. | LOW | Callout block: Docker Engine 24+, docker compose plugin, 2 GB RAM, port 443/8001 open. |
| Expected-state checkpoints after each step | Users need to know when a step is done. "It should look like X." | LOW | After each step: "You should see: [screenshot or terminal output snippet]". |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "30-minute badge" — honest time estimate per section | Sets expectation. Reduces abandonment from uncertainty. | LOW | Section headers: "Step 1: Start the server (~5 min)", "Step 2: Enroll your first node (~10 min)". Only add if accurate. |
| Troubleshooting accordion in install doc | Installs fail. Embedded troubleshooting reduces support burden. | MEDIUM | 3–5 common failures: "Caddy 502", "Node won't enroll", "Admin password mismatch". Each: symptom → cause → fix. |
| Copy-paste command blocks with no modifications needed | Zero-edit install is the gold standard. | MEDIUM | Replace all `<YOUR_HOSTNAME>` placeholders with `localhost` defaults. Let users override in `.env`, not by editing the compose file. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Single compose file for everything (server + nodes) | "One command" is appealing | Conflates orchestrator and node. Nodes are on different machines in real deployments. Teaches wrong mental model. | Two files. Document that nodes run `node-compose.yaml` on a separate machine (or same for dev). |
| Wizard/installer script | Reduces friction further | Adds a maintenance surface. Script goes out of date. Compose + .env is already declarative. | Well-commented `.env.example` with sensible defaults. |
| Video walkthrough as primary onboarding path | High engagement for learners | Videos go stale on every UI change. Cannot be searched or copy-pasted from. | Text + screenshots. Link to video from docs if one exists, but not as the only path. |

---

## Sub-Domain D: Hello-World Signing UX (axiom-push CLI)

The current flow requires: `pip install axiom-push` → `axiom-push login` (OAuth device flow) → `axiom-push key generate` → upload public key in dashboard → `axiom-push sign my_script.py` → `axiom-push push my_script.py`. This is 5+ distinct operations. First users abandon at step 3.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `axiom-push init` — single onboarding command | CLI tools that require manual multi-step setup before first use fail. `init` is the standard pattern (cf. `git init`, `npm init`, `gh auth login`). | MEDIUM | Chains: login (OAuth device flow) → key generation → uploads public key to server → prints confirmation. Interactive prompts for server URL and key name. |
| Server URL prompted interactively on first run | Users don't know to pass `--server` on first use. | LOW | `axiom-push init` prompts "Server URL [https://localhost:443]:" with a sensible default. Saves to `~/.axiom/config.json`. |
| Key already-registered check before generating | Users who run `init` twice should not get duplicate key errors. | LOW | Check existing key on server before generating. If registered: "Key already registered — skipping." |
| Actionable error messages for auth failures | Expired JWT, wrong server URL, 401 — these must tell the user what to do next, not just print a status code. | LOW | "Authentication failed. Your session may have expired. Run `axiom-push login` to re-authenticate." |
| `axiom-push sign-and-push` (combined command) | After init, the repetitive sign+push is the daily-use pattern. A combined command reduces friction. | LOW | Thin wrapper: runs `sign` then `push`. Accepts same args as `push`. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `axiom-push status` — health check command | Shows: logged-in as X, server Y, key registered (yes/no), licence state. Answers "am I set up correctly?" in one command. | LOW | High value for support/debugging. Reduces "why isn't it working?" tickets. |
| Progress indicators during sign+push | Large scripts can be slow. Silent tools feel broken. | LOW | Use `rich` (already likely a dep) or plain stderr progress. "Signing... done. Pushing... done." |
| Config file at `~/.axiom/config.json` with documented format | Enables scripting and CI/CD use. | LOW | Document schema in CLI `--help` output and in docs. Fields: `server_url`, `key_id`, `token_path`. |
| `--dry-run` flag on push | CI/CD pipelines need to validate without executing. | LOW | Validate signature and server reachability but do not submit job. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-generate and auto-upload key without user consent | "Zero config" | Private key generated silently with no user awareness violates principle of least surprise for a security tool. | Interactive prompt: "Generate a new signing key? [Y/n]". One prompt. Not five. |
| Separate `login`, `keygen`, `upload-key`, `sign`, `push` commands as the documented "getting started" | Granular control | Too many steps for first use. Users abandon. | Keep all sub-commands, but document `init` and `sign-and-push` as the happy path. Advanced users discover the rest. |
| Keychain/OS credential store integration in v1 | Looks like polish | Platform-specific bugs, complex to test, adds dependencies. | Store token in `~/.axiom/token` (600 permissions). Document clearly. Keychain integration is a v2 item. |

---

## Feature Dependencies

```
[Marketing Homepage]
    requires existing --> [MkDocs docs site at github.io] (already built — v14.2)
    blocks on        --> [30-min install path] (Sub-Domain C must be complete first)
    references       --> [CE vs EE table] (licence system already built — v14.3)

[Licence Banner]
    requires         --> [GET /api/licence endpoint] (already built — v14.3)
    requires         --> [useLicence hook] (already built — used in Admin.tsx)
    requires         --> [authenticated layout wrapper] (already built — MainLayout.tsx)
    enhances         --> [Admin LicenceSection deep-link] (already exists)
    no blockers      --> can ship independently

[Clean Install Docs]
    blocks           --> [Marketing Homepage 30-min claim] (cannot make the claim until the path is real)
    requires         --> [compose.cold-start.yaml refactor] (code change, not just docs)
    requires         --> [axiom-push init] (Sub-Domain D, for the CLI tab in install docs)

[axiom-push init / sign-and-push]
    requires         --> [OAuth device flow] (already built — v8.0)
    requires         --> [key upload API] (already built)
    blocks           --> [Clean Install Docs CLI tab] (can't document a command that doesn't exist)
```

### Dependency Notes

- **Licence banner has zero blocking dependencies.** It can be built and shipped independently of everything else. It is the lowest-risk item in this milestone.
- **axiom-push init must land before the install docs rewrite.** The CLI tab in `enroll-node.md` documents `axiom-push init` — the command must exist before the docs reference it.
- **Clean install docs must land before the marketing homepage 30-min claim.** Do not add "up and running in 30 minutes" to the homepage until the actual path is verified to take 30 minutes.
- **Phase ordering implied:** Licence banner (parallel, unblocked) → axiom-push CLI → install docs → marketing homepage.

---

## MVP Definition

### Launch With (v1 — this milestone)

- [ ] **Licence state banner** — amber (GRACE) and red (EXPIRED/DEGRADED_CE), admin-only, persistent, with days-remaining and deep-link CTA. Backend is ready; this is a pure frontend task.
- [ ] **axiom-push init command** — chains login + keygen + key upload into one interactive command. Reduces first-user abandonment at the most critical funnel step.
- [ ] **sign-and-push combined command** — thin daily-use wrapper. Trivial to implement once `init` exists.
- [ ] **Clean compose.cold-start.yaml** — test nodes removed or separated. Single most confusing thing for first users today.
- [ ] **Docs rewrite matching clean compose** — `install.md` and `enroll-node.md` updated to match the new node-free cold start. Includes prerequisite callout and expected-state checkpoints.
- [ ] **Marketing homepage** — static `index.html` on GitHub Pages (separate from `/docs/`). Hero, security positioning, CE/EE table, link to docs. Unblocked only after clean install path exists.

### Add After Validation (v1.x)

- [ ] **axiom-push status command** — useful but not blocking first-use. Add when support questions reveal "am I set up?" confusion.
- [ ] **Troubleshooting accordion in install docs** — add based on actual first-user failure modes observed after launch.
- [ ] **Changelog/release signal on homepage** — add once release cadence is established and signals "active project".

### Future Consideration (v2+)

- [ ] **OS keychain credential storage in axiom-push** — complex, platform-specific. Plain file with 600 permissions is sufficient for v1.
- [ ] **Animated terminal demo on homepage** — high maintenance. Only if a stable, auto-updating mechanism exists.
- [ ] **Video walkthrough** — high production cost. Deferred until content is stable.
- [ ] **Testimonials section on homepage** — only when 2–3 real, attributed quotes exist.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Licence state banner (amber/red) | HIGH | LOW — backend ready, pure frontend | P1 |
| axiom-push init | HIGH — removes biggest abandonment point | MEDIUM — chains 3 existing operations | P1 |
| sign-and-push combined command | MEDIUM — daily-use convenience | LOW — thin wrapper | P1 |
| Clean compose.cold-start.yaml (no test nodes) | HIGH — eliminates first-user confusion | LOW — restructure one file | P1 |
| Docs rewrite (install + enroll-node) | HIGH — must match new compose | MEDIUM — rewrite, not edit | P1 |
| Marketing homepage | HIGH — acquisition surface | MEDIUM — static HTML/CSS, 6 sections | P2 |
| axiom-push status | MEDIUM — debugging aid | LOW | P2 |
| Troubleshooting accordion in install docs | MEDIUM — reduces abandonment | MEDIUM — need real failure data first | P2 |
| Homepage changelog signal | LOW | LOW | P3 |
| Homepage testimonials | HIGH (if real) / LOW (if fake) | LOW | P3 |

**Priority key:**
- P1: Must have for this milestone — directly unblocks first-user success
- P2: Should have — add when P1 items are stable
- P3: Nice to have — future consideration

---

## Competitor Feature Analysis

| Feature | Temporal (job scheduler) | Rundeck | Our Approach |
|---------|--------------------------|---------|--------------|
| Marketing homepage | Polished site, feature matrix, pricing | Enterprise marketing site, demo CTA | Minimal static page on GitHub Pages — honest, fast, security-focused |
| Licence banner | N/A (OSS) | Trial expiry modal (blocks UI) | Non-blocking top banner, admin-only, role-gated |
| Install docs | Single Docker command, no test infra bundled | Complex installer | Two-file compose (server / node separate), .env defaults, no bundled test nodes |
| CLI signing UX | No signing concept | No signing concept | `axiom-push init` as single onboarding command, `sign-and-push` for daily use |

---

## Sources

- Evil Martians: "We studied 100 dev tool landing pages — here's what actually works in 2025" — https://evilmartians.com/chronicles/we-studied-100-devtool-landing-pages-here-is-what-actually-works-in-2025
- Lucas F. Costa: "UX patterns for CLI tools" — https://www.lucasfcosta.com/blog/ux-patterns-cli-tools
- Notification banner severity patterns (Astro UX DS) — https://www.astrouxds.com/components/notification-banner/
- Smashing Magazine: "Design Guidelines For Better Notifications UX" (2025) — https://www.smashingmagazine.com/2025/07/design-guidelines-better-notifications-ux/
- Docker Compose official quickstart — https://docs.docker.com/compose/gettingstarted/
- Postman Onboarding Teardown: "7 UX Moves Every Dev Tool Should Copy" — https://www.candu.ai/blog/postman-onboarding-ux-lessons
- Project context: `.planning/PROJECT.md` (v14.3 validated features)

---
*Feature research for: Axiom go-to-market polish milestone*
*Researched: 2026-03-27*
