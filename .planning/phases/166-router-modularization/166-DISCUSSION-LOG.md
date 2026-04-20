# Phase 166: Router Modularization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 166-router-modularization
**Areas discussed:** Router boundary drawing, main.py residual shape, CE smelter_router wiring, Behavior equivalence standard

---

## Router boundary drawing

| Option | Description | Selected |
|--------|-------------|----------|
| Collapse into 7 (roadmap) | Follow roadmap names: auth, jobs, nodes, workflows, foundry, admin, system | |
| 6 routers (no foundry CE) | Drop foundry_router (EE-only); collapse fringe groups into the 6 natural domains | ✓ |
| You decide | Claude picks groupings | |

**User's choice:** 6 routers — agreed with Claude's analysis that there are zero CE foundry routes in main.py (confirmed by grep). The `foundry_router` in the roadmap is a planning artifact.

**Notes:** User asked Claude to verify CE foundry route count before committing. Grep confirmed `/api/foundry` is an EE-only prefix with no CE handlers in main.py.

Final groupings:
- `auth_router` ← Authentication
- `jobs_router` ← Jobs, Job Definitions, Job Templates, CI/CD Dispatch
- `nodes_router` ← Nodes, Node Agent
- `workflows_router` ← Workflows
- `admin_router` ← Admin, Signatures, Alerts & Webhooks, Headless Automation
- `system_router` ← System, Health, Schedule

---

## main.py residual shape

| Option | Description | Selected |
|--------|-------------|----------|
| Pure shell | App + middleware + include_router only; WebSocket /ws moves to a router | ✓ |
| Shell + special routes | Retain WebSocket and HTML response routes in main.py | |
| You decide | Claude decides | |

**User's choice:** Pure shell — zero route handlers remain in main.py.

---

## CE smelter_router wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Wire it in during Phase 166 | Fix inconsistency; use existing CE smelter_router.py; remove inline duplicates | ✓ |
| Leave as-is | Move 2 smelter routes into another router inline; delete unused file | |
| You decide | Claude decides | |

**User's choice:** Wire in the existing CE `routers/smelter_router.py` as part of this modularization pass.

---

## Behavior equivalence standard

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAPI diff + full pytest | Schema diff before/after + no new test failures | ✓ |
| OpenAPI diff only | Schema proof only | |
| Request-level smoke per route | Hit every endpoint with a real request | |

**User's choice:** OpenAPI diff + full pytest. No per-route smoke test required.

---

## Claude's Discretion

- Router prefix strategy (inline full paths vs. shared prefix)
- WebSocket router placement (system_router.py vs. dedicated ws_router.py)
- Circular import mitigation within router files

## Deferred Ideas

None.
