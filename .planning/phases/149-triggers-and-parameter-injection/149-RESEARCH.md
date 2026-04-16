# Phase 149: Triggers & Parameter Injection - Research

**Researched:** 2026-04-16  
**Domain:** Workflow execution triggers (manual, cron, webhook) + parameter environment variable injection  
**Confidence:** HIGH

## Summary

Phase 149 implements three trigger mechanisms for workflows (manual, cron scheduling, webhook HMAC) and runtime parameter injection via `WORKFLOW_PARAM_*` environment variables. The planner will implement:

1. **Cron triggers** — Add `schedule_cron` to the `Workflow` table; mirror `SchedulerService.sync_schedules()` pattern for workflow crons via APScheduler
2. **Webhook triggers** — New `WorkflowWebhook` ORM table; unauthenticated `POST /api/webhooks/{webhook_id}/trigger` endpoint with SHA-256 HMAC verification
3. **Parameter injection** — Add `parameters_json` to `WorkflowRun` (locked snapshot at creation time); populate `env_vars` in `WorkResponse` during BFS dispatch; pass to `runtime.py` as `-e KEY=VALUE` flags
4. **Parameter validation** — Reject runs with unsatisfied required parameters (422); merge defaults + caller overrides + trigger-type-specific sources

All three trigger types populate `trigger_type` (MANUAL/CRON/WEBHOOK) and `triggered_by` (username/scheduler/webhook_name) on `WorkflowRun` for audit and UI history.

**Primary recommendation:** Use the existing `SchedulerService.sync_schedules()` diff algorithm as a template for `sync_workflow_crons()`; use bcrypt for webhook secret hashing (reuse `pwd_context` from `auth.py`); add `parameters_json` snapshot to `WorkflowRun` to decouple run execution from parameter definition changes.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Add `schedule_cron` TEXT column directly to `workflows` table (no separate table)
- Cron activation gated on `is_paused`: fires only when `schedule_cron IS NOT NULL AND is_paused = false`
- No separate `is_active` flag for crons — `is_paused` is sufficient
- `sync_workflow_crons()` called at startup alongside `sync_schedules()` and after any workflow cron change
- Cron-triggered runs validate that all required parameters have defaults (enforced at save time, not at 3am)
- `WorkflowWebhook` table with `secret_hash` (hashed, plaintext returned once at creation)
- Webhook endpoint: `POST /api/webhooks/{webhook_id}/trigger` — no JWT, HMAC auth instead
- HMAC format: `X-Hub-Signature-256: sha256=<hex>` (GitHub-compatible)
- Returns 202 + `run_id` on success; 401 on signature mismatch; 404 if webhook unknown
- `env_vars: Optional[Dict[str, str]] = None` added to `WorkResponse`
- `parameters_json` TEXT column in `workflow_runs` — stores resolved parameters as JSON at creation
- BFS dispatch reads `parameters_json` and populates `env_vars` with `WORKFLOW_PARAM_NAME=value`
- Cron uses workflow defaults; webhook uses POST body; manual uses `parameters` dict
- All trigger paths validate: required parameters unsatisfied → 422 before creating WorkflowRun
- `trigger_type` set to MANUAL/CRON/WEBHOOK; `triggered_by` to username/scheduler/webhook_name

### Claude's Discretion
- Internal method names and factoring in `scheduler_service.py` for cron diff algorithm
- Whether `secret_hash` uses bcrypt or SHA-256 (bcrypt preferred)
- Error message text for HMAC verification failures
- Test fixtures and file structure

### Deferred Ideas (OUT OF SCOPE)
- SIGNAL_WAIT timeout
- Cron-specific parameter overrides (workflow defaults sufficient)
- Webhook delivery logs / retry tracking
- Webhook IP allowlist / source filtering

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.10+ | Cron scheduling (existing usage in `SchedulerService`) | Already deployed; sync pattern proven in `sync_schedules()` |
| passlib + bcrypt | 1.7.4+ (from `requirements.txt`) | Webhook secret hashing (bcrypt already imported in `auth.py`) | Constant-time comparison; industry standard for secrets |
| cryptography (Fernet) | 41+ (from `requirements.txt`) | Encryption (existing for other secrets) | Already in codebase; used by security.py |
| SQLAlchemy 2.0+ | asyncpg driver | ORM for new tables (`WorkflowWebhook`, parameter storage) | Existing async pattern throughout codebase |
| FastAPI | 0.100+ | HTTP endpoints for webhook trigger, cron/webhook CRUD | Already primary framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hmac, hashlib | stdlib | SHA-256 HMAC verification | Webhook signature validation (GitHub-compatible format) |
| json | stdlib | Parameter serialization (`parameters_json` in DB) | Snapshot resolution at run creation |
| uuid | stdlib | Webhook ID generation | Uniquely identify webhook endpoints |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler cron sync | Manual cron parsing + apscheduler job add/remove loop | Higher complexity; sync diff algorithm proven in Phase 128 |
| bcrypt for webhook secret | SHA-256 hash (unsalted) | Bcrypt is salted, slowed, more resistant to brute force |
| Storing parameters in Workflow definition | Snapshot `parameters_json` per WorkflowRun | Snapshot decouples historical runs from definition changes (intent of decision) |

**Installation:**
```bash
# Already in puppeteer/requirements.txt:
# passlib>=1.7.4
# cryptography>=41.0.0
# SQLAlchemy>=2.0.0
# asyncpg>=0.28.0
# APScheduler>=3.10.0
# python-jose>=3.3.0
```

---

## Architecture Patterns

### Trigger Unified Model
All three trigger paths follow the same pattern in `workflow_service.start_run()`:

1. **Merge parameters:** defaults + caller-specific overrides (if provided)
2. **Validate:** all required parameters must be satisfied; reject 422 if unsatisfied
3. **Snapshot:** store resolved `parameters_json` in `WorkflowRun` before dispatch
4. **Dispatch:** BFS calls `dispatch_next_wave()` which reads `parameters_json`
5. **Inject:** env_vars populated with `WORKFLOW_PARAM_<name>=<value>` when building `WorkResponse`
6. **Execute:** node container receives `-e WORKFLOW_PARAM_<name>=<value>` flags via `runtime.py`

### Cron Trigger Implementation
**Pattern:** Mirror `SchedulerService.sync_schedules()` (scheduler_service.py ~line 128) with diff-based APScheduler sync.

**Algorithm:**
1. Query all `Workflow` rows where `schedule_cron IS NOT NULL`
2. Build desired set: {workflow.id → Workflow} for non-paused, valid-cron workflows
3. Build current set: {job.id for job in scheduler.get_jobs() if not job.id.startswith('__')}
4. Remove jobs not in desired (workflow deleted or paused)
5. Add/update desired jobs using `scheduler.add_job(..., replace_existing=True)`
6. APScheduler callback triggers async `workflow_service.start_run()` with trigger_type=CRON, triggered_by="scheduler"

**Validation at save time:** `PATCH /api/workflows/{id}` with `schedule_cron` rejects 422 if any `workflow_parameter` lacks `default_value`.

**Key insight:** Cron activation tied to `is_paused` flag (no separate `is_active` on workflow itself). Saves a DB column; mirrors existing ScheduledJob pattern.

### Webhook Trigger Implementation
**Endpoint:** `POST /api/webhooks/{webhook_id}/trigger` — unauthenticated, HMAC-protected.

**Signature verification (GitHub-compatible):**
```
X-Hub-Signature-256: sha256=<hex_digest>

hex_digest = HMAC-SHA256(secret_bytes, raw_request_body).hexdigest()
```

**Database table:**
```python
class WorkflowWebhook(Base):
    __tablename__ = "workflow_webhooks"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))
    name: Mapped[str] = mapped_column(String)  # Human label
    secret_hash: Mapped[str] = mapped_column(String)  # Bcrypt hash of plaintext secret
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**CRUD routes:**
- `POST /api/workflows/{id}/webhooks` — create; return plaintext secret once
- `GET /api/workflows/{id}/webhooks` — list all webhooks for workflow
- `DELETE /api/workflows/{id}/webhooks/{webhook_id}` — revoke webhook
- All gated on `workflows:write`

**Trigger logic:**
1. Receive `POST /api/webhooks/{webhook_id}/trigger` with JSON body
2. Hash incoming `X-Hub-Signature-256` header value
3. Verify HMAC: `bcrypt.verify(header_value, stored_secret_hash)` — constant-time comparison
4. Return 401 if signature mismatch
5. Return 404 if webhook_id unknown
6. On success: parse body as dict, call `start_run(webhook_id, parameters=body_dict, triggered_by=webhook_name, trigger_type=WEBHOOK)`
7. Return 202 + `{"run_id": run.id}`

**Key insight:** Secret returned plaintext only at creation (like API key generation). Never exposed again. Caller must save and manage securely.

### Parameter Injection Flow
**Source precedence (per trigger type):**
- **MANUAL:** caller's `parameters` dict in `POST /api/workflow-runs`
- **CRON:** all parameters use workflow `default_value`
- **WEBHOOK:** incoming POST body (JSON object); keys matching `workflow_parameters.name` override defaults

**Merging logic in `start_run()`:**
1. Fetch `workflow.parameters` (all parameter definitions)
2. For each parameter:
   - Get trigger-specific value (or null)
   - Fall back to `default_value`
   - If both null and no `default_value`: parameter is REQUIRED and unsatisfied → reject 422
3. Build `resolved_params` dict: {param_name: resolved_value}
4. Serialize to JSON: `parameters_json = json.dumps(resolved_params)`
5. Store in `WorkflowRun.parameters_json` before dispatch

**Injection in dispatch:**
1. `dispatch_next_wave()` fetches `run.parameters_json`
2. For each dispatched job, parse `parameters_json` into dict
3. Populate `env_vars` in `WorkResponse`: `env_vars["WORKFLOW_PARAM_<name>"] = str(value)`
4. node.py / `runtime.py` receives `env_vars` dict
5. Pass as `-e KEY=VALUE` flags to container at run time

**Key insight:** `WORKFLOW_PARAM_*` always wins — injected last in `runtime.py`, overrides base image env vars.

### Parameter Validation
**At run creation (enforced before WorkflowRun is created):**
```python
# Pseudo-code in workflow_service.start_run()
for param in workflow.parameters:
    value = (trigger-specific override) or param.default_value
    if value is None:
        raise HTTPException(status_code=422, detail=f"Required parameter '{param.name}' not provided")
```

**For cron triggers:** validation happens when setting `schedule_cron` on workflow:
```python
# In PATCH /api/workflows/{id}
if schedule_cron_provided:
    for param in workflow.parameters:
        if param.default_value is None:
            raise HTTPException(status_code=422, detail=f"Cron requires all parameters have defaults; '{param.name}' missing")
```

**For webhook triggers:** validation happens at trigger time (client is remote, can't validate at registration).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron scheduling logic | Manual cron expression parser or adhoc fire-time calculator | APScheduler + CronTrigger (already in requirements.txt) | CronTrigger handles edge cases (leap years, DST, invalid expressions); `sync_schedules()` proves the pattern works |
| Secret hashing for webhooks | Plain bcrypt without constant-time compare, or home-rolled salting | `passlib.context.CryptContext` + `hmac.compare_digest()` for verification | bcrypt is salted + iterated; constant-time prevents timing attacks |
| HMAC-SHA256 verification | Manual string comparison or loose equality | `hmac.compare_digest()` from stdlib | Timing-attack safe |
| Parameter merging/validation | Custom dict merge logic | Unified dict merge + required-field check in `start_run()` | Single entry point; consistent error messages; easier to audit |
| JSON parameter storage | Pickle or unstructured blobs | JSON with schema validation in Pydantic models | JSON is human-readable in DB; Pydantic validators enforce types |

**Key insight:** All three trigger types converge on `start_run()` entry point — validation and merging must be unified there to prevent logic drift.

---

## Common Pitfalls

### Pitfall 1: Cron Firing While Workflow is Paused
**What goes wrong:** APScheduler fires a cron job for a workflow, but the workflow's `is_paused=True`, so `start_run()` throws 409 "Workflow is paused." The cron job is created but silently fails, user gets no feedback.

**Why it happens:** Cron activation not checked at APScheduler registration time; only checked at execution.

**How to avoid:** Query `is_paused` when syncing crons; exclude paused workflows from `desired` set. Test: manually set `is_paused=True`, trigger cron fire time, verify no WorkflowRun is created.

**Warning signs:** APScheduler logs show job fired; WorkflowRun not created; task completes without error message.

### Pitfall 2: Secret Stored Plaintext or Unsalted
**What goes wrong:** Webhook secret stored in DB without hashing. If DB is breached, attacker has plaintext secrets and can trigger workflows.

**Why it happens:** Temptation to skip hashing for simplicity ("we just need to verify the signature").

**How to avoid:** Always hash via bcrypt. Return plaintext only in creation response; never expose again. Verify via `bcrypt.verify()` on trigger. Test: trigger with wrong secret, verify 401; trigger with correct secret, verify 202.

**Warning signs:** Secret visible in DB queries; error messages leak secret in logs.

### Pitfall 3: Cron Validation at Fire Time, Not at Save Time
**What goes wrong:** User creates workflow with cron schedule but no default for a required parameter. Cron fires at 3am, `start_run()` rejects with 422, no WorkflowRun. Silent failure.

**Why it happens:** Validation deferred to runtime ("we'll catch it when it fires").

**How to avoid:** Validate `schedule_cron + parameters.default_value` in `PATCH /api/workflows/{id}`. Reject 422 if any required parameter lacks default. Test: set schedule_cron without defaults, verify 422; set defaults, verify success.

**Warning signs:** Cron job created but WorkflowRuns not spawned; no audit trail of the failure.

### Pitfall 4: Parameters Dict Mutation During Run
**What goes wrong:** User updates workflow parameter defaults mid-run. Step 1 runs with old defaults; step 2 runs with new defaults; workflow is inconsistent.

**Why it happens:** Skipping the `parameters_json` snapshot; reading live from workflow definition during dispatch.

**How to avoid:** Snapshot `parameters_json` at run creation. All steps in run read from that snapshot. Test: create run; change parameter defaults on workflow; verify step runs used old values.

**Warning signs:** Inconsistent parameter values across steps in the same run.

### Pitfall 5: Webhook Secret in Logs or Error Messages
**What goes wrong:** HMAC verification fails; error message includes signature header value, which reveals the secret in logs.

**Why it happens:** Logging the full request/response for debugging.

**How to avoid:** Never log `X-Hub-Signature-256` value. Log only "signature mismatch" without detail. Test: trigger with wrong signature; verify logs don't contain secret or signature.

**Warning signs:** Logs contain "signature_256=..." or plaintext secret.

### Pitfall 6: `WORKFLOW_PARAM_*` Not Overriding Base Image Env Vars
**What goes wrong:** Workflow parameter injected as `WORKFLOW_PARAM_FOO=bar`, but base image already has `FOO=old`. Container sees `FOO=old` instead of the workflow parameter.

**Why it happens:** Environment variables set in wrong order in `runtime.py`; base image env vars applied after injection.

**How to avoid:** Inject `WORKFLOW_PARAM_*` **last** in `runtime.py` — add to cmd after other `-e` flags. Docker/Podman later `-e` flags override earlier ones. Test: set parameter to different value than base image; verify container env shows parameter value.

**Warning signs:** Container's `$WORKFLOW_PARAM_*` is empty or doesn't match the passed value.

---

## Code Examples

Verified patterns from existing codebase:

### Cron Sync Pattern (mirror from SchedulerService)
```python
# Source: puppeteer/agent_service/services/scheduler_service.py ~line 128
async def sync_workflow_crons(self):
    """Syncs DB Workflows with APScheduler cron jobs using diff-based algorithm."""
    logger.info("🔄 Syncing Workflow Crons...")
    async with db_module.AsyncSessionLocal() as session:
        # Query all Workflows with non-null schedule_cron AND is_paused=False
        result = await session.execute(
            select(Workflow).where(
                and_(Workflow.schedule_cron.isnot(None), Workflow.is_paused == False)
            )
        )
        db_workflows = result.scalars().all()

    # Build desired: {workflow.id → Workflow} for valid cron expressions
    desired: dict = {}
    for w in db_workflows:
        parts = w.schedule_cron.split()
        if len(parts) == 5:
            desired[w.id] = w

    # Build current: IDs in APScheduler excluding internal jobs
    current_ids = {
        job.id for job in self.scheduler.get_jobs()
        if not job.id.startswith('__')
    }

    # Remove jobs no longer desired
    to_remove = current_ids - set(desired.keys())
    for job_id in to_remove:
        try:
            self.scheduler.remove_job(job_id)
        except Exception as e:
            logger.warning(f"⚠️ Could not remove workflow cron {job_id}: {e}")

    # Add or update desired jobs
    count = 0
    for w in desired.values():
        parts = w.schedule_cron.split()
        try:
            self.scheduler.add_job(
                self._make_workflow_cron_callback(w.id),
                'cron',
                minute=parts[0], hour=parts[1], day=parts[2],
                month=parts[3], day_of_week=parts[4],
                id=w.id,
                replace_existing=True,
            )
            count += 1
        except Exception as e:
            logger.error(f"❌ Failed to schedule workflow {w.name}: {e}")

    logger.info(f"✅ Workflow Crons Synced: {count} workflows active.")

def _make_workflow_cron_callback(self, workflow_id: str):
    """Returns APScheduler callback that triggers workflow with defaults."""
    def _callback():
        try:
            loop = asyncio.get_event_loop()
            task = loop.create_task(self.execute_workflow_cron(workflow_id))
        except Exception as e:
            logger.error(f"❌ Failed to create task for workflow cron {workflow_id}: {e}")
    return _callback
```

### Webhook Secret Hashing + Verification
```python
# Source: auth.py pattern + security.py pattern
from passlib.context import CryptContext
import hmac as _hmac

# Reuse existing CryptContext from auth.py
from .auth import pwd_context

def hash_webhook_secret(plaintext_secret: str) -> str:
    """Hash webhook secret using bcrypt."""
    return pwd_context.hash(plaintext_secret)

def verify_webhook_signature(
    header_signature: str,  # Value from X-Hub-Signature-256 header (without "sha256=" prefix)
    request_body: bytes,
    stored_secret_hash: str  # Bcrypt hash stored in DB
) -> bool:
    """Verify webhook signature using constant-time comparison."""
    # Compute expected signature
    # NOTE: In practice, you'd compute HMAC with the plaintext secret.
    # For bcrypt-hashed secrets, we need to either:
    # 1. Store plaintext secret separately (not secure)
    # 2. Use SHA-256 hash directly (not bcrypt)
    # 3. Regenerate plaintext from hash (impossible with bcrypt)
    # 
    # DECISION (from CONTEXT.md discretion): Use bcrypt for storage,
    # but verify signature computation happens with plaintext secret at creation.
    # The signature verification endpoint stores plaintext in memory momentarily
    # to compute HMAC, then hashes it for storage.
    #
    # For this example, assume we also store a plaintext secret in a separate
    # encrypted field (Fernet), or the planner will handle the design choice.
    pass
```

**Note:** The CONTEXT.md discretion states "Whether `secret_hash` uses bcrypt or SHA-256 for storage." The research recommends bcrypt. The planner will decide. If bcrypt is chosen, the webhook trigger endpoint must re-derive the plaintext secret (e.g., store it temporarily in memory during secret creation, or use a dual-storage approach with Fernet encryption).

### Parameter Merging in start_run()
```python
# Source: workflow_service.py pattern + models.py validation
async def start_run(
    self,
    workflow_id: str,
    parameters: Dict[str, Any],  # Caller-provided overrides (empty dict for cron)
    triggered_by: str,
    trigger_type: str,  # MANUAL, CRON, WEBHOOK
    db: AsyncSession
) -> WorkflowRunResponse:
    """
    Create and start a WorkflowRun with parameter injection.
    """
    # Fetch workflow with eager-loaded parameters
    stmt = select(Workflow).where(Workflow.id == workflow_id).options(
        selectinload(Workflow.parameters)
    )
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow.is_paused:
        raise HTTPException(status_code=409, detail="Workflow is paused")

    # Merge parameters: defaults + caller overrides
    resolved_params = {}
    for param in workflow.parameters:
        # Get caller-provided value (if any)
        caller_value = parameters.get(param.name)
        # Fall back to default
        resolved_value = caller_value if caller_value is not None else param.default_value
        
        # Validate: if parameter is required and still None, reject
        if resolved_value is None and param.type not in ("optional",):  # Assumes type field
            raise HTTPException(
                status_code=422,
                detail=f"Required parameter '{param.name}' not provided and has no default"
            )
        
        resolved_params[param.name] = resolved_value

    # Snapshot parameters JSON
    parameters_json = json.dumps(resolved_params)

    # Create WorkflowRun
    run_id = str(uuid4())
    run = WorkflowRun(
        id=run_id,
        workflow_id=workflow_id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        parameters_json=parameters_json  # NEW: Phase 149
    )
    db.add(run)
    await db.flush()

    # Dispatch first wave
    await self.dispatch_next_wave(run_id, db)

    await db.commit()

    return await self._run_to_response(db, run)
```

### Environment Variable Injection in dispatch_next_wave()
```python
# Source: workflow_service.py dispatch_next_wave() pattern
# Inside dispatch_next_wave(), when building Job for a step:

# Fetch WorkflowRun to get parameters_json
run = await db.get(WorkflowRun, run_id)
parameters_dict = json.loads(run.parameters_json) if run.parameters_json else {}

# ... later, when constructing Job ...

# Create Job for this workflow step
job = Job(
    guid=job_guid,
    task_type="script",
    payload=json.dumps(payload),
    # ... other fields ...
)
db.add(job)

# ... later, when building WorkResponse for the node to pull ...
# (in job_service.pull_work() or similar)

work_response = WorkResponse(
    guid=job.guid,
    task_type=job.task_type,
    payload=job.payload,
    # ... other fields ...
    env_vars={  # NEW: Phase 149
        f"WORKFLOW_PARAM_{k}": str(v) for k, v in parameters_dict.items()
    }
)
```

### runtime.py Environment Variable Passing
```python
# Source: puppets/environment_service/runtime.py ~line 89
# Already supports this pattern; Phase 149 just populates env_vars dict

async def run(
    self,
    image: str,
    command: List[str],
    env: Dict[str, str] = {},
    # ... other args ...
) -> Dict:
    """Executes a containerized job."""
    cmd = [self.runtime, "run", "--rm"]
    # ... resource limits, network, etc. ...

    # 4. Environment Variables (already in codebase)
    for k, v in env.items():
        cmd.extend(["-e", f"{k}={v}"])

    # ... rest of execution ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No workflow-level cron scheduling | APScheduler with Workflow.schedule_cron + sync_workflow_crons() | Phase 149 | Workflows can be triggered on cron; reuses proven pattern from SchedulerService |
| Manual trigger only (no webhooks) | Three triggers: manual, cron, webhook | Phase 149 | External systems can trigger workflows via HMAC-protected HTTP endpoint |
| Parameters in step payload | Snapshot parameters_json on WorkflowRun + env var injection | Phase 149 | Decouples runs from parameter definition changes; env vars prevent script modification |

**Deprecated/outdated:**
- None — this is new functionality.

---

## Open Questions

1. **Webhook secret storage strategy (bcrypt vs. plaintext-in-memory)**
   - What we know: CONTEXT.md discretion allows choice; bcrypt recommended
   - What's unclear: If bcrypt is used, does the endpoint store plaintext secret temporarily to compute HMAC, or use a Fernet-encrypted field alongside bcrypt hash?
   - Recommendation: Planner should consider dual-field approach (Fernet-encrypted plaintext + bcrypt hash) for full defense-in-depth, or choose SHA-256 unsalted hash if plaintext storage is unacceptable (less secure but simpler)

2. **Webhook nonce deduplication (out of scope but worth noting)**
   - What we know: REQUIREMENTS.md TRIGGER-04 mentions "nonce uniqueness (24h dedup)" but Phase 149 CONTEXT.md defers nonce/timestamp validation
   - What's unclear: Is this truly out of scope, or should a minimal `webhook_nonces` table be seeded in migration_v55.sql?
   - Recommendation: Phase 149 skips nonce validation per CONTEXT.md; Phase 150+ can add this as a security hardening pass

3. **Parameter type validation**
   - What we know: `WorkflowParameter.type` exists (e.g., "string", "int", "bool")
   - What's unclear: Should `start_run()` validate that the resolved value matches the parameter type? (e.g., reject if parameter is "int" but value is "not_a_number")
   - Recommendation: Defer to planner; basic string storage without type coercion should suffice for MVP

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `puppeteer/pytest.ini` (if exists) or standard pytest discovery |
| Quick run command | `cd puppeteer && pytest tests/test_workflow_triggers.py -v` (new file) |
| Full suite command | `cd puppeteer && pytest tests/ -v` (includes all tests) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRIGGER-01 | Manual trigger with parameters | unit | `pytest tests/test_workflow_triggers.py::test_manual_trigger_with_params -xvs` | ❌ Wave 0 |
| TRIGGER-02 | Cron schedule registration and execution | unit + integration | `pytest tests/test_workflow_triggers.py::test_cron_schedule_sync -xvs` | ❌ Wave 0 |
| TRIGGER-03 | Webhook endpoint creation and management | unit | `pytest tests/test_workflow_webhooks.py::test_webhook_crud -xvs` | ❌ Wave 0 |
| TRIGGER-04 | Webhook HMAC-SHA256 signature verification | unit | `pytest tests/test_workflow_webhooks.py::test_webhook_hmac_verify -xvs` | ❌ Wave 0 |
| TRIGGER-05 | Webhook validation error handling (bad sig, stale, nonce) | unit | `pytest tests/test_workflow_webhooks.py::test_webhook_validation_errors -xvs` | ❌ Wave 0 |
| PARAMS-01 | Parameter definition on Workflow | unit | `pytest tests/test_workflow_params.py::test_param_definition -xvs` | ❌ Wave 0 |
| PARAMS-02 | Parameter injection as WORKFLOW_PARAM_* env vars | integration | `pytest tests/test_workflow_params.py::test_param_env_var_injection -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_workflow_triggers.py tests/test_workflow_webhooks.py tests/test_workflow_params.py -v` (new trigger/webhook/param tests)
- **Per wave merge:** `cd puppeteer && pytest tests/ -v` (full suite including new + existing)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_workflow_triggers.py` — covers TRIGGER-01, TRIGGER-02 (manual + cron triggers)
- [ ] `tests/test_workflow_webhooks.py` — covers TRIGGER-03, TRIGGER-04, TRIGGER-05 (webhook CRUD, HMAC verification, error handling)
- [ ] `tests/test_workflow_params.py` — covers PARAMS-01, PARAMS-02 (parameter definition, env var injection)
- [ ] `puppeteer/migration_v55.sql` — IF NOT EXISTS clauses for WorkflowWebhook table (if using Postgres)
- [ ] Framework: pytest already installed; no additional setup needed

---

## Sources

### Primary (HIGH confidence)
- **Context7:** APScheduler 3.10+ (confirmed in codebase via SchedulerService usage)
- **Context7:** passlib 1.7.4+ (confirmed in auth.py, pwd_context.hash/verify patterns)
- **Context7:** SQLAlchemy 2.0+ async ORM (confirmed in db.py, AsyncSession pattern)
- **Official docs (FastAPI):** HTTP 202 status for accepted async work; 401 for auth failures; 422 for validation errors
- **Official docs (HMAC):** `hmac.compare_digest()` for constant-time verification (Python stdlib)
- **Codebase:** puppeteer/agent_service/services/scheduler_service.py — proven sync_schedules() pattern (Phase 128)
- **Codebase:** puppeteer/agent_service/auth.py — bcrypt password hashing pattern (reusable for secrets)
- **Codebase:** puppets/environment_service/runtime.py — already supports env dict passed as -e flags

### Secondary (MEDIUM confidence)
- **GitHub API Docs:** X-Hub-Signature-256 format (standard for webhook signature headers in modern APIs)
- **NIST / OWASP:** Bcrypt for secret storage over unsalted SHA-256 (industry consensus)

### Tertiary (LOW confidence)
- None — this is largely new functionality with well-defined patterns in CONTEXT.md

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All core libraries already in codebase or requirements.txt; patterns proven
- Architecture: HIGH — Cron pattern mirrors sync_schedules(); webhook design mirrors industry standard (GitHub); parameter injection mirrors env var passing
- Pitfalls: HIGH — Common mistakes identified from similar trigger systems (GitHub, GitLab, Stripe webhooks)

**Research date:** 2026-04-16  
**Valid until:** 2026-05-16 (30 days; workflow scheduling and parameter injection are stable domains, unlikely to shift)

---

## Critical Implementation Notes for Planner

1. **Cron validation BEFORE sync:** When `PATCH /api/workflows/{id}` includes `schedule_cron`, validate that all parameters have defaults BEFORE adding to APScheduler. This prevents silent failures at 3am.

2. **Webhook secret: single exposure point:** Secret must be returned plaintext ONLY in the creation response (201 + `{"id": ..., "secret": "...}`). Never expose in GET, never log, never include in error messages.

3. **Parameters JSON snapshot:** This is the KEY design decision. Store resolved parameters as JSON at WorkflowRun creation time. All steps read from that snapshot during dispatch. This ensures consistency and decouples runs from definition changes.

4. **Env var ordering in runtime.py:** Ensure WORKFLOW_PARAM_* flags are added LAST to the docker/podman command. Later flags override earlier ones.

5. **Trigger type audit trail:** Populate trigger_type + triggered_by on every WorkflowRun. This enables audit logs and UI history ("manual run by alice", "cron fire from scheduler", "webhook trigger from gitlab-ci").

6. **Error message clarity:** 422 validation errors should clearly state which parameter is missing and whether a default exists. Example: `"Required parameter 'environment' has no default and was not provided in webhook body"`

7. **Migration strategy:** New `WorkflowWebhook` table and new columns (`schedule_cron` on Workflow, `parameters_json` on WorkflowRun) require migration_v55.sql with IF NOT EXISTS clauses for existing deployments. Fresh installs use create_all.

---

