# Phase 116: Fix Smelter DB Migration and Add EE Licence Hot-Reload — Research

**Gathered:** 2026-04-02
**Status:** RESEARCH COMPLETE

---

## Objective

Answer: "What do I need to know to PLAN this phase well?"

This research examines the two parallel workstreams: (1) DB migration gap-fixing for the Smelter ingredient model, and (2) EE licence hot-reload runtime activation without restart.

---

## Problem Statement

**DB Migration Gap:** The `ApprovedIngredient` model was introduced in Phase 107 but the migration SQL is missing the `mirror_log` column that the frontend expects when filtering approved ingredients. This breaks the Smelter UI. Broader audit needed to catch similar schema↔model mismatches.

**EE Licence Lifecycle:** Currently, EE licences are loaded at startup and never re-evaluated at runtime. Operators cannot update/activate/renew licences without a full restart, creating downtime. Phase 116 must enable hot-reload while maintaining atomic state transitions and avoiding accidental CE→EE→CE flapping from bad reloads.

---

## Context from Phase 107 & Prior Art

### DB Model Evolution
- Phase 107 added `ApprovedIngredient`, `ToolRecipe`, `CuratedBundle` tables in `puppeteer/agent_service/db.py`
- Migration pattern: `puppeteer/migration_vN.sql` files (currently up to v45 in repo)
- Each migration uses `ADD COLUMN IF NOT EXISTS ... ON CONFLICT DO NOTHING` — idempotent, safe to rerun
- SQLite local dev uses `jobs.db`; Postgres in Docker via `DATABASE_URL` env var
- Schema is initialized via `Base.metadata.create_all()` at startup — **no Alembic**

### EE Licensing Precedent
- `puppeteer/agent_service/services/licence_service.py` exists with:
  - `load_licence()` — loads from env/file at startup, returns `Licence` object
  - `_read_licence_raw()` — reads raw file or env var
  - `LicenceStatus` enum: `VALID`, `GRACE`, `EXPIRED`
- Licence is attached to `app.state.licence_state` at startup
- Smelter routing guards already check `app.state.licence_state` — EE routers in `ee/routers/` are only imported if VALID

### EE Router Pattern
- `puppeteer/agent_service/ee/__init__.py` uses `importlib.metadata.entry_points(group="axiom.ee")` to load EE plugins
- Currently only loaded at startup in `lifespan` event
- No runtime registration mechanism exists

### Audit Trail
- `audit()` helper in `main.py` logs security events to `AuditLog` table
- Used for user actions, cert revocation, etc.
- Can be extended for licence reload events (who, old→new status, timestamp)

### WebSocket Infrastructure
- `/ws` endpoint in `main.py` broadcasts state changes (node status, job updates)
- `useWebSocket.ts` hook in frontend listens and auto-reconnects
- No existing `licence_status_changed` event type — would need to add

---

## Key Decisions to Verify

### 1. DB Migration Scope

**Decision from CONTEXT.md:** "Audit ALL EE models against migration SQL files for model↔DB mismatches (not just mirror_log)"

**What to validate:**
- Scan `db.py` for all Pydantic columns in EE models
- Cross-reference against latest migration SQL in `puppeteer/migration_v*.sql`
- Identify gaps: missing columns, mismatched types, renamed fields
- Example gaps to look for:
  - `ApprovedIngredient.mirror_log` (known issue)
  - Any columns added to Phase 107 models but missing from DB migration
  - Pydantic `@field_validator` overrides (e.g., JSON fields) that may require DB casting

**Outcome:** Single migration file (e.g., `migration_v46.sql`) with ALL gaps fixed at once, not piecemeal per-model.

### 2. Hot-Reload Mechanism — Reload Endpoint

**Decision from CONTEXT.md:**
- Admin API: `POST /api/admin/licence/reload`
- Optional body: `{"licence_key": "..."}` to override default (env/file)
- Return 422 if reload fails (keep old state active)
- Return 200 with new metadata if successful

**What to validate:**
- Endpoint should be admin-only (`require_permission("system:write")`)
- Atomic state swap: old `app.state.licence_state` → new in one assignment
- Audit the reload action (who, timestamp, old status → new status)
- Test failure path: invalid key → 422 with error detail, old state preserved

### 3. Hot-Reload Mechanism — Background Timer

**Decision from CONTEXT.md:** "Background timer checks licence expiry every 60 seconds, updates `app.state.licence_state`"

**What to validate:**
- Implementation choice: `asyncio.create_task()` in lifespan vs APScheduler job?
  - APScheduler already used for job scheduling — consistency favors APScheduler
  - But simple timer may be overkill; `asyncio.create_task()` is sufficient
  - **Recommendation:** `asyncio.create_task()` — simpler, no extra scheduler config
- Timer should run only if licence enabled (don't check expiry on CE)
- On expiry transition (VALID→GRACE or GRACE→EXPIRED):
  - Update `app.state.licence_state`
  - Broadcast `licence_status_changed` event to all WebSocket clients
  - Log to audit trail

### 4. CE→EE vs EE→CE Runtime Transitions

**Decision from CONTEXT.md:**
- CE→EE: Full re-init on reload (warm permission cache, run clock rollback detection)
- EE→CE (expiry): EE routers stay registered but return 402 Payment Required

**What to validate:**
- When licence goes VALID (CE→EE):
  - Re-run `init_permissions()` (currently in lifespan)
  - Re-run `check_and_record_boot()` (clock rollback detection)
  - Dynamically mount/include EE routers if not already mounted
- When licence goes EXPIRED (EE→CE):
  - EE router middleware should catch and return:
    ```json
    {
      "error": "licence_expired",
      "message": "EE licence has expired. Please renew to continue.",
      "status": "EXPIRED"
    }
    ```
  - This 402 response is more specific than generic 403
- No need to unmount routers (keep registered, just block traffic)

### 5. Dashboard License Section

**Decision from CONTEXT.md:** "Admin page licence section shows full metadata: org name, tier, expiry date, node limit, current status badge"

**What to validate:**
- New Admin.tsx section or subsection for "Licence & Compliance"
- Displays:
  - Org name (from licence.organization)
  - Tier (from licence.tier) with badge styling
  - Expiry date (from licence.expires_at) with countdown "X days remaining"
  - Node limit (from licence.max_nodes) with current node count for utilization %
  - Status badge: VALID (green), GRACE (amber), EXPIRED (red)
  - Last reload timestamp
- Reload button: calls `POST /api/admin/licence/reload`, shows loading spinner, displays result toast
- Amber warning if in GRACE period:
  - Can place in Admin section directly
  - Optional: global header banner for admins (non-intrusive)

### 6. Migration File Organization

**Current state:** `migration_v45.sql` is the latest (after Phase 107)

**What to validate:**
- Next file: `migration_v46.sql` (or v45+N if gaps found)
- Contents:
  - All ADD COLUMN IF NOT EXISTS statements for found gaps
  - Idempotent (can re-run without error)
  - Targets both Postgres and SQLite if they diverge (but both should support IF NOT EXISTS)
- No schema changes needed for hot-reload feature (licence is already a Licence object in memory)

---

## Existing Code Patterns to Reuse

### Pattern: Audit Trail + WebSocket Broadcast
From Phase 9+ (session security, audit log):
```python
# In main.py lifespan or endpoint:
await audit("licence_reload", {
    "old_status": old_licence.status,
    "new_status": new_licence.status,
    "triggered_by": current_user.id,
    "licence_org": new_licence.organization
})

# Broadcast to all connected WebSocket clients:
await broadcast_ws_event("licence_status_changed", {
    "old_status": str(old_status),
    "new_status": str(new_status),
    "message": f"Licence updated: {new_status.value}"
})
```

### Pattern: Admin-Only Endpoint
From Phase 10 (service principals, user management):
```python
@app.post("/api/admin/licence/reload")
async def reload_licence(
    body: LicenceReloadRequest,
    current_user = Depends(require_permission("system:write"))
):
    # Admin check via Depends — built-in to require_permission
    ...
```

### Pattern: Idempotent Migration
From Phase 107 + Phase 9 (migration_v10.sql):
```sql
-- migration_v46.sql
ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS mirror_log TEXT;
ALTER TABLE tool_recipes ADD COLUMN IF NOT EXISTS {field} {type};
-- ... more gaps found in audit
```

### Pattern: EE Router Import
From Phase 107 (ee/__init__.py):
```python
def load_ee_routers():
    """Load EE routers from entry points (can be called at runtime)."""
    routers = []
    for entry_point in importlib.metadata.entry_points(group="axiom.ee"):
        try:
            router_module = entry_point.load()
            routers.append(router_module.router)
        except Exception as e:
            logger.error(f"Failed to load EE router {entry_point.name}: {e}")
    return routers

# Can be called at startup or runtime
```

---

## Risk Mitigation

### Risk: Race condition during reload
**Mitigation:** Atomic assignment to `app.state.licence_state`. In-flight requests see either old or new (both valid). No locking needed.

### Risk: Invalid licence key during reload leaves system in bad state
**Mitigation:** Reload endpoint validates key before swapping state. If validation fails, keep old state active, return 422 with error detail. Operator can fix and retry.

### Risk: Background timer fires while operator is manually reloading
**Mitigation:** Both paths update same `app.state.licence_state`. Last-write-wins is acceptable (both old and new states are valid). No mutex needed.

### Risk: EE→CE transition (expiry) breaks in-flight requests
**Mitigation:** EE router middleware returns 402 Payment Required (not 403). Client can handle gracefully. Operator re-activates without restart.

### Risk: Licence expires between background check cycles (60s)
**Mitigation:** Acceptable. Max grace period is 60s. SLA for licence updates is "within a minute". If operator needs instant expiry, issue new key + reload.

---

## Testing Strategy

### Unit Testing
- Mock `load_licence()` with valid/expired/invalid keys
- Test reload endpoint: valid key → 200, invalid key → 422
- Test background timer: fires on schedule, updates state, broadcasts event
- Test EE router middleware: returns 402 on expired licence

### Integration Testing
- Full-stack test: reload licence → check WebSocket broadcast received → verify Admin UI updates
- Test CE→EE transition: load CE licence → reload with EE key → verify permission cache warmth → verify EE routers respond
- Test EE→CE transition: load EE licence → let it expire (or force via test) → verify EE routers return 402
- Test reload failure: try invalid key → verify old state preserved → try valid key → verify recovery

### E2E Testing (Playwright)
- Admin user navigates to Licence section
- Sees current status (VALID/GRACE/EXPIRED)
- Clicks "Reload" button
- See spinner, then success toast with new metadata
- Verify WebSocket broadcast received (optional subscription in test)
- Force expiry (manual state update in test), verify warning banner appears

---

## Validation Architecture

This phase needs Dimension 8 verification (full stack testing):

1. **DB Migration:** Run migration on test DB with both old and new schema states
2. **API Endpoints:**
   - `POST /api/admin/licence/reload` (valid key → 200, invalid → 422)
   - `GET /api/admin/system/licence` (returns current licence metadata)
   - EE-gated endpoint (e.g., `GET /api/smelter/ingredients`) returns 402 when expired
3. **WebSocket:** Broadcast `licence_status_changed` event received on client
4. **UI:** Admin licence section renders, reload button works, GRACE warning displays
5. **Background Timer:** Timer fires on schedule, updates expiry status

---

## Known Unknowns to Clarify During Planning

1. **Migration audit scope:** How many gaps found? (Estimated 1–3 beyond mirror_log)
2. **Background timer implementation:** APScheduler vs asyncio.create_task? (Recommend: create_task)
3. **Global GRACE warning:** In MainLayout header or only in Admin section? (Recommend: Admin only, not global)
4. **EE plugin re-registration:** Can routers be unmounted/remounted safely, or keep always-registered? (Recommend: keep always-registered, guard with middleware)
5. **Licence reload test data:** How to generate test EE licences with controlled expiry? (Use mock in tests, real keys in E2E)

---

## Summary

Phase 116 is a **maintenance + feature** hybrid:

- **Maintenance:** Fix DB schema gaps via idempotent migration (`migration_v46.sql`)
- **Feature:** Implement licence hot-reload via endpoint + background timer + UI section
- **Risk:** Low (no breaking changes; old and new states are both valid)
- **Complexity:** Medium (coordination of reload endpoint + background task + WebSocket broadcast + EE router re-initialization)
- **Dependencies:** None outside current codebase (builds on existing audit, WebSocket, EE plugin patterns)
- **Testing:** Full stack required (DB + API + WebSocket + UI)

---

## RESEARCH COMPLETE
