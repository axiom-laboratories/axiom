# Phase 166: Router Modularization - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor `puppeteer/agent_service/main.py` (3,828 lines, ~89 routes) into 6 domain-specific `APIRouter` modules. All route paths, response models, middleware behaviour, and test coverage must remain identical after the refactor. No feature work, no API changes, no new capabilities.

</domain>

<decisions>
## Implementation Decisions

### Router structure
- **D-01:** Create exactly **6 CE routers** — do NOT create a `foundry_router` (foundry is EE-only; `/api/foundry` is already handled entirely by `ee/routers/foundry_router.py` and is an EE-only prefix).
- **D-02:** Router-to-domain mapping:

  | Router file | Tag groups absorbed |
  |-------------|---------------------|
  | `auth_router.py` | Authentication |
  | `jobs_router.py` | Jobs, Job Definitions, Job Templates, CI/CD Dispatch |
  | `nodes_router.py` | Nodes, Node Agent |
  | `workflows_router.py` | Workflows |
  | `admin_router.py` | Admin, Signatures, Alerts & Webhooks, Headless Automation |
  | `system_router.py` | System, Health, Schedule |

  All routers live in `puppeteer/agent_service/routers/`.

### main.py residual shape
- **D-03:** After extraction, `main.py` becomes a **pure shell**: FastAPI app creation, lifespan function, middleware registration (`CORSMiddleware`, `LicenceExpiryGuard`, rate limiter), `include_router` calls, and static file mounts only.
- **D-04:** The WebSocket `/ws` endpoint must move out of `main.py` into a router (the most natural home is `system_router.py`). Zero route handlers remain in `main.py`.

### CE smelter_router wiring
- **D-05:** The existing `routers/smelter_router.py` (CE) exists but is not wired in — the 2 CE smelter routes are currently inline in `main.py`. Phase 166 **wires in** the CE `smelter_router.py` and removes the inline duplicate routes. The smelter router is mounted via `include_router` like any other CE router.

### Behavior equivalence standard
- **D-06:** Equivalence verification = **OpenAPI schema diff + full pytest suite**. Export the OpenAPI JSON before refactor and after; do a structural diff (routes, methods, path params, response models). Run the full `pytest` suite with no new failures. This is the pass bar for Plan 03 and Plan 04.
- **D-07:** No request-level smoke test per route required beyond what pytest already covers.

### Claude's Discretion
- Exact router prefix strategy (whether routers use `prefix=""` with full paths inline, or a shared prefix with sub-paths — match whatever pattern `ee/routers/` uses for consistency)
- WebSocket router file placement (system_router.py or a minimal ws_router.py)
- Import ordering and circular-import mitigation within each router file (follow the established `deps.py` pattern)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing router pattern to follow
- `puppeteer/agent_service/routers/smelter_router.py` — the one existing CE router; use its import structure and APIRouter instantiation as the template
- `puppeteer/agent_service/ee/routers/foundry_router.py` — EE router example showing how routers integrate with deps.py and the EE interface pattern

### Shared dependency layer
- `puppeteer/agent_service/deps.py` — `get_current_user`, `require_permission`, `audit` — all routers import from here, not from `main.py`

### App setup to preserve
- `puppeteer/agent_service/main.py` lines 447–515 — FastAPI app creation, lifespan, middleware stack, EE router injection pattern — this block stays in main.py, everything else moves out

### Test infrastructure
- `puppeteer/tests/conftest.py` — imports `from agent_service.main import app`; this import must remain valid after refactor (app still exported from main.py)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `routers/smelter_router.py`: existing CE router file — wire this in rather than recreating
- `ee/routers/` (10 EE routers): fully working examples of the router pattern to follow
- `deps.py`: shared auth/permission/audit helpers — already the standard import point for all new routers

### Established Patterns
- EE routers use `APIRouter()` with no prefix (full paths inline), `Depends(require_permission(...))` per route
- `deps.py` was extracted specifically to break the circular import between `main.py` and EE routers — CE routers follow the same pattern
- `conftest.py` imports `app` from `agent_service.main` — this must not break

### Integration Points
- `app.include_router(...)` calls in `main.py` are the sole wiring point for CE routers
- `LicenceExpiryGuard` middleware checks `EE_PREFIXES` — adding new CE router prefixes does NOT require updating this list (CE routes are not EE-gated)
- EE router injection happens at lifespan startup via `app.state` — CE routers are registered at module load time via `include_router`, which is different and must remain so

</code_context>

<specifics>
## Specific Ideas

- The roadmap names `foundry_router` in Plan 02 — this is a planning artifact. There are zero CE foundry routes in `main.py` (confirmed by grep). Do not create a CE `foundry_router`.
- The roadmap's plan count (4 plans) can remain as-is with adjusted scope: Plan 01 = auth/jobs/nodes/workflows routers, Plan 02 = admin/system routers + smelter wiring, Plan 03 = OpenAPI diff verification, Plan 04 = full pytest validation.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 166-router-modularization*
*Context gathered: 2026-04-18*
