# Phase 52: Queue Visibility, Node Drawer and DRAINING - Research

**Researched:** 2026-03-23
**Domain:** FastAPI backend (new endpoints + DB column) + React/TypeScript frontend (new Queue view, Node drawer, live WebSocket patches)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Queue view (VIS-02)**
- New `/queue` route with its own sidebar nav entry (positioned after Jobs in the nav)
- Read-only monitoring layout — no GuidedDispatchCard, focused on queue state
- Shows PENDING + ASSIGNED + RUNNING + recently terminal jobs (COMPLETED/FAILED/CANCELLED)
- Adjustable recency window for terminal jobs: dropdown with 1h / 6h / 24h options
- PENDING jobs in the queue show a diagnosis callout inline (see VIS-01 below)
- DRAINING node status visible as a badge on affected jobs
- Live updates via WebSocket (same `useWebSocket` hook already in Jobs.tsx and Nodes.tsx)

**PENDING diagnosis (VIS-01)**
- Location: callout section at the top of the existing job detail drawer (Phase 51's `JobDetailPanel`) when job is PENDING
- Backend endpoint: `GET /jobs/{guid}/dispatch-diagnosis` — backend computes with full node state + queue position; frontend just displays the result
- Diagnosis cases surfaced:
  - No nodes currently ONLINE
  - Capability mismatch — nodes are online but none match required capabilities (show which capability is missing)
  - All eligible nodes busy — capable nodes exist but all are at concurrency limit; show queue position ("Queue position: 3")
  - Target node offline or DRAINING — job targets a specific node that is unavailable
- Live refresh: diagnosis updates via WebSocket when node state changes (no polling)

**Node detail drawer (VIS-03)**
- Trigger: click anywhere on a node row in the Nodes view (consistent with Jobs.tsx pattern)
- Sheet drawer (right-side), following established Phase 51 / Jobs.tsx pattern
- Contents:
  - Currently running job (link to job detail)
  - Jobs eligible for this node — all PENDING jobs that match this node's capabilities + targeting (full eligibility check)
  - Recent execution history — all jobs that ran on this node in the past 24 hours
  - Node's reported capabilities displayed as chip/badge list (reuses existing chip pattern)
  - Drain / Un-drain action button (admin only — see DRAINING section)

**DRAINING mechanics (VIS-04)**
- Who can drain: admin only (`nodes:write` permission, admin bypass)
- Enforcement: `job_service.py` node selection loop skips DRAINING nodes
- Auto-transition: when the last running job on a DRAINING node completes, node automatically transitions to OFFLINE
- Un-drain: admin can return DRAINING node to ONLINE via Un-drain action in node detail drawer
- Backend endpoints needed: `PATCH /nodes/{id}/drain` and `PATCH /nodes/{id}/undrain`
- Visibility: DRAINING status shows as a badge in both Nodes view and Queue view

### Claude's Discretion
- Exact wording of diagnosis messages (plain English)
- Queue view column layout and density
- Whether the `dispatch-diagnosis` endpoint is polled once on drawer open then patched via WebSocket, or fetched fresh on each WebSocket event
- Exact animation/transition when the Drain button transforms to Un-drain
- Whether the node drawer's "eligible jobs" list links back to the Queue view or opens the job detail drawer inline

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIS-01 | PENDING job drawer shows plain-English dispatch diagnosis (no nodes / capability mismatch / all busy / queue position) that updates live via WebSocket | `GET /jobs/{guid}/dispatch-diagnosis` backend endpoint; diagnosis logic mirrors `pull_work` node selection loop in `job_service.py`; frontend patches via `job:updated` or new `node:heartbeat` WebSocket events |
| VIS-02 | Dedicated live Queue dashboard view (PENDING/RUNNING/recently completed) — WebSocket-driven, no polling | New `Queue.tsx` view + `/queue` route; `GET /jobs` endpoint already supports status filtering; queue-specific variant using multi-status filter or dedicated endpoint; sidebar nav addition |
| VIS-03 | Nodes page per-node detail drawer (running job, queued jobs, recent history, reported capabilities) | New `GET /nodes/{id}/detail` backend endpoint aggregating current job, eligible PENDING jobs, 24h history; Radix `Sheet` component already used in Jobs.tsx; click handler on node rows |
| VIS-04 | Admin can DRAINING a node from node detail drawer; DRAINING visible in Queue and Nodes views; no new jobs dispatched to DRAINING node | `PATCH /nodes/{id}/drain` + `PATCH /nodes/{id}/undrain` endpoints; `Node.status` DB column gains DRAINING as valid value; `migration_v42.sql` for existing Postgres deployments; `job_service.py` node selection skips DRAINING |
</phase_requirements>

---

## Summary

Phase 52 is a pure operational visibility and control improvement with no new job submission mechanics. It spans four coordinated concerns: (1) a backend diagnosis endpoint that introspects why a specific PENDING job hasn't dispatched, (2) a new read-only Queue view aggregating active and recent terminal jobs, (3) a Node detail drawer surfacing per-node runtime context, and (4) the DRAINING node state lifecycle.

All four concerns integrate with existing infrastructure. The diagnosis endpoint mirrors the existing `pull_work` node selection loop in `job_service.py` — it reads the same node state and job requirements to produce human-readable output rather than actually assigning work. The Queue view reuses the existing `GET /jobs` endpoint and `useWebSocket` hook already wired in Jobs.tsx. The Node drawer follows the exact Sheet+row-click pattern established in Phase 51's `JobDetailPanel`. DRAINING adds one column value to `Node.status`, one exclusion clause to the node selection loop, and a migration SQL for existing Postgres deployments.

The highest complexity item is the dispatch diagnosis endpoint: it must faithfully replicate the eligibility logic from `pull_work` (tag matching, capability version comparison, env_tag isolation, concurrency limits) without refactoring that function. The safest approach is to extract shared eligibility helpers so the diagnosis endpoint and `pull_work` both call the same code rather than duplicating the matching rules.

**Primary recommendation:** Extract node eligibility helpers from `pull_work` into `JobService` static methods; the diagnosis endpoint and pull_work both call them. Do NOT duplicate the matching logic.

---

## Standard Stack

### Core — already in the project, no new dependencies needed

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | installed | New backend endpoints | Already the API framework |
| SQLAlchemy (async) | installed | DB queries for diagnosis + node detail | Already the ORM |
| Radix UI Sheet | installed | Node detail drawer | Same component used in Jobs.tsx |
| React + TypeScript | installed | Queue.tsx + node drawer | Project stack |
| `useWebSocket` hook | project | Live updates | Already wired in Jobs.tsx, Nodes.tsx |
| `@tanstack/react-query` | installed | Data fetching | Already used in Nodes.tsx |
| `recharts` | installed | (existing sparklines) | No new charting needed for this phase |

### No New Dependencies

This phase requires zero new npm packages or Python packages. All patterns and components are already present in the codebase.

---

## Architecture Patterns

### Recommended Project Structure — new files

```
puppeteer/
├── migration_v42.sql               # ADD COLUMN status DRAINING support (Postgres IF NOT EXISTS guard)
└── agent_service/
    ├── main.py                     # 4 new endpoints (diagnosis, drain, undrain, node-detail)
    └── services/
        └── job_service.py          # _node_eligible() helper extracted; diagnosis logic added

puppeteer/dashboard/src/
├── views/
│   └── Queue.tsx                   # New VIS-02 view
├── AppRoutes.tsx                   # Add /queue route
└── layouts/
    └── MainLayout.tsx              # Add Queue nav item after Jobs
```

`Nodes.tsx` gains a drawer state + row click handler inline (no separate file needed, consistent with how Jobs.tsx embeds `JobDetailPanel`).

### Pattern 1: Dispatch Diagnosis Endpoint

**What:** `GET /jobs/{guid}/dispatch-diagnosis` reads full node state and the job's requirements, then returns a structured result with a `reason` enum and a `message` string.

**When to use:** Called by the frontend once when a PENDING job drawer opens, then re-fetched (or result patched) whenever a relevant WebSocket event arrives (`node:heartbeat`, `job:updated`).

**Implementation approach:**
```python
# Source: existing pull_work logic in job_service.py (lines 550-610)
# Extract reusable helper:

@staticmethod
def _node_is_eligible(node: Node, job: Job, node_tags: list, node_caps_dict: dict) -> bool:
    """Returns True if this node could accept this job under current conditions.
    Mirrors the guard logic in pull_work without side effects."""
    # ... tag check, env_tag check, capability version check ...

@staticmethod
async def get_dispatch_diagnosis(guid: str, db: AsyncSession) -> dict:
    """Returns {reason, message, queue_position} for a PENDING job."""
    # 1. Load job
    # 2. Load all ONLINE nodes
    # 3. If no ONLINE nodes: reason="no_nodes_online"
    # 4. Filter by eligibility: if none eligible: reason="capability_mismatch", detail missing cap
    # 5. Check concurrency on eligible nodes: if all at limit: reason="all_nodes_busy", queue_position=N
    # 6. If job has target_node_id and that node is OFFLINE/DRAINING: reason="target_node_unavailable"
    # 7. Happy path (job WILL dispatch next cycle): reason="pending_dispatch"
```

**Queue position calculation:** Count PENDING/RETRYING jobs with `created_at < this_job.created_at` that match any of the eligible nodes. This is a best-effort count, not a reserved slot — make the wording appropriately hedged ("ahead in queue: approximately 3").

### Pattern 2: Node Detail Aggregation Endpoint

**What:** `GET /nodes/{node_id}/detail` returns a compound object with current running job, eligible pending jobs, 24h execution history, and capabilities.

**Response shape:**
```python
{
  "running_job": JobResponse | None,           # ASSIGNED job on this node
  "eligible_pending_jobs": List[JobResponse],  # PENDING jobs this node could accept
  "recent_history": List[dict],                # last 24h completed/failed jobs via ExecutionRecord
  "capabilities": dict,                        # node.capabilities parsed
}
```

**Query efficiency:** Four focused queries, not a join. The eligible pending jobs query runs the same `_node_eligible()` helper over the first N PENDING jobs (cap at 50 to avoid full-table scan).

### Pattern 3: DRAINING Status Lifecycle

**What:** A new valid value for `Node.status`. The DB column is a plain String — no enum constraint — so no schema change beyond documenting the new value. The migration SQL guards for Postgres deployments where the `nodes` table already exists.

**Enforcement points:**
1. `pull_work` in `job_service.py` — add `node.status == "DRAINING"` to the existing early-return guard alongside `"TAMPERED"`
2. `receive_heartbeat` — a DRAINING node should NOT be promoted back to ONLINE by heartbeat; the heartbeat still updates `last_seen` (keeps node alive) but must not change status when DRAINING
3. `list_nodes` in `main.py` — the offline detection logic currently overwrites status with OFFLINE if last_seen > 60s. It must NOT overwrite DRAINING → OFFLINE (the node is intentionally draining, not absent)
4. Auto-transition in `report_result` — after a job result arrives, check: if the node is DRAINING and has zero ASSIGNED jobs remaining, set `node.status = "OFFLINE"` and broadcast `node:updated`

**CRITICAL: list_nodes offline detection override.** Current code (main.py ~line 1481):
```python
is_offline = (datetime.utcnow() - n.last_seen).total_seconds() > 60
node_status = "OFFLINE" if is_offline else "ONLINE"
```
This wipes any persistent status. The fix is:
```python
if n.status in ("REVOKED", "TAMPERED", "DRAINING"):
    node_status = n.status
else:
    is_offline = (datetime.utcnow() - n.last_seen).total_seconds() > 60
    node_status = "OFFLINE" if is_offline else "ONLINE"
```

**Frontend:** `Nodes.tsx` Node interface currently types `status` as `'ONLINE' | 'OFFLINE' | 'BUSY' | 'REVOKED' | 'TAMPERED'` — add `'DRAINING'` to the union.

### Pattern 4: Queue.tsx View

**What:** Read-only table view of PENDING + ASSIGNED + RUNNING + recently terminal jobs. Uses the existing `GET /jobs` endpoint with a multi-status filter approach.

**Implementation options (Claude's discretion):**
- Option A: Single request with no status filter + client-side partition — simpler but loads all jobs
- Option B: Separate requests for active (PENDING/ASSIGNED/RUNNING) and terminal (COMPLETED/FAILED/CANCELLED with `date_from` filter) — matches the 1h/6h/24h time window cleanly
- **Recommended:** Option B — the time-window dropdown maps cleanly onto `date_from` for terminal jobs only; active jobs always shown in full.

**Live update pattern (mirrors Jobs.tsx):**
```typescript
// Source: Jobs.tsx useWebSocket pattern (established Phase 49/50)
useWebSocket((event, data) => {
    if (event === 'job:created' || event === 'job:updated') {
        queryClient.invalidateQueries({ queryKey: ['queue'] });
        // OR: patch in-place for status updates — same as Jobs.tsx
    }
    if (event === 'node:heartbeat') {
        // May trigger diagnosis refresh for PENDING jobs in the drawer
    }
});
```

### Pattern 5: Node Drawer in Nodes.tsx

**What:** Right-side Sheet that opens on node row click, showing the aggregated detail from `GET /nodes/{id}/detail`.

**State shape (minimal, follows Jobs.tsx JobDetailPanel pattern):**
```typescript
const [selectedNode, setSelectedNode] = useState<Node | null>(null);
const [nodeDrawerOpen, setNodeDrawerOpen] = useState(false);
// ...
<TableRow onClick={() => { setSelectedNode(n); setNodeDrawerOpen(true); }} className="cursor-pointer" />
```

### Anti-Patterns to Avoid

- **Duplicating the eligibility logic:** Don't copy-paste the tag/capability matching from `pull_work` into the diagnosis endpoint. Extract a shared helper first.
- **DRAINING overwriting heartbeat status:** The heartbeat handler must NOT call `node.status = "ONLINE"` unconditionally. It only updates `last_seen`.
- **list_nodes overwriting DRAINING:** The offline detection in `list_nodes` must be guarded to preserve DRAINING status (see Pattern 3 above — this is a critical correctness point).
- **Queue view polling:** Never use `setInterval` / `refetchInterval` for the Queue view. WebSocket events must drive invalidation. The `useWebSocket` hook already handles reconnection.
- **Full eligible-jobs scan:** The `eligible_pending_jobs` list in the node detail endpoint must be capped (e.g. limit 50 PENDING jobs evaluated) to avoid a full table scan on large deployments.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Right-side drawer | Custom overlay/modal | Radix `Sheet` (already imported in Jobs.tsx) | Handles focus trap, animation, backdrop, keyboard close |
| Tag/capability chip display | Custom span elements | Existing Badge component pattern from Phase 49/51 | Consistent styling, zero new code |
| WebSocket live updates | `setInterval` polling | `useWebSocket` hook (already in both Jobs.tsx and Nodes.tsx) | Auto-reconnect, exponential back-off, keepalive ping already built in |
| Amber callout box | Custom div styling | Reuse amber callout pattern from Phase 48 (DRAFT warning) / Phase 51 (SECURITY_REJECTED) | Consistent UX language |
| Queue position count | Complex window query | Simple `SELECT count(*) WHERE status IN ('PENDING','RETRYING') AND created_at < this_job.created_at` | Exact semantics, fast with index on created_at |

---

## Common Pitfalls

### Pitfall 1: list_nodes Offline Detection Overwrites DRAINING
**What goes wrong:** The `list_nodes` route computes `node_status` from `last_seen` timestamp, ignoring the persisted DB value. A DRAINING node that is still heartbeating (normal — it's running jobs) would appear ONLINE in the API response, and a DRAINING node that goes quiet would appear OFFLINE.
**Why it happens:** Status is not persisted as authoritative in the current `list_nodes` — it's recomputed from heartbeat freshness. REVOKED is handled specially, but DRAINING is not.
**How to avoid:** Add DRAINING (and TAMPERED) to the guard that bypasses the freshness check. See Pattern 3 above for the exact code fix.
**Warning signs:** Frontend shows ONLINE badge instead of DRAINING badge on a node that was just drained.

### Pitfall 2: Heartbeat Clears DRAINING
**What goes wrong:** `receive_heartbeat` currently sets `node.status = "ONLINE"` (or equivalent). If a DRAINING node heartbeats, its status would be overwritten and the drain would be silently undone.
**Why it happens:** The heartbeat handler is designed to mark nodes online. DRAINING was not a concept when it was written.
**How to avoid:** In `receive_heartbeat`, only update status to ONLINE if `node.status not in ("DRAINING", "TAMPERED", "REVOKED")`.
**Warning signs:** DRAINING badge disappears from the UI a few seconds after the drain action.

### Pitfall 3: Auto-Transition Race Condition
**What goes wrong:** The auto-transition DRAINING → OFFLINE (when last running job completes) must check the ASSIGNED job count AFTER the result has been committed. If the check runs before commit, it will still see the completing job as ASSIGNED.
**Why it happens:** SQLAlchemy async sessions — the count query might execute before the status update is flushed.
**How to avoid:** In `report_result`, do the DRAINING auto-transition check after `await db.commit()`, then run a fresh count query in the same session to get the post-commit count.

### Pitfall 4: Diagnosis Logic Drift from pull_work
**What goes wrong:** If the diagnosis endpoint re-implements eligibility checks independently, the checks will eventually diverge from the actual dispatch logic. Operators will see "eligible" in the diagnosis but the job won't dispatch (or vice versa).
**Why it happens:** Copy-paste of complex conditional logic.
**How to avoid:** Extract `_node_is_eligible(node, job, node_tags, caps_dict)` as a static method on `JobService` BEFORE implementing the diagnosis endpoint. Both `pull_work` and `get_dispatch_diagnosis` call the same helper.

### Pitfall 5: Queue View Time Window Off-by-One
**What goes wrong:** The "1h" time window filter for terminal jobs in the Queue view may not use UTC, producing confusing results for operators in non-UTC timezones.
**Why it happens:** JavaScript `new Date()` is local time; the backend stores UTC.
**How to avoid:** Use `subHours(new Date(), 1)` from `date-fns` (already imported in Jobs.tsx) and pass as ISO string. The backend's `date_from` filter compares against `Job.created_at` which is UTC.

### Pitfall 6: DRAINING Does Not Appear in Nodes.tsx Status Dot Logic
**What goes wrong:** Nodes.tsx has status-to-color/icon mapping that doesn't include DRAINING — the node would render with a fallback color or no icon.
**Why it happens:** The TypeScript interface and rendering switch were written before DRAINING existed.
**How to avoid:** Add DRAINING to the Node status union type AND to every `switch`/`if` block that maps status to icon/color in Nodes.tsx.

---

## Code Examples

### Eligibility Helper Extraction (new shared method)
```typescript
// Source: puppeteer/agent_service/services/job_service.py (pull_work lines ~553-610)
// Extract into:
@staticmethod
def _node_is_eligible(node: 'Node', job: 'Job', node_tags: list, node_caps_dict: dict) -> bool:
    """Pure eligibility check: True if this node can accept this job.
    Called by both pull_work and get_dispatch_diagnosis."""
    import json
    req_tags = json.loads(job.target_tags) if job.target_tags else []
    if not isinstance(req_tags, list):
        req_tags = []
    if not all(t in node_tags for t in req_tags):
        return False
    node_env_tags = [t for t in node_tags if t.startswith("env:")]
    job_env_tags = [t for t in req_tags if t.startswith("env:")]
    if node_env_tags and not any(et in job_env_tags for et in node_env_tags):
        return False
    if job_env_tags and not any(et in node_env_tags for et in job_env_tags):
        return False
    if job.env_tag:
        node_env_tag = (node.env_tag or "").upper() if node.env_tag else None
        if node_env_tag != job.env_tag.upper():
            return False
    if job.capability_requirements:
        try:
            req_caps = json.loads(job.capability_requirements)
            for cap_name, min_ver in req_caps.items():
                if cap_name not in node_caps_dict:
                    return False
                node_ver = node_caps_dict[cap_name]
                try:
                    from packaging.version import Version
                    if not (Version(node_ver) >= Version(min_ver)):
                        return False
                except Exception:
                    if not (node_ver >= min_ver):
                        return False
        except Exception:
            return False
    return True
```

### DRAINING Guard in pull_work
```python
# Source: puppeteer/agent_service/services/job_service.py — receive at top of node selection
# After fetching node:
if node.status in ("TAMPERED", "DRAINING"):
    return PollResponse(job=None)
```

### DRAINING Guard in list_nodes (main.py ~line 1477)
```python
# Source: puppeteer/agent_service/main.py list_nodes handler
if n.status in ("REVOKED", "TAMPERED", "DRAINING"):
    node_status = n.status
else:
    is_offline = (datetime.utcnow() - n.last_seen).total_seconds() > 60
    node_status = "OFFLINE" if is_offline else "ONLINE"
```

### Auto-Transition in report_result
```python
# After db.commit() in report_result handler:
if node and node.status == "DRAINING":
    running_count_result = await db.execute(
        select(func.count(Job.guid)).where(
            Job.status == 'ASSIGNED',
            Job.node_id == node_id
        )
    )
    if running_count_result.scalar() == 0:
        node.status = "OFFLINE"
        await db.commit()
        await ws_manager.broadcast("node:updated", {"node_id": node_id, "status": "OFFLINE"})
```

### Drain/Undrain Endpoints (main.py)
```python
@app.patch("/nodes/{node_id}/drain", tags=["Nodes"])
async def drain_node(node_id: str, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status not in ("ONLINE", "BUSY"):
        raise HTTPException(status_code=409, detail=f"Cannot drain node in {node.status} state")
    node.status = "DRAINING"
    audit(db, current_user, "node:drain", node_id)
    await db.commit()
    await ws_manager.broadcast("node:updated", {"node_id": node_id, "status": "DRAINING"})
    return {"status": "DRAINING", "node_id": node_id}

@app.patch("/nodes/{node_id}/undrain", tags=["Nodes"])
async def undrain_node(node_id: str, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status != "DRAINING":
        raise HTTPException(status_code=409, detail="Node is not in DRAINING state")
    node.status = "ONLINE"
    audit(db, current_user, "node:undrain", node_id)
    await db.commit()
    await ws_manager.broadcast("node:updated", {"node_id": node_id, "status": "ONLINE"})
    return {"status": "ONLINE", "node_id": node_id}
```

### Migration SQL (migration_v42.sql)
```sql
-- Phase 52: No schema changes needed — Node.status is a plain VARCHAR, no constraint
-- DRAINING is a new valid value requiring no column alteration.
-- This migration is a no-op placeholder for documentation purposes.
-- The node selection loop in job_service.py enforces the DRAINING exclusion at runtime.
-- Existing deployments: no action required.
```
Note: Because `Node.status` is `String` (unbounded VARCHAR), no migration SQL is needed for the DRAINING value itself. The migration file should be created as documentation but has no DDL.

### WebSocket Broadcast for node:updated
The existing `ws_manager.broadcast` pattern (already used for `job:updated`, `node:heartbeat`) handles the `node:updated` event. The Queue.tsx and Nodes.tsx views should handle this event to refresh node status badges.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Node status computed at read time | Node status partially computed, partially persisted | Phase 52 introduces DRAINING as persisted value | list_nodes must protect persisted statuses from freshness override |
| All jobs routed to any ONLINE node | Nodes can be explicitly excluded via DRAINING | Phase 52 | No dispatch to DRAINING nodes |

---

## Open Questions

1. **`node:heartbeat` vs `node:updated` for diagnosis refresh**
   - What we know: diagnosis should refresh when a node comes online or a running job completes
   - What's unclear: whether the frontend should re-fetch `dispatch-diagnosis` on every `node:heartbeat` (potentially noisy if many nodes heartbeat every few seconds) or only on status-change events
   - Recommendation (Claude's discretion): re-fetch diagnosis only when the WebSocket event carries a status change that could affect the pending job (e.g., a node goes ONLINE, a running job completes). If the backend sends `node:heartbeat` with status in the payload, the frontend can gate the re-fetch on `data.status === 'ONLINE'`.

2. **Queue position semantics**
   - What we know: queue position should count jobs ahead with similar eligibility
   - What's unclear: whether to count all PENDING jobs ahead (by created_at) or only jobs that are eligible for the same set of nodes
   - Recommendation: count all PENDING/RETRYING jobs with earlier `created_at` as a simple approximation; label it "approximately" in the message to set correct expectations.

3. **`node:updated` broadcast event name**
   - What we know: `node:heartbeat` is already broadcast; no `node:updated` exists yet
   - What's unclear: whether to add a new `node:updated` event type or reuse `node:heartbeat` with additional fields
   - Recommendation: add `node:updated` as a distinct event for explicit status changes (drain/undrain/auto-offline); keep `node:heartbeat` for periodic stat updates. This lets the frontend differentiate stat noise from structural state changes.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (installed) |
| Config file | `puppeteer/pytest.ini` or implicit via `pyproject.toml` |
| Quick run command | `cd puppeteer && pytest tests/test_draining.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIS-01 | dispatch-diagnosis returns correct reason for each case | unit | `pytest tests/test_dispatch_diagnosis.py -x` | ❌ Wave 0 |
| VIS-01 | diagnosis "all_nodes_busy" includes correct queue position | unit | `pytest tests/test_dispatch_diagnosis.py::test_queue_position -x` | ❌ Wave 0 |
| VIS-02 | GET /jobs with multi-status filter returns expected job sets | unit | `pytest tests/test_pagination.py::test_status_filter -x` (existing file) | existing |
| VIS-03 | GET /nodes/{id}/detail returns running job + eligible pending + 24h history | unit | `pytest tests/test_node_detail.py -x` | ❌ Wave 0 |
| VIS-04 | PATCH /nodes/{id}/drain sets status DRAINING, pull_work skips DRAINING node | unit | `pytest tests/test_draining.py -x` | ❌ Wave 0 |
| VIS-04 | Auto-transition DRAINING → OFFLINE when last job completes | unit | `pytest tests/test_draining.py::test_auto_offline_transition -x` | ❌ Wave 0 |
| VIS-04 | Heartbeat does NOT clear DRAINING status | unit | `pytest tests/test_draining.py::test_heartbeat_preserves_draining -x` | ❌ Wave 0 |
| VIS-04 | list_nodes preserves DRAINING status (not overwritten by freshness check) | unit | `pytest tests/test_draining.py::test_list_nodes_draining_preserved -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_draining.py tests/test_dispatch_diagnosis.py tests/test_node_detail.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_draining.py` — covers VIS-04 (drain/undrain endpoints, pull_work exclusion, heartbeat guard, auto-transition, list_nodes preservation)
- [ ] `tests/test_dispatch_diagnosis.py` — covers VIS-01 (all four diagnosis cases, queue position calculation)
- [ ] `tests/test_node_detail.py` — covers VIS-03 (node detail aggregation endpoint)

Existing test infrastructure: `tests/test_pagination.py` (in-memory SQLite DB fixture) provides the right fixture pattern to copy for new test files.

---

## Sources

### Primary (HIGH confidence)
- Direct code read: `puppeteer/agent_service/services/job_service.py` — full node selection loop (`pull_work` lines 438-648), eligibility logic lines 553-610
- Direct code read: `puppeteer/agent_service/main.py` — `list_nodes` handler (lines 1438-1508), `revoke_node` pattern (lines 1543-1560), `ws_manager.broadcast` calls
- Direct code read: `puppeteer/agent_service/db.py` — `Node.status` column type (String, no constraint), all existing DB models
- Direct code read: `puppeteer/dashboard/src/views/Jobs.tsx` — `JobDetailPanel` Sheet pattern (lines 155-234), WebSocket integration
- Direct code read: `puppeteer/dashboard/src/views/Nodes.tsx` — Node interface (lines 66-80), existing status handling
- Direct code read: `puppeteer/dashboard/src/hooks/useWebSocket.ts` — full hook implementation
- Direct code read: `puppeteer/dashboard/src/layouts/MainLayout.tsx` — nav structure (lines 82-124)
- Direct code read: `puppeteer/dashboard/src/AppRoutes.tsx` — all existing routes

### Secondary (MEDIUM confidence)
- Established Phase 49 pagination pattern: `tests/test_pagination.py` — confirmed in-memory SQLite fixture pattern for new test files
- Migration SQL pattern: `migration_v41.sql` — confirms `IF NOT EXISTS` guard format for Postgres-only migrations

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all components confirmed present in codebase
- Architecture: HIGH — patterns directly derived from existing code; DRAINING lifecycle fully specified with exact guard locations
- Pitfalls: HIGH — all pitfalls derived from direct code inspection of the specific lines that need modification (list_nodes freshness override, heartbeat handler, report_result flow)
- Test strategy: HIGH — follows confirmed test patterns from test_pagination.py

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable stack — no fast-moving dependencies)
