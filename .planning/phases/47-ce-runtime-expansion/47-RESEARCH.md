# Phase 47: CE Runtime Expansion - Research

**Researched:** 2026-03-22
**Domain:** Multi-runtime job execution (Python / Bash / PowerShell), unified task type API, server-side display_type, scheduled job runtime field
**Confidence:** HIGH

## Summary

Phase 47 extends the job execution model to support Bash and PowerShell alongside Python via a unified `script` task type with a required `runtime` field. The work spans five layers: the node image (`Containerfile.node`), the node agent (`node.py:execute_task`), the backend API (`models.py`, `job_service.py`, `main.py`), the scheduler (`scheduler_service.py`, `db.py:ScheduledJob`), and the frontend Jobs view (`Jobs.tsx`).

The codebase is clean and well-factored. The existing `python_script` branch in `execute_task` provides the exact template for the new `script` branch — the differences are: (a) the script is written to a temp file rather than piped via stdin, and (b) the runtime-appropriate command is selected (`bash /tmp/job.sh`, `pwsh /tmp/job.ps1`, `python /tmp/job.py`). The `ContainerRuntime.run()` method accepts any command list and already handles mounts, env vars, timeouts, and resource limits — no changes needed to `runtime.py`.

The key decisions from CONTEXT.md are locked: `python_script` is dropped entirely, all runtimes are containerised, signing is mandatory for all runtimes, `display_type` is server-side, and the submission form gets a conditional runtime dropdown.

**Primary recommendation:** Implement in three sequential waves — (1) node image + node agent execution, (2) backend API validation and display_type, (3) frontend dropdown and column swap — plus a cross-cutting migration wave for `ScheduledJob.runtime`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Bash and PowerShell scripts run **containerised** via `ContainerRuntime` (Docker/Podman) — same as non-python_script tasks
- Script content is written to a **temp file** (`/tmp/job_<guid>.sh` or `.ps1`) before execution, then cleaned up — handles multi-line scripts and special characters
- stdout + stderr are captured via `report_result()` — same pattern as existing Python execution
- Standard node image (`Containerfile.node`) ships with Python (already present), Bash (apt already present), PowerShell Core (`pwsh`)
- **All runtimes must be signed** — Ed25519 signing required for Python, Bash, and PowerShell equally
- Signature covers SHA256 hash of script content — same `signature_payload` pattern
- **`python_script` is dropped** — no existing deployments means no backward compat needed; `task_type: python_script` returns HTTP 422
- New unified type: `task_type: script` with required `runtime` field (`python` | `bash` | `powershell`)
- Unknown `runtime` values → HTTP 422 with clear validation error (RT-04)
- RT-06 (python_script alias) **removed from scope** — capture as dropped requirement during planning
- `display_type` computed **server-side** — format: `script (python)`, `script (bash)`, `script (powershell)`
- Current `task_type` column in Jobs list **replaced** with `display_type` — plain text, no coloured badges
- No filtering/search by runtime in Phase 47 — deferred to Phase 49
- Phase 47 **adds a runtime selector** to the existing raw-JSON submission form
- When task type is `script`, a second dropdown appears for runtime; hidden for other task types
- Control style: dropdown (consistent with existing form patterns in Jobs.tsx)
- `ScheduledJob` gains a `runtime` column (nullable, defaults to `'python'`)
- Migration: `migration_v38.sql` with `ADD COLUMN IF NOT EXISTS runtime VARCHAR DEFAULT 'python'`
- When scheduler fires a job, `runtime` is read from `ScheduledJob.runtime` and included in dispatched payload

### Claude's Discretion
- Exact temp file path pattern and cleanup approach (try/finally vs context manager)
- How `display_type` is surfaced on the API response — new field on `JobResponse` or computed in list query
- ContainerRuntime invocation details for Bash vs PowerShell (image selection, volume mounts)
- PowerShell Core package name and Containerfile.node install instructions

### Deferred Ideas (OUT OF SCOPE)
- Runtime-based job filtering — Phase 49 (Pagination, Filtering and Search)
- Full structured submission form with runtime selector — Phase 50 (Guided Form) will supersede the Phase 47 stopgap
- Capability-gated runtime dispatch (node advertises supported runtimes) — not in scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RT-01 | Operator can submit a Bash script job using `task_type: script` with `runtime: bash` | Confirmed via node.py execute_task pattern + ContainerRuntime.run() |
| RT-02 | Operator can submit a PowerShell script job using `task_type: script` with `runtime: powershell` | Confirmed via same execution path; pwsh already probed in get_capabilities() |
| RT-03 | Standard node image ships with Python, Bash, and PowerShell pre-installed | Containerfile.node currently has Python+Bash; PowerShell Core needs adding via apt |
| RT-04 | Backend validates `runtime` field at job creation, rejects unknown values with HTTP 422 | Pydantic enum validator on `JobCreate.runtime` field; pattern exists in codebase |
| RT-05 | `display_type` field rendered in job list, computed server-side | `list_jobs()` in job_service.py already builds dicts; add `display_type` computation there |
| RT-06 | DROPPED — `python_script` alias removed from scope per CONTEXT.md decisions | N/A |
| RT-07 | Operator can schedule a Bash or PowerShell job via job definitions | `ScheduledJob.runtime` column + migration_v38.sql; `execute_scheduled_job` reads and passes it |
</phase_requirements>

## Standard Stack

### Core (already in use)
| Library/Component | Version | Purpose | Notes |
|-------------------|---------|---------|-------|
| ContainerRuntime (runtime.py) | — | Containerised job execution via Docker/Podman | No changes needed — accepts arbitrary command list |
| Pydantic v2 | pinned in requirements.txt | Request model validation + enum enforcement | `Literal["python","bash","powershell"]` or `Enum` for runtime field |
| SQLAlchemy async | pinned | ORM column addition for ScheduledJob.runtime | `create_all` handles fresh installs; migration SQL handles existing |
| APScheduler | pinned | Scheduled job firing | `execute_scheduled_job()` reads new `runtime` column |

### PowerShell Core Install (Containerfile.node addition)
| Approach | Package | Notes |
|----------|---------|-------|
| Debian/Ubuntu apt | `powershell` via Microsoft APT repo | Requires adding Microsoft GPG key + repo; confirmed method for Debian-based images |
| Alternative (Alpine) | Not viable without extra work | `python:3.12-slim` is Debian-based — apt path is correct |

PowerShell Core on Debian (confirmed install pattern, HIGH confidence):
```bash
# Microsoft APT repository method
apt-get install -y wget apt-transport-https
wget -q "https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb"
dpkg -i packages-microsoft-prod.deb
apt-get update && apt-get install -y powershell
```
Binary name: `pwsh` (not `powershell`). Already probed in `get_capabilities()` — confirms the team planned for this.

### Frontend (already in use)
| Component | Purpose |
|-----------|---------|
| `<Select>` from `@/components/ui/select` | Existing task type dropdown pattern — exact same component for runtime dropdown |

## Architecture Patterns

### Recommended Change Scope

```
puppets/
├── Containerfile.node              # Add PowerShell Core install (RT-03)
└── environment_service/
    └── node.py                     # Add task_type=="script" branch (RT-01, RT-02)

puppeteer/
├── agent_service/
│   ├── db.py                       # ScheduledJob.runtime column (RT-07)
│   ├── models.py                   # JobCreate.runtime, JobCreate validator, JobResponse.display_type, JobDefinitionCreate.runtime, JobDefinitionResponse.runtime (RT-04, RT-05, RT-07)
│   ├── main.py                     # No new routes needed; task_type validation bubbles from JobCreate
│   └── services/
│       ├── job_service.py          # list_jobs() adds display_type; create_job() validates task_type=="script" (RT-04, RT-05)
│       └── scheduler_service.py    # execute_scheduled_job() uses s_job.runtime instead of hardcoded "python_script" (RT-07)
├── migration_v38.sql               # ADD COLUMN IF NOT EXISTS runtime (RT-07)
└── dashboard/src/views/
    └── Jobs.tsx                    # Runtime dropdown + display_type column (RT-05)
```

### Pattern 1: Script Temp File Execution (Claude's Discretion — recommended approach)

Write to temp file, pass as argument (not stdin), clean up in `finally`. This avoids stdin encoding issues with special characters.

**File extension mapping:**
```python
RUNTIME_EXT = {
    "python": ("py", ["python", "/tmp/job_{guid}.py"]),
    "bash": ("sh", ["bash", "/tmp/job_{guid}.sh"]),
    "powershell": ("ps1", ["pwsh", "/tmp/job_{guid}.ps1"]),
}
```

**Execution pattern (node.py, execute_task):**
```python
if task_type == "script":
    runtime = payload.get("runtime", "python")
    script = payload.get("script_content")
    signature = payload.get("signature")
    secrets = payload.get("secrets", {})

    # Signature verification (same as python_script branch)
    ...verify signature against script...

    # Write temp file
    ext, cmd_template = RUNTIME_EXT.get(runtime, ("py", ["python", f"/tmp/job_{guid}.py"]))
    tmp_path = f"/tmp/job_{guid}.{ext}"
    try:
        with open(tmp_path, "w") as f:
            f.write(script)
        cmd = [c.replace(f"/tmp/job_{guid}.{ext}", tmp_path) for c in cmd_template]
        # Mount temp file into container
        mounts = [...existing mounts..., f"{tmp_path}:{tmp_path}:ro"]
        result = await self.runtime_engine.run(
            image=image,
            command=cmd,
            env=env,
            mounts=mounts,
            ...
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
```

**Note:** For Python, `python -` (stdin) currently works and could be kept. For Bash and PowerShell, temp file via bind mount is cleaner. The temp-file approach is uniform across all runtimes — apply it to all three for consistency.

### Pattern 2: display_type Computation (Claude's Discretion — recommended approach)

Compute in `job_service.py:list_jobs()` where the dict is assembled. This avoids adding a computed property to the ORM model.

```python
# In list_jobs(), inside the per-job dict:
def _compute_display_type(task_type: str, payload: dict) -> str:
    if task_type == "script":
        runtime = payload.get("runtime", "python")
        return f"script ({runtime})"
    return task_type  # "web_task", "file_download", etc.

response_jobs.append({
    ...existing fields...,
    "task_type": job.task_type,
    "display_type": _compute_display_type(job.task_type, payload),
})
```

`JobResponse` gains `display_type: Optional[str] = None`. Frontend reads `job.display_type ?? job.task_type` for backward compat with non-script types during the transition.

### Pattern 3: JobCreate Runtime Validation (RT-04)

```python
# models.py
from typing import Literal, Optional
from pydantic import field_validator

class JobCreate(BaseModel):
    task_type: str
    runtime: Optional[Literal["python", "bash", "powershell"]] = None
    payload: Dict
    ...

    @field_validator("runtime", mode="before")
    @classmethod
    def validate_runtime(cls, v, info):
        # Only required when task_type == "script"; Pydantic Literal handles enum enforcement
        return v

    @model_validator(mode="after")
    def require_runtime_for_script(self):
        if self.task_type == "script" and self.runtime is None:
            raise ValueError("runtime is required when task_type is 'script'")
        if self.task_type == "python_script":
            raise ValueError("task_type 'python_script' is no longer supported; use task_type 'script' with runtime 'python'")
        return self
```

Pydantic v2 `Literal["python","bash","powershell"]` enforces the enum — unknown values automatically produce a 422 with a clear message identifying the invalid value.

### Pattern 4: Scheduler Runtime Field (RT-07)

`execute_scheduled_job()` currently hardcodes `task_type="python_script"`. Change to:
```python
runtime = getattr(s_job, 'runtime', None) or 'python'
new_job = Job(
    guid=execution_guid,
    task_type="script",                          # unified type
    payload=json.dumps({
        "script_content": s_job.script_content,
        "signature": s_job.signature_payload,
        "runtime": runtime,                      # from ScheduledJob.runtime
        "secrets": {}
    }),
    ...
)
```

`ScheduledJob.runtime` column: `nullable=True`, DB default `'python'`. `getattr` guard handles the case where existing in-memory ORM objects don't yet have the attribute (safe during startup before migration).

### Pattern 5: Frontend Runtime Dropdown (Jobs.tsx)

The existing form has:
1. Task type `<Select>` — currently has `python_script`, `web_task`, `file_download`
2. JSON payload textarea

Phase 47 changes:
1. Task type options: replace `python_script` with `script`, keep `web_task` and `file_download`
2. When `newTaskType === 'script'`, render a second `<Select>` for runtime: `python`, `bash`, `powershell`
3. `createJob()` passes `runtime` at the top level of the POST body (not inside payload)
4. Jobs table "Type" column: replace `job.task_type || job.payload?.task_type` with `job.display_type || job.task_type`

State additions to Jobs.tsx:
```typescript
const [newRuntime, setNewRuntime] = useState<string>('python');
```

Interface update:
```typescript
interface Job {
    ...existing fields...,
    display_type?: string;  // server-computed
}
```

### Anti-Patterns to Avoid

- **Piping Bash/PS scripts via stdin:** Works for Python (`python -`) but `bash` reads from stdin differently when piped — temp file is the correct approach for all runtimes.
- **Frontend parsing payload JSON for runtime:** Explicitly prohibited by RT-05. `display_type` must come from the server.
- **Keeping `python_script` in the task type Select dropdown:** The decision removes it entirely — update the dropdown to show `script` only.
- **Ignoring `getattr` guard on `s_job.runtime`:** The ORM column is new. Fresh installs use `create_all` and will have it. Existing deployments apply migration_v38.sql. But defensive `getattr` is cheap insurance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Runtime enum validation | Custom string checks in route handler | Pydantic `Literal` type + `@model_validator` | Already the project pattern; produces correct 422 automatically |
| Temp file cleanup | Manual try/except scattered | `try/finally` block (consistent with UpgradeManager in node.py) | The upgrade recipe in node.py already uses this pattern — line 272 |
| PowerShell install | Building from source | Microsoft APT repo | Official supported path; already probed in `get_capabilities()` |
| display_type in frontend | Parsing `payload.runtime` in TSX | Add `display_type` to `list_jobs()` dict | RT-05 explicit requirement; server-authoritative |

## Common Pitfalls

### Pitfall 1: Temp File Not Mounted into Container
**What goes wrong:** Script is written to the node's filesystem at `/tmp/job_<guid>.sh` but the container can't see it — execution fails with "file not found."
**Why it happens:** `ContainerRuntime.run()` uses `docker run --network=host` but no automatic bind mount of `/tmp`.
**How to avoid:** Add `f"{tmp_path}:{tmp_path}:ro"` to the `mounts` list before calling `runtime_engine.run()`.
**Warning signs:** Container exits with code 1 and stderr "bash: /tmp/job_xxx.sh: No such file or directory."

### Pitfall 2: Runtime Field Not in WorkResponse / Payload on Wire
**What goes wrong:** Backend stores `runtime` in `job_service.create_job()` but `assign_job()` / `WorkResponse` doesn't pass it to the node, so `execute_task()` can't read it from `payload`.
**Why it happens:** `runtime` is a top-level `JobCreate` field; if it's not merged into the stored `payload` JSON, the node never sees it.
**How to avoid:** Two options — (a) store `runtime` inside the encrypted payload dict, or (b) add `runtime` as a top-level column on `Job` and include it in `WorkResponse`. Option (a) is simpler and consistent with how `script_content` and `signature` are already in the payload.
**Recommended:** Merge `runtime` into the payload dict at `create_job()` time: `encrypted_payload["runtime"] = job_req.runtime`.

### Pitfall 3: ScheduledJob.runtime Not Present on In-Memory ORM Objects
**What goes wrong:** After deploying without running migration_v38.sql, existing `ScheduledJob` objects from DB lack the `runtime` attribute — `s_job.runtime` raises `AttributeError`.
**Why it happens:** SQLAlchemy lazy-loads columns; missing DB column means the attribute is absent.
**How to avoid:** Use `getattr(s_job, 'runtime', 'python') or 'python'` in `execute_scheduled_job()`.

### Pitfall 4: python_script Still in Frontend Type Select
**What goes wrong:** Operator submits with `task_type: python_script` from the old dropdown and gets a 422 they don't understand.
**Why it happens:** Frontend was not updated when backend dropped the legacy type.
**How to avoid:** Remove the `python_script` SelectItem from Jobs.tsx and replace with `script`. The task type and runtime are now two separate fields.

### Pitfall 5: display_type Not Returned for Non-Script Jobs
**What goes wrong:** Jobs with `task_type: web_task` appear blank in the Type column if frontend switches entirely to `display_type`.
**Why it happens:** `_compute_display_type()` only handles `script` and falls through to raw `task_type` for others — but if `JobResponse.display_type` is None for old jobs, frontend sees `undefined`.
**How to avoid:** Always populate `display_type` for all jobs. For non-script types, use the `task_type` value as the display string. Frontend reads `job.display_type ?? job.task_type`.

### Pitfall 6: PowerShell Core Not in Image After Build
**What goes wrong:** `pwsh` not found in container; PowerShell jobs fail with "executable not found."
**Why it happens:** Microsoft APT repo requires GPG key + repo registration before `apt-get install powershell`. If the Dockerfile layer is wrong the package is silently absent.
**How to avoid:** After building the image, verify: `docker run --rm <image> pwsh -Command 'Write-Host "ok"'` returns exit 0.

## Code Examples

### Containerfile.node — PowerShell Core Addition
```dockerfile
# Containerfile.node (RT-03 addition)
FROM python:3.12-slim

WORKDIR /app

# Install system deps including PowerShell Core
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget apt-transport-https gnupg podman krb5-user iptables docker.io \
    && wget -q "https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb" \
    && dpkg -i packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y powershell \
    && rm -rf /var/lib/apt/lists/* packages-microsoft-prod.deb

# ... rest of Containerfile unchanged
```

### migration_v38.sql
```sql
-- migration_v38: Add runtime column to scheduled_jobs for multi-runtime support (RT-07)
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS runtime VARCHAR DEFAULT 'python';
```

### JobCreate model update (models.py)
```python
from typing import Literal, Optional
from pydantic import model_validator

class JobCreate(BaseModel):
    task_type: str
    runtime: Optional[Literal["python", "bash", "powershell"]] = None
    payload: Dict
    # ... existing fields unchanged ...

    @model_validator(mode="after")
    def validate_task_type_and_runtime(self):
        if self.task_type == "python_script":
            raise ValueError(
                "task_type 'python_script' is no longer supported. "
                "Use task_type='script' with runtime='python'."
            )
        if self.task_type == "script" and self.runtime is None:
            raise ValueError("runtime is required when task_type is 'script'")
        return self
```

### display_type computation (job_service.py)
```python
def _compute_display_type(task_type: str, payload: dict) -> str:
    """Server-side display_type — never let frontend parse payload."""
    if task_type == "script":
        runtime = payload.get("runtime", "python")
        return f"script ({runtime})"
    return task_type
```

### node.py — script task_type branch (execute_task)
```python
elif task_type == "script":
    runtime = payload.get("runtime", "python")
    script = payload.get("script_content")
    signature = payload.get("signature")
    secrets = payload.get("secrets", {})

    # ... signature verification (identical to python_script branch) ...

    ext_map = {"python": "py", "bash": "sh", "powershell": "ps1"}
    cmd_map = {
        "python": ["python", f"/tmp/job_{guid}.py"],
        "bash": ["bash", f"/tmp/job_{guid}.sh"],
        "powershell": ["pwsh", f"/tmp/job_{guid}.ps1"],
    }
    ext = ext_map.get(runtime, "py")
    cmd = cmd_map.get(runtime, ["python", f"/tmp/job_{guid}.py"])
    tmp_path = f"/tmp/job_{guid}.{ext}"

    script_hash = hashlib.sha256(script.encode('utf-8')).hexdigest()

    try:
        with open(tmp_path, "w") as f:
            f.write(script)
        env = {...secrets...}
        mounts = [f"{tmp_path}:{tmp_path}:ro"]
        result = await self.runtime_engine.run(
            image=image, command=cmd, env=env, mounts=mounts,
            memory_limit=memory_limit, cpu_limit=cpu_limit, timeout=timeout_secs,
        )
        # ... report_result() identical to python_script branch ...
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
```

## State of the Art

| Old Approach | Current Approach | Phase | Impact |
|--------------|------------------|-------|--------|
| `task_type: python_script` | `task_type: script` + `runtime: python\|bash\|powershell` | 47 | Single task type, runtime explicit and validated |
| Frontend reads `payload.task_type` for display | Server returns `display_type` field | 47 | Consistent display regardless of payload shape |
| `ScheduledJob` always fires Python | `ScheduledJob.runtime` selects interpreter | 47 | Scheduled Bash/PS jobs supported |
| Script piped via stdin (`python -`) | Script written to temp file, mounted into container | 47 | Works for all runtimes, avoids stdin encoding edge cases |

**Deprecated/outdated:**
- `task_type: python_script`: removed — HTTP 422 on submission
- Frontend `job.payload?.task_type` fallback for type display: replaced by `job.display_type`
- Hardcoded `task_type="python_script"` in `execute_scheduled_job()`: replaced by `task_type="script"` + `runtime` from column

## Open Questions

1. **Should Python runtime also switch to temp-file execution?**
   - What we know: Python currently uses stdin (`python -`), which works correctly today
   - What's unclear: Whether stdin approach should be retired for consistency
   - Recommendation: Yes — use temp file for all three runtimes for uniformity. The `UpgradeManager` already uses this pattern (line 243 in node.py). Minor change, avoids two execution code paths.

2. **Should `runtime` be stored as a top-level `Job` column or inside the payload?**
   - What we know: Existing fields like `signature` and `script_content` live inside the payload dict; `task_type` is a top-level column
   - What's unclear: Whether `runtime` warrants its own column for future filtering (Phase 49 SRCH-03 will need it)
   - Recommendation: Store as both — add `runtime` to the payload dict (so the node sees it in `WorkResponse.payload`) AND add a `runtime` column to `Job` (nullable, populated at create time). This enables Phase 49 server-side filtering without a migration later. Add `runtime VARCHAR` to `migration_v38.sql` for both tables.

3. **Image selection for Bash/PowerShell jobs**
   - What we know: Python jobs use `JOB_IMAGE` env var (default: `localhost/master-of-puppets-node:latest`)
   - What's unclear: Whether Bash/PS jobs should use the same image or a different default
   - Recommendation: Same image (`localhost/master-of-puppets-node:latest`) — since RT-03 installs all three runtimes in the standard node image. No per-runtime image selection needed in Phase 47.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `puppeteer/pytest.ini` or inferred from `pyproject.toml` |
| Quick run command | `cd puppeteer && pytest tests/test_runtime_expansion.py -x` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RT-01 | `task_type: script, runtime: bash` accepted; node executes bash | unit (source inspection) + smoke | `pytest tests/test_runtime_expansion.py::test_bash_job_accepted -x` | Wave 0 |
| RT-02 | `task_type: script, runtime: powershell` accepted; node executes pwsh | unit + smoke | `pytest tests/test_runtime_expansion.py::test_powershell_job_accepted -x` | Wave 0 |
| RT-03 | Containerfile.node installs `pwsh` | unit (Containerfile text inspection) | `pytest tests/test_runtime_expansion.py::test_containerfile_has_powershell -x` | Wave 0 |
| RT-04 | Unknown runtime → HTTP 422; `python_script` task_type → HTTP 422 | unit | `pytest tests/test_runtime_expansion.py::test_invalid_runtime_rejected -x` | Wave 0 |
| RT-05 | `display_type` present in list_jobs output; never parses payload on frontend | unit | `pytest tests/test_runtime_expansion.py::test_display_type_computed_serverside -x` | Wave 0 |
| RT-07 | `ScheduledJob.runtime` column exists; scheduler fires with correct runtime | unit | `pytest tests/test_runtime_expansion.py::test_scheduled_job_runtime_field -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_runtime_expansion.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full backend + frontend suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_runtime_expansion.py` — covers RT-01 through RT-07
- [ ] No framework install needed — pytest already present

*(Pattern: test_job_staging.py uses source inspection via `inspect.getsource()` — same approach works well here for validating models, DB schema, and service logic without needing a live DB.)*

## Sources

### Primary (HIGH confidence)
- Direct source read: `puppets/environment_service/node.py` — execute_task(), run_python_script(), UpgradeManager
- Direct source read: `puppets/environment_service/runtime.py` — ContainerRuntime.run()
- Direct source read: `puppets/Containerfile.node` — current image definition
- Direct source read: `puppeteer/agent_service/db.py` — ScheduledJob, Job models
- Direct source read: `puppeteer/agent_service/models.py` — JobCreate, JobResponse, JobDefinitionCreate
- Direct source read: `puppeteer/agent_service/services/job_service.py` — list_jobs(), create_job()
- Direct source read: `puppeteer/agent_service/services/scheduler_service.py` — execute_scheduled_job()
- Direct source read: `puppeteer/dashboard/src/views/Jobs.tsx` — existing form and table patterns
- Direct source read: `puppeteer/migration_v37.sql` — migration format reference

### Secondary (MEDIUM confidence)
- node.py `get_capabilities()` already probes `pwsh --Version` — confirms PowerShell was planned for the standard image
- `UpgradeManager.execute_upgrade()` uses try/finally temp file cleanup pattern — confirms correct idiom for the project

### Tertiary (LOW confidence)
- Microsoft PowerShell Core Debian install method — well-known, but specific .deb URL may change; verify current URL at build time

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies except PowerShell system package
- Architecture: HIGH — all changes are additive; execution flow confirmed by reading source
- Pitfalls: HIGH — identified by tracing through ContainerRuntime.run() signature and execute_task() data flow
- RT-06 dropped: HIGH — CONTEXT.md explicitly removes it from scope

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable domain — FastAPI/Pydantic/APScheduler patterns are stable)
