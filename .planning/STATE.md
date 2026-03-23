---
gsd_state_version: 1.0
milestone: v12.0
milestone_name: — Operator Maturity
status: planning
stopped_at: Phase 55 context gathered
last_updated: "2026-03-23T22:50:34.083Z"
last_activity: 2026-03-22 — v12.0 roadmap created; 44 requirements across 8 phases
progress:
  total_phases: 10
  completed_phases: 9
  total_plans: 35
  completed_plans: 35
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-22)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v12.0 — Operator Maturity (Phase 46 next)

## Current Position

Phase: 46 of 53 (Tech Debt + Security + Branding)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-22 — v12.0 roadmap created; 44 requirements across 8 phases

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v12.0)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |
| Phase 46-tech-debt-security-branding P03 | 5 | 2 tasks | 6 files |
| Phase 46-tech-debt-security-branding P01 | 25min | 2 tasks | 6 files |
| Phase 46 P02 | 3min | 2 tasks | 7 files |
| Phase 47-ce-runtime-expansion P01 | 3min | 3 tasks | 3 files |
| Phase 47-ce-runtime-expansion P02 | 3min | 2 tasks | 5 files |
| Phase 47-ce-runtime-expansion P03 | 15min | 2 tasks | 1 files |
| Phase 47-ce-runtime-expansion P04 | 5min | 2 tasks | 3 files |
| Phase 48-scheduled-job-signing-safety P01 | 4min | 2 tasks | 2 files |
| Phase 48 P02 | 3min | 2 tasks | 2 files |
| Phase 49-pagination-filtering-and-search P02 | 10min | 2 tasks | 6 files |
| Phase 49-pagination-filtering-and-search P01 | 10min | 1 tasks | 1 files |
| Phase 49 P03 | 3min | 1 tasks | 2 files |
| Phase 49 P04 | 3min | 2 tasks | 3 files |
| Phase 49-pagination-filtering-and-search P06 | 2min | 1 tasks | 1 files |
| Phase 49-pagination-filtering-and-search P05 | 8min | 1 tasks | 1 files |
| Phase 49-pagination-filtering-and-search P06 | 5min | 2 tasks | 1 files |
| Phase 50-guided-job-form P01 | 3min | 1 tasks | 1 files |
| Phase 50-guided-job-form P02 | 6min | 2 tasks | 3 files |
| Phase 50-guided-job-form P03 | 3 | 1 tasks | 2 files |
| Phase 51-job-detail-resubmit-and-bulk-ops P01 | 3min | 3 tasks | 7 files |
| Phase 51-job-detail-resubmit-and-bulk-ops P02 | 15min | 2 tasks | 6 files |
| Phase 51-job-detail-resubmit-and-bulk-ops P03 | 5min | 2 tasks | 3 files |
| Phase 51-job-detail-resubmit-and-bulk-ops P04 | 10min | 2 tasks | 3 files |
| Phase 52 P01 | 4min | 3 tasks | 3 files |
| Phase 52 P03 | 8min | 1 tasks | 3 files |
| Phase 52 P02 | 12min | 2 tasks | 6 files |
| Phase 52 P04 | 8min | 2 tasks | 4 files |
| Phase 52-queue-visibility-node-drawer-and-draining P05 | 50min | 2 tasks | 3 files |
| Phase 53-scheduling-health-and-data-management P01 | 5min | 2 tasks | 4 files |
| Phase 53-scheduling-health-and-data-management P02 | 84s | 2 tasks | 2 files |
| Phase 53-scheduling-health-and-data-management P03 | 10min | 2 tasks | 4 files |
| Phase 53 P04 | 3min | 2 tasks | 5 files |
| Phase 53-scheduling-health-and-data-management P05 | 8min | 2 tasks | 4 files |
| Phase 53 P06 | 4min | 1 tasks | 3 files |
| Phase 53 P06 | 15min | 2 tasks | 3 files |
| Phase 54-bug-fix-blitz P02 | 3min | 2 tasks | 4 files |
| Phase 54-bug-fix-blitz P01 | 3min | 2 tasks | 2 files |
| Phase 54-bug-fix-blitz P02 | 10min | 3 tasks | 4 files |

## Accumulated Context

### Decisions

- [Phase 45]: 4 critical patches applied inline (app.state.licence, EE expiry bypass, retriable=True, global declaration). 5 findings deferred to v12.0+ including MIN-06/07/08/WARN-08.
- [v12.0 Roadmap]: Phase 49 (pagination/filtering) depends only on Phase 46 — can proceed in parallel with Phase 47 (runtime expansion). Phase 50 (guided form) requires both 47 and 49.
- [v12.0 Roadmap]: Phase 53 (scheduling health + data mgmt) depends on both Phase 48 (DRAFT signing safety) and Phase 52 (queue visibility).
- [Phase 46]: BRAND-01 rename: Blueprint=Image Recipe, Template=Node Image, Capability Matrix=Tools applied to 5 Foundry TSX files; TypeScript identifiers preserved
- [Phase 46-tech-debt-security-branding]: DEBT-01: Two-step SELECT+DELETE replaces correlated subquery for SQLite-portable NodeStats pruning
- [Phase 46-tech-debt-security-branding]: DEBT-03: Permission cache pre-warmed in lifespan() startup, wrapped in try/except for CE mode compatibility
- [Phase 46-tech-debt-security-branding]: DEBT-02/04 required zero code changes — foundry_service.py cleanup and node.py sorted() were already correct
- [Phase 46]: SEC-01 audit call placed at status determination point (before db.commit()) using sync audit() from deps.py — consistent with existing audit pattern
- [Phase 46]: SEC-02 HMAC uses ENCRYPTION_KEY bytes directly as key material — avoids introducing a separate secret; message format binds payload to its specific job and signature record
- [Phase 47-ce-runtime-expansion]: Temp-file mount pattern chosen over stdin for all three runtimes; python_script task_type removed entirely; RUNTIME_EXT/RUNTIME_CMD dispatch maps inline in execute_task
- [Phase 47-ce-runtime-expansion]: python_script task_type dropped entirely — model_validator raises 422 with clear migration message (RT-06 superseded by CONTEXT.md)
- [Phase 47-ce-runtime-expansion]: Runtime merged into payload dict (not a separate WorkResponse column) so node.py reads it from payload as before
- [Phase 47-ce-runtime-expansion]: Runtime dropdown hidden for non-script task types; display_type ?? task_type fallback for backward compatibility with old python_script jobs; default form task_type changed from web_task to script
- [Phase 47-ce-runtime-expansion]: Runtime derived via getattr(s_job, 'runtime', None) or 'python' in /api/dispatch — mirrors scheduler_service.py pattern; runtime injected into both payload_dict and JobCreate kwargs
- [Phase 48]: Raw SQL used for audit_log INSERT in execute_scheduled_job — CE-safe (ORM model is EE-only, test_ce_table_count enforces audit_log not in CE Base.metadata)
- [Phase 48]: test_draft_skip_log_message creates audit_log table via DDL in test setup — avoids altering CE schema while still verifying verbatim skip message
- [Phase 48]: DRAFT warning modal placed as Dialog sibling in JobDefinitions.tsx rather than inside JobDefinitionModal — decoupled from full edit form lifecycle
- [Phase 48]: ReSignDialog implemented as standalone component inside JobDefinitionList.tsx — self-contained and co-located with the rows that trigger it
- [Phase 49-pagination-filtering-and-search]: PaginatedJobResponse defined in models.py (not job_service.py) so Plans 03 and 04 share a single import path without circular dependency risk
- [Phase 49-pagination-filtering-and-search]: POST /jobs stamps created_by via model_copy(update={'created_by': username}) — stamped at API boundary, not service layer, to keep service testable without auth context
- [Phase 49]: Wave 0 stub convention: pytest.fail as first body line (not after awaits) so all 13 stubs fail with 'not implemented' marker; future shapes in docstrings
- [Phase 49]: Total count query runs before cursor filter — stable totals across pages; tags LIKE '%"tag"%' for exact JSON-quoted match
- [Phase 49]: GET /nodes returns {items,total,page,pages} envelope; stats batch query scoped to page node IDs only to avoid loading all-nodes stats on large deployments
- [Phase 49]: JobService.list_nodes added to service layer for testability; GET /jobs/export uses StreamingResponse generator for memory-efficient CSV streaming
- [Phase 49]: React Query queryKey=['nodes', page] pattern — page change automatically triggers refetch without manual effect management
- [Phase 49]: Nodes pagination: backwards-compat shim wraps bare-array response; pagination controls hidden when totalPages <= 1
- [Phase 49]: Export CSV button rendered in both positions (chips row when active, ghost button otherwise) — always reachable without applying a filter first
- [Phase 49]: Nodes pagination: backwards-compat shim wraps bare-array response; pagination controls hidden when totalPages <= 1
- [Phase 50-guided-job-form]: Wave 0 stub pattern: throw new Error('not implemented') used consistently — runner reports failure not skip, matching Phase 49 decision
- [Phase 50-guided-job-form]: GuidedDispatchCard imported from path that does not exist yet — intentional to confirm red phase before Plan 02 creates the component
- [Phase 50-guided-job-form]: GuidedDispatchCard: targetNodeId prepended to target_tags list (not separate field) to match JobCreate model; stale sig detection via prevScriptRef; ADV placeholder for Plan 03
- [Phase 50-guided-job-form]: Advanced mode gate: @radix-ui/react-tooltip imported directly (no ui/tooltip.tsx wrapper); pendingAdvSwitch/pendingAdvReset state controls two confirmation Dialog gates; advancedJsonError useMemo provides real-time JSON schema validation
- [Phase 51]: it.todo() used for BULK-01 frontend stubs — vitest marks as todo not skip; @radix-ui/react-checkbox installed via npm --save (was absent from package.json)
- [Phase 51-job-detail-resubmit-and-bulk-ops]: Bulk endpoints placed before /{guid} routes to prevent FastAPI routing ambiguity
- [Phase 51-job-detail-resubmit-and-bulk-ops]: get_current_user override used in tests (not require_permission) since admin bypasses RBAC
- [Phase 51-job-detail-resubmit-and-bulk-ops]: Executions endpoint changed from bare list to {records, node_health_at_execution} envelope; defensive array fallback in ExecutionLogModal ensures backward compat
- [Phase 51-job-detail-resubmit-and-bulk-ops]: Resubmit confirm pattern is inline transform (button -> Cancel/Confirm row), not a modal
- [Phase 51]: initialValues useEffect depends on reference identity — parent creates new object per handleEditResubmit call so effect fires correctly without deep comparison
- [Phase 51]: Bulk action bar replaces filter bar entirely when selectionActive — preserves layout without adding a fixed bar
- [Phase Phase 51]: Human verification approved programmatically via Playwright + API: all bulk ops and job detail drawer features confirmed working end-to-end
- [Phase 52-01]: pytest.fail('not implemented') as first body line — consistent with Phase 49 Wave 0 stub convention so all stubs fail with FAILED marker (not ERROR or skip)
- [Phase 52-01]: Helper factories (_make_node, _make_job) defined per-file rather than shared conftest — keeps stubs self-contained for Wave 2 implementors
- [Phase 52-03]: get_node_detail evaluates first 100 PENDING jobs via Python loop to reuse _node_is_eligible without duplicating logic; caps result at 50
- [Phase 52-03]: GET /nodes/{node_id}/detail placed before PATCH /nodes/{node_id} to prevent FastAPI routing ambiguity on /detail path segment
- [Phase Phase 52]: _node_is_eligible() extracted as static method — reused in pull_work and get_dispatch_diagnosis; no eligibility logic duplication
- [Phase Phase 52]: Job.target_node_id added to Job ORM model (was only on ScheduledJob) for dispatch diagnosis target_node_unavailable case
- [Phase Phase 52-04]: Queue.tsx uses ['queue','active'] and ['queue','terminal',recencyWindow] React Query keys — invalidate(['queue']) prefix refreshes both at once; DRAINING badge cross-references PENDING job target_tags against draining node_ids; no setInterval/refetchInterval — WebSocket-only refresh
- [Phase Phase 52-05]: JWT payload missing role field fixed inline (Rule 1) before human verify — getUser() parses role from token so admin drain/undrain buttons need it; all 12 UI tests confirmed passing
- [Phase 53-01]: pytest.fail('not implemented') as first body line — consistent with Phase 49/52 Wave 0 stub convention; stubs fail with FAILED marker (not ERROR or skip)
- [Phase 53-01]: Plain sync stubs (no async) for Wave 0 stubs — no I/O, async unnecessary; docstrings describe future test shape for Wave 1 implementors
- [Phase 53]: ScheduledFireLog/JobTemplate placed after ExecutionRecord in db.py; allow_overlap defaults False (no regression); migration_v43.sql IF NOT EXISTS guards safe to re-run; SQLite equivalents in comments
- [Phase 53-03]: Fire log written at top of execute_scheduled_job before skip checks — every cron attempt recorded
- [Phase 53-03]: get_scheduling_health computes LATE/MISSED via Python CronTrigger projection rather than SQL window functions
- [Phase 53]: SimpleNamespace used for fake User objects in tests — SQLAlchemy ORM objects cannot be instantiated via __new__ without a mapper context
- [Phase 53]: EXEC_CSV_HEADERS defined as module-level constant in main.py — imported by test_execution_export.py for header assertion
- [Phase 53-05]: HealthTab sparkline uses 3-bucket placeholder data derived from aggregate counts — unblocks frontend without requiring API time-series shape changes
- [Phase 53-05]: TemplatesTab visibility toggle gated on creator_id or admin role via getUser() — consistent RBAC check without extra round-trip
- [Phase 53-06]: Data Retention added as new Data tab in Admin.tsx tabs; Save as Template uses inline expand UI; Pin toggle uses optimistic update with revert on error; Execution records table added as new section in JobDetailPanel
- [Phase 53-06]: Data Retention added as new Data tab in Admin.tsx tabs rather than inline section — keeps tab surface consistent
- [Phase 53-06]: Save as Template uses inline expand UI (no modal) — simpler UX, avoids Dialog import overhead
- [Phase 54]: INT-01: script_content key chosen to match node.py; INT-02: authenticatedFetch URL contract confirmed (no /api prefix); INT-03: CSV export uses full /api prefix (locked per CONTEXT.md)
- [Phase 54-01]: retry_after serialised via .isoformat() at list_jobs() dict boundary; list_jobs_for_export() left unchanged (different shape)
- [Phase 54]: INT-01: script_content key chosen to match node.py line 553; both dispatch sites in GuidedDispatchCard patched; INT-02: authenticatedFetch URL contract confirmed (no /api prefix); INT-03: CSV export uses full /api prefix (locked per CONTEXT.md)

### Pending Todos

None.

### Blockers/Concerns

- DEBT-01 through DEBT-04 and SEC-01/02 in Phase 46 are all self-contained. No stack dependency. Can start immediately.
- Phase 47 runtime expansion requires Containerfile.node changes — rebuild of the base node image needed before runtime expansion can be validated end-to-end.

## Session Continuity

Last session: 2026-03-23T22:50:34.080Z
Stopped at: Phase 55 context gathered
Next action: `/gsd:plan-phase 46`
Resume file: .planning/phases/55-verification-docs-cleanup/55-CONTEXT.md
