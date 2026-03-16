# Pitfalls Research

**Domain:** Enterprise documentation — adding MkDocs Material to an existing Docker Compose / FastAPI / security-focused orchestration stack
**Researched:** 2026-03-16
**Confidence:** HIGH (codebase directly inspected; Caddyfile, compose.server.yaml, and existing docs/ tree examined; MkDocs Material official docs and GitHub issues verified)

---

## Critical Pitfalls

### Pitfall 1: Running `mkdocs serve` in Production

**What goes wrong:**
The MkDocs development server (`mkdocs serve`) is used as the container entrypoint in production. This is the single most widely documented MkDocs Docker mistake. The development server is not designed for production: it does not handle concurrent connections well, has no access controls, no gzip, no proper HTTP/1.1 keep-alive handling, and exposes internal filesystem paths in error messages.

**Why it happens:**
Developers prototype with `mkdocs serve` locally and copy the same Docker command into the compose file. Official MkDocs Material GitHub issue #1825 and #2168 both document that the official image is explicitly scoped to "local preview only." The container starts, docs look fine on first check, and no one revisits it.

**How to avoid:**
Use a two-stage Docker build: stage 1 runs `mkdocs build` to produce `site/` static HTML; stage 2 copies `site/` into an Nginx or Caddy static file server. The docs Containerfile should look like:

```dockerfile
FROM squidfunk/mkdocs-material:9 AS builder
WORKDIR /docs
COPY . .
RUN mkdocs build --strict

FROM caddy:2-alpine
COPY --from=builder /docs/site /srv
COPY Caddyfile /etc/caddy/Caddyfile
```

The `--strict` flag during build causes MkDocs to fail on broken internal links, missing nav entries, and undefined macros — this turns silent content problems into build failures before they reach production.

**Warning signs:**
- `CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8000"]` in the docs Containerfile
- No separate `build` stage in the Dockerfile
- Container logs show `Serving on http://0.0.0.0:8000` (mkdocs dev server banner)

**Phase to address:** Container infrastructure phase (first phase — get the build right before writing a word of content)

---

### Pitfall 2: OpenAPI Snapshot Drift — Generated Docs Diverge From Live API

**What goes wrong:**
The API reference is generated from a snapshot of `/openapi.json` committed to the docs repository. Over time, routes are added to `agent_service/main.py`, models change in `models.py`, and response schemas evolve — but the committed JSON snapshot is never updated. The published API reference describes endpoints that no longer exist and omits new ones. Operators trying to build integrations against the docs get 404s or wrong schemas.

**Why it happens:**
OpenAPI generation is a manual step ("run `curl localhost:8001/openapi.json > docs/api/openapi.json`"), not an automated one. It requires the service to be running, which is awkward in CI. The initial generation looks complete, so no one adds it to the build pipeline.

**How to avoid:**
Automate the OpenAPI snapshot as part of the docs build, not as a manual step. In the docs `Containerfile` or CI script:

```bash
# Start a lightweight instance of agent_service
python -m agent_service.main &
sleep 3
curl -f http://localhost:8001/openapi.json -o docs/api/openapi.json
kill %1
```

Alternatively: FastAPI's `app.openapi()` can be called directly in a Python script that imports the app without starting a server — this is the most reliable approach and works without a running HTTP server:

```python
# scripts/export_openapi.py
from agent_service.main import app
import json
print(json.dumps(app.openapi()))
```

Run this script in the docs build step. Any time a route is added but the doc build is not re-run, the snapshot is stale — make the build fail if the committed `openapi.json` differs from the generated one (`git diff --exit-code`).

**Warning signs:**
- `openapi.json` in the repo has a `info.version` that doesn't match the current codebase version
- New routes in `main.py` are not reflected in the committed `openapi.json`
- No CI step runs `export_openapi.py` before building docs

**Phase to address:** API reference phase — define the generation pipeline before writing any API docs prose

---

### Pitfall 3: Caddy Path Routing Conflict — `/docs` Swallowed by Dashboard Fallback

**What goes wrong:**
The docs container is added to `compose.server.yaml` and a `/docs` route is added to the Caddyfile. But the existing Caddyfile ends with `handle { reverse_proxy dashboard:80 }` — a catch-all that handles every path not matched by earlier rules. In Caddy, `handle` blocks are evaluated in order, but a wildcard `handle` at the bottom catches everything that is not an exact prefix match. If the `/docs` handler is placed after the catch-all (a common copy-paste error), or if a path stripping mistake sends `/docs/` with a trailing slash that doesn't match `/docs*`, requests hit the dashboard instead of the docs container. The failure mode is silent: users see the dashboard, not a 404, so the routing error is invisible.

**Why it happens:**
The Caddyfile already has a working pattern for `/api/*` and `/auth/*` with `uri strip_prefix`. Copy-pasting this pattern for `/docs` strips the prefix but the docs container expects to serve from the root (`/`), so all asset references in the generated HTML (`/assets/`, `/stylesheets/`) become relative to the wrong root and 404. The correct approach depends on whether the docs site is built to serve at a subpath or at root.

**How to avoid:**
Two clean options:

**Option A — Subpath-aware MkDocs build (recommended):** Set `site_url: https://your-domain/docs/` in `mkdocs.yml` and use `use_directory_urls: true`. Then in the Caddyfile, proxy with the prefix intact:

```caddyfile
handle /docs* {
    reverse_proxy docs:80
}
```

The docs container receives `/docs/...` paths and serves them correctly because the site was built with that base URL.

**Option B — Root-mount with prefix stripping:** Build MkDocs at root (`site_url: /`), strip the prefix in Caddy (`uri strip_prefix /docs`), and rely on the docs container serving from `/`. This works but breaks all absolute asset URLs (`/assets/...`) unless MkDocs is configured with `use_directory_urls: false` and relative links only — which is fragile.

Option A is the correct choice. Always set `site_url` explicitly in `mkdocs.yml` to match the subpath.

**Warning signs:**
- CSS/JS assets 404 after proxying (browser dev tools show `/assets/stylesheets/main.css` returning 404)
- Navigating to `/docs/` works but internal page links redirect to `/` (the dashboard)
- `handle /docs*` block appears after the catch-all `handle {}` in the Caddyfile

**Phase to address:** Container infrastructure phase — test routing before any content is written

---

### Pitfall 4: Docs Content That Is Accurate at Write Time But Stale By Launch

**What goes wrong:**
Documentation is written during a milestone and describes the system as it was when the docs were written. By the time the milestone ships, code has changed: route paths renamed, env variable names updated, default values changed. The docs are 100% accurate about a system that no longer exists. This is especially acute for security/infra tools where operators rely on exact env var names and exact API paths.

**Why it happens:**
Docs are treated as a discrete task ("write the docs in phase N") rather than as a living artifact updated alongside code. For a fast-moving codebase, any doc written more than a few days before it is reviewed against the current code is likely to contain at least one stale reference.

**How to avoid:**
- Docs must be reviewed against the live codebase on the same day they are merged, not when they were written.
- Embed code references in docs where possible: use the `pymdownx.snippets` extension to pull actual code blocks from source files directly into docs. If the source changes, the snippet changes automatically.
- For env variables: maintain a single source-of-truth env var reference table (in code comments or a `config.py` docstring), and pull it into docs via snippets or a Jinja macro. Never duplicate env var names as freestanding prose.
- For API endpoints: use OpenAPI-generated reference, not hand-written endpoint lists.

**Warning signs:**
- Docs reference `AGENT_URL` but the code uses a different variable name
- Route documented as `GET /admin/audit-log` but the actual route is different
- "Last reviewed" date is more than 1 sprint old

**Phase to address:** Every content phase — enforce a "review against live code" gate before merging any doc PR

---

### Pitfall 5: Missing Documentation for the Security Model's Hard Requirements

**What goes wrong:**
Security/infra tools fail users not because the docs are wrong, but because they omit the hard requirements that operators must satisfy. For Master of Puppets specifically: operators deploy nodes without knowing they must install the Root CA, without knowing that join tokens expire, without understanding that `mop-push` must sign locally (the private key cannot be uploaded). The node silently fails mTLS handshake, the join token is rejected with a generic 403, and the operator has no path to diagnosis.

**Why it happens:**
Developers know the security model intimately and don't document the "obvious" constraints. The constraints feel self-evident to the author but are invisible to a first-time operator. This is the most common reason infrastructure tool docs fail enterprise users: missing prerequisites and error diagnosis paths.

**How to avoid:**
For every security-relevant operation, document in this order:
1. Prerequisites (what must be true before you start)
2. The operation itself
3. How to verify it succeeded
4. What the most common failure looks like and how to diagnose it

Specific content required for Master of Puppets that cannot be omitted:
- Root CA installation on operator workstations and nodes (Linux, macOS, Windows, NSS for Firefox/Chrome)
- join token format, expiry behaviour, and what a stale token looks like
- Ed25519 key generation: `admin_signer.py --generate`, where keys are stored, why the private key must never be uploaded
- mTLS failure symptoms (TLS handshake errors, certificate verify failed) and their causes
- cert rotation procedure: what breaks, in what order, and how to recover

**Warning signs:**
- Getting started guide jumps from "deploy the stack" to "add a node" without a CA installation step
- No error diagnosis section in any runbook
- Security guide exists but contains no troubleshooting content

**Phase to address:** Security & compliance guide phase — treat this as the highest-priority content category

---

### Pitfall 6: Plugin Dependencies Not Pinned in the Docs Container Image

**What goes wrong:**
The `docs/requirements.txt` (or the `pip install` in the Containerfile) specifies MkDocs Material and plugins without version pins. A build six months from now pulls a breaking release of `mkdocs-material`, `pymdownx`, or a rendering plugin. The CI build starts failing with cryptic Python tracebacks. Worse: the site builds but renders incorrectly because a plugin's output format changed.

**Why it happens:**
Documentation infrastructure is treated as less critical than application code. Version pins feel like maintenance overhead for "just a docs site." The MkDocs Material changelog includes breaking changes between minor versions that affect theme configuration keys and plugin APIs.

**How to avoid:**
Pin every dependency in `docs/requirements.txt` to an exact version (`==`), not a range. Use `pip-compile` (pip-tools) to generate a lock file from a `requirements.in`. Separate the docs requirements from the application `requirements.txt` — they should never share a file.

```
# docs/requirements.in
mkdocs-material>=9.0
pymdownx>=10.0
mkdocs-minify-plugin
neoteroi-mkdocs
```

Generate locked: `pip-compile docs/requirements.in -o docs/requirements.txt`

Rebuild the lock file intentionally, not automatically. Treat docs dependency updates as deliberate choices.

**Warning signs:**
- `docs/requirements.txt` contains `mkdocs-material` with no version pin or only `>=`
- No `requirements.in` / `requirements.txt` split
- Docs container uses `pip install mkdocs-material` in the Containerfile with no version

**Phase to address:** Container infrastructure phase

---

### Pitfall 7: Navigation Architecture That Does Not Match User Mental Models

**What goes wrong:**
The MkDocs nav is organised by system component ("Foundry," "Smelter," "OAuth") rather than by what users need to accomplish ("Get started," "Run your first job," "Set up a node"). Component-oriented navigation makes perfect sense to developers who built each component in isolation. It fails enterprise operators who need to accomplish tasks that span multiple components. A user who wants to schedule a recurring job needs to read: Job Definitions (scheduler), mop-push (CLI), Ed25519 signing (security), Staging view (dashboard) — but each lives in a different section with no cross-linking.

**Why it happens:**
Documentation structure mirrors the codebase structure, because the same people who built the code also wrote the docs. This is the most common structural failure mode in infrastructure tool documentation (confirmed by multiple SRE post-mortems on internal tooling docs).

**How to avoid:**
Structure the top-level navigation by audience and task, not by component:

```
- Getting Started (E2E first-run walkthrough for new operators)
- User Guides (task-oriented: "Schedule a job," "Enroll a node," "Build a custom image")
- Feature Reference (component-oriented: Foundry, Smelter, OAuth, Staging)
- Security & Compliance (security model, cert management, RBAC config)
- API Reference (generated from OpenAPI)
- Runbooks & Troubleshooting (by symptom, not by component)
```

Getting Started must link forward to relevant Feature Reference and Security sections. Every Feature Reference page must link to the relevant Runbook for failure cases.

**Warning signs:**
- Nav top level is: Foundry, Smelter, OAuth, Staging, Nodes, Jobs (component-by-component)
- No "Getting Started" section that works end-to-end without jumping between sections
- Troubleshooting is scattered across feature pages instead of consolidated

**Phase to address:** Getting started guide phase — establish the nav architecture before any other content is written

---

### Pitfall 8: Dashboard "Docs" Link Opens New Tab to Dead URL

**What goes wrong:**
The existing `Docs.tsx` in-app docs view is replaced with a link to the docs container. The link is hardcoded to `http://localhost:8080/docs` (or a relative path) that works in the developer's local environment but is wrong in production (different hostname, different port, different TLS state). The dashboard "Documentation" nav item silently opens to an error page for every production user.

**Why it happens:**
The dashboard and docs are now separate containers with potentially different access URLs. The developer who wires the link uses their local URL because it works in local testing. In production, behind Caddy, the docs are at `https://your-domain/docs/`. These are different URLs and the hardcoded one is always wrong for someone.

**How to avoid:**
Make the docs URL configurable via a `VITE_DOCS_URL` environment variable in `dashboard/.env.*`. Default to `/docs/` (relative path, which works whether Caddy proxies at the same domain or not). Do not hardcode a port or hostname. In `AppRoutes.tsx` or wherever the link is placed, use `import.meta.env.VITE_DOCS_URL ?? '/docs/'`.

**Warning signs:**
- `Docs.tsx` or the nav link contains `localhost:8080` or any hardcoded port
- No `VITE_DOCS_URL` variable in `dashboard/.env.example`
- The link works in dev but has not been tested on the production Caddy-proxied stack

**Phase to address:** Dashboard integration phase

---

### Pitfall 9: Security-Sensitive Information in Publicly Accessible Docs

**What goes wrong:**
The docs are intended for internal operators but end up served without authentication on a route that is exposed to the internet (via Cloudflare Tunnel, which routes all traffic at `dev.master-of-puppets.work`). The security & compliance guide contains the exact format of `JOIN_TOKEN`, the CA certificate fingerprint format, details of the mTLS handshake that could assist an attacker enumerating the system, and troubleshooting guidance that reveals internal IP ranges or hostnames.

**Why it happens:**
Documentation is assumed to be "non-sensitive" because it describes a system rather than containing credentials. For a security-hardened orchestration platform, detailed architectural documentation (cert formats, token schemas, internal routing) provides material intelligence for an attacker who wants to target the system.

**How to avoid:**
The docs container should be behind the same Caddy/Cloudflare Access authentication as the dashboard. The existing Cloudflare Access service token (CF-Access-Client-Id + CF-Access-Client-Secret) already protects the tunnel. Verify that `/docs*` is included in the Cloudflare Access policy, not excluded.

If the docs must be partially public (e.g., getting started guide is public, security internals are private), use MkDocs Material's `tags` plugin to mark pages as internal, and serve them at a separate path that is gated by Cloudflare Access rules.

Do not include in any publicly accessible doc page:
- Internal IP ranges or hostname patterns
- CA fingerprint format + example values (these help attackers craft fake certs)
- Full JOIN_TOKEN schema with example values
- Any credential format + example

**Warning signs:**
- Caddy `/docs*` route does not require authentication
- Security guide contains a "full example" of a JOIN_TOKEN with all fields populated
- The Cloudflare Tunnel config does not list `/docs*` as a protected path

**Phase to address:** Container infrastructure phase AND security guide phase

---

### Pitfall 10: `mkdocs build --strict` Broken Links Not Treated as Blocking

**What goes wrong:**
MkDocs builds successfully with broken internal links when `--strict` is not set. The published docs contain links to pages that don't exist yet ("coming soon" stubs), cross-references to anchors that were renamed, and relative links that work locally but break when served at a subpath. Users click links and get 404s in the docs — which is worse than having no docs, because it signals an abandoned or untrusted source.

**Why it happens:**
Content is written incrementally, with stub pages as placeholders. `--strict` is not added to the build command because it prevents the build from succeeding while stubs exist. The compromise ("I'll fix the links later") becomes permanent.

**How to avoid:**
Use `--strict` from the first build. For pages not yet written, use MkDocs Material's `status: stub` page metadata (supported natively) rather than empty placeholder pages — this renders a visible "in progress" banner without creating broken links. Never link forward to pages that do not exist. If a feature guide doesn't exist yet, do not link to it from the navigation.

```yaml
# In a stub page's front matter:
---
status: stub
---
```

This keeps `--strict` passing while communicating to users that the page is in progress.

**Warning signs:**
- `mkdocs build` runs without `--strict` flag
- Pages in `nav:` in `mkdocs.yml` that don't exist in `docs/`
- Links to `#anchors` that were renamed (most common after a heading is reformatted)

**Phase to address:** Container infrastructure phase — enforce `--strict` from the beginning

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `mkdocs serve` as the container entrypoint | No Dockerfile complexity | Not production-safe; no caching, no gzip, no concurrent connections | Never — two-stage build is 10 extra lines |
| OpenAPI JSON committed as a static snapshot | No automation required | Diverges from live API within weeks; operators build against wrong schemas | Never for an actively developed API |
| MkDocs plugin versions unpinned | Less maintenance | Breaking plugin releases break the docs build silently | Only in throwaway internal preview; never in production docs |
| Nav structured by component not by task | Mirrors codebase structure | Operators can't find anything by task; docs feel developer-internal | Never — task-oriented nav must be the top level even if component pages exist underneath |
| Docs URL hardcoded in dashboard | Works in dev immediately | Wrong in every other environment | Never — takes 5 minutes to make it env-configurable |
| No `--strict` on `mkdocs build` | Build succeeds with stub pages | Broken links accumulate; users lose trust in docs | Never — use `status: stub` front matter instead |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Caddy + MkDocs subpath | Use `uri strip_prefix /docs` and expect assets to work | Set `site_url: https://domain/docs/` in `mkdocs.yml`; proxy without stripping prefix |
| FastAPI OpenAPI export | `curl /openapi.json` requires a running server in CI | Import `app.openapi()` directly from a Python script; no server needed |
| Cloudflare Tunnel + docs | Add `/docs*` route but forget to add it to CF Access policy | Verify Access policy covers `/docs*`; test from a browser not in CF Access session |
| Dashboard Docs link | Hardcode `localhost:8080/docs` from local testing | Use `VITE_DOCS_URL` env var defaulting to `/docs/` (relative) |
| MkDocs Material + Caddy static files | Serve `site/` directly without setting correct MIME types | Use Caddy or Nginx to serve `site/` — they set MIME types correctly; never use Python's `http.server` |
| `pymdownx.snippets` + code pulled from source | Snippet paths are relative to `docs_dir` by default | Set `base_path` in snippets config to repo root; verify snippet paths survive a rename |

---

## Performance Traps

For docs at the scale of Master of Puppets (dozens of pages, one team), performance is not a concern at runtime. All risks are at build time.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `mkdocs build` re-runs OpenAPI export on every build | Slow CI; export fails if agent service not available | Cache `openapi.json` in CI; only regenerate on `main.py`/`models.py` changes | Immediately in CI if service isn't running |
| MkDocs social plugin generates OG images on every build | Build takes 3-5 minutes | Disable social plugin in CI builds; only enable for production build | Any CI pipeline with frequent doc changes |
| Large video/image assets committed to `docs/` git tree | Repo clone time grows; Docker build context is huge | Store large assets in a volume or CDN; only commit small screenshots | When assets exceed ~10 MB total |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Docs served unauthenticated via Cloudflare Tunnel | Security architecture details (cert formats, token schemas, internal routing) exposed publicly | Add `/docs*` to Cloudflare Access policy same as dashboard |
| JOIN_TOKEN full schema with example values in public docs | Assists attacker crafting enrollment tokens or understanding trust boundaries | Document schema abstractly; never include example values with real structure |
| Docs container mounts Docker socket or any application volume | Docs container has no legitimate reason for host access; reduces isolation | Docs container should have zero volume mounts except the static `site/` directory |
| Internal hostnames / IP ranges appear in troubleshooting examples | Leaks network topology | Use placeholder hostnames (`orchestrator.internal`, `10.0.x.x`) in all examples |
| mTLS troubleshooting guide shows exact cipher suite + certificate field details | Provides enumeration assistance | Describe symptoms and resolution steps; omit specific cipher names and field paths |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Getting started requires jumping between 5 separate doc sections | Operator gives up before first successful node enrollment | Single linear walkthrough: install → deploy stack → install CA → enroll node → run job — all on one long page with section anchors |
| API reference is just a rendered OpenAPI spec with no usage examples | Developers can see the schema but don't know how to chain calls | Each API section includes a minimal `curl` example showing authentication and a realistic payload |
| Troubleshooting organised by feature (Foundry issues, OAuth issues) | Operator sees symptom ("403 on /work/pull"), has to know which feature caused it | Troubleshooting organised by symptom/error message, not by feature |
| Runbooks describe what to do but not what went wrong | Operator follows steps without understanding; can't adapt when steps fail | Each runbook opens with a 2-sentence root cause explanation before the recovery steps |
| Security guide is a feature list, not a threat model | Operator knows what features exist but not what risks they mitigate | Security guide opens with "what attacks does this prevent and how" before listing configuration steps |
| Code examples use `admin` credentials | Operator copy-pastes admin credentials into their own scripts | Always use a service principal with minimum permissions in examples; show how to create it |

---

## "Looks Done But Isn't" Checklist

- [ ] **Container build:** `mkdocs build --strict` passes with zero warnings before the image is tagged for production. Run it — don't assume.
- [ ] **Caddy routing:** Navigate to `/docs/`, `/docs/getting-started/`, and a deep asset URL (`/docs/assets/stylesheets/main.css`) in a browser against the actual production Caddy stack, not a local dev server.
- [ ] **OpenAPI sync:** After adding a new route to `main.py`, run the OpenAPI export script and confirm the committed `openapi.json` diff shows the new route. Then run `mkdocs build` and confirm the API reference page shows the new route.
- [ ] **Dashboard Docs link:** Click the Docs nav item in the production dashboard. Confirm it opens the docs container, not the old in-app markdown renderer.
- [ ] **Auth gate:** Open `/docs/` in a private browser window not in a Cloudflare Access session. Confirm it prompts for access, not displays content.
- [ ] **Getting started completeness:** Follow the getting started guide on a fresh machine (or fresh LXC container using the existing `manage-test-nodes` skill) with zero prior knowledge. Every step must succeed without external context.
- [ ] **Security guide prerequisites:** Every security procedure in the guide lists its prerequisites. Test the CA installation procedure on a machine that has not previously installed the CA.
- [ ] **No hardcoded localhost:** Grep the docs source for `localhost`, `127.0.0.1`, `8001`, `8000`, `8080`. Any hit that isn't inside a code example marked as "local dev only" is a bug.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `mkdocs serve` in production discovered post-launch | LOW | Replace container entrypoint with two-stage Nginx/Caddy build. Rebuild image. No content change needed. |
| OpenAPI snapshot is 2 months stale | MEDIUM | Run `export_openapi.py` against the live API, commit the diff, review all changed endpoints to verify prose docs are still accurate, update prose where needed. |
| Caddy routing strips prefix, breaking all asset URLs | LOW | Add `site_url` to `mkdocs.yml`, rebuild docs image, update Caddyfile to not strip prefix. Test routing after each change. |
| Docs served publicly without auth | HIGH | Add Cloudflare Access policy for `/docs*` immediately. Audit Cloudflare Access logs to see if unauthenticated access occurred. Rotate any credentials or token schemas documented in detail. |
| Getting started guide does not work end-to-end | MEDIUM | Follow the guide on a fresh LXC node (use `manage-test-nodes` skill), document every point of failure, fix each issue before re-testing. Never publish "working on it" placeholders — use `status: stub`. |
| Nav structure makes docs unusable | HIGH | Restructure nav in `mkdocs.yml` (no content changes required). Add redirects for any external links that pointed to old paths. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| `mkdocs serve` in production | Phase 1: Container infrastructure | Confirm Containerfile uses two-stage build with Nginx/Caddy static serving |
| OpenAPI snapshot drift | Phase 2: API reference generation pipeline | Confirm `export_openapi.py` runs in CI and `git diff --exit-code` guards committed JSON |
| Caddy prefix routing + asset 404s | Phase 1: Container infrastructure | Navigate deep asset URLs in production Caddy stack before writing content |
| Stale docs at launch | All content phases | "Review against live code" gate on every doc PR |
| Missing security prerequisites | Phase 5: Security & compliance guide | Walk through guide on fresh machine; every step must succeed without prior knowledge |
| Unpinned plugin versions | Phase 1: Container infrastructure | `requirements.txt` uses `==` pins; `pip-compile` lock file committed |
| Component-oriented nav | Phase 3: Getting started guide | Top-level nav is task/audience oriented; getting started is a single linear walkthrough |
| Hardcoded docs URL in dashboard | Phase 4: Dashboard integration | `VITE_DOCS_URL` env var used; tested in production Caddy stack |
| Docs served unauthenticated | Phase 1: Container infrastructure | Verify CF Access policy covers `/docs*`; test from unauthenticated browser |
| Broken internal links | All content phases | `mkdocs build --strict` is required step; build fails on broken links |
| Security-sensitive content in public docs | Phase 5: Security & compliance guide | Security review before merge: no example token values, no internal hostnames, no cipher details |

---

## Sources

- MkDocs Material GitHub issue #1825 — official image not suitable for production deployment: https://github.com/squidfunk/mkdocs-material/issues/1825
- MkDocs Material GitHub issue #2168 — Docker serve limitations: https://github.com/squidfunk/mkdocs-material/issues/2168
- MkDocs Material installation docs — plugin support and custom Dockerfiles: https://squidfunk.github.io/mkdocs-material/getting-started/
- Neoteroi MkDocs OpenAPI plugin: https://www.neoteroi.dev/mkdocs-plugins/web/oad/
- MkDocs community — how to build API reference docs (GitHub issue #641): https://github.com/mkdocs/mkdocs/issues/641
- Caddy as Docker Compose reverse proxy — networking pitfalls: https://blog.wirelessmoves.com/2025/06/caddy-as-a-docker-compose-reverse-proxy.html
- Platform engineering anti-patterns — documentation staleness: https://jellyfish.co/library/platform-engineering/anti-patterns/
- Best practices for technical documentation 2025: https://www.llmoutrank.com/blog/best-practices-for-technical-documentation
- Direct codebase inspection: `puppeteer/cert-manager/Caddyfile`, `puppeteer/compose.server.yaml`, `docs/` tree, `puppeteer/dashboard/src/views/`
- Existing docs tree shows: `docs/security.md`, `docs/security_signatures.md`, `docs/API_REFERENCE.md`, `docs/INSTALL.md` — content exists but not yet in MkDocs format

---
*Pitfalls research for: Master of Puppets v9.0 — adding enterprise MkDocs documentation to existing Docker Compose stack*
*Researched: 2026-03-16*
