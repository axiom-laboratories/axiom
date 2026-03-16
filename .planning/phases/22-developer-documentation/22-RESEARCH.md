# Phase 22: Developer Documentation - Research

**Researched:** 2026-03-16
**Domain:** Technical documentation authoring — MkDocs Material, Mermaid diagrams, Black/Ruff tooling config
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Legacy content cleanup**
- Write all three guides fresh from scratch — do not port content from old files
- Delete all old documentation files in this phase (not deferred):
  - `docs/architecture.md`, `docs/INSTALL.md`, `docs/deployment_guide.md`, `docs/SDK_GUIDE.md`, `docs/UserGuide.md`, `docs/scheduling.md`, `docs/security.md`, `docs/security_signatures.md`, `docs/ssl_guide.md`, `docs/compatibility.md`, `docs/REMOTE_DEPLOYMENT.md`, `docs/third_party_audit_report.md`
  - `puppeteer/docs/` directory and all its contents
- The new MkDocs site (`docs/docs/`) is the canonical and sole documentation location

**MkDocs nav placement**
- All three guides go under a `Developer` section in `mkdocs.yml` nav
- Consistent with the audience-oriented nav structure established in STATE.md
- Nav entry: `Developer:` → `Architecture`, `Setup & Deployment`, `Contributing`

**Architecture guide — full technical deep-dive**
- Level of detail: Full technical deep-dive (not a high-level overview)
- Diagrams: 4+ Mermaid diagrams — minimum: system overview, mTLS enrollment sequence, job execution data flow, at least one more (DB schema, RBAC model, or Foundry build flow)
- Topics to cover:
  - All services explained: agent_service, model_service (scheduler), job_service, foundry_service, scheduler_service, pki_service, signature_service — what each does
  - DB schema / data model: key tables and relationships (Job, Node, ScheduledJob, PuppetTemplate, Blueprint, etc.)
  - Security model deep-dive: mTLS cert lifecycle, Ed25519 signing chain, RBAC permission model, JWT + token versioning, Fernet encryption at rest
  - Foundry & Smelter: image build pipeline, blueprint/template model, CVE scanning, BOM, image lifecycle enforcement

**Setup & deployment guide — operator-first**
- Structure: Operator path first (Docker Compose production), then local dev section
- Quick start block: 5-command runnable block at the very top — gets anyone to a running stack without reading further
- Env vars documentation: Document ALL required env vars (SECRET_KEY, ENCRYPTION_KEY, ADMIN_PASSWORD, DATABASE_URL, API_KEY, etc.) with placeholder example values + note on how to generate secure values; docs are behind CF Access so this is safe
- TLS bootstrap: Brief coverage — where to find JOIN_TOKEN in dashboard, how to set AGENT_URL on a node; deep cert rotation/revocation lives in Phase 24 Security guide (link to it)
- DEVDOC-02 success criterion: A developer following this guide on a clean machine can reach a running local stack (SQLite + backend + dashboard) without consulting the codebase

**Contributing guide — explicit PR bar**
- Tests required to merge: Both must pass:
  - Backend: `cd puppeteer && pytest` — clean run
  - Frontend: `cd puppeteer/dashboard && npm run test` — clean run
  - No numeric coverage threshold — green is the bar
- Code style:
  - Python: Black (formatting) + Ruff (linting)
  - Frontend: ESLint (`npm run lint`) — already configured
  - Add `pyproject.toml` with Black + Ruff config to the repo as part of this phase
- Database migration pattern: Dedicated section — "No Alembic: adding DB columns requires a `migration_vN.sql` file with `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements; `create_all` will NOT alter existing tables on existing deployments"
- DEVDOC-03 success criterion: Guide specifies exactly how to run tests and what a passing PR requires

### Claude's Discretion
- Exact Mermaid diagram syntax and styling
- Section ordering within each guide beyond the structural decisions above
- Tone and formatting conventions (consistent with MkDocs Material best practices)
- Which additional diagram(s) beyond the 3 required ones to include (DB schema, RBAC, or Foundry flow)
- `pyproject.toml` Ruff rule selection (sensible defaults, not overly strict)

### Deferred Ideas (OUT OF SCOPE)
- Reformatting existing Python codebase with Black + Ruff — Phase 22 adds the config files and documents the standard; actually running `black .` and `ruff --fix .` on all existing code is a separate housekeeping task (future phase or standalone task)
- All other legacy doc content (security guides, feature guides, runbooks) — covered by Phases 23-25
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEVDOC-01 | Architecture guide documents all system components, security model, and data flow (with Mermaid diagrams) | Mermaid syntax verified via MkDocs Material docs; all service/DB/security details extracted from codebase |
| DEVDOC-02 | Setup & deployment guide covers local dev, Docker Compose, production deployment, env vars, TLS bootstrap | All env vars catalogued from security.py, auth.py, node.py, compose.server.yaml; local dev commands verified from CLAUDE.md |
| DEVDOC-03 | Contributing guide covers code structure, testing conventions, and PR workflow | pytest + vitest confirmed as test runners; pyproject.toml does not exist yet (must be created); Black+Ruff standard documented |
</phase_requirements>

---

## Summary

Phase 22 is a content-authoring phase: write three markdown guides in `docs/docs/developer/`, update `docs/mkdocs.yml` with a `Developer:` nav section, create `puppeteer/pyproject.toml` with Black + Ruff configuration, and delete all legacy documentation files. The MkDocs infrastructure (Material 9.7.5, privacy+offline plugins, nginx, Docker two-stage build) is fully operational from Phase 20 — this phase adds content only.

The most significant technical consideration is Mermaid diagram rendering. MkDocs Material 9.7.5 supports Mermaid natively via `pymdownx.superfences`, but the combination of the `privacy` plugin (which downloads external assets at build time) and Mermaid's CDN dependency means the builder stage needs internet access during `mkdocs build`. The Dockerfile already runs the builder stage with internet access, so this is not a problem — but the `mkdocs.yml` needs a `markdown_extensions` block added for Mermaid to work at all. Without it, Mermaid code blocks will render as plain text.

The codebase is well-understood. All architecture content needed for the guides already exists in the source code: service implementations, DB models, security/PKI logic, compose files, and env var references are all directly readable. No guessing is required.

**Primary recommendation:** Add `pymdownx.superfences` with the Mermaid custom fence to `mkdocs.yml`, create the `docs/docs/developer/` subdirectory with three new markdown files, update the nav, create `puppeteer/pyproject.toml`, and delete the listed legacy files.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| MkDocs Material | 9.7.5 (pinned in docs/requirements.txt) | Documentation site framework | Already installed and operational from Phase 20 |
| pymdownx.superfences | bundled with Material | Mermaid diagram rendering | Official Material Mermaid integration — no additional pip package needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| black | latest (unpinned) | Python formatter | Added to pyproject.toml, run in dev workflow |
| ruff | latest (unpinned) | Python linter | Added to pyproject.toml, run in dev workflow |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pymdownx.superfences (native Material) | mkdocs-mermaid2-plugin | Native integration requires zero extra packages; mermaid2 plugin is a separate PyPI package and has known issues with the privacy plugin |

### Installation

No new pip packages needed for Mermaid — only mkdocs.yml configuration changes. For pyproject.toml tooling:

```bash
pip install black ruff
```

---

## Architecture Patterns

### Recommended Project Structure for Phase Deliverables

```
docs/
├── mkdocs.yml                    # Add nav: section + markdown_extensions for Mermaid
└── docs/
    ├── index.md                  # UNTOUCHED (placeholder)
    ├── api-reference/            # UNTOUCHED (Phase 21)
    └── developer/                # NEW — create this directory
        ├── architecture.md       # DEVDOC-01
        ├── setup-deployment.md   # DEVDOC-02
        └── contributing.md       # DEVDOC-03

puppeteer/
└── pyproject.toml                # NEW — Black + Ruff config (DEVDOC-03 dependency)

docs/ (root-level legacy files to DELETE):
  architecture.md, INSTALL.md, deployment_guide.md, SDK_GUIDE.md,
  UserGuide.md, scheduling.md, security.md, security_signatures.md,
  ssl_guide.md, compatibility.md, REMOTE_DEPLOYMENT.md,
  third_party_audit_report.md, WEBHOOKS.md (also present)

puppeteer/docs/                   # DIRECTORY to DELETE
```

### Pattern 1: Enabling Mermaid in MkDocs Material

**What:** Adding `pymdownx.superfences` with a custom fence definition to `mkdocs.yml` enables Mermaid JS diagrams that render in the browser. Material auto-injects the Mermaid JS loader when a page contains a `mermaid` code fence.

**When to use:** Any `mkdocs.yml` that needs Mermaid diagrams.

**Configuration to add to `docs/mkdocs.yml`:**
```yaml
markdown_extensions:
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
```

**Privacy plugin interaction:** MkDocs Material auto-fetches `mermaid.min.js` from unpkg.com during the `mkdocs build` step and bundles it locally (via the privacy plugin). This requires outbound internet access at build time — which is already true in the Dockerfile builder stage. At runtime (nginx), no external calls are made. This is the correct behavior for an air-gapped deployment.

**Mermaid syntax in markdown:**
```markdown
```mermaid
graph LR
    A[Puppeteer] -->|mTLS| B[Puppet Node]
```
```

Source: [Material for MkDocs — Diagrams](https://squidfunk.github.io/mkdocs-material/reference/diagrams/)

### Pattern 2: MkDocs nav Section Structure

**What:** The `nav:` key in `mkdocs.yml` defines the sidebar structure. Each top-level key is a section header; nested keys are page links.

**Configuration for this phase:**
```yaml
nav:
  - Home: index.md
  - Developer:
    - Architecture: developer/architecture.md
    - Setup & Deployment: developer/setup-deployment.md
    - Contributing: developer/contributing.md
  - API Reference:
    - Overview: api-reference/index.md
```

Note: Phases 23-25 will add `Getting Started`, `Feature Guides`, `Security`, and `Runbooks` sections. This nav will expand. Adding a partial nav now is safe — additional sections are appended later.

**Critical:** `mkdocs build --strict` is enforced. Every file listed in `nav:` must exist on disk. Create the markdown files before or in the same task that updates the nav.

### Pattern 3: pyproject.toml Black + Ruff Configuration

**What:** A minimal `pyproject.toml` in `puppeteer/` that configures Black (formatter) and Ruff (linter). This is not a full `setup.py` replacement — just the tool configuration stanza.

**Recommended configuration:**
```toml
[tool.black]
line-length = 88
target-version = ["py312"]

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["agent_service", "model_service"]
```

Rules chosen: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `W` (pycodestyle warnings). `E501` (line-too-long) is ignored because Black handles line length — dual enforcement creates noise. This is "sensible defaults, not overly strict" per the locked decision.

Source: [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/)

### Anti-Patterns to Avoid

- **Listing files in nav: before they exist on disk:** `mkdocs build --strict` will fail the Docker build. Create files first.
- **Using `mkdocs serve` in documentation about production deployment:** The Dockerfile uses nginx — `mkdocs serve` is not production-safe (known upstream issue #1825). The setup guide must only reference the Docker compose path for production.
- **Referencing external CDN assets in Mermaid or other extensions:** The privacy + offline plugins must handle asset bundling at build time. Never add `<script src="https://unpkg.com/...">` to markdown content.
- **Running `black .` or `ruff --fix .` on the existing codebase in this phase:** Explicitly deferred. Only add the config file and document the standard.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mermaid rendering | Custom JS injection, custom HTML templates | `pymdownx.superfences` native Material integration | Material handles CDN bundling, theming, dark/light mode automatically |
| Python linting config | Per-file flake8 comments, custom lint scripts | `pyproject.toml` with Ruff | Ruff is 10-100x faster than flake8; pyproject.toml is the standard PEP 518 location |
| DB diagram | Manual ASCII tables, custom SVGs | Mermaid `erDiagram` syntax | Rendered from code, version-controllable, auto-styled by Material |

**Key insight:** All tooling infrastructure for this phase is already in place. The work is writing accurate content, not configuring infrastructure.

---

## Common Pitfalls

### Pitfall 1: Mermaid Code Fences Not Rendering

**What goes wrong:** The `mermaid` code fence renders as a styled code block with syntax highlighting rather than a diagram.

**Why it happens:** `pymdownx.superfences` with `custom_fences` is not configured in `mkdocs.yml`. Without it, MkDocs treats ` ```mermaid ` as a regular code block.

**How to avoid:** Add the `markdown_extensions` block (Pattern 1 above) to `mkdocs.yml` before writing any content that uses Mermaid. Verify in the Docker build that the output HTML contains `<div class="mermaid">` not `<code class="language-mermaid">`.

**Warning signs:** During `mkdocs build`, no errors are raised — but the rendered HTML has `<code>` tags instead of `<div class="mermaid">`.

### Pitfall 2: mkdocs build --strict Fails on New Files

**What goes wrong:** The Docker build fails because a file referenced in `nav:` in `mkdocs.yml` does not exist yet, or a markdown file has a broken internal link.

**Why it happens:** `--strict` mode treats all MkDocs warnings as errors. The most common triggers: (a) file in nav not on disk, (b) `[link text](non-existent-file.md)` internal link, (c) anchor reference `#section-name` that doesn't match any heading.

**How to avoid:** Create the target markdown files and the nav entry in the same task/commit. Test anchor links carefully — MkDocs slugifies heading text with lowercase and hyphens.

**Warning signs:** Docker build log shows `WARNING - Documentation file 'developer/architecture.md' is not found` followed by build failure.

### Pitfall 3: Legacy Files Not Deleted Before Strict Build

**What goes wrong:** Legacy markdown files in `docs/` root (e.g., `docs/architecture.md`) are orphaned — they exist on disk but are not in `nav:`. In strict mode, MkDocs warns about files not included in the nav.

**Why it happens:** Phase 20 established that all content goes in `docs/docs/`. Legacy files in `docs/` root (not `docs/docs/`) are not actually part of the MkDocs source tree — MkDocs only processes files under `docs_dir` (which is `docs/docs/`). So the files in `docs/*.md` are actually outside MkDocs' scope and won't trigger strict build failures. **However**, the CONTEXT.md decision is to delete them anyway for canonical clarity.

**How to avoid:** Delete legacy files as a dedicated task. They are outside `docs_dir` so deletion does not risk breaking the build. Confirm `docs_dir` is `docs/docs/` (default) or explicitly set in `mkdocs.yml`.

**Warning signs:** Not a build failure risk, but a content maintenance risk — someone following an old link finds stale content.

### Pitfall 4: Architecture Guide Omitting the model_service

**What goes wrong:** The architecture guide mentions `agent_service` but omits `model_service` (the APScheduler-backed scheduling service running on port 8000).

**Why it happens:** `model_service` is a separate process from `agent_service` in `compose.server.yaml` — it runs as `uvicorn model_service.main:app --host 0.0.0.0 --port 8000`. It is easy to focus only on `agent_service` since that's the primary API surface.

**How to avoid:** The architecture guide must cover both services. From `compose.server.yaml`: `agent` (port 8001) = control plane API + PKI + job dispatch + WebSocket; `model` (port 8000) = APScheduler integration, cron job execution.

### Pitfall 5: Incorrect Local Dev Quick-Start Commands

**What goes wrong:** The setup guide documents commands that work in Docker but fail in a clean local Python environment (e.g., missing `aiosqlite` for SQLite, missing `API_KEY` env var causing `sys.exit(1)`).

**Why it happens:** `security.py` has `sys.exit(1)` at module-level import if `API_KEY` is not set. `requirements.txt` does not include `aiosqlite` (it's only added in the Dockerfile `RUN pip install ...` line). A developer running `python -m agent_service.main` locally with SQLite will hit both of these.

**How to avoid:** The setup guide must document minimum required env vars for local dev:
```bash
export API_KEY=dev-key
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```
And note that local dev with SQLite requires `pip install aiosqlite` in addition to `requirements.txt`.

---

## Code Examples

### Mermaid System Overview Diagram (Starting Point)

```mermaid
graph TB
    subgraph Puppeteer ["Puppeteer (Control Plane)"]
        A[agent_service :8001]
        M[model_service :8000]
        DB[(PostgreSQL / SQLite)]
        DASH[React Dashboard :5173]
        A <--> DB
        M <--> DB
        DASH --> A
    end
    subgraph Puppet ["Puppet Node (Worker)"]
        N[environment_service/node.py]
        R[runtime.py]
        N --> R
    end
    N -->|"mTLS client cert\nPOLL /work/pull"| A
    N -->|"POST /heartbeat"| A
    A -->|"WorkResponse\n(signed script + limits)"| N
    N -->|"POST /work/result"| A
```

### Mermaid mTLS Enrollment Sequence

```mermaid
sequenceDiagram
    participant N as Puppet Node
    participant P as Puppeteer (agent_service)
    participant CA as Internal Root CA

    N->>N: Decode JOIN_TOKEN (base64 JSON → root CA PEM)
    N->>N: Write root CA to disk (trust anchor)
    N->>N: Generate RSA keypair + CSR
    N->>P: POST /api/enroll {csr_pem, hostname, machine_id, node_secret}
    P->>CA: sign_csr(csr_pem, hostname)
    CA-->>P: client_cert.pem
    P->>P: Store client_cert_pem in Node DB row
    P-->>N: {client_cert, node_id}
    N->>N: Write cert + key to secrets/node-{id}.crt/.key
    Note over N,P: Subsequent requests use mTLS (client cert presented)
```

### Mermaid Job Execution Data Flow

```mermaid
sequenceDiagram
    participant OP as Operator
    participant D as Dashboard
    participant A as agent_service
    participant N as Puppet Node
    participant R as runtime.py

    OP->>D: Dispatch job (script + signature)
    D->>A: POST /jobs {payload, signature_payload}
    A->>A: Verify Ed25519 signature
    A->>A: Insert Job (PENDING) into DB
    loop Poll every N seconds
        N->>A: POST /work/pull (mTLS)
        A->>A: Match job to node (tags, capabilities, memory)
        A-->>N: WorkResponse {script, signature, memory_limit}
    end
    N->>N: Verify Ed25519 signature (refuse if invalid)
    N->>R: run(script, memory_limit, cpu_limit)
    R-->>N: {stdout, stderr, exit_code}
    N->>A: POST /work/result {guid, status, output}
    A->>A: Update Job (COMPLETED), write ExecutionRecord
    A->>D: WebSocket push (job update)
```

### pyproject.toml (Complete Content)

```toml
[tool.black]
line-length = 88
target-version = ["py312"]

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["agent_service", "model_service"]
```

Source: [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/), verified against [Ruff settings reference](https://docs.astral.sh/ruff/settings/)

---

## Codebase Facts for Documentation Authors

These facts are required content for the three guides and were verified directly from the source code.

### Services Inventory (`puppeteer/agent_service/services/`)

| Service | File | Purpose |
|---------|------|---------|
| job_service | job_service.py | Job assignment, node selection, heartbeat processing, capability matching, execution records |
| foundry_service | foundry_service.py | Docker image builds from templates + blueprints; Smelter enforcement; semaphore (max 2 concurrent builds) |
| scheduler_service | scheduler_service.py | APScheduler integration (AsyncIOScheduler); job definition CRUD; cron job dispatch; stats/history pruning |
| signature_service | signature_service.py | Ed25519 public key storage + signature verification |
| pki_service | pki_service.py | PKI lifecycle helpers (wraps pki.py CertificateAuthority) |
| smelter_service | smelter_service.py | Approved ingredient registry; validates blueprints against allowlist; enforcement mode (STRICT/WARNING) |
| vault_service | vault_service.py | Binary artifact storage with SHA-256 hashing; used for CapabilityMatrix injection files |
| alert_service | alert_service.py | Alerting for job failures, node offline, security tamper events |
| webhook_service | webhook_service.py | HMAC-signed outbound webhook delivery |
| trigger_service | trigger_service.py | Webhook-triggered job dispatch (slug + secret token) |
| mirror_service | mirror_service.py | PyPI/APT mirror management for air-gap builds |
| staging_service | staging_service.py | Job definition staging + approval workflow |

### DB Tables (from db.py)

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| jobs | guid, task_type, payload, status, node_id, result, target_tags, capability_requirements, memory_limit, cpu_limit, max_retries, depends_on | Job queue |
| nodes | node_id, hostname, ip, last_seen, status, capabilities, concurrency_limit, job_memory_limit, client_cert_pem, template_id | Enrolled puppet nodes |
| node_stats | id, node_id, recorded_at, cpu, ram | Time-series CPU/RAM per heartbeat (pruned to last 60) |
| scheduled_jobs | id, name, script_content, signature_id, schedule_cron, target_tags, capability_requirements, is_active | Cron job definitions |
| signatures | id, name, public_key (PEM), uploaded_by | Ed25519 signing keys |
| users | username, password_hash, role, must_change_password, token_version | User accounts |
| user_signing_keys | id, username, name, public_key_pem, encrypted_private_key | Per-user Ed25519 keys |
| user_api_keys | id, username, name, key_hash, key_prefix, permissions, expires_at | API key auth |
| service_principals | id, name, role, client_id, client_secret_hash, is_active | Machine-to-machine auth |
| role_permissions | id, role, permission | RBAC permission grants (UniqueConstraint role+permission) |
| blueprints | id, type (RUNTIME/NETWORK), name, definition (JSON), os_family | Foundry build ingredients |
| puppet_templates | id, friendly_name, runtime_blueprint_id, network_blueprint_id, canonical_id, current_image_uri, last_built_at, is_compliant | Foundry templates |
| capability_matrix | id, base_os_family, tool_id, injection_recipe (Dockerfile snippet), validation_cmd | Foundry capability injection registry |
| approved_ingredients | id, name, version_constraint, sha256, os_family, mirror_status | Smelter allowlist |
| artifacts | id, filename, sha256, size_bytes | Binary artifact vault |
| audit_log | id, timestamp, username, action, resource_id, detail | Security audit trail |
| revoked_certs | serial_number, node_id, revoked_at | CRL backing store |
| execution_records | id, job_guid, node_id, status, exit_code, started_at, completed_at, output_log, truncated | Per-execution stdout/stderr |
| triggers | id, slug, name, job_definition_id, secret_token, is_active | Webhook-triggered job dispatch |
| signals | name, payload | Async signal bus |
| alerts | id, type, severity, message, resource_id, acknowledged | Alert state |
| webhooks | id, url, secret (HMAC), events, active | Outbound webhook config |
| tokens | token, used, template_id | One-use enrollment tokens |
| config | key, value | System configuration KV store |
| approved_os | id, name, image_uri, os_family | Approved base OS list for Foundry |

### Required Environment Variables (for Setup Guide)

| Variable | Service | Required? | Purpose | How to Generate |
|----------|---------|-----------|---------|-----------------|
| `API_KEY` | agent_service | **REQUIRED** (sys.exit if missing) | Legacy shared API key; used by nodes | Any random string; `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | agent_service | Required (auto-generates if missing, not stable) | Fernet key for job secrets at rest | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SECRET_KEY` | agent_service | Recommended (defaults to weak dev value) | JWT signing key | `openssl rand -hex 32` |
| `ADMIN_PASSWORD` | agent_service | Recommended (random if unset, logged) | Initial admin user password | Any secure password |
| `DATABASE_URL` | agent_service, model_service | Optional (defaults to SQLite) | DB connection; SQLite for dev, Postgres for prod | `postgresql+asyncpg://user:pass@host/db` |
| `AGENT_URL` | model_service, puppet nodes | Required for nodes | URL nodes use to reach agent_service | `https://<host-ip>:8001` |
| `CLOUDFLARE_TUNNEL_TOKEN` | compose tunnel service | Only if using CF tunnel | Cloudflare tunnel credentials | From CF dashboard |
| `DUCKDNS_TOKEN`, `DUCKDNS_DOMAIN` | cert-manager | Only if using DuckDNS | Dynamic DNS | From DuckDNS dashboard |

### Local Dev Gotchas (Critical for DEVDOC-02)

1. `aiosqlite` is NOT in `requirements.txt` but is required for SQLite local dev. Install separately: `pip install aiosqlite`
2. `API_KEY` env var must be set before import — `security.py` calls `sys.exit(1)` at module level if missing
3. Frontend dev server (`npm run dev`) proxies `/api` to `https://localhost:8001` per `.env.development` — the backend must be running with TLS or the proxy must be adjusted for plain HTTP local dev

### Migration Pattern (Critical for DEVDOC-03)

- No Alembic. `Base.metadata.create_all` runs at startup but only creates new tables — it will NOT alter existing tables.
- Adding columns to an existing deployment: create a `migration_vN.sql` file with `ALTER TABLE x ADD COLUMN IF NOT EXISTS y TYPE;`
- Current migration files exist up to `migration_v31.sql` in `puppeteer/`
- Fresh deployments: `create_all` handles schema creation entirely — no migrations needed

### Docker Services Summary (for Setup Guide)

From `compose.server.yaml`:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| db | postgres:15-alpine | 5432 | Primary database |
| cert-manager | local build | 80, 8443 | Caddy reverse proxy + TLS termination |
| agent | local build | 8001 | Control plane API (FastAPI) |
| model | local build | (internal) | APScheduler + cron job service |
| dashboard | local build | (via Caddy) | React SPA |
| docs | local build | (via Caddy at /docs/) | MkDocs static site |
| registry | registry:2 | 5000 | Local Docker registry for Foundry |
| pypi | pypiserver | 8080 | Local PyPI mirror |
| mirror | caddy | 8081 | APT mirror proxy |
| tunnel | cloudflare/cloudflared | (outbound) | Cloudflare tunnel |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline Mermaid via separate `mkdocs-mermaid2` plugin | `pymdownx.superfences` native Material integration | Material 8.x+ | Zero extra packages; privacy plugin handles CDN bundling |
| flake8 + isort + pyupgrade (separate tools) | Ruff (single tool, replaces all three) | 2023+ | 10-100x faster; single config block |
| `setup.cfg` for tool config | `pyproject.toml` (PEP 518 standard) | 2021+ | Standard location recognized by all modern tools |

**Deprecated/outdated:**
- `mkdocs-mermaid2-plugin`: Superseded by native Material integration for Material 8+. Do not add this to `docs/requirements.txt`.
- `mkdocs serve` for production: Not safe (GitHub issue #1825). Dockerfile already uses nginx correctly.

---

## Open Questions

1. **WEBHOOKS.md in docs/ root**
   - What we know: `docs/WEBHOOKS.md` exists alongside the listed legacy files but is NOT in the deletion list in CONTEXT.md
   - What's unclear: Was it intentionally omitted from the deletion list, or was it overlooked?
   - Recommendation: Delete it in 22-01 (architecture task) alongside the other legacy files. It is outside MkDocs' docs_dir, it's legacy content, and the canonical location is `docs/docs/`. If the planner wants to preserve it, a note should be added to the plan.

2. **pymdownx.superfences package availability**
   - What we know: `mkdocs-material==9.7.5` is pinned. `pymdownx.superfences` is part of `pymdown-extensions` which is a transitive dependency of mkdocs-material.
   - What's unclear: Whether `pymdown-extensions` is explicitly installed or only transitively present.
   - Recommendation: Add `pymdownx.superfences` configuration to `mkdocs.yml` — if the package is missing, `mkdocs build` will fail with a clear error during the Docker build, making it immediately detectable. In practice, `pymdown-extensions` is always installed with Material.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest (version from requirements.txt; no version pin) |
| Framework (frontend) | vitest 3.0.5 (pinned in package.json) |
| Config file (backend) | None — pytest discovers tests automatically |
| Config file (frontend) | `puppeteer/dashboard/vitest.config.ts` |
| Quick run command (backend) | `cd puppeteer && pytest tests/ -x -q` |
| Quick run command (frontend) | `cd puppeteer/dashboard && npm run test -- --run` |
| Full suite command (backend) | `cd puppeteer && pytest` |
| Full suite command (frontend) | `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map

This phase is documentation-only. The deliverables are markdown files, a `pyproject.toml`, nav updates, and file deletions. There are no code paths to unit test.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEVDOC-01 | Architecture guide renders Mermaid diagrams | smoke | `docker build -f docs/Dockerfile .` — build succeeds with Mermaid config | ❌ Wave 0 (Docker build is the test) |
| DEVDOC-02 | Setup guide covers all required env vars | manual | Review guide against env var table above | N/A |
| DEVDOC-03 | Contributing guide specifies test commands and migration pattern | manual | Review guide for required sections | N/A |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/ -x -q` (backend) + `cd puppeteer/dashboard && npm run test -- --run` (frontend) — verify no regressions from file deletions
- **Per wave merge:** Full suite: `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test`
- **Phase gate:** Full suite green + `docker build -f docs/Dockerfile .` succeeds before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `docs/Dockerfile` build test — the primary validation for DEVDOC-01 is that `mkdocs build --strict` succeeds with Mermaid config. No new test file needed; the Docker build IS the test.
- [ ] No pytest or vitest gaps introduced by this phase. Existing test infrastructure covers all code.

*(The phase has no new Python or TypeScript code — no new unit tests are needed.)*

---

## Sources

### Primary (HIGH confidence)
- MkDocs Material official docs — [Diagrams reference](https://squidfunk.github.io/mkdocs-material/reference/diagrams/) — Mermaid + superfences configuration verified
- Project source code (direct read) — `puppeteer/agent_service/db.py`, `security.py`, `auth.py`, `pki.py`, `main.py`, all services — all architecture content
- Project source code (direct read) — `puppeteer/compose.server.yaml` — service inventory, env vars, ports
- Project source code (direct read) — `docs/requirements.txt`, `docs/mkdocs.yml`, `docs/Dockerfile` — MkDocs version, plugin config, build process
- [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/) — pyproject.toml patterns verified

### Secondary (MEDIUM confidence)
- [MkDocs Material privacy plugin docs](https://squidfunk.github.io/mkdocs-material/plugins/privacy/) — Mermaid CDN bundling behavior at build time
- [GitHub issue #3742 — Mermaid + privacy plugin](https://github.com/squidfunk/mkdocs-material/issues/3742) — Known interaction; builder-stage internet access is the correct mitigation

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — MkDocs Material 9.7.5 already operational; Mermaid config from official docs; Ruff from official docs
- Architecture content: HIGH — extracted directly from source code, not inferred
- Pitfalls: HIGH for Mermaid rendering and strict build (verified via official docs and issue tracker); MEDIUM for local dev gotchas (verified from source, not end-to-end tested)

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable stack — MkDocs Material and Ruff config patterns are stable)
