# Phase 66: Backend Code Fixes - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Verify and complete all node image and compose fixes; CE-gate all execution routes via EE stub. Covers CODE-01 through CODE-04. No new features — this phase makes existing infrastructure correct and enforces the CE/EE API boundary for Execution History.

</domain>

<decisions>
## Implementation Decisions

### CODE-01: Docker CLI binary (verify only)
- `COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker` is already present in Containerfile.node
- No code change needed — planner should document as confirmed-done and include a verification step (docker build + `docker --version` inside container)

### CODE-02: /tmp bind mount (verify only)
- `/tmp:/tmp` is already present in compose.cold-start.yaml for both puppet-node-1 and puppet-node-2
- No code change needed — planner should document as confirmed-done

### CODE-03: PowerShell arm64 platform guard
- Use `ARG TARGETARCH` (BuildKit automatic arg) with a shell conditional in the RUN block
- When `TARGETARCH=arm64` (or `aarch64`), download the `_arm64.deb` from GitHub releases; otherwise download `_amd64.deb`
- PowerShell version stays hardcoded at 7.6.0 in the CE Containerfile — EE can pin a preferred version via Foundry
- Single-stage Containerfile (no multi-stage split for this)

### CODE-04: CE-gate execution routes
- Remove all 7 execution-related routes from main.py:
  - `GET /api/executions`
  - `GET /api/executions/{id}`
  - `GET /api/executions/{id}/attestation`
  - `GET /jobs/{guid}/executions`
  - `PATCH /api/executions/{exec_id}/pin`
  - `PATCH /api/executions/{exec_id}/unpin`
  - `GET /api/jobs/{guid}/executions/export`
- Create `ee/interfaces/executions.py` with `execution_stub_router` — same pattern as `foundry.py` (one stub handler per route, shared `_EE_RESPONSE` returning 402)
- Add `execution_stub_router` to `_mount_ce_stubs` in `ee/__init__.py`
- Add `executions: bool = False` field to `EEContext` dataclass
- Create `ee/routers/executions_router.py` with the real implementation (moved from main.py), for the EE plugin to load

### test_ce_smoke.py updates
- Update `test_ce_features_all_false` to include `"executions"` in the `ee_flags` list
- Update `test_ce_stub_routers_return_402` to import and call all 7 execution stub handlers, asserting each returns 402
- The `test_ce_table_count` assertion stays at 13 — `execution_records` is a CE table (CE nodes store execution data; the API to view it is EE)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ee/interfaces/foundry.py`: Direct template for the new `ee/interfaces/executions.py` stub — same `_EE_RESPONSE`, same stub handler pattern
- `ee/__init__.py` `_mount_ce_stubs()`: Just needs `execution_stub_router` imported and `app.include_router()`'d
- `EEContext` dataclass: Add `executions: bool = False` alongside existing flags

### Established Patterns
- CE stub pattern: `stub_router = APIRouter(tags=[...])`, `_EE_RESPONSE = JSONResponse(status_code=402, ...)`, one `async def` per route returning `_EE_RESPONSE`
- EE plugin loading: Entry point group `axiom.ee`; plugin calls `plugin.register(ctx)` which mounts real routers
- test_ce_smoke.py: Calls stub handler functions directly (not ASGI) because `ASGITransport` doesn't trigger lifespan; test pattern is `resp = await handler(); assert resp.status_code == 402`

### Integration Points
- `main.py`: 7 execution routes to be removed
- `ee/__init__.py`: `_mount_ce_stubs` and `EEContext`
- `puppeteer/agent_service/tests/test_ce_smoke.py`: Existing file to update (not create)
- `puppets/Containerfile.node`: RUN block with wget PowerShell download — add `ARG TARGETARCH` before `RUN apt-get update`

</code_context>

<specifics>
## Specific Ideas

- PowerShell version 7.6.0 stays hardcoded in CE Containerfile; EE Foundry handles version flexibility for enterprise builds
- The `execution_records` table stays in CE Base.metadata — CE nodes record job execution data locally; the EE API just gates the ability to query it remotely
- The 13-table CE count in `test_ce_table_count` does not change

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 66-backend-code-fixes*
*Context gathered: 2026-03-25*
