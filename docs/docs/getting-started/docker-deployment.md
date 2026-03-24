# Running with Docker

Axiom ships as a multi-service Docker Compose stack. This guide covers everything needed to run it in production — from secret generation to upgrades.

---

## Prerequisites

- Docker 24+ and Docker Compose v2
- A Linux host (amd64 or arm64)
- A PostgreSQL 15 database (see [PostgreSQL setup](#postgresql-setup) below, or use a managed service)

Copy `.env.example` to `.env` and fill in the required values before starting:

```bash
cp .env.example .env
```

---

## PostgreSQL Setup

Axiom uses SQLite by default (dev only). For production, provide a PostgreSQL connection string via `DATABASE_URL`.

If you are running the full Compose stack (`compose.server.yaml`), a PostgreSQL service named `db` is already included. Set:

```bash
DATABASE_URL=postgresql+asyncpg://puppet:password@db/puppet_db
```

!!! warning "SQLite is not suitable for production"
    SQLite has no concurrent write protection and no backup tooling. Always use PostgreSQL for deployments with more than one operator or any scheduled jobs.

---

## Secret Generation

Three secrets must be set before first start:

**JWT signing key** — used to sign all operator session tokens:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# → paste result into SECRET_KEY=
```

**Fernet encryption key** — encrypts node join tokens and secrets at rest:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# → paste result into ENCRYPTION_KEY=
```

**API key** — required by the agent service (crashes at import if absent):
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# → paste result into API_KEY=
```

!!! danger "API_KEY has no fallback"
    Unlike `SECRET_KEY` (which falls back to a weak dev default), `API_KEY` has no default value. The agent service will crash at startup if it is not set.

---

## Starting the Stack

```bash
docker compose -f puppeteer/compose.server.yaml up -d
```

The stack starts four services: `agent` (FastAPI on 8001), `model` (port 8000), `db` (PostgreSQL), and `caddy` (reverse proxy on 443).

Check that all services are healthy:

```bash
docker compose -f puppeteer/compose.server.yaml ps
```

---

## Optional Service Toggles

| Feature | How to enable | Env var |
|---------|---------------|---------|
| Cloudflare Tunnel | Set `CLOUDFLARE_TUNNEL_TOKEN` | See `.env.example` Tunnel section |
| Axiom EE | Set `AXIOM_LICENCE_KEY` | Paste your EE licence key |
| Custom TLS hostname | Set `SERVER_HOSTNAME` | Your domain (e.g. `axiom.example.com`) |

Leave any optional var commented-out (or blank) to skip that feature. The stack runs without them.

---

## Upgrade and Re-deploy

To apply a code change or pull a new image:

```bash
# 1. Pull the latest image (or rebuild locally)
docker compose -f puppeteer/compose.server.yaml pull agent

# 2. Apply any pending migration SQL (check release notes)
docker exec puppeteer-db-1 psql -U puppet puppet_db < puppeteer/migration_vNN.sql

# 3. Restart only the agent (zero PostgreSQL downtime)
docker compose -f puppeteer/compose.server.yaml up -d --no-deps agent
```

!!! note "Schema migrations"
    Axiom uses `CREATE TABLE IF NOT EXISTS` (no Alembic). New tables are created automatically on restart. New *columns* require a manual `ALTER TABLE` — check the `migration_vNN.sql` files in the repo for each release.

---

## Production Checklist

Before exposing Axiom to the network:

- [ ] `SECRET_KEY` set to a randomly generated 32-byte hex string
- [ ] `ENCRYPTION_KEY` set to a Fernet-generated key
- [ ] `API_KEY` set (non-empty — service crashes without it)
- [ ] `ADMIN_PASSWORD` set to something strong (only read on first start)
- [ ] `DATABASE_URL` points to PostgreSQL, not SQLite
- [ ] TLS configured (Caddy handles this automatically via HTTPS redirect)
- [ ] Cloudflare Tunnel or reverse proxy restricts public access to port 443 only

---

## Next Steps

- [Enroll your first node](enroll-node.md) to start routing jobs
- [Set up RBAC](../feature-guides/rbac.md) for operator and viewer accounts
- [Configure Foundry](../feature-guides/foundry.md) to build custom node images
