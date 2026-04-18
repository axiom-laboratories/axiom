# Phase 168 Plan 02: SIEM EE Gating & Admin Routes Summary

**Plan:** 168-02  
**Subsystem:** SIEM audit streaming (EE-only feature gating and administrative API)  
**Phase:** 168 (SIEM Audit Streaming - Enterprise Edition)  
**Completed:** 2026-04-18  
**Duration:** ~30 minutes  
**Tasks Completed:** 5/5  

## One-Liner

Implemented CE/EE gating for SIEM endpoints, created 4 FastAPI admin routes for SIEM configuration management, integrated SIEMService into application lifespan, and added SIEM status to system health check.

## Summary

Plan 168-02 completes the integration of SIEM audit streaming into the control plane application. This plan layers EE feature gating (returning HTTP 402 in CE mode) on top of the core SIEMService built in 168-01, exposes 4 new admin endpoints for operators, and wires service lifecycle management into FastAPI startup/shutdown.

### Key Accomplishments

1. **CE/EE Router Gating**
   - Created CE stub router (`ee/interfaces/siem.py`) returning 402 Unavailable
   - Created EE implementation router (`ee/routers/siem_router.py`) with full functionality
   - Registered conditional import of siem_router in main.py (matches vault_router pattern)
   - Mounted CE stubs in ee/__init__.py _mount_ce_stubs()

2. **Admin API Endpoints (4 routes)**
   - `GET /admin/siem/config` — retrieve current SIEM configuration
   - `PATCH /admin/siem/config` — update configuration with hot-reload of service singleton
   - `POST /admin/siem/test-connection` — test connectivity to SIEM destination
   - `GET /admin/siem/status` — retrieve service status, failure tracking, event drop counters
   - All endpoints require `require_ee()` gate and appropriate permission checks

3. **Service Lifecycle Integration**
   - SIEM service initialization in main.py lifespan startup block (after vault init)
   - Fetches SIEMConfig from database; initializes service only if enabled=True
   - Calls set_active() module-level singleton for integration with audit() helper
   - Non-blocking startup with connection test and status logging
   - Graceful shutdown with queue drain before service shutdown
   - Proper ImportError and exception handling for CE mode

4. **System Health Integration**
   - Added optional `siem` field to SystemHealthResponse model
   - Updated system_health endpoint to fetch SIEM status via get_siem_service()
   - SIEM status follows same pattern as vault (healthy/degraded/disabled)

### Architecture Highlights

**Router Registration Pattern**
```
CE mode:
  main.py loads ee/__init__.py
  → _mount_ce_stubs() registers siem stub router
  → /admin/siem/* endpoints return 402

EE mode:
  main.py conditionally imports siem_router
  → registers real implementation
  → /admin/siem/* endpoints fully functional
```

**Hot-Reload on Config Change**
When PATCH /admin/siem/config is called:
1. Update SIEMConfig in database
2. Get existing SIEMService from get_siem_service()
3. Call await old.shutdown() (graceful)
4. Create new SIEMService with updated config
5. Call new.startup()
6. Call set_active(new_siem)
7. Return updated config to client

This allows operators to change SIEM destinations without restarting the agent.

**Graceful Shutdown**
On application shutdown:
1. Retrieve siem_service from app.state
2. Drain remaining events from queue (avoid event loss)
3. Call flush_batch() for any remaining events
4. Call await siem.shutdown()
5. Log completion or errors

## Verification

All endpoints tested via manual integration:

1. ✓ GET /admin/siem/config — returns SIEMConfigResponse with full config
2. ✓ PATCH /admin/siem/config — updates fields, hot-reloads service, returns updated config
3. ✓ POST /admin/siem/test-connection — creates temp config, tests connectivity, returns SIEMTestConnectionResponse
4. ✓ GET /admin/siem/status — returns SIEMStatusResponse with service health metrics
5. ✓ GET /system/health — includes siem field with current status

CE mode verification: Stub router correctly returns 402 Unavailable when EE feature not available.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `puppeteer/agent_service/ee/interfaces/siem.py` | CREATE | CE stub router (402 responses) |
| `puppeteer/agent_service/ee/routers/siem_router.py` | CREATE | EE admin routes (full implementation) |
| `puppeteer/agent_service/ee/__init__.py` | MODIFY | Register CE stub router in _mount_ce_stubs() |
| `puppeteer/agent_service/main.py` | MODIFY | Conditional siem_router import + registration; SIEM startup/shutdown in lifespan |
| `puppeteer/agent_service/models.py` | MODIFY | Add optional siem field to SystemHealthResponse |
| `puppeteer/agent_service/routers/system_router.py` | MODIFY | Fetch SIEM status in system_health endpoint |

## Commits

| Hash | Message |
|------|---------|
| `1fdc0e4b` | feat(168-02): create CE stub router for SIEM endpoints (402 unavailable) |
| `3be6b274` | feat(168-02): create EE SIEM admin router with 4 endpoints |
| `7fe9a5b8` | feat(168-02): register SIEM routers (CE stub + EE implementation) |
| `3ef1b7cb` | feat(168-02): initialize SIEMService in main.py lifespan |
| `1adbc773` | feat(168-02): add siem field to GET /system/health endpoint |

## Deviations from Plan

None — plan executed exactly as written. All tasks completed within scope, no Rule 1/2/3/4 issues encountered.

## Known Stubs / TBD

None. Plan 168-02 is feature-complete. The admin routes are fully wired and functional. Future work (168-03+) will focus on audit event filtering, queue persistence, and UI controls.

## Tech Stack & Patterns

**Added/Modified:**
- FastAPI conditional router registration (matches vault pattern)
- Module-level singleton pattern for service access (set_active/get_siem_service)
- Hot-reload service reinitialization via PATCH endpoint
- Application lifespan integration (startup/shutdown blocks)
- Type-safe Pydantic response models with Field descriptions
- Permission gating via require_ee() + require_permission()

**Dependencies/Integrations:**
- SIEMService (from 168-01) — core audit log streaming engine
- APScheduler integration (from scheduler_service) — batching scheduler
- SQLAlchemy ORM (SIEMConfig, User models)
- FastAPI dependency injection (Depends)

## Threat Surface

No new security threats introduced. All endpoints:
- Require authentication (JWT via current_user or require_ee())
- Require appropriate permissions (config:write, system:admin)
- Audit all config changes and test attempts
- Validate request payloads via Pydantic models
- Use SIEM service's own connection handling (no new network surface)

## Outstanding Requirements

All plan requirements met:
- [x] CE/EE gating via stub/implementation routers
- [x] 4 admin endpoints for SIEM config management
- [x] Hot-reload service reinit on config update
- [x] Graceful lifecycle integration (startup/shutdown)
- [x] System health endpoint includes SIEM status
- [x] Audit logging on all config operations

## Next Steps

Plan 168-03 will focus on:
- Audit event filtering (topic-based subscription)
- Queue persistence (SQLite/Postgres backing)
- Batch commit thresholds and flushing strategies
- Dashboard UI for audit log viewing and filtering

---

**Generated by:** Claude Code (claude.ai/code)  
**Model:** Haiku 4.5  
**Execution mode:** Autonomous (no checkpoints)
