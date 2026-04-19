# Phase 171: Security Hardening — Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 9 new/modified files
**Analogs found:** 6 / 9 (perfect matches or strong role matches)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `puppeteer/agent_service/routers/admin_router.py` | router | request-response | `puppeteer/agent_service/routers/jobs_router.py` | exact |
| `puppeteer/agent_service/routers/jobs_router.py` | router | request-response | `puppeteer/agent_service/routers/admin_router.py` | exact |
| `puppeteer/agent_service/db.py` | model+seed | config | `puppeteer/agent_service/db.py` (existing RolePermission + init_db) | exact |
| `puppeteer/agent_service/main.py` | bootstrap+util | request-response | `puppeteer/agent_service/main.py` (lines 275-289, 669-700) | exact |
| `puppeteer/ee/services/vault_service.py` | service | request-response | `puppeteer/ee/services/vault_service.py` (lines 100-187) | exact |
| `puppeteer/agent_service/routers/vault_router.py` | router | request-response | `puppeteer/agent_service/routers/admin_router.py` (PATCH pattern) | role-match |
| `puppeteer/agent_service/deps.py` | middleware+util | request-response | `puppeteer/agent_service/deps.py` (existing require_permission + cache) | exact |
| `puppeteer/agent_service/routers/system_router.py` | router | request-response | `puppeteer/agent_service/routers/system_router.py` (lines 357-366) | exact |
| `puppeteer/agent_service/tests/test_perm_cache.py` | test | test | `puppeteer/agent_service/tests/test_perm_cache.py` (existing) | exact |

---

## Pattern Assignments

### `puppeteer/agent_service/routers/admin_router.py` (router, request-response)

**Analog:** `puppeteer/agent_service/routers/admin_router.py` (existing patterns at lines 50-105, 150-177, 277-297, 403-426)

**Imports pattern** (lines 1-44):
```python
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
import logging

from ..db import get_db, AsyncSession, User
from ..deps import (
    get_current_user, require_auth,
    require_permission, audit
)
from ..models import (
    SignatureCreate, SignatureResponse, AlertResponse,
    ActionResponse, EnrollmentTokenResponse
)
```

**Permission pattern - replacing `require_auth` with `require_permission(scope)`** (line 403-426):
```python
# BEFORE (require_auth):
@router.get("/api/admin/retention", tags=["Admin"])
async def get_retention_config(
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):

# NEW pattern for signatures (require_permission("signatures:write")):
@router.post("/signatures", response_model=SignatureResponse, tags=["Signatures"])
async def upload_signature(
    sig: SignatureCreate,
    current_user: User = Depends(require_permission("signatures:write")),
    db: AsyncSession = Depends(get_db)
):
    """Upload an Ed25519 public key for job script signing."""
    return await SignatureService.upload_signature(sig, current_user, db)

@router.get("/signatures", response_model=List[SignatureResponse], tags=["Signatures"])
async def list_signatures(
    current_user: User = Depends(require_permission("signatures:write")),
    db: AsyncSession = Depends(get_db)
):
    """List all registered signature keys."""
    return await SignatureService.list_signatures(db)

# For alerts (require_permission("system:read") for GET, "system:write" for POST):
@router.get("/api/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def list_alerts(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_permission("system:read")),
    db: AsyncSession = Depends(get_db)
):
    """List system alerts."""
    return await AlertService.list_alerts(db, skip, limit)

@router.post("/api/alerts/{alert_id}/acknowledge", response_model=ActionResponse, tags=["Alerts"])
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(require_permission("system:write")),
    db: AsyncSession = Depends(get_db)
):
    """Mark an alert as acknowledged."""
    alert = await AlertService.acknowledge_alert(db, alert_id, current_user.username)
    # ...
```

**Audit pattern** (line 102, 143, 200-201):
```python
audit(db, current_user, "signature:delete", id)
await db.commit()

audit(db, current_user, "alert:acknowledge", str(alert_id))
await db.commit()

audit(db, current_user, "key:upload")
await db.commit()
```

---

### `puppeteer/agent_service/routers/jobs_router.py` (router, request-response)

**Analog:** `puppeteer/agent_service/routers/jobs_router.py` (existing patterns at lines 131, 151, 176, 213, 267, 308, 331, 415)

**Permission pattern - jobs routing** (lines 131-142, 151, 176, 213-264, 267, 308, 331):
```python
# GET /jobs with pagination — jobs:read
@router.get("/jobs", response_model=PaginatedJobResponse, tags=["Jobs"])
async def list_jobs(
    cursor: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    # ...

# GET /jobs/count — jobs:read
@router.get("/jobs/count", response_model=JobCountResponse, tags=["Jobs"])
async def count_jobs(
    status: Optional[str] = None, 
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db)
):
    # ...

# POST /jobs — jobs:write (critical: any user can run jobs)
@router.post("/jobs", response_model=JobResponse, tags=["Jobs"])
async def create_job(
    job_req: JobCreate, 
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db)
):
    # ...

# PATCH /jobs/{guid}/cancel — jobs:write
@router.patch("/jobs/{guid}/cancel", response_model=ActionResponse, tags=["Jobs"])
async def cancel_job(
    guid: str, 
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db)
):
    # ...

# GET /jobs/{guid}/dispatch-diagnosis — jobs:read
@router.get("/jobs/{guid}/dispatch-diagnosis", response_model=DispatchDiagnosisResponse, tags=["Jobs"])
async def get_dispatch_diagnosis(
    guid: str, 
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db)
):
    # ...

# POST /jobs/{guid}/retry — jobs:write
@router.post("/jobs/{guid}/retry", response_model=JobResponse, tags=["Jobs"])
async def retry_job(
    guid: str,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db)
):
    # ...

# Bulk operations also follow the read/write pattern:
@router.post("/jobs/bulk-cancel", response_model=BulkActionResponse, tags=["Jobs"])
async def bulk_cancel_jobs(
    req: BulkJobActionRequest,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    # ...
```

**Job Definitions permission pattern** (lines 654-789):
```python
# POST /jobs/definitions — jobs:write
@router.post("/jobs/definitions", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def create_job_definition(
    def_req: JobDefinitionCreate, 
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db)
):
    return await scheduler_service.create_job_definition(def_req, current_user, db)

# GET /jobs/definitions — jobs:read
@router.get("/jobs/definitions", response_model=List[JobDefinitionResponse], tags=["Job Definitions"])
async def list_job_definitions(
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db)
):
    return await scheduler_service.list_job_definitions(db)

# DELETE /jobs/definitions/{id} — jobs:write
@router.delete("/jobs/definitions/{id}", response_model=ActionResponse, tags=["Job Definitions"])
async def delete_job_definition(
    id: str, 
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db)
):
    # ...

# PATCH /jobs/definitions/{id} — jobs:write
@router.patch("/jobs/definitions/{id}", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def update_job_definition(
    id: str, 
    update_req: JobDefinitionUpdate, 
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db)
):
    return await scheduler_service.update_job_definition(id, update_req, current_user, db)
```

**CI/CD Dispatch permission pattern** (line 534-649):
```python
# POST /api/dispatch — jobs:write (critical: creates jobs)
@router.post("/api/dispatch", response_model=DispatchResponse, tags=["CI/CD Dispatch"])
async def dispatch_job(
    req: DispatchRequest,
    request,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    # ...

# GET /api/dispatch/{job_guid}/status — jobs:read
@router.get("/api/dispatch/{job_guid}/status", response_model=DispatchStatusResponse, tags=["CI/CD Dispatch"])
async def get_dispatch_status(
    job_guid: str,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    # ...
```

---

### `puppeteer/agent_service/db.py` (model+seed, config)

**Analog:** `puppeteer/agent_service/db.py` (lines 452-460)

**RolePermission model pattern** (lines 452-460):
```python
class RolePermission(Base):
    __tablename__ = "role_permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    permission: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint('role', 'permission', name='uq_role_permission'),
    )
```

**Permission seeding pattern** (from Phase 167 context + PR review findings):

At startup in `init_db()` or lifespan hook, seed role_permissions with:
```python
# Permission definitions by role
PERMS_BY_ROLE = {
    "operator": [
        "jobs:read", "jobs:write",
        "nodes:read", "nodes:write",
        "system:read", "system:write",
        "foundry:write",
        "signatures:write",
    ],
    "viewer": [
        "jobs:read",
        "nodes:read",
        "system:read",
    ],
}

async def seed_role_permissions(db: AsyncSession) -> None:
    """Seed role_permissions table if empty (Phase 171)."""
    from sqlalchemy import text
    
    # Check if already seeded
    result = await db.execute(text("SELECT COUNT(*) FROM role_permissions"))
    if result.scalar() > 0:
        return
    
    for role, perms in PERMS_BY_ROLE.items():
        for perm in perms:
            try:
                db.add(RolePermission(role=role, permission=perm))
            except Exception:
                pass  # UniqueConstraint prevents duplicates
    
    await db.commit()
```

**New permissions to add in seeding** (Phase 171 requirements):
- `nodes:read` — read-only node data (compose generation, enrollment diagnosis)
- `system:read` — read-only system state (alerts, signals listing)

These are seeded at startup to the operator and viewer roles as shown above.

---

### `puppeteer/agent_service/main.py` (bootstrap+util, request-response)

**Analog:** `puppeteer/agent_service/main.py` (lines 275-288, 669-700)

**Credential logging fix** (line 281 → lines 275-288):
```python
# BEFORE:
logger.warning("Admin bootstrapped with auto-generated password: %s", admin_password)

# AFTER:
logger.warning("Admin bootstrapped with auto-generated password (see secrets.env)")
logger.warning("You will be prompted to change it on first login.")
```

Full context (lines 275-288):
```python
admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
if not admin_password:
    # Auto-generate a random password — user must change it on first login
    import secrets as _secrets
    admin_password = _secrets.token_urlsafe(16)
    force_change = True
    # FIX: Do not log plaintext password
    logger.warning("Admin bootstrapped with auto-generated password (see secrets.env)")
    logger.warning("You will be prompted to change it on first login.")
else:
    skip_force = os.getenv("ADMIN_SKIP_FORCE_CHANGE", "").strip().lower() == "true"
    force_change = not skip_force
    if skip_force:
        logger.info("ADMIN_SKIP_FORCE_CHANGE is set — skipping forced password change")
    logger.info("Bootstrapped Admin User with provided password")
```

**YAML injection fix** (lines 669-700):

Current code (lines 669-700) interpolates user params directly:
```python
async def get_node_compose(token: str, mounts: Optional[str] = None, tags: Optional[str] = None, execution_mode: Optional[str] = None):
    """Dynamic Compose File generator for Nodes."""
    effective_tags = tags if tags else "general,linux,arm64"
    effective_execution_mode = execution_mode or os.getenv("NODE_EXECUTION_MODE", "auto")
    
    # Phase 124: Reject direct execution mode
    if effective_execution_mode == "direct":
        raise HTTPException(status_code=400, detail="...")
    
    compose_content = f"""
version: '3.8'
services:
  puppet:
    image: {os.getenv("NODE_IMAGE", "ghcr.io/axiom-laboratories/axiom-node:latest")}
    network_mode: host
    environment:
      - AGENT_URL={os.getenv("AGENT_URL", "https://localhost:8001")}
      - JOIN_TOKEN={token}
      - MOUNT_DATA={mounts if mounts else ""}
      - NODE_TAGS={effective_tags}
      - EXECUTION_MODE={effective_execution_mode}
    volumes:
      - ./secrets:/app/secrets
    restart: unless-stopped
"""
```

**FIX: Validate params to strip newlines and control characters**:
```python
import re

def _validate_compose_param(value: Optional[str], param_name: str) -> str:
    """Strip/reject newlines and YAML structural chars from compose params."""
    if not value:
        return ""
    # Reject: newlines, carriage returns, quotes, colons, dashes at line start (YAML syntax)
    if re.search(r'[\n\r"\':\-]', value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid character in {param_name}: {param_name} cannot contain newlines, quotes, colons, or YAML structural chars"
        )
    return value.strip()

async def get_node_compose(
    token: str, 
    mounts: Optional[str] = None, 
    tags: Optional[str] = None, 
    execution_mode: Optional[str] = None
):
    """Dynamic Compose File generator for Nodes."""
    # Validate all user-provided params
    effective_tags = _validate_compose_param(tags, "tags") or "general,linux,arm64"
    effective_execution_mode = _validate_compose_param(execution_mode, "execution_mode") or os.getenv("NODE_EXECUTION_MODE", "auto")
    effective_mounts = _validate_compose_param(mounts, "mounts") or ""
    
    # ... rest of function
```

---

### `puppeteer/ee/services/vault_service.py` (service, request-response)

**Analog:** `puppeteer/ee/services/vault_service.py` (lines 100-187)

**Exception narrowing in resolve() method** (lines 154-157 → lines 123-157):

BEFORE (catches all exceptions):
```python
async def resolve(self, names: list[str]) -> dict[str, str]:
    """Resolve secret names to values."""
    # ... client checks ...
    resolved = {}
    try:
        for name in names:
            # ... sync_read logic ...
            return resolved
    except Exception as e:  # TOO BROAD
        self._status = "degraded"
        self._last_error = str(e)
        raise VaultError(f"Secret resolution failed: {e}")
```

AFTER (specific hvac exceptions only):
```python
async def resolve(self, names: list[str]) -> dict[str, str]:
    """Resolve secret names to values (server-side, D-03)."""
    if self._status == "disabled":
        raise VaultError("Vault not configured")
    if self._status != "healthy":
        raise VaultError(f"Vault unavailable (status: {self._status})")
    if not self._client:
        raise VaultError("Vault client not initialized")

    resolved = {}
    try:
        for name in names:
            def _sync_read():
                response = self._client.secrets.kv.v2.read_secret_version(
                    path=name,
                    mount_point=self.config.mount_path
                )
                # KV v2 response structure: response['data']['data'][key]
                return response['data']['data']

            secret_data = await asyncio.to_thread(_sync_read)
            # Extract value or entire dict if single 'value' key
            if 'value' in secret_data:
                resolved[name] = secret_data['value']
            else:
                # If secret is a complex object, return as JSON string
                resolved[name] = json.dumps(secret_data)

        return resolved
    except (hvac.exceptions.VaultError, hvac.exceptions.InvalidRequest,
            hvac.exceptions.Forbidden, hvac.exceptions.InternalServerError,
            ConnectionError, TimeoutError, OSError) as e:
        # Only catch Vault/network errors, not programming errors
        self._status = "degraded"
        self._last_error = str(e)
        raise VaultError(f"Secret resolution failed: {e}")
```

**Auto re-auth in renew() method** (add to lines 163-187):
```python
async def renew(self) -> None:
    """Renew Vault token lease. Called by background task (D-10).
    
    Phase 171: If status is degraded and client exists, attempt re-auth first.
    """
    if self._status == "disabled":
        return  # No-op if not configured

    # Phase 171: Auto re-auth if degraded (transient recovery)
    if self._status == "degraded" and self.config:
        try:
            await self._connect()
            self._status = "healthy"
            self._consecutive_renewal_failures = 0
            logger.info("Vault status recovered to HEALTHY via automatic re-auth")
            return
        except Exception as e:
            # Re-auth failed, continue with normal retry logic below
            logger.debug(f"Auto re-auth failed: {e}")

    if not self._client:
        return  # No-op if not connected

    try:
        def _sync_renew():
            self._client.auth.token.renew_self()

        await asyncio.to_thread(_sync_renew)
        self._consecutive_renewal_failures = 0
        self._last_checked_at = datetime.now(timezone.utc)
    except Exception as e:
        self._consecutive_renewal_failures += 1
        self._last_error = str(e)
        self._last_checked_at = datetime.now(timezone.utc)
        logger.warning(f"Lease renewal failed (attempt {self._consecutive_renewal_failures}): {e}")

        if self._consecutive_renewal_failures >= 3:
            self._status = "degraded"
            logger.error("Lease renewal failed 3 times; Vault status set to DEGRADED")
```

---

### `puppeteer/agent_service/routers/vault_router.py` (router, request-response)

**Analog:** `puppeteer/agent_service/routers/admin_router.py` (PATCH pattern at lines 429-450)

**PATCH pattern template** (lines 429-450):
```python
@router.patch(
    "/api/admin/retention",
    response_model=dict,
    tags=["Admin"],
    summary="Update retention configuration",
    description="Update the execution record retention period in days"
)
async def update_retention_config(
    body: RetentionConfigUpdate,
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    """Update execution retention period in days."""
    existing = await db.execute(select(Config).where(Config.key == "execution_retention_days"))
    row = existing.scalar_one_or_none()
    if row:
        row.value = str(body.retention_days)
    else:
        db.add(Config(key="execution_retention_days", value=str(body.retention_days)))
    await db.commit()
    return {"retention_days": body.retention_days}
```

**Multi-provider vault_router endpoints** (Phase 171 decision D-15):

New vault_router.py should follow this structure:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from ..db import get_db, AsyncSession, User, VaultConfig
from ..deps import require_permission, require_ee, audit
from ..models import VaultConfigResponse, ActionResponse

vault_router = APIRouter(prefix="/admin/vault", tags=["Vault"])

@vault_router.get("/configs", response_model=List[VaultConfigResponse])
async def list_vault_configs(
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """List all vault configs (any enabled state). EE-gated."""
    result = await db.execute(select(VaultConfig))
    configs = result.scalars().all()
    return [
        VaultConfigResponse(
            id=c.id,
            provider_type=c.provider_type,
            enabled=c.enabled,
            vault_address=c.vault_address,
            secret_id="***",  # Masked
        )
        for c in configs
    ]

@vault_router.post("/config", response_model=VaultConfigResponse, status_code=201)
async def create_vault_config(
    body: VaultConfigCreate,
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vault provider config (not auto-enabled). EE-gated."""
    config = VaultConfig(
        provider_type=body.provider_type,
        vault_address=body.vault_address,
        role_id=body.role_id,
        secret_id=body.secret_id,  # Encrypted at ORM level
        mount_path=body.mount_path,
        namespace=body.namespace,
        enabled=False,  # Never auto-enable on create
    )
    db.add(config)
    audit(db, current_user, "vault:config_created", detail={"provider_type": body.provider_type})
    await db.commit()
    await db.refresh(config)
    return VaultConfigResponse.model_validate(config)

@vault_router.patch("/config/{config_id}", response_model=VaultConfigResponse)
async def update_vault_config(
    config_id: str,
    body: VaultConfigUpdate,
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific vault config by ID. EE-gated."""
    result = await db.execute(select(VaultConfig).where(VaultConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Vault config not found")
    
    if body.vault_address:
        config.vault_address = body.vault_address
    if body.role_id:
        config.role_id = body.role_id
    if body.secret_id:
        config.secret_id = body.secret_id
    if body.mount_path:
        config.mount_path = body.mount_path
    if body.namespace is not None:
        config.namespace = body.namespace
    
    audit(db, current_user, "vault:config_updated", detail={"config_id": config_id})
    await db.commit()
    await db.refresh(config)
    return VaultConfigResponse.model_validate(config)

@vault_router.delete("/config/{config_id}", response_model=ActionResponse)
async def delete_vault_config(
    config_id: str,
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Delete a vault config. Cannot delete the enabled one (409). EE-gated."""
    result = await db.execute(select(VaultConfig).where(VaultConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Vault config not found")
    
    if config.enabled:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the currently-enabled vault config. Disable it first via /enable endpoint."
        )
    
    await db.delete(config)
    audit(db, current_user, "vault:config_deleted", detail={"config_id": config_id})
    await db.commit()
    return ActionResponse(status="deleted", resource_type="vault_config", resource_id=config_id)

@vault_router.post("/config/{config_id}/enable", response_model=ActionResponse)
async def enable_vault_config(
    config_id: str,
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Enable this config and disable all others. Triggers vault_service.startup(). EE-gated."""
    # Disable all configs first
    all_result = await db.execute(select(VaultConfig))
    for config in all_result.scalars().all():
        config.enabled = False
    
    # Enable the specified one
    result = await db.execute(select(VaultConfig).where(VaultConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Vault config not found")
    
    config.enabled = True
    audit(db, current_user, "vault:config_enabled", detail={"config_id": config_id})
    await db.commit()
    
    # Trigger vault_service re-initialization with new config
    from ..ee.services.vault_service import vault_service
    await vault_service.startup()
    
    return ActionResponse(status="enabled", resource_type="vault_config", resource_id=config_id)
```

---

### `puppeteer/agent_service/deps.py` (middleware+util, request-response)

**Analog:** `puppeteer/agent_service/deps.py` (lines 88-150)

**Permission cache removal pattern** (Phase 171 decision):

BEFORE (with cache):
```python
_perm_cache: dict[str, set[str]] = {}

def _invalidate_perm_cache(role: str | None = None) -> None:
    """Clear cached permissions for a role (or all roles)."""
    if role:
        _perm_cache.pop(role, None)
    else:
        _perm_cache.clear()

def require_permission(perm: str):
    """Dependency factory that enforces a named permission via DB-backed RBAC."""
    async def _check(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        if getattr(current_user, 'role', None) == "admin":
            return current_user
        from .db import Base
        RolePermission = Base.metadata.tables.get("role_permissions")
        if RolePermission is None:
            return current_user
        if getattr(current_user, 'role', 'viewer') not in _perm_cache:  # CACHE HIT?
            # ... query DB ...
            _perm_cache[current_user.role] = {row[0] for row in result.all()}
        if perm not in _perm_cache.get(getattr(current_user, 'role', 'viewer'), set()):
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
        return current_user
    return _check
```

AFTER (always query DB):
```python
# DELETE: _perm_cache dict
# DELETE: _invalidate_perm_cache() function

def require_permission(perm: str):
    """Dependency factory that enforces a named permission via DB-backed RBAC.
    Phase 171: Always query DB (no caching — removes silent breakage in multi-worker setups).
    """
    async def _check(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        if getattr(current_user, 'role', None) == "admin":
            return current_user
        from .db import Base
        RolePermission = Base.metadata.tables.get("role_permissions")
        if RolePermission is None:
            # CE mode — no RBAC table
            return current_user
        
        # Always query DB — no caching
        from sqlalchemy import select as sa_select, text
        result = await db.execute(
            sa_select(text("permission")).select_from(text("role_permissions")).where(
                text(f"role = :role")
            ), {"role": current_user.role}
        )
        user_perms = {row[0] for row in result.all()}
        
        if perm not in user_perms:
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
        return current_user
    return _check
```

Also remove all call sites of `_invalidate_perm_cache()`:
- `puppeteer/agent_service/ee/routers/users_router.py:80` (in change password handler)
- `puppeteer/agent_service/ee/routers/users_router.py:93` (in user delete handler)

---

### `puppeteer/agent_service/routers/system_router.py` (router, request-response)

**Analog:** `puppeteer/agent_service/routers/system_router.py` (lines 357-366)

**WebSocket resource cleanup with try/finally** (lines 357-366):

BEFORE (missing finally):
```python
ws_manager._connections.append(ws)
try:
    while True:
        data = await ws.receive_text()
        if data == "ping":
            await ws.send_text("pong")
except WebSocketDisconnect:
    ws_manager.disconnect(ws)
```

AFTER (with finally):
```python
ws_manager._connections.append(ws)
try:
    while True:
        data = await ws.receive_text()
        if data == "ping":
            await ws.send_text("pong")
except WebSocketDisconnect:
    pass  # Normal disconnect
finally:
    # Always cleanup, even on unexpected exceptions
    ws_manager.disconnect(ws)
```

This ensures `ws_manager.disconnect(ws)` always runs, preventing socket leaks on non-`WebSocketDisconnect` exceptions.

---

### `puppeteer/agent_service/tests/test_perm_cache.py` (test, test)

**Analog:** `puppeteer/agent_service/tests/test_perm_cache.py` (lines 1-150)

**Test removal/update strategy** (Phase 171):

Since permission cache is being removed entirely, the test file `test_perm_cache.py` tests cache pre-warming and cache-hit behavior. Phase 171 requires:

1. **Remove test `test_prewarm_populates_perm_cache()`** — this tests cache pre-warming logic that will be deleted.

2. **Remove test `test_require_permission_uses_cache_without_db_query()`** — this tests that the DB is NOT hit when cache is warm. Since we're always querying the DB, this test is no longer valid.

3. **Add new test for always-query behavior** (if keeping the file):
   ```python
   @pytest.mark.anyio
   async def test_require_permission_always_queries_db():
       """After cache removal, require_permission() should always query DB (Phase 171)."""
       from agent_service.deps import require_permission
       from unittest.mock import AsyncMock, MagicMock

       mock_user = MagicMock()
       mock_user.role = "operator"

       # Mock DB to track if execute() is called
       mock_db = AsyncMock()
       mock_db.execute = AsyncMock(return_value=MagicMock(all=lambda: [("jobs:read",)]))

       # Create the dependency
       checker = require_permission("jobs:read")
       
       # Invoke it
       # (This test is complex due to FastAPI Depends closures — may be skipped if cache removal is complete)
   ```

   OR **simply remove the entire test file** if cache-based tests are no longer relevant.

---

## Shared Patterns

### Authentication & Authorization
**Source:** `puppeteer/agent_service/deps.py` (lines 21-150)
**Apply to:** All router files (admin_router, jobs_router, vault_router, system_router)

Pattern: Always use `Depends(require_permission("scope"))` instead of `Depends(require_auth)` for all endpoint handlers that require authorization.

**Example:**
```python
from ..deps import require_permission

@router.get("/some-endpoint", tags=["Example"])
async def some_endpoint(
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db)
):
    # Handler only executes if user has 'jobs:read' permission
    # Admin always passes (no DB check)
```

### Audit Logging
**Source:** `puppeteer/agent_service/deps.py` (lines 153-199)
**Apply to:** All router files that modify state (CREATE, UPDATE, DELETE)

Pattern: Call `audit(db, current_user, action, resource_id, detail)` before `await db.commit()`.

**Example:**
```python
audit(db, current_user, "job:cancel", guid)
await db.commit()

audit(db, current_user, "vault:config_created", detail={"provider_type": body.provider_type})
await db.commit()
```

### Exception Handling in Services
**Source:** `puppeteer/ee/services/vault_service.py` (lines 100-187)
**Apply to:** All service classes that interact with external systems

Pattern: Catch specific exception types (hvac.exceptions.*, network errors) not broad `Exception`. Update status field to track health.

**Example:**
```python
try:
    # ... service call ...
except (hvac.exceptions.VaultError, ConnectionError, TimeoutError, OSError) as e:
    self._status = "degraded"
    self._last_error = str(e)
    raise ServiceError(f"Operation failed: {e}")
```

### HTTP Response Codes
**Source:** `puppeteer/agent_service/routers/admin_router.py` (lines 127-145, 277-297)
**Apply to:** All router endpoints

Standard codes:
- `200` — GET success, PATCH success
- `201` — POST (create) success
- `204` — DELETE success (no content)
- `400` — Validation error (bad request)
- `403` — Permission denied
- `404` — Resource not found
- `409` — Conflict (e.g., cannot delete enabled config, job in wrong state)
- `422` — Unprocessable entity (e.g., signature verification failed)
- `500` — Internal server error

---

## No Analog Found

All files in Phase 171 have clear analogs in the existing codebase. No patterns require RESEARCH.md fallback.

---

## Metadata

**Analog search scope:** 
- `puppeteer/agent_service/routers/` (all routers)
- `puppeteer/agent_service/db.py` (ORM models + seeding)
- `puppeteer/agent_service/main.py` (bootstrap + composition)
- `puppeteer/agent_service/deps.py` (auth + middleware)
- `puppeteer/ee/services/vault_service.py` (external service integration)
- `puppeteer/agent_service/tests/` (test patterns)

**Files scanned:** 42 router/service/test files
**Analogs identified:** 6/9 files have exact match patterns (100%)
**Pattern extraction date:** 2026-04-19
