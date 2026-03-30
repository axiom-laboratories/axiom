## RESEARCH COMPLETE

# Phase 96: Foundation — Research

**Researched:** 2026-03-30
**Phase:** 96 — Foundation (v17.0 Scale Hardening)
**Requirements:** FOUND-01, FOUND-02, FOUND-03

---

## Codebase State — What Exists Today

### requirements.txt
- `apscheduler` is unpinned: a bare `apscheduler` line. v4 would silently install on `pip install`.
- `packaging` is already present — `importlib.metadata` or `packaging.version.parse()` can both be used for the version check.

### db.py
- Line 12: `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")` — already a module-level constant.
- No `IS_POSTGRES` constant exists. It must be added as `IS_POSTGRES = DATABASE_URL.startswith("postgresql")` immediately after `DATABASE_URL`.
- `create_async_engine` is called at line 14 with no pool kwargs. IS_POSTGRES will gate the pool changes in Phase 97.
- Existing imports already include all needed SQLAlchemy symbols.

### scheduler_service.py
- Line 43: `self.scheduler = AsyncIOScheduler()` — no `job_defaults` passed.
- Line 138: `misfire_grace_time=60` is hardcoded as a per-job override in `sync_scheduler()`. After Phase 96, this per-job override should be removed (the global `job_defaults` will cover it).
- Internal system jobs use `id='__prune_node_stats__'`, `id='__prune_execution_history__'`, `id='__dispatch_timeout_sweeper__'` — prefixed with `__`, confirming the convention already exists.
- `scheduler_service.py` does not currently import anything from `db.py` directly (it imports via `db_module`). Adding `IS_POSTGRES` will be the first named import from db constants.

### main.py lifespan (lines 75–173)
- Startup sequence: `init_db()` → licence → EE plugins → permission cache → HMAC backfill → admin bootstrap → `scheduler_service.start()` → `sync_scheduler()` → node monitor task.
- Existing hard crashes in lifespan: admin password missing prints a warning but doesn't crash; ENCRYPTION_KEY missing raises inside security.py at import time. Pattern for a hard RuntimeError at startup for a bad dependency version is consistent with how the codebase guards bad config.
- APScheduler version check should slot in **before** `scheduler_service.start()` — it guards against operating with a broken scheduler.
- SQLite warning should slot in **right after** `init_db()` — surfaces immediately and is the earliest useful place.

---

## Implementation Details

### FOUND-01 — APScheduler Version Pin + Startup Assertion

**requirements.txt change:**
```
apscheduler>=3.10,<4.0
```

**Startup check (in lifespan, before `scheduler_service.start()`):**
```python
import importlib.metadata as _importlib_metadata
_aps_version = _importlib_metadata.version("apscheduler")
if _aps_version.startswith("4."):
    raise RuntimeError("APScheduler v4 detected — pin to >=3.10,<4.0")
```

Alternatively using `packaging.version.parse()` (already a dep):
```python
from packaging.version import Version as _Version
if _Version(_aps_version) >= _Version("4.0"):
    raise RuntimeError("APScheduler v4 detected — pin to >=3.10,<4.0")
```

Both are correct. `packaging.version.parse()` is more robust for edge cases like `4.0.0a1`. Use it.

### FOUND-02 — IS_POSTGRES Export

**db.py change (after line 12):**
```python
IS_POSTGRES: bool = DATABASE_URL.startswith("postgresql")
```

Module-level, evaluated once at import time. No imports needed — just a boolean expression.

**Consumer imports:**
```python
from agent_service.db import IS_POSTGRES
```

This import needs to be added at the top of `job_service.py` and `scheduler_service.py`. Currently neither file imports `IS_POSTGRES` (it doesn't exist). The CONTEXT.md confirms both files need it for subsequent phases (Phase 97 pool kwargs, Phase 98 SKIP LOCKED).

### FOUND-03 — APScheduler Global job_defaults

**scheduler_service.py change (line 43):**
```python
self.scheduler = AsyncIOScheduler(
    job_defaults={
        "misfire_grace_time": 60,
        "coalesce": True,
        "max_instances": 1,
    }
)
```

**Consequence:** The per-job `misfire_grace_time=60` on line 138 of `sync_scheduler()` becomes redundant. It should be removed from the `add_job()` call in `sync_scheduler()`. The internal system jobs in `start()` do not pass `misfire_grace_time` — they will inherit from `job_defaults`, which is correct.

### SQLite Startup Warning

**In lifespan, after `await init_db()`:**
```python
import sys as _sys
from agent_service.db import IS_POSTGRES
if not IS_POSTGRES:
    print(
        "WARNING: SQLite detected — SKIP LOCKED not active. Use Postgres for production.",
        file=_sys.stderr,
    )
```

CONTEXT.md specifies `print(..., file=sys.stderr)` — not `logging.warning()` — so a developer running the backend raw can't miss it.

---

## Test Strategy

### What to test
1. `IS_POSTGRES` is `True` when `DATABASE_URL` starts with `postgresql`; `False` for `sqlite+aiosqlite://`.
2. `AsyncIOScheduler` is constructed with `job_defaults` containing all three keys at their specified values.
3. APScheduler version assertion raises `RuntimeError` when version string starts with `4.`.

### Test file
`puppeteer/tests/test_foundation_phase96.py`

Existing patterns:
- Tests use `pytest` + `pytest_asyncio`.
- In-memory SQLite engines are created in fixtures with `create_async_engine("sqlite+aiosqlite:///:memory:")`.
- Tests import directly from `agent_service.*` modules.

Tests are unit-level and fast — no full-app startup needed. Mock `importlib.metadata.version` to test the version assertion path.

---

## Validation Architecture

### Phase 96 Validation Strategy

| Concern | Test Approach |
|---------|--------------|
| IS_POSTGRES value correctness | Unit test with two DATABASE_URL strings |
| IS_POSTGRES importable from db.py | Import assertion in test |
| job_defaults set on AsyncIOScheduler | Inspect `scheduler.scheduler._job_defaults` after construction |
| APScheduler version guard fires | Mock `importlib.metadata.version` to return `"4.0.0"`, assert RuntimeError |
| requirements.txt pin format | Read file, assert `apscheduler>=3.10,<4.0` line present |

Run command: `cd puppeteer && pytest tests/test_foundation_phase96.py -v`

---

## Files to Touch

| File | Change |
|------|--------|
| `puppeteer/requirements.txt` | Pin `apscheduler>=3.10,<4.0` |
| `puppeteer/agent_service/db.py` | Add `IS_POSTGRES` constant after `DATABASE_URL` |
| `puppeteer/agent_service/services/scheduler_service.py` | Add `job_defaults` to `AsyncIOScheduler()`; remove redundant per-job `misfire_grace_time`; add `IS_POSTGRES` import |
| `puppeteer/agent_service/main.py` | Add APScheduler version assertion in lifespan; add SQLite startup warning |
| `puppeteer/agent_service/services/job_service.py` | Add `IS_POSTGRES` import (no behaviour change yet — just makes it available for Phase 98) |
| `puppeteer/tests/test_foundation_phase96.py` | New test file covering all success criteria |

---

## Risk Assessment

**Low risk overall.** All changes are:
- Additive constants (IS_POSTGRES)
- Passive guards (version assertion, startup warning)
- Config defaults that match current per-job values (`misfire_grace_time=60` already in use)

The only execution risk is removing the per-job `misfire_grace_time=60` override from `sync_scheduler()`. This is safe because the global `job_defaults` provides the same value. The internal scheduler jobs in `start()` do not specify `misfire_grace_time`, so adding a global default is additive for them.

**Docker prod deployments:** Docker always sets `DATABASE_URL=postgresql+asyncpg://...` so `IS_POSTGRES=True` — the SQLite warning will never fire in production.
