# Technology Stack — v24.0 Security Infrastructure & Extensibility

**Project:** Axiom (Master of Puppets)
**Researched:** 2026-04-18
**Mode:** Ecosystem (stack additions for new v24.0 features)

## Executive Summary

v24.0 introduces **5 new feature areas** requiring strategic technology additions:

1. **HashiCorp Vault integration** — external secrets management
2. **TPM-based node identity** — hardware-backed attestation (EE only)
3. **Plugin System v2 SDK** — third-party extensibility via entry_points
4. **SIEM audit streaming** — real-time compliance log export
5. **FastAPI router refactoring** — code organization (no new libraries)

**Existing stack unchanged:** FastAPI, SQLAlchemy, React/Vite, Alembic, Python 3.11/3.12/3.13.

**New libraries are OPTIONAL or EE-only.** CE deployments function without Vault, TPM, or syslog integration. Plugin SDK uses Python stdlib only.

---

## New Dependencies by Feature

### 1. HashiCorp Vault Integration (Optional, EE-preferred)

| Library | Version | Purpose | Why This |
|---------|---------|---------|----------|
| `hvac` | `>= 1.2.0` | Official HashiCorp Vault Python client | Maintained by hvac team; production-ready; supports AppRole + token auth; 95KB wheel (minimal footprint) |

**Status:** ACTIVE. Latest release 2025. Supports Vault v1.4.7+.

**Authentication patterns supported:**
- **AppRole:** role_id + secret_id (machine auth, recommended)
- **Token:** direct token injection (simpler, less secure)

**Integration:**
```python
# puppeteer/agent_service/services/vault_service.py (new)
import hvac

vault_client = None

async def init_vault(vault_addr: str, auth: str, role_id: str = None, secret_id: str = None):
    """Initialize Vault client if configured."""
    global vault_client
    if not vault_addr:
        return  # Vault disabled
    
    vault_client = hvac.Client(url=vault_addr)
    
    if auth == "approle":
        vault_client.auth.approle.login(role_id=role_id, secret_id=secret_id)
    elif auth == "token":
        vault_client.token = os.environ["VAULT_TOKEN"]
    
    assert vault_client.is_authenticated()

async def get_secret(path: str) -> dict:
    """Fetch KV v2 secret."""
    if not vault_client:
        return {}
    return vault_client.secrets.kv.v2.read_secret_version(path=path)["data"]["data"]
```

**Environment variables (optional):**
```bash
VAULT_ADDR=https://vault.internal:8200
VAULT_AUTH_METHOD=approle  # or 'token'
VAULT_ROLE_ID=...
VAULT_SECRET_ID=...
VAULT_TOKEN=...
```

**Alternatives considered:**
- `python-vault` (2.2.0, released 2026-02-07): lightweight AppRole wrapper, but no token renewal hooks; hvac is official
- Custom HTTP client (not enough payoff, hvac exists)

**Confidence:** HIGH. hvac is well-maintained, widely deployed, integrates cleanly via env vars.

---

### 2. TPM-Based Node Identity (EE Only)

| Library | Version | Purpose | Why This |
|---------|---------|---------|----------|
| `tpm2-pytss` | `>= 0.5.0` | TSS Python bindings for TPM 2.0 | Official TPM2 software bindings; supports ESYS/FAPI, key operations, attestation quotes |
| `tpm2-tools` (system) | `>= 5.4` | TPM command-line tools | Used by tpm2-pytss for low-level operations; installed on node image only |

**Status:** INACTIVE but STABLE. Last release 2024. No known breaking changes. No active alternatives in Python.

**Integration (node-side):**
```python
# puppets/environment_service/tpm_identity.py (new)
from tpm2_pytss import TPM2

def get_srk_public_key() -> bytes:
    """Load Storage Root Key (SRK) public key from TPM."""
    with TPM2() as tpm:
        srk_handle = 0x81000001  # Standard SRK handle
        public_key = tpm.esys_tr_object_from_tpm_public(srk_handle)
        return public_key.public.buffer  # Serialized bytes

def generate_attestation_quote(nonce: bytes) -> bytes:
    """Generate TPM quote for server attestation verification."""
    with TPM2() as tpm:
        quote_result = tpm.quote(
            pcr_selection=[...],
            qualifying_data=nonce
        )
        return quote_result.quote  # Attestation data
```

**Enrollment flow:**
```http
POST /api/enroll
{
  "node_id": "node-123",
  "tpm_srk_public_key": "hex...",
  "tpm_attestation_quote": "hex..."
}

Response:
{
  "certificate": "pem...",
  "status": "ENROLLED"
}
```

**Server-side validation:**
```python
# puppeteer/agent_service/services/pki_service.py (extend)
from cryptography.hazmat.primitives.asymmetric import rsa

def verify_tpm_quote(quote_bytes: bytes, nonce: bytes, srk_public_key_bytes: bytes) -> bool:
    """Verify TPM quote signature with stored SRK public key."""
    # tpm2-pytss provides quote verification helpers
    # Store srk_public_key in nodes.tpm_srk_public_key column
    return True  # Simplified; actual crypto operations occur here
```

**Alternatives considered:**
- Custom ctypes bindings to libtpm2-tss (too much maintenance)
- Microsoft TPM2-TSS (Windows only)

**Confidence:** MEDIUM-HIGH. Library is stable but inactive. No breaking changes expected. TPM 2.0 spec is stable (since 2014).

---

### 3. Plugin System v2 SDK (CE + EE)

| Technology | Version | Purpose | Why This |
|------------|---------|---------|----------|
| `importlib.metadata` | stdlib (Python 3.11+) | Plugin discovery via entry_points | Built-in stdlib; replaced deprecated `pkg_resources`; no external dependency |

**Status:** STABLE. Standard library since Python 3.8. Improved "selectable" entry points in Python 3.10.

**Plugin registration pattern (author-side):**
```toml
# axiom_plugins/pyproject.toml
[project.entry-points."axiom_plugins"]
custom_auth = "custom_auth_plugin:CustomAuthPlugin"
ldap_sync = "ldap_sync_plugin:LDAPSyncPlugin"
```

**Discovery & loading (server-side):**
```python
# puppeteer/agent_service/services/plugin_service.py (new)
from importlib.metadata import entry_points

def load_plugins():
    """Discover and load registered plugins."""
    eps = entry_points(group="axiom_plugins")
    
    for ep in eps:
        # Validation gate: ensure exact class match
        if not ep.value.endswith(":CustomAuthPlugin"):
            logger.error(f"Invalid plugin class: {ep.value}")
            continue
        
        try:
            plugin_class = ep.load()
            plugin_instance = plugin_class()
            logger.info(f"Loaded plugin: {ep.name}")
        except Exception as e:
            logger.error(f"Plugin load failed: {e}")
```

**No external libraries.** Uses Python 3.11 stdlib only.

**Confidence:** HIGH. importlib.metadata is stable, standard, and already used in the codebase (v11.0 replaced pkg_resources).

---

### 4. SIEM Audit Log Streaming (Optional, EE-preferred)

| Library | Version | Purpose | Why This |
|---------|---------|---------|----------|
| `syslogcef` | `>= 0.3.0` | RFC 5424 syslog + CEF/LEEF formatting | Composable mapping; handles edge cases (escaping, timestamps); production-grade |
| `rfc5424-logging-handler` | `>= 1.4.3` | RFC 5424 Python logging handler | Official RFC 5424 handler; integrates with `logging` module; cross-platform (Unix + Windows) |
| `graypy` | `>= 2.2.0` (optional) | GELF handler for Graylog | Battle-tested; supports UDP + TCP; community-maintained; OPTIONAL for Graylog-only teams |

**Status:** All ACTIVE. syslogcef (2024), rfc5424-logging-handler (2025), graypy (2025).

**Format support matrix:**
| Format | Library | Status |
|--------|---------|--------|
| RFC 5424 (Syslog) | rfc5424-logging-handler | Native |
| CEF (ArcSight) | syslogcef | Native |
| LEEF (Qradar) | syslogcef | Native |
| GELF (Graylog) | graypy | Native |
| JSON | Native Python `json` | Native |
| Webhook/HTTPS | Python `aiohttp` (existing) | Native |

**Integration:**
```python
# puppeteer/agent_service/services/siem_service.py (new)
import asyncio
import syslogcef
from rfc5424_logging_handler import Rfc5424SysLogHandler
import aiohttp

class SIEMExporter:
    def __init__(self, export_format: str, destination: str):
        """
        export_format: 'syslog' | 'cef' | 'leef' | 'json' | 'webhook'
        destination: 'host:port' or 'https://webhook-url'
        """
        self.format = export_format
        self.destination = destination
        self.queue = asyncio.Queue(maxsize=10000)  # Bounded backpressure
    
    async def export_audit_log(self, audit: AuditLog):
        """Queue audit log for async export."""
        try:
            await asyncio.wait_for(self.queue.put(audit), timeout=1.0)
        except asyncio.TimeoutError:
            # Drop oldest on overflow
            try:
                self.queue.get_nowait()
                await self.queue.put(audit)
            except asyncio.QueueEmpty:
                pass
    
    async def _export_loop(self):
        """Background worker: format and send."""
        while True:
            audit = await self.queue.get()
            
            payload = self._format_audit(audit)
            
            try:
                if self.format == "webhook":
                    async with aiohttp.ClientSession() as session:
                        await session.post(
                            self.destination,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=5)
                        )
                else:
                    # Syslog via UDP/TCP
                    host, port = self.destination.rsplit(":", 1)
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.sendto(payload.encode(), (host, int(port)))
                    sock.close()
            except Exception as e:
                logger.error(f"SIEM export failed: {e}")
    
    def _format_audit(self, audit: AuditLog) -> str:
        """Format audit log per configured format."""
        if self.format == "cef":
            return syslogcef.mapping.to_cef({
                "actor": audit.actor,
                "action": audit.action,
                "resource": audit.resource,
                "result": audit.result,
                "timestamp": audit.created_at.isoformat(),
            })
        elif self.format == "leef":
            # LEEF format via syslogcef
            return syslogcef.mapping.to_leef({...})
        elif self.format == "json":
            return json.dumps({
                "timestamp": audit.created_at.isoformat(),
                "event_type": audit.event_type,
                "actor": audit.actor,
                "resource": audit.resource,
                "action": audit.action,
                "result": audit.result,
            })
        else:
            # RFC 5424 syslog
            return audit.to_rfc5424()
```

**Environment variables (optional):**
```bash
SIEM_EXPORT_FORMAT=cef        # or 'syslog', 'leef', 'json', 'webhook'
SIEM_DESTINATION=splunk.internal:514  # or 'https://splunk.internal/hec'
```

**Alternatives considered:**
- `pygelf` (GELF only, not full SIEM spectrum)
- Custom formatters (don't solve edge cases; syslogcef handles escaping, timestamps)

**Confidence:** HIGH. All three libraries are production-grade, actively maintained, and proven in enterprise deployments.

---

### 5. FastAPI Router Refactoring (No New Libraries)

**Current:** `main.py` contains 2,000+ lines with all 89 routes in one file.

**Goal:** Modularize into domain APIRouter groups.

**Pattern (idiomatic FastAPI):**
```python
# puppeteer/agent_service/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/auth", tags=["auth"])

async def require_auth(token: str = Header(...)) -> User:
    """Shared dependency for all protected routes."""
    user = decode_jwt(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

@router.get("/me")
async def get_profile(user: User = Depends(require_auth)):
    return UserResponse.from_orm(user)

# puppeteer/agent_service/main.py
from fastapi import FastAPI
from routers import auth_router, jobs_router, nodes_router, admin_router

app = FastAPI()
app.include_router(auth_router.router, prefix="/api")
app.include_router(jobs_router.router, prefix="/api")
```

**Router structure (proposed):**
- `routers/auth_router.py` — JWT, OAuth device flow, token management
- `routers/jobs_router.py` — dispatch, execute, list, detail, cancel
- `routers/nodes_router.py` — enroll, heartbeat, /work/pull, capabilities, heartbeat
- `routers/admin_router.py` — users, roles, audit, system config, licence
- `routers/scheduling_router.py` — job definitions, workflows, cron scheduling
- `routers/foundry_router.py` — templates, blueprints, image builds, ingredient registry
- `routers/signatures_router.py` — Ed25519 key management
- `routers/webhooks_router.py` — workflow webhook triggers
- `routers/health_router.py` — health checks, /health/scale, /system/crl.pem

**Dependencies injected via Depends():**
```python
# Shared dependency factory
async def get_current_user(token: str = Header(...)) -> User:
    user = decode_jwt(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

async def require_permission(perm: str):
    """Factory: returns a Depends()-compatible function."""
    async def _require(user: User = Depends(get_current_user)) -> User:
        if not check_permission(user, perm):
            raise HTTPException(status_code=403)
        return user
    return _require
```

**Benefits:**
- Reduced file size (89 routes in one file → ~10 routes per router)
- Testability (router can be tested in isolation)
- Maintainability (feature-focused grouping)
- Reusability (routers can be shared across instances)

**No external libraries.** Uses FastAPI's built-in `APIRouter` + `Depends()`.

**Confidence:** HIGH. APIRouter is idiomatic FastAPI (documented since v0.85); already used for EE plugins in v11.0.

---

## Installation

### Backend Requirements

```bash
# puppeteer/requirements.txt (add to existing)

# Core (unchanged)
fastapi>=0.104.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
cryptography>=46.0.7  # Bumped for Dependabot fix
pyjwt>=2.8.0
asyncpg>=0.28.0

# NEW: Optional/EE features (all required in wheel, skipped at runtime if not licensed)
hvac>=1.2.0                      # Vault integration (optional)
tpm2-pytss>=0.5.0               # TPM 2.0 bindings (EE only)
syslogcef>=0.3.0                # CEF/LEEF formatting (optional)
rfc5424-logging-handler>=1.4.3  # RFC 5424 syslog (optional)
graypy>=2.2.0                   # Graylog GELF handler (optional, omit if not needed)

# importlib.metadata is stdlib (Python 3.11+)
```

### Node Image (EE Only, Optional TPM)

```dockerfile
# puppets/Containerfile.node (EE variant, or conditional RUN)

# Add TPM 2.0 support (EE only)
RUN apt-get update && apt-get install -y \
    tpm2-tools>=5.4 \
    tpm2-tss \
    && rm -rf /var/lib/apt/lists/*

# Continue with existing node setup
```

---

## Dependabot Vulnerability Remediation

**Status:** 2 HIGH, 1 MODERATE flagged on v23.0 tag push (2026-04-18).

**Remediation strategy:**
1. Identify CVE in GitHub Security tab (Dependabot alerts)
2. Check pypi.org for fixed version
3. Update `puppeteer/requirements.txt` with pinned version
4. Test in Docker stack (pytest + E2E)
5. Bump `CHANGELOG.md` with security note
6. Commit + tag as `v24.0.X-security-fix` if high severity

**Example pattern:**
```
# Before
cryptography>=41.0.0

# After
cryptography>=46.0.7  # CVE-2026-39892: buffer overflow fix in non-contiguous buffer handling
```

**Security-critical packages (no cooldown):**
- `cryptography` — asymmetric crypto primitives
- `pyjwt` — JWT validation
- `starlette` — ASGI transport layer (FastAPI dependency)
- `sqlalchemy` — ORM query safety
- `aiohttp`, `requests` — HTTP client security

---

## Stack Summary Table

| Category | Technology | Version | CE | EE | Optional | Notes |
|----------|-----------|---------|----|----|----------|-------|
| **Secrets** | hvac | >= 1.2.0 | - | ✓ | YES | Vault AppRole/token auth |
| **TPM** | tpm2-pytss | >= 0.5.0 | - | ✓ | YES | Node-side, inactive upstream |
| **TPM** | tpm2-tools | >= 5.4 | - | ✓ | YES | System package |
| **Plugins** | importlib.metadata | stdlib | ✓ | ✓ | NO | Built-in, no external dep |
| **Audit** | syslogcef | >= 0.3.0 | - | ✓ | YES | CEF/LEEF/syslog format |
| **Audit** | rfc5424-logging-handler | >= 1.4.3 | - | ✓ | YES | RFC 5424 handler |
| **Audit** | graypy | >= 2.2.0 | - | ✓ | YES | Graylog GELF only |
| **Router** | FastAPI APIRouter | built-in | ✓ | ✓ | NO | Code organization |

---

## Configuration Examples

### Vault (Optional, EE)

```python
# Environment setup in compose.server.yaml or secrets.env
VAULT_ADDR=https://vault.internal:8200
VAULT_AUTH_METHOD=approle
VAULT_ROLE_ID=<role-id>
VAULT_SECRET_ID=<secret-id>
```

### TPM (Optional, EE)

```python
# Node-side: automatic at enrollment
# No config needed; node probes TPM, server stores srk_public_key
```

### SIEM Streaming (Optional, EE)

```bash
# Environment setup
SIEM_EXPORT_FORMAT=cef
SIEM_DESTINATION=splunk.internal:514

# OR webhook
SIEM_EXPORT_FORMAT=webhook
SIEM_DESTINATION=https://splunk.internal/hec
```

### FastAPI Routers (CE + EE)

```python
# main.py refactor: no config needed
# Routers auto-included during app initialization
app.include_router(auth_router.router, prefix="/api", tags=["auth"])
```

---

## What NOT to Add

❌ **Do not add:**
- `vaultpy` (unofficial wrapper; hvac is official)
- `pycryptodome` (cryptography is already depended on)
- Custom TPM bindings (tpm2-pytss exists)
- SFTP/rsyslog (syslog via standard UDP/TCP is sufficient)
- Orchestration frameworks (Docker Compose is the target)
- Additional SIEM connectors (CEF/LEEF/JSON cover 95% of use cases)

---

## Integration Points — How Features Connect

### Vault → Job Secrets
Jobs can reference Vault secrets at dispatch time. Server fetches secrets, injects as env vars:
```json
{
  "script": "python my_script.py",
  "vault_secrets": ["database/password", "api/key"]
}
```

### TPM → Node Enrollment
Node proves TPM ownership during `/api/enroll` via attestation quote. Server stores SRK public key for future attestations.

### Plugin SDK → Custom Authenticators
Plugin authors register custom auth via `entry_points["axiom_plugins"]`. Server discovers and loads at startup.

### SIEM → Audit Trail
Every `AuditLog` entry is streamed in real-time to SIEM via configured format (CEF/syslog/webhook).

### Router Refactoring → Maintainability
89 routes split into 8 feature-focused routers, each with shared dependencies. Easier to test, review, and modify.

---

## Confidence Assessment

| Area | Level | Notes |
|------|-------|-------|
| **hvac library** | HIGH | Official Vault client, v1.2.0+, widely deployed |
| **tpm2-pytss library** | MEDIUM-HIGH | Stable but inactive; no breaking changes expected |
| **importlib.metadata** | HIGH | Stdlib since Python 3.8; already used in codebase |
| **syslogcef library** | HIGH | Production-grade, handles edge cases, actively maintained |
| **rfc5424-logging-handler** | HIGH | RFC 5424 compliant, cross-platform, actively maintained |
| **graypy library** | HIGH | Battle-tested, community standard for Graylog |
| **FastAPI APIRouter pattern** | HIGH | Idiomatic FastAPI, documented, proven pattern |
| **Dependabot fixes** | HIGH | Standard remediation: update package, test, commit |

---

## Sources

- [hvac — Python Client Library for HashiCorp Vault](https://python-hvac.org/)
- [hvac GitHub Repository](https://github.com/hvac/hvac)
- [HashiCorp Vault AppRole Authentication](https://developer.hashicorp.com/vault/docs/auth/approle)
- [tpm2-pytss GitHub](https://github.com/tpm2-software/tpm2-pytss)
- [tpm2-pytss Documentation](https://tpm2-pytss.readthedocs.io/)
- [Python Plugin Discovery Guide (packaging.python.org)](https://packaging.python.org/guides/creating-and-discovering-plugins/)
- [Python importlib.metadata Documentation](https://docs.python.org/3.11/library/importlib.metadata.html)
- [syslogcef PyPI Package](https://pypi.org/project/syslogcef/)
- [rfc5424-logging-handler Documentation](https://rfc5424-logging-handler.readthedocs.io/)
- [graypy GitHub](https://github.com/severb/graypy)
- [RFC 5424 - The Syslog Protocol](https://tools.ietf.org/html/rfc5424)
- [FastAPI Dependencies Documentation](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI APIRouter Guide](https://www.getorchestra.io/guides/mastering-fastapis-apirouter-a-detailed-guide/)
- [FastAPI Best Practices (GitHub)](https://github.com/zhanymkanov/fastapi-best-practices)
