# Setup & Deployment

This guide covers everything you need to get Axiom running — whether you want a full production stack via Docker Compose or a local development environment to hack on the code.

---

## Quick Start

!!! tip "Get running in 60 seconds"
    The fastest path to a working stack:

    ```bash
    git clone <repo-url> master-of-puppets
    cd master-of-puppets/puppeteer
    cp .env.example .env   # fill in SECRET_KEY, ENCRYPTION_KEY, ADMIN_PASSWORD, API_KEY
    docker compose -f compose.server.yaml up -d
    # Dashboard available at https://localhost (Caddy self-signed) or your CF tunnel domain
    ```

    The stack takes approximately 15 seconds to become healthy after containers start.
    See the [Environment Variables](#environment-variables) section for how to generate the values needed before `docker compose up`.

---

## Prerequisites

### All deployments

- **Docker 24+** and **Docker Compose v2** (`docker compose` — not the legacy `docker-compose`)

### Local development only

- **Python 3.12** (the backend uses `asyncio` features not available in earlier versions)
- **Node.js 18+** and npm (for the React dashboard)

---

## Production Deployment (Docker Compose)

The recommended way to run Axiom is via the provided `compose.server.yaml`. This brings up the entire stack as a set of coordinated containers.

### Services

The stack runs ten services:

| Service | Image | Port | Purpose |
|---|---|---|---|
| `db` | `postgres:15-alpine` | 5432 (internal) | PostgreSQL — primary datastore |
| `cert-manager` | Custom Caddy | 80, 8443 | Reverse proxy, TLS termination, static asset serving |
| `agent` | Custom Python | 8001 | FastAPI agent service — the control plane API |
| `model` | Custom Python | 8000 (internal) | Model service — job model and scoring |
| `dashboard` | Via Caddy | — | React dashboard (served by cert-manager) |
| `docs` | Custom nginx | — | MkDocs static site (served by cert-manager at `/docs/`) |
| `registry` | `registry:2` | 5000 | Local Docker registry for Foundry-built images |
| `pypi` | Custom | 8080 (internal) | Local PyPI mirror for node builds |
| `mirror` | Custom | 8081 (internal) | Package mirror for offline node builds |
| `tunnel` | `cloudflare/cloudflared` | — | Cloudflare tunnel (outbound only, if enabled) |

!!! note "docs container uses nginx, not mkdocs serve"
    The `docs` container is a pre-built static site served by nginx. It does **not** run `mkdocs serve`. Running `mkdocs serve` in production is unsafe (see [MkDocs GitHub issue #1825](https://github.com/mkdocs/mkdocs/issues/1825)) and is only used during local documentation development.

### Bring up the stack

Run from the repository root (or adjust the path accordingly):

```bash
docker compose -f puppeteer/compose.server.yaml up -d
```

Or, if you are already inside `puppeteer/`:

```bash
docker compose -f compose.server.yaml up -d
```

### Check health

```bash
docker compose -f puppeteer/compose.server.yaml ps
```

All services should show `healthy` or `running` within ~30 seconds. If `agent` is slow to start, it is usually waiting for the `db` health check to pass — this is normal.

### View logs

```bash
# Follow logs for the agent service
docker compose -f puppeteer/compose.server.yaml logs -f agent

# Follow all services
docker compose -f puppeteer/compose.server.yaml logs -f
```

### Rebuild after code changes

The `agent` service is the most frequently changed. To rebuild and hot-swap it without restarting the entire stack:

```bash
docker compose -f puppeteer/compose.server.yaml build agent
docker compose -f puppeteer/compose.server.yaml up -d --no-build agent
```

To rebuild all services:

```bash
docker compose -f puppeteer/compose.server.yaml build
docker compose -f puppeteer/compose.server.yaml up -d
```

!!! warning "Do not use `docker restart` for code changes"
    `docker restart` only restarts the container — it does not pick up new image layers. Always use `docker compose build` followed by `docker compose up -d` to apply code changes.

### Tear down

```bash
# Stop containers, keep volumes (preserves database data)
docker compose -f puppeteer/compose.server.yaml down

# Stop containers and remove volumes (destroys all data — destructive!)
docker compose -f puppeteer/compose.server.yaml down -v
```

---

## Environment Variables

The orchestrator reads environment variables from `puppeteer/.env` (and optionally `puppeteer/secrets.env` for sensitive values like `ADMIN_PASSWORD`).

Copy the example file before your first run:

```bash
cp puppeteer/.env.example puppeteer/.env
```

Then edit `puppeteer/.env` and fill in the required values:

| Variable | Required | Purpose | Example / How to Generate |
|---|---|---|---|
| `API_KEY` | **Required** | Shared API key for legacy API key auth. `security.py` calls `sys.exit(1)` at import time if this is missing — the service **will not start** without it. | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | **Required** (unstable if absent) | Fernet key for job secrets encrypted at rest. If you change this after deployment, all stored secrets become unreadable. | `openssl rand -base64 32 \| tr '+/' '-_' \| tr -d '\n='` (append a trailing `=`) |
| `SECRET_KEY` | Recommended | JWT signing key. Defaults to a weak dev value — always override in production. | `openssl rand -hex 32` |
| `ADMIN_PASSWORD` | Recommended | Initial admin account password. Only used on **first** startup if the admin user does not yet exist. The database password is the source of truth after that. | Any secure password |
| `DATABASE_URL` | Optional | Database connection string. Defaults to SQLite (`jobs.db`) if absent. | `postgresql+asyncpg://user:pass@host/db` |
| `AGENT_URL` | Required for nodes | The URL nodes use to reach the agent service from the network. Must be reachable from every node. | `https://192.168.1.10:8001` |
| `CLOUDFLARE_TUNNEL_TOKEN` | CF tunnel only | Cloudflare Tunnel credentials. Only needed if you are routing the dashboard through a Cloudflare Tunnel. | From CF Dashboard → Tunnels |
| `DUCKDNS_TOKEN` / `DUCKDNS_DOMAIN` | DuckDNS only | Dynamic DNS for Caddy cert-manager TLS. Only needed if using DuckDNS for certificate issuance. | From DuckDNS account page |

!!! warning "Never commit real keys to git"
    The `.env` file is gitignored for good reason. Even though the docs site sits behind Cloudflare Access protection, never commit real API keys, encryption keys, or passwords to the repository. Use `.env` files, `secrets.env`, or a proper secrets manager.

---

## Local Development

Most production deployments run via Docker Compose (see above). This section is for contributors who want to run the backend and/or frontend directly on their machine for rapid iteration.

### Backend (FastAPI)

#### Install dependencies

```bash
cd puppeteer
pip install -r requirements.txt
pip install aiosqlite  # required for SQLite local dev — NOT included in requirements.txt
```

!!! warning "aiosqlite is required for SQLite local dev"
    The `requirements.txt` targets the Docker image, which runs against PostgreSQL. If you run locally without a `DATABASE_URL` pointing to Postgres, SQLAlchemy defaults to SQLite and requires `aiosqlite`. Install it separately as shown above.

#### Set required environment variables

`security.py` calls `sys.exit(1)` at **import time** if `API_KEY` is not set. This means the FastAPI process will not start — not even to print a helpful error — unless the env var is present before launch. Set these before running:

```bash
export API_KEY=dev-key
export ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n=')=
export SECRET_KEY=dev-secret-key
```

You can also place these in a `.env` file in `puppeteer/` and load them with `source .env` or a tool like `direnv`.

#### Start the backend

```bash
cd puppeteer
python -m agent_service.main
```

The backend starts on **https://localhost:8001** using a self-signed TLS certificate. The first startup will create `jobs.db` (SQLite) in the `puppeteer/` directory and seed the default roles and admin user.

### Frontend (React / Vite)

#### Install and run

```bash
cd puppeteer/dashboard
npm install
npm run dev
```

The dev server runs at **http://localhost:5173**. API calls are proxied to `https://localhost:8001` per the settings in `.env.development` — the backend must be running for any API calls to succeed.

The dev server handles hot module replacement (HMR) automatically. Changes to `.tsx` / `.ts` / `.css` files appear immediately without a manual refresh.

#### Production build

To test the production bundle locally:

```bash
cd puppeteer/dashboard
npm run build
npm run preview
```

#### Lint

```bash
cd puppeteer/dashboard
npm run lint
```

### Running Tests

#### Backend tests (pytest)

```bash
cd puppeteer
pytest
```

Run a single test file:

```bash
cd puppeteer
pytest tests/test_tools.py
```

#### Frontend tests (vitest)

```bash
cd puppeteer/dashboard
npm run test
```

Run a single test file:

```bash
cd puppeteer/dashboard
npx vitest run src/views/__tests__/JobDefinitions.test.tsx
```

---

## TLS Bootstrap & Node Enrollment

After deploying the orchestrator, nodes need to know where to connect and which CA to trust. This is handled via two environment variables on each node container.

### How it works

1. **Get the JOIN_TOKEN** — after your first login, navigate to the **Admin** panel in the dashboard. The `JOIN_TOKEN` is displayed there. It is a base64-encoded JSON blob containing the Root CA PEM that nodes use to bootstrap trust.

2. **Set env vars on the node** — when deploying a puppet node container, provide:

    ```bash
    JOIN_TOKEN=<token-from-admin-panel>
    AGENT_URL=https://192.168.1.10:8001   # puppeteer's address reachable from the node
    ```

3. **Node auto-enrolls** — on first startup, the node generates a key pair, sends a CSR to `AGENT_URL/api/enroll`, and receives a signed client certificate. The node appears in the **Nodes** view of the dashboard once enrollment succeeds.

4. **Subsequent restarts** — the node stores its certificate in the `secrets/` volume mount and reuses it on restart. The node ID is derived from the certificate filename to prevent identity drift on container restart.

!!! note "Deep cert rotation and mTLS details"
    This section covers the happy-path enrollment flow. For certificate revocation, CRL management, mTLS verification, and the full PKI lifecycle, see the **Security Guide** (coming in a later documentation phase).

---

## Upgrading

### Pull and rebuild

```bash
git pull
docker compose -f puppeteer/compose.server.yaml build
docker compose -f puppeteer/compose.server.yaml up -d
```

This rebuilds all images from the updated source and replaces running containers. Volumes (including the database) are preserved.

### Database migrations

**New deployments** are handled automatically — `Base.metadata.create_all` runs at startup and creates all tables.

**Existing deployments** require manual migration for any new columns added since your last upgrade. Check the `puppeteer/` directory for migration files:

```bash
ls puppeteer/migration_v*.sql
```

Apply any migration files with a version higher than your current schema version:

```bash
# Example: applying a migration to a running Postgres container
docker exec -i puppeteer-db-1 psql -U postgres -d puppeteer < puppeteer/migration_v14.sql
```

See the Contributing guide for the migration pattern used in this project.
