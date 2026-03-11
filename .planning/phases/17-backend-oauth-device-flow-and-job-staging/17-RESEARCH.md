# Phase 17: Backend — OAuth Device Flow & Job Staging - Research

**Researched:** 2026-03-11
**Domain:** FastAPI auth endpoints, OAuth 2.0 Device Authorization Grant (RFC 8628), SQLAlchemy ORM schema evolution, APScheduler dispatch filtering
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Device approval page**
- A minimal GET /auth/device/approve?user_code=XXXX route returning inline HTML — no React, no build step
- Approval page requires the user to be logged in (valid session JWT); redirect to /login if not authenticated
- Page has both Approve and Deny buttons — Deny immediately invalidates the device code
- Post-action: success screen on Approve ("Device authorized. You may close this tab."), error screen on Deny

**Device code storage**
- In-memory dict with TTL — a module-level dict mapping device_code → {user_code, expiry, status, username, approved_by}
- TTL: 5 minutes
- Distinct error codes at POST /auth/device/token: authorization_pending (still waiting), access_denied (user clicked Deny), expired_token (TTL passed)
- Default polling interval: 5 seconds, with slow_down support (server returns slow_down, CLI backs off +5s per occurrence) per RFC 8628

**Device flow JWT**
- Issued JWT is a full user JWT matching the approving user's role — same claims as password login (sub=username, role=..., tv=token_version)
- Same expiry as regular tokens (ACCESS_TOKEN_EXPIRE_MINUTES env var)
- JWT carries type=device_flow in claims to distinguish from regular login tokens (allows future restriction if needed)

**verification_uri construction**
- verification_uri = AGENT_URL + /auth/device/approve (reads existing AGENT_URL env var — no new config)
- Response also includes verification_uri_complete = AGENT_URL/auth/device/approve?user_code=XXXX (pre-filled for CLI to open directly)
- User code format: XXXX-XXXX alphanumeric, uppercase, excluding confusable chars (0/O, 1/I/L) — e.g. "JTKB-MXRQ"

**status vs is_active**
- Status field is additive alongside is_active — both coexist as separate concerns
  - is_active: the scheduler on/off switch (admin/operator toggle from dashboard)
  - status: lifecycle governance (DRAFT / ACTIVE / DEPRECATED / REVOKED)
- Default status for new pushed jobs: DRAFT (not scheduled until operator promotes to ACTIVE)
- Scheduler dispatch checks BOTH: is_active=true AND status NOT IN (DRAFT, REVOKED)
- DEPRECATED jobs are also skipped at dispatch — auditable (AuditLog entry written each time a DEPRECATED job is skipped)
- Status check fires at APScheduler cron trigger time — DRAFT/REVOKED/DEPRECATED jobs never produce a Job record
- is_active and status are orthogonal — toggling is_active does NOT auto-update status

**REVOKE governance**
- Admin-only: only admin role can set a job to REVOKED
- REVOKE is reversible to DEPRECATED (not permanent) — guards against mistakes
- REVOKED jobs are immutable via the push endpoint — POST /api/jobs/push with a REVOKED job's ID returns 409
- Admin must un-REVOKE to DEPRECATED first before re-pushing

**Push endpoint (POST /api/jobs/push) behavior**
- Accepts both user JWTs (device flow) and service principal JWTs — pushed_by records "username" or "sp:name"
- Permission gate: jobs:write (consistent with existing job management endpoints)
- Upsert key: name for create, id for update
  - Push with name only: creates new job (DRAFT status) — returns 409 if name already exists, with the conflicting job's ID in the error
  - Push with id: updates script/signature on the existing job
- Pushing an update does NOT change status — status is managed separately (dashboard or PATCH /api/jobs/definitions/{id})
- Response: full JobDefinitionResponse including id, name, status, pushed_by, created_at

### Claude's Discretion
- Exact migration number for the new columns (next available after migration_v26)
- HTML styling for the minimal approval page
- Exact in-memory dict cleanup strategy (background task vs lazy expiry on next access)
- Whether to add an index on ScheduledJob.status for dispatch query performance

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-CLI-01 | MoP Control Plane exposes a device authorization endpoint (`POST /auth/device`) that issues a device code and user code | RFC 8628 device authorization request/response shape; in-memory store pattern; user code generation with confusable-char exclusion |
| AUTH-CLI-02 | MoP polls and exchanges a device code for a short-lived JWT once the user approves in browser | RFC 8628 token request/response including error codes; existing `create_access_token()` reuse; approval page form POST handlers |
| STAGE-01 | `ScheduledJob` has a `status` field: DRAFT / ACTIVE / DEPRECATED / REVOKED | DB column addition via migration_v27.sql; backfill to ACTIVE for existing rows; model update |
| STAGE-02 | `POST /api/jobs/push` upsert endpoint — creates a new DRAFT or updates existing job by ID | Upsert logic, 409 conflict on duplicate name, immutability of REVOKED jobs |
| STAGE-03 | Server verifies the JWT identity before processing, then verifies the Ed25519 signature before saving | Existing `require_permission("jobs:write")` + `get_current_user()` + `SignatureService.verify_payload_signature()` reuse |
| STAGE-04 | `pushed_by` field records the authenticated operator identity on each push | DB column addition; derive identity from `current_user.username` or `sub` claim for service principals |
| GOV-CLI-01 | Admin can DEPRECATE or REVOKE a job definition; REVOKED jobs are never dispatched to nodes | PATCH /api/jobs/definitions/{id} status update with admin gate for REVOKED; `execute_scheduled_job()` status check + AuditLog |
</phase_requirements>

---

## Summary

Phase 17 is a pure backend phase — no frontend changes. It adds three independent but related capabilities: (1) an RFC 8628 OAuth Device Authorization Grant flow implemented natively in FastAPI with in-memory state, (2) a `status` lifecycle field on `ScheduledJob` (DRAFT/ACTIVE/DEPRECATED/REVOKED) plus a `pushed_by` attribution field, and (3) a `POST /api/jobs/push` upsert endpoint that applies dual JWT + Ed25519 verification before writing to the database.

All new code builds entirely on existing patterns. The device flow uses `create_access_token()` from `auth.py` unchanged. The push endpoint is gated with the existing `require_permission("jobs:write")` factory and calls `SignatureService.verify_payload_signature()` directly — the same call already used by `scheduler_service.create_job_definition()`. The status field requires one migration file (`migration_v27.sql`) to ADD COLUMN to `scheduled_jobs` and backfill existing rows to `ACTIVE`.

The most delicate integration point is `execute_scheduled_job()` in `scheduler_service.py`: it currently checks `s_job.is_active` but not `status`. This check must be extended to gate on `status NOT IN (DRAFT, REVOKED, DEPRECATED)`, and DEPRECATED skips must write an AuditLog entry before returning (following the existing `cron_skip` pattern already in the function).

**Primary recommendation:** Implement in four logical groups: (1) DB migration + model changes, (2) push endpoint + status transition in PATCH, (3) scheduler dispatch hardening, (4) device flow endpoints.

---

## Standard Stack

### Core (all already in requirements.txt)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-jose` | current | JWT encode/decode | Already used in `auth.py` via `create_access_token()` |
| `cryptography` | current | Ed25519 verification | Already used in `signature_service.py` |
| `apscheduler` | current | Cron-based job dispatch | Already managing `ScheduledJob` lifecycle |
| `fastapi` | current | Route handlers + HTMLResponse | Already the web framework; `HTMLResponse` just needs importing |
| `sqlalchemy[asyncio]` | current | ORM + async session | All DB models use this |

### No New Dependencies
This phase adds zero new packages. All required functionality (JWT, Ed25519, HTML response, in-memory dict, APScheduler) is already present in the codebase.

**Installation:** None required.

---

## Architecture Patterns

### In-Memory Device Code Store

```python
# Module-level in main.py — consistent with codebase style
import secrets
import string

_device_codes: dict[str, dict] = {}
# Structure: device_code -> {user_code, expiry, status, approved_by}
# status values: "pending" | "approved" | "denied"
```

Cleanup strategy: lazy expiry on next access. On `POST /auth/device/token`, check `expiry < datetime.utcnow()` first and return `expired_token`. Separately, a lightweight cleanup sweep can run inside `POST /auth/device` to evict entries older than 10 minutes (2x TTL). This avoids a background task (which would need a separate scheduler entry) while keeping memory bounded.

### User Code Generation

The RFC 8628 guidance (Section 6.1) specifies using characters that are easy to read and type. The locked decision uses XXXX-XXXX uppercase alphanumeric, excluding `0`, `O`, `1`, `I`, `L`.

```python
# Source: RFC 8628 Section 6.1 + CONTEXT.md decision
_USER_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # excludes 0,O,1,I,L

def _generate_user_code() -> str:
    part1 = "".join(secrets.choice(_USER_CODE_ALPHABET) for _ in range(4))
    part2 = "".join(secrets.choice(_USER_CODE_ALPHABET) for _ in range(4))
    return f"{part1}-{part2}"

def _generate_device_code() -> str:
    return secrets.token_urlsafe(32)
```

Use `secrets` module (not `random`) — device codes are security tokens.

### RFC 8628 Endpoint Shape

**POST /auth/device — Device Authorization Request**
```
Request: { "client_id": "mop-cli" }   (or empty body — client_id optional for MoP-native)
Response 200:
{
  "device_code": "<opaque string>",
  "user_code": "JTKB-MXRQ",
  "verification_uri": "https://mop.example.com/auth/device/approve",
  "verification_uri_complete": "https://mop.example.com/auth/device/approve?user_code=JTKB-MXRQ",
  "expires_in": 300,
  "interval": 5
}
```

**POST /auth/device/token — Device Access Token Request**
```
Request: { "device_code": "<opaque>", "grant_type": "urn:ietf:params:oauth:grant-type:device_code" }
Response 200 (approved):  { "access_token": "...", "token_type": "bearer", "role": "operator" }
Response 400 (pending):   { "error": "authorization_pending" }
Response 400 (denied):    { "error": "access_denied" }
Response 400 (expired):   { "error": "expired_token" }
Response 400 (too fast):  { "error": "slow_down" }
```

**GET /auth/device/approve — Browser Approval Page**
- Requires session JWT in Authorization header OR cookie
- The dashboard uses JWT in localStorage — the approval page must accept the token as a query parameter `?token=<jwt>` OR read it from a cookie set by the browser session
- Simplest approach (given dashboard uses Bearer tokens): Accept `?token=<jwt>` query param for the GET, or have the Approve/Deny form POST include a hidden token field

**POST /auth/device/approve and POST /auth/device/deny — Form Submit**
- Accept form data: `user_code`, `token` (JWT)
- Validate JWT to get approving user identity
- Update `_device_codes[device_code]["status"]` and `"approved_by"`

### Approval Page — Token Handling

Since the dashboard stores JWT in `localStorage` (not a cookie), the approval page cannot rely on a cookie. The `verification_uri_complete` URL includes `?user_code=XXXX`. The page needs to:

1. Render with `?user_code=XXXX` pre-filled
2. Require the operator to have their JWT — use a small JavaScript snippet in the inline HTML to read `localStorage.getItem('access_token')` and inject it into the form as a hidden field before submit

This is the most pragmatic approach for a minimal inline HTML page without a separate React build.

```html
<!-- Inline JS pattern for approval page -->
<script>
  document.addEventListener('DOMContentLoaded', function() {
    var token = localStorage.getItem('access_token') || '';
    document.getElementById('token-field').value = token;
    if (!token) {
      window.location.href = '/login?next=' + encodeURIComponent(window.location.href);
    }
  });
</script>
```

### DB Schema Changes

**migration_v27.sql** (next after v26):
```sql
-- migration_v27.sql: Job lifecycle status + push attribution
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'ACTIVE';
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS pushed_by VARCHAR NULL;

-- Backfill: existing jobs are live (dashboard-created), not drafts
UPDATE scheduled_jobs SET status = 'ACTIVE' WHERE status IS NULL;

-- Optional: index for dispatch query performance
CREATE INDEX IF NOT EXISTS ix_scheduled_jobs_status ON scheduled_jobs(status);
```

New jobs created via the **dashboard** (`create_job_definition`) keep their current flow — they should default to `ACTIVE` status since the scheduler was previously activated immediately. New jobs pushed via `POST /api/jobs/push` default to `DRAFT`.

### JobDefinitionResponse Additions

Add two fields to the existing Pydantic model:
```python
class JobDefinitionResponse(BaseModel):
    # ... existing fields ...
    status: str = "ACTIVE"          # DRAFT / ACTIVE / DEPRECATED / REVOKED
    pushed_by: Optional[str] = None  # username or "sp:name"
```

### JobDefinitionUpdate — Status Transitions

Extend the existing `JobDefinitionUpdate` model:
```python
class JobDefinitionUpdate(BaseModel):
    # ... existing fields ...
    status: Optional[str] = None  # ACTIVE / DEPRECATED / REVOKED (DRAFT transitions handled separately)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid = {"DRAFT", "ACTIVE", "DEPRECATED", "REVOKED"}
        if v is not None and v not in valid:
            raise ValueError(f"status must be one of {sorted(valid)}")
        return v
```

The **PATCH /api/jobs/definitions/{id}** route must add an admin-only gate for `REVOKED` transitions:
```python
if update_req.status == "REVOKED" and current_user.role != "admin":
    raise HTTPException(403, "Only admin can REVOKE a job definition")
```

### Push Endpoint — New Model

```python
class JobPushRequest(BaseModel):
    name: Optional[str] = None   # for create (name-based upsert)
    id: Optional[str] = None     # for update (id-based upsert)
    script_content: str
    signature: str               # Base64 Ed25519 signature
    signature_id: str            # UUID of registered public key

    @model_validator(mode='after')
    def require_name_or_id(self):
        if not self.name and not self.id:
            raise ValueError("Either 'name' or 'id' is required")
        return self
```

### Scheduler Dispatch Hardening

The key change in `execute_scheduled_job()`:

```python
# Current code (line 109):
if not s_job or not s_job.is_active:
    logger.warning(f"⚠️ Job {scheduled_job_id} not found or inactive.")
    return

# New code — status check after is_active check:
if not s_job or not s_job.is_active:
    logger.warning(f"⚠️ Job {scheduled_job_id} not found or inactive.")
    return

SKIP_STATUSES = {"DRAFT", "REVOKED", "DEPRECATED"}
if s_job.status in SKIP_STATUSES:
    logger.warning(f"Skipping cron fire for '{s_job.name}' — status={s_job.status}")
    session.add(AuditLog(
        username="scheduler",
        action=f"job:{s_job.status.lower()}_skip",
        resource_id=s_job.id,
        detail=json.dumps({"status": s_job.status}),
    ))
    await session.commit()
    return
```

Note: `sync_scheduler()` loads only `is_active=True` jobs into APScheduler. The status check inside `execute_scheduled_job()` is a runtime guard for jobs that get REVOKED/DEPRECATED after the last sync.

### Anti-Patterns to Avoid

- **Using `random` for device codes**: Must use `secrets.token_urlsafe()` — these are security tokens
- **Blocking `sync_scheduler()` on status**: Do NOT filter by status in `sync_scheduler()` — APScheduler only loads active jobs, and status can change between syncs. The runtime check in `execute_scheduled_job()` is the correct gate.
- **Storing device codes in the DB**: In-memory is correct — codes are short-lived and ephemeral. Persisting them adds unnecessary DB load and complicates cleanup.
- **Returning 200 on `slow_down`**: RFC 8628 mandates 400 for all error responses at the token endpoint.
- **Changing status on push update**: The push endpoint MUST NOT change status when updating an existing job — status is managed separately via PATCH.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT issuance for device flow | Custom token builder | `create_access_token()` in `auth.py` | Already handles expiry, encoding, SECRET_KEY — identical claims structure |
| Ed25519 verification in push endpoint | Custom verify logic | `SignatureService.verify_payload_signature()` | Already handles base64 decode, PEM load, exception path |
| User code collision detection | UUID/hash approach | Simple set membership check on `_device_codes` values | Codes are 8 chars from 32-char alphabet — collision probability negligible in 5-minute window |
| Polling rate limiting | Redis / token bucket | Module-level dict tracking `last_poll_time` per device_code | Low traffic; simple `datetime` comparison sufficient |
| HTML template rendering | Jinja2/templates | Inline f-string HTML in route handler | No build step, no static files — consistent with locked decision |

---

## Common Pitfalls

### Pitfall 1: HTMLResponse Not Imported
**What goes wrong:** `HTMLResponse` is not in `fastapi.responses` in the current import line (`from fastapi.responses import Response, StreamingResponse`). Forgetting to add it causes `NameError` at route registration.
**How to avoid:** Add `HTMLResponse` to the existing import: `from fastapi.responses import Response, StreamingResponse, HTMLResponse`

### Pitfall 2: Device Code Lookup by User Code (Not Device Code)
**What goes wrong:** The approval page receives `user_code` (the human-readable code), not `device_code` (the opaque token). The in-memory store is keyed by `device_code`. You need a reverse lookup.
**How to avoid:** On approval/denial form submit, iterate `_device_codes.items()` to find the entry matching `user_code`. Or maintain a secondary index `_user_code_index: dict[str, str]` mapping `user_code -> device_code` for O(1) lookup.

### Pitfall 3: audit() Called with await
**What goes wrong:** `audit()` is a sync function (`def audit(...)` at line 760 in main.py). The codebase pattern is: call `audit()` synchronously, then `await db.commit()`. Accidentally calling `await audit(...)` raises `TypeError`.
**How to avoid:** `audit(db, current_user, "action", resource_id, detail_dict)` — no await. Then `await db.commit()`.

### Pitfall 4: REVOKED Check Missing in push endpoint
**What goes wrong:** If the push endpoint does an upsert by `id` without checking current status, it can update a REVOKED job, bypassing the immutability constraint.
**How to avoid:** After fetching the job by `id`, check `if job.status == "REVOKED": raise HTTPException(409, ...)` before any modifications.

### Pitfall 5: Backfill Uses DRAFT Instead of ACTIVE
**What goes wrong:** If migration backfills existing rows to `DRAFT`, all currently live scheduled jobs stop running at next dispatch (scheduler skips DRAFT).
**How to avoid:** `UPDATE scheduled_jobs SET status = 'ACTIVE' WHERE status IS NULL;` — existing dashboard-created jobs are already live and should stay ACTIVE.

### Pitfall 6: Token Expiry Race in Device Flow
**What goes wrong:** Device code expires between the poll (pending) and the browser approval (approved), leading to inconsistent state.
**How to avoid:** Check expiry at poll time and return `expired_token`. On approval, also check expiry and return an error screen. The TTL is enforced on both paths independently.

### Pitfall 7: pushed_by Identity for Service Principals
**What goes wrong:** Service principal JWTs have `sub = "sp:<name>"` (e.g., `"sp:ci-bot"`). If `pushed_by` is set to `current_user.username` it will work for `User` objects but `_SPUserProxy` (used for SP auth) may have a different `.username` attribute.
**How to avoid:** Extract `pushed_by` from the raw JWT `sub` claim if available, or verify that `_SPUserProxy.username` returns `"sp:<name>"` — check `_authenticate_sp_jwt()` in main.py to confirm the username value set on the proxy.

---

## Code Examples

### Device Authorization Response (POST /auth/device)
```python
# Source: RFC 8628 Section 3.2 + CONTEXT.md decisions
from fastapi.responses import HTMLResponse
import secrets, os
from datetime import datetime, timedelta

_device_codes: dict[str, dict] = {}
_user_code_index: dict[str, str] = {}  # user_code -> device_code
_USER_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_DEVICE_TTL_SECONDS = 300
_POLL_INTERVAL_SECONDS = 5

def _generate_user_code() -> str:
    p1 = "".join(secrets.choice(_USER_CODE_ALPHABET) for _ in range(4))
    p2 = "".join(secrets.choice(_USER_CODE_ALPHABET) for _ in range(4))
    return f"{p1}-{p2}"

@app.post("/auth/device")
async def device_authorization():
    # Lazy cleanup of expired codes
    now = datetime.utcnow()
    expired_keys = [k for k, v in _device_codes.items() if v["expiry"] < now]
    for k in expired_keys:
        uc = _device_codes.pop(k, {}).get("user_code")
        if uc:
            _user_code_index.pop(uc, None)

    device_code = secrets.token_urlsafe(32)
    user_code = _generate_user_code()
    expiry = now + timedelta(seconds=_DEVICE_TTL_SECONDS)

    _device_codes[device_code] = {
        "user_code": user_code,
        "expiry": expiry,
        "status": "pending",
        "approved_by": None,
    }
    _user_code_index[user_code] = device_code

    agent_url = os.getenv("AGENT_URL", "https://localhost:8001")
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": f"{agent_url}/auth/device/approve",
        "verification_uri_complete": f"{agent_url}/auth/device/approve?user_code={user_code}",
        "expires_in": _DEVICE_TTL_SECONDS,
        "interval": _POLL_INTERVAL_SECONDS,
    }
```

### Token Exchange (POST /auth/device/token)
```python
# Source: RFC 8628 Section 3.4 + CONTEXT.md decisions
from .auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

@app.post("/auth/device/token")
async def device_token_exchange(req: dict, db: AsyncSession = Depends(get_db)):
    device_code = req.get("device_code")
    entry = _device_codes.get(device_code)

    if not entry:
        raise HTTPException(400, detail={"error": "expired_token"})
    if entry["expiry"] < datetime.utcnow():
        _device_codes.pop(device_code, None)
        _user_code_index.pop(entry["user_code"], None)
        raise HTTPException(400, detail={"error": "expired_token"})
    if entry["status"] == "denied":
        raise HTTPException(400, detail={"error": "access_denied"})
    if entry["status"] == "pending":
        raise HTTPException(400, detail={"error": "authorization_pending"})

    # status == "approved"
    username = entry["approved_by"]
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, detail={"error": "access_denied"})

    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tv": user.token_version, "type": "device_flow"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # Clean up consumed code
    _device_codes.pop(device_code)
    _user_code_index.pop(entry["user_code"], None)

    audit(db, user, "device_flow:token_issued", detail={"username": user.username})
    await db.commit()
    return {"access_token": token, "token_type": "bearer", "role": user.role}
```

### Push Endpoint (POST /api/jobs/push)
```python
# Source: CONTEXT.md push endpoint decisions + existing scheduler_service patterns
@app.post("/api/jobs/push", response_model=JobDefinitionResponse)
async def push_job_definition(
    req: JobPushRequest,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    # 1. Validate signature BEFORE DB write
    sig_result = await db.execute(select(Signature).where(Signature.id == req.signature_id))
    sig = sig_result.scalar_one_or_none()
    if not sig:
        raise HTTPException(404, "Signature ID not found")
    try:
        SignatureService.verify_payload_signature(sig.public_key, req.signature, req.script_content)
    except Exception as e:
        raise HTTPException(422, f"Invalid Ed25519 signature: {e}")

    # 2. Determine pushed_by identity
    pushed_by = current_user.username  # "username" or "sp:name" for SPs

    # 3. Upsert logic
    if req.id:
        # Update existing job by ID
        result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == req.id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(404, "Job definition not found")
        if job.status == "REVOKED":
            raise HTTPException(409, detail={"error": "job_revoked", "id": job.id,
                                             "message": "Job is REVOKED. Un-REVOKE to DEPRECATED before re-pushing."})
        job.script_content = req.script_content
        job.signature_id = req.signature_id
        job.signature_payload = req.signature
        job.pushed_by = pushed_by
        job.updated_at = datetime.utcnow()
    else:
        # Create new job by name
        existing = await db.execute(select(ScheduledJob).where(ScheduledJob.name == req.name))
        if existing.scalar_one_or_none():
            existing_job = existing.scalar_one_or_none()
            raise HTTPException(409, detail={"error": "name_conflict", "id": existing_job.id})
        job = ScheduledJob(
            id=uuid.uuid4().hex,
            name=req.name,
            script_content=req.script_content,
            signature_id=req.signature_id,
            signature_payload=req.signature,
            status="DRAFT",
            pushed_by=pushed_by,
            created_by=pushed_by,
        )
        db.add(job)

    audit(db, current_user, "job:pushed", job.id if req.id else None,
          {"name": req.name or job.name, "pushed_by": pushed_by})
    await db.commit()
    await db.refresh(job)
    return JobDefinitionResponse.model_validate(job)
```

### Scheduler Dispatch Status Guard
```python
# In execute_scheduled_job() — add after the existing is_active check
SKIP_STATUSES = {"DRAFT", "REVOKED", "DEPRECATED"}
if hasattr(s_job, 'status') and s_job.status in SKIP_STATUSES:
    logger.warning(f"Skipping cron fire for '{s_job.name}' — status={s_job.status}")
    session.add(AuditLog(
        username="scheduler",
        action=f"job:{s_job.status.lower()}_skip",
        resource_id=s_job.id,
        detail=json.dumps({"status": s_job.status, "name": s_job.name}),
    ))
    await session.commit()
    return
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Username+password only for CLI auth | OAuth Device Flow (RFC 8628) for interactive CLI | This phase | CLI can authenticate without embedding credentials |
| ScheduledJob has no lifecycle status | DRAFT/ACTIVE/DEPRECATED/REVOKED | This phase | Push-based staging workflow enabled |
| All scheduled jobs dispatch unconditionally (beyond is_active) | Dispatch blocked for DRAFT/REVOKED/DEPRECATED | This phase | Job governance enforced at scheduler level |

---

## Open Questions

1. **_SPUserProxy.username attribute for pushed_by**
   - What we know: `_authenticate_sp_jwt()` returns a proxy object, not a real `User`. The `sub` claim is `"sp:<name>"`.
   - What's unclear: Whether `.username` on the proxy equals `"sp:<name>"` or just `"<name>"`.
   - Recommendation: Read `_authenticate_sp_jwt()` in `main.py` before implementing push endpoint to confirm. If `.username` is just `"<name>"`, prefix with `"sp:"` explicitly.

2. **409 conflict response shape for name collision**
   - What we know: CONTEXT.md says "returns 409 if name already exists, with the conflicting job's ID in the error"
   - What's unclear: Whether the existing ID is accessible in the same query (the `scalar_one_or_none()` call is consumed before the 409 path).
   - Recommendation: Fetch the existing job first, then check — don't rely on a single query.

3. **Approval page token injection via localStorage**
   - What we know: Dashboard uses `localStorage.getItem('access_token')`.
   - What's unclear: Whether the approval page will always be opened in the same browser session that has the JWT.
   - Recommendation: Include the JS snippet to read localStorage, but also show a clear message if no token is found rather than silently failing.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none — run from `puppeteer/` directory |
| Quick run command | `cd puppeteer && pytest tests/test_device_flow.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-CLI-01 | POST /auth/device returns device_code, user_code, verification_uri, expires_in | unit | `pytest tests/test_device_flow.py::test_device_authorization_response -x` | Wave 0 |
| AUTH-CLI-01 | User code format XXXX-XXXX excludes confusable chars | unit | `pytest tests/test_device_flow.py::test_user_code_format -x` | Wave 0 |
| AUTH-CLI-02 | POST /auth/device/token returns authorization_pending while waiting | unit | `pytest tests/test_device_flow.py::test_token_exchange_pending -x` | Wave 0 |
| AUTH-CLI-02 | POST /auth/device/token returns access_denied after denial | unit | `pytest tests/test_device_flow.py::test_token_exchange_denied -x` | Wave 0 |
| AUTH-CLI-02 | POST /auth/device/token returns expired_token after TTL | unit | `pytest tests/test_device_flow.py::test_token_exchange_expired -x` | Wave 0 |
| AUTH-CLI-02 | POST /auth/device/token returns JWT with type=device_flow on approval | unit | `pytest tests/test_device_flow.py::test_token_exchange_approved -x` | Wave 0 |
| STAGE-01 | ScheduledJob ORM model has status field | unit | `pytest tests/test_job_staging.py::test_scheduled_job_status_field -x` | Wave 0 |
| STAGE-02 | POST /api/jobs/push creates DRAFT job for new name | unit | `pytest tests/test_job_staging.py::test_push_creates_draft -x` | Wave 0 |
| STAGE-02 | POST /api/jobs/push returns 409 for duplicate name | unit | `pytest tests/test_job_staging.py::test_push_duplicate_name_conflict -x` | Wave 0 |
| STAGE-02 | POST /api/jobs/push returns 409 for REVOKED job ID | unit | `pytest tests/test_job_staging.py::test_push_revoked_job_blocked -x` | Wave 0 |
| STAGE-03 | POST /api/jobs/push returns 401 for missing JWT | unit | `pytest tests/test_job_staging.py::test_push_requires_auth -x` | Wave 0 |
| STAGE-03 | POST /api/jobs/push returns 422 for bad signature | unit | `pytest tests/test_job_staging.py::test_push_invalid_signature -x` | Wave 0 |
| STAGE-04 | pushed_by records username on successful push | unit | `pytest tests/test_job_staging.py::test_push_records_pushed_by -x` | Wave 0 |
| GOV-CLI-01 | execute_scheduled_job skips REVOKED job and writes AuditLog | unit | `pytest tests/test_job_staging.py::test_scheduler_skips_revoked -x` | Wave 0 |
| GOV-CLI-01 | execute_scheduled_job skips DEPRECATED job and writes AuditLog | unit | `pytest tests/test_job_staging.py::test_scheduler_skips_deprecated -x` | Wave 0 |
| GOV-CLI-01 | execute_scheduled_job skips DRAFT job | unit | `pytest tests/test_job_staging.py::test_scheduler_skips_draft -x` | Wave 0 |
| GOV-CLI-01 | Non-admin cannot set status to REVOKED (403) | unit | `pytest tests/test_job_staging.py::test_revoke_requires_admin -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_device_flow.py tests/test_job_staging.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_device_flow.py` — covers AUTH-CLI-01, AUTH-CLI-02
- [ ] `puppeteer/tests/test_job_staging.py` — covers STAGE-01..04, GOV-CLI-01

**Test approach note:** The existing test suite uses `unittest.mock.patch` and `MagicMock` for isolation (see `test_tools.py`, `test_compatibility_engine.py`). Device flow and push endpoint tests should follow the same pattern — mock `AsyncSessionLocal` or use the `inspect.getsource` stub pattern from Phase 11 tests for Wave 0.

---

## Sources

### Primary (HIGH confidence)
- Source code inspection: `puppeteer/agent_service/main.py`, `db.py`, `auth.py`, `services/scheduler_service.py`, `services/signature_service.py`, `models.py` — direct code reading, no inference
- `17-CONTEXT.md` — locked decisions from the discuss phase

### Secondary (MEDIUM confidence)
- RFC 8628 (OAuth 2.0 Device Authorization Grant) — well-established standard, all error codes and response shapes verified against spec text
- Existing migration pattern: `migration_v26.sql` — establishes `IF NOT EXISTS` pattern, index creation style, and backfill approach

### Tertiary (LOW confidence)
- None — all claims are grounded in direct code inspection or RFC text

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all verified by source inspection
- Architecture: HIGH — all patterns derived directly from existing codebase code
- RFC 8628 compliance: HIGH — error codes and response shapes are normative RFC text
- Pitfalls: HIGH — derived from direct code analysis (audit() sync pattern, HTMLResponse import gap, backfill risk)

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable codebase, no external dependencies to track)
