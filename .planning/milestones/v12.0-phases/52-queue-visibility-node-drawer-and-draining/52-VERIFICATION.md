---
phase: 52-queue-visibility-node-drawer-and-draining
verified: 2026-03-23T18:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 52: Queue Visibility, Node Drawer and DRAINING Verification Report

**Phase Goal:** Operators can diagnose why a PENDING job is stuck, see the full live queue in one place, inspect per-node state in detail, and safely drain a node without forcefully terminating jobs.
**Verified:** 2026-03-23
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A PENDING job's detail drawer shows automatic plain-English dispatch diagnosis that refreshes live via WebSocket | VERIFIED | `Jobs.tsx` has `DispatchDiagnosis` interface, `useEffect` fetching `/jobs/{guid}/dispatch-diagnosis` on PENDING open, `useWebSocket` inside `JobDetailPanel` re-fetching on `node:updated`/`job:updated` events (lines 183–243) |
| 2 | A dedicated Queue view shows PENDING/RUNNING/recently completed jobs; WebSocket-driven, no polling | VERIFIED | `Queue.tsx` (406 lines) with two React Query fetches, `useWebSocket` invalidating `['queue']` prefix on `job:created`/`job:updated`/`node:updated`/`node:heartbeat`; zero `setInterval`/`refetchInterval` in file |
| 3 | Nodes page has per-node detail drawer showing running job, queued jobs, recent history, capabilities | VERIFIED | `Nodes.tsx` has `NodeDetail` interface, row-click state (`nodeDrawerOpen`, `nodeDetail`), `handleNodeClick` fetching `/nodes/{id}/detail`, Sheet drawer rendering all four sections |
| 4 | Admin can set node to DRAINING; DRAINING visible in Nodes and Queue views; no new jobs dispatched to DRAINING node | VERIFIED | `PATCH /nodes/{id}/drain` and `/undrain` endpoints in `main.py` (lines 1579–1605); `pull_work` guard `status in ("TAMPERED", "DRAINING")` in `job_service.py` (line 557); DRAINING amber badge in `Nodes.tsx` (line 383); `Queue.tsx` cross-references DRAINING nodes for badge display |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/tests/test_draining.py` | 8 VIS-04 stubs (all passing) | VERIFIED | 8 tests pass: drain endpoint, undrain endpoint, 409 guard, pull_work skip, heartbeat preservation, list_nodes status, auto-transition to OFFLINE, no-revert-with-active-jobs |
| `puppeteer/tests/test_dispatch_diagnosis.py` | 6 VIS-01 stubs (all passing) | VERIFIED | 6 tests pass: no_nodes_online, capability_mismatch, all_nodes_busy+queue_position, target_node_unavailable, pending_dispatch, queue_position_ordering |
| `puppeteer/tests/test_node_detail.py` | 6 VIS-03 stubs (all passing) | VERIFIED | 6 tests pass: running_job present, running_job absent, eligible_pending with exclusion, 50-cap, 24h history filter, capabilities |
| `puppeteer/agent_service/services/job_service.py` | `_node_is_eligible`, `get_dispatch_diagnosis`, `get_node_detail` | VERIFIED | All three methods at lines 438, 488, 1226 respectively; `_node_is_eligible` called from all three callers |
| `puppeteer/agent_service/main.py` | drain/undrain/dispatch-diagnosis/node-detail endpoints; DRAINING list_nodes guard; heartbeat guard; auto-transition | VERIFIED | `PATCH /nodes/{id}/drain` (line 1579), `PATCH /nodes/{id}/undrain` (line 1594), `GET /jobs/{guid}/dispatch-diagnosis` (line 1167), `GET /nodes/{id}/detail` (line 1519), DRAINING guard in `list_nodes` (line 1486), DRAINING guard in `receive_heartbeat` (line 751), auto-transition in `report_result` (line 1197) |
| `puppeteer/migration_v42.sql` | Documentation + `ALTER TABLE jobs ADD COLUMN target_node_id` | VERIFIED | Exists with both DDL comment (DRAINING is documentation-only) and actual `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS target_node_id VARCHAR` |
| `puppeteer/dashboard/src/views/Queue.tsx` | Read-only queue view, WebSocket, recency window | VERIFIED | 406 lines; `recencyWindow` state (1/6/24h); `subHours` for `date_from`; `useWebSocket` invalidating `['queue']`; no `setInterval` |
| `puppeteer/dashboard/src/AppRoutes.tsx` | `/queue` route | VERIFIED | `lazy(() => import('./views/Queue'))` at line 20; `Route path="queue"` at line 44 |
| `puppeteer/dashboard/src/layouts/MainLayout.tsx` | Queue nav item between Jobs and History | VERIFIED | `ListOrdered` icon imported (line 20); `NavItem to="/queue"` at line 90, sandwiched between `/jobs` (line 89) and `/history` (line 91) |
| `puppeteer/dashboard/src/views/Nodes.tsx` | DRAINING status union, row-click drawer, drain/undrain buttons (admin-gated) | VERIFIED | `'DRAINING'` in status union (line 72); amber badge (line 383); `Sheet` drawer (line 753); `handleDrain`/`handleUndrain` (lines 602–623); admin guard `currentUser?.role === 'admin'` (line 765) |
| `puppeteer/dashboard/src/views/Jobs.tsx` | Amber diagnosis callout in JobDetailPanel for PENDING | VERIFIED | `DispatchDiagnosis` interface (line 82); `useEffect` fetching on PENDING open (line 226); `useWebSocket` refresh (line 233); amber callout JSX (line 270) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.py list_nodes` | `Node.status` | DRAINING guard before freshness check | WIRED | `n.status in ("REVOKED", "TAMPERED", "DRAINING")` at line 1486 bypasses freshness override |
| `job_service.py pull_work` | `_node_is_eligible` | static method call | WIRED | `JobService._node_is_eligible(node, candidate, node_tags, node_caps_dict)` at line 663 |
| `main.py report_result` | `Node.status` | auto-transition after commit | WIRED | DRAINING auto-transition block at lines 1197–1210 runs post-commit; count query sees updated ASSIGNED state |
| `main.py GET /nodes/{id}/detail` | `JobService.get_node_detail` | `await` call | WIRED | `detail = await JobService.get_node_detail(node_id, db)` at line 1521 |
| `JobService.get_node_detail` | `JobService._node_is_eligible` | called per-job in eligibility filter | WIRED | `JobService._node_is_eligible(node, job, node_tags, node_caps_dict)` at line 513 |
| `Nodes.tsx NodeDrawer` | `/api/nodes/{id}/detail` | `authenticatedFetch` on drawer open | WIRED | `authenticatedFetch(\`/nodes/${node.node_id}/detail\`)` in `handleNodeClick` at line 596 |
| `Nodes.tsx drain button` | `PATCH /api/nodes/{id}/drain` | `authenticatedFetch PATCH` | WIRED | `authenticatedFetch(\`/nodes/${nodeId}/drain\`, { method: 'PATCH' })` at line 603 |
| `Jobs.tsx JobDetailPanel` | `GET /api/jobs/{guid}/dispatch-diagnosis` | `authenticatedFetch` when PENDING | WIRED | `authenticatedFetch(\`/jobs/${job.guid}/dispatch-diagnosis\`)` at line 226 |
| `Queue.tsx` | `useWebSocket` | `invalidateQueries` on job/node events | WIRED | `useWebSocket` at line 235; invalidates `['queue']` prefix on four event types |
| `AppRoutes.tsx` | `Queue.tsx` | lazy import + Route | WIRED | `const Queue = lazy(() => import('./views/Queue'))` + `<Route path="queue" element={<Queue />} />` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| VIS-01 | 52-01, 52-02, 52-05 | PENDING job dispatch diagnosis callout with live WebSocket refresh | SATISFIED | `get_dispatch_diagnosis()` in `job_service.py` (5 reason codes); `GET /jobs/{guid}/dispatch-diagnosis` endpoint; amber callout in `Jobs.tsx` `JobDetailPanel` |
| VIS-02 | 52-04 | Dedicated live Queue view, WebSocket-driven, no polling | SATISFIED | `Queue.tsx` (406 lines); two-query architecture; `useWebSocket` sole refresh; `/queue` route and nav entry |
| VIS-03 | 52-01, 52-03, 52-05 | Per-node detail drawer with running job, queued jobs, history, capabilities | SATISFIED | `get_node_detail()` in `job_service.py`; `GET /nodes/{id}/detail` endpoint; `Sheet` drawer in `Nodes.tsx` with all four sections |
| VIS-04 | 52-01, 52-02, 52-05 | Admin DRAINING lifecycle: drain/undrain from drawer; visible in Nodes and Queue; no dispatch to DRAINING | SATISFIED | `PATCH /nodes/{id}/drain` and `/undrain`; `pull_work` DRAINING guard; `receive_heartbeat` status preservation; auto-transition to OFFLINE; DRAINING amber badge in `Nodes.tsx`; DRAINING cross-reference in `Queue.tsx` |

No orphaned requirements detected. All four VIS-01 through VIS-04 requirements are claimed by plans and verified in code. VIS-05 and VIS-06 are explicitly Phase 53 scope and not claimed by any Phase 52 plan.

### Anti-Patterns Found

No code anti-patterns detected. All `placeholder` strings found in scan are HTML form field `placeholder` attributes (input hints) — not code stubs. No `TODO`, `FIXME`, `return null` stubs, or unimplemented handlers found in Phase 52 files.

### Human Verification

Phase 52 Plan 05 included a blocking human verify checkpoint covering all four features. The SUMMARY records the checkpoint was completed and approved (phase completed at 2026-03-23T17:20:14Z with "approved" signal). The following behaviors require a live Docker stack to re-confirm if needed:

1. **Queue view live updates** — Test: Submit a job from Jobs view; verify it appears immediately in Queue view under "Active" without page refresh. Expected: job appears within one WebSocket cycle (~1s). Why human: WebSocket real-time behavior requires a running stack.

2. **PENDING diagnosis callout accuracy** — Test: Submit a job requiring `capability_requirements: {"nonexistent_cap": "1.0"}`; open job detail drawer. Expected: amber callout appears with message mentioning the missing capability. Why human: requires live nodes and job dispatch cycle.

3. **DRAINING end-to-end** — Test: As admin, click a node row, click "Drain Node", observe amber DRAINING badge in Nodes view, submit a job, verify it is not assigned to the draining node. Why human: requires live node connection and job dispatch.

4. **Admin vs non-admin drain visibility** — Test: Log in as operator role, open node detail drawer. Expected: drain/undrain buttons are absent. Why human: RBAC enforcement in UI requires session testing.

### Gaps Summary

No gaps. All four success criteria from the ROADMAP are implemented and verified:

- VIS-01: `get_dispatch_diagnosis()` service method + endpoint + amber callout in `Jobs.tsx` — all wired.
- VIS-02: `Queue.tsx` with two-query architecture, WebSocket-driven, recency window, route, nav entry — all wired.
- VIS-03: `get_node_detail()` service method + endpoint + Sheet drawer in `Nodes.tsx` — all wired.
- VIS-04: drain/undrain endpoints, pull_work guard, heartbeat guard, list_nodes guard, auto-OFFLINE transition, amber badge, admin-gated UI controls — all wired.

All 20 backend tests (test_draining.py: 8, test_dispatch_diagnosis.py: 6, test_node_detail.py: 6) pass. Frontend builds cleanly (`npm run build`: ok, no errors). Frontend test suite: 39 passed, 3 todo across 8 test files. Test failures in the broader suite (`test_attestation.py`, `test_compatibility_engine.py`, `test_device_flow.py`, etc.) are pre-existing Phase 53+ stubs unrelated to Phase 52 scope.

The JWT role-in-payload fix (`"role": user.role` added to `create_access_token` calls in `main.py`) was applied as part of Plan 05 before human verification — this was a prerequisite for admin-gated drain/undrain UI controls to render correctly.

---

_Verified: 2026-03-23T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
