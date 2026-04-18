# Phase 167: HashiCorp Vault Integration (EE) - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 13 new/modified files
**Analogs found:** 11/13 with close matches

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `puppeteer/ee/services/vault_service.py` | service | request-response + async background | `puppeteer/agent_service/services/scheduler_service.py` | exact |
| `puppeteer/ee/interfaces/secrets_provider.py` | protocol/interface | definition | `puppeteer/agent_service/db.py` (SQLAlchemy patterns) | role-match |
| `puppeteer/ee/routers/vault_router.py` | router | request-response | `puppeteer/agent_service/ee/routers/webhook_router.py` | exact |
| `puppeteer/agent_service/db.py` (VaultConfig) | model | CRUD | `puppeteer/agent_service/db.py` (existing Config class) | exact |
| `puppeteer/agent_service/models.py` (Vault models) | pydantic model | request-response | `puppeteer/agent_service/models.py` (existing JobCreate) | exact |
| `puppeteer/agent_service/services/job_service.py` (dispatch mod) | service integration point | CRUD + secret injection | `puppeteer/agent_service/routers/jobs_router.py` | same-file |
| `puppeteer/agent_service/main.py` (lifespan hook) | initialization | startup/shutdown | `puppeteer/agent_service/main.py` (existing lifespan) | exact |
| `puppeteer/agent_service/security.py` (encryption) | utility | encryption | `puppeteer/agent_service/security.py` (existing Fernet) | exact |
| `puppeteer/dashboard/src/views/Admin.tsx` (Vault section) | component | request-response + form | `puppeteer/dashboard/src/views/Admin.tsx` (existing users/roles sections) | exact |
| `puppeteer/migration_v24_vault.sql` | migration | DDL | `puppeteer/migration*.sql` (pattern) | N/A - pattern only |
| `puppeteer/tests/test_vault_integration.py` | test | unit/integration | `puppeteer/tests/test_*.py` (existing pattern) | pattern-match |
| `puppeteer/tests/test_vault_admin.py` | test | integration | `puppeteer/tests/test_*.py` (existing pattern) | pattern-match |
| `puppeteer/requirements.txt` (hvac add) | config | dependency | existing file | update-only |

---

## Pattern Assignments

### `puppeteer/ee/services/vault_service.py` (service, request-response + background task)

**Analog:** `puppeteer/agent_service/services/scheduler_service.py` (APScheduler integration + async patterns)

**Imports pattern** (lines 1-20):
```python
import asyncio
import logging
from typing import Optional, Literal, Dict
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

# Service class with __init__, startup, and background task method
class VaultService:
    def __init__(self, config: Optional[VaultConfig], db: AsyncSession, scheduler: AsyncIOScheduler):
        self.config = config
        self.db = db
        self.scheduler = scheduler
        self._status: Literal["healthy", "degraded", "disabled"] = "disabled"
        self._consecutive_renewal_failures = 0
        self._client = None
```

**Source:** `puppeteer/agent_service/services/scheduler_service.py` lines 1-20 and 42-50

**Async startup pattern** (non-blocking initialization):
```python
async def startup(self):
    """Initialize Vault connection; non-blocking fallback on error."""
    if not self.config or not self.config.enabled:
        self._status = "disabled"
        return
    
    try:
        await self._connect()  # asyncio.to_thread() wraps hvac calls
        self._status = "healthy"
        logger.info("Vault connection established")
        # Schedule lease renewal background task
        self.scheduler.add_job(
            self._renew_leases,
            "interval",
            minutes=5,
            id="vault-lease-renewal",
            replace_existing=True,
            max_instances=1,
        )
    except Exception as e:
        self._status = "degraded"
        logger.warning(f"Vault unavailable at startup: {e}; continuing in degraded mode")
```

**Source:** `puppeteer/agent_service/services/scheduler_service.py` lines 52-79 (scheduler.start() pattern adapted for vault startup)

**Core async pattern with hvac wrapping**:
```python
async def _connect(self):
    """Establish Vault connection via AppRole using asyncio.to_thread()."""
    def _sync_login():
        import hvac
        client = hvac.Client(url=self.config.vault_address, verify=True)
        client.auth.approle.login(
            role_id=self.config.role_id,
            secret_id=self.config.decrypt_secret_id()  # Decrypt before auth
        )
        return client
    
    self._client = await asyncio.to_thread(_sync_login)

async def resolve(self, secret_names: list[str]) -> Dict[str, str]:
    """Fetch secrets from Vault KV v2 at dispatch time."""
    if self._status != "healthy":
        raise VaultUnavailableError(f"Vault status: {self._status}")
    
    resolved = {}
    for name in secret_names:
        def _sync_read():
            response = self._client.secrets.kv.v2.read_secret_version(
                path=f"{self.config.mount_path}/data/{name}"
            )
            return response["data"]["data"]["value"]
        
        try:
            value = await asyncio.to_thread(_sync_read)
            resolved[name] = value
        except Exception as e:
            self._status = "degraded"
            raise VaultError(f"Secret resolution failed for {name}: {e}")
    
    return resolved

async def _renew_leases(self):
    """Background task: renew leases at 30% TTL remaining."""
    try:
        # Query Job rows with active leases
        active_leases = await self._query_active_leases()
        for lease_id, lease_ttl in active_leases:
            if lease_ttl < (lease_ttl * 0.3):  # Renewal threshold
                try:
                    await self._renew_lease(lease_id)
                    self._consecutive_renewal_failures = 0
                except Exception as e:
                    self._consecutive_renewal_failures += 1
                    logger.warning(f"Lease renewal failed (attempt {self._consecutive_renewal_failures}): {e}")
                    if self._consecutive_renewal_failures >= 3:
                        self._status = "degraded"
    except Exception as e:
        logger.error(f"Lease renewal task error: {e}")

async def status(self) -> Literal["healthy", "degraded", "disabled"]:
    """Return current Vault status."""
    return self._status
```

**Source:** Composite pattern from `scheduler_service.py` (async/APScheduler) + `security.py` (encryption patterns)

**Status method pattern**:
```python
async def status(self) -> Literal["healthy", "degraded", "disabled"]:
    """Return three-state health status for dispatch gate + health endpoint."""
    return self._status
```

---

### `puppeteer/ee/interfaces/secrets_provider.py` (protocol/abstraction)

**Analog:** Python `typing.Protocol` + pattern from `puppeteer/agent_service/db.py` (SQLAlchemy Base pattern)

**Pattern**:
```python
from typing import Protocol, Literal
import asyncio

class SecretsProvider(Protocol):
    """Protocol for secret backends (Vault, Azure, AWS, etc.).
    
    Any class implementing this interface can be injected into job_service.dispatch_job().
    Future phases add new providers without dispatch layer changes.
    """
    
    async def resolve(self, names: list[str]) -> dict[str, str]:
        """Resolve secret names to values.
        
        Args:
            names: List of secret names/paths
        
        Returns:
            dict mapping name -> value (not encrypted; returned as plaintext for env var injection)
        
        Raises:
            SecretsError: if resolution fails
        """
        ...
    
    async def status(self) -> Literal["healthy", "degraded", "disabled"]:
        """Return current provider status.
        
        "healthy": connected, credentials valid, ready to resolve
        "degraded": connection lost, operations failed, fallback mode
        "disabled": not configured, no startup errors
        """
        ...
    
    async def renew(self) -> None:
        """Renew leases / refresh credentials.
        
        Called by background task every 5 minutes. Must not raise.
        """
        ...
```

**Source:** CONTEXT.md D-13; Python typing.Protocol standard pattern

---

### `puppeteer/ee/routers/vault_router.py` (router, request-response)

**Analog:** `puppeteer/agent_service/ee/routers/webhook_router.py` (lines 1-49)

**Imports and router setup**:
```python
"""EE Router: Vault Configuration & Management."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ...db import get_db, AsyncSession, User
from ...deps import require_permission, require_ee
from ...models import VaultConfigResponse, VaultConfigCreate, VaultStatusResponse

vault_router = APIRouter()

@vault_router.get("/admin/vault/status", response_model=VaultStatusResponse, tags=["Vault (EE)"])
async def get_vault_status(
    current_user: User = Depends(require_permission("admin:config")),
    vault_service = Depends(get_vault_service)  # Injected from app.state
):
    """Return Vault connection status (healthy/degraded/disabled)."""
    status = await vault_service.status()
    return {
        "status": status,
        "address": vault_service.config.vault_address if vault_service.config else None,
        "last_checked_at": vault_service.last_checked_at,
        "error_detail": vault_service.last_error if status == "degraded" else None
    }

@vault_router.get("/admin/vault/config", response_model=VaultConfigResponse, tags=["Vault (EE)"])
async def get_vault_config(
    current_user: User = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db)
):
    """Get current Vault configuration (secret_id masked)."""
    config = await VaultService.get_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="Vault not configured")
    return {
        "vault_address": config.vault_address,
        "role_id": config.role_id,
        "secret_id": "***MASKED***",  # Never expose plaintext
        "mount_path": config.mount_path,
        "namespace": config.namespace,
        "enabled": config.enabled,
        "provider_type": config.provider_type
    }

@vault_router.post("/admin/vault/config", response_model=VaultConfigResponse, tags=["Vault (EE)"])
async def create_or_update_vault_config(
    config_create: VaultConfigCreate,
    current_user: User = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db)
):
    """Create or update Vault configuration."""
    config = await VaultService.save_config(db, config_create)
    await db.commit()
    return {...}

@vault_router.post("/admin/vault/test", response_model=dict, tags=["Vault (EE)"])
async def test_vault_connection(
    current_user: User = Depends(require_permission("admin:config")),
    vault_service = Depends(get_vault_service)
):
    """Test current Vault connection without saving."""
    try:
        await vault_service._connect()
        return {"status": "ok", "message": "Vault connection successful"}
    except Exception as e:
        return {"status": "failed", "message": str(e)}
```

**Source:** `puppeteer/agent_service/ee/routers/webhook_router.py` lines 1-49 (APIRouter setup, Depends pattern, tags, response_model)

---

### `puppeteer/agent_service/db.py` — Add VaultConfig ORM Model

**Analog:** `puppeteer/agent_service/db.py` lines 115-118 (Config class) and security.py Fernet encryption

**Pattern**:
```python
from sqlalchemy.orm import Mapped
from sqlalchemy import String, Boolean, Text, DateTime
from datetime import datetime

class VaultConfig(Base):
    """HashiCorp Vault connection configuration (EE-gated).
    
    Stores AppRole credentials encrypted at rest via Fernet.
    Env vars VAULT_ADDRESS, VAULT_ROLE_ID, VAULT_SECRET_ID bootstrap on first boot.
    """
    __tablename__ = "vault_config"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vault_address: Mapped[str] = mapped_column(String(512), nullable=False)
    role_id: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_id: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-encrypted at rest
    mount_path: Mapped[str] = mapped_column(String(255), default="secret", nullable=False)
    namespace: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(32), default="vault", nullable=False)  # D-15: extensibility
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def encrypt_secret_id(self, cipher_suite):
        """Encrypt secret_id before storing in DB."""
        if isinstance(self.secret_id, str):
            self.secret_id = cipher_suite.encrypt(self.secret_id.encode()).decode()
    
    def decrypt_secret_id(self, cipher_suite) -> str:
        """Decrypt secret_id from DB for use with hvac."""
        if isinstance(self.secret_id, str):
            return cipher_suite.decrypt(self.secret_id.encode()).decode()
        return self.secret_id
```

**Source:** `puppeteer/agent_service/db.py` lines 115-118 (Config) + `puppeteer/agent_service/security.py` lines 61-72 (encrypt_secrets pattern)

---

### `puppeteer/agent_service/models.py` — Vault Pydantic Models

**Analog:** `puppeteer/agent_service/models.py` lines 126-150 (JobCreate pattern)

**Pattern**:
```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime

class VaultConfigCreate(BaseModel):
    """Request model for creating/updating Vault config."""
    vault_address: str = Field(..., description="Vault server address (e.g., https://vault.example.com:8200)")
    role_id: str = Field(..., description="AppRole Role ID")
    secret_id: str = Field(..., description="AppRole Secret ID")
    mount_path: str = Field(default="secret", description="KV v2 mount path (default: secret)")
    namespace: Optional[str] = Field(None, description="Vault Enterprise namespace (optional)")
    provider_type: str = Field(default="vault", description="Provider type: vault, azure_keyvault, etc.")
    enabled: bool = Field(default=False, description="Enable Vault integration")
    
    model_config = ConfigDict(from_attributes=True)

class VaultConfigResponse(BaseModel):
    """Response model for Vault config (secret_id masked)."""
    id: str
    vault_address: str
    role_id: str
    secret_id: str = Field(description="Always masked in response (***MASKED***)")
    mount_path: str
    namespace: Optional[str]
    provider_type: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class VaultStatusResponse(BaseModel):
    """Response model for Vault health status."""
    status: Literal["healthy", "degraded", "disabled"]
    address: Optional[str]
    last_checked_at: Optional[datetime]
    error_detail: Optional[str]

# Extend JobCreate (or create JobDispatchRequest) to add vault_secrets
class JobDispatchRequest(BaseModel):
    """Job dispatch request with optional Vault secret injection."""
    script_content: str
    vault_secrets: Optional[List[str]] = Field(None, description="List of Vault secret names to resolve")
    use_vault_secrets: bool = Field(default=False, description="Enable Vault secret injection")
    # ... other fields unchanged
```

**Source:** `puppeteer/agent_service/models.py` lines 126-150 (JobCreate pattern: Pydantic BaseModel, Field descriptions, model_config)

---

### `puppeteer/agent_service/services/job_service.py` — Dispatch Integration

**Analog:** Job dispatch route from `puppeteer/agent_service/routers/jobs_router.py`

**Integration pattern in dispatch_job()**:
```python
async def dispatch_job(
    job_create: JobCreate,
    current_user: User,
    db: AsyncSession,
    vault_service: Optional[VaultService] = None,  # Injected from app.state
) -> WorkResponse:
    """Dispatch job with optional Vault secret resolution."""
    
    injected_env = {}
    
    # If job requests Vault secrets, resolve server-side
    if job_create.use_vault_secrets and job_create.vault_secrets:
        if not vault_service or await vault_service.status() != "healthy":
            raise HTTPException(
                status_code=503,
                detail="Vault unavailable; cannot resolve secrets for this job"
            )
        
        try:
            resolved = await vault_service.resolve(job_create.vault_secrets)
            # Inject as VAULT_SECRET_<NAME> env vars
            injected_env = {
                f"VAULT_SECRET_{name.upper()}": value
                for name, value in resolved.items()
            }
        except VaultError as e:
            raise HTTPException(status_code=502, detail=f"Secret resolution failed: {e}")
    
    # Create Job; store secret names for audit, resolved values encrypted in DB
    job = Job(
        script_content=job_create.script_content,
        vault_secret_names=job_create.vault_secrets,  # For audit trail
        vault_injected_env=encrypt_secrets({"secrets": injected_env}),  # Encrypted
        created_by=current_user.username,
    )
    db.add(job)
    await db.commit()
    
    # Build WorkResponse with injected env vars
    work = WorkResponse(
        job_id=job.id,
        script_content=job.script_content,
        env={
            **injected_env,  # Vault secrets as env vars
            **job_create.env,  # Other env vars (unsigned)
        }
    )
    return work
```

**Source:** Pattern composite from `puppeteer/agent_service/routers/jobs_router.py` (dispatch request handling) + `puppeteer/agent_service/security.py` (encrypt_secrets)

---

### `puppeteer/agent_service/main.py` — Lifespan Integration

**Analog:** `puppeteer/agent_service/main.py` lines 87-150 (existing lifespan context manager)

**Integration pattern**:
```python
# Inside existing lifespan() context manager, after licence_service startup:

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup logic (Alembic, init_db, licence loading) ...
    
    # Load Vault service (non-blocking fallback)
    vault_service = None
    if licence_state.is_ee_active:
        try:
            async with AsyncSessionLocal() as _db:
                vault_config = await VaultService.get_config(_db)
            if vault_config:
                vault_service = VaultService(vault_config, AsyncSessionLocal, scheduler_service.scheduler)
                await vault_service.startup()
                app.state.vault_service = vault_service
                logger.info("Vault service initialized")
        except Exception as e:
            logger.warning(f"Vault initialization failed: {e}; continuing without Vault")
    
    # Register Vault router (conditional on EE license)
    if licence_state.is_ee_active:
        from .ee.routers.vault_router import vault_router
        app.include_router(vault_router, tags=["Vault (EE)"])
    
    # ... rest of startup logic ...
    
    yield  # Server runs
    
    # Shutdown: stop background lease renewal task
    if vault_service:
        if vault_service.scheduler:
            vault_service.scheduler.shutdown()
```

**Source:** `puppeteer/agent_service/main.py` lines 87-150 (lifespan structure: try/except, async with, app.state, logger patterns)

---

### `puppeteer/agent_service/security.py` — Fernet Encryption

**Analog:** `puppeteer/agent_service/security.py` lines 61-72 and 74-88 (existing encrypt/decrypt patterns)

**Pattern already established**:
```python
# Existing code in security.py can be reused:
from cryptography.fernet import Fernet

ENCRYPTION_KEY = _load_or_generate_encryption_key()  # Lines 38-39
cipher_suite = Fernet(ENCRYPTION_KEY)

# For VaultConfig.secret_id encryption:
def encrypt_value(value: str) -> str:
    """Encrypt a plaintext value using Fernet."""
    return cipher_suite.encrypt(value.encode()).decode()

def decrypt_value(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted value."""
    return cipher_suite.decrypt(encrypted.encode()).decode()
```

**Source:** `puppeteer/agent_service/security.py` lines 38-39, 61-88 (cipher_suite instance, encrypt/decrypt helpers)

**Usage in VaultConfig**:
```python
class VaultConfig(Base):
    ...
    def decrypt_secret_id(self) -> str:
        from .security import cipher_suite
        return cipher_suite.decrypt(self.secret_id.encode()).decode()
```

---

### `puppeteer/dashboard/src/views/Admin.tsx` — Vault Configuration Section

**Analog:** `puppeteer/dashboard/src/views/Admin.tsx` (existing Users/Roles tabs)

**Pattern**:
```typescript
// Inside Admin.tsx: add new tab for Vault configuration

// 1. Import existing components and hooks
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

// 2. Define Pydantic -> Zod schema for form validation
const VaultConfigSchema = z.object({
  vault_address: z.string().url("Must be valid HTTPS URL"),
  role_id: z.string().min(1, "Role ID required"),
  secret_id: z.string().min(1, "Secret ID required"),
  mount_path: z.string().default("secret"),
  namespace: z.string().optional(),
  provider_type: z.literal("vault"),
  enabled: z.boolean().default(false),
});

// 3. Component for Vault config form (reuse existing Admin form patterns)
function VaultConfigPanel() {
  const [status, setStatus] = useState<"healthy" | "degraded" | "disabled">("disabled");
  const form = useForm({
    resolver: zodResolver(VaultConfigSchema),
    defaultValues: {
      vault_address: "",
      role_id: "",
      secret_id: "",
      mount_path: "secret",
      namespace: "",
      enabled: false,
    }
  });

  async function onSubmit(data: z.infer<typeof VaultConfigSchema>) {
    try {
      const response = await authenticatedFetch("/admin/vault/config", {
        method: "POST",
        body: JSON.stringify(data),
      });
      if (response.ok) {
        // Success: reload status
        fetchVaultStatus();
      } else {
        form.setError("root", { message: await response.text() });
      }
    } catch (error) {
      form.setError("root", { message: String(error) });
    }
  }

  async function fetchVaultStatus() {
    const response = await authenticatedFetch("/admin/vault/status");
    if (response.ok) {
      const data = await response.json();
      setStatus(data.status);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Vault Configuration
          <span className={`ml-2 px-2 py-1 text-xs rounded ${
            status === "healthy" ? "bg-green-100" : status === "degraded" ? "bg-yellow-100" : "bg-gray-100"
          }`}>
            {status}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label>Vault Address</label>
            <Input {...form.register("vault_address")} placeholder="https://vault.example.com:8200" />
          </div>
          <div>
            <label>Role ID</label>
            <Input {...form.register("role_id")} />
          </div>
          <div>
            <label>Secret ID (will be masked after save)</label>
            <Input {...form.register("secret_id")} type="password" />
          </div>
          <div>
            <label>Mount Path</label>
            <Input {...form.register("mount_path")} />
          </div>
          <div>
            <label>
              <input {...form.register("enabled")} type="checkbox" />
              Enable Vault Integration
            </label>
          </div>
          <Button type="submit">Save Configuration</Button>
          <Button type="button" onClick={fetchVaultStatus}>Test Connection</Button>
        </form>
      </CardContent>
    </Card>
  );
}

// 4. Add tab to existing Admin.tsx TabsList
// In the existing <Tabs> component:
<TabsList>
  <TabsTrigger value="users">Users</TabsTrigger>
  <TabsTrigger value="roles">Roles</TabsTrigger>
  <TabsTrigger value="vault">Vault (EE)</TabsTrigger>  {/* NEW */}
</TabsList>

<TabsContent value="vault">
  <VaultConfigPanel />
</TabsContent>
```

**Source:** `puppeteer/dashboard/src/views/Admin.tsx` (existing tab pattern: TabsList/TabsContent, Card, form patterns with react-hook-form and zod validation)

---

### `puppeteer/migration_v24_vault.sql` — Database Schema

**Pattern** (no exact analog, follows migration file convention):
```sql
-- Phase 167: Add Vault configuration table
-- Run once: createdb initializes schema via create_all; existing DBs run this migration

CREATE TABLE IF NOT EXISTS vault_config (
    id VARCHAR(36) PRIMARY KEY,
    vault_address VARCHAR(512) NOT NULL,
    role_id VARCHAR(255) NOT NULL,
    secret_id TEXT NOT NULL,  -- Fernet-encrypted at rest
    mount_path VARCHAR(255) NOT NULL DEFAULT 'secret',
    namespace VARCHAR(255),
    provider_type VARCHAR(32) NOT NULL DEFAULT 'vault',
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add vault_secrets and vault_injected_env columns to jobs table (if not already exist)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS vault_secret_names TEXT;  -- JSON list of secret names
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS vault_injected_env TEXT;  -- Fernet-encrypted JSON dict
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_id VARCHAR(255);    -- Vault lease ID for renewal tracking
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_ttl INTEGER;        -- TTL in seconds

CREATE INDEX IF NOT EXISTS idx_jobs_lease_id ON jobs(lease_id) WHERE lease_id IS NOT NULL;
```

**Source:** Pattern from existing `puppeteer/migration*.sql` files (IF NOT EXISTS for idempotency, TIMESTAMP defaults, index conventions)

---

### `puppeteer/tests/test_vault_integration.py` — Unit & Integration Tests

**Analog:** Existing test patterns in `puppeteer/tests/test_*.py`

**Pattern structure**:
```python
"""Unit and integration tests for Vault service."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from agent_service.db import VaultConfig, AsyncSession
from agent_service.ee.services.vault_service import VaultService, VaultUnavailableError
from agent_service.models import VaultConfigCreate

@pytest.fixture
async def vault_config():
    """Mock VaultConfig for testing."""
    from cryptography.fernet import Fernet
    cipher = Fernet(Fernet.generate_key())
    config = VaultConfig(
        id="test-vault-id",
        vault_address="https://vault.test:8200",
        role_id="test-role",
        secret_id=cipher.encrypt(b"test-secret").decode(),
        mount_path="secret",
        enabled=True
    )
    return config

@pytest.fixture
async def vault_service(vault_config):
    """Mock VaultService with stubbed scheduler."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    db = AsyncMock(spec=AsyncSession)
    service = VaultService(vault_config, db, scheduler)
    return service

@pytest.mark.asyncio
async def test_vault_startup_healthy():
    """Test successful Vault connection at startup."""
    # Mock hvac client
    with patch('hvac.Client') as mock_client:
        mock_client.return_value.auth.approle.login.return_value = {"auth": {"client_token": "test-token"}}
        service = vault_service
        await service.startup()
        assert service._status == "healthy"

@pytest.mark.asyncio
async def test_vault_startup_unavailable():
    """Test graceful degradation when Vault unavailable at startup."""
    with patch('hvac.Client', side_effect=Exception("Connection refused")):
        service = vault_service
        await service.startup()
        assert service._status == "degraded"
        # Log warning should be called

@pytest.mark.asyncio
async def test_resolve_secrets_healthy():
    """Test secret resolution when Vault is healthy."""
    service = vault_service
    service._status = "healthy"
    service._client = MagicMock()
    service._client.secrets.kv.v2.read_secret_version.return_value = {
        "data": {"data": {"value": "test-password"}}
    }
    
    with patch('asyncio.to_thread', return_value=asyncio.coroutine(lambda: {"data": {"data": {"value": "test-password"}}})):
        result = await service.resolve(["db_password"])
        assert result == {"db_password": "test-password"}

@pytest.mark.asyncio
async def test_resolve_secrets_degraded():
    """Test secret resolution fails when Vault is degraded."""
    service = vault_service
    service._status = "degraded"
    
    with pytest.raises(VaultUnavailableError):
        await service.resolve(["db_password"])

@pytest.mark.asyncio
async def test_lease_renewal_scheduled():
    """Test lease renewal background task is registered with APScheduler."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    service = VaultService(vault_config, AsyncMock(), scheduler)
    
    await service.startup()
    
    # Check that renewal job is scheduled
    job = scheduler.get_job("vault-lease-renewal")
    assert job is not None
    assert job.trigger.interval.total_seconds() == 300  # 5 minutes

@pytest.mark.asyncio
async def test_renewal_failure_threshold():
    """Test that 3 renewal failures set status to DEGRADED."""
    service = vault_service
    service._status = "healthy"
    
    # Simulate 3 renewal failures
    for _ in range(3):
        await service._handle_renewal_failure()
    
    assert service._status == "degraded"
```

**Source:** Pattern from existing `puppeteer/tests/` (pytest fixtures, AsyncMock, patch decorators, @pytest.mark.asyncio)

---

### `puppeteer/tests/test_vault_admin.py` — Admin API Integration Tests

**Analog:** Existing integration test patterns

**Pattern structure**:
```python
"""Integration tests for Vault admin API endpoints."""
import pytest
from httpx import AsyncClient
from agent_service.main import app
from agent_service.db import AsyncSession

@pytest.mark.asyncio
async def test_vault_config_create_requires_ee():
    """Test that /admin/vault/config returns 402 if not EE."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/admin/vault/config",
            json={
                "vault_address": "https://vault.test:8200",
                "role_id": "test-role",
                "secret_id": "test-secret"
            }
        )
        # In CE mode: expect 402 (Payment Required)
        assert response.status_code == 402

@pytest.mark.asyncio
async def test_vault_status_endpoint():
    """Test /admin/vault/status returns health indicator."""
    # Assuming EE license is active in test env
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/admin/vault/status",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "disabled"]

@pytest.mark.asyncio
async def test_vault_test_connection():
    """Test POST /admin/vault/test validates Vault credentials."""
    # This tests the "Test Connection" button functionality
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/admin/vault/test",
            json={
                "vault_address": "https://invalid.test:8200",
                "role_id": "bad-role",
                "secret_id": "bad-secret"
            },
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        # Should return 200 with failed status (not 5xx)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
```

**Source:** Pattern from existing `puppeteer/tests/` (AsyncClient, @pytest.mark.asyncio, response assertions)

---

### `puppeteer/requirements.txt` — Dependency Addition

**Update required**:
```
hvac>=2.4.0
```

**Placement:** Add after existing dependencies, alphabetically between `hiredis` and `idna` if present, or at end of main dependencies section (before optional extras).

**Source:** Existing `puppeteer/requirements.txt` (format convention)

---

## Shared Patterns

### EE Gating Pattern (All Vault Routes)

**Source:** `puppeteer/agent_service/ee/routers/webhook_router.py` + `puppeteer/agent_service/services/licence_service.py`

**Apply to:** All `/admin/vault/*` routes

```python
from ...deps import require_permission

@vault_router.get("/admin/vault/status", ...)
async def get_vault_status(
    current_user: User = Depends(require_permission("admin:config")),
    ...
):
    """All vault routes require both EE licence (via app.state.vault_service) and admin:config permission."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not app.state.licence_state.is_ee_active:
        raise HTTPException(status_code=402, detail="Vault integration requires EE licence")
```

**Pattern:** Conditional router registration in `main.py` lifespan + `require_permission()` dependency on routes

---

### Error Handling Pattern

**Source:** `puppeteer/agent_service/services/job_service.py` + `security.py`

**Apply to:** All vault_service methods

```python
class VaultError(Exception):
    """Base exception for Vault service errors."""
    pass

class VaultUnavailableError(VaultError):
    """Raised when Vault is unavailable (degraded/disabled status)."""
    pass

# In dispatch_job():
try:
    resolved = await vault_service.resolve(job_create.vault_secrets)
except VaultError as e:
    raise HTTPException(status_code=502, detail=f"Vault error: {e}")
```

**Pattern:** Custom exception hierarchy + HTTPException wrapping for API responses

---

### Async/Sync Bridge Pattern (hvac wrapping)

**Source:** `scheduler_service.py` APScheduler patterns + Python 3.9+ `asyncio.to_thread()`

**Apply to:** All hvac calls in VaultService

```python
async def _connect(self):
    """Wrap synchronous hvac login in asyncio.to_thread()."""
    def _sync_login():
        import hvac
        client = hvac.Client(url=self.config.vault_address)
        client.auth.approle.login(role_id=..., secret_id=...)
        return client
    
    self._client = await asyncio.to_thread(_sync_login)

async def resolve(self, names: list[str]) -> dict[str, str]:
    """Wrap hvac read calls."""
    resolved = {}
    for name in names:
        def _sync_read():
            return self._client.secrets.kv.v2.read_secret_version(path=...)
        value = await asyncio.to_thread(_sync_read)
        resolved[name] = value
    return resolved
```

**Pattern:** Define inner `_sync_*()` function, wrap with `asyncio.to_thread()`, return/await result

---

### Encryption at Rest Pattern

**Source:** `puppeteer/agent_service/security.py` lines 38-88

**Apply to:** VaultConfig.secret_id and Job.vault_injected_env

```python
from cryptography.fernet import Fernet

# In VaultConfig model:
def decrypt_secret_id(self) -> str:
    """Decrypt secret_id from DB."""
    from agent_service.security import cipher_suite
    if isinstance(self.secret_id, str):
        return cipher_suite.decrypt(self.secret_id.encode()).decode()
    return self.secret_id

# Before storing config:
config.secret_id = cipher_suite.encrypt(plaintext_secret.encode()).decode()
```

**Pattern:** Use existing `ENCRYPTION_KEY` and `cipher_suite` from `security.py`; encrypt on save, decrypt on load

---

## No Analog Found

Files with no close match requiring pure new implementation:

| File | Role | Reason |
|------|------|--------|
| `puppeteer/ee/interfaces/secrets_provider.py` | protocol | Python Protocol is a language feature; no codebase example exists yet |

*All other files have clear analogs and can copy patterns directly from existing code.*

---

## Metadata

**Analog search scope:** `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/` (main service), `/puppeteer/ee/` (existing EE plugins), `/puppeteer/dashboard/src/views/` (React components), `/puppeteer/tests/` (test patterns)

**Files scanned:** 30+ source files; 11 strong analog matches found

**Pattern extraction date:** 2026-04-18

---

## Key Takeaways for Executor

1. **hvac wrapping:** Always wrap hvac calls in `asyncio.to_thread()` (hvac is sync; Axiom is async). See `VaultService._connect()` pattern.

2. **Lifespan integration:** Add vault_service startup to existing lifespan context manager in `main.py` (non-blocking). Avoid blocking the startup sequence if Vault is unavailable.

3. **Router registration:** Conditional on `licence_state.is_ee_active` in main.py. Include vault_router only if EE licence is valid or in grace period.

4. **Status pattern:** Use three-state Literal `["healthy", "degraded", "disabled"]` consistently. "disabled" = not configured (no errors); "degraded" = was healthy, now offline; "healthy" = working.

5. **Dispatch injection:** Resolve secrets at dispatch time in job_service, inject as `VAULT_SECRET_<NAME>` env vars. Never modify signed script content.

6. **Encryption:** Reuse existing Fernet cipher from security.py for VaultConfig.secret_id. Encrypt on save, decrypt on load and use.

7. **APScheduler integration:** Register lease renewal job with `id="vault-lease-renewal"`, `replace_existing=True`, `max_instances=1`. Use existing scheduler_service instance.

8. **EE Gating:** All `/admin/vault/*` routes behind `require_permission("admin:config")`. CE mode: 402 responses via router-level guard (no route registered).

---

*Pattern mapping complete — ready for planning phase.*
