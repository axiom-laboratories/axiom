# Phase 170: PR Review Fix — Code Hygiene and Resource Safety - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 7 files to modify
**Analogs found:** 7 / 7 (100% coverage)

## File Classification

| File to Modify | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `puppeteer/agent_service/deps.py` | utility | async-context-access | `puppeteer/agent_service/services/licence_service.py` | role-match |
| `puppeteer/ee/services/vault_service.py` | service | initialization | `puppeteer/ee/services/siem_service.py` | exact |
| `puppeteer/agent_service/main.py` | controller | route-definition | `puppeteer/agent_service/routers/admin_router.py` | role-match |
| `puppeteer/agent_service/routers/admin_router.py` | router | route-definition | `puppeteer/agent_service/routers/admin_router.py` (self) | exact |
| `puppeteer/agent_service/routers/jobs_router.py` | router | route-definition | `puppeteer/agent_service/routers/jobs_router.py` (self) | exact |
| `puppeteer/agent_service/routers/system_router.py` | router | route-definition | `puppeteer/agent_service/routers/system_router.py` (self) | exact |
| `puppeteer/agent_service/ee/routers/vault_router.py` | router | route-definition | `puppeteer/agent_service/ee/routers/vault_router.py` (self) | exact |

## Pattern Assignments

### `puppeteer/agent_service/deps.py` (utility, async-context-access)

**Analog:** `puppeteer/agent_service/deps.py` (existing code at line 171)

**Context:** This file contains async dependency helpers. Fix D-01 replaces a deprecated asyncio call in the `audit()` function.

**Async loop pattern** (lines 170-176):
```python
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(_insert())
except Exception:
    pass
```

**Replacement pattern** (use `get_running_loop()` instead):
```python
try:
    loop = asyncio.get_running_loop()
    loop.create_task(_insert())
except RuntimeError:
    # Called outside async context
    pass
```

**Notes:**
- `asyncio.get_running_loop()` raises `RuntimeError` if called outside async context (correct failure mode)
- `asyncio.get_event_loop()` is deprecated in Python 3.10+ and emits `DeprecationWarning`
- The `if loop.is_running()` check becomes unnecessary — `get_running_loop()` only returns if running

---

### `puppeteer/ee/services/vault_service.py` (service, initialization)

**Analog:** `puppeteer/ee/services/siem_service.py` (frozen dataclass snapshot pattern)

**Imports pattern** (lines 1-20 in `siem_service.py`):
```python
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from agent_service.db import VaultConfig
from agent_service.security import cipher_suite
```

**Frozen dataclass snapshot** (from `siem_service.py` lines 25-38):
```python
@dataclass(frozen=True)
class _SIEMConfigSnapshot:
    """Immutable snapshot of SIEMConfig values taken at service construction time.

    Avoids DetachedInstanceError when the ORM session that loaded the config
    is closed or committed while the long-lived singleton still holds a reference.
    """
    backend: str
    destination: str
    syslog_port: int
    # ... more fields
```

**VaultConfigSnapshot definition** (for `vault_service.py`):
Must include these 7 fields (from `agent_service/db.py` VaultConfig model):
- `enabled: bool` (line 130)
- `vault_address: str` (line 124)
- `role_id: str` (line 125)
- `secret_id: str` (line 126, stored encrypted)
- `mount_path: str` (line 127)
- `namespace: Optional[str]` (line 128)
- `provider_type: str` (line 129)

Exclude metadata: `id`, `created_at`, `updated_at`

**Renewal failures property** (current `vault_service.py` line 41):
```python
self._consecutive_renewal_failures = 0
```

Add a simple property (pattern from `siem_service.py` line 160 for `_consecutive_failures`):
```python
@property
def renewal_failures(self) -> int:
    """Return count of consecutive lease renewal failures."""
    return self._consecutive_renewal_failures
```

**VaultService.__init__ pattern** (current lines 35-43 in `vault_service.py`):
```python
def __init__(self, config: Optional[VaultConfig], db: AsyncSession):
    self.config = config
    self.db = db
    # ... rest of initialization
```

**Snapshot pattern** (from `siem_service.py` lines 80-91):
```python
self.config: Optional[VaultConfigSnapshot] = (
    VaultConfigSnapshot(
        enabled=config.enabled,
        vault_address=config.vault_address,
        role_id=config.role_id,
        secret_id=config.secret_id,
        mount_path=config.mount_path,
        namespace=config.namespace,
        provider_type=config.provider_type,
    )
    if config else None
)
```

---

### `puppeteer/agent_service/main.py` (controller, route-definition)

**Analog:** `puppeteer/agent_service/routers/admin_router.py` (example of router pattern)

**Context:** Four route groups need to be removed from `main.py` after being moved to dedicated routers. The routes are:

1. **Retention routes** (lines ~1079, ~1113) → migrate to `admin_router.py`
2. **Verification-key route** (line ~713) → migrate to `system_router.py`
3. **Docs routes** (lines ~1013, ~1043) → migrate to `system_router.py`
4. **Job-definitions alias** (line ~975) → migrate to `jobs_router.py`

**Route registration pattern** (from `main.py`, current approach using `@app.get`, `@app.post`):
```python
@app.get(
    "/api/admin/retention",
    response_model=dict,
    tags=["Admin"],
    summary="Get retention configuration",
)
async def get_retention_config(...):
    ...

@app.patch(
    "/api/admin/retention",
    response_model=dict,
    tags=["Admin"],
    summary="Update retention configuration",
)
async def update_retention_config(...):
    ...
```

**After migration**, these become router-based in the target routers using `@router.get`, `@router.post`, `@router.patch`.

**Router registration** (in `main.py` lifespan, around line ~130-180):
The routers are already registered with `app.include_router()`:
```python
# Existing pattern for all routers
app.include_router(admin_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(system_router, prefix="/api")
```

After moving routes, no additional registration is needed — the routers are already included.

---

### `puppeteer/agent_service/routers/admin_router.py` (router, route-definition)

**Analog:** `puppeteer/agent_service/routers/admin_router.py` (self — existing patterns in this file)

**Context:** Add retention routes (`GET /api/admin/retention` + `PATCH /api/admin/retention`) to this router.

**Router structure** (lines 1-45 of `admin_router.py`):
```python
"""
Admin domain router: user/role management, signatures, alerts, system config, signals, and admin tokens.
...
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func as sqlfunc
from typing import Optional, List
import logging
import uuid
import json
import base64
from datetime import datetime

from ..db import (
    get_db, AsyncSession, User, Signature, Alert, Signal, Token, Config,
    ScheduledJob
)
from ..deps import (
    get_current_user, get_current_user_optional, require_auth,
    require_permission, audit
)
from ..models import (
    SignatureCreate, SignatureResponse, AlertResponse, SignalResponse,
    SignalFire, ActionResponse, EnrollmentTokenResponse, UploadKeyRequest,
    LicenceReloadResponse, LicenceReloadRequest, NetworkMount
)

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Route pattern with permission guard** (from lines 50+ in `admin_router.py`):
```python
@router.post("/signatures", response_model=SignatureResponse, tags=["Signatures"])
async def create_signature(
    sig: SignatureCreate,
    current_user: User = Depends(require_permission("signatures:write")),
    db: AsyncSession = Depends(get_db)
):
```

**Retention routes** (from `main.py` lines 1079-1124) use `require_permission("users:write")`:
- GET `/api/admin/retention` — read config + count eligible/pinned records
- PATCH `/api/admin/retention` — update config, update Config table

**Imports needed** (add to admin_router.py imports):
- From existing: `Config` (already imported line 26)
- From existing: `timedelta` (add to `datetime` imports)
- From existing: `ExecutionRecord` (add to db imports)
- From existing: `require_permission` (already imported)
- From models: `RetentionConfigUpdate` (add to models import)

---

### `puppeteer/agent_service/routers/jobs_router.py` (router, route-definition)

**Analog:** `puppeteer/agent_service/routers/jobs_router.py` (self — existing patterns in this file)

**Context:** Add an alias route `GET /job-definitions` that delegates to the canonical `/jobs/definitions`.

**Existing job-definitions route location** (from `jobs_router.py`, find existing):
The canonical route is `GET /jobs/definitions` already in this router. Add an alias that calls the same handler or re-uses the logic.

**Alias route pattern** (from `main.py` lines 975-984):
```python
@app.get(
    "/job-definitions",
    response_model=List[JobDefinitionResponse],
    tags=["Job Definitions"],
    summary="List job definitions (alias)",
    description="Alias for GET /jobs/definitions - returns list of all scheduled job definitions"
)
async def dashboard_job_definitions(current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /job-definitions instead of /jobs/definitions"""
    return await scheduler_service.list_job_definitions(db)
```

**Add to jobs_router.py** using same pattern but with `@router.get` instead of `@app.get`:
- Path: `/job-definitions` (no `/api` prefix — router is registered with prefix)
- Response model: `List[JobDefinitionResponse]`
- Auth: `require_auth` (no permission check required for this endpoint)
- Handler: calls `scheduler_service.list_job_definitions(db)`

**Imports check** (ensure in jobs_router.py):
- `scheduler_service` should be imported (verify line 51+)
- `JobDefinitionResponse` should be in models import
- `require_auth` should be imported from `deps`

---

### `puppeteer/agent_service/routers/system_router.py` (router, route-definition)

**Analog:** `puppeteer/agent_service/routers/system_router.py` (self — existing patterns in this file)

**Context:** Add two route groups:
1. **Verification-key route** (`GET /verification-key`) — unauthenticated, returns PEM public key
2. **Docs routes** (`GET /api/docs`, `GET /api/docs/{filename}`) — authenticated, returns markdown

**Existing system_router structure** (lines 1-100):
```python
from fastapi import APIRouter, Depends, HTTPException, Request, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging
import os
from pathlib import Path

from ..db import (get_db, AsyncSession, User, Config, RevokedCert, ScheduledJob, Job)
from ..deps import (get_current_user, require_auth, require_permission, audit)
from ..models import (...)

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Verification-key route** (from `main.py` lines 709-723):
```python
@router.get(
    "/verification-key",
    response_class=Response,
    tags=["System"],
    summary="Get Ed25519 verification public key",
    description="Returns the PEM-encoded Ed25519 public key used to verify signed job scripts"
)
async def get_verification_key():
    """Serves the Public Verification Key for Code Signing."""
    key_path = "/app/secrets/verification.key"
    if not os.path.exists(key_path):
        if os.path.exists("secrets/verification.key"):
            key_path = "secrets/verification.key"
        else:
            raise HTTPException(status_code=404, detail="Verification Key not configured on Server")
    
    with open(key_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")
```

**Docs routes** (from `main.py` lines 1008-1059):
```python
@router.get(
    "/api/docs",
    response_model=list,
    tags=["System"],
    summary="List available documentation files",
    description="Get list of available markdown documentation files"
)
async def list_docs(current_user: User = Depends(require_auth)):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    if not os.path.exists(docs_dir):
        docs_dir = os.path.join(base_dir, "../docs")
            
    if not os.path.exists(docs_dir):
        return []

    files = []
    for f in os.listdir(docs_dir):
        if f.endswith(".md"):
            title = f
            try:
                with open(os.path.join(docs_dir, f), "r") as md_file:
                    first_line = md_file.readline().strip()
                    if first_line.startswith("#"):
                        title = first_line.lstrip("# ").strip()
            except:
                pass
            files.append({"filename": f, "title": title})
    return files


@router.get(
    "/api/docs/{filename}",
    response_model=dict,
    tags=["System"],
    summary="Get documentation file content",
    description="Retrieve the full content of a markdown documentation file"
)
async def get_doc_content(filename: str, current_user: User = Depends(require_auth)):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    if not os.path.exists(docs_dir):
        docs_dir = os.path.join(base_dir, "../docs")

    if not docs_dir:
        raise HTTPException(status_code=404, detail="Docs directory not found")

    safe_path = validate_path_within(Path(docs_dir), Path(docs_dir) / filename)

    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    with open(safe_path, "r") as f:
        content = f.read()
    # ... rest of function
```

**Path adjustment note** (D-07):
When moved from `main.py` at `agent_service/main.py` to `system_router.py` at `agent_service/routers/system_router.py`, the relative path changes:
- In `main.py`: `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` goes up 2 levels (`agent_service/main.py` → `puppeteer/`)
- In `system_router.py`: needs 3 levels to reach the same `puppeteer/` root (`agent_service/routers/system_router.py` → `puppeteer/`)

Use: `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`

**Imports needed** (add to system_router.py):
- `os` (likely already imported)
- `Path` from `pathlib` (check if already imported; if not, add)
- `validate_path_within` from security module (check if imported; if not add: `from ..utils import validate_path_within` or similar)

---

### `puppeteer/agent_service/ee/routers/vault_router.py` (router, route-definition)

**Analog:** `puppeteer/agent_service/ee/routers/vault_router.py` (self — the reinit line that needs updating)

**Context:** Update line 86 where `VaultService` is reinitialized after config update. The assignment must use the snapshot conversion.

**Current code** (lines 82-90 in `vault_router.py`):
```python
# Reinitialize vault_service with new config
try:
    vault_service = getattr(request.app.state, 'vault_service', None)
    if vault_service:
        vault_service.config = vault_config  # <-- This line needs updating
        await vault_service.startup()
        _status = await vault_service.status()
        logger.info(f"Vault service reinitialized after config update: status={_status}")
except Exception as e:
    logger.warning(f"Failed to reinitialize Vault service: {e}")
```

**Updated code** (use `VaultConfigSnapshot.from_orm()` or direct constructor):
```python
# Reinitialize vault_service with new config
try:
    vault_service = getattr(request.app.state, 'vault_service', None)
    if vault_service:
        # Create snapshot from ORM object (same pattern as VaultService.__init__)
        vault_service.config = VaultConfigSnapshot(
            enabled=vault_config.enabled,
            vault_address=vault_config.vault_address,
            role_id=vault_config.role_id,
            secret_id=vault_config.secret_id,
            mount_path=vault_config.mount_path,
            namespace=vault_config.namespace,
            provider_type=vault_config.provider_type,
        )
        await vault_service.startup()
        _status = await vault_service.status()
        logger.info(f"Vault service reinitialized after config update: status={_status}")
except Exception as e:
    logger.warning(f"Failed to reinitialize Vault service: {e}")
```

**Import addition** (at top of file, around line 1-10):
```python
from ...ee.services.vault_service import VaultService, VaultConfigSnapshot
```

or if `VaultService` is already imported differently, add `VaultConfigSnapshot` to that import.

---

## Shared Patterns

### Frozen Dataclass Pattern (used for VaultConfigSnapshot)
**Source:** `puppeteer/ee/services/siem_service.py` lines 25-38
**Apply to:** `vault_service.py`

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class VaultConfigSnapshot:
    """Immutable snapshot of VaultConfig values taken at service construction time.

    Avoids DetachedInstanceError when the ORM session that loaded the config
    is closed or committed while the long-lived singleton still holds a reference.
    """
    enabled: bool
    vault_address: str
    role_id: str
    secret_id: str
    mount_path: str
    namespace: Optional[str]
    provider_type: str
```

### Router Route Pattern
**Source:** `puppeteer/agent_service/routers/admin_router.py`, `jobs_router.py`, `system_router.py` (all consistent)
**Apply to:** All route additions in `admin_router.py`, `jobs_router.py`, `system_router.py`

```python
@router.get(
    "/path",
    response_model=SomeModel,
    tags=["TagName"],
    summary="Short summary",
    description="Longer description"
)
async def handler_name(
    param1: str,
    current_user: User = Depends(require_auth),  # or require_permission("x:y")
    db: AsyncSession = Depends(get_db)
):
    """Docstring explaining the handler."""
    # implementation
```

### Permission Guard Pattern
**Source:** `puppeteer/agent_service/routers/admin_router.py` (all admin routes)
**Apply to:** Retention routes in `admin_router.py`

```python
current_user: User = Depends(require_permission("users:write"))
```

---

## No Analog Found

All files have strong analogs or are self-contained modifications. **100% coverage achieved.**

---

## Metadata

**Analog search scope:** 
- `puppeteer/agent_service/` (deps, services, routers, main)
- `puppeteer/ee/services/` (vault_service, siem_service patterns)
- `puppeteer/ee/routers/` (vault_router reinit pattern)

**Files scanned:** 20+ Python source files

**Pattern extraction date:** 2026-04-18
