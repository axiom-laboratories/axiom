# Phase 38: Clean Teardown + Fresh CE Install - Research

**Researched:** 2026-03-20
**Domain:** Bash scripting, Docker Compose lifecycle, Incus/LXC management, PostgreSQL introspection, Python verification scripts
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Script form + location**
- Bash scripts: `teardown_soft.sh` and `teardown_hard.sh`
- Location: `mop_validation/scripts/`
- Hardcoded relative path to puppeteer/ — scripts assume they're run from `~/Development/master_of_puppets` (matches existing mop_validation patterns)

**Soft teardown scope**
- Run `docker compose down` (no `-v`) — stops and removes containers
- Then explicitly remove `pgdata` volume only via `docker volume rm`
- Preserved volumes: `certs-volume`, `caddy_data`, `caddy_config`, `registry-data`
- LXC node `secrets/` dirs: left completely untouched — nodes keep their certs and re-enroll next start
- Stack is left down after teardown — caller runs `docker compose up -d` when ready

**Hard teardown scope**
- Run `docker compose down -v --remove-orphans` — removes all named volumes
- Then clear LXC node `secrets/` dirs via `incus exec`

**LXC node secrets discovery (hard teardown)**
- Use `incus list --format csv` to dynamically discover containers matching `axiom-node-` prefix
- Node secrets path: `/home/ubuntu/secrets/` inside each container
- Error handling: skip with warning if a node is not running or `incus exec` fails — teardown is best-effort for nodes
- Do not fail fast on individual node errors

**Verification method**
- Standalone Python script: `mop_validation/scripts/verify_ce_install.py`
- Table count: `docker exec` into postgres container with `psql` query against `information_schema.tables` (no external DB driver needed)
- Features assertion: `GET /api/features` via requests, confirm all values false
- Admin re-seed test (INST-04): manual test with documented steps in script comments — not automated

### Claude's Discretion
- Script banner/output formatting (PASS/FAIL prefix, colors if desired)
- Exact postgres container name detection (use `docker ps` filter or hardcode `puppeteer-postgres-1`)
- Wait/retry logic for stack startup before verification hits the API

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INST-01 | A soft teardown script preserves the Root CA and node `secrets/` dirs — only stops containers and clears DB data | Soft teardown: `docker compose down` + targeted `docker volume rm pgdata` removes DB only; certs-volume survives |
| INST-02 | A hard teardown script runs `docker compose down -v --remove-orphans` AND clears all LXC node `secrets/` dirs — true clean slate | `docker compose down -v` removes all named volumes; `incus exec <node> -- rm -rf /home/ubuntu/secrets/` clears node certs |
| INST-03 | Fresh CE install from cold start produces exactly 13 CE tables, `GET /api/features` all false, and a correctly seeded admin account | axiom-split CE code creates exactly 13 tables (verified in db.py); `/api/features` returns all-false object in CE mode |
| INST-04 | Admin password re-seed behaviour verified: if admin already exists, `ADMIN_PASSWORD` env var change does NOT overwrite DB password | axiom-split main.py lifespan checks `if not result.scalar_one_or_none()` before creating admin — existing admin is never touched |
</phase_requirements>

---

## Summary

Phase 38 creates three files in `mop_validation/scripts/`: `teardown_soft.sh`, `teardown_hard.sh`, and `verify_ce_install.py`. All work against the **axiom-split worktree** CE stack (`~/.worktrees/axiom-split/puppeteer/compose.server.yaml`), not the `main` branch monolith currently running. This distinction is critical: the running stack has 29 tables (monolith); the CE target has exactly 13 tables.

The soft teardown is safe to run between test runs because `certs-volume` (Root CA), `caddy_data`, `caddy_config`, and `registry-data` survive. Only `pgdata` is explicitly removed. LXC node `secrets/` dirs are untouched, so nodes can re-enroll after `docker compose up -d` without new JOIN_TOKENs.

The hard teardown is the full clean-slate: `docker compose down -v --remove-orphans` plus `incus exec` into each `axiom-node-*` container to wipe `/home/ubuntu/secrets/`. Node errors are skipped with a warning (best-effort, not fail-fast). The verification script drives the PASS/FAIL assertions for INST-01 through INST-04 using only `subprocess` (for `docker exec psql`) and `requests` (for API calls) — no external DB driver needed.

**Primary recommendation:** Target `axiom-split` CE stack for all teardown and verification. Use `COMPOSE_FILE` variable in the scripts pointing to `$HOME/Development/master_of_puppets/.worktrees/axiom-split/puppeteer/compose.server.yaml`.

---

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| bash | system | teardown_soft.sh + teardown_hard.sh | All mop_validation scripts follow bash for one-liner invocability |
| docker compose | v2 (plugin) | Stack lifecycle management | The project's canonical compose invocation |
| incus | installed | LXC container management | Established in manage_incus_node.py and `manage-test-nodes` skill |
| python3 + requests | 3.11+ / 2.31+ | verify_ce_install.py | Matches mop_validation existing scripts (test_local_stack.py pattern) |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `psql` (via docker exec) | postgres:15-alpine | Table count query | No external psycopg2 needed — psql is inside the container |
| `subprocess` (Python stdlib) | stdlib | Run docker exec from verify script | No extra deps required |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `docker exec psql` | External psycopg2 | psycopg2 requires install; docker exec needs no deps |
| `incus list --format csv` | `incus list --format json` | CSV is simpler for prefix filtering; JSON needed if state checks required |

---

## Architecture Patterns

### Recommended Project Structure
```
mop_validation/scripts/
├── teardown_soft.sh       # INST-01: preserve PKI, clear DB only
├── teardown_hard.sh       # INST-02: full clean slate
└── verify_ce_install.py   # INST-03, INST-04: post-cold-start assertions
```

### Pattern 1: Bash Teardown Script Structure
**What:** Set COMPOSE_FILE variable pointing to axiom-split compose, cd to repo root, run compose commands, handle errors with explicit exit codes.
**When to use:** Both teardown scripts follow this exact structure.

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$HOME/Development/master_of_puppets"
COMPOSE_FILE="$REPO_DIR/.worktrees/axiom-split/puppeteer/compose.server.yaml"
COMPOSE_PROJECT="puppeteer"

cd "$REPO_DIR/.worktrees/axiom-split/puppeteer"

echo "[SOFT TEARDOWN] Stopping containers (preserving volumes)..."
docker compose -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT" down

echo "[SOFT TEARDOWN] Removing pgdata volume..."
docker volume rm "${COMPOSE_PROJECT}_pgdata" 2>/dev/null || echo "[WARN] pgdata not found — already clean"

echo "[SOFT TEARDOWN] Done. Preserved: certs-volume, caddy_data, caddy_config, registry-data, mirror-data, devpi-data"
```

### Pattern 2: Hard Teardown with Incus Discovery
**What:** Dynamically discover `axiom-node-*` Incus containers via `incus list --format csv`, iterate and clear `/home/ubuntu/secrets/` with best-effort error handling.
**When to use:** Hard teardown only.

```bash
# Dynamic LXC node discovery — prefix match on first CSV column (name)
while IFS=',' read -r name rest; do
    name=$(echo "$name" | tr -d '"')
    if [[ "$name" == axiom-node-* ]]; then
        echo "[HARD TEARDOWN] Clearing secrets on $name..."
        incus exec "$name" -- rm -rf /home/ubuntu/secrets/ || \
            echo "[WARN] Could not clear $name (not running or exec failed) — skipping"
    fi
done < <(incus list --format csv 2>/dev/null || true)
```

### Pattern 3: Python Verification Script Structure
**What:** Sequential PASS/FAIL checks: stack up, table count via psql, API features, API licence, admin re-seed documentation.
**When to use:** verify_ce_install.py.

```python
#!/usr/bin/env python3
"""CE install verification — run after cold start from axiom-split CE.

Usage:
    python3 mop_validation/scripts/verify_ce_install.py

Prerequisites:
    - Stack running: docker compose -f .worktrees/axiom-split/puppeteer/compose.server.yaml up -d
    - pip install requests
"""
import subprocess, sys, time, json
import requests

AGENT_URL = "https://localhost:8001"
POSTGRES_CONTAINER = "puppeteer-db-1"  # or discover via docker ps filter
CE_TABLE_COUNT = 13
requests.packages.urllib3.disable_warnings()

def check(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    return passed
```

### Pattern 4: Table Count via docker exec psql
**What:** Run `psql` inside the postgres container with `-t -c` (tuples-only, single command) to count tables in `pg_tables` where `schemaname='public'`, excluding `apscheduler_jobs` (APScheduler creates its own table).
**When to use:** INST-03 verification.

```bash
# Shell version (for reference — Python uses subprocess)
docker exec puppeteer-db-1 psql -U puppet -d puppet_db -t -c \
  "SELECT count(*) FROM pg_tables WHERE schemaname='public';"
```

**CRITICAL NOTE:** APScheduler creates `apscheduler_jobs` as a 14th table at startup. The INST-03 assertion of "exactly 13 CE tables" refers to SQLAlchemy-managed tables only. The query must either:
- Exclude `apscheduler_jobs` explicitly: `WHERE schemaname='public' AND tablename != 'apscheduler_jobs'`
- Or verify >= 13 AND the specific 13 table names are present

This is a known pitfall — see Pitfalls section.

### Pattern 5: Wait/Retry Before API Calls
**What:** Poll the health endpoint with exponential-ish backoff before firing verification calls.
**When to use:** verify_ce_install.py, after cold start.

```python
def wait_for_stack(url: str, timeout: int = 60):
    """Poll /api/health until the stack is up or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/api/health", verify=False, timeout=3)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(3)
    return False
```

### Anti-Patterns to Avoid
- **Using `docker compose down -v` in soft teardown:** `-v` removes ALL volumes including certs-volume — that destroys the Root CA and breaks node enrollment. Soft teardown must never use `-v`.
- **Hardcoding postgres container name without fallback:** Container is `puppeteer-db-1` when run with default project name, but `docker ps --filter` is safer if project name differs.
- **`set -e` without `|| true` on incus best-effort steps:** Hard teardown must not abort if one LXC node fails. Wrap incus per-node commands with `|| echo "[WARN] ..."`.
- **Asserting exactly 14 tables (including apscheduler_jobs):** APScheduler creates this at runtime. CE SQLAlchemy tables are 13. Query must exclude it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DB connectivity in verify script | psycopg2 client | `docker exec psql` | Already installed in container; no Python dep to manage |
| Container name discovery | Custom parser | `docker ps --filter name=puppeteer-db --format {{.Names}}` | Docker CLI handles this; less fragile than hardcode |
| Wait-for-API polling | Custom httpd poller | Simple requests loop + sleep | Sufficient for local stack; no extra library needed |
| Incus node discovery | Parse `incus list` JSON | `incus list --format csv` prefix filter | CSV column 0 is the name; simpler than JSON for this use |

---

## Common Pitfalls

### Pitfall 1: APScheduler Creates a 14th Table
**What goes wrong:** `information_schema.tables` query returns 14 rows on CE cold start, causing INST-03 FAIL.
**Why it happens:** APScheduler (used by scheduler_service) creates its own `apscheduler_jobs` table at startup, outside SQLAlchemy `Base.metadata`.
**How to avoid:** Query excludes `apscheduler_jobs`: `WHERE schemaname='public' AND tablename != 'apscheduler_jobs'`
**Confirmed by:** Live inspection — `apscheduler_jobs` appears in `pg_tables` on the running stack.

### Pitfall 2: Soft Teardown Leaves Stale pgdata Volume
**What goes wrong:** After `docker compose down`, the `pgdata` volume still exists because `down` without `-v` does not remove named volumes.
**Why it happens:** Docker's design — named volumes persist across `down` unless `-v` flag is used.
**How to avoid:** Soft teardown explicitly runs `docker volume rm <project>_pgdata` after `docker compose down`.
**Warning signs:** `docker volume ls` still shows `puppeteer_pgdata` after soft teardown.

### Pitfall 3: Compose Project Name Prefixes Volume Names
**What goes wrong:** `docker volume rm pgdata` fails — the actual volume name is `puppeteer_pgdata` (project-prefixed).
**Why it happens:** Docker Compose prefixes named volumes with the project name (defaults to directory name — `puppeteer` for the axiom-split compose).
**How to avoid:** Use `${COMPOSE_PROJECT}_pgdata` variable in teardown scripts, or derive project name from compose file directory.
**Confirmed by:** Live `docker volume ls` shows `puppeteer_pgdata`, `puppeteer_certs-volume`, etc.

### Pitfall 4: Admin Re-seed Bug (INST-04) Is In the main Branch, Not axiom-split
**What goes wrong:** Verifying INST-04 on the wrong codebase gives a false positive.
**Why it happens:** The `main` branch monolith has the same `if not result.scalar_one_or_none()` guard (line 87 main.py), and the axiom-split CE has the same guard (line 75). Both are safe. INST-04 is about confirming the guard works end-to-end on the CE stack.
**How to avoid:** Run verify_ce_install.py against the axiom-split CE stack exclusively.

### Pitfall 5: incus list --format csv Column Order
**What goes wrong:** Parsing the wrong column for container names.
**Why it happens:** `incus list --format csv` columns are: `NAME,STATE,IPV4,IPV6,TYPE,SNAPSHOTS`. Name is column 0.
**How to avoid:** `while IFS=',' read -r name rest; do` captures name cleanly. Strip quotes with `tr -d '"'`.

### Pitfall 6: CE vs Main Branch Stack — Wrong Compose File
**What goes wrong:** Running teardown against `puppeteer/compose.server.yaml` (main branch, 29 tables) instead of `.worktrees/axiom-split/puppeteer/compose.server.yaml` (CE, 13 tables).
**Why it happens:** Both compose files are in the same repo but different locations. Scripts that hardcode `puppeteer/compose.server.yaml` target the wrong stack.
**How to avoid:** Both teardown scripts and verify_ce_install.py MUST reference `.worktrees/axiom-split/puppeteer/compose.server.yaml`.

### Pitfall 7: `GET /api/features` Requires Specific CE Response Shape
**What goes wrong:** Assert "all values false" but the structure has 8 specific keys.
**Why it happens:** The axiom-split CE returns a fixed object: `{"audit": false, "foundry": false, "webhooks": false, "triggers": false, "rbac": false, "resource_limits": false, "service_principals": false, "api_keys": false}`.
**How to avoid:** Verify all 8 keys exist AND all values are `False`. Don't just check `all(response.values()) == False` — verify the key set matches exactly.

---

## Code Examples

### Table Count Query (Python subprocess)
```python
# Source: direct codebase inspection (db.py axiom-split, live psql verification)
def check_table_count(container: str = "puppeteer-db-1") -> tuple[bool, int]:
    result = subprocess.run(
        ["docker", "exec", container, "psql", "-U", "puppet", "-d", "puppet_db",
         "-t", "-c",
         "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename != 'apscheduler_jobs';"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return False, 0
    count = int(result.stdout.strip())
    return count == 13, count
```

### Features Endpoint Verification
```python
# Source: axiom-split main.py lines 820-836 (confirmed)
def check_features(base_url: str, token: str) -> bool:
    r = requests.get(f"{base_url}/api/features",
                     headers={"Authorization": f"Bearer {token}"},
                     verify=False)
    if r.status_code != 200:
        return False
    features = r.json()
    expected_keys = {"audit", "foundry", "webhooks", "triggers",
                     "rbac", "resource_limits", "service_principals", "api_keys"}
    return features.keys() == expected_keys and not any(features.values())
```

### Licence Endpoint CE Check
```python
# Source: axiom-split main.py lines 838-851 (confirmed)
def check_licence_ce(base_url: str, token: str) -> bool:
    r = requests.get(f"{base_url}/api/licence",
                     headers={"Authorization": f"Bearer {token}"},
                     verify=False)
    if r.status_code != 200:
        return False
    data = r.json()
    return data.get("edition") == "community"
```

### Admin Login Helper
```python
def get_admin_token(base_url: str, password: str) -> str | None:
    r = requests.post(f"{base_url}/auth/login",
                      data={"username": "admin", "password": password},
                      verify=False)
    if r.status_code != 200:
        return None
    return r.json().get("access_token")
```

### Soft Teardown Shell Pattern
```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$HOME/Development/master_of_puppets"
CE_DIR="$REPO_ROOT/.worktrees/axiom-split/puppeteer"
COMPOSE_FILE="$CE_DIR/compose.server.yaml"
PROJECT_NAME="puppeteer"

echo "[SOFT TEARDOWN] Stopping stack (no volume removal)..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down

echo "[SOFT TEARDOWN] Removing pgdata only..."
docker volume rm "${PROJECT_NAME}_pgdata" 2>/dev/null \
    || echo "[WARN] ${PROJECT_NAME}_pgdata not present — already clean"

echo "[SOFT TEARDOWN] Complete. PKI and node certs preserved."
```

### Hard Teardown Shell Pattern
```bash
#!/usr/bin/env bash
# Do NOT use set -e globally — LXC steps are best-effort
set -uo pipefail

REPO_ROOT="$HOME/Development/master_of_puppets"
CE_DIR="$REPO_ROOT/.worktrees/axiom-split/puppeteer"
COMPOSE_FILE="$CE_DIR/compose.server.yaml"
PROJECT_NAME="puppeteer"

echo "[HARD TEARDOWN] Removing all volumes + orphan containers..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v --remove-orphans

echo "[HARD TEARDOWN] Clearing LXC node secrets dirs..."
while IFS=',' read -r name rest; do
    name=$(echo "$name" | tr -d '"')
    if [[ "$name" == axiom-node-* ]]; then
        echo "  Clearing $name:/home/ubuntu/secrets/ ..."
        incus exec "$name" -- rm -rf /home/ubuntu/secrets/ \
            || echo "  [WARN] Failed on $name — skipping (not running?)"
    fi
done < <(incus list --format csv 2>/dev/null || true)

echo "[HARD TEARDOWN] Complete. True clean slate."
```

---

## Key Discoveries

### CE vs Main Branch — Critical Context
The `main` branch monolith has **29 tables** (verified live). The CE codebase in `.worktrees/axiom-split` has **exactly 13 tables** in db.py (verified by grepping `__tablename__`). All scripts in this phase MUST target `.worktrees/axiom-split/puppeteer/compose.server.yaml`.

### CE Table Names (all 13)
From `.worktrees/axiom-split/puppeteer/agent_service/db.py` (HIGH confidence — direct source inspection):
`jobs`, `signatures`, `scheduled_jobs`, `tokens`, `config`, `users`, `nodes`, `alerts`, `revoked_certs`, `node_stats`, `execution_records`, `signals`, `pings`

### Admin Seeding Guard (confirmed)
axiom-split `main.py` line 74: `if not result.scalar_one_or_none()` — admin is only created if it does not exist. Changing `ADMIN_PASSWORD` env var and restarting will NOT overwrite an existing admin's DB password. (HIGH confidence — direct source read.)

### Features Endpoint (confirmed)
`GET /api/features` returns 8-key dict, all `false` in CE mode (no EE plugin loaded). Unauthenticated. (HIGH confidence — axiom-split main.py lines 820-836.)

### Licence Endpoint (confirmed)
`GET /api/licence` returns `{"edition": "community"}` when `app.state.licence is None` (CE mode). Requires auth (`require_auth` dependency). (HIGH confidence — axiom-split main.py lines 838-851.)

### Compose Volume Name Prefix (confirmed)
Live Docker shows volumes named `puppeteer_pgdata`, `puppeteer_certs-volume` etc — project name `puppeteer` (from compose file directory name). Scripts must use `puppeteer_pgdata` not `pgdata`.

### Named Volumes in axiom-split Compose (confirmed)
`pgdata`, `certs-volume`, `caddy_data`, `caddy_config`, `registry-data`, `mirror-data`, `devpi-data` — 7 named volumes total. Soft teardown removes only `pgdata`; the other 6 survive.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| monolith `main` (29 tables) | CE split `.worktrees/axiom-split` (13 tables) | v11.0 | All v11.1 validation targets axiom-split, not main |
| `docker-compose` (v1) | `docker compose` (v2 plugin) | Docker 20.10+ | No hyphen; `docker compose` is the correct invocation |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (mop_validation scripts are standalone Python; no pytest runner needed for this phase) |
| Config file | none — verify_ce_install.py is standalone executable |
| Quick run command | `python3 ~/Development/mop_validation/scripts/verify_ce_install.py` |
| Full suite command | same — single script covers INST-01 through INST-04 assertions |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INST-01 | Soft teardown preserves certs-volume, removes pgdata | smoke | `bash teardown_soft.sh && docker volume ls` | Wave 0 |
| INST-02 | Hard teardown removes all volumes + LXC secrets | smoke | `bash teardown_hard.sh` | Wave 0 |
| INST-03 | 13 CE tables, /api/features all false, admin seeded | integration | `python3 verify_ce_install.py` | Wave 0 |
| INST-04 | Admin re-seed safety | manual (documented) | see script comments in verify_ce_install.py | Wave 0 |

### Sampling Rate
- **Per task commit:** Manual inspection — these are one-shot scripts, not unit tests
- **Per wave merge:** Run `python3 verify_ce_install.py` against a fresh CE cold start
- **Phase gate:** All verify_ce_install.py checks PASS before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `mop_validation/scripts/teardown_soft.sh` — covers INST-01
- [ ] `mop_validation/scripts/teardown_hard.sh` — covers INST-02
- [ ] `mop_validation/scripts/verify_ce_install.py` — covers INST-03, INST-04

---

## Open Questions

1. **Does the axiom-split CE stack use the same Postgres credentials as main?**
   - What we know: axiom-split compose.server.yaml has `POSTGRES_USER: puppet`, `POSTGRES_PASSWORD: masterpassword`, `POSTGRES_DB: puppet_db` — same as main.
   - What's unclear: Whether `puppeteer/.env` or `secrets.env` overrides these for the axiom-split worktree.
   - Recommendation: verify_ce_install.py should read ADMIN_PASSWORD from `mop_validation/secrets.env` using the established `load_env()` pattern.

2. **What is the exact postgres container name for the axiom-split CE stack?**
   - What we know: With project name `puppeteer` (derive from compose directory name `puppeteer`), the DB container would be `puppeteer-db-1`.
   - What's unclear: If a different `-p` project name is used, container name changes.
   - Recommendation: Discover dynamically via `docker ps --filter "ancestor=postgres:15-alpine" --format {{.Names}}` or `docker ps --filter "name=db" --filter "label=com.docker.compose.project=puppeteer"`.

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `.worktrees/axiom-split/puppeteer/agent_service/db.py` — all 13 CE table names confirmed
- Direct source inspection: `.worktrees/axiom-split/puppeteer/agent_service/main.py` lines 68-85, 820-851 — lifespan admin guard, /api/features, /api/licence endpoints confirmed
- Direct source inspection: `.worktrees/axiom-split/puppeteer/compose.server.yaml` — 7 named volumes confirmed
- Live system: `docker volume ls` — volume naming pattern `puppeteer_<name>` confirmed
- Live system: `docker exec puppeteer-db-1 psql` — table listing (main branch, 29 tables confirmed)
- Direct source inspection: `puppeteer/compose.server.yaml` (main branch) — same volume set, same project name

### Secondary (MEDIUM confidence)
- Existing mop_validation scripts (`test_local_stack.py`, `manage_incus_node.py`) — established patterns for script structure, path resolution, secrets loading

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools confirmed present in codebase and on system
- Architecture: HIGH — compose files, table names, and API endpoints verified by direct source inspection
- Pitfalls: HIGH — APScheduler table confirmed live; volume naming confirmed live; admin guard confirmed in source

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable — no fast-moving dependencies)
