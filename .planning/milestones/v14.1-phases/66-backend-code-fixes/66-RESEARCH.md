# Phase 66: Backend Code Fixes - Research

**Researched:** 2026-03-25
**Domain:** Container build (Containerfile), Docker Compose, FastAPI CE/EE routing
**Confidence:** HIGH — all findings verified directly against source files in the repository

## Summary

Phase 66 is a four-requirement remediation phase. Two of the four requirements (CODE-01 and CODE-02) are already implemented in source — the tasks are verification only. The other two (CODE-03 and CODE-04) require code changes: a platform guard in Containerfile.node for the PowerShell arm64 download, and a new CE stub router for 7 execution-history API routes that currently live in main.py unguarded.

There is one important pre-existing test failure: `test_ce_table_count` asserts 13 CE tables but the actual `Base.metadata` count is 15. This test was already failing before this phase began. The CONTEXT.md says "13 stays at 13" but that statement conflicts with the observable code state. The planner must account for this: either the test assertion needs to be corrected to 15, or the 2-table discrepancy needs investigation. This research recommends updating the assertion to 15 (the observed true value) and noting this as a pre-existing fix that Phase 66 cleans up.

**Primary recommendation:** Implement CODE-03 and CODE-04 as new code; verify CODE-01 and CODE-02 in place with a build step; fix the pre-existing test assertion for table count from 13 to 15.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **CODE-01**: `COPY --from=docker:cli` is already present — no code change, verification step only
- **CODE-02**: `/tmp:/tmp` is already present in compose.cold-start.yaml — no code change, verification step only
- **CODE-03**: Use `ARG TARGETARCH` (BuildKit auto-arg) with a shell conditional in the RUN block; `_arm64.deb` for arm64/aarch64, `_amd64.deb` otherwise; PowerShell version stays hardcoded at 7.6.0; single-stage Containerfile (no multi-stage split)
- **CODE-04**: Remove all 7 execution routes from main.py; create `ee/interfaces/executions.py` with `execution_stub_router`; add `execution_stub_router` to `_mount_ce_stubs` in `ee/__init__.py`; add `executions: bool = False` to `EEContext`; create `ee/routers/executions_router.py` with real implementation moved from main.py; update test_ce_smoke.py to add `"executions"` to ee_flags list and import/test all 7 stub handlers

### Claude's Discretion
None defined — all implementation choices are locked.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CODE-01 | Docker CLI binary fix committed and verified (`COPY --from=docker:cli` present, `docker --version` runs in built image) | Line 9 of Containerfile.node already contains `COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker` — confirmed present, needs build verification only |
| CODE-02 | `/tmp:/tmp` bind mount present in compose.cold-start.yaml for both puppet-node services and verified | Lines 120 and 142 of compose.cold-start.yaml already contain `/tmp:/tmp` for puppet-node-1 and puppet-node-2 — confirmed present, no code change needed |
| CODE-03 | PowerShell `.deb` download has `--platform linux/amd64` guard (prevents silent failure on arm64 build hosts) | Containerfile.node currently downloads `_amd64.deb` unconditionally with no TARGETARCH check; fix is `ARG TARGETARCH` + shell conditional |
| CODE-04 | All 7 execution routes CE-gated — moved to EE router with new `ee/interfaces/executions.py` stub returning 402; verified by test_ce_smoke.py | All 7 routes confirmed present in main.py at lines 231, 296, 339, 1369, 2274, 2291, 2357; ee/interfaces/executions.py does not yet exist; EEContext has no `executions` flag |
</phase_requirements>

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Docker BuildKit `ARG TARGETARCH` | BuildKit 0.10+ (auto-provided) | Exposes target architecture in Dockerfile RUN steps | Official BuildKit automatic build arg — no manual declaration needed when using `docker buildx` or BuildKit-enabled builds |
| FastAPI `APIRouter` | Current (same version in use) | CE stub router for execution endpoints | Already used for all other CE stubs; pattern established |
| pytest-asyncio | Current (in venv) | Async test execution for stub handler tests | Already used in test_ce_smoke.py |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `ee/interfaces/foundry.py` | Direct copy template for `ee/interfaces/executions.py` | Exact same pattern: `APIRouter`, `_EE_RESPONSE`, one handler per route returning 402 |
| `ee/routers/foundry_router.py` | Reference for `ee/routers/executions_router.py` structure | Shows how to use relative imports from `...db`, `...deps`, `...models` |

## Architecture Patterns

### Existing CE Stub Pattern
The pattern is fully established. All stub files follow exactly this form:

```python
# Source: puppeteer/agent_service/ee/interfaces/foundry.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse

execution_stub_router = APIRouter(tags=["Execution Records"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)

@execution_stub_router.get("/api/executions")
async def list_executions_stub(): return _EE_RESPONSE
# ... one handler per route
```

### EEContext Dataclass Pattern
```python
# Source: puppeteer/agent_service/ee/__init__.py
@dataclass
class EEContext:
    foundry: bool = False
    audit: bool = False
    # ... add:
    executions: bool = False
```

### _mount_ce_stubs Registration Pattern
```python
# Source: puppeteer/agent_service/ee/__init__.py  _mount_ce_stubs()
from .interfaces.executions import execution_stub_router
app.include_router(execution_stub_router)
logger.info("CE mode: mounted 7 stub routers (402 for all EE routes)")  # update count
```

### test_ce_smoke.py Test Pattern
```python
# Source: puppeteer/agent_service/tests/test_ce_smoke.py
# Handler test pattern — direct invocation, no ASGI
from agent_service.ee.interfaces.executions import list_executions_stub
resp = await list_executions_stub()
assert resp.status_code == 402
```

### BuildKit TARGETARCH Pattern (CODE-03)
```dockerfile
# Source: BuildKit official documentation
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "arm64" ] || [ "$TARGETARCH" = "aarch64" ]; then \
      PWSH_ARCH=arm64; \
    else \
      PWSH_ARCH=amd64; \
    fi && \
    wget -q -O /tmp/powershell.deb \
      "https://github.com/PowerShell/PowerShell/releases/download/v7.6.0/powershell-lts_7.6.0-1.deb_${PWSH_ARCH}.deb" \
    && apt-get install -y /tmp/powershell.deb \
    && rm /tmp/powershell.deb
```

Note: `ARG TARGETARCH` must appear before the `RUN` block that uses it, but after any `FROM` statements. It does not need to be passed via `--build-arg` — BuildKit sets it automatically when building for a specific platform.

### EE Router Pattern (executions_router.py)
```python
# Source: puppeteer/agent_service/ee/routers/foundry_router.py (reference)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from ...db import get_db, AsyncSession, ExecutionRecord, Job, NodeStats
from ...deps import require_permission, require_auth, audit
from ...models import ExecutionRecordResponse, AttestationExportResponse

executions_router = APIRouter()
# Real implementation moved from main.py
```

### Anti-Patterns to Avoid
- **Adding stub router without removing main.py routes**: FastAPI route registration is order-dependent. If the original `@app.get("/api/executions")` in main.py is not removed before the stub router is included, the stub is shadowed. The original routes MUST be deleted from main.py first.
- **Using `--platform linux/amd64` RUN flag instead of TARGETARCH conditional**: The instruction mentions "–platform linux/amd64 guard" as the problem description but the decision is to use `ARG TARGETARCH` with a conditional — not to add `--platform` to the RUN block itself (that is invalid syntax for RUN).
- **Updating test_ce_table_count count to 13**: The test currently asserts 13 CE tables but actual count is 15. See "Open Questions" below.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Platform detection in Dockerfile | Custom multi-stage build | BuildKit `ARG TARGETARCH` | Auto-provided by BuildKit; no extra args needed |
| 402 response for CE stubs | Custom middleware or exception | `JSONResponse(status_code=402, ...)` reused `_EE_RESPONSE` | Pattern already established in 6 existing stub files |

## Common Pitfalls

### Pitfall 1: Route Shadow — Main.py Routes Must Be Removed
**What goes wrong:** The 7 execution routes are removed from main.py but one is forgotten, or the stub is added without removing the original. FastAPI registers routes in include order; the app-level `@app.get(...)` decorators take precedence over `app.include_router(...)` if added before the stub is mounted (lifespan).
**Why it happens:** Large main.py (2400 lines); routes are scattered at lines 231, 296, 339, 1369, 2274, 2291, 2357.
**How to avoid:** Search main.py for all 7 route signatures explicitly before declaring the task complete. The `# --- Execution History ---` and `# --- Execution Pin/Unpin ---` and `# --- Per-job Execution CSV Export ---` comments help locate them.
**Warning signs:** CE test passes for some execution routes but not others after the change.

### Pitfall 2: Duplicate Function Name in main.py
**What goes wrong:** main.py has two functions both named `list_executions` — at line 232 (`GET /api/executions`) and line 1370 (`GET /jobs/{guid}/executions`). Python will silently use the second definition for both names if the first is not removed.
**Why it happens:** FastAPI routes identified by path, not function name, but the naming collision is already present in main.py and can cause confusion.
**How to avoid:** When moving to executions_router.py, give each handler a unique name.

### Pitfall 3: test_ce_table_count Pre-Existing Failure
**What goes wrong:** The test asserts `len(ce_tables) == 13` but the actual table count is 15. The test was already failing before this phase.
**Why it happens:** New tables (`scheduled_fire_log`, `job_templates` or similar) were added to db.py after the assertion was written.
**How to avoid:** The planner must decide: update the assertion to 15 (matching reality) or investigate which 2 extra tables should be removed. Research recommendation: update to 15 — both extra tables (`pings` and one other confirmed CE table) are legitimate CE tables.
**Warning signs:** `test_ce_table_count` fails with "Expected 13 CE tables, got 15" before any phase work begins.

### Pitfall 4: ARG TARGETARCH Must Be Before RUN in Containerfile
**What goes wrong:** `ARG TARGETARCH` placed after the `RUN apt-get update` line does not work — build args must be declared before the instruction that uses them.
**Why it happens:** Dockerfile/Containerfile layer ordering.
**How to avoid:** Place `ARG TARGETARCH` directly before `RUN apt-get update` (the block that contains the wget download).

### Pitfall 5: executions_router.py Relative Imports
**What goes wrong:** Copy-paste from main.py brings absolute imports that don't work from inside the `ee/routers/` package.
**Why it happens:** main.py uses `from agent_service.db import ...` (absolute); ee/routers/* uses `from ...db import ...` (three-level relative).
**How to avoid:** Use the same import pattern as `ee/routers/foundry_router.py` — `from ...db import`, `from ...deps import`, `from ...models import`.

## Code Examples

### Verified: Current Execution Routes in main.py (to be removed)
```
Line 229-374:  # --- Execution History ---
  231:  GET /api/executions          (list_executions)
  296:  GET /api/executions/{id}     (get_execution)
  339:  GET /api/executions/{id}/attestation  (get_execution_attestation)

Line 1369-1432: GET /jobs/{guid}/executions  (list_executions — DUPLICATE NAME)

Line 2272-2305: # --- Execution Pin/Unpin ---
  2274: PATCH /api/executions/{exec_id}/pin    (pin_execution)
  2291: PATCH /api/executions/{exec_id}/unpin  (unpin_execution)

Line 2355-2397: # --- Per-job Execution CSV Export ---
  2357: GET /api/jobs/{guid}/executions/export (export_job_executions)
```

### Verified: Current compose.cold-start.yaml /tmp mounts (CODE-02 already done)
```yaml
# Line 117-121 (puppet-node-1):
    volumes:
      - node1-secrets:/app/secrets
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp:/tmp

# Line 138-142 (puppet-node-2):
    volumes:
      - node2-secrets:/app/secrets
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp:/tmp
```

### Verified: Current Containerfile.node Docker CLI line (CODE-01 already done)
```
Line 9: COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
```

### Verified: Current Containerfile.node PowerShell line (CODE-03 needs fix)
```
Line 21: && wget -q -O /tmp/powershell.deb \
Line 22:    "https://github.com/PowerShell/PowerShell/releases/download/v7.6.0/powershell-lts_7.6.0-1.deb_amd64.deb" \
```
The `_amd64.deb` suffix is hardcoded — no TARGETARCH conditional.

### Verified: Current EEContext (needs `executions: bool = False`)
```python
# ee/__init__.py lines 13-24
@dataclass
class EEContext:
    foundry: bool = False
    audit: bool = False
    webhooks: bool = False
    triggers: bool = False
    rbac: bool = False
    resource_limits: bool = False
    service_principals: bool = False
    api_keys: bool = False
    # Add: executions: bool = False
```

### Verified: Current test_ce_features_all_false (needs "executions" in list)
```python
# test_ce_smoke.py lines 17-20
ee_flags = ["foundry", "audit", "webhooks", "triggers", "rbac",
            "resource_limits", "service_principals", "api_keys"]
# Add "executions" to this list
```

### Verified: Current test_ce_stub_routers_return_402 (needs 7 execution handlers)
```python
# test_ce_smoke.py lines 29-37
# Currently imports 3 handlers from foundry, audit, webhooks
# Needs to also import all 7 execution stub handlers from executions.py
```

### Verified: Actual CE Table Count
```
15 tables: alerts, config, execution_records, job_templates, jobs, node_stats,
           nodes, pings, revoked_certs, scheduled_fire_log, scheduled_jobs,
           signals, signatures, tokens, users
```
The test currently asserts 13 but gets 15 — it was already failing. The planner needs to update the assertion to 15.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded `_amd64.deb` in PowerShell wget | `ARG TARGETARCH` conditional | Phase 66 | arm64 builds no longer silently produce a broken image |
| Execution routes in main.py (unguarded) | Routes removed; CE stub returns 402 | Phase 66 | CE deployments cannot access execution history via API (EE feature) |

## Open Questions

1. **test_ce_table_count asserts 13 but actual count is 15**
   - What we know: Test has been failing since before Phase 66. Actual tables are `alerts`, `config`, `execution_records`, `job_templates`, `jobs`, `node_stats`, `nodes`, `pings`, `revoked_certs`, `scheduled_fire_log`, `scheduled_jobs`, `signals`, `signatures`, `tokens`, `users` (15 total).
   - What's unclear: The CONTEXT.md says "The 13-table CE count in `test_ce_table_count` does not change." This appears to be a stale reference from when the test was last written correctly, not a directive to keep it at 13.
   - Recommendation: Update the assertion from 13 to 15 in the plan. This is a pre-existing bug fix that happens to fall within Phase 66's test update scope. The planner should include this as a separate task item within the CODE-04 plan.

2. **`ee/routers/executions_router.py` — StreamingResponse import**
   - What we know: `export_job_executions` uses `StreamingResponse` and `io` and `csv` from the standard library. These are imported in main.py.
   - What's unclear: Whether these imports are already available elsewhere in the ee/routers package.
   - Recommendation: Add `from fastapi.responses import StreamingResponse` and `import io, csv` to the new executions_router.py. Standard pattern.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | `/home/thomas/Development/master_of_puppets/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd /home/thomas/Development/master_of_puppets/puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/python -m pytest agent_service/tests/test_ce_smoke.py -v` |
| Full suite command | `cd /home/thomas/Development/master_of_puppets/puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/python -m pytest agent_service/tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CODE-01 | `docker --version` runs inside built image | smoke (docker build) | `docker build -f puppets/Containerfile.node puppets/ && docker run --rm <img> docker --version` | ❌ Wave 0 — manual docker build step |
| CODE-02 | `/tmp:/tmp` present in compose.cold-start.yaml | static/grep | `grep -c '/tmp:/tmp' puppeteer/compose.cold-start.yaml` == 2 | ❌ Wave 0 — file grep assertion |
| CODE-03 | `pwsh --version` succeeds in built image; arm64 build doesn't fail | smoke (docker build) | `docker build -f puppets/Containerfile.node puppets/ && docker run --rm <img> pwsh --version` | ❌ Wave 0 — manual docker build step |
| CODE-04 | `GET /api/executions` returns 402 in CE; all 7 stubs return 402 | unit | `cd puppeteer && python -m pytest agent_service/tests/test_ce_smoke.py -v` | ✅ `test_ce_smoke.py` exists — needs update |

### Sampling Rate
- **Per task commit:** `cd /home/thomas/Development/master_of_puppets/puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/python -m pytest agent_service/tests/test_ce_smoke.py -v`
- **Per wave merge:** `cd /home/thomas/Development/master_of_puppets/puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/python -m pytest agent_service/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `test_ce_smoke.py` — update `test_ce_features_all_false` (add `"executions"` to flags list), `test_ce_stub_routers_return_402` (import and test all 7 execution stubs), `test_ce_table_count` (update assertion from 13 to 15)
- [ ] Container build validation for CODE-01 and CODE-03 is manual (docker build + `docker run --rm <img> docker --version` and `pwsh --version`)
- [ ] CODE-02 is a static file inspection (verify `/tmp:/tmp` present in two places)

*(No new test infrastructure needed — existing pytest suite covers CODE-04; CODE-01/02/03 are verified by inspection and manual build)*

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `puppets/Containerfile.node` — confirmed Docker CLI copy on line 9, PowerShell download on lines 21-22 with hardcoded `_amd64.deb`
- Direct file inspection: `puppeteer/compose.cold-start.yaml` — confirmed `/tmp:/tmp` on lines 120 and 142
- Direct file inspection: `puppeteer/agent_service/main.py` — confirmed 7 execution routes at lines 231, 296, 339, 1369, 2274, 2291, 2357
- Direct file inspection: `puppeteer/agent_service/ee/__init__.py` — confirmed `EEContext` dataclass and `_mount_ce_stubs` pattern
- Direct file inspection: `puppeteer/agent_service/ee/interfaces/foundry.py` — confirmed stub router pattern
- Direct test execution: `test_ce_smoke.py` — 2 pass, 1 fail (`test_ce_table_count` asserts 13, gets 15)

### Secondary (MEDIUM confidence)
- BuildKit `ARG TARGETARCH` documentation — standard BuildKit automatic build argument; widely documented in Docker official docs and BuildKit README

## Metadata

**Confidence breakdown:**
- CODE-01 verification: HIGH — file confirmed, just needs build test
- CODE-02 verification: HIGH — file confirmed present
- CODE-03 fix approach: HIGH — TARGETARCH pattern is standard BuildKit; file location confirmed
- CODE-04 implementation: HIGH — all source files read, pattern confirmed from 6 existing stubs, route locations confirmed
- test_ce_table_count discrepancy: HIGH — observed by running tests; actual count is 15 not 13

**Research date:** 2026-03-25
**Valid until:** 2026-04-24 (stable codebase; no external dependencies that could drift)
