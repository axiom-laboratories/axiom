# Core Pipeline Gap Report
## Foundry → Node Deployment → Job Execution

**Generated**: 2026-02-28
**Priority scope**: Get Foundry templates, node deployment, and reliable job scheduling working
**Out of scope for now**: User management, account centre, WebSockets

---

## CRITICAL BUGS (break existing functionality)

### BUG-1: `/job-definitions` endpoint returns Blueprints instead of Job Definitions
**File**: `puppeteer/agent_service/main.py:459-463`
**Severity**: Critical — scheduled jobs list is completely broken

```python
# CURRENT (WRONG):
@app.get("/job-definitions")
async def dashboard_job_definitions(db: AsyncSession = Depends(get_db)):
    return await list_blueprints(db)  # <-- returns blueprints!

# FIX: point to scheduler_service
    return await scheduler_service.list_job_definitions(db)
```

---

### BUG-2: `NodeResponse` omits `capabilities`, `tags`, `concurrency_limit`
**File**: `puppeteer/agent_service/main.py:296-318`
**Severity**: Critical — node cards can't show what tools a node actually has; job targeting is invisible

The `/nodes` route builds the response dict manually and drops `capabilities`, `concurrency_limit`, and `job_memory_limit` even though all three are stored in `Node`. The frontend `Node` interface has a `tags?: string[]` field but capabilities are completely absent.

**Fix**: Add to the response dict in `list_nodes`:
```python
resp.append({
    ...existing fields...,
    "tags": tags,
    "capabilities": json.loads(n.capabilities) if n.capabilities else None,
    "concurrency_limit": n.concurrency_limit,
    "job_memory_limit": n.job_memory_limit,
})
```
Also add `capabilities`, `concurrency_limit`, `job_memory_limit` to `NodeResponse` model in `models.py`.

---

### BUG-3: Version comparison is lexicographic — breaks capability matching
**File**: `puppeteer/agent_service/services/job_service.py:151-158`
**Severity**: High — jobs may be routed to wrong nodes

`"3.9.0" >= "3.11"` is `True` with string comparison because `"9" > "1"`. A node with Python 3.9 will accept jobs requiring Python 3.11.

**Fix**: Replace with a proper semver comparison:
```python
from packaging.version import Version, InvalidVersion

def version_satisfies(node_ver: str, min_ver: str) -> bool:
    try:
        return Version(node_ver) >= Version(min_ver)
    except InvalidVersion:
        return node_ver >= min_ver  # fallback
```
`packaging` is a transitive dependency of pip — already available.

---

### BUG-4: `PuppetTemplateResponse` missing `last_built_at`; `current_image_uri` not mapped to `last_built_image`
**File**: `puppeteer/agent_service/models.py:162-172`, `puppeteer/agent_service/db.py:110-118`
**Severity**: High — frontend always shows "Never built" even after a successful build

Frontend `Template` interface uses:
- `last_built_image` — backend has `current_image_uri`
- `last_built_at` — backend has no such field in DB or response

**Fixes needed**:
1. Add `last_built_at: Optional[datetime]` column to `PuppetTemplate` DB model
2. Populate it in `foundry_service.build_template()` on success
3. Add `last_built_at: Optional[datetime]` to `PuppetTemplateResponse`
4. In `list_templates`, alias `current_image_uri` → `last_built_image` in the response OR update frontend to use `current_image_uri`

Consistent approach: update `PuppetTemplateResponse` to include both, update frontend to match.

---

### BUG-5: Foundry Dockerfile COPY is broken — puppet code never makes it into the image
**File**: `puppeteer/agent_service/services/foundry_service.py:65-68`
**Severity**: High — built images can't run jobs

```python
# CURRENT (WRONG):
context_path = "/app/puppets"          # build context
dockerfile.append("COPY environment_service/node.py .")  # looks for this inside context_path
```

The temp build dir is separate from `context_path`. The COPY will fail unless `environment_service/node.py` exists at `{context_path}/environment_service/node.py`. Also the node.py needs its `runtime.py` dependency.

The `build_image()` legacy method uses `Containerfile.node` in `/puppets/` which has a proper multi-file structure — that approach is better.

**Fix**: Copy the required puppet source files into the temp build dir before building, or change the context to the actual puppets directory and write the Dockerfile there:
```python
context_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "puppets")
context_path = os.path.realpath(context_path)
# Write Dockerfile INTO context_path/temp dir, then build with context_path
```

---

### BUG-6: `build_template` runs as blocking subprocess on the HTTP request thread
**File**: `puppeteer/agent_service/services/foundry_service.py:79-98`
**Severity**: Medium — Docker builds can take minutes; the HTTP request hangs

`subprocess.run()` is synchronous and blocks the async event loop. For large images this will either timeout or starve other requests.

**Fix**: Use `asyncio.create_subprocess_exec` with `await proc.communicate()`, or run in a thread pool via `asyncio.get_event_loop().run_in_executor(None, ...)`.

---

### BUG-7: `AddNodeModal` is commented out in Nodes.tsx — "Provision Puppet" button does nothing
**File**: `puppeteer/dashboard/src/views/Nodes.tsx:17-18`
**Severity**: High — primary node enrollment flow is unreachable from the UI

```typescript
// TODO: Migrate
// import AddNodeModal from '../components/AddNodeModal';
// import ManageMountsModal from '../components/ManageMountsModal';
```

The `AddNodeModal` component exists and works (`/components/AddNodeModal.tsx`). It just needs to be re-imported and the "Provision Puppet" button wired to `setShowAddModal(true)`.

`ManageMountsModal` doesn't exist yet — needs to be created.

---

## MISSING FEATURES (functional gaps in the core pipeline)

### GAP-1: No delete endpoints for Blueprints, Templates, or Scheduled Jobs
**Backend**: `puppeteer/agent_service/main.py`
**Severity**: High — no way to clean up or iterate on definitions

Missing endpoints:
- `DELETE /api/blueprints/{id}` — must check no PuppetTemplate references it
- `DELETE /api/templates/{id}` — must check no active jobs reference it
- `DELETE /jobs/definitions/{id}` — should de-register from APScheduler too
- `PATCH /jobs/definitions/{id}/toggle` — pause/resume a scheduled job (`is_active` toggle)

**Frontend**: No delete buttons exist in Templates.tsx or JobDefinitions.tsx.

---

### GAP-2: Job dispatch form has no node targeting
**File**: `puppeteer/dashboard/src/views/Jobs.tsx`
**Severity**: High — all jobs go to any available node regardless of capabilities

`JobCreate` supports `target_tags: List[str]` and `capability_requirements: Dict[str, str]`. The frontend form only exposes `task_type` and `payload`.

**Fix**: Add two optional fields to the dispatch form:
- Tags input (comma-separated or badge input)
- Capability requirements (key:version pairs)

---

### GAP-3: No job detail / result view
**File**: `puppeteer/dashboard/src/views/Jobs.tsx`
**Severity**: High — can't see job output, errors, or flight recorder data

The "More" action button per job row is a placeholder. Clicking it should open a slide-out panel showing:
- Full job metadata (GUID, node, timings, duration)
- Result JSON (if COMPLETED)
- Flight recorder report (if FAILED — error, stack trace, exit code)
- Telemetry data

---

### GAP-4: GUID search filter is non-functional
**File**: `puppeteer/dashboard/src/views/Jobs.tsx:165`
**Severity**: Medium — usability issue at scale

The `<Input placeholder="Filter GUID..." />` is not connected to any state or filter logic.

**Fix**: Add `useState` for filterText, filter the `jobs` array client-side on `job.guid.includes(filterText)`.

---

### GAP-5: Node capabilities not displayed on node cards
**File**: `puppeteer/dashboard/src/views/Nodes.tsx`
**Severity**: Medium — operator can't see what a node can do without querying the DB

Once BUG-2 is fixed (capabilities returned in `/nodes`), the node cards need a capabilities badge row showing `python: 3.11.0`, `docker: 24.0`, etc.

---

### GAP-6: `ManageMountsModal` component doesn't exist
**File**: needs to be created at `puppeteer/dashboard/src/components/ManageMountsModal.tsx`
**Severity**: Medium — network mount configuration is backend-complete but unreachable from UI

Backend: `GET /config/mounts`, `POST /config/mounts` — fully implemented.
Frontend: Button exists, no modal, no component.

The modal needs:
- Fetch current mounts on open
- Add/remove rows (name + UNC path `//server/share`)
- Submit to `POST /config/mounts`

---

### GAP-7: Scheduled job form missing `target_tags` and `capability_requirements`
**File**: `puppeteer/dashboard/src/components/JobDefinitionModal.tsx`
**Severity**: Medium — scheduled jobs always go to any node

The DB model has these fields, the `JobDefinitionCreate` request model has them, but the form only has `target_node_id`. You can't schedule a job to "any node with python-3.11".

---

### GAP-8: OS family detection hardcoded to DEBIAN in Foundry
**File**: `puppeteer/agent_service/services/foundry_service.py:36`
**Severity**: Medium — Alpine blueprints (already in capability matrix if seeded) silently use wrong recipes

```python
os_family = "DEBIAN" # Simplified detection
```

**Fix**: Derive from `base_os`:
```python
base_os = rt_def.get("base_os", "debian-12-slim")
os_family = "ALPINE" if "alpine" in base_os.lower() else "DEBIAN"
```

---

### GAP-9: Node resource charts use mock data
**File**: `puppeteer/dashboard/src/views/Nodes.tsx` — `generateMockHistory()`
**Severity**: Low-Medium — misleading display

Real `stats: {cpu, ram}` arrive via heartbeat and are stored in `Node.stats`. The frontend receives them in the `/nodes` response. But the Recharts area graphs use a locally-generated fake history array instead of the real point.

**Short-term fix**: Remove the history chart, replace with a simple gauge/bar showing the current CPU% and RAM% from `node.stats`.
**Proper fix**: Store a rolling stats history on the backend (new `NodeStats` table, populated by heartbeat) and serve it as `/nodes/{id}/stats/history`.

---

### GAP-10: `upload-key` endpoint is a stub
**File**: `puppeteer/agent_service/main.py:545-549`
**Severity**: Low — Admin page "Upload Key" does nothing

```python
@app.post("/admin/upload-key")
async def upload_public_key(req: object, ...):
    return {"status": "stored"}  # does nothing
```

This should store the PEM key in the `Config` table under `signing_public_key` and optionally also register it as a `Signature`. The frontend sends key content to this endpoint.

---

## IMPLEMENTATION ORDER (recommended)

### Sprint 1 — Fix the broken stuff (backend only, no new UI)
1. **BUG-1**: Fix `/job-definitions` endpoint to call `list_job_definitions`
2. **BUG-2**: Add `capabilities`, `concurrency_limit`, `job_memory_limit` to `NodeResponse`
3. **BUG-3**: Replace lexicographic version comparison with `packaging.version.Version`
4. **BUG-4**: Add `last_built_at` to DB + response; align field names with frontend
5. **BUG-5**: Fix Foundry Dockerfile build context so puppet code is actually copied
6. **BUG-8**: Fix OS family detection from `base_os` string

### Sprint 2 — Wire up Foundry end-to-end
7. **BUG-6**: Make `build_template` async (run_in_executor or asyncio subprocess)
8. **GAP-1 backend**: Add DELETE endpoints for blueprints, templates, scheduled jobs + toggle
9. **GAP-1 frontend**: Add delete buttons to Templates.tsx and JobDefinitions.tsx
10. Wire "View JSON" button on blueprints to a modal showing the definition JSON

### Sprint 3 — Node provisioning & monitoring
11. **BUG-7**: Uncomment `AddNodeModal` import + wire "Provision Puppet" button
12. **GAP-6**: Create `ManageMountsModal` + wire "Network Mounts" button
13. **GAP-5**: Display capabilities/tags on node cards (after BUG-2 is merged)
14. **GAP-9**: Replace mock charts with real CPU/RAM gauges using `node.stats`

### Sprint 4 — Job dispatch & execution quality
15. **GAP-2**: Add `target_tags` + `capability_requirements` to job dispatch form
16. **GAP-3**: Implement job detail panel (click row → slide-out with result/flight recorder)
17. **GAP-4**: Wire GUID filter input
18. **GAP-7**: Add `target_tags`/`capability_requirements` to scheduled job form

### Sprint 5 — Polish & completeness
19. **GAP-10**: Fix `upload-key` endpoint to actually store the key
20. Node concurrency/memory limit editing on node cards
21. Job cancellation (`PATCH /jobs/{guid}/cancel`, add status `CANCELLED`)
22. Scheduled job `is_active` toggle in UI (resume/pause)

---

## FILE MAP (agent quick reference)

| What | File |
|------|------|
| Backend API routes | `puppeteer/agent_service/main.py` |
| DB models (SQLAlchemy) | `puppeteer/agent_service/db.py` |
| Pydantic request/response models | `puppeteer/agent_service/models.py` |
| Job assignment & heartbeat logic | `puppeteer/agent_service/services/job_service.py` |
| Docker image build logic | `puppeteer/agent_service/services/foundry_service.py` |
| Scheduler (APScheduler + cron) | `puppeteer/agent_service/services/scheduler_service.py` |
| Ed25519 signature verification | `puppeteer/agent_service/services/signature_service.py` |
| Foundry page (templates + blueprints) | `puppeteer/dashboard/src/views/Templates.tsx` |
| Node monitoring page | `puppeteer/dashboard/src/views/Nodes.tsx` |
| Job queue page | `puppeteer/dashboard/src/views/Jobs.tsx` |
| Scheduled jobs page | `puppeteer/dashboard/src/views/JobDefinitions.tsx` |
| Add node modal (exists, not wired) | `puppeteer/dashboard/src/components/AddNodeModal.tsx` |
| Create blueprint dialog | `puppeteer/dashboard/src/components/CreateBlueprintDialog.tsx` |
| Create template dialog | `puppeteer/dashboard/src/components/CreateTemplateDialog.tsx` |
| Scheduled job create modal | `puppeteer/dashboard/src/components/JobDefinitionModal.tsx` |
| Auth + fetch wrapper | `puppeteer/dashboard/src/auth.ts` |
| Node puppet agent | `puppets/environment_service/node.py` |
| Node runtime helpers | `puppets/environment_service/runtime.py` |
