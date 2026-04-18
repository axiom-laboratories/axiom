# Phase 166: Router Modularization - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 7 new/modified files
**Analogs found:** 6 / 6 (100% coverage)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `puppeteer/agent_service/routers/auth_router.py` | router | request-response | `routers/smelter_router.py` | exact |
| `puppeteer/agent_service/routers/jobs_router.py` | router | request-response (CRUD + async polling) | `routers/smelter_router.py` | exact |
| `puppeteer/agent_service/routers/nodes_router.py` | router | request-response (CRUD) | `routers/smelter_router.py` | exact |
| `puppeteer/agent_service/routers/workflows_router.py` | router | request-response (CRUD) | `ee/routers/foundry_router.py` | exact |
| `puppeteer/agent_service/routers/admin_router.py` | router | request-response (CRUD + updates) | `ee/routers/foundry_router.py` | exact |
| `puppeteer/agent_service/routers/system_router.py` | router | request-response + websocket | `routers/smelter_router.py` | exact |
| `puppeteer/agent_service/main.py` (modified) | app setup | app lifecycle + middleware | (current main.py lines 447–515) | reference |

## Pattern Assignments

### CE Router Template Pattern

All 6 CE routers follow the same template pattern. Use `routers/smelter_router.py` as the canonical reference.

**Source file:** `puppeteer/agent_service/routers/smelter_router.py`

**Import block** (lines 1–31):
```python
"""
[Module docstring describing the domain and endpoints]
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging
from typing import List, Optional

from ..db import get_db, AsyncSession, [relevant DB models]
from ..deps import get_current_user, require_permission, audit
from ..models import [relevant Pydantic models]
from ..services.[relevant_service] import [ServiceClass]

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Key patterns:**
- Router instantiated as `router = APIRouter()` (not `APIRouter(prefix=...)`)
- All imports use relative paths: `from ..deps import ...`, `from ..db import ...`
- No `prefix` argument in `APIRouter()` — full paths inline in route handlers
- Imports from `deps.py` for auth/permission/audit (NOT from `auth.py` or `security.py`)
- Module-level `logger = logging.getLogger(__name__)`

**Route handler pattern** (lines 189–221):
```python
@router.get(
    "/api/smelter/ingredients/{ingredient_id}/tree",
    response_model=DependencyTreeResponse,
    tags=["Smelter"],
    summary="Get dependency tree with CVE information"
)
async def get_dependency_tree(
    ingredient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("smelter:read"))
):
    """Full docstring describing the endpoint."""
    # Implementation
    ...
```

**Key patterns:**
- Full path in route (e.g., `/api/smelter/ingredients/{ingredient_id}/tree`) — NO prefix stripping
- `tags=["Domain"]` parameter included for OpenAPI grouping
- `Depends(get_db)` for AsyncSession (always last parameter for consistency)
- `Depends(require_permission(...))` or `Depends(get_current_user)` for auth (order varies by route)
- Route name matches handler function name (e.g., `get_dependency_tree`)

**Error handling** (lines 208–221):
```python
# Simple pattern: HTTPException for not found / validation errors
result = await db.execute(
    select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id)
)
ingredient = result.scalar_one_or_none()
if not ingredient:
    raise HTTPException(
        status_code=404,
        detail=f"Ingredient {ingredient_id} not found"
    )
```

**Audit pattern** (lines 462–464 in smelter_router_context):
```python
# Call audit BEFORE commit
audit(db, current_user, "action.type", resource_id, {"field": value})
await db.commit()
```

**WebSocket broadcast pattern** (from main.py — copy to new routers):
```python
# At top of handler that needs broadcast:
from ..main import ws_manager

# After DB commit:
await ws_manager.broadcast("event:type", {"data": "payload"})
```

---

### `puppeteer/agent_service/routers/auth_router.py` (router, request-response)

**Analog:** `routers/smelter_router.py`

**Routes to extract from main.py:**
- Lines ~881–1130: Authentication endpoints (device auth, device token, device approve/deny, login, /auth/me GET/PATCH)

**Imports pattern** (adapt from smelter):
```python
"""Authentication domain router: device auth, JWT token, password management."""

from fastapi import APIRouter, Depends, HTTPException, status, Form, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import logging

from ..db import get_db, AsyncSession, User, Token
from ..deps import get_current_user, get_current_user_optional
from ..models import TokenResponse, DeviceCodeResponse, UserResponse
from ..auth import verify_password, get_password_hash, create_access_token
from ..security import oauth2_scheme

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Core pattern:** Device auth flow (POST /auth/device → device code) + JWT login (POST /auth/login) + password change (PATCH /auth/me)

**Key difference from other routers:** Auth routes do NOT use `require_permission()` — they use `Depends(get_current_user)` (for /auth/me) or no auth at all (for login/device endpoints).

---

### `puppeteer/agent_service/routers/jobs_router.py` (router, request-response)

**Analog:** `routers/smelter_router.py`

**Routes to extract from main.py:**
- Lines ~1500–1810: Jobs CRUD, bulk actions, resubmit, status
- Lines ~1623–1690: Job Definitions (list, create, get, update, delete)
- Lines ~1133–1210: Job Templates (list, create, get, update, delete)
- Lines ~1383–1500: CI/CD Dispatch endpoints

**Imports pattern** (adapt from smelter):
```python
"""Jobs domain router: job CRUD, job definitions, job templates, CI/CD dispatch."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
import logging

from ..db import get_db, AsyncSession, User, Job, ScheduledJob, JobTemplate
from ..deps import get_current_user, require_permission, audit
from ..models import (
    JobCreate, JobResponse, JobDefinitionCreate, JobDefinitionResponse,
    JobTemplateCreate, JobTemplateResponse, DispatchRequest, DispatchResponse,
    BulkActionResponse, PaginatedResponse
)
from ..services.job_service import JobService
from ..services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Core pattern:** All routes require `require_permission("jobs:read")` or `require_permission("jobs:write")` per operation.

**WebSocket broadcast:** Use `await ws_manager.broadcast("job:created", {...})` for job lifecycle events. Import at handler scope:
```python
from ..main import ws_manager
```

---

### `puppeteer/agent_service/routers/nodes_router.py` (router, request-response)

**Analog:** `routers/smelter_router.py`

**Routes to extract from main.py:**
- Lines ~1846–1930: Node Agent endpoints (/work/pull, /heartbeat, /api/enroll — these are UNAUTHENTICATED, kept as-is but moved to router)
- Lines ~1931–2090: Nodes CRUD (list, detail, patch, delete, revoke, drain, undrain)

**Imports pattern** (adapt from smelter):
```python
"""Nodes domain router: node CRUD, enrollment, agent heartbeat, drain/revoke."""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
import logging

from ..db import get_db, AsyncSession, User, Node
from ..deps import get_current_user, require_permission, audit
from ..models import NodeResponse, PollResponse, NodeUpdateRequest, ActionResponse
from ..services.job_service import JobService
from ..security import verify_client_cert, verify_node_secret

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Key difference:** Endpoints `/work/pull`, `/heartbeat`, `/api/enroll` are **unauthenticated** — they use mTLS client certs and node secrets instead. Keep those handlers exactly as they are in main.py (no auth decorator).

**Authenticated endpoints** (list_nodes, get_node, patch_node, delete_node, revoke_node, drain/undrain) use `require_permission("nodes:read")` or `require_permission("nodes:write")`.

---

### `puppeteer/agent_service/routers/workflows_router.py` (router, request-response)

**Analog:** `ee/routers/foundry_router.py` (for pattern structure; adapt permissions)

**Routes to extract from main.py:**
- Lines ~2098–2250: Workflow CRUD, runs, webhooks (approximately 15 workflow routes tagged "workflows")

**Imports pattern** (adapt from ee/foundry):
```python
"""Workflows domain router: workflow CRUD, execution runs, webhook management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
import logging

from ..db import get_db, AsyncSession, User, Workflow, WorkflowRun
from ..deps import get_current_user, require_permission, audit
from ..models import (
    WorkflowCreate, WorkflowResponse, WorkflowUpdate,
    WorkflowRunResponse, WorkflowWebhookCreate, WorkflowWebhookResponse
)
from ..services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Core pattern:** All routes require `require_permission("workflows:read")` or `require_permission("workflows:write")`.

**WebSocket broadcast:** Similar to jobs_router. After DB commit:
```python
from ..main import ws_manager
await ws_manager.broadcast("workflow:updated", {...})
```

---

### `puppeteer/agent_service/routers/admin_router.py` (router, request-response)

**Analog:** `ee/routers/foundry_router.py` (for structure and permission checks)

**Routes to extract from main.py:**
- Lines ~516–596: Alerts & Webhooks (GET/POST alerts)
- Lines ~678–786: Signatures CRUD (list, create, get, delete)
- Lines ~1258–1364: Admin health checks, audit log, licence, config
- Lines ~3231–3290: Headless Automation (signal fire, signal list, get signal)
- Lines ~547–676: Various admin endpoints (system config, features, licence reload, etc.)

**Imports pattern** (adapt from ee/foundry):
```python
"""Admin domain router: user/role management, signatures, alerts, system config, signals."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
import logging

from ..db import get_db, AsyncSession, User, Signature, Alert, Signal
from ..deps import get_current_user, require_permission, audit
from ..models import (
    SignatureCreate, SignatureResponse, AlertResponse, SignalResponse,
    ActionResponse, SystemConfigResponse, AuditLogResponse
)
from ..services.signature_service import SignatureService
from ..services.alert_service import AlertService

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Core pattern:** Most routes require `require_permission("admin:write")` or similar high-level permission. Some (like GET endpoints) may use `require_permission("admin:read")`.

**Error handling:** Similar to other routers — HTTPException with 403/404/422 status codes.

**Audit logging:** Before every admin action (user create, signature register, config change):
```python
audit(db, current_user, "admin.action_type", resource_id, {"field": value})
await db.commit()
```

---

### `puppeteer/agent_service/routers/system_router.py` (router, request-response + websocket)

**Analog:** `routers/smelter_router.py` (for HTTP routes) + main.py lines 3179–3210 (for WebSocket)

**Routes to extract from main.py:**
- Lines ~1148–1230: System health, scheduling health, scale health, features, licence status
- Lines ~1289–1364: CRL endpoint, config endpoints
- Lines ~3179–3210: WebSocket /ws endpoint
- Any "Schedule" tagged routes (APScheduler integration)

**Imports pattern** (adapt from smelter):
```python
"""System domain router: health checks, WebSocket, CRL, features, licensing."""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import logging

from ..db import get_db, AsyncSession, User, RevokedCert, AsyncSessionLocal
from ..deps import get_current_user, get_current_user_optional
from ..models import SystemHealthResponse, FeaturesResponse, LicenceStatusResponse
from ..auth import SECRET_KEY, ALGORITHM
from ..main import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()
```

**WebSocket pattern** (lines 3179–3210 from main.py — move exactly as-is):
```python
@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: Optional[str] = None):
    """Live event feed. Requires a valid JWT passed as ?token=<jwt> query param."""
    await ws.accept()
    # Validate token using a short-lived session so we don't hold a pool slot
    # for the entire WebSocket lifetime (which exhausts the connection pool).
    authed = False
    if token:
        try:
            from jose import jwt as _jwt, JWTError
            payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username:
                async with AsyncSessionLocal() as _db:
                    result = await _db.execute(select(User).where(User.username == username))
                    user = result.scalar_one_or_none()
                    if user and payload.get("tv", 0) == user.token_version:
                        authed = True
        except Exception:
            pass
    if not authed:
        await ws.close(code=1008)
        return
    ws_manager._connections.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
```

**Key pattern:** WebSocket endpoint is unauthenticated (validates token inline, not via `Depends()`). No audit logging needed.

---

### `puppeteer/agent_service/main.py` (modified — app setup shell)

**Analog:** Current main.py lines 447–515 (app creation, middleware, lifespan)

**After refactor, main.py contains ONLY:**

**Section 1: Imports** (lines 1–85 of current main.py — minimize to essentials)
```python
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os
from contextlib import asynccontextmanager

from .models import [ONLY response models used by main.py itself, not routers]
from .security import [encryption/security utilities]
from .auth import [auth utilities]
from .services.licence_service import [licence utilities]
from .services.scheduler_service import [scheduler_service only if needed at app level]
# ... minimal imports

logger = logging.getLogger(__name__)
```

**Section 2: Lifespan, Middleware, App creation** (lines 87–505 of current main.py — UNCHANGED)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    # ... validation checks, licence loading, EE plugin loading
    # Pre-warm permission cache
    asyncio.create_task(check_mirrors_health())
    yield
    # Shutdown logic
    scheduler_service.scheduler.shutdown()

app = FastAPI(...)
app.state.limiter = limiter
app.add_exception_handler(...)
app.add_middleware(CORSMiddleware, ...)
class LicenceExpiryGuard(BaseHTTPMiddleware):
    # ... EE_PREFIXES unchanged
app.add_middleware(LicenceExpiryGuard)
```

**Section 3: Global state exports** (new — needed by routers for broadcasting)
```python
# Shared state for routers that broadcast WebSocket events
class ConnectionManager:
    """Broadcasts JSON messages to all connected WebSocket clients."""
    
    def __init__(self):
        self._connections: List[WebSocket] = []
    
    async def broadcast(self, event_type: str, data: dict):
        """Broadcast to all connected clients."""
        import json
        message = json.dumps({"type": event_type, "data": data})
        for connection in self._connections[:]:  # copy to avoid modification during iteration
            try:
                await connection.send_text(message)
            except Exception:
                self._connections.remove(connection)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a client connection."""
        if websocket in self._connections:
            self._connections.remove(websocket)

ws_manager = ConnectionManager()  # Singleton, exported for use by all routers
```

**Section 4: Router wiring** (NEW)
```python
# Import all CE routers (after app creation)
from .routers.auth_router import router as auth_router
from .routers.jobs_router import router as jobs_router
from .routers.nodes_router import router as nodes_router
from .routers.workflows_router import router as workflows_router
from .routers.admin_router import router as admin_router
from .routers.system_router import router as system_router
from .routers.smelter_router import router as smelter_router

# Register CE routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(jobs_router, tags=["Jobs", "Job Definitions", "Job Templates", "CI/CD Dispatch"])
app.include_router(nodes_router, tags=["Nodes", "Node Agent"])
app.include_router(workflows_router, tags=["Workflows"])
app.include_router(admin_router, tags=["Admin", "Signatures", "Alerts & Webhooks", "Headless Automation"])
app.include_router(system_router, tags=["System", "Health", "Schedule"])
app.include_router(smelter_router, tags=["Smelter"])

# Mount static files (if applicable)
app.mount("/installer", StaticFiles(directory="installer"), name="installer")
```

**Section 5: EE plugin injection** (lines 150–160 of current main.py — keep in lifespan)
```python
# Inside lifespan() startup block:
from .ee import load_ee_plugins, EEContext, _mount_ce_stubs
if licence_state.is_ee_active:
    app.state.ee = await load_ee_plugins(app, engine)
else:
    ctx = EEContext()
    _mount_ce_stubs(app)
    app.state.ee = ctx
```

**Section 6: Uvicorn runner** (lines 3825–3860 of current main.py — UNCHANGED)
```python
if __name__ == "__main__":
    import uvicorn
    # ... PKI setup, cert generation
    if ssl_enabled:
        uvicorn.run(app, host="0.0.0.0", port=8001, ssl_keyfile=..., ssl_certfile=...)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8001)
```

**What to DELETE from main.py:**
- ALL `@app.get()`, `@app.post()`, `@app.put()`, `@app.patch()`, `@app.delete()`, `@app.websocket()` decorators
- Helper functions that are only used by those route handlers (move them to the appropriate router)
- The 2 duplicate smelter endpoints (lines ~3673–3780) — already in `routers/smelter_router.py`

**Verification grep commands** (after extraction):
```bash
# Should return ~15 (lifespan, middleware setup, exception handlers, app.mount)
grep -c "^@app\." puppeteer/agent_service/main.py

# Should return 0 — all routes moved to routers
grep -c "^@app\.\(get\|post\|put\|patch\|delete\|websocket\)" puppeteer/agent_service/main.py

# Should return non-zero — routers imported
grep -c "from.*routers.*import" puppeteer/agent_service/main.py
```

---

## Shared Patterns

### Dependency Injection (All Routers)

**Source:** `puppeteer/agent_service/deps.py` (lines 1–100)

All routers import from `deps.py`:
```python
from ..deps import get_current_user, require_permission, audit
```

**Authentication:**
```python
# Unauthenticated route (none)
# Public route with optional auth (node agent routes — use client certs instead)
# Authenticated route (requires valid JWT)
current_user: User = Depends(get_current_user)

# Permission-gated route (EE feature, requires role in DB)
current_user: User = Depends(require_permission("permission:name"))
```

**Audit logging:**
```python
# Before any mutating operation, call audit() BEFORE commit:
audit(db, current_user, "resource.action", resource_id, {"field": "value"})
await db.commit()
```

**Database session:**
```python
# All routes declare:
db: AsyncSession = Depends(get_db)
```

### WebSocket Broadcasting (Jobs, Nodes, Workflows, Admin Routers)

**Source:** main.py lines 3193–3210

Routes that modify state and want to notify clients use:
```python
# At handler scope (not module level) to avoid circular imports:
from ..main import ws_manager

# After db.commit():
await ws_manager.broadcast("event:type", {
    "guid": obj.guid,
    "status": obj.status,
    "timestamp": datetime.utcnow().isoformat()
})
```

**Key pattern:** Import `ws_manager` inside the handler function, not at module level. This avoids circular imports between main.py and routers.

### Error Handling (All Routers)

**Source:** `routers/smelter_router.py` (lines 208–221)

Consistent pattern:
```python
from fastapi import HTTPException, status

# Not found
if not resource:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Resource {id} not found"
    )

# Permission denied (alternative to 403)
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Permission denied"
)

# Validation error
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Invalid input"
)

# Server error
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Internal server error"
)
```

### Response Models (All Routers)

**Source:** `puppeteer/agent_service/models.py`

All route handlers declare `response_model=ModelClass` where ModelClass is a Pydantic model. FastAPI auto-serializes the handler's return value.

```python
@router.get(
    "/jobs/{guid}",
    response_model=JobResponse,  # FastAPI validates and serializes return value
    tags=["Jobs"]
)
async def get_job(guid: str, ...):
    # Return a Job ORM object or dict
    return JobResponse.from_orm(job)
```

### Permission Pattern (Admin & System Routers)

**Source:** `ee/routers/foundry_router.py` (lines 38–42) and `deps.py` (lines 94–110)

```python
# EE feature check (requires permission in DB)
current_user: User = Depends(require_permission("foundry:write"))

# CE route (no permission required, just authentication)
current_user: User = Depends(get_current_user)
```

---

## No Analog Found

None — all 6 router patterns covered by existing `routers/smelter_router.py` and `ee/routers/foundry_router.py`.

---

## Metadata

**Analog search scope:** `puppeteer/agent_service/routers/`, `puppeteer/agent_service/ee/routers/`, `puppeteer/agent_service/main.py`

**Files scanned:** 3 (smelter_router.py, foundry_router.py, main.py)

**Pattern extraction date:** 2026-04-18

**Key findings:**
- All 6 new routers follow identical pattern: `APIRouter()` instantiation, relative imports from `..deps`, `..db`, `..models`, full paths in route decorators, `tags` parameter for OpenAPI grouping
- `deps.py` is the single source of truth for `get_current_user`, `require_permission`, `audit`
- `ws_manager` must be defined in main.py and imported by routers (not vice versa) to avoid circular imports
- Smelter router is a CE router (already in codebase) and must be wired into main.py in Phase 166 Plan 02
- No modifications needed to `deps.py`, `db.py`, `models.py`, `services/`, or `auth.py`
