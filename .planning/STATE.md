---
gsd_state_version: 1.0
milestone: v23.0
milestone_name: DAG & Workflow Orchestration
status: in_progress
last_updated: "2026-04-15T00:00:00.000Z"
last_activity: "2026-04-15 — Milestone v23.0 started. Research complete (4 researchers + synthesizer). Requirements defined: 32 requirements across WORKFLOW/ENGINE/GATE/TRIGGER/PARAMS/UI. Roadmap pending."
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

**Current focus:** v23.0 DAG & Workflow Orchestration — defining roadmap phases.

## Current Position

**Phase:** Not started (defining roadmap)
**Plan:** —
**Status:** Defining roadmap
**Last activity:** 2026-04-15 — Requirements confirmed (32 requirements). Spawning roadmapper to create phased execution plan starting from Phase 146.

## Milestone v23.0 Summary

**32 requirements across 6 categories:**
- WORKFLOW-01..05 — Core data model (Workflow CRUD, Save-as-New ghost protection)
- ENGINE-01..07 — Execution engine (BFS dispatch, atomic guards, PARTIAL state, cancellation)
- GATE-01..06 — Node types (IF gate, AND/JOIN, OR, fan-out, Signal wait)
- TRIGGER-01..05 — Triggers (manual, cron, webhook + HMAC/nonce)
- PARAMS-01..02 — Parameter injection (WORKFLOW_PARAM_* env vars)
- UI-01..07 — Dashboard (read-only DAG view, live status, run history, unified schedule, visual editor)

## Key Architectural Decisions

**2026-04-15 — v23.0 DAG/Workflow Orchestration**
- Parameter passing: WORKFLOW_PARAM_* env vars (NOT template substitution — preserves Ed25519 signatures)
- IF gate structured output: /tmp/axiom/result.json result file (NOT last-line stdout — immune to logging noise)
- Unmatched IF gate: FAILED + cascade cancellation
- Webhook triggers: included in v23.0 scope
- Concurrency guards: SELECT...FOR UPDATE on BFS cascade to prevent race conditions
- Depth limit: 30 levels for workflow-instantiated jobs (override from 10-level default)
- Save-as-New: auto-pauses original cron trigger to prevent ghost execution

## Previous Milestone

**v22.0 Security Hardening — COMPLETE (2026-04-15)**

Archive: `.planning/milestones/v22.0-ROADMAP.md`
Phases: 132–145 (14 phases, 165 plans total across all milestones)
Requirements: 16 (CONT-01..10, EE-01..06) — all satisfied

**Key deliverables:**
- Container hardening: non-root execution, cap_drop ALL, no-new-privileges, resource limits, socket mount, Podman support
- EE licence protection: Ed25519 wheel manifest verification, HMAC-SHA256 boot log, entry point whitelist, wheel signing tool
- Nyquist validation: 100% test coverage across all 14 phases
