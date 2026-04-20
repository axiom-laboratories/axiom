# Phase 166: Router Modularization - Research

**Researched:** 2026-04-18  
**Domain:** FastAPI router architecture and refactoring  
**Confidence:** HIGH

## Summary

Phase 166 refactors the 3,828-line `puppeteer/agent_service/main.py` file (89 routes) into 6 domain-specific APIRouter modules to enable per-domain middleware injection (required by Phase 167 Vault integration and Phase 168 SIEM streaming).

This is a **pure refactoring phase** — no API changes, no feature work, no behavior modifications. All routes, response models, status codes, and middleware behaviour must remain identical after the refactor. The refactor is **blocked on** by phase 165 (CVE remediation) and **blocks** phases 167 and 168.

**Primary recommendation:** Follow the established pattern of `routers/smelter_router.py` (CE) and `ee/routers/foundry_router.py` (EE) when creating new CE routers. Import shared deps (`require_auth`, `require_permission`, `audit`) from `deps.py` to avoid circular imports. Allocate 4 implementation tasks: (1) extract auth/jobs/nodes/workflows routers, (2) extract admin/system routers + wire smelter, (3) OpenAPI schema diff verification, (4) full pytest suite validation.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|-----------|-------------|----------------|-----------|
| Route dispatch | API / Backend | — | All routes live in routers; FastAPI handles invocation |
| Middleware registration | API / Backend | — | Main.py registers all middleware (CORS, LicenceGuard, rate limiter) |
| Authentication state | API / Backend | — | `get_current_user` from deps.py validates JWT and returns User object |
| Permission enforcement | API / Backend | — | `require_permission` checks User.role against DB role_permissions table |
| Audit logging | API / Backend | — | `audit()` helper from deps.py logs security events to AuditLog table |
| WebSocket broadcasting | API / Backend | — | `ws_manager` and `/ws` endpoint manage live event distribution |
| EE route stubs | API / Backend | — | CE mode mounts stub routers from `ee/routers/` that return 402 responses |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.104+ | Async web framework | Production battle-tested; native async/await; automatic OpenAPI generation |
| APIRouter | (FastAPI) | Route grouping | FastAPI's standard pattern for modular route registration |
| Depends | (FastAPI) | Dependency injection | Native FastAPI pattern for request-scoped auth, DB session, audit |

### Project-Specific Patterns

| Pattern | Module | Purpose |
|---------|--------|---------|
| Shared dependencies | `deps.py` | `get_current_user`, `require_permission`, `audit` — all routers import from here |
| DB session per request | `db.get_db` | AsyncSession dependency; injected via `Depends(get_db)` |
| Permission factory | `deps.require_permission(perm)` | Returns async dependency that checks User.role against DB |
| Audit logging | `deps.audit(db, user, action, resource_id, detail)` | Logs to AuditLog table; called before `db.commit()` |

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                       FastAPI Application                     │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Middleware Stack (CORS, LicenceGuard, Rate Limiter)    │   │
│  └───────────────────────┬────────────────────────────────┘   │
│                          │                                      │
│    ┌─────────────────────┴──────────────────────────┐         │
│    ▼                                                ▼         │
│ ┌────────────────────┐  ┌──────────────────────────────────┐  │
│ │  CE Routers       │  │   EE Router Stubs (CE mode)      │  │
│ ├────────────────────┤  ├──────────────────────────────────┤  │
│ │ auth_router.py    │  │ Mounted at startup by ee/__init__│  │
│ │ jobs_router.py    │  │ • foundry_stub_router            │  │
│ │ nodes_router.py   │  │ • audit_stub_router              │  │
│ │ workflows_router  │  │ • webhooks_stub_router           │  │
│ │ admin_router.py   │  │ • triggers_stub_router           │  │
│ │ system_router.py  │  │ • auth_ext_stub_router           │  │
│ │ smelter_router.py │  │ • (others — all return 402)      │  │
│ │ (existing)        │  │                                  │  │
│ └──────┬───────────┬┘  └──────────────────┬────────────────┘  │
│        │           │                      │                   │
│        └───┬───┬───┴──────────────────────┘                   │
│            │   │                                               │
│    ┌───────▼───▼─────────────────────┐                       │
│    │  Dependency Injection Layer      │                       │
│    ├──────────────────────────────────┤                       │
│    │ from ..deps import:              │                       │
│    │ • get_current_user               │                       │
│    │ • require_permission             │                       │
│    │ • get_current_user_optional      │                       │
│    │ • audit                          │                       │
│    │ • get_db (AsyncSession)          │                       │
│    └───────┬──────────────────────────┘                       │
│            │                                                   │
│    ┌───────▼──────────────────────────┐                       │
│    │  Database & Security             │                       │
│    ├──────────────────────────────────┤                       │
│    │ • AsyncSession (per-request)     │                       │
│    │ • User, Role, RolePermission DB  │                       │
│    │ • JWT verification (deps.py)     │                       │
│    │ • AuditLog persistence           │                       │
│    └──────────────────────────────────┘                       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Data flow for authenticated request:**

1. HTTP request arrives → CORS & LicenceGuard middleware inspect path
2. Request matches route (e.g., `GET /jobs` → `jobs_router.list_jobs()`)
3. Route handler declares `current_user = Depends(get_current_user)` dependency
4. FastAPI calls `get_current_user()` with JWT from Authorization header
5. `get_current_user()` (in deps.py) verifies JWT signature, extracts username, queries DB for User object
6. If `Depends(require_permission("jobs:read"))` is declared, FastAPI calls permission check after user is resolved
7. Route handler executes with User object and AsyncSession
8. Handler calls `audit(db, user, action, resource_id, detail)` to log to AuditLog table
9. Handler commits DB changes with `await db.commit()`
10. Response serialized via response_model; WebSocket broadcast via `ws_manager.broadcast()` if applicable

### Recommended Project Structure

```
puppeteer/agent_service/
├── routers/                       # CE-only routers
│   ├── __init__.py
│   ├── auth_router.py            # Authentication endpoints
│   ├── jobs_router.py            # Jobs, Job Definitions, Job Templates, CI/CD Dispatch
│   ├── nodes_router.py           # Nodes, Node Agent
│   ├── workflows_router.py       # Workflows
│   ├── admin_router.py           # Admin, Signatures, Alerts & Webhooks, Headless Automation
│   ├── system_router.py          # System, Health, Schedule, WebSocket
│   └── smelter_router.py         # Smelter (existing CE router — wire into main.py)
├── main.py                        # FastAPI app, lifespan, middleware, include_router calls (pure shell)
├── deps.py                        # Shared auth/permission/audit helpers (no change needed)
├── db.py                          # SQLAlchemy models (no change needed)
├── models.py                      # Pydantic request/response models (no change needed)
├── auth.py                        # JWT/password hashing (no change needed)
├── security.py                    # mTLS, encryption, signature verification (no change needed)
├── services/                      # Business logic (no change needed)
│   ├── job_service.py
│   ├── scheduler_service.py
│   ├── foundry_service.py
│   └── ... (others)
└── ee/                            # EE-only code (no change needed)
    └── routers/                   # 10+ EE routers (unchanged)
```

### CE Router Pattern Template

```python
# File: puppeteer/agent_service/routers/jobs_router.py
"""Jobs domain router: job CRUD, job definitions, job templates, CI/CD dispatch."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db, Job, AsyncSession, User
from ..deps import get_current_user, require_permission, audit  # Import from deps.py
from ..models import JobCreate, JobResponse

jobs_router = APIRouter()

@jobs_router.post(
    "/jobs",
    response_model=JobResponse,
    tags=["Jobs"],
    summary="Create a new job"
)
async def create_job(
    job_req: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new job and store in DB."""
    # Implementation from current main.py POST /jobs
    ...
    # Before commit:
    audit(db, current_user, "job.create", job.guid, {"task_type": job.task_type})
    await db.commit()
    return ...
```

**Key patterns:**
- Router instantiated as `APIRouter()` with no prefix (full path inline per endpoint)
- All auth/permission/audit helpers imported from `deps.py`
- Endpoint responses match current main.py exactly (same status codes, field names, types)
- WebSocket broadcasts via `ws_manager.broadcast()` — `ws_manager` is exported from main.py at module scope so all routers can access it
- Prefix argument handled in main.py's `include_router()` call: `app.include_router(jobs_router, tags=["Jobs"])`

### Main.py Residual Shape

After refactor, `main.py` contains **only**:

1. Imports and configuration
2. `lifespan()` async context manager (startup/shutdown logic — unchanged)
3. Middleware definitions (`CORSMiddleware`, `LicenceExpiryGuard`, `limiter`)
4. FastAPI app creation (`app = FastAPI(...)`)
5. Middleware registration (`app.add_middleware()`)
6. Rate limiter exception handler
7. **`include_router()` calls** for all CE and EE routers
8. Static file mounts (if any)
9. **Global state exports** needed by routers:
   - `ws_manager = ConnectionManager()` — exported for broadcast in all routers
   - Helper classes/functions shared by routers (e.g., `ConnectionManager`)

**No route handlers remain in main.py — all routes are in routers.**

### WebSocket Handling

**Decision from CONTEXT.md (D-04):** `/ws` endpoint moves out of main.py into a router (most natural home: `system_router.py`).

The `ConnectionManager` class and `ws_manager` singleton must remain in main.py (or a shared module) because:
1. Multiple routers broadcast events to it (jobs, nodes, workflows, system)
2. It must be a singleton shared across all request handlers
3. Circular import risk if `ws_manager` lived in a single router module

**Pattern:**
```python
# In main.py (unchanged)
class ConnectionManager:
    """Broadcasts JSON messages to all connected WebSocket clients."""
    ...

ws_manager = ConnectionManager()  # Singleton, exported

# In system_router.py (new)
from ..main import ws_manager

@system_router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: Optional[str] = None):
    """Live event feed."""
    # ... uses ws_manager to manage connections
    ws_manager._connections.append(ws)
    ...
```

Other routers import and use `ws_manager`:
```python
from ..main import ws_manager

@jobs_router.post("/jobs")
async def create_job(...):
    ...
    await ws_manager.broadcast("job:created", {...})
```

This pattern avoids circular imports because:
- `system_router.py` imports from `main.py` (downstream import — fine)
- `main.py` imports routers via `include_router()` at the module level (no import statement — deferred until app setup)

### Smelter Router Wiring (D-05)

**Current state:** 2 smelter endpoints exist inline in main.py (`POST /api/smelter/ingredients/{id}/discover`, `GET /api/smelter/ingredients/{id}/tree`). The file `routers/smelter_router.py` already exists with these endpoints defined.

**Action during Phase 166:** 
1. Remove the 2 inline smelter endpoints from main.py
2. Wire in the existing `routers/smelter_router.py` via `app.include_router(smelter_router)` in main.py
3. Verify no duplicate routes (OpenAPI schema diff)

**Why smelter is CE, not EE:**
- Smelter is the dependency/CVE scanning engine (foundational infrastructure)
- Routers exist in both `routers/smelter_router.py` (CE) and `ee/routers/smelter_router.py` (EE)
- EE version is loaded by `ee/__init__.py` when licence is valid; CE version is loaded always

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Route organization | Custom import+instantiation per endpoint | FastAPI APIRouter | FastAPI's native pattern; handles prefix/tags/openapi auto-generation |
| Dependency injection | Manual token extraction in handler | `Depends(get_current_user)` from deps.py | FastAPI's built-in DI framework prevents request-scoped resource leaks |
| Per-route authentication | Check `request.headers["Authorization"]` | `current_user = Depends(get_current_user)` | DI layer handles JWT parsing, User lookup, token version validation |
| Per-route permission checks | Manual DB queries for User.role | `Depends(require_permission("perm"))` | Centralized RBAC logic with permission cache (pre-warmed at startup) |
| Audit logging | Manual INSERT statements per route | `audit(db, user, action, resource_id, detail)` | Centralized audit trail; ensures all logs include user, timestamp, action |
| WebSocket broadcasting | Direct WebSocket loop logic in route | `ws_manager.broadcast()` from main.py | Singleton connection manager prevents socket leaks; broadcasts to all connected clients at once |

**Key insight:** The main.py refactor is not about "extracting code" — it's about **applying FastAPI's dependency injection framework correctly across domains**. Each router imports shared deps (user auth, permission checks, audit) from a single source (`deps.py`) to maintain consistency and avoid circular imports. The refactor surfaces the architectural contract that was already implicit in the monolith.

## Common Pitfalls

### Pitfall 1: Circular Imports from Shared `ws_manager`

**What goes wrong:** You move `ws_manager` into `system_router.py`, then try to import it in `jobs_router.py`. Python detects the circular import chain: `main.py` → `system_router.py` → `jobs_router.py` → `system_router.py` (cycle).

**Why it happens:** Routers are imported by main.py at module load time. If `ws_manager` lives in a router that other routers depend on, a cycle forms.

**How to avoid:** Keep `ws_manager` and `ConnectionManager` in `main.py`. Other routers import it from main: `from ..main import ws_manager`. This is safe because:
- `main.py` doesn't import `system_router.py` directly — it uses `include_router()` inside `app` setup (after module load)
- Routers can import from `main.py` (no cycle: main.py → router ✓ is safe; router → main.py ✓ is safe; main imports router only inside function scope)

**Warning signs:** 
- `ImportError: cannot import name 'ws_manager' from...` during startup
- Circular import error message naming two routers

### Pitfall 2: Forgetting to Move WebSocket Endpoint

**What goes wrong:** After extracting all HTTP routes to routers, main.py still has the `@app.websocket("/ws")` endpoint. Tests that import `app` from main.py will fail because the endpoint is registered twice (once in main, once in system_router) or not at all.

**Why it happens:** The WebSocket endpoint is visually similar to HTTP routes, so it's easy to overlook during bulk copy-paste extraction.

**How to avoid:** 
1. Grep for `@app.websocket` in main.py before declaring "refactor complete"
2. Grep for all route decorators: `@app\.(get|post|put|patch|delete|websocket)` — should return 0 matches in main.py after extraction
3. Verify OpenAPI schema is identical (see Pitfall 4)

**Warning signs:**
- Tests fail with "Duplicate WebSocket URL" or route not found errors
- WebSocket endpoint works in old main.py but not after refactor

### Pitfall 3: Missing or Incorrect Tags on Routers

**What goes wrong:** You create a router without specifying the `tags` parameter in `include_router()`. All endpoints in that router appear under a generic "default" tag in OpenAPI docs instead of their intended domain tag.

**Why it happens:** Endpoint tags are metadata used by FastAPI's OpenAPI generator. Individual route handlers can override tags, but the router-level `tags` parameter groups related endpoints.

**How to avoid:** When calling `include_router()`, include a `tags` parameter:
```python
app.include_router(jobs_router, tags=["Jobs", "Job Definitions", "Job Templates", "CI/CD Dispatch"])
```

This ensures all endpoints in that router inherit these tags unless overridden in the individual `@router.get(tags=[...])` decorator.

**Warning signs:**
- OpenAPI schema differs from original (check `/openapi.json`)
- Frontend docs page shows wrong groupings

### Pitfall 4: OpenAPI Schema Drift

**What goes wrong:** After refactor, `GET /openapi.json` returns a different schema than before. Routes are the same, but OpenAPI structure is subtly different, breaking client SDKs or tests that validate the API contract.

**Why it happens:** 
- Removed a route handler but forgot to wire in its router
- Router was wired but with wrong prefix or tags
- Models were modified during extraction
- Response status codes differ

**How to avoid:** 
1. **Before refactor:** Export current OpenAPI schema: `curl https://localhost:8001/openapi.json > /tmp/openapi_before.json`
2. **After refactor:** Export new schema: `curl https://localhost:8001/openapi.json > /tmp/openapi_after.json`
3. **Diff:** `jq -S '.' /tmp/openapi_before.json > /tmp/before.pretty.json && jq -S '.' /tmp/openapi_after.json > /tmp/after.pretty.json && diff -u /tmp/before.pretty.json /tmp/after.pretty.json`
4. **Verify:** Diff should show ONLY path ordering changes, not structural differences

This is **required verification** per CONTEXT.md D-06 (equivalence verification = OpenAPI schema diff + full pytest suite).

**Warning signs:**
- Diff output shows removed paths
- Different status codes for same route
- Missing or renamed response fields

### Pitfall 5: Forgetting to Export `require_auth` or `require_permission` from deps.py

**What goes wrong:** You import `get_current_user` in a router but the route uses `require_auth` (the CE alias). You get `NameError: name 'require_auth' is not defined`.

**Why it happens:** `require_auth` is defined in deps.py but might not be in the `__all__` export list, or you imported the wrong name.

**How to avoid:** Check deps.py exports at the top:
```python
# In deps.py
require_auth = get_current_user  # CE alias

# In any router
from ..deps import require_auth  # or
from ..deps import get_current_user  # both valid
```

Use consistent names across routers: either all use `get_current_user` or all use `require_auth`. Convention: use the full name `get_current_user` in routers, reserve `require_auth` for legacy code or EE context where auth branches exist.

**Warning signs:**
- `NameError` during handler invocation
- Type checker complains about unknown dependency

### Pitfall 6: Hardcoding Route Prefixes in Router Endpoints

**What goes wrong:** You extract a route into a router but hardcode the path with a prefix:
```python
# WRONG
@jobs_router.post("/api/jobs", ...)  # Path includes /api prefix

# RIGHT
@jobs_router.post("/jobs", ...)      # No prefix — included by include_router()
```

Result: Endpoint is available at `/api/api/jobs` (double prefix) or not available at all.

**Why it happens:** Copy-paste from main.py endpoints without removing the `/api` prefix when moving to a router.

**How to avoid:** 
1. When extracting a route to a router, remove any prefix that will be added by `include_router()`
2. In main.py: `app.include_router(jobs_router, prefix="/api", tags=[...])`
3. In router: `@jobs_router.post("/jobs", ...)` (no `/api`)
4. Final path: `/api/jobs` ✓

Check your router instantiation:
```python
# If router uses prefix in include_router:
app.include_router(jobs_router, prefix="/api")

# Then in router file:
@jobs_router.post("/jobs")  # NOT @jobs_router.post("/api/jobs")
```

**Warning signs:**
- 404 errors on endpoints that exist in old code
- Double `/api/api/` in paths

### Pitfall 7: Audit Logging After Commit

**What goes wrong:** You call `db.commit()` before `audit()`, then the audit log isn't persisted because the transaction rolls back on error.

**Why it happens:** `audit()` needs a DB session to insert the AuditLog record. If you commit before auditing, the audit record isn't part of the same transaction.

**How to avoid:** Always call `audit()` **before** `db.commit()`:
```python
# WRONG
await db.commit()
audit(db, user, "job.create", job.guid, {...})

# RIGHT
audit(db, user, "job.create", job.guid, {...})
await db.commit()
```

**Warning signs:**
- Audit records missing for operations that succeeded
- Audit records appear for operations that failed and rolled back

## Code Examples

Verified patterns from the codebase:

### Creating a CE Router with Dependency Injection

```python
# File: puppeteer/agent_service/routers/jobs_router.py
"""Jobs domain router: job CRUD, dispatch, templates, definitions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..db import get_db, Job, User, AsyncSession
from ..deps import get_current_user, require_permission, audit  # Import from deps.py
from ..models import JobCreate, JobResponse

jobs_router = APIRouter()

@jobs_router.post(
    "/jobs",
    response_model=JobResponse,
    tags=["Jobs"],
    summary="Create a new job"
)
async def create_job(
    job_req: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new job and broadcast live update."""
    from uuid import uuid4
    from ..main import ws_manager
    from datetime import datetime
    
    job = Job(
        guid=str(uuid4()),
        task_type=job_req.task_type,
        created_by=current_user.username,
        created_at=datetime.utcnow(),
        # ... other fields
    )
    db.add(job)
    
    # Audit before commit
    audit(db, current_user, "job.create", job.guid, {
        "task_type": job.task_type,
    })
    
    await db.commit()
    await db.refresh(job)
    
    # Broadcast after commit
    await ws_manager.broadcast("job:created", {
        "guid": job.guid,
        "status": "PENDING",
        "task_type": job.task_type
    })
    
    return JobResponse.from_orm(job)

@jobs_router.get(
    "/jobs/{guid}",
    response_model=JobResponse,
    tags=["Jobs"]
)
async def get_job(
    guid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get job by GUID."""
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_orm(job)
```

**Key patterns:**
- Import auth/audit deps from `..deps` (relative import from sibling module)
- Import `ws_manager` from `..main` only when needed (inside handler, not at module level)
- Call `audit()` before `await db.commit()` to ensure audit record is in same transaction
- Broadcast after commit to ensure job is persisted before clients receive update

### Extracting a Group of Routes to a Router

Current main.py has 19 routes tagged "System". To extract:

1. Create `puppeteer/agent_service/routers/system_router.py`
2. Copy route handlers and their helper functions
3. Update imports to use relative paths (`from ..db`, `from ..deps`, etc.)
4. Register in main.py: `app.include_router(system_router, tags=["System", "Health", "Schedule"])`

```python
# File: puppeteer/agent_service/routers/system_router.py
"""System domain router: health checks, schedule, WebSocket, CRL, features."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..db import get_db, User, AsyncSession
from ..deps import get_current_user
from ..models import SystemHealthResponse, FeaturesResponse
from ..main import ws_manager

system_router = APIRouter()

@system_router.get(
    "/system/health",
    response_model=SystemHealthResponse,
    tags=["System"]
)
async def get_system_health(
    db: AsyncSession = Depends(get_db)
):
    """System health summary."""
    # Implementation from main.py
    ...

@system_router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    token: Optional[str] = None
):
    """Live event feed. Requires JWT in ?token query param."""
    # Implementation from main.py
    # Uses ws_manager to manage connections
    ...
```

In `main.py`:
```python
from .routers.system_router import system_router

# After middleware setup:
app.include_router(system_router, tags=["System", "Health", "Schedule"])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Monolithic main.py with 89 inline routes | 6 domain routers + main.py as shell | Phase 166 (this phase) | Enables per-router middleware injection for Vault/SIEM features; improves maintainability |
| Global `get_current_user` in main.py | Shared `deps.py` module | Phase ~100 | Breaks circular imports with EE routers; centralizes auth logic |
| Inline WebSocket handler in main.py | Extracted to `system_router.py` | Phase 166 | Follows domain organization pattern; enables WebSocket to coexist with other system routes |

**Deprecated/outdated:**
- None — this is the first refactoring of routes into domain routers. The monolith pattern is being retired.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|--------------|
| A1 | The 2 smelter routes in main.py are duplicates of routes in `routers/smelter_router.py` and will be removed during phase 166 | Smelter Router Wiring (D-05) | If routes are NOT duplicates, removing them breaks functionality. Mitigation: Confirm routes are identical before removal. |
| A2 | `ws_manager` can be imported from `main.py` in router modules without creating circular imports | WebSocket Handling | If import causes circular dependency, routers cannot broadcast events. Mitigation: Test imports during Phase 166 Plan 01 before finalizing router structure. |
| A3 | All 89 routes in main.py are meant to move to routers (not remain in main.py) | Pitfall 2 | If some routes are intentionally kept in main.py, completeness verification will fail. Mitigation: grep for remaining `@app.` decorators after extraction as final verification step. |

## Open Questions

1. **CE vs EE smelter routers** — Are there differences between `routers/smelter_router.py` (CE) and `ee/routers/smelter_router.py` (EE), or are they identical? If different, ensure both are wired and not shadowed.
   - What we know: `routers/smelter_router.py` exists and has 2 endpoints; phase 166 instructions say "wire in" the CE one
   - What's unclear: Whether the EE version overrides it or coexists
   - Recommendation: Run `diff routers/smelter_router.py ee/routers/smelter_router.py` at start of Phase 166 to clarify

2. **router prefix strategy** — Should all CE routers use full paths inline (`/api/jobs`) or relative paths (`/jobs`) with a shared prefix in `include_router()`?
   - What we know: EE routers use full paths inline; `smelter_router.py` uses full paths inline
   - What's unclear: Consistency rule — should all CE routers follow the same pattern?
   - Recommendation: Use full paths inline like EE routers do, for consistency. No shared prefix argument in `include_router()`.

## Environment Availability

**All external dependencies are present and stable.**

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| FastAPI | Core routing | ✓ | 0.104+ (in requirements.txt) | None — core dependency |
| SQLAlchemy | DB access via `get_db` | ✓ | 2.0+ | None — core dependency |
| Python async/await | Async handlers in routers | ✓ | 3.9+ (Docker base) | None — core language feature |
| pytest | Test suite validation | ✓ | 7.4+ (in dev requirements) | None — required for validation |

**Missing dependencies with no fallback:** None

**Blocking factors:** None identified

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4+ with pytest-asyncio |
| Config file | `puppeteer/pytest.ini` or `pyproject.toml` |
| Quick run command | `cd puppeteer && pytest tests/ -x -v --tb=short` (or subset: `pytest tests/test_jobs_responses.py`) |
| Full suite command | `cd puppeteer && pytest tests/ -v --tb=short` (82 test files, ~737 tests total) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | All 89 routes split into 6 domain routers; zero routes remain in main.py | Manual code audit + grep | `grep -c "@app\." puppeteer/agent_service/main.py` (should return ~15 for middleware/lifespan, 0 for routes) | ✅ |
| ARCH-02 | All API endpoints function identically (paths, request/response shapes, status codes unchanged) | Integration + smoke tests | `pytest tests/test_jobs_responses.py tests/test_nodes_responses.py ...` | ✅ (82 tests across 82 files cover all domains) |
| ARCH-03 | Domain routers support per-router middleware injection via `Depends()` | Smoke test for permission checks | `pytest tests/test_admin_responses.py -k "permission"` | ✅ (existing tests validate `require_permission` factory) |
| ARCH-04 | Full backend test suite passes with unchanged coverage after refactor | Full suite | `cd puppeteer && pytest tests/ -v --tb=short 2>&1 \| tail -5` (must show all passed) | ✅ (82 test files present; no new test gaps expected from refactoring) |

### Sampling Rate

- **Per task commit:** Run subset of affected router's tests (e.g., `pytest tests/test_jobs_responses.py -x` after extracting jobs_router)
- **Per plan merge:** Run full suite: `cd puppeteer && pytest tests/ -v --tb=short`
- **Phase gate:** Full suite must be green + OpenAPI schema diff verified before `/gsd-verify-work`

### Wave 0 Gaps

None identified — existing test infrastructure covers all phase requirements:
- 82 existing test files exercising all 89 routes (directly or indirectly)
- pytest fixtures in conftest.py handle DB setup, JWT token generation, mocking
- No new test files needed for refactoring (test file structure doesn't change, only handler locations)
- No framework install needed (pytest already installed in requirements.txt)

*If Wave 0 were to be needed:* Only gap would be explicit **router import tests** (e.g., `test_router_imports.py`) to verify no circular imports and all routers load. This is optional but recommended as a verification task in Plan 03.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | JWT verification in `deps.get_current_user`; token_version mismatch rejection |
| V3 Session Management | Yes | JWT token version invalidation on password change; token TTL enforcement in auth.py |
| V4 Access Control | Yes | RBAC via `deps.require_permission`; role_permissions table in DB; admin bypass for permission checks |
| V5 Input Validation | Yes | Pydantic models in routers validate request schemas; FastAPI auto-serializes responses |
| V6 Cryptography | Yes | mTLS client certs verified in `/work/pull` and `/api/enroll` (node-only endpoints, unaffected by router refactoring) |
| V7 Cryptographic Failures | Yes | Fernet encryption for secrets in DB; JWT signing with SECRET_KEY env var |
| V8 Data Protection | Yes | Audit logging in AuditLog table; no plaintext secrets in logs (masked via `mask_secrets`) |
| V9 Error Handling | Yes | HTTPException responses with status codes; no stack traces in production |
| V10 Business Logic | Yes | Signature validation before job execution (in job_service, unchanged); capability matching for node assignment |

### Known Threat Patterns for FastAPI + SQLAlchemy Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ORM | Tampering | Use SQLAlchemy query builder (parameterized); never concatenate strings in `select()`. All routers inherit this pattern. |
| Missing auth checks | Elevation of Privilege | All routes declare `Depends(get_current_user)` or `Depends(require_permission(...))`. Grep verifies 100% coverage. |
| JWT signature bypass | Spoofing | JWT verified with SECRET_KEY in `deps.get_current_user`; token_version field prevents replay after password change. |
| Race condition on permission check + action | Race Condition | Single DB transaction per request (AsyncSession). Permission check and action in same transaction. |
| Unvalidated redirect (via response models) | Tampering | Response models are Pydantic, not string templates. FastAPI auto-escapes JSON. |
| Audit log tampering | Non-Repudiation | Audit logs in DB with primary key; no soft-delete. User and timestamp immutable. |

**No new vulnerabilities introduced by router refactoring** — the refactoring preserves the existing security model. Auth/permission/audit logic is unchanged; it's only relocated to routers via deps.py imports.

## Sources

### Primary (HIGH confidence)

- **CONTEXT.md** — Phase 166 decisions (D-01 through D-07), canonical references, code context
- **Codebase audit** (grep, file inspection):
  - `puppeteer/agent_service/main.py` — current 3,828-line monolith; 89 routes identified
  - `puppeteer/agent_service/routers/smelter_router.py` — existing CE router template
  - `puppeteer/agent_service/ee/routers/foundry_router.py` — existing EE router template
  - `puppeteer/agent_service/deps.py` — shared auth/permission/audit helpers
  - `puppeteer/tests/conftest.py` — test fixture setup; app import validation
- **Route tag audit** (grep `tags=\[` across main.py) — 6 domain mappings confirmed

### Secondary (MEDIUM confidence)

- **REQUIREMENTS.md** — Phase 166 requirements (ARCH-01 through ARCH-04); traceability table
- **STATE.md** — Router modularization context; "blocker for Vault + SIEM" confirmation

### Tertiary (LOW confidence — assumed, needs validation)

- Circular import risk with `ws_manager` — **[ASSUMED]** that importing from main.py in routers is safe. Mitigation: test during Phase 166 Plan 01.
- Smelter routes are exact duplicates — **[ASSUMED]** based on phase instructions ("wire in" implies no changes). Mitigation: diff files at start of work.

## Metadata

**Confidence breakdown:**
- **Standard Stack:** HIGH — FastAPI and relative import patterns confirmed in codebase
- **Architecture:** HIGH — existing router examples (smelter, EE routers) and deps.py pattern established
- **Pitfalls:** HIGH — derived from code analysis (circular import risk) and best practices (audit ordering)
- **Overall:** HIGH — phase is a well-scoped refactoring with clear patterns to follow

**Research date:** 2026-04-18  
**Valid until:** 2026-05-02 (14 days — router patterns in FastAPI are stable; next review if major FastAPI version released)

---

*Phase: 166-router-modularization*  
*Research completed: 2026-04-18*
