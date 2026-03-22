# Phase 42: EE Validation Pass - Research

**Researched:** 2026-03-21
**Domain:** Python validation scripting, Docker Compose orchestration, FastAPI RBAC, Axiom EE plugin
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Script structure**
- Single script: `mop_validation/scripts/verify_ee_pass.py`
- Covers all three requirements (EEV-01, EEV-02, EEV-03) sequentially in one run
- `[PASS]` / `[FAIL]` per requirement ID, summary table at end — same pattern as all prior phases
- Exit non-zero on any failure; CI-safe

**Pre-flight checks (before main assertions)**
- Assert `GET /api/features` all true AND `GET /api/licence` returns `{"edition": "enterprise"}`
- If either fails: exit immediately with exact commands printed:
  ```
  Run: python mop_validation/scripts/patch_ee_source.py
       docker compose -f puppeteer/compose.server.yaml up -d
  Then re-run this script.
  ```
- This ensures the script is non-destructive and produces clear operator guidance if preconditions aren't met

**Stack setup ownership**
- Operator pre-runs: script assumes the EE stack is already up with a valid `AXIOM_LICENCE_KEY`
- Script does NOT run `patch_ee_source.py` or restart the stack itself — non-destructive by default (matches Phase 38/41 pattern)

**EEV-01 — Feature flags + table count + EE routes**
- Feature flags: `GET /api/features` — assert all values true
- Table count: `docker exec puppeteer-postgres-1 psql` against `information_schema.tables` — assert exactly 28 (13 CE + 15 EE)
- EE routes: same 7 routes tested in CEV-01 (`verify_ce_stubs.py`), but inverted assertion — assert each returns any non-402 status (2xx or 403 both count as EE live)
- All three assertions bundled under the EEV-01 section of the script

**EEV-02 — Licence gating (startup-only)**
- Fully automated restart cycle — script handles the docker compose down/up sequence:
  1. Assert features still true at runtime (before any restart)
  2. Read `mop_validation/secrets/ee/ee_expired_licence.env`, inject `AXIOM_LICENCE_KEY` as env override
  3. Run `docker compose down` + `docker compose up -d` with expired key
  4. Wait for API readiness
  5. Assert `GET /api/features` all false (expired key = CE-degraded mode)
  6. Restore: restart once more with valid licence (`ee_valid_licence.env`) — stack left healthy after EEV-02
  7. Wait for API readiness again before proceeding to EEV-03
- Stack is left in a known-good EE state after EEV-02 completes (ready for Phase 43)

**EEV-03 — RBAC on licence endpoint**
- Script creates temp users at the start of the EEV-03 section via `POST /admin/users`
- User names: `eev03_operator` (role: operator) and `eev03_viewer` (role: viewer)
- Script logs in as each, gets their tokens via `POST /auth/login`
- Asserts `GET /api/licence` returns HTTP 403 for both operator and viewer tokens
- Asserts `GET /api/licence` returns HTTP 200 for admin token (positive confirmation)
- Cleanup: script calls `DELETE /admin/users/{id}` for both temp users after assertions complete

**Claude's Discretion**
- Exact wait/retry logic between docker compose restarts (polling interval, timeout)
- `docker compose` v1 vs v2 command detection (prefer `docker compose` plugin if available)
- Exact postgres container name detection (`puppeteer-postgres-1` hardcoded, matching prior scripts)
- Error messaging when `mop_validation/secrets/ee/ee_expired_licence.env` or `ee_valid_licence.env` is missing
- Summary table formatting at end

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EEV-01 | CE+EE combined install: `GET /api/features` all true, 28 tables (13 CE + 15 EE), EE routes return real responses | Feature flag endpoint is unauthenticated; table count via `docker exec psql` (pattern from verify_ce_tables.py); EE routes same 7 from verify_ce_stubs.py, inverted to non-402 |
| EEV-02 | Licence gating is startup-only: change to expired licence at runtime, confirm features remain true until restart, then false after restart | `AXIOM_LICENCE_KEY` env var injected via `docker compose up -e` override; wait_for_stack() pattern from prior scripts; expired key in `mop_validation/secrets/ee/ee_expired_licence.env` |
| EEV-03 | `GET /api/licence` admin endpoint returns full licence detail; non-admin (operator/viewer) gets 403 | CRITICAL GAP: `GET /api/licence` currently uses `require_auth` (any authenticated user), NOT admin-only. Must be patched to use `require_permission("licence:read")` or role check before EEV-03 can pass. EE users router provides `POST /admin/users` and `DELETE /admin/users/{username}` (path param is username string, not numeric ID) |
</phase_requirements>

## Summary

Phase 42 writes a single validation script (`mop_validation/scripts/verify_ee_pass.py`) covering three EE acceptance criteria. The script structure follows the exact pattern established in Phases 38–41: `[PASS]`/`[FAIL]` output, summary table, non-zero exit on any failure, non-destructive pre-flight checks.

All reusable assets exist and have been verified. The 7 EE stub routes are hardcoded in `verify_ce_stubs.py` and can be copied verbatim. The postgres table count pattern, API readiness wait loop, and admin token acquisition are all copy-paste from prior scripts. The `ee_valid_licence.env` and `ee_expired_licence.env` files exist in `mop_validation/secrets/ee/`.

**Critical gap identified:** `GET /api/licence` in `main.py` uses `require_auth` (any authenticated user), but EEV-03 requires HTTP 403 for operator/viewer. The endpoint must be patched to admin-only before the EEV-03 assertion can pass. This is a backend code change in `puppeteer/agent_service/main.py` that must ship as part of Phase 42.

**Primary recommendation:** Phase 42 has two deliverables: (1) patch `GET /api/licence` to admin-only in `main.py`, rebuild the EE image, and (2) write `verify_ee_pass.py` against the patched stack.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | >=2.28 | HTTP calls to agent API | Used in all prior validation scripts |
| subprocess | stdlib | `docker compose` and `docker exec psql` | Used in verify_ce_tables.py and verify_ce_install.py |
| pathlib.Path | stdlib | File path handling | Established pattern across all scripts |
| urllib3 | >=1.26 | Disable SSL warnings for self-signed cert | `urllib3.disable_warnings(InsecureRequestWarning)` |

### Compose Command Pattern
| Command | Usage | Confidence |
|---------|-------|------------|
| `docker compose -f compose.server.yaml down` | Stop EEV-02 restart cycle | HIGH — from 41-03-RESULTS.md |
| `docker compose -f compose.server.yaml up -d -e AXIOM_LICENCE_KEY=...` | Restart with env override | HIGH — standard docker compose v2 |

**Installation:** All dependencies are already installed in the project venv.

## Architecture Patterns

### Recommended Script Structure
```
mop_validation/scripts/
└── verify_ee_pass.py   # single-file, covers EEV-01, EEV-02, EEV-03 sequentially
```

### Pattern 1: Shared Helper Functions (copy from prior scripts)
**What:** `load_env()`, `wait_for_stack()`, `get_admin_token()`, `get_postgres_container()` are identical across all Phase 38–41 scripts.
**When to use:** Copy verbatim — do not reinvent.
**Key signatures:**
```python
def load_env(path: Path) -> dict          # parses key=value env file
def wait_for_stack(base_url, timeout=90)  # polls /api/features every 3s
def get_admin_token(base_url, password)   # POST /auth/login (form-encoded)
def get_postgres_container() -> str       # docker ps filter, fallback puppeteer-db-1
```

### Pattern 2: EEV-02 Compose Restart Cycle
**What:** Stop stack, restart with env override for expired key, assert features false, restore with valid key.
**When to use:** The EEV-02 restart section of the script.
**Compose file path:** `~/Development/master_of_puppets/puppeteer/compose.server.yaml` (main branch — `.worktrees/axiom-split/` no longer exists)
**Docker compose env override syntax:**
```python
subprocess.run([
    "docker", "compose",
    "-f", str(COMPOSE_FILE),
    "up", "-d",
    "-e", f"AXIOM_LICENCE_KEY={licence_key}",
], ...)
```
**Important:** `docker compose down` then `docker compose up -d -e KEY=val` — the `-e` flag is for `up`, not `down`. The env var only needs overriding at `up` time.

### Pattern 3: Postgres Table Count
**What:** Run psql inside the db container to count tables.
**Container name:** Use `get_postgres_container()` (dynamic discovery, fallback `puppeteer-db-1`).
**Query:**
```python
query = (
    "SELECT count(*) FROM pg_tables "
    "WHERE schemaname='public' AND tablename != 'apscheduler_jobs';"
)
result = subprocess.run(
    ["docker", "exec", pg_container,
     "psql", "-U", "puppet", "-d", "puppet_db", "-t", "-c", query],
    ...
)
count = int(result.stdout.strip())
```
**Expected count for EEV-01:** 28 (not 13)

### Pattern 4: EEV-03 Temp User Lifecycle
**What:** Create users with `POST /admin/users`, acquire tokens, assert 403 on licence endpoint, delete users.
**Key facts from code inspection:**
- `POST /admin/users` returns HTTP **201** (not 200) — `status_code=201` in EE router
- `DELETE /admin/users/{username}` path param is the **username string** (not a numeric ID)
- `POST /admin/users` requires `require_permission("users:write")` — admin token is sufficient
- Admin token bypasses all permission checks (confirmed in `deps.py`: `if role == "admin": return current_user`)

### Anti-Patterns to Avoid
- **Using `DELETE /admin/users/{id}` with a numeric ID:** The route uses username as path param, not a DB integer ID.
- **Assuming `POST /admin/users` returns 200:** It returns 201 — check `resp.status_code == 201`.
- **Targeting `.worktrees/axiom-split/puppeteer/compose.server.yaml`:** That worktree no longer exists. Target `~/Development/master_of_puppets/puppeteer/compose.server.yaml`.
- **Leaving stack in expired-key state:** EEV-02 MUST restore the valid licence before EEV-03 — temp user creation via `POST /admin/users` requires a running EE stack with `users_router` mounted.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client for API calls | Custom socket/urllib | `requests` with `verify=False` | Already used in all prior scripts |
| Postgres table count | SQLAlchemy or pg driver | `docker exec psql -t -c` | No external DB driver needed; established pattern |
| Wait-for-ready loop | Custom polling | `wait_for_stack()` from prior scripts | Identical implementation across all scripts |
| Env file parsing | configparser or dotenv lib | `load_env()` from prior scripts | Simple, no external dependency |

## Critical Findings

### Finding 1: EEV-03 Requires a Backend Patch

**What:** `GET /api/licence` in `puppeteer/agent_service/main.py` line 838–851 uses `Depends(require_auth)`. This allows any authenticated user (operator, viewer) to read licence details.

**EEV-03 requires:** HTTP 403 for operator/viewer, HTTP 200 for admin.

**Current behaviour:** Both admin AND operator/viewer receive HTTP 200 with the licence payload.

**Fix required:** Change the dependency from `require_auth` to admin-only enforcement. Two options:
- Option A (simplest): Change to `require_permission("licence:read")` and ensure only `admin` role has that permission seeded.
- Option B (explicit): Change to a custom `require_admin` check using `if current_user.role != "admin": raise HTTPException(403)`.

**Impact on Phase 42:** The backend change must be made AND the EE image rebuilt before `verify_ee_pass.py` can pass EEV-03. Phase 42 plan must include a task for the backend patch + image rebuild.

**Confidence:** HIGH — verified by reading `main.py` line 838 directly.

### Finding 2: Compose File Location Changed

**What:** Phases 38–41 targeted `.worktrees/axiom-split/puppeteer/compose.server.yaml`. That worktree no longer exists (`git worktree list` confirms only main branch).

**Phase 41 EE restore** (confirmed in 41-03-RESULTS.md) used `compose.server.yaml` directly from the puppeteer directory, which is `~/Development/master_of_puppets/puppeteer/compose.server.yaml`.

**Impact:** `COMPOSE_FILE` in the script must point to `MOP_DIR / "puppeteer" / "compose.server.yaml"`.

**Confidence:** HIGH — confirmed by git worktree list and Phase 41 results.

### Finding 3: teardown_soft.sh and teardown_hard.sh Still Reference Old Worktree Path

**What:** Both teardown scripts in `mop_validation/scripts/` hardcode `CE_DIR="$REPO_ROOT/.worktrees/axiom-split/puppeteer"`. This is a latent bug but does not affect Phase 42 since the script does its own compose down/up.

**Impact on Phase 42:** Not blocking — Phase 42 script uses `subprocess` directly, not the teardown scripts. Document as a known issue in the gap report (Phase 45).

### Finding 4: EE Stack AXIOM_LICENCE_KEY Is Already Wired

**What:** `compose.server.yaml` line 71: `- AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` — the env var is passed from the shell/`.env` file. To test with expired key, either: (a) set `AXIOM_LICENCE_KEY` in the shell before `docker compose up`, or (b) use `docker compose up -e AXIOM_LICENCE_KEY=<value>`.

**Recommended approach for EEV-02:** Read the expired key from `ee_expired_licence.env`, extract the value, and pass via `subprocess.run` with `env` override or `-e` flag.

**Alternative approach:** Write a temporary env file and pass via `--env-file`. Simpler and avoids shell escaping issues with long JWT strings.

### Finding 5: EE Router Users Are Available Only When EE Stack Is Running

**What:** `POST /admin/users` and `DELETE /admin/users/{username}` are mounted by `ee.users.router` which is only active when `axiom-ee` plugin loads with a valid licence. In CE mode or expired-key mode, these routes return 402.

**Impact on EEV-03:** EEV-02 MUST complete its restore step (restart with valid licence + wait for readiness) before EEV-03 can create temp users. The CONTEXT.md already accounts for this correctly.

## Common Pitfalls

### Pitfall 1: Using Username vs ID for Delete Route
**What goes wrong:** Script passes a numeric ID to `DELETE /admin/users/{id}` and gets 404 or 422.
**Why it happens:** CONTEXT.md says `{id}` but the actual route in `ee/users/router.py` line 37 uses `{username}`.
**How to avoid:** Use `DELETE /admin/users/eev03_operator` and `DELETE /admin/users/eev03_viewer` — the path param is the username string.
**Warning signs:** HTTP 422 Unprocessable Entity when calling delete with numeric ID.

### Pitfall 2: POST /admin/users Returns 201 Not 200
**What goes wrong:** Script checks `resp.status_code == 200` on user creation and incorrectly reports failure.
**Why it happens:** EE users router line 25: `@users_router.post("/admin/users", ..., status_code=201)`.
**How to avoid:** Assert `resp.status_code == 201` for user creation; use `resp.ok` (status < 400) as a safe alternative.

### Pitfall 3: Docker Compose Down/Up Timing
**What goes wrong:** Script calls `docker compose up -d` immediately after `docker compose down` and the postgres healthcheck hasn't passed yet — agent container fails to connect to DB.
**Why it happens:** The `db` service has a healthcheck (5s interval, 5 retries) that `agent` service depends on. `docker compose up -d` returns as soon as containers are scheduled, not when they're healthy.
**How to avoid:** Use `wait_for_stack()` with a 120s timeout after `docker compose up -d`. 90s is usually sufficient but use 120s for the EEV-02 restart cycle since postgres also needs to recover.

### Pitfall 4: AXIOM_LICENCE_KEY Shell Escaping
**What goes wrong:** Passing the long base64url JWT as a shell argument gets mangled by subprocess escaping.
**Why it happens:** The JWT contains `_`, `-`, `.` characters and is ~300 chars long — shell quoting issues can truncate or corrupt it.
**How to avoid:** Use `subprocess.run(..., env={**os.environ, "AXIOM_LICENCE_KEY": key_value})` — set via Python dict, not shell argument. This avoids all shell escaping issues entirely. Use `--env-file` approach as an alternative.

### Pitfall 5: Features Endpoint Returns Wrong Keys After EEV-02 Restore
**What goes wrong:** After restart with valid licence, `GET /api/features` returns some features as false (router mount failed silently).
**Why it happens:** EE router mount exceptions are swallowed (try/except in `plugin.py` lines 113–168). A transient import error leaves a feature flag false without crashing startup.
**How to avoid:** Assert ALL feature keys are true in the post-restore check, not just that any are true. Log the actual response on failure.

## Code Examples

Verified patterns from source code inspection:

### Load Licence Value from .env File
```python
# Source: load_env() pattern from verify_ce_stubs.py
def load_licence_key(env_path: Path) -> str:
    env = load_env(env_path)
    key = env.get("AXIOM_LICENCE_KEY", "")
    if not key:
        print(f"[ERROR] AXIOM_LICENCE_KEY not found in {env_path}")
        sys.exit(1)
    return key
```

### Docker Compose Down/Up with Env Override (No Shell Escaping Issues)
```python
# Source: Derived from compose.server.yaml line 71 + subprocess pattern
import os, subprocess

def restart_with_licence(compose_file: Path, licence_key: str, timeout: int = 120) -> bool:
    env = {**os.environ, "AXIOM_LICENCE_KEY": licence_key}
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "down"],
        check=True, env=env,
    )
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        check=True, env=env,
    )
    return wait_for_stack(BASE_URL, timeout=timeout)
```

### Assert All Features True
```python
# Source: inverted from verify_ce_install.py check_features()
def assert_features_true(base_url: str) -> tuple[bool, dict]:
    resp = requests.get(f"{base_url}/api/features", verify=False, timeout=10)
    features = resp.json()
    all_true = all(features.values())
    return all_true, features
```

### EEV-01 Non-402 Route Assertion (Inverted from verify_ce_stubs.py)
```python
# Source: verify_ce_stubs.py EE_STUB_ROUTES — inverted assertion
EE_STUB_ROUTES = [
    ("GET",  "/api/blueprints",          "foundry"),
    ("GET",  "/api/smelter/ingredients", "smelter"),
    ("GET",  "/admin/audit-log",         "audit"),
    ("GET",  "/api/webhooks",            "webhooks"),
    ("GET",  "/api/admin/triggers",      "triggers"),
    ("GET",  "/admin/users",             "users/rbac"),
    ("GET",  "/auth/me/api-keys",        "auth_ext"),
]

# EE active: any non-402 status (2xx or 403 both count)
passed = resp.status_code != 402
```

### EEV-03 Temp User Create/Delete
```python
# Source: ee/users/router.py lines 25-48
# POST returns 201; DELETE path param is username string

def create_temp_user(base_url, token, username, role):
    resp = requests.post(
        f"{base_url}/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": username, "password": "TempPass123!", "role": role},
        verify=False, timeout=10,
    )
    return resp.status_code == 201

def delete_temp_user(base_url, token, username):
    resp = requests.delete(
        f"{base_url}/admin/users/{username}",   # username string, not numeric ID
        headers={"Authorization": f"Bearer {token}"},
        verify=False, timeout=10,
    )
    return resp.status_code == 200
```

### Required Backend Patch for EEV-03
```python
# File: puppeteer/agent_service/main.py line 838
# Current (BREAKS EEV-03):
@app.get("/api/licence", tags=["System"])
async def get_licence(request: Request, current_user: User = Depends(require_auth)):

# Fixed (admin-only):
@app.get("/api/licence", tags=["System"])
async def get_licence(request: Request, current_user: User = Depends(require_auth)):
    if current_user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Worktree at `.worktrees/axiom-split/` | Main branch `puppeteer/compose.server.yaml` | Phase 41 (EE restore) | COMPOSE_FILE path must use `MOP_DIR / "puppeteer" / "compose.server.yaml"` |
| Hard teardown for CE/EE switch | docker compose down/up with env override | Phase 42 (new) | Preserves pgdata/certs-volume between EEV-02 cycles |

**Deprecated/outdated:**
- `.worktrees/axiom-split/` path: used in teardown scripts but no longer valid — scripts fail if run as-is. Phase 42 validation script uses direct subprocess calls instead.

## Open Questions

1. **Admin-only fix for `GET /api/licence` — which approach?**
   - What we know: The endpoint uses `require_auth`. Two fix options: explicit role check inline, or `require_permission("licence:read")` with seeded admin-only permission.
   - What's unclear: Whether a `licence:read` permission needs to be seeded in the DB (which would require a migration or startup seed change).
   - Recommendation: Use the inline role check (`if current_user.role != "admin": raise HTTPException(403)`) — no seed change, no migration, aligned with how admin-only bypass works in `deps.py`.

2. **`docker compose down` scope for EEV-02 — does it need `-v`?**
   - What we know: EEV-02 only needs to swap the `AXIOM_LICENCE_KEY` env var — it does NOT need a clean DB. `down` without `-v` preserves pgdata (and therefore EE tables and all test state).
   - What's unclear: Nothing — `down` without `-v` is correct here.
   - Recommendation: Use `down` (no `-v`) for EEV-02. Only use `down -v` for hard teardown (INST-02 pattern).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (puppeteer/agent_service/tests/) |
| Config file | puppeteer/pytest.ini or pyproject.toml |
| Quick run command | `cd puppeteer && pytest tests/test_licence.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EEV-01 | All features true + 28 tables + EE routes non-402 | integration (external script) | `python3 mop_validation/scripts/verify_ee_pass.py` | ❌ Wave 0 |
| EEV-02 | Expired licence disables features after restart | integration (external script) | `python3 mop_validation/scripts/verify_ee_pass.py` | ❌ Wave 0 |
| EEV-03 | Licence endpoint admin-only | integration (external script) | `python3 mop_validation/scripts/verify_ee_pass.py` | ❌ Wave 0 |
| GET /api/licence admin-only (backend patch) | Role check returns 403 for non-admin | unit | `cd puppeteer && pytest tests/test_licence.py -x` | ✅ exists |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_licence.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** `python3 mop_validation/scripts/verify_ee_pass.py` exits 0 before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `mop_validation/scripts/verify_ee_pass.py` — covers EEV-01, EEV-02, EEV-03
- [ ] Backend patch in `puppeteer/agent_service/main.py` (`GET /api/licence` admin-only) — prerequisite for EEV-03
- [ ] Rebuilt EE Docker image after backend patch — required for integration assertions to pass

## Sources

### Primary (HIGH confidence)
- Direct file reads: `puppeteer/agent_service/main.py` lines 838–851 — `GET /api/licence` current implementation
- Direct file reads: `axiom-ee/ee/users/router.py` lines 18–48 — `POST /admin/users` (status 201), `DELETE /admin/users/{username}` (string path param)
- Direct file reads: `axiom-ee/ee/plugin.py` lines 41–172 — EE plugin register() sequence, feature flag assignment
- Direct file reads: `mop_validation/scripts/verify_ce_stubs.py` — `EE_STUB_ROUTES` list (7 routes), helper functions
- Direct file reads: `mop_validation/scripts/verify_ce_tables.py` — psql table count pattern
- Direct file reads: `mop_validation/scripts/verify_ce_install.py` — `[PASS]`/`[FAIL]` output pattern, summary table structure
- Direct file reads: `mop_validation/secrets/ee/ee_valid_licence.env` + `ee_expired_licence.env` — files confirmed present with correct `AXIOM_LICENCE_KEY` format
- Direct file reads: `.planning/phases/41-ce-validation-pass/41-03-RESULTS.md` — confirmed `compose.server.yaml` path and `puppeteer-db-1` container name
- Direct reads: `puppeteer/compose.server.yaml` — `AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` env var wiring confirmed
- `git worktree list` — confirmed `.worktrees/axiom-split/` no longer exists

### Secondary (MEDIUM confidence)
- `puppeteer/agent_service/deps.py` — `require_permission()` admin bypass logic confirmed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed in existing scripts
- Architecture: HIGH — verified from source code and Phase 41 results
- Pitfalls: HIGH — based on direct code inspection, not assumptions
- EEV-03 gap: HIGH — verified line 838 of main.py directly

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable codebase — no third-party library churn risk)
