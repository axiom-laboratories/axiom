---
created: 2026-03-22T09:00:00.000Z
title: Research parallel job swarming and its architectural implications
area: architecture
files:
  - puppeteer/agent_service/services/job_service.py
  - mop_validation/reports/user_story_friction_3.md
---

## Problem

MoP's dispatch model is a pull queue — nodes poll for work, pick up a job if capable, execute, repeat. The orchestrator makes no assumptions about parallel execution across nodes. This model is simple and robust but may be limiting for fleet-scale operations where an operator wants to coordinate simultaneous execution across many nodes (e.g. rolling deploys, coordinated maintenance, timed fleet-wide actions).

Node-pinning (Tier 1) and fan-out campaigns (Tier 2) are being implemented separately and do not require swarming. This todo covers the deeper question of whether the orchestrator should ever actively coordinate parallel workloads — and what the architectural cost of that would be.

## Questions to answer before any planning

1. **Is there a real operator need?** Fan-out campaigns (N pinned jobs dispatched simultaneously) may satisfy the use case without the orchestrator needing to know about parallelism. Does "coordinated parallel execution" mean something beyond fan-out?

2. **Pull model compatibility:** The pull model assumes nodes self-select work. Active swarming would require the orchestrator to push or reserve jobs for specific nodes — a meaningful change to the dispatch contract. What breaks?

3. **Capacity and backpressure:** If 50 jobs are dispatched simultaneously, how does the orchestrator manage backpressure? Job queue already handles this passively (nodes pull when ready). Active coordination would need explicit capacity tracking.

4. **Ordering and synchronisation:** Does swarming require barrier synchronisation (wait for all N nodes to reach a checkpoint before proceeding)? That's a significantly more complex primitive than fan-out.

5. **Failure semantics:** In a swarm, if 3/10 nodes fail mid-execution, does the orchestrator need to roll back the other 7? This implies distributed transaction semantics.

## Solution

Research phase only — no implementation until research is complete. Produce a design document covering:
- Use case analysis (is fan-out + campaigns sufficient, or is there a genuine gap?)
- Architectural impact assessment on the pull model
- Complexity/value trade-off recommendation
- Prerequisite: Tier 1 (node-pinning) and Tier 2 (fan-out campaigns) must be complete first — research swarming against a known-good fan-out baseline
