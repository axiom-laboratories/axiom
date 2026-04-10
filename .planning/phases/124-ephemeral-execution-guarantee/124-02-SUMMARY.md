---
phase: 124-ephemeral-execution-guarantee
plan: 02
subsystem: "execution-mode-validation"
tags:
  - "hardening"
  - "fail-fast"
  - "api-validation"
  - "startup-checks"
dependency_graph:
  requires:
    - phase-124-01
  provides:
    - "Compose generator rejects EXECUTION_MODE=direct"
    - "Server startup validation for NODE_EXECUTION_MODE"
  affects:
    - "node-deployment-flow"
    - "operator-onboarding"
tech_stack:
  added: []
  patterns:
    - "HTTPException with 400 status for invalid config"
    - "Startup-time sys.exit(1) for env var validation"
key_files:
  created: []
  modified:
    - puppeteer/agent_service/main.py
decisions:
  - "Validation timing: startup (fail fast) rather than per-request for NODE_EXECUTION_MODE"
  - "Error messages include actionable guidance (Docker socket mount pattern)"
  - "Use _sys import pattern consistent with rest of codebase"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-08"
  tasks_completed: 2
  commits: 1
---

# Phase 124 Plan 02: Compose Generator & Startup Hardening Summary

**Execution Mode hardening: Fail-fast validation prevents misconfiguration of direct execution on control plane**

## Objective

Harden the compose generator and server startup to reject `EXECUTION_MODE=direct` configuration at validation time (not runtime). Prevents broken compose files and catches operator misconfiguration immediately on server startup.

## What Was Built

Two complementary validation checks:

### 1. Compose Generator Validation (Endpoint)

**File:** `puppeteer/agent_service/main.py:501-514`

The `GET /api/node/compose` endpoint now validates the effective execution mode before generating the docker-compose.yaml file:

```python
# Phase 124: Reject direct execution mode
if effective_execution_mode == "direct":
    raise HTTPException(
        status_code=400,
        detail="EXECUTION_MODE=direct is not supported. Use 'docker', 'podman', or 'auto' instead. "
               "For Docker-in-Docker, mount the host Docker socket and use EXECUTION_MODE=docker or EXECUTION_MODE=auto."
    )
```

**Behavior:**
- Checks either the `execution_mode` query param or `NODE_EXECUTION_MODE` env var
- Returns HTTP 400 with clear, actionable error message if direct mode is detected
- Message tells operator valid alternatives and the Docker socket mount pattern
- Prevents returning a misconfigured compose file

### 2. Server Startup Validation (Lifespan)

**File:** `puppeteer/agent_service/main.py:81-86`

The FastAPI lifespan function validates `NODE_EXECUTION_MODE` at startup, immediately after database initialization:

```python
# Phase 124: Validate NODE_EXECUTION_MODE at startup
import sys as _sys
node_execution_mode = os.getenv("NODE_EXECUTION_MODE", "auto").lower()
if node_execution_mode == "direct":
    logger.error("NODE_EXECUTION_MODE=direct is not supported. Use 'docker', 'podman', or 'auto'.")
    _sys.exit(1)
```

**Behavior:**
- Runs before any endpoints become available
- Logs error with actionable message
- Exits with code 1 (config error) to signal Docker Compose that startup failed
- Operator sees error immediately on `docker compose up` rather than later during compose endpoint calls

## Task Completion

| Task | Status | Details |
|------|--------|---------|
| 1. Compose Generator Validation | ✓ Complete | HTTP 400 rejection with socket mount guidance |
| 2. Server Startup Validation | ✓ Complete | sys.exit(1) with logged error message |

## Verification Results

All success criteria met:

```bash
✓ Compose endpoint rejects EXECUTION_MODE=direct with HTTP 400
✓ Error message is actionable (lists valid alternatives, explains Docker socket pattern)
✓ Server startup validates NODE_EXECUTION_MODE env var
✓ Server exits with code 1 if NODE_EXECUTION_MODE=direct
✓ Error logged before exit for operator visibility
✓ All validation happens before or at startup (fail fast)
```

### Grep Verification

Compose validation found:
```
if effective_execution_mode == "direct":
    raise HTTPException(
        status_code=400,
        detail="EXECUTION_MODE=direct is not supported. Use 'docker', 'podman', or 'auto' instead. "
               "For Docker-in-Docker, mount the host Docker socket..."
```

Server startup validation found:
```
if node_execution_mode == "direct":
    logger.error("NODE_EXECUTION_MODE=direct is not supported...")
    _sys.exit(1)
```

## Integration Notes

- **Endpoint path:** Both `GET /api/node/compose` and `GET /api/installer/compose` are decorated on the same handler, so both reject direct mode
- **Import pattern:** Uses `import sys as _sys` locally within lifespan, consistent with existing codebase pattern (lines 82, 155, etc.)
- **Backward compatibility:** Non-direct modes (docker, podman, auto) are unaffected; no API contract changes
- **Error handling:** HTTPException is the standard FastAPI pattern already used throughout main.py

## Deviations from Plan

None — plan executed exactly as specified.

## Related Requirements

- **EPHR-02:** EXECUTION_MODE=direct flagged as unsafe; operator warned or blocked in production
  - Status: Addressed by this plan (compose generator and startup blocking)

## Connection to Phase 124

This plan builds on Phase 124-01 which added the `execution_mode` column to the Node database model. The next plan (124-03) will handle the heartbeat integration and API response exposure. This plan focuses on the hardening/validation layer that ensures direct mode can never be configured.

## Next Steps

- **Phase 124-03:** Execute heartbeat integration to collect and persist execution_mode from nodes
- **Phase 124-04:** Document removal and dead code cleanup

## Files Modified

- `puppeteer/agent_service/main.py`: +17 lines (validation logic), -3 lines (outdated comment)

## Commits

| Hash | Message |
|------|---------|
| 04d8d21 | feat(124-02): harden compose generator and server startup to reject EXECUTION_MODE=direct |

---

**Plan Status:** COMPLETE
**Execution Time:** 2 minutes 5 seconds
**Generated:** 2026-04-08T20:12:00Z
