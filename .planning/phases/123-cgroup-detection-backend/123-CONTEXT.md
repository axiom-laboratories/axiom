# Phase 123: Cgroup Detection Backend - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Node detects cgroup v1 vs v2 vs unsupported at startup and reports the detected version in every heartbeat. Orchestrator stores the cgroup version (and raw detection info) on the Node table for downstream dashboard consumption (Phase 127).

</domain>

<decisions>
## Implementation Decisions

### Value representation
- Three possible values: `v1`, `v2`, `unsupported`
- Hybrid cgroup setups (some controllers on v1, some on v2) report as `v1` — conservative, triggers amber warning path
- Unreadable /proc or /sys (permission denied, restricted container) returns `unsupported`
- Field named `detected_cgroup_version` across DB column, HeartbeatPayload, and heartbeat JSON key — distinguishes from a hypothetical future "required" or "expected" cgroup version
- DB column default is null (not "unsupported") — clean distinction between "never reported" and "detected unsupported"

### Detection approach
- Detect from the container's own perspective using filesystem paths only (/proc/self/cgroup, /sys/fs/cgroup/cgroup.controllers)
- What the container sees IS what governs job containers it spawns — correct semantic for Docker-in-Docker
- No cross-referencing with container runtime (docker info, podman info) — keep detection orthogonal to runtime config
- runtime.py already handles --cgroup-manager=cgroupfs for Podman separately

### Raw detection info
- Store raw detection data (e.g. /proc/self/cgroup contents, detection reasoning) in a separate `cgroup_raw` DB column (Text, nullable)
- Useful for debugging detection mismatches in Docker-in-Docker and restricted environments
- Raw data sent in heartbeat alongside version string — keeps node stateless

### Startup behavior
- Detection runs once at module load (cached in module-level variable) — consistent with NODE_ID resolution pattern
- `logger.info` for v1 and v2 detections; `logger.warning` for unsupported
- Startup log includes version + brief reason: e.g. "Detected cgroup: v2 (cgroup.controllers found at /sys/fs/cgroup/)"
- Nodes with unsupported cgroups still accept and execute jobs — detection is informational, not blocking. Operator risk decision. Phase 127 dashboard handles warnings.

### Heartbeat integration
- `detected_cgroup_version` and `cgroup_raw` sent in every heartbeat — simple, stateless, no "first heartbeat" tracking
- Both fields optional on HeartbeatPayload (`Optional[str] = None`) — backward compatible with old nodes that don't send them
- Orchestrator updates both DB columns unconditionally on every heartbeat — consistent with how stats/tags are updated, no change-detection needed

### Migration
- Two new columns on Node table: `detected_cgroup_version` (String, nullable) and `cgroup_raw` (Text, nullable)
- Migration SQL follows existing pattern: `ALTER TABLE nodes ADD COLUMN IF NOT EXISTS ...`

### Claude's Discretion
- CgroupDetector class design vs simple function
- Exact /proc and /sys parsing logic for v1/v2 detection
- Raw data format (full /proc contents vs summarized)
- Test fixture design for mocking /proc and /sys paths

</decisions>

<specifics>
## Specific Ideas

No specific requirements — standard Linux cgroup detection following Kubernetes/systemd patterns. Key references: /proc/self/cgroup format (v1: hierarchy IDs with controller names; v2: single `0::` entry), /sys/fs/cgroup/cgroup.controllers existence (v2 indicator).

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `heartbeat_loop()` at `node.py:288` — already builds payload dict with stats, tags, capabilities, env_tag; add detected_cgroup_version and cgroup_raw here
- `HeartbeatPayload` at `models.py:162` — add two new Optional[str] fields
- `Node` table at `db.py:127` — add two new nullable columns
- `runtime.py:67` — already has `--cgroup-manager=cgroupfs` Podman flag (related but separate concern)
- `_load_or_generate_node_id()` pattern — module-level detection + caching, reuse this pattern for cgroup detection

### Established Patterns
- Module-level detection cached in global variable (NODE_ID pattern in node.py)
- HeartbeatPayload optional fields with None default (env_tag, upgrade_result)
- Node table nullable String columns for optional metadata (machine_id, template_id, env_tag)
- Migration SQL with IF NOT EXISTS for idempotency

### Integration Points
- `node.py:335-342` — heartbeat payload dict construction; add cgroup fields here
- `main.py:1668` — receive_heartbeat endpoint; update node.detected_cgroup_version and node.cgroup_raw
- `job_service.py` — receive_heartbeat implementation; add column updates
- `models.py` — NodeResponse needs detected_cgroup_version for Phase 127 dashboard consumption

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 123-cgroup-detection-backend*
*Context gathered: 2026-04-08*
