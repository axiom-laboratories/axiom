# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Developer Profile (auto-generated 2026-04-19)

| Dimension | Rating | Confidence |
|-----------|--------|------------|
| Communication Style | conversational | HIGH |
| Decision Speed | deliberate-informed | HIGH |
| Explanation Depth | concise | MEDIUM |
| Debugging Approach | diagnostic | MEDIUM |
| UX Philosophy | function-first | MEDIUM |
| Vendor Philosophy | pragmatic-fast | MEDIUM |
| Frustration Triggers | instruction-adherence | LOW |
| Learning Style | guided | MEDIUM |

**Key instructions for Claude:**
- Match conversational tone; mix imperatives with questions that invite input
- Offer Gemini second-opinion recommendations for significant architectural decisions
- Keep explanations concise — focus on what changed and why, skip basics
- Debug diagnostically: share root cause, help form hypotheses collaboratively
- Prioritize function over polish; treat docs/UI as deliverables not afterthoughts
- Suggest pragmatic tool choices based on LOE, not exhaustive comparison
- Respect explicit scope boundaries; follow instructions precisely
- Explain concepts conversationally with concrete examples rather than linking to docs

Full profile: `~/.claude/get-shit-done/USER-PROFILE.md` · Refresh: `/gsd-profile-user --refresh`

## Workflow Rules

- Always run discuss-phase before plan-phase to ensure CONTEXT.md exists. Never attempt plan-phase without first checking for the phase's CONTEXT.md file.

## Workflow Execution

- During execution phases, run autonomously to completion without pausing for user input on setup tasks. If a prerequisite (e.g., devpi setup, token creation) is needed, attempt it or document it as a manual step — do not block the workflow waiting for the user.
- After completing each plan's implementation, spawn a verification agent that: 1) runs the full test suite, 2) checks all API endpoints mentioned in the plan return 200, 3) verifies all UI components render correctly via Playwright against the Docker stack. Report any failures before marking the plan complete.

## Testing

- Never use local dev servers (npm dev, Vite dev server, Cloudflare tunnels) for testing. Always rebuild and test inside the Docker stack containers.

### Playwright Testing

- **MCP browser is broken in this environment** — the `@playwright/mcp` plugin crashes on every navigation (`Target page, context or browser has been closed`). Use Python Playwright directly instead.
- **Python Playwright requires `--no-sandbox`** — always launch with `args=['--no-sandbox']`, otherwise Chrome crashes on Linux. Working invocation: `p.chromium.launch(args=['--no-sandbox'], headless=True)`.
- **Auth: inject JWT via localStorage, don't use the login form** — React controlled inputs don't respond reliably to Playwright `fill()`. Instead: get a token from the API, then `page.evaluate(f"localStorage.setItem('mop_auth_token', '{token}')")` before navigating to the target route.
- **API login uses form-encoded data, not JSON** — `requests.post(url, data={...})` not `json={...}`. The FastAPI OAuth2 endpoint requires `application/x-www-form-urlencoded`.
- **localStorage key is `mop_auth_token`** — not `token` or `auth_token`.
- **Don't check `textarea count == 0` to verify guided form** — the guided dispatch form itself has textareas (Script field, Signature field). After resetting from Advanced mode, check for the `[ADV]` button and guided-mode controls (e.g. Python/Any node buttons) instead.

## General Rules

- When running scans or batch operations, always scope to relevant source directories only. Exclude venvs, node_modules, .git, generated/build dirs, and any gitignored paths.

## Commands

### Backend (FastAPI)
```bash
# Install dependencies
pip install -r puppeteer/requirements.txt

# Run backend locally (from puppeteer/)
python -m agent_service.main

# Run all backend tests
cd puppeteer && pytest

# Run a single test file
cd puppeteer && pytest tests/test_tools.py

# Run the full stack (production-like)
cd puppeteer && docker compose -f compose.server.yaml up -d

# Rebuild the agent image after code changes
docker compose -f puppeteer/compose.server.yaml build agent
docker compose -f puppeteer/compose.server.yaml up -d --no-build agent
```

### Frontend (React/Vite)
```bash
cd puppeteer/dashboard

# Install dependencies
npm install

# Dev server (proxies /api to https://localhost:8001 per .env.development)
npm run dev

# Production build
npm run build

# Lint
npm run lint

# Run all tests (vitest)
npm run test

# Run a single test file
npx vitest run src/views/__tests__/JobDefinitions.test.tsx
```

### Node (Puppet Agent)
```bash
# Deploy a node using the node compose file
cd puppets && docker compose -f node-compose.yaml up -d

# Build the node image
docker build -t localhost/master-of-puppets-node:latest -f puppets/Containerfile.node puppets/
```

## Architecture

### Three-Component System

```
Puppeteer (Control Plane)     ←── mTLS ──→   Puppet Nodes
  ├── Agent Service (8001)                       └── environment_service/node.py
  ├── Model Service (8000)                            (polls /work/pull every N sec)
  ├── PostgreSQL DB
  └── React Dashboard (5173 dev / Caddy prod)
```

**Puppeteer** (`puppeteer/`) is the server-side control plane. All state lives here.

**Puppet** (`puppets/environment_service/`) is the stateless worker agent. It:
1. Decodes `JOIN_TOKEN` to trust the Root CA
2. Generates a CSR and gets a client cert signed at `/api/enroll`
3. Polls `/work/pull` every few seconds for assigned jobs
4. Executes jobs via `runtime.py` and reports results back

The **pull model** means nodes initiate all connections — no inbound firewall rules needed on nodes.

### Backend Code Layout

| File | Purpose |
|------|---------|
| `puppeteer/agent_service/main.py` | All FastAPI route handlers, lifespan/startup logic, WebSocket |
| `puppeteer/agent_service/db.py` | SQLAlchemy ORM models + `init_db()` (uses `create_all`) |
| `puppeteer/agent_service/models.py` | Pydantic request/response models |
| `puppeteer/agent_service/auth.py` | JWT creation/verification, bcrypt password hashing |
| `puppeteer/agent_service/security.py` | API key validation, cert verification, Fernet encryption |
| `puppeteer/agent_service/pki.py` | Root CA and client cert signing (cryptography lib) |
| `puppeteer/agent_service/services/job_service.py` | Job assignment, node selection, heartbeat processing, capability matching |
| `puppeteer/agent_service/services/foundry_service.py` | Docker image builds from templates + blueprints |
| `puppeteer/agent_service/services/scheduler_service.py` | APScheduler integration, job definition CRUD |
| `puppeteer/agent_service/services/signature_service.py` | Ed25519 public key storage + signature verification |
| `puppeteer/agent_service/services/pki_service.py` | PKI lifecycle helpers |

### Frontend Code Layout

Views are in `puppeteer/dashboard/src/views/`. Each view is a self-contained page:
- `Dashboard.tsx` — summary metrics
- `Nodes.tsx` — live node monitoring with sparkline charts (recharts)
- `Jobs.tsx` — job queue dispatch and status
- `JobDefinitions.tsx` — cron-scheduled job definitions
- `Templates.tsx` — Foundry: Docker image templates + blueprints
- `Signatures.tsx` — Ed25519 public key management
- `Users.tsx` — user/role management + `MyAccount` (self-service password change)
- `AuditLog.tsx` — security audit trail
- `Admin.tsx` — system configuration
- `Docs.tsx` — in-app documentation (renders markdown)

All authenticated API calls go through `authenticatedFetch()` in `src/auth.ts`, which injects the JWT from `localStorage` and redirects to `/login` on 401.

WebSocket live updates: `src/hooks/useWebSocket.ts` — connects to `/ws?token=<jwt>`, auto-reconnects with exponential backoff.

### Auth & RBAC

Three roles: `admin`, `operator`, `viewer`. Permissions are stored per-role in the `role_permissions` DB table and seeded at startup. Admin bypasses all permission checks.

Route protection pattern:
```python
# In main.py — require a specific permission
async def some_route(current_user = Depends(require_permission("jobs:write"))):
```

Node-facing endpoints (`/api/enroll`, `/work/pull`, `/heartbeat`) are **unauthenticated** — they use mTLS client certs instead.

JWT includes a `tv` (token version) field. Any password change increments `User.token_version`, instantly invalidating all prior sessions.

### Database

- **Local dev**: SQLite (`jobs.db`) — set by default if `DATABASE_URL` env var is absent
- **Production**: PostgreSQL 15 via `DATABASE_URL=postgresql+asyncpg://...`
- Schema is managed by **Alembic** (`puppeteer/agent_service/migrations/`). `Base.metadata.create_all` still runs at startup as a safety net but Alembic is the source of truth.
- Baseline migration: `001_baseline_schema.py`. All future schema changes get a new numbered migration (`002_...`, `003_...`).
- Legacy `migration_*.sql` files were removed in Phase 164-03 — do not create new `.sql` migration files.
- Run migrations: `cd puppeteer && alembic upgrade head`

### Security Model

- **mTLS**: Nodes enroll using a `JOIN_TOKEN` (base64 JSON containing the Root CA PEM). After enrollment they hold a signed client cert. Revoked certs are tracked in `RevokedCert` table and served as a CRL at `GET /system/crl.pem`.
- **Job signing**: All job scripts must be signed with an Ed25519 key whose public key is registered in `signatures`. Nodes verify the signature before executing.
- **Secrets**: Fernet (AES-128) encrypted in the DB. `ENCRYPTION_KEY` env var required in production.
- **JWT Secret**: `SECRET_KEY` env var (defaults to a weak dev value — always override in production).

### Foundry (Docker Image Builder)

Foundry builds custom node images from:
1. **Blueprints** (`blueprints` table): runtime or network definitions (JSON). Packages must use `{"python": [...]}` dict format.
2. **Templates** (`puppet_templates` table): combine a runtime blueprint + network blueprint into a Docker image.

Build process (`foundry_service.py`): copies `puppets/environment_service/` into a temp dir, generates a Dockerfile from capability matrix injection recipes, then runs `docker build` via the mounted Docker socket.

### Node Execution Modes

`puppets/environment_service/runtime.py` reads `EXECUTION_MODE` env var. All modes execute jobs in ephemeral containers for security isolation.
- `auto` — detects Docker or Podman at runtime (default)
- `docker` / `podman` — explicit container runtime

**Deprecated:** `EXECUTION_MODE=direct` (Python subprocess execution) is no longer supported as of v20.0. For Docker-in-Docker scenarios, mount the host Docker socket and use `EXECUTION_MODE=docker` or `auto`. See [FAQ → RuntimeError: No container runtime found](docs/docs/runbooks/faq.md) for guidance.

### Configuration

Puppeteer server reads from `puppeteer/.env` (or `secrets.env` for sensitive values like `ADMIN_PASSWORD`). Key variables:

| Variable | Purpose |
|----------|---------|
| `ADMIN_PASSWORD` | Initial admin password (if unset, a random one is generated) |
| `API_KEY` | Shared key for legacy API key auth |
| `ENCRYPTION_KEY` | Fernet key for secrets at rest |
| `SECRET_KEY` | JWT signing key |
| `DATABASE_URL` | Postgres connection string |

Dashboard dev server reads `puppeteer/dashboard/.env.development` — defaults `VITE_API_URL=https://localhost:8001`.

## Known Deferred Issues

See `.agent/reports/core-pipeline-gaps.md` for full details. Deferred items: MIN-6 (SQLite `NodeStats` pruning compat), MIN-7 (foundry build dir cleanup), MIN-8 (per-request DB query in `require_permission`), WARN-8 (non-deterministic node ID scan order).

## Sister Repositories

### `~/Development/mop_validation`
Validation, diagnostics, and development tooling that is kept **separate from the main repo** to avoid cluttering it with test infrastructure.

| Directory | Contents |
|-----------|---------|
| `scripts/` | E2E and integration tests (`test_local_stack.py`, `test_playwright.py`, sprint-specific tests), deployment helpers, key generation, node validation |
| `diagnostics/` | Cluster health checks, SSL debugging, dashboard smoke tests |
| `dev_tools/` | Remote deployment scripts, Docker socket fixers, credential testers |
| `local_nodes/` | Docker Compose configs for local test nodes (`node_alpha`, `node_beta`, `node_gamma`, `node_1`, `node_2`) |
| `reports/` | Output directory for skill review reports (backend, security, frontend, QA, etc.) |
| `docs/` | Feature planning docs, roadmaps, user guides |

`secrets.env` at the root of `mop_validation` holds credentials used by the test scripts (same format as the main repo's `secrets.env`).

Key scripts to know:
```bash
# Full local stack validation (API-level)
python ~/Development/mop_validation/scripts/test_local_stack.py

# Full E2E Playwright UI test
python ~/Development/mop_validation/scripts/test_playwright.py

# Generate and upload a signing key
python ~/Development/mop_validation/scripts/generate_signing_key.py

# Submit a signed job
python ~/Development/mop_validation/scripts/run_signed_job.py
```

### `~/Development/toms_home`
Personal agent tooling — rules, skills, workflows, and admin tools that apply across projects.

```
toms_home/.agents/
  rules/       # Coding standards and architectural constraints
  skills/      # Specialized review/planning capabilities (each has a SKILL.md)
  workflows/   # Multi-step agentic workflows (full_audit, self_healing_quality_loop, etc.)
  tools/       # Admin utilities (Ed25519 key gen + job signing)
```

**Skills** (in `.agents/skills/`) — invoke by name to get a focused review or plan:

| Skill | Purpose |
|-------|---------|
| `review-security` | Vulnerability scan — output → `mop_validation/reports/security_review.md` |
| `review-backend` | FastAPI/async architecture review → `reports/backend_review.md` |
| `review-frontend` | React patterns and bundle review → `reports/frontend_review.md` |
| `review-frontend-functional` | Functional correctness of UI flows |
| `review-stack-alignment` | Finds orphaned API calls / frontend↔backend mismatches → `reports/stack_alignment_report.md` |
| `review-database` | SQL safety and schema review → `reports/database_review.md` |
| `review-qa` | Test coverage gaps → `reports/qa_review.md` |
| `review-accessibility` | A11y audit → `reports/accessibility_review.md` |
| `review-data-privacy` | PII scan → `reports/compliance_review.md` |
| `write-documentation` | Generates docs/screenshots for critical flows |
| `write-tests` | Generates missing test cases |
| `plan-feature` | Feature design and scoping |
| `plan-release` | Reads all reports in `mop_validation/reports/` and creates a prioritized action plan |
| `plan-product-strategy` | High-level product direction |
| `interrogate-features` | Examines feature completeness |
| `state-of-the-nation` | Honest, data-driven product assessment with explicit GO/NO-GO — produces `.planning/STATE-OF-NATION.md` |

**Workflows** (in `.agents/workflows/`) — orchestrate multiple skills end-to-end:
- `full_audit.md` — runs all review skills sequentially and synthesises a release plan
- `self_healing_quality_loop.md` — finds missing tests and fills the gaps
- `close_gaps.md` — targets a specific gap report and implements fixes
- `ideation_loop.md` — product ideation cycle

**Rules** (in `.agents/rules/`) — coding standards and architectural constraints that apply to all work on this project: `python-coding-structure.md`, `version-control.md`, `documentation_standards.md`, `speedy-mini-deployment.md`.

**Admin tools** (in `.agents/tools/`):
```bash
# Generate an Ed25519 signing keypair (output: secrets/signing.key + secrets/verification.key)
python ~/Development/toms_home/.agents/tools/admin_signer.py --generate

# Sign a Python script and submit it to the Model Service
python ~/Development/toms_home/.agents/tools/admin_signer.py --sign my_script.py
```

### `GEMINI.md` (this repo)
`GEMINI.md` at the repo root is the equivalent of this file for the Gemini CLI. Check it for context on work that Gemini agents may have completed — it summarises the same project structure and links to the same sister repos. Its "Agentic Instructions" section notes that skill outputs are always saved to `mop_validation/reports/`, which is a useful audit trail of past agent activity regardless of which agent ran the skill.
