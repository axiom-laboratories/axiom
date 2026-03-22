---
phase: 42-ee-validation-pass
plan: "01"
subsystem: auth
tags: [rbac, licence, fastapi, ee, docker, postgres, migration]

# Dependency graph
requires:
  - phase: 39-ee-test-keypair-dev-install
    provides: axiom-test-agent EE image with valid/expired licence env files
  - phase: 41-ce-validation-pass
    provides: EE stack restored to operational state after CE validation tests

provides:
  - "Admin-only guard on GET /api/licence (HTTP 403 for operator/viewer, 200 for admin)"
  - "role column restored to CE User model and users DB table"
  - "migration_v36.sql: ALTER TABLE users ADD COLUMN IF NOT EXISTS role"
  - "EE agent image rebuilt with patched main.py and db.py tagged localhost/master-of-puppets-server:v3"
  - "Stack running in EE mode with valid AXIOM_LICENCE_KEY and all 8 feature flags active"

affects: [42-ee-validation-pass-02, 43-foundry-smoke-test, 44-scheduler-smoke-test]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EE image rebuild via FROM axiom-test-agent:latest + COPY agent_service/ (bypasses devpi when EE_INSTALL not available)"
    - "getattr(user, 'role', None) pattern for safe role access — consistent with deps.py require_permission pattern"
    - "role column server_default='admin' preserves existing admin user on fresh CE deploy"
    - "EE stack requires manual AXIOM_LICENCE_KEY env inject on docker compose up — not persisted in .env"

key-files:
  created:
    - puppeteer/migration_v36.sql
  modified:
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/db.py

key-decisions:
  - "Used getattr(current_user, 'role', None) != 'admin' instead of direct attribute access — CE User model lacks role column without EE migration, getattr with None default provides safe fallback"
  - "Added role column back to CE db.py User model (server_default='admin') — EE users router requires it, stripped from CE in commit bbcb209 but not re-added by EE plugin startup"
  - "EE image rebuild uses FROM axiom-test-agent:latest + COPY approach — devpi root/dev index lost after container restart, full EE_INSTALL=1 rebuild not possible without re-uploading axiom-ee wheel"
  - "migration_v36.sql required for existing deployments — create_all does not ALTER existing tables"

patterns-established:
  - "EE image patching: docker build -t axiom-test-agent:latest -f Dockerfile.ee-patch (FROM axiom-test-agent + COPY agent_service)"
  - "EE stack restart: AXIOM_LICENCE_KEY=$(grep ...) docker compose up -d --no-build agent"
  - "Verify EE active: docker logs puppeteer-agent-1 | grep 'EEPlugin.register() complete'"

requirements-completed: [EEV-03]

# Metrics
duration: 14min
completed: 2026-03-21
---

# Phase 42 Plan 01: EE Licence Endpoint Admin Guard Summary

**Admin-only guard on GET /api/licence using getattr role check, with role column restored to User model and EE image rebuilt from axiom-test-agent base**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-03-21T18:37:02Z
- **Completed:** 2026-03-21T18:51:21Z
- **Tasks:** 2
- **Files modified:** 3 (main.py, db.py, migration_v36.sql created)

## Accomplishments

- Patched `GET /api/licence` in `main.py` to return HTTP 403 for non-admin users using `getattr(current_user, "role", None) != "admin"` check
- Restored `role` column to CE `User` SQLAlchemy model in `db.py` with `server_default='admin'` so existing admin user works on fresh deploys
- Created `migration_v36.sql` to add `role` column to existing DB deployments via `ALTER TABLE users ADD COLUMN IF NOT EXISTS role`
- Rebuilt EE agent image using `FROM axiom-test-agent:latest` + `COPY agent_service/` approach (devpi unavailable), tagged as `localhost/master-of-puppets-server:v3`
- Verified admin token returns HTTP 200, operator token returns HTTP 403 on `GET /api/licence`
- EE stack confirmed operational: all 8 feature flags active (foundry, audit, webhooks, triggers, rbac, resource_limits, service_principals, api_keys)

## Task Commits

1. **Task 1: Patch GET /api/licence to admin-only in main.py** - `221c059` (fix)
2. **Task 2: Add role column to db.py, migration_v36.sql, rebuild EE image** - `bad85c0` (fix)

## Files Created/Modified

- `puppeteer/agent_service/main.py` - Admin-only guard added to `get_licence` handler using `getattr` pattern
- `puppeteer/agent_service/db.py` - `role` column added to `User` model (`String`, `server_default='admin'`)
- `puppeteer/migration_v36.sql` - ALTER TABLE migration adding role column with DEFAULT 'admin'

## Decisions Made

- Used `getattr(current_user, "role", None) != "admin"` instead of `current_user.role != "admin"` — the CE User model (without migration) lacks the role attribute, causing AttributeError 500. The `getattr` pattern is consistent with `deps.py` line 100's `require_permission` function.
- Added `role` back to CE `db.py` `User` model — it was stripped in commit `bbcb209` when EE DB tables were extracted. However the EE users router (`ee/users/router.py`) reads and writes `u.role` directly on the CE User model, so the column must exist in CE too.
- Chose `FROM axiom-test-agent:latest + COPY agent_service/` Docker build approach — the devpi `root/dev` index was lost after container restart (volume not persisted through CE validation teardown). This is faster than re-uploading the wheel and re-running the full build.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed AttributeError on current_user.role in CE mode**
- **Found during:** Task 2 (rebuild and smoke test)
- **Issue:** CE `User` model has no `role` attribute — direct attribute access `current_user.role != "admin"` raised `AttributeError: 'User' object has no attribute 'role'` → HTTP 500
- **Fix:** Changed to `getattr(current_user, "role", None) != "admin"` — consistent with `deps.py` line 100 pattern
- **Files modified:** `puppeteer/agent_service/main.py`
- **Verification:** No 500 errors in container logs after fix
- **Committed in:** `bad85c0` (Task 2 commit)

**2. [Rule 1 - Bug] Restored missing role column to CE User model**
- **Found during:** Task 2 (smoke test — admin got 403 instead of 200 because `getattr` returned `None`)
- **Issue:** `role` column stripped from CE `db.py` User model in commit `bbcb209`, but EE users router accesses `u.role` directly. Column never added back by EE plugin startup (`EEBase.metadata.create_all` only creates EE-specific tables).
- **Fix:** Added `role: Mapped[str] = mapped_column(String, default="admin", server_default="admin")` to CE `User` model; applied `ALTER TABLE users ADD COLUMN IF NOT EXISTS role` migration to running DB; created `migration_v36.sql` for future deployments
- **Files modified:** `puppeteer/agent_service/db.py`, `puppeteer/migration_v36.sql`
- **Verification:** Admin user returns HTTP 200, operator user returns HTTP 403 on `GET /api/licence`
- **Committed in:** `bad85c0` (Task 2 commit)

**3. [Rule 3 - Blocking] Devpi root/dev index unavailable — used alternative EE image build**
- **Found during:** Task 2 (EE rebuild attempt)
- **Issue:** `docker compose build --build-arg EE_INSTALL=1 agent` requires devpi `root/dev` index with `axiom-ee==0.1.0`. The `root/dev` stage was lost after devpi container restart (CE validation Phase 41 wiped volumes). Direct rebuild not possible.
- **Fix:** Built patched EE image using `FROM axiom-test-agent:latest + COPY agent_service/` Dockerfile — preserves EE plugin from the existing 28hr-old EE build while injecting updated `agent_service/`
- **Files modified:** None (build process only)
- **Verification:** `docker run ... python3 -c "entry_points(group='axiom.ee')"` shows EE plugin present; EE logs show all 8 routers mounted
- **Committed in:** `bad85c0` (Task 2 commit — image build artifact, not source)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for correctness. The role column absence was a latent bug from the CE/EE split refactor. No scope creep.

## Issues Encountered

- devpi `root/dev` stage unavailable — alternative image build approach used (see Deviation 3)
- Initial commit used `current_user.role` (direct access) which caused 500 in CE mode; corrected to `getattr` pattern in same task's follow-up commit

## Next Phase Readiness

- `GET /api/licence` returns 403 for operator/viewer, 200 for admin — EEV-03 backend prerequisite satisfied
- EE stack operational with valid licence: 8/8 feature flags active, 29 tables (28 schema + apscheduler_jobs)
- `puppeteer-agent-1` running `localhost/master-of-puppets-server:v3` (EE build with patched code)
- Phase 42 Plan 02 (`verify_ee_pass.py` script) can now proceed

---
*Phase: 42-ee-validation-pass*
*Completed: 2026-03-21*
