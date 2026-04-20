# Phase 168: SIEM Audit Streaming (EE) - Pattern Map

**Mapped:** 2026-04-18  
**Files analyzed:** 9 new/modified  
**Analogs found:** 8 / 9 (89% coverage)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `puppeteer/ee/services/siem_service.py` | service | event-driven, CRUD | `puppeteer/ee/services/vault_service.py` | exact |
| `puppeteer/agent_service/ee/interfaces/siem.py` | middleware/stub | request-response | `puppeteer/agent_service/ee/interfaces/audit.py` | exact |
| `puppeteer/agent_service/ee/routers/siem_router.py` | controller/router | request-response, CRUD | `puppeteer/agent_service/ee/routers/vault_router.py` | exact |
| `puppeteer/agent_service/db.py` (SIEMConfig) | model | CRUD | `puppeteer/agent_service/db.py` (VaultConfig) | exact |
| `puppeteer/agent_service/models.py` (SIEM responses) | model/schema | CRUD | `puppeteer/agent_service/models.py` (VaultConfig responses) | exact |
| `puppeteer/agent_service/deps.py` (audit hook) | utility/integration | event-driven | `puppeteer/agent_service/deps.py` (audit function) | exact |
| `puppeteer/agent_service/main.py` (lifespan init) | config | request-response | `puppeteer/agent_service/main.py` (vault_service init) | exact |
| `puppeteer/dashboard/src/views/Admin.tsx` (SIEM tab) | component | request-response | `puppeteer/dashboard/src/views/Admin.tsx` (Vault tab) | exact |
| `puppeteer/tests/test_siem_integration.py` | test | CRUD, event-driven | `puppeteer/tests/test_vault_integration.py` (if exists) or pytest patterns | good |

## Pattern Assignments

### `puppeteer/ee/services/siem_service.py` (service, event-driven)

**Analog:** `puppeteer/ee/services/vault_service.py` (lines 1-149)

**Imports pattern** (lines 1-20):
```python
import asyncio
import logging
from typing import Optional, Literal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
```

**Class init pattern** (lines 28-43):
```python
class VaultService(SecretsProvider):
    """HashiCorp Vault integration via AppRole auth.
    
    Non-blocking startup; graceful degradation if Vault unreachable.
    """
    
    def __init__(self, config: Optional[VaultConfig], db: AsyncSession):
        self.config = config
        self.db = db
        self._status: Literal["healthy", "degraded", "disabled"] = \
            "disabled" if not config or not config.enabled else "unknown"
        self._consecutive_renewal_failures = 0
        self._last_error: Optional[str] = None
        self._last_checked_at: Optional[datetime] = None
```

**Non-blocking startup pattern** (lines 45-61):
```python
async def startup(self) -> None:
    """Initialize Vault connection. Non-blocking; sets status to DEGRADED if fails."""
    if not self.config or not self.config.enabled:
        self._status = "disabled"
        logger.info("Vault not configured; running in dormant mode")
        return
    
    try:
        await self._connect()
        self._status = "healthy"
        self._last_checked_at = datetime.utcnow()
        logger.info(f"Vault connection established: {self.config.vault_address}")
    except Exception as e:
        self._status = "degraded"
        self._last_error = str(e)
        self._last_checked_at = datetime.utcnow()
        logger.warning(f"Vault unavailable at startup; running in degraded mode: {e}")
```

**Status methods** (lines 121-123):
```python
async def status(self) -> Literal["healthy", "degraded", "disabled"]:
    """Return current Vault status."""
    return self._status
```

**For SIEM:** Apply this pattern to `SIEMService` class with fields:
- `self.queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)` — in-memory batch buffer
- `self._dropped_events_count = 0` — overflow tracking
- Status fields inherited: `_status`, `_consecutive_failures`, `_last_error`, `_last_checked_at`
- `startup()` initializes `_test_connection()` instead of `_connect()`
- No `SecretsProvider` protocol; direct class (like VaultService inherits from protocol)

---

### `puppeteer/agent_service/ee/interfaces/siem.py` (middleware, request-response)

**Analog:** `puppeteer/agent_service/ee/interfaces/audit.py` (lines 1-13)

**Full content:**
```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

audit_stub_router = APIRouter(tags=["Audit"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)


@audit_stub_router.get("/admin/audit-log")
async def audit_log_get(): return _EE_RESPONSE
```

**For SIEM:** Create `siem_stub_router` with:
- Same 402 pattern for: `/admin/siem/config`, `/admin/siem/status`, `/admin/siem/test-connection`
- Reuse `_EE_RESPONSE` or custom variant
- Tag: `["SIEM Configuration"]`

---

### `puppeteer/agent_service/ee/routers/siem_router.py` (controller, request-response, CRUD)

**Analog:** `puppeteer/agent_service/ee/routers/vault_router.py` (lines 1-196)

**Router setup** (lines 1-18):
```python
"""EE Router: Vault integration configuration (Phase 167)."""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db, VaultConfig, User
from ...deps import require_permission, audit, require_ee
from ...models import VaultConfigResponse, VaultConfigUpdateRequest, VaultTestConnectionRequest, VaultTestConnectionResponse, VaultStatusResponse
from ...security import cipher_suite

logger = logging.getLogger(__name__)
vault_router = APIRouter()
```

**GET config endpoint pattern** (lines 21-33):
```python
@vault_router.get("/admin/vault/config", response_model=VaultConfigResponse, tags=["Vault Configuration"])
async def get_vault_config(
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Get current Vault configuration. Masks secret_id for security."""
    result = await db.execute(select(VaultConfig).where(VaultConfig.enabled == True).limit(1))
    vault_config = result.scalar_one_or_none()

    if not vault_config:
        raise HTTPException(status_code=404, detail="No Vault configuration found")

    return VaultConfigResponse.from_vault_config(vault_config)
```

**PATCH config endpoint pattern** (lines 36-94):
```python
@vault_router.patch("/admin/vault/config", response_model=VaultConfigResponse, tags=["Vault Configuration"])
async def update_vault_config(
    req: VaultConfigUpdateRequest,
    request: Request,
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Update Vault configuration and reinitialize service."""
    # Fetch existing config
    result = await db.execute(select(VaultConfig).where(VaultConfig.enabled == True).limit(1))
    vault_config = result.scalar_one_or_none()

    if not vault_config:
        raise HTTPException(status_code=404, detail="No Vault configuration found")

    # Update fields (only non-None values)
    if req.vault_address is not None:
        vault_config.vault_address = req.vault_address
    if req.role_id is not None:
        vault_config.role_id = req.role_id
    if req.secret_id is not None:
        # Encrypt secret_id before storing (D-05)
        vault_config.secret_id = cipher_suite.encrypt(req.secret_id.encode()).decode()
    # ... more fields

    # Audit the update
    audit(db, current_user, "vault:config_update", vault_config.id, {
        "vault_address": req.vault_address,
        "role_id": req.role_id is not None,
        "secret_id_updated": req.secret_id is not None,
        # ...
    })

    db.add(vault_config)
    await db.commit()

    # Reinitialize vault_service with new config
    try:
        vault_service = getattr(request.app.state, 'vault_service', None)
        if vault_service:
            vault_service.config = vault_config
            await vault_service.startup()
            _status = await vault_service.status()
            logger.info(f"Vault service reinitialized after config update: status={_status}")
    except Exception as e:
        logger.warning(f"Failed to reinitialize Vault service: {e}")

    return VaultConfigResponse.from_vault_config(vault_config)
```

**Test connection endpoint pattern** (lines 97-162):
```python
@vault_router.post("/admin/vault/test-connection", response_model=VaultTestConnectionResponse, tags=["Vault Configuration"])
async def test_vault_connection(
    req: VaultTestConnectionRequest,
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Test connection to Vault without persisting configuration."""
    try:
        from ee.services.vault_service import VaultService, VaultError
        from ...db import AsyncSessionLocal

        # Create temporary test config
        test_config = VaultConfig(
            id="test-connection",
            vault_address=req.vault_address,
            role_id=req.role_id,
            secret_id=cipher_suite.encrypt(req.secret_id.encode()).decode(),
            mount_path=req.mount_path or "secret",
            namespace=req.namespace,
            provider_type="vault",
            enabled=True,
        )

        # Create test service and attempt connection
        async with AsyncSessionLocal() as test_db:
            test_service = VaultService(test_config, test_db)
            await test_service.startup()
            status = await test_service.status()

            # Audit the test attempt
            audit(db, current_user, "vault:test_connection", req.vault_address, {
                "status": status,
                "success": status == "healthy",
            })
            await db.commit()

            if status == "healthy":
                return VaultTestConnectionResponse(
                    success=True,
                    status=status,
                    message="Connection successful. Vault is healthy and ready."
                )
            else:
                return VaultTestConnectionResponse(
                    success=False,
                    status=status,
                    error_detail=f"Vault status is {status}",
                    message=f"Connection attempted but Vault status is {status}..."
                )

    except Exception as e:
        logger.error(f"Vault test connection failed: {e}")
        error_msg = str(e)

        # Audit the failed attempt
        audit(db, current_user, "vault:test_connection_failed", req.vault_address, {
            "error": error_msg,
        })
        await db.commit()

        return VaultTestConnectionResponse(
            success=False,
            status="disabled",
            error_detail=error_msg,
            message=f"Connection test failed: {error_msg}"
        )
```

**Status endpoint pattern** (lines 165-195):
```python
@vault_router.get("/admin/vault/status", response_model=VaultStatusResponse, tags=["Vault Configuration"])
async def get_vault_status(
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Get current Vault health status with renewal failure tracking."""
    result = await db.execute(select(VaultConfig).where(VaultConfig.enabled == True).limit(1))
    vault_config = result.scalar_one_or_none()

    if not vault_config:
        raise HTTPException(status_code=404, detail="No Vault configuration found")

    vault_service = getattr(request.app.state, 'vault_service', None)

    if not vault_service:
        raise HTTPException(status_code=503, detail="Vault service not initialized")

    status = await vault_service.status()
    renewal_failures = vault_service._consecutive_renewal_failures

    return VaultStatusResponse(
        status=status,
        vault_address=vault_config.vault_address,
        last_checked_at=getattr(vault_service, '_last_checked_at', None),
        error_detail=getattr(vault_service, '_last_error', None),
        renewal_failures=renewal_failures
    )
```

**For SIEM router:** Follow the same structure with:
- `/admin/siem/config` — GET + PATCH (SIEMConfig fields: backend, destination, syslog_port, syslog_protocol, cef_device_vendor, cef_device_product, enabled)
- `/admin/siem/test-connection` — POST (similar error handling, but simpler since no creds stored)
- `/admin/siem/status` — GET (expose: status, backend, destination, last_checked_at, last_error, consecutive_failures, dropped_events)
- All endpoints require `require_ee()` dependency
- All audit actions with action names like `"siem:config_update"`, `"siem:test_connection"`, `"siem:test_connection_failed"`

---

### `puppeteer/agent_service/db.py` — SIEMConfig Model (model, CRUD)

**Analog:** `puppeteer/agent_service/db.py` VaultConfig (lines 114-132)

**VaultConfig pattern:**
```python
class VaultConfig(Base):
    """Vault integration configuration (EE only). Per D-05.

    Stored in DB for runtime editability without restart.
    secret_id is Fernet-encrypted at rest (same cipher as ENCRYPTION_KEY).
    Env var bootstrap (VAULT_ADDRESS, VAULT_ROLE_ID, VAULT_SECRET_ID) seeds this on first boot.
    """
    __tablename__ = "vault_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    vault_address: Mapped[str] = mapped_column(String(512), nullable=False)
    role_id: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_id: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-encrypted at rest
    mount_path: Mapped[str] = mapped_column(String(255), default="secret", nullable=False)
    namespace: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(32), default="vault", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**For SIEMConfig:** Create similar model with:
- `id: Mapped[str]` — primary key UUID(36)
- `backend: Mapped[str]` — "webhook" or "syslog" (String, nullable=False)
- `destination: Mapped[str]` — webhook URL or syslog host (String, nullable=False)
- `syslog_port: Mapped[int]` — default 514 (Integer, nullable=True for webhook)
- `syslog_protocol: Mapped[str]` — "UDP" or "TCP", default "UDP" (String, nullable=True)
- `cef_device_vendor: Mapped[str]` — default "Axiom" (String)
- `cef_device_product: Mapped[str]` — default "MasterOfPuppets" (String)
- `enabled: Mapped[bool]` — default False (Boolean)
- `created_at`, `updated_at` — standard datetime fields

**Env var bootstrap (in main.py):**
- `SIEM_BACKEND` → `backend`
- `SIEM_DESTINATION` → `destination`
- `SIEM_SYSLOG_PORT` → `syslog_port`
- `SIEM_SYSLOG_PROTOCOL` → `syslog_protocol`
- `SIEM_ENABLED` → `enabled`

---

### `puppeteer/agent_service/models.py` — SIEM Response Models (model/schema, CRUD)

**Analog:** `puppeteer/agent_service/models.py` VaultConfig responses (lines 187-245)

**VaultConfigResponse pattern** (lines 187-215):
```python
class VaultConfigResponse(BaseModel):
    """Response for GET /admin/vault/config. Masks secret_id for security (T-167-03)."""
    vault_address: str
    role_id: str
    secret_id_masked: str = Field(description="First 8 chars of secret_id")
    mount_path: str
    namespace: Optional[str] = None
    provider_type: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_vault_config(config: "VaultConfig") -> "VaultConfigResponse":
        """Convert DB VaultConfig to response, masking secret_id (T-167-03)."""
        masked = "***" if config.secret_id else ""
        return VaultConfigResponse(
            vault_address=config.vault_address,
            role_id=config.role_id,
            secret_id_masked=masked,
            mount_path=config.mount_path,
            namespace=config.namespace,
            provider_type=config.provider_type,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
```

**VaultConfigUpdateRequest pattern** (lines 218-226):
```python
class VaultConfigUpdateRequest(BaseModel):
    """Request body for PATCH /admin/vault/config. All fields optional (T-167-02)."""
    vault_address: Optional[str] = None
    role_id: Optional[str] = None
    secret_id: Optional[str] = None  # Only updated if provided; not returned in responses
    mount_path: Optional[str] = None
    namespace: Optional[str] = None
    provider_type: Optional[str] = None
    enabled: Optional[bool] = None
```

**VaultTestConnectionResponse pattern** (lines 240-245):
```python
class VaultTestConnectionResponse(BaseModel):
    """Response for POST /admin/vault/test-connection."""
    success: bool
    status: Literal["healthy", "degraded", "disabled"]
    error_detail: Optional[str] = None
    message: str
```

**VaultStatusResponse pattern** (lines 741-751):
```python
class VaultStatusResponse(BaseModel):
    """Response for GET /admin/vault/status. Detailed connection info."""
    status: Literal["healthy", "degraded", "disabled"]
    vault_address: str
    last_checked_at: Optional[datetime] = None
    error_detail: Optional[str] = None
    renewal_failures: int = Field(
        description="Current count of consecutive renewal failures (0-3)"
    )

    model_config = ConfigDict(from_attributes=True)
```

**For SIEM models:** Create:
- `SIEMConfigResponse` — similar to VaultConfigResponse, with fields: backend, destination, syslog_port, syslog_protocol, cef_device_vendor, cef_device_product, enabled, created_at, updated_at. No masking needed (no secrets stored). Add `from_siem_config()` factory.
- `SIEMConfigUpdateRequest` — all optional fields matching SIEMConfig
- `SIEMTestConnectionRequest` — fields: backend, destination, syslog_port (optional), syslog_protocol (optional)
- `SIEMTestConnectionResponse` — success, status, error_detail, message (same pattern as Vault)
- `SIEMStatusResponse` — status, backend, destination, last_checked_at, error_detail, consecutive_failures, dropped_events

---

### `puppeteer/agent_service/deps.py` — audit() Integration (utility, event-driven)

**Analog:** `puppeteer/agent_service/deps.py` audit() function (lines 148-174)

**Existing pattern:**
```python
def audit(db: AsyncSession, user, action: str, resource_id: str = None, detail: dict = None):
    """Append an audit entry. No-op in CE (table absent — exception swallowed).
    Works in EE regardless of which SQLAlchemy metadata AuditLog is registered in.

    Intentionally sync so callers don't need await. The DB write is scheduled as
    a background task on the running event loop so the coroutine is properly awaited.
    """
    import asyncio

    async def _insert():
        try:
            from sqlalchemy import text
            await db.execute(
                text("INSERT INTO audit_log (username, action, resource_id, detail) VALUES (:u, :a, :r, :d)"),
                {"u": user.username, "a": action, "r": resource_id, "d": json.dumps(detail) if detail else None}
            )
        except Exception:
            # In CE mode the table doesn't exist — silently ignore.
            pass

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_insert())
    except Exception:
        pass
```

**For SIEM integration:** Add after the DB insert scheduling block (around line 173):
```python
    # [NEW] Enqueue to SIEM (fire-and-forget, non-blocking, D-03)
    try:
        from .ee.services.siem_service import get_siem_service
        siem_svc = get_siem_service()
        if siem_svc is not None:
            event = {
                "timestamp": datetime.utcnow(),
                "username": user.username if user else "system",
                "action": action,
                "resource_id": resource_id,
                "detail": detail,
            }
            siem_svc.enqueue(event)  # Sync, non-blocking, returns immediately
    except Exception:
        # Never block audit() on SIEM errors
        pass
```

**Key pattern:** Wrap in try/except at module level (not inside `_insert()`). Call `enqueue()` is sync and never awaits.

---

### `puppeteer/agent_service/main.py` — Lifespan Initialization (config, request-response)

**Analog:** `puppeteer/agent_service/main.py` lines 151-168 (Vault service initialization)

**Vault pattern:**
```python
# Phase 167-02: Initialize Vault service for secret resolution
try:
    from .ee.services.vault_service import VaultService
    from .db import VaultConfig
    async with AsyncSessionLocal() as _db:
        _vc_result = await _db.execute(select(VaultConfig).where(VaultConfig.enabled == True).limit(1))
        _vault_config = _vc_result.scalar_one_or_none()
        # VaultService initialized with config (None if not enabled) and db session
        app.state.vault_service = VaultService(_vault_config, _db)
        await app.state.vault_service.startup()
        _status = await app.state.vault_service.status()
        logger.info(f"Vault service initialized: status={_status}")
except ImportError:
    logger.debug("Vault service not available (EE feature)")
    app.state.vault_service = None
except Exception as _e:
    logger.warning(f"Vault service initialization failed: {_e}")
    app.state.vault_service = None
```

**For SIEM:** Insert after Vault initialization block (same pattern):
```python
# Phase 168: Initialize SIEM service for audit log streaming
try:
    from .ee.services.siem_service import SIEMService
    from .db import SIEMConfig
    from .services.scheduler_service import scheduler_service
    async with AsyncSessionLocal() as _db:
        _siem_result = await _db.execute(select(SIEMConfig).where(SIEMConfig.enabled == True).limit(1))
        _siem_config = _siem_result.scalar_one_or_none()
        # SIEMService initialized with config (None if not enabled), db session, and scheduler
        app.state.siem_service = SIEMService(_siem_config, _db, scheduler_service.scheduler)
        await app.state.siem_service.startup()
        _status = await app.state.siem_service.status()
        logger.info(f"SIEM service initialized: status={_status}")
except ImportError:
    logger.debug("SIEM service not available (EE feature)")
    app.state.siem_service = None
except Exception as _e:
    logger.warning(f"SIEM service initialization failed: {_e}")
    app.state.siem_service = None
```

**Key difference:** Pass `scheduler_service.scheduler` (APScheduler instance) to SIEMService for flush job registration.

---

### `/system/health` Endpoint Enhancement (controller, request-response)

**Analog:** `puppeteer/agent_service/routers/system_router.py` lines 60-74

**Existing pattern:**
```python
@router.get("/system/health", response_model=SystemHealthResponse, tags=["System"])
async def system_health(request: Request):
    mirrors_available = getattr(request.app.state, "mirrors_available", True)

    # Add Vault status if configured
    vault_status = None
    vault_service = getattr(request.app.state, "vault_service", None)
    if vault_service is not None:
        vault_status = await vault_service.status()

    return {
        "status": "healthy",
        "mirrors_available": mirrors_available,
        "vault": vault_status
    }
```

**For SIEM:** Add before `return` statement:
```python
    # Add SIEM status if configured
    siem_status = None
    siem_service = getattr(request.app.state, "siem_service", None)
    if siem_service is not None:
        siem_status = await siem_service.status()

    return {
        "status": "healthy",
        "mirrors_available": mirrors_available,
        "vault": vault_status,
        "siem": siem_status,
    }
```

**Update SystemHealthResponse model** (in models.py):
```python
class SystemHealthResponse(BaseModel):
    """Response model for GET /system/health."""
    status: str = Field(description="Overall health status (healthy/degraded/unhealthy)")
    mirrors_available: bool = Field(description="Whether package mirrors are available")
    vault: Optional[Literal["healthy", "degraded", "disabled"]] = Field(
        default=None,
        description="Vault status (healthy/degraded/disabled); None if not configured"
    )
    siem: Optional[Literal["healthy", "degraded", "disabled"]] = Field(
        default=None,
        description="SIEM status (healthy/degraded/disabled); None if not configured"
    )

    model_config = ConfigDict(from_attributes=True)
```

---

### `puppeteer/dashboard/src/views/Admin.tsx` — SIEM Tab (component, request-response)

**Analog:** `puppeteer/dashboard/src/views/Admin.tsx` Vault tab (lines ~1660-2483)

**Tab structure pattern** (from lines ~2140-2160):
```typescript
<Tabs defaultValue="users" className="w-full">
    <TabsList className="mb-6 border-b rounded-none bg-transparent p-0">
        <TabsTrigger value="users" className="px-6 rounded-lg ...">Users & Roles</TabsTrigger>
        <TabsTrigger value="hashicorp-vault" className="px-6 rounded-lg ...">Vault</TabsTrigger>
        {/* NEW: Add SIEM tab here */}
        <TabsTrigger value="siem" className="px-6 rounded-lg ...">SIEM</TabsTrigger>
    </TabsList>
    
    <TabsContent value="users">
        {/* Users content */}
    </TabsContent>
    
    <TabsContent value="hashicorp-vault">
        <VaultConfigPanel isEE={isEnterprise} />
    </TabsContent>
    
    {/* NEW: Add SIEM tab content */}
    <TabsContent value="siem">
        <SIEMConfigPanel isEE={isEnterprise} />
    </TabsContent>
</Tabs>
```

**Vault panel component pattern** (from lines ~1668-2000):
```typescript
interface VaultConfigPanelProps {
  isEE: boolean;
}

function VaultConfigPanel({ isEE }: VaultConfigPanelProps) {
  const { data: config, isLoading: configLoading } = useVaultConfig();
  const { data: status, isLoading: statusLoading } = useVaultStatus();
  const updateMutation = useUpdateVaultConfig();
  const testMutation = useTestVaultConnection();

  // Form state with React Hook Form or useState
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({...});

  if (!isEE) {
    return <EEFeatureGate feature="Vault Integration" description="..." />;
  }

  return (
    <div className="space-y-6">
      {/* Status section */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Vault Status</CardTitle>
            <Badge variant={status?.status === 'healthy' ? 'outline' : 'destructive'}>
              {status?.status || 'unknown'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {/* Status details */}
        </CardContent>
      </Card>

      {/* Configuration section */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Vault Configuration</CardTitle>
            <Button onClick={() => setEditMode(!editMode)}>
              {editMode ? 'Cancel' : 'Edit'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {editMode ? (
            <form onSubmit={handleSubmit}>
              {/* Form inputs for each field */}
              <Button type="submit">Save Configuration</Button>
            </form>
          ) : (
            <div className="space-y-2">
              {/* Display current config */}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Test connection button */}
      <Button onClick={handleTestConnection} disabled={testMutation.isPending}>
        Test Connection
      </Button>
    </div>
  );
}
```

**For SIEM panel:** Create similar component with:
- Backend selector (radio buttons: Webhook / Syslog)
- Destination input (URL for webhook, host:port for syslog)
- Syslog protocol selector (UDP/TCP, shown only when syslog backend selected)
- CEF device vendor/product fields (optional, with defaults "Axiom" / "MasterOfPuppets")
- Enabled toggle
- Status badge (healthy/degraded/disabled) in header
- Test connection button
- Same edit/view mode toggle pattern

---

### `puppeteer/tests/test_siem_integration.py` (test, CRUD + event-driven)

**Analog:** Pytest patterns and test structure from codebase

**Test file structure pattern:**
- Use `pytest.fixture` for setup
- Use `AsyncSession` fixtures for DB access
- Use `pytest.mark.asyncio` for async tests
- Assert HTTP status codes and response models
- Mock external services (webhook, syslog) as needed

**Test cases (recommended):**
1. `test_siem_service_init_disabled()` — SIEMService with no config → status "disabled"
2. `test_siem_service_startup_healthy()` — SIEMService startup succeeds → status "healthy"
3. `test_enqueue_event()` — enqueue() adds event to queue
4. `test_queue_full_overflow()` — exceeding 10K events drops oldest with warning
5. `test_mask_detail()` — sensitive keys masked correctly at format time
6. `test_flush_batch_webhook()` — batch delivered to webhook URL
7. `test_flush_batch_syslog_udp()` — batch delivered to syslog UDP
8. `test_flush_batch_syslog_tcp()` — batch delivered to syslog TCP
9. `test_retry_exponential_backoff()` — failed delivery retries with 5s, 10s, 20s delays
10. `test_degraded_after_3_failures()` — status transitions to DEGRADED after 3 consecutive failures
11. `test_cef_formatting()` — event formatted as valid CEF with correct field mapping
12. `test_audit_log_not_masked()` — audit_log DB records contain raw (unmasked) detail
13. `test_siem_config_crud()` — GET/PATCH /admin/siem/config endpoints
14. `test_siem_test_connection()` — POST /admin/siem/test-connection endpoint
15. `test_siem_status()` — GET /admin/siem/status endpoint

---

## Shared Patterns

### Authentication & EE Gating
**Source:** `puppeteer/agent_service/deps.py:require_ee()` and `puppeteer/agent_service/ee/routers/vault_router.py`
**Apply to:** All SIEM admin endpoints (`/admin/siem/*`)

```python
# Pattern from vault_router.py lines 21-23:
async def get_vault_config(
    current_user: User = Depends(require_ee()),  # EE gating
    db: AsyncSession = Depends(get_db)
):
```

**For SIEM:** Every endpoint in `siem_router.py` requires `require_ee()` dependency.

---

### Audit Logging
**Source:** `puppeteer/agent_service/ee/routers/vault_router.py` lines 69-77
**Apply to:** All configuration change endpoints

```python
# Audit the update
audit(db, current_user, "vault:config_update", vault_config.id, {
    "vault_address": req.vault_address,
    "role_id": req.role_id is not None,  # Don't log actual role_id
    "secret_id_updated": req.secret_id is not None,
    "mount_path": req.mount_path,
    # ...
})
```

**For SIEM:** Audit actions:
- `"siem:config_update"` — when config is patched
- `"siem:test_connection"` — when test succeeds
- `"siem:test_connection_failed"` — when test fails

---

### Non-Blocking Startup
**Source:** `puppeteer/ee/services/vault_service.py` lines 45-61
**Apply to:** SIEMService startup initialization

Pattern: Never raise exceptions on startup. Catch all errors and set `_status = "degraded"`. Log warnings, not errors.

---

### Fire-and-Forget Event Enqueue
**Source:** Pattern from deps.py audit() and Phase 167 async patterns
**Apply to:** SIEMService.enqueue() method

```python
def enqueue(self, event: dict) -> None:
    """Queue an audit event (fire-and-forget, non-blocking)."""
    try:
        self.queue.put_nowait(event)  # Sync call, never awaits
    except asyncio.QueueFull:
        # Drop oldest on overflow
        try:
            self.queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        self.queue.put_nowait(event)
        logger.warning(f"SIEM queue overflow; dropped oldest event")
```

**Key:** Sync method (not async), uses `put_nowait()` (not `put()`), never awaits internally.

---

### Module-Level Singleton
**Source:** Pattern to be inferred from Phase 167 vault_service usage
**Apply to:** SIEM service accessor in `ee/services/siem_service.py`

```python
# At module level in siem_service.py
_siem_service: Optional[SIEMService] = None

def get_siem_service() -> Optional[SIEMService]:
    """Get active SIEM service (None in CE/dormant mode)."""
    return _siem_service

def set_active(service: SIEMService) -> None:
    """Set active SIEM service (called from main.py lifespan)."""
    global _siem_service
    _siem_service = service
```

Called in main.py:
```python
from .ee.services.siem_service import SIEMService, set_active
siem_service = SIEMService(_siem_config, _db, scheduler_service.scheduler)
await siem_service.startup()
set_active(siem_service)
```

---

### Masking Sensitive Fields
**Source:** From RESEARCH.md and project security patterns
**Apply to:** SIEMService CEF formatting

```python
SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "secret_id", "role_id", "encryption_key"}

def mask_detail(detail: dict) -> dict:
    """Mask sensitive fields in audit detail (format time, not storage time)."""
    if not detail:
        return None
    
    masked = {}
    for key, value in detail.items():
        key_lower = key.lower()
        if key_lower in SENSITIVE_KEYS or key_lower.endswith(("_key", "_secret")):
            masked[key] = "***"
        else:
            masked[key] = value
    return masked
```

**Key:** Masking happens AFTER reading from queue, BEFORE CEF formatting. Never modify stored audit_log records.

---

### Exponential Backoff Retry with APScheduler
**Source:** Phase 167 lease renewal pattern and RESEARCH.md
**Apply to:** SIEMService batch delivery

```python
# On delivery failure, schedule retry with exponential backoff
max_attempts = 3
backoff_delays = [5, 10, 20]  # seconds

for attempt in range(max_attempts):
    try:
        await self._deliver(payload)
        self._consecutive_failures = 0
        self._status = "healthy"
        return
    except Exception as e:
        self._last_error = str(e)
        self._consecutive_failures += 1
        
        if attempt < max_attempts - 1:
            delay = backoff_delays[attempt]
            self.scheduler.add_job(
                self.flush_batch,
                'date',
                run_date=datetime.utcnow() + timedelta(seconds=delay),
                args=[batch],
                id=f"siem_retry_{uuid4()}_{attempt + 1}",
                replace_existing=False,
            )
```

---

## CE Stub Router Pattern

**File:** `puppeteer/agent_service/ee/interfaces/siem.py`

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

siem_stub_router = APIRouter(tags=["SIEM Configuration"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)


@siem_stub_router.get("/admin/siem/config")
async def siem_config_get(): 
    return _EE_RESPONSE

@siem_stub_router.patch("/admin/siem/config")
async def siem_config_patch(): 
    return _EE_RESPONSE

@siem_stub_router.post("/admin/siem/test-connection")
async def siem_test_connection(): 
    return _EE_RESPONSE

@siem_stub_router.get("/admin/siem/status")
async def siem_status_get(): 
    return _EE_RESPONSE
```

**Registration in ee/__init__.py:** Add to `_mount_ce_stubs()`:
```python
from .interfaces.siem import siem_stub_router
app.include_router(siem_stub_router)
```

**Registration in ee/routers/__init__.py:**
```python
from .siem_router import siem_router
__all__ = [..., "siem_router"]
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (None) | — | — | All files have direct analogs from Phase 167 or existing codebase patterns. |

---

## Architecture Notes

### APScheduler Integration
**Key fact:** `scheduler_service.scheduler` (AsyncIOScheduler instance) is already running in main.py. Pass it to SIEMService for:
1. Periodic flush job (every 5s) — register with `id='__siem_flush__'` and `replace_existing=True`
2. Retry jobs on failed delivery — use unique IDs like `f"siem_retry_{uuid4()}_{attempt}"`

### Database Session Handling
**Key fact:** SIEMService receives a DB session in `__init__()` but startup is non-blocking. Do not pass the same session to `startup()` — it may be stale. Instead, fetch fresh SIEMConfig from DB on every startup call.

### Service Accessor Import Path
**Key:** In `deps.py:audit()`, import as:
```python
from .ee.services.siem_service import get_siem_service
```

Not a direct import of `siem_service` module. This allows CE mode to work (module imports fine; `get_siem_service()` returns None).

---

## Metadata

**Analog search scope:** 
- `puppeteer/ee/services/` — VaultService class structure
- `puppeteer/agent_service/ee/interfaces/` — CE stub router pattern
- `puppeteer/agent_service/ee/routers/` — vault_router endpoint patterns
- `puppeteer/agent_service/db.py` — VaultConfig ORM model
- `puppeteer/agent_service/models.py` — Response model patterns (Vault*)
- `puppeteer/agent_service/deps.py` — audit() function integration point
- `puppeteer/agent_service/main.py` — lifespan and VaultService init
- `puppeteer/agent_service/routers/system_router.py` — /system/health endpoint
- `puppeteer/dashboard/src/views/Admin.tsx` — Vault tab UI pattern

**Files scanned:** 12 files (service, interfaces, routers, models, deps, main, system, Admin component)

**Pattern extraction date:** 2026-04-18

---

**Planner can now reference these analogs in task implementations. All patterns are concrete (specific files and line numbers) and immediately actionable.**
