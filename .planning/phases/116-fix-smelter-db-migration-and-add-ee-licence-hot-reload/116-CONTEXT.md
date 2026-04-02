# Phase 116: Fix Smelter DB Migration and Add EE Licence Hot-Reload - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Two targeted fixes: (1) add missing `mirror_log` column to `ApprovedIngredient` model and audit all EE models for similar gaps, and (2) implement EE licence hot-reload so operators can update/activate/renew licences without restarting the server. Includes a dashboard licence section on the Admin page.

</domain>

<decisions>
## Implementation Decisions

### Reload mechanism
- Admin API endpoint: `POST /api/admin/licence/reload` — explicit, auditable
- Re-reads from existing source (env var / `secrets/licence.key`) by default
- Optional: accepts licence key in request body as override
- Dashboard UI: reload button on Admin page in a new "Licence" section
- Admin page licence section shows full metadata: org name, tier, expiry date, node limit, current status badge
- Amber warning banner when in GRACE period (both in licence section and optionally in global header for admins)

### CE to EE transitions
- Full runtime transition supported: CE→EE works without restart by dynamically registering EE routers on reload
- EE→CE (licence expiry): EE routers stay registered but return 402 Payment Required with structured error body: `{"error": "licence_expired", "message": "...", "status": "EXPIRED"}`
- Background timer checks licence expiry every 60 seconds, updates `app.state.licence_state`
- On CE→EE transition: full re-init — re-warm permission cache and re-run clock rollback detection
- Atomic swap of `app.state.licence_state` — no locking needed, in-flight requests see either old or new state (both valid)
- WebSocket broadcast `licence_status_changed` event when status transitions (VALID→GRACE, GRACE→EXPIRED, etc.)

### Reload failure handling
- If reload fails (invalid key, corrupted file): keep old licence state active, return 422 with error details
- Operator can fix and retry — no accidental EE→CE transition from a bad reload attempt

### Migration approach
- Audit ALL EE models against migration SQL files for model↔DB mismatches (not just mirror_log)
- Fix all gaps found in this phase — we're already touching migrations
- Separate migration SQL files: one for DB column fixes, licence hot-reload likely needs no schema changes
- All migrations use `ADD COLUMN IF NOT EXISTS` — idempotent, safe to re-run (matches migration_v10.sql pattern)

### Audit trail
- All licence reload events logged via existing `audit()` helper: who triggered, old status → new status, timestamp
- Full DB audit trail visible in Audit Log dashboard

### Claude's Discretion
- Background timer implementation (asyncio.create_task vs APScheduler job)
- EE router dynamic registration approach (FastAPI mount/include_router at runtime)
- Migration SQL file numbering (next available after v45)
- Exact Admin page licence section layout and component structure
- Global header warning banner placement for GRACE period

</decisions>

<specifics>
## Specific Ideas

- Amber warning banner pattern already used for stale Foundry templates — reuse same visual treatment for GRACE period
- Structured 402 error response enables mop-push CLI and other tooling to give specific "licence expired" guidance instead of generic 4xx handling
- Background timer at 60s interval is frequent enough to catch expiry within a minute without adding meaningful load

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `licence_service.py`: `load_licence()`, `_read_licence_raw()`, `LicenceStatus` enum — extend with reload logic
- `audit()` helper in `main.py` — use for licence reload events
- WebSocket broadcast infrastructure in `main.py` — add `licence_status_changed` event type
- `useWebSocket.ts` hook — subscribe to new licence event
- Stale template amber badge pattern in `Templates.tsx` — reuse for GRACE warning

### Established Patterns
- EE models in `db.py` with same `Base` (Phase 107 decision)
- Migration SQL files: `puppeteer/migration_v{N}.sql`, currently up to v45
- EE plugin registration via `importlib.metadata.entry_points(group="axiom.ee")` in `ee/__init__.py`
- Permission cache pre-warming at startup in `main.py` (lines 112-116)
- Clock rollback detection via `check_and_record_boot()` at startup

### Integration Points
- `main.py`: add reload endpoint, background timer task in lifespan, EE router dynamic registration
- `licence_service.py`: add `reload_licence()` function, expiry check logic
- `ee/__init__.py`: make plugin registration callable at runtime (not just startup)
- `db.py`: add `mirror_log` column to `ApprovedIngredient` + fix any other gaps found in audit
- `Admin.tsx` (or `Admin` section): add licence status section with metadata + reload button
- `MainLayout.tsx`: optional global GRACE warning banner for admin users

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 116-fix-smelter-db-migration-and-add-ee-licence-hot-reload*
*Context gathered: 2026-04-02*
