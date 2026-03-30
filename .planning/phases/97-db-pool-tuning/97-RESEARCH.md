# Phase 97: DB Pool Tuning — Research

**Phase:** 97 — DB Pool Tuning
**Requirements:** POOL-01, POOL-02, POOL-03, POOL-04
**Researched:** 2026-03-30

---

## Summary

Phase 97 is a narrow, well-scoped infrastructure change: add asyncpg connection pool kwargs to `create_async_engine()` in `db.py`, guarded by the `IS_POSTGRES` flag, with one env-var knob and a `.env.example` template. Four requirements, one code file, one compose file, one new file, one new test file.

---

## Technical Findings

### SQLAlchemy asyncpg pool parameters

`create_async_engine()` from `sqlalchemy.ext.asyncio` accepts standard `QueuePool` kwargs:

```python
create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True,
)
```

- `pool_size`: steady-state connections kept open (default: 5)
- `max_overflow`: extra connections allowed above pool_size during bursts (default: 10)
- `pool_timeout`: seconds to wait for a free connection before raising `TimeoutError` (default: 30)
- `pool_recycle`: seconds before a connection is recycled to prevent stale TCP keepalive issues (default: -1 = no recycle)
- `pool_pre_ping=True`: before lending a connection, issue a cheap `SELECT 1` to verify liveness; stale connections discarded

**SQLite incompatibility:** SQLite uses `StaticPool` or `NullPool` — none of the above kwargs apply. Passing `pool_size` or `pool_recycle` to a SQLite engine raises `TypeError: Invalid argument(s) 'pool_size' sent to create_engine()`. Guard with `IS_POSTGRES`.

### Pattern for conditional engine kwargs

Standard approach — build a kwargs dict conditionally at module level:

```python
_pool_kwargs: dict = {}
if IS_POSTGRES:
    _pool_kwargs = {
        "pool_size": int(os.getenv("ASYNCPG_POOL_SIZE", "20")),
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

engine = create_async_engine(DATABASE_URL, echo=False, **_pool_kwargs)
```

This is idiomatic, keeps the engine creation line clean, and makes the conditional explicit.

### Existing code target — `db.py` line 15

```python
# BEFORE
engine = create_async_engine(DATABASE_URL, echo=False)

# AFTER
_pool_kwargs: dict = {}
if IS_POSTGRES:
    _pool_kwargs = {
        "pool_size": int(os.getenv("ASYNCPG_POOL_SIZE", "20")),
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
engine = create_async_engine(DATABASE_URL, echo=False, **_pool_kwargs)
```

No other files need changes for the pool itself.

### compose.server.yaml env var injection

The agent service environment block already uses `${VAR:-default}` syntax. Add one line:

```yaml
- ASYNCPG_POOL_SIZE=${ASYNCPG_POOL_SIZE:-20}
```

### .env.example — new file

`puppeteer/.env.example` does not exist. Create it as a comprehensive operator template. All real values in `puppeteer/.env` are secrets — `.env.example` uses placeholder values and explanatory comments. Include:

- DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY, API_KEY, ADMIN_PASSWORD
- AGENT_URL, NODE_IMAGE, NODE_EXECUTION_MODE
- DUCKDNS_TOKEN, DUCKDNS_DOMAIN, ACME_EMAIL, SERVER_HOSTNAME
- POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- ASYNCPG_POOL_SIZE (with tuning formula comment)
- AXIOM_LICENCE_KEY

### Test strategy — `test_pool_phase97.py`

Two categories of tests:

**Unit/import tests (no DB needed):**
1. `test_pool_kwargs_applied_for_postgres` — mock `IS_POSTGRES=True`, reload db module, assert engine pool kwargs present. Use `importlib.reload` + monkeypatch on `os.environ`.
2. `test_no_pool_kwargs_for_sqlite` — verify engine created without pool kwargs when `IS_POSTGRES=False` (default test environment).
3. `test_asyncpg_pool_size_env_var` — monkeypatch `ASYNCPG_POOL_SIZE=5`, verify the engine would use pool_size=5.
4. `test_env_example_contains_pool_size` — file existence + grep for `ASYNCPG_POOL_SIZE`.
5. `test_compose_yaml_contains_pool_size` — grep `compose.server.yaml` for `ASYNCPG_POOL_SIZE`.

**Note on reload approach:** `db.py` computes `IS_POSTGRES` and builds `_pool_kwargs` at import time. To test the Postgres path in a SQLite test environment, the test must either:
- Monkeypatch `os.environ["DATABASE_URL"]` before `importlib.reload(db)`, OR
- Directly test the conditional logic (like phase 96 tests did for IS_POSTGRES)

The phase 96 pattern (test the logic directly without reload) is safer and avoids asyncpg import errors. Apply the same approach.

---

## Validation Architecture

### Test file location
`puppeteer/tests/test_pool_phase97.py`

### Test commands
- Quick: `cd puppeteer && pytest tests/test_pool_phase97.py -v`
- Full backend suite: `cd puppeteer && pytest`

### Coverage
| Requirement | Test | Type |
|-------------|------|------|
| POOL-01 (pool kwargs) | `test_pool_kwargs_structure` | unit (logic) |
| POOL-02 (pre_ping) | `test_pool_pre_ping_included` | unit (logic) |
| POOL-03 (env var + .env.example + compose) | `test_asyncpg_pool_size_env_var`, `test_env_example_contains_pool_size`, `test_compose_yaml_contains_pool_size` | unit |
| POOL-04 (SQLite guard) | `test_no_pool_kwargs_for_sqlite` | unit (logic) |

All 4 requirements have automated test coverage. No manual-only verifications needed.

---

## ## RESEARCH COMPLETE

**Confidence:** High — narrow change with clear code targets and established project patterns.
**Key risk:** None significant. SQLite guard (`IS_POSTGRES`) is already in place from Phase 96.
**Recommendation:** Single plan wave, single plan file. All 4 requirements fit in one focused change set.
