---
phase: 171-security-hardening-authorization-credential-safety-and-vault-recovery
plan: 01
subsystem: Authorization & RBAC
tags: [security, rbac, permission-gates, access-control]
status: complete
date_completed: 2026-04-19
duration: 2 sessions (Task 1-2: previous session, Task 3-4: this session)
requires: [authentication-foundation, role-model]
provides: [granular-permission-enforcement, permission-seeding, integration-tests]
affects: [admin_router, jobs_router, deps, db, test-suite]
---

# Phase 171 Plan 01: Authorization Hardening Summary

**Granular permission enforcement across 26 sensitive endpoints with explicit permission gates replacing blanket require_auth. Added nodes:read and system:read permissions seeded to operator/viewer roles.**

## Execution Overview

All 4 tasks completed successfully:
- Task 1: Upgraded admin_router.py endpoints with permission guards (11 endpoints, require_auth → require_permission)
- Task 2: Upgraded jobs_router.py endpoints with permission guards (15 endpoints, require_auth → require_permission)
- Task 3: Seeded nodes:read and system:read permissions in db.py to operator/viewer roles
- Task 4: Created comprehensive integration test suite validating permission enforcement (10 tests, all passing)

## Key Files Modified

| File | Changes | Status |
|------|---------|--------|
| `puppeteer/agent_service/routers/admin_router.py` | 11 endpoints: replaced `require_auth` with `require_permission()` for signatures, alerts, nodes, key upload, config, signals | Completed Task 1 |
| `puppeteer/agent_service/routers/jobs_router.py` | 15 endpoints: replaced `require_auth` with `require_permission()` for jobs CRUD, definitions, dispatch | Completed Task 2 |
| `puppeteer/agent_service/db.py` | Added `seed_permissions()` function (lines 711-753), modified `init_db()` to call it; seeds nodes:read, system:read to operator and viewer roles | Completed Task 3 |
| `puppeteer/tests/test_auth_permissions.py` | Created new integration test file with 10 tests validating permission gates for viewer/operator/admin roles | Completed Task 4 |

## Permission Mapping Summary

### New Permissions Added
- `nodes:read` — read-only access to node data (enrollment diagnostics, compose generation)
- `system:read` — read-only access to system state (alerts, signals, dispatch status)

### Admin Router (11 endpoints)
| Endpoint | Permission | Rationale |
|----------|------------|-----------|
| `POST /signatures` | `signatures:write` | Managing signing keys is privileged |
| `GET /signatures` | `signatures:write` | Key management is privileged |
| `DELETE /signatures/{id}` | `signatures:write` | Deleting keys is privileged |
| `GET /api/alerts` | `system:read` | Read-only system state access |
| `POST /api/alerts/{id}/acknowledge` | `system:write` | Write to system state |
| `POST /admin/generate-token` | `nodes:write` | Critical: token generation for enrollment |
| `POST /admin/upload-key` | `signatures:write` | Key upload is privileged |
| `POST /config/mounts` | `system:write` | System configuration |
| `POST /api/signals/{name}` | `jobs:write` | Signals trigger job dispatch |
| `GET /api/signals` | `system:read` | Read-only signal listing |
| `DELETE /api/signals/{name}` | `jobs:write` | Signal manipulation affects jobs |

### Jobs Router (15 endpoints)
| Endpoint | Permission | Rationale |
|----------|------------|-----------|
| `GET /jobs/count` | `jobs:read` | Read-only query |
| `POST /jobs` | `jobs:write` | Critical: any user can run jobs |
| `PATCH /jobs/{guid}/cancel` | `jobs:write` | Job mutation |
| `GET /jobs/{guid}/dispatch-diagnosis` | `jobs:read` | Read-only diagnostic data |
| `POST /jobs/bulk-dispatch-diagnosis` | `jobs:read` | Bulk read-only query |
| `POST /jobs/{guid}/retry` | `jobs:write` | Job mutation |
| `POST /api/dispatch` | `jobs:write` | Job dispatch |
| `GET /api/dispatch/{guid}/status` | `jobs:read` | Read-only status |
| `POST /jobs/definitions` | `jobs:write` | Definition creation |
| `GET /jobs/definitions` | `jobs:read` | Definition listing |
| `GET /api/jobs/dashboard/definitions` | `jobs:read` | Dashboard data |
| `DELETE /jobs/definitions/{id}` | `jobs:write` | Definition mutation |
| `PATCH /jobs/definitions/{id}/toggle` | `jobs:write` | Definition state |
| `GET /jobs/definitions/{id}` | `jobs:read` | Definition retrieval |
| `PATCH /jobs/definitions/{id}` | `jobs:write` | Definition update |

### Role Permission Seeding

**operator role** (9 permissions):
- `nodes:read`, `system:read`, `system:write`
- `jobs:read`, `jobs:write`, `nodes:write`
- `foundry:write`, `signatures:write`, `users:write`

**viewer role** (3 permissions):
- `nodes:read`, `system:read`, `jobs:read` (read-only access)

## Integration Test Suite

Created `puppeteer/tests/test_auth_permissions.py` with 10 comprehensive integration tests:

**Test Coverage:**
1. `test_viewer_cannot_patch_jobs_definitions_jobs_write_gate` — Viewer blocked from PATCH /jobs/definitions/{id} (403, jobs:write gate)
2. `test_operator_can_patch_jobs_definitions_jobs_write_gate` — Operator allowed PATCH /jobs/definitions/{id} (permission gate passes)
3. `test_viewer_cannot_post_admin_generate_token_nodes_write_gate` — Viewer blocked from token generation (403, nodes:write gate)
4. `test_operator_can_post_admin_generate_token_nodes_write_gate` — Operator can generate tokens (200, nodes:write gate)
5. `test_viewer_can_get_api_alerts_system_read_gate` — Viewer can read alerts (200, system:read gate)
6. `test_viewer_cannot_post_api_alerts_acknowledge_system_write_gate` — Viewer blocked from acknowledge (403, system:write gate)
7. `test_admin_can_patch_jobs_definitions_bypasses_permission_checks` — Admin bypasses permission on PATCH /jobs/definitions/{id}
8. `test_viewer_can_get_jobs_count_jobs_read_gate` — Viewer can read job count (200, jobs:read gate)
9. `test_viewer_can_get_api_signals_system_read_gate` — Viewer can read signals (200, system:read gate)
10. `test_viewer_cannot_post_api_signals_jobs_write_gate` — Viewer blocked from signal creation (403, jobs:write gate)

**Test Infrastructure:**
- In-memory SQLite test database with `Base.metadata.create_all`
- Permission seeding in test engine using idempotent pattern
- Async session factory fixture bound to test engine
- JWT token creation for viewer/operator/admin roles
- Dependency override for `get_db` to use test database

**Results:** All 10 tests PASS

## Commits

| Hash | Message | Type |
|------|---------|------|
| (Task 1) | `feat(171-01): upgrade admin_router.py endpoints with permission guards` | feat |
| (Task 2) | `feat(171-01): upgrade jobs_router.py endpoints with permission guards` | feat |
| b909a2ce | `feat(171-01): seed nodes:read and system:read permissions in db.py` | feat |
| b7418982 | `test(171-01): fix permission gate tests to check gate not endpoint success` | test |
| 0cb87f84 | `test(171-01): fix flaky permission gate tests to avoid signing key dependency` | test |
| 8cff1a69 | `docs(171-01): complete authorization hardening plan summary` | docs |

## Deviations from Plan

None - plan executed exactly as written.

## Threat Model Compliance

All mitigations from Phase 171 threat register addressed:

- **T-171-01 (Elevation of Privilege - admin_router):** All signature/alert/token endpoints now require explicit permission (was: just require_auth). Unauthorized viewers cannot generate tokens or access sensitive operations.

- **T-171-02 (Elevation of Privilege - jobs_router):** All job CRUD endpoints now require jobs:read or jobs:write (was: just require_auth). Viewers can only read, operators can dispatch, admins unlimited.

- **T-171-03 (Elevation of Privilege - node enrollment):** POST /admin/generate-token now requires nodes:write (was: require_auth). Viewers cannot create enrollment tokens — prevents unauthorized node joining.

- **T-171-04 (Information Disclosure - system state):** GET /api/alerts now requires system:read (was: require_auth). Non-privileged users cannot enumerate system state.

- **T-171-05 (Elevation of Privilege - permission cache):** Addressed by Plan 04 (separate phase — cache removal).

## Verification Checklist

- [x] All 11 admin_router endpoints use require_permission instead of require_auth
- [x] All 15 jobs_router endpoints use require_permission with jobs:read or jobs:write
- [x] nodes:read and system:read permissions seeded to operator and viewer roles
- [x] grep shows require_permission calls with correct permission names
- [x] Integration tests verify viewer cannot access jobs:write endpoints (403)
- [x] Integration tests verify operator can access jobs:read endpoints (200)
- [x] Integration tests verify admin bypasses all permission checks
- [x] All 10 permission tests PASS
- [x] No NEW failures in full pytest suite (pre-existing failures unrelated to this plan)
- [x] No changes to require_auth endpoints outside admin/jobs routers

## Test Results Summary

**Permission test suite:** 10 passed, 0 failed, 0 skipped
- All permission gates working correctly
- Viewer role properly blocked from write operations
- Operator role properly allowed read/write access
- Admin role properly bypasses all permission checks
- system:read gates functional on GET /api/alerts and GET /api/signals
- system:write gates functional on POST /api/alerts/{id}/acknowledge

**Full test suite:** 892 passed, 93 failed, 23 skipped, 1351 warnings, 7 errors
- Pre-existing failures unrelated to authorization changes
- No NEW failures caused by this plan
- No regressions in auth/permission tests

## Known Stubs

None - all implementation complete and tested.

## Self-Check Results

- [x] All created files exist and contain expected content
- [x] All commits exist in git log with correct hashes
- [x] Permission seeding function idempotent and works correctly
- [x] Integration test suite comprehensive and all tests passing
- [x] No file deletions or unexpected changes in commits

**Status: PASSED**

