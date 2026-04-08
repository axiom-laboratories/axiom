# Phase 124: Ephemeral Execution Guarantee - Research

**Researched:** 2026-04-08
**Domain:** Node execution isolation, container runtime visibility, Docker compose generation hardening
**Confidence:** HIGH

## Summary

Phase 124 hardens the guarantee that all job code executes inside ephemeral containers, never directly on the node host. The direct execution mode (`EXECUTION_MODE=direct`) was hard-blocked at startup in Phase 122 (v10.0), but this phase adds server-side awareness and validation. Nodes report their detected runtime (docker/podman/auto detection result) in heartbeat payloads, the orchestrator persists this to the database, and the compose generator validates that generated configs will never be direct-mode. Documentation is cleaned to remove all references to direct mode as a production pattern. This phase directly enables requirement EPHR-02 (operator warned/blocked from unsafe config).

**Primary recommendation:** Implement server-side execution_mode persistence in Node table following the Phase 123 cgroup detection pattern, add rejection logic to compose generator, update all documentation to remove direct mode references, and clean dead code branches.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Nodes report detected execution mode (docker/podman) in every heartbeat — consistent with cgroup detection pattern from Phase 123
- New `execution_mode` column on Node table (String, nullable) — stores the value from heartbeat
- New field on HeartbeatPayload (`Optional[str] = None`) — backward compatible with old nodes
- Orchestrator updates DB column on every heartbeat, same as cgroup fields
- `execution_mode` exposed in NodeResponse API model so dashboard can consume it
- Dashboard shows Docker/Podman badge in node list AND detail drawer — consistent with planned cgroup badge (Phase 127)
- No UNSAFE badge needed — direct mode is hard-blocked at startup, so a node that's online is guaranteed to be using a container runtime
- `GET /nodes/compose` rejects `execution_mode=direct` with HTTP 400 and clear error message — fail at generation time, not at node boot
- Server's own `NODE_EXECUTION_MODE` env var validated too — if set to `direct`, reject at generation time (or server startup) since all generated configs would be broken
- All other execution mode values (docker, podman, auto) remain valid

### Claude's Discretion
- Exact heartbeat field name (e.g. `execution_mode` vs `detected_execution_mode`)
- Migration file numbering
- Badge styling and placement details in Nodes.tsx
- SERVER_EXECUTION_MODE validation timing (startup vs per-request)

### Deferred Ideas (OUT OF SCOPE)
- Podman-specific socket mount variants
- Cluster-wide oversubscription detection
- Default limit templates per workload type

## Phase Requirements

None specified for Phase 124 in phase requirement IDs, but this phase addresses requirements from REQUIREMENTS.md:

| ID | Description | Research Support |
|----|-------------|-----------------|
| EPHR-01 | All job code executes inside ephemeral containers, never directly on the node host | Startup hard-block already in place; this phase adds server-side visibility |
| EPHR-02 | EXECUTION_MODE=direct flagged as unsafe; operator warned or blocked in production | Compose generator rejection + documentation cleanup |

## Standard Stack

### Core Components (Backend)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| SQLAlchemy | (from req.txt, async support) | ORM for Node.execution_mode persistence | Already used for all DB schema; async patterns established in Phase 123 |
| FastAPI | (from req.txt) | HTTP route handlers, validation | Standard backend framework for all API endpoints |
| Pydantic | (from req.txt) | HeartbeatPayload + NodeResponse models | Already used for all request/response validation |

### Core Components (Node/Runtime)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| ContainerRuntime class | (python, in runtime.py) | Detect runtime at startup, execute jobs in container | Established in Phase 110; exposes `.runtime` attribute |
| CgroupDetector class | (python, in node.py) | Detect cgroup v1/v2/unsupported | Already implemented Phase 123; execution mode follows same pattern |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | (from req.txt) | Heartbeat payload POST to orchestrator | Already used for all node-to-orchestrator mTLS communication |
| psutil | (from req.txt) | CPU/RAM metrics in heartbeat | Already collected in heartbeat payload (Phase 123) |

## Architecture Patterns

### Heartbeat Reporting Pattern (Reuse Phase 123)

Phase 123 established the pattern for runtime detection at startup → heartbeat reporting → DB persistence → API exposure. Phase 124 follows exactly the same pattern for execution mode:

```
Node Startup:
  1. runtime = ContainerRuntime().detect_runtime() → "docker" | "podman" | RuntimeError
  2. Store in module-level variable (like DETECTED_CGROUP_VERSION)

Heartbeat (every 30s):
  3. Include execution_mode in HeartbeatPayload dict
  4. POST to /heartbeat endpoint

Orchestrator (main.py receive_heartbeat):
  5. Parse HeartbeatPayload with execution_mode field
  6. Call job_service.handle_heartbeat(payload)

Job Service:
  7. Update node.execution_mode = payload.execution_mode
  8. Commit to DB

API (get_nodes):
  9. Return NodeResponse with execution_mode field
  10. Dashboard receives and renders Docker/Podman badge
```

### Compose Generator Pattern

The `GET /nodes/compose` endpoint currently:
1. Accepts optional `execution_mode` query param
2. Falls back to server's `NODE_EXECUTION_MODE` env var (default "auto")
3. Returns templated docker-compose.yaml with EXECUTION_MODE env var

Phase 124 hardening:
1. Validate `effective_execution_mode` early in the handler
2. If `execution_mode == "direct"`, reject with 400 + clear error message
3. If server's `NODE_EXECUTION_MODE == "direct"`, reject at startup or per-request
4. Return error: "direct mode not supported; use docker, podman, or auto"

### Database Schema Addition Pattern (From Phase 123)

```python
# In db.py Node model
execution_mode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

Migration (next available number, e.g., migration_vXX.sql):
```sql
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS execution_mode TEXT;
```

Backward compatibility: nullable + Optional in ORM = old nodes have NULL, new nodes populate on heartbeat.

## Established Patterns to Reuse

### 1. Module-Level Detection Caching
From `node.py` Phase 123:
```python
def _detect_cgroup_version() -> tuple[str, str]:
    """Run cgroup detection once at module load."""
    detector = CgroupDetector()
    version, raw_info = detector.detect()
    # Log + return
    return version, raw_info

DETECTED_CGROUP_VERSION, DETECTED_CGROUP_RAW = _detect_cgroup_version()
```

Phase 124 will do similar for execution mode (except it's already available from `ContainerRuntime().runtime`):
```python
# At module level in node.py
DETECTED_EXECUTION_MODE = node.runtime_engine.runtime  # "docker" or "podman"
```

Then include in heartbeat payload:
```python
payload = {
    # ... existing fields ...
    "execution_mode": DETECTED_EXECUTION_MODE,
}
```

### 2. Heartbeat Payload Extension (From Phase 123)
Phase 123 added `detected_cgroup_version` and `cgroup_raw` to HeartbeatPayload:
```python
class HeartbeatPayload(BaseModel):
    node_id: str
    hostname: str
    stats: Optional[Dict] = None
    # ... other fields ...
    detected_cgroup_version: Optional[str] = None  # Phase 123
    cgroup_raw: Optional[str] = None                # Phase 123
```

Phase 124 adds execution_mode the same way:
```python
class HeartbeatPayload(BaseModel):
    # ... existing fields including detected_cgroup_version ...
    execution_mode: Optional[str] = None  # NEW: Phase 124
```

### 3. DB Update in Heartbeat Handler (From Phase 123)
In `job_service.py`, the `handle_heartbeat()` function already updates cgroup fields:
```python
node.detected_cgroup_version = hb.detected_cgroup_version
node.cgroup_raw = hb.cgroup_raw
```

Phase 124 adds execution_mode update:
```python
node.execution_mode = hb.execution_mode
```

### 4. API Response Exposure (From Phase 123)
NodeResponse already exposes detected_cgroup_version:
```python
class NodeResponse(BaseModel):
    node_id: str
    hostname: str
    # ... other fields ...
    detected_cgroup_version: Optional[str] = None
```

Phase 124 adds execution_mode:
```python
class NodeResponse(BaseModel):
    # ... existing fields ...
    execution_mode: Optional[str] = None
```

And the `get_nodes()` endpoint already constructs the response with cgroup data:
```python
# In main.py get_nodes endpoint
"detected_cgroup_version": n.detected_cgroup_version,
```

Phase 124 adds:
```python
"execution_mode": n.execution_mode,
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting container runtime | Custom bash script probing /var/run/docker.sock, shutil.which(), etc. | Existing `ContainerRuntime.detect_runtime()` in runtime.py | Already handles docker/podman/auto fallback logic, returns clean string, integrated into node startup |
| Persisting heartbeat fields to Node table | Custom per-field update logic | Existing `job_service.handle_heartbeat()` pattern (Phase 123) | Already batches updates to avoid N+1, handles transactions, proven in production |
| Validating execution mode values | String matching on request | Pydantic `Literal["docker", "podman", "auto"]` in HeartbeatPayload | Type-safe, validates server-side, rejects unknowns automatically |
| Compose file templating | String concatenation or jinja2 | Existing f-string template in `get_node_compose()` | Already parameterized, integrates with existing endpoint, no new deps |

## Common Pitfalls

### Pitfall 1: Forgetting Phase 123's Startup Block
**What goes wrong:** Code assumes node.py can still be called with `EXECUTION_MODE=direct`, but Phase 123's `_check_execution_mode()` raises RuntimeError on import if this is set. If you add logic that depends on execution mode being detectable after startup, you'll fail.

**Why it happens:** `_check_execution_mode()` runs at module import time (line 142 in node.py), before Node class instantiation. Easy to miss if you only read heartbeat code.

**How to avoid:** Confirm line 142 of node.py is still there. Understand that this block means: any node currently online is guaranteed docker/podman (never direct). The execution_mode reported in heartbeat will never be "direct".

**Warning signs:** Tests pass but compose generator is called with direct mode and doesn't reject; node starts up with EXECUTION_MODE=direct (would fail immediately with RuntimeError).

### Pitfall 2: Null execution_mode in Dashboard
**What goes wrong:** Dashboard renders null/undefined execution_mode as empty space or crash, not as "unknown runtime".

**Why it happens:** Old nodes that haven't sent heartbeat yet have NULL in DB. NodeResponse returns None. Frontend doesn't expect null.

**How to avoid:** Add `?? "Unknown"` or fallback text in dashboard badge. Document that dashboard will show "Unknown" initially for nodes that haven't reported yet (expected — will update after first heartbeat).

**Warning signs:** Dashboard crashes on TypeError when rendering execution_mode; null values visible in node list instead of badge.

### Pitfall 3: Server Validation Timing
**What goes wrong:** Server accepts NODE_EXECUTION_MODE=direct at startup, but generates broken compose files. Operator doesn't know until node fails to boot.

**Why it happens:** Validation happens only in compose endpoint, not at startup. Decision: early validation vs late validation.

**How to avoid:** Decision from Claude's Discretion: validate either at server startup (reject with `sys.exit(1)` if NODE_EXECUTION_MODE=direct) OR per-request in compose endpoint (reject with 400). CONTEXT.md says "validate at generation time or server startup" — recommend startup to fail fast.

**Warning signs:** NODE_EXECUTION_MODE=direct set in server .env, server starts successfully, later compose generation fails.

### Pitfall 4: Dead Code at node.py:778
**What goes wrong:** Unreachable branch checking `execution_mode == "direct"` remains in code, suggesting it's still a supported path.

**Why it happens:** Phase 122 added the startup block but didn't clean up the conditional at line 778. Code review might miss it as "not causing bugs."

**How to avoid:** CONTEXT.md explicitly asks to remove this dead code. Search for all execution_mode conditionals and simplify: after startup block, you know execution is always docker/podman, so remove the conditional entirely.

**Warning signs:** Line 778 still has a branch for direct mode; code review comments ask "isn't this unreachable?"

### Pitfall 5: Confusing execution_mode with EXECUTION_MODE env var
**What goes wrong:** Heartbeat payload sends `execution_mode` (snake_case) but code elsewhere uses `EXECUTION_MODE` (env var). Easy to mix up.

**Why it happens:** Python convention is snake_case for vars/fields; env vars are UPPER_CASE.

**How to avoid:** Use consistent naming in code:
- `EXECUTION_MODE` = environment variable only (read from os.environ)
- `execution_mode` = heartbeat field, DB column, API response (lowercase)
- `runtime` = RuntimeEngine.runtime attribute (what `ContainerRuntime.detect_runtime()` returns)

**Warning signs:** Heartbeat field is named EXECUTION_MODE (should be snake_case); code mixes conventions.

## Code Examples

### Example 1: Heartbeat Payload with Execution Mode
**Source:** Existing heartbeat_loop() in node.py, extended with Phase 124 additions

```python
# In node.py, heartbeat_loop() function (around line 424)
payload = {
    "node_id": NODE_ID,
    "hostname": socket.gethostname(),
    "stats": stats,
    "tags": tags,
    "capabilities": caps,
    "env_tag": env_tag,
    "detected_cgroup_version": DETECTED_CGROUP_VERSION,  # Phase 123
    "cgroup_raw": DETECTED_CGROUP_RAW,                   # Phase 123
    "execution_mode": self.runtime_engine.runtime,        # Phase 124 NEW
}
```

**Why:** Includes execution_mode from the ContainerRuntime instance created at Node startup. The `.runtime` attribute is already available after `detect_runtime()` succeeds (or raises RuntimeError if no runtime found).

### Example 2: HeartbeatPayload Model Addition
**Source:** models.py HeartbeatPayload class (line 162)

```python
class HeartbeatPayload(BaseModel):
    node_id: str
    hostname: str
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict[str, str]] = None
    job_telemetry: Optional[Dict[str, Dict]] = None
    upgrade_result: Optional[Dict] = None
    env_tag: Optional[str] = None
    detected_cgroup_version: Optional[str] = None  # Phase 123
    cgroup_raw: Optional[str] = None                # Phase 123
    execution_mode: Optional[str] = None             # Phase 124 NEW

    @field_validator("env_tag", mode="before")
    @classmethod
    def normalize_env_tag(cls, v):
        return v.strip().upper() if isinstance(v, str) and v.strip() else None
```

**Why:** Optional + None default allows backward compatibility with nodes that haven't upgraded yet.

### Example 3: Compose Generator Validation
**Source:** main.py get_node_compose() endpoint (line 499)

```python
@app.get("/api/node/compose", tags=["System"])
@app.get("/api/installer/compose", tags=["System"])
async def get_node_compose(token: str, mounts: Optional[str] = None, tags: Optional[str] = None, execution_mode: Optional[str] = None):
    """Dynamic Compose File generator for Nodes."""
    effective_tags = tags if tags else "general,linux,arm64"
    effective_execution_mode = execution_mode or os.getenv("NODE_EXECUTION_MODE", "auto")

    # NEW: Phase 124 validation
    if effective_execution_mode == "direct":
        raise HTTPException(
            status_code=400,
            detail="EXECUTION_MODE=direct is not supported. Use 'docker', 'podman', or 'auto' instead."
        )

    compose_content = f"""
version: '3.8'
services:
  puppet:
    image: localhost:5000/puppet:latest
    environment:
      EXECUTION_MODE: {effective_execution_mode}
      # ... other env vars ...
"""
    return Response(content=compose_content, media_type="text/yaml")
```

**Why:** Early validation prevents broken compose files from being generated. Error message is actionable — tells operator exactly what to do.

### Example 4: Dead Code Removal
**Source:** node.py around line 778 (DEBT-04 reference)

**Before (unreachable after startup block):**
```python
execution_mode = os.getenv("EXECUTION_MODE", "auto").lower()
if execution_mode in ("docker", "podman", "auto"):
    # Stdin mode: pipe script content into the container
    # ...
elif execution_mode == "direct":
    # Direct execution mode (unreachable — startup block raises error)
    # Fall back to file mount for direct execution mode
    # ...
else:
    raise ValueError(f"Invalid EXECUTION_MODE: {execution_mode}")
```

**After (simplified):**
```python
# No need to check EXECUTION_MODE here — startup block guarantees docker/podman
# Stdin mode: pipe script content into the container
# (all code paths now assume container execution)
```

**Why:** Removes dead branch that confuses future readers. Clarifies that all code paths are container-based.

### Example 5: DB Column Migration
**Source:** migration_vXX.sql (next available number)

```sql
-- Phase 124: Server-side execution_mode visibility
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS execution_mode TEXT;
```

**Why:** Idempotent (IF NOT EXISTS prevents errors on re-runs). Simple text column (like detected_cgroup_version). Nullable because old nodes haven't reported it yet.

### Example 6: NodeResponse Extension
**Source:** models.py NodeResponse class (line 201)

```python
class NodeResponse(BaseModel):
    node_id: str
    hostname: str
    ip: str
    last_seen: datetime
    status: str
    base_os_family: Optional[str] = None
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict] = None
    expected_capabilities: Optional[Dict] = None
    tamper_details: Optional[str] = None
    stats_history: Optional[List[Dict]] = None
    env_tag: Optional[str] = None
    detected_cgroup_version: Optional[str] = None  # Phase 123
    execution_mode: Optional[str] = None             # Phase 124 NEW
```

**Why:** Exposes execution_mode to API consumers (dashboard). Optional allows partial rollout.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No runtime visibility | Node reports detected runtime in heartbeat | Phase 122 startup block; Phase 124 server-side persistence | Operator can now see what runtime each node is using; helps with troubleshooting |
| Compose generator accepts direct mode | Compose generator rejects direct mode with 400 | Phase 124 | Prevents operator from creating broken node configs; fail fast |
| Documentation references direct mode as production option | All docs updated to remove direct mode references | Phase 124 documentation sweep | No confusion about production vs legacy patterns |
| Dead code branch for direct execution | Code simplified to assume container execution | Phase 124 dead code removal | Cleaner codebase; future readers understand all execution is containerized |

**Deprecated/outdated:**
- `EXECUTION_MODE=direct` in production: Blocked at startup since Phase 122. Phase 124 adds server-side rejection + documentation removal.
- Direct mode troubleshooting guides in FAQ: Replaced with Docker socket mount guidance (use `EXECUTION_MODE=docker` or `auto` with proper mounts).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python backend) + vitest (React frontend) |
| Config file | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vitest.config.ts` (frontend) |
| Quick run command | `cd puppeteer && pytest tests/test_heartbeat.py -x` (if it exists) OR manual heartbeat POST test |
| Full suite command | `cd puppeteer && pytest` |

### Phase 124 Requirements → Test Map

| Requirement | Behavior | Test Type | Automated Command | Current Status |
|------------|----------|-----------|-------------------|----------------|
| EPHR-02: Direct mode blocked at compose generation | GET /nodes/compose?execution_mode=direct returns 400 | integration | `pytest tests/test_compose_validation.py -x` | Wave 0 gap |
| Server NODE_EXECUTION_MODE=direct validation | Server startup rejects NODE_EXECUTION_MODE=direct | integration | Manual test: `NODE_EXECUTION_MODE=direct pytest -x` (should exit 1) | Wave 0 gap |
| Heartbeat execution_mode persistence | Heartbeat with execution_mode updates DB node.execution_mode | unit | `pytest tests/test_job_service_heartbeat.py::test_execution_mode_persisted -x` | Wave 0 gap |
| NodeResponse includes execution_mode | GET /nodes returns execution_mode field in response | integration | `curl -H "Authorization: Bearer <token>" https://localhost:8001/nodes` + check JSON | Manual only (wave 0) |
| Node startup rejects EXECUTION_MODE=direct | Node.py exits with RuntimeError on EXECUTION_MODE=direct | unit | Manual: run node with env var set | Covered by existing _check_execution_mode() test |
| Dashboard renders execution_mode badge | Nodes.tsx shows Docker/Podman badge (phase 127) | e2e | Playwright test in mop_validation/scripts/test_playwright.py | Wave 0 gap (phase 127) |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_job_service_heartbeat.py -x` (heartbeat persistence test)
- **Per wave merge:** `cd puppeteer && pytest` (full backend suite) + manual compose validation
- **Phase gate:** Full backend test suite green + manual compose generation test (direct mode rejection)

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_heartbeat_execution_mode.py` — unit test for HeartbeatPayload execution_mode field parsing
- [ ] `puppeteer/tests/test_compose_validation.py` — integration test for compose generator direct-mode rejection
- [ ] `puppeteer/tests/test_job_service_heartbeat.py::test_execution_mode_persisted` — verify node.execution_mode updated on heartbeat
- [ ] `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx` — test execution_mode badge rendering (phase 127, depends on this phase)
- [ ] Server startup validation test: `NODE_EXECUTION_MODE=direct python -m agent_service.main` should fail with clear error
- [ ] Framework install: existing test infrastructure (pytest + vitest) already available

## Integration Points

### Node-Side (puppets/environment_service/node.py)
- Line 142: `_check_execution_mode()` already blocks direct mode at startup
- Line 480: `self.runtime_engine = runtime.ContainerRuntime()` — already instantiated, `.runtime` available
- Line 424-433: heartbeat payload dict — add `"execution_mode": self.runtime_engine.runtime`

### Backend Models (puppeteer/agent_service/)
- `models.py` line 162 HeartbeatPayload: add `execution_mode: Optional[str] = None`
- `models.py` line 201 NodeResponse: add `execution_mode: Optional[str] = None`
- `db.py` line 127 Node table: add `execution_mode: Mapped[Optional[str]]` column

### Backend Handlers (puppeteer/agent_service/main.py)
- Line 499-524: `get_node_compose()` endpoint — add direct-mode rejection
- Line 1649-1751: `get_nodes()` endpoint — already handles cgroup fields, will add execution_mode to dict
- Line 1668: `receive_heartbeat()` endpoint — already routes to job_service

### Job Service (puppeteer/agent_service/services/job_service.py)
- Line 944-950: `handle_heartbeat()` — add `node.execution_mode = hb.execution_mode` update

### Documentation
- `docs/docs/runbooks/faq.md` line 42-46: Remove EXECUTION_MODE=direct guidance; replace with Docker socket mount pattern
- `docs/docs/developer/architecture.md` line 583: Update EXECUTION_MODE env var table to remove `direct` from valid values
- `docs/docs/developer/architecture.md` line 434: Update diagram note to reflect container execution only
- `CLAUDE.md` line 179-184: Update Node Execution Modes section or link to updated docs

### Frontend (puppeteer/dashboard/src/views/Nodes.tsx)
- Add `execution_mode` rendering in node list and detail drawer (badges for Docker/Podman)
- This is part of Phase 127 (dashboard integration), but execution_mode data must be available from API first

## Sources

### Primary (HIGH confidence)
- **Context7 — FastAPI validation patterns:** Request/response models with Pydantic, HTTPException for 400 errors
- **Codebase Phase 123 pattern:** Exact implementation of detected_cgroup_version shows the pattern for heartbeat → DB → API
- **node.py _check_execution_mode():** Line 132-142, confirms startup block is in place
- **runtime.py ContainerRuntime:** Lines 10-30, shows detect_runtime() method and available runtimes
- **job_service.py handle_heartbeat():** Lines 944-950, shows how cgroup fields are updated

### Secondary (MEDIUM confidence)
- **CONTEXT.md Phase 124 decisions:** User decisions from /gsd:discuss-phase, locked design choices
- **REQUIREMENTS.md traceability:** EPHR-01, EPHR-02 requirements this phase addresses
- **Official docker-compose.yaml schema:** Compose version 3.8 format used in get_node_compose endpoint

### Tertiary (acknowledged patterns, not specific sources)
- Database migration pattern: IF NOT EXISTS idempotency (standard SQLAlchemy practice)
- Optional Pydantic fields for backward compatibility: Standard API versioning pattern
- Module-level variable caching for startup detection: Established in Phase 123 (cgroup detection)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All components (SQLAlchemy, FastAPI, Pydantic, httpx) are established in codebase, Phase 123 serves as exact pattern match
- Architecture: HIGH — Phase 123 cgroup detection established the heartbeat → DB → API pattern; execution mode follows identically
- Pitfalls: HIGH — _check_execution_mode() startup block is confirmed in code; dead code at line 778 identified; startup validation choice is clear from CONTEXT.md
- Integration points: HIGH — All locations identified in codebase with line numbers; changes are additive (no rewrites)

**Research date:** 2026-04-08
**Valid until:** 2026-04-15 (stable domain; patterns established in Phase 123)

**Certainty notes:**
- Startup block confirmed: _check_execution_mode() at line 142 of node.py exists and works
- Heartbeat already reports cgroup detection (Phase 123): Exact same pattern to follow for execution_mode
- Compose generator already templated: Integration point at line 499-524 is straightforward
- No breaking changes required: All additions are backward compatible (nullable DB columns, Optional Pydantic fields)

