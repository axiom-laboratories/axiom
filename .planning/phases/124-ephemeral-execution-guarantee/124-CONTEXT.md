# Phase 124: Ephemeral Execution Guarantee - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

All job code executes inside ephemeral containers, never directly on the node host. `EXECUTION_MODE=direct` is blocked, documented as unsupported, and verified end-to-end. Nodes report their detected runtime (docker/podman) in heartbeat for server-side visibility.

**Key context:** The startup hard-block (`_check_execution_mode()` in node.py:132) and removal of the `direct` branch from `runtime.py` were completed in v10.0 Phase 29. This phase focuses on server-side visibility, documentation cleanup, dead code removal, compose generator hardening, and formal verification.

</domain>

<decisions>
## Implementation Decisions

### Server-side awareness
- Nodes report detected execution mode (docker/podman) in every heartbeat — consistent with cgroup detection pattern from Phase 123
- New `execution_mode` column on Node table (String, nullable) — stores the value from heartbeat
- New field on HeartbeatPayload (`Optional[str] = None`) — backward compatible with old nodes
- Orchestrator updates DB column on every heartbeat, same as cgroup fields
- `execution_mode` exposed in NodeResponse API model so dashboard can consume it
- Dashboard shows Docker/Podman badge in node list AND detail drawer — consistent with planned cgroup badge (Phase 127)
- No UNSAFE badge needed — direct mode is hard-blocked at startup, so a node that's online is guaranteed to be using a container runtime

### Compose generator hardening
- `GET /nodes/compose` rejects `execution_mode=direct` with HTTP 400 and clear error message — fail at generation time, not at node boot
- Server's own `NODE_EXECUTION_MODE` env var validated too — if set to `direct`, reject at generation time (or server startup) since all generated configs would be broken
- All other execution mode values (docker, podman, auto) remain valid

### Documentation cleanup
- Full sweep of all docs/ for stale `EXECUTION_MODE=direct` references — remove or update every occurrence
- FAQ (docs/runbooks/faq.md): replace `direct` mode DinD guidance with Docker socket mount guidance — mount host Docker socket and use `EXECUTION_MODE=docker` or `auto`
- Architecture docs (docs/developer/architecture.md): remove `direct` from the valid values table
- Node validation runbook: update DinD references
- CLAUDE.md: update Full-Stack Validation section to remove direct-mode references

### Dead code removal
- Remove dead `execution_mode` check at node.py:778 — unreachable since startup blocks direct mode. Simplify: all execution always goes through container runtime stdin path
- Improve RuntimeError message in runtime.py:27 (no runtime found) — add actionable guidance: "Rebuild this image with a Docker or Podman runtime, or mount the host Docker socket"

### Migration
- Migration SQL (next available number) with `ALTER TABLE nodes ADD COLUMN IF NOT EXISTS execution_mode TEXT`
- Follows established pattern from Phase 120/123 migrations

### Claude's Discretion
- Exact heartbeat field name (e.g. `execution_mode` vs `detected_execution_mode`)
- Migration file numbering
- Badge styling and placement details in Nodes.tsx
- SERVER_EXECUTION_MODE validation timing (startup vs per-request)

</decisions>

<specifics>
## Specific Ideas

No specific requirements beyond what was discussed. Key references: Phase 123's cgroup heartbeat pattern is the model for execution mode reporting. Phase 29 (v10.0) summary documents the original direct-mode removal.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_check_execution_mode()` at `node.py:132` — startup guard already exists, hard-blocks direct mode
- `ContainerRuntime.detect_runtime()` at `runtime.py:15` — already resolves docker/podman/auto, returns the detected runtime string
- `heartbeat_loop()` at `node.py:288` — already builds payload dict; add execution_mode field here (same pattern as cgroup fields from Phase 123)
- `HeartbeatPayload` at `models.py:162` — add Optional[str] field (same pattern as `detected_cgroup_version`)
- `Node` table at `db.py:127` — add nullable String column (same pattern as `detected_cgroup_version`)
- `NodeResponse` at `models.py` — add field for API exposure

### Established Patterns
- Heartbeat → DB column → API response → dashboard badge (cgroup detection in Phase 123 is the exact pattern)
- Migration SQL with `IF NOT EXISTS` for idempotency
- `Optional[str] = None` for backward-compatible heartbeat fields
- Module-level detection cached in global variable (NODE_ID, cgroup detection)

### Integration Points
- `node.py:335-342` — heartbeat payload dict; add execution_mode from `self.runtime_engine.runtime`
- `main.py:1668` — receive_heartbeat endpoint; update `node.execution_mode`
- `job_service.py` — heartbeat handler; add column update
- `main.py:501` — `get_node_compose()` endpoint; add direct-mode rejection
- `Nodes.tsx` — node list and detail drawer; add runtime badge
- `docs/runbooks/faq.md:42-46` — primary stale reference to update
- `docs/developer/architecture.md:583` — secondary stale reference

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 124-ephemeral-execution-guarantee*
*Context gathered: 2026-04-08*
