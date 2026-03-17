# Contributing to Master of Puppets

This guide covers how to contribute to Master of Puppets — from running tests locally to the PR bar and database migration conventions. Read it before opening a pull request.

---

## Overview

The project is split into three components:

- **Puppeteer** (`puppeteer/`) — FastAPI control plane + React dashboard
- **Puppet nodes** (`puppets/`) — stateless worker agents that poll for jobs
- **Docs** (`docs/`) — MkDocs Material static site

Most contributions touch `puppeteer/`. Changes to `puppets/environment_service/` affect running nodes — test them carefully.

---

## Code Style

### Python — Black (formatter)

All Python code must be formatted with [Black](https://black.readthedocs.io/):

```bash
pip install black ruff
black puppeteer/
```

Configuration lives in `puppeteer/pyproject.toml`:

- Line length: 88 characters
- Target Python version: 3.12

To check without modifying files:

```bash
black --check puppeteer/
```

### Python — Ruff (linter)

[Ruff](https://docs.astral.sh/ruff/) replaces flake8, isort, and pyupgrade in a single fast tool:

```bash
ruff check puppeteer/
```

Active rule sets (from `puppeteer/pyproject.toml`):

| Rule set | Source |
|----------|--------|
| `E` | pycodestyle errors |
| `F` | pyflakes |
| `I` | isort (import ordering) |
| `W` | pycodestyle warnings |

`E501` (line-too-long) is explicitly ignored — Black handles line length.

To auto-fix safe issues:

```bash
ruff check --fix puppeteer/
```

### Frontend — ESLint

Frontend linting uses ESLint with the existing project config:

```bash
cd puppeteer/dashboard
npm run lint
```

This must pass with no errors before a PR can merge. The config is already set up — do not modify the ESLint configuration as part of a feature PR.

### Style-Only Reformatting

!!! warning "Keep style changes separate"
    Do NOT run `black .` or `ruff --fix .` on existing code in the same PR as your feature changes. Style-only reformatting should be a separate commit or PR to keep diffs reviewable.

---

## Running Tests

Both test suites must be green before a PR can merge. Run them with the exact commands and working directories shown below.

### Backend (pytest)

```bash
cd puppeteer
pytest
```

For faster iteration during development:

!!! tip "Quick run (fail-fast)"
    ```bash
    pytest tests/ -x -q
    ```
    `-x` stops on first failure. `-q` reduces output noise. Use this during active development; run the full `pytest` suite before submitting.

### Frontend (vitest)

```bash
cd puppeteer/dashboard
npm run test
```

For CI-style non-interactive run:

```bash
cd puppeteer/dashboard
npm run test -- --run
```

### Coverage

There is no numeric coverage threshold. Green = pass. The bar is: **all existing tests continue to pass** and new code has tests for its core behaviour. Do not submit untested business logic.

---

## PR Requirements

Before opening a pull request, verify each of the following:

- [ ] `cd puppeteer && pytest` passes with no failures
- [ ] `cd puppeteer/dashboard && npm run test` passes with no failures
- [ ] `cd puppeteer/dashboard && npm run lint` passes with no errors
- [ ] New Python code follows Black formatting (`black --check puppeteer/`)
- [ ] New Python code passes Ruff lint (`ruff check puppeteer/`)
- [ ] New API routes include a `tags=` parameter (17 tag groups established — check existing routes in `main.py` for examples)
- [ ] New DB columns include a migration SQL file (see the [Database Migrations](#database-migrations) section below)

### Commit style

Use conventional commits:

```
feat(component): short present-tense description

- Detail 1
- Detail 2
```

Types: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`.

---

## Database Migrations

!!! warning "Major contributor gotcha — read this before adding DB columns"
    This project does **not** use Alembic. `Base.metadata.create_all` runs at startup and creates new tables automatically — but it will **never alter existing tables**. If you add a column to a model without a migration file, fresh deployments will have the column; existing deployments will silently miss it.

### How it works

- **Fresh deployments**: fully covered by `create_all` — no migration steps needed.
- **Existing deployments**: if you add a column to an existing DB model, you **must** also create a `puppeteer/migration_vN.sql` file with the necessary `ALTER TABLE` statement.

### Migration file format

```sql
-- migration_v32.sql (increment from current highest: migration_v31.sql)
-- NOTE: IF NOT EXISTS syntax is PostgreSQL-only. For SQLite use bare ALTER TABLE.
ALTER TABLE my_table ADD COLUMN IF NOT EXISTS new_column TEXT;
ALTER TABLE my_table ADD COLUMN IF NOT EXISTS another_column INTEGER DEFAULT 0;
```

### Rules

| Rule | Why |
|------|-----|
| Use `IF NOT EXISTS` | Makes the migration idempotent — safe to apply twice |
| SQLite caveat | SQLite's `ALTER TABLE ... ADD COLUMN` does not support `IF NOT EXISTS` — add a comment in the file noting it's for Postgres |
| Never drop columns | Dropping columns is destructive — coordinate separately, outside a migration file |
| Sequential naming | `migration_v32.sql`, `migration_v33.sql` — increment from the current highest file |

### Finding the current migration number

```bash
ls puppeteer/migration_v*.sql | sort -V | tail -1
```

The next migration should be one higher than whatever this returns.

---

## Code Structure

See `CLAUDE.md` at the repo root for the full layout table. Key patterns to follow:

### Backend

- **All FastAPI route handlers** live in `puppeteer/agent_service/main.py` — do not split routes across multiple files. The single-file convention keeps routing searchable and consistent.
- **Business logic** goes in `puppeteer/agent_service/services/` — one service module per domain (`job_service.py`, `foundry_service.py`, `scheduler_service.py`, etc.)
- **Pydantic models** for request/response in `puppeteer/agent_service/models.py`
- **SQLAlchemy ORM models** in `puppeteer/agent_service/db.py`
- **Auth** (`auth.py`) and **security** (`security.py`) are separate from business logic

#### Adding a new API route

1. Define the Pydantic request/response models in `models.py`
2. Add the SQLAlchemy model to `db.py` if new storage is needed
3. Write the business logic in the appropriate `services/` file
4. Add the route handler in `main.py` with:
   - The correct `tags=` parameter (check existing routes for the 17 established tag groups)
   - A `Depends(require_permission("..."))` guard
5. Write a migration file if new DB columns are needed

### Frontend

- **All authenticated API calls** go through `authenticatedFetch()` in `dashboard/src/auth.ts` — never call `fetch()` directly for authenticated endpoints
- **Views** are self-contained pages in `dashboard/src/views/`
- **Shared components** go in `dashboard/src/components/`
- **Custom hooks** go in `dashboard/src/hooks/`

---

## WebSocket and Real-Time Updates

The WebSocket endpoint is at `/ws?token=<jwt>` and pushes job/node status updates to the dashboard. The token is required — unauthenticated WebSocket connections are rejected.

When adding new real-time events:

1. Emit the event via the WebSocket manager in `main.py` (after the relevant DB write)
2. Handle the message type in the client-side hook: `dashboard/src/hooks/useWebSocket.ts`

The hook auto-reconnects with exponential backoff — do not add custom reconnect logic in view components.

---

## Environment Variables

When adding new configuration:

1. Document the variable in `CLAUDE.md` under the Configuration table
2. Set a safe default for local dev (SQLite-compatible, no external services)
3. Note whether the variable is required in production

Key variables used in local dev (set in `puppeteer/.env`):

| Variable | Dev default | Purpose |
|----------|-------------|---------|
| `DATABASE_URL` | (unset, uses SQLite) | Postgres connection string in production |
| `SECRET_KEY` | weak dev default | JWT signing — always override in production |
| `ENCRYPTION_KEY` | (none) | Fernet key for secrets at rest |
| `API_KEY` | (none) | Legacy API key auth |
| `ADMIN_PASSWORD` | random | Initial admin password |

!!! warning "aiosqlite is not in requirements.txt"
    The async SQLite driver (`aiosqlite`) is not listed in `requirements.txt` because production uses PostgreSQL. If you see `ModuleNotFoundError: aiosqlite` when running locally, install it manually: `pip install aiosqlite`. Do not add it to `requirements.txt`.

---

## Getting Help

- **Architecture overview**: [developer/architecture.md](architecture.md) — system components, data flow, mTLS, job signing
- **API reference**: [API Reference](/docs/api-reference/) — full OpenAPI endpoint schemas, generated from the live server
- **CLAUDE.md**: at the repo root — concise reference for all commands, file paths, and architecture decisions
