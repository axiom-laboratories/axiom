---
phase: 124-ephemeral-execution-guarantee
plan: 01
subsystem: backend
type: feature
tags:
  - execution-mode
  - heartbeat
  - node-visibility
  - phase-124
dependencies:
  requires:
    - Phase 123 (cgroup detection pattern established)
  provides:
    - Node.execution_mode persistence in DB
    - HeartbeatPayload with execution_mode field
    - NodeResponse with execution_mode field
    - API exposure of execution_mode
  affects:
    - Phase 127 (dashboard badges will consume execution_mode)
    - Phase 124 subsequent plans (compose generator validation)
tech_stack:
  added: []
  patterns:
    - Heartbeat → DB column → API response (Phase 123 pattern reuse)
    - Optional Pydantic fields for backward compatibility
    - Nullable DB columns with IF NOT EXISTS migration pattern
key_files:
  created:
    - puppeteer/migration_v52.sql (new migration file)
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/main.py
decisions: []
metrics:
  duration: ~15 minutes
  completed_date: 2026-04-08T20:20:30Z
  tasks_completed: 4/4
  commits: 4
---

# Phase 124 Plan 01: Server-Side Execution Mode Persistence — COMPLETE

## One-liner

Added server-side persistence of node execution mode detection (docker/podman) following the Phase 123 cgroup detection pattern: DB column, HeartbeatPayload field, heartbeat handler update, and API response exposure.

## Objective

Implement server-side persistence of node execution mode (docker/podman detection) reported in heartbeat payloads. Purpose: Nodes report their detected runtime in every heartbeat; orchestrator stores this for dashboard visibility and later validation logic.

## Summary of Work

### Task 1: Add execution_mode column to Node DB model and migration
- Added `execution_mode: Mapped[Optional[str]]` column to Node model in `puppeteer/agent_service/db.py` (line 153)
- Created migration file `puppeteer/migration_v52.sql` with idempotent `ALTER TABLE nodes ADD COLUMN IF NOT EXISTS execution_mode TEXT`
- Follows Phase 123 migration pattern (nullable String, IF NOT EXISTS for idempotency)
- **Commit:** 4d7ea5b

### Task 2: Extend HeartbeatPayload and NodeResponse models with execution_mode field
- Added `execution_mode: Optional[str] = None` to HeartbeatPayload (line 173 in `models.py`)
- Added `execution_mode: Optional[str] = None` to NodeResponse (line 217 in `models.py`)
- Both fields are Optional with None default for backward compatibility with older nodes
- **Commit:** 10ca2fe

### Task 3: Update heartbeat handler to persist execution_mode from payload to DB
- Updated `receive_heartbeat()` in `puppeteer/agent_service/services/job_service.py` (line 951)
- Added unconditional `node.execution_mode = hb.execution_mode` alongside cgroup field updates
- Follows same pattern as Phase 123 cgroup persistence (stateless, update every heartbeat)
- **Commit:** 1e4e724

### Task 4: Extend get_nodes() endpoint to include execution_mode in NodeResponse
- Updated `list_nodes()` endpoint in `puppeteer/agent_service/main.py` (line 1764)
- Added `"execution_mode": n.execution_mode` to response dict
- Exposes field as "execution_mode" in JSON API, aligned with existing cgroup_version field
- **Commit:** cd14e42

## Verification

All must-haves verified:

- [x] Node table has execution_mode column (nullable String) — Line 153 of db.py
- [x] HeartbeatPayload accepts execution_mode field (Optional[str]) — Line 173 of models.py
- [x] NodeResponse exposes execution_mode field (Optional[str]) — Line 217 of models.py
- [x] Heartbeat handler persists execution_mode to database — Line 951 of job_service.py
- [x] get_nodes() API endpoint returns execution_mode in response dict — Line 1764 of main.py
- [x] All changes are backward compatible (Optional fields, nullable column)
- [x] Migration file created with idempotent ALTER TABLE — migration_v52.sql

## Deviations from Plan

None - plan executed exactly as written. All four tasks completed in sequence with proper backward compatibility and following Phase 123 patterns.

## Integration Points Confirmed

- **Node heartbeat (node.py):** Will include execution_mode from `self.runtime_engine.runtime` (already available after Phase 122 startup block)
- **Backend models:** HeartbeatPayload + NodeResponse both extended with execution_mode field
- **DB schema:** Node model + migration_v52.sql align with established patterns
- **Heartbeat handler:** Updates node.execution_mode unconditionally on every heartbeat (same as cgroup fields)
- **API endpoint:** get_nodes() includes execution_mode in response dict, ready for dashboard consumption

## Next Steps

- Phase 124 Plan 02 will add compose generator validation (reject `execution_mode=direct`)
- Phase 127 will implement dashboard badges showing Docker/Podman runtime for each node

## Test Coverage

Manual verification performed:
1. Python syntax validation: all modified files compile without errors
2. Schema definition: execution_mode column present in Node model
3. Pydantic models: both HeartbeatPayload and NodeResponse include execution_mode
4. Heartbeat handler: update statement in correct location with proper transaction
5. API response: execution_mode included in list_nodes response dict

Full backend test suite to be run during Phase 124 verification phase.
