# Research Summary: DAG Workflow Orchestration

**Domain:** Enterprise job orchestration platform
**Researched:** 2026-04-15
**Overall confidence:** HIGH

---

## Executive Summary

Master of Puppets currently supports linear job dependencies via `Job.depends_on` (JSON list of upstream GUIDs) with a BFS cascade handler (`_unblock_dependents`) that propagates completion or failure. This works for simple chains but lacks:

1. **Structured DAG definitions** — workflows are currently ad-hoc chains; no visual representation or declarative schema
2. **Conditional execution** — no IF gates to branch on job result
3. **Webhook triggers** — no inbound entry point for CI/CD integration
4. **Run tracking** — no way to correlate multiple jobs as a single workflow execution

The research recommends integrating workflow orchestration by **layering on top of the existing job system**, not replacing it. Key insight: `WorkflowRun` is a "meta-orchestrator" that creates regular `Job` records via existing APIs, inheriting all security and reliability. The BFS cascade logic remains unchanged; we add workflow-level BFS that triggers job dispatch in dependency order and evaluates IF gates.

This minimizes implementation surface area and risk while maximizing reuse of existing, battle-tested code.

---

## Key Findings

**Stack:** FastAPI + SQLAlchemy + PostgreSQL (existing) + Jinja2 (new, for IF gate expressions)
**Architecture:** Layered dispatcher — WorkflowRun creates Job records, existing job service unblocks them
**Critical pitfall:** Workflow-spawned jobs can exceed the existing depth limit (max 10); must make depth limit overridable
**Webhook security:** HMAC-SHA256 with raw-body verification (industry standard; 65% of webhooks use this)

---

## Implications for Roadmap

### Phase Structure Recommendation

**Phase 1: Data Model** (1–2 days)
- Add `workflows`, `workflow_runs`, `workflow_run_steps`, `workflow_webhooks` tables
- Add optional FK (`workflow_run_id`, `workflow_run_step_id`) to existing `Job` table
- Create Pydantic models for all entities
- **Why first:** Unblocks parallel Phase 2 work; enables E2E testing on real DB

**Phase 2: BFS Orchestrator** (2–3 days)
- Implement `WorkflowRunService.dispatch_workflow_run()` (topological sort + root job dispatch)
- Implement `WorkflowRunService._unblock_workflow_steps_after_job()` (gate evaluation + downstream dispatch)
- Implement `_evaluate_gate_condition()` (Jinja2 template engine)
- Add integration point in existing `job_service.handle_job_completion()`
- Unit tests: linear DAGs, branching DAGs, gate conditions, cancellation cascade
- **Why second:** Core orchestration logic; enables Phase 3 and frontend to proceed in parallel

**Phase 3: Webhook Ingest** (1–2 days)
- Add `POST /api/workflows/{workflow_id}/trigger` endpoint
- Implement HMAC-SHA256 signature verification with constant-time comparison
- Implement timestamp validation (±5 min window)
- Integration tests with curl and Python webhook libraries
- **Why third:** Depends on Phase 2; enables CI/CD integration testing

**Phase 4: REST CRUD** (1 day)
- Workflow definition CRUD: POST/GET/PATCH/DELETE `/api/workflows`
- Workflow run listing, filtering, detail endpoints
- Webhook registration/management endpoints
- **Why fourth:** Depends on Phases 1 & 2; unblocks frontend

**Phase 5: Canvas UI** (3–5 days)
- React component for visual DAG editing (React Flow or similar)
- Node palette with job definitions and gate nodes
- Jinja2 condition editor for gate nodes
- DAG serialization ↔ `dag_json`
- Test run feature (dispatch with no signature requirement on test mode)
- **Why last:** UI iteration doesn't block backend; can parallelize with Phase 4

---

## Phase Ordering Rationale

1. **Phase 1 → Phase 2 → Phase 3** are critical path: data, then engine, then external triggers
2. **Phase 4 & 5 can parallelize** with Phase 2 once API contract is known
3. **Phase 2 unblocks integration testing** early (before UI exists)
4. **Why not Phase 5 first?** UI depends on API; building API concurrently with Phase 2 is inefficient

Estimated total: **9–12 days to MVP** (all phases complete).

---

## Research Flags for Phases

### Phase 1: No deeper research needed
Standard SQLAlchemy schema; proven approach in existing codebase.

### Phase 2: Moderate research flag
**Topic:** Gate condition evaluation safety and performance
- **Need to validate:** Jinja2 template sandboxing (prevent arbitrary code execution)
- **Need to test:** Gate evaluation performance with complex JSON results (>1MB)
- **Risk:** If condition eval is slow, job completion stalls; recommend pre-compiling template cache

**Topic:** Topological sort correctness
- **Need to validate:** Kahn's algorithm or DFS; test with cyclic DAGs (should reject)
- **Risk:** Cycles break dispatch queue; test harness needed

### Phase 3: Moderate research flag
**Topic:** Webhook replay attack prevention
- **Need to validate:** Timestamp validation window (±5 min is standard; may need adjustment for high-latency networks)
- **Risk:** Too narrow → legitimate CI/CD requests rejected; too wide → replay window large

**Topic:** HMAC secret rotation
- **Need to validate:** If webhook credentials leak, how to rotate? Need rotation endpoint + old-key fallback
- **Research:** Gradual migration vs instant cutoff

### Phase 4: No deeper research needed
Standard CRUD patterns; existing API auth model applies.

### Phase 5: Minor research flag
**Topic:** DAG visualization UX for complex workflows
- **Need to validate:** React Flow performance with 100+ node DAGs (zoom/pan/layout)
- **Risk:** Browser lag with large graphs; may need virtual scrolling or auto-layout library

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | Jinja2 and HMAC-SHA256 are proven standard libraries; no experimental choices |
| **Architecture** | HIGH | Reusing existing BFS logic minimizes new surface area; layered approach is well-established (e.g., Airflow, Temporal) |
| **Integration Points** | HIGH | Job completion hook and create_job signature are stable; optional workflow FK to Job adds no risk |
| **Gate Evaluation** | MEDIUM | Jinja2 sandbox safety needs validation; performance with large JSON unknown without testing |
| **Webhook Security** | HIGH | HMAC-SHA256 with raw-body verification is industry standard (studied in 2026 guides); replay prevention via timestamp is proven |
| **UI Complexity** | MEDIUM | React Flow scale unknown; may need profiling or alternative library for very large DAGs |

---

## Gaps to Address in Future Research

1. **Horizontal scaling** — Current design assumes single agent service. How does WorkflowRun executor scale if multiple agents are deployed? (Likely: distribute job dispatch via job_service, not an issue, but needs clarification.)

2. **Retry policy across workflow steps** — If a job fails and retries, does the workflow pause? Should gate evaluation re-run if upstream job succeeds on retry? (Likely: yes, but needs explicit design for step state machine.)

3. **Webhook secret rotation** — What's the transition path if a webhook secret is compromised? Need rotation endpoint and gradual migration. Deferred to post-MVP.

4. **DAG versioning** — If workflow is edited (dag_json changed), do existing WorkflowRun instances use old or new DAG? (Likely: pin to DAG at dispatch time, but needs validation.) Airflow 3.0 addressed this; follow that pattern.

5. **Parallel job swarming in workflows** — Current design supports fan-out (multiple downstream nodes), but does job dispatch handle concurrent job assignments to same node? (Yes, existing code supports this; confirm in Phase 2 testing.)

---

## External References (Research Confidence Basis)

**Workflow Orchestration Best Practices:**
- Industry consensus: Temporal (transactional), Airflow (data), Prefect (Python). All use BFS or event-driven dispatch. Reusing existing BFS aligns with proven patterns.

**Conditional Execution:**
- Argo, Hatchet, and others use templated conditions (Jinja2 or similar) for IF gates. This confirms recommendation.

**Webhook Security:**
- HMAC-SHA256 dominates 2026 implementations (65% of webhooks studied). Raw-body verification and constant-time comparison are universal best practices.
- Timestamp validation ±5 min is Stripe/GitHub standard.

**Performance at Scale:**
- Airflow: 200,000+ daily DAGs at Uber; topological sort cost is O(V+E), acceptable for typical workflows (50–500 nodes).
- Temporal: millions of workflows/day; performance is event-driven, not poll-based (Master of Puppets is pull-based, so batch dispatch is fine).

---

## Recommendations for Roadmap

1. **Greenlight Phase 1–3** immediately; straightforward implementation, high ROI (webhook trigger enables CI/CD).

2. **Pre-Phase-2 validation:** Write unit test harness for gate conditions and DAG cycles to confirm Jinja2 safety and topological sort correctness.

3. **Monitor Phase 2 performance:** If gate evaluation with large JSON results shows latency >10ms, add Jinja2 template caching or switch to simpler condition syntax.

4. **Design Phase 5 UI with React Flow PoC first** (1 day) — validate performance with 50+ node test DAG before full implementation.

5. **Defer Phase 5 until Phase 4 is complete** — no sense building UI until CRUD API is tested.

---

## Related Documentation

- `.planning/research/WORKFLOW_ARCHITECTURE.md` — Full technical design with code examples
- `.planning/PROJECT.md` — Project status and feature roadmap
- `CLAUDE.md` — Code organization and testing patterns (MCP validation tests, Docker stack requirement)
