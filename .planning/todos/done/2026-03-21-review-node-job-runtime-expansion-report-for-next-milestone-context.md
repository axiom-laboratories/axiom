---
created: 2026-03-21T19:16:29.480Z
updated: 2026-03-21T21:03:46.957Z
title: Review runtime expansion and package management reports, prepare milestones
area: planning
files:
  - mop_validation/reports/node_job_runtime_expansion.md
  - mop_validation/reports/apt_package_management.md
---

## Problem

Two research reports have been completed during the 2026-03-21 session that need to inform the next milestone plan. Planning from memory alone would miss the nuance and decisions captured in them.

**Report 1:** `mop_validation/reports/node_job_runtime_expansion.md`
- Multi-runtime node image (Python, Bash, PowerShell) for CE
- Unified `script` task type with `runtime` field
- CE/EE feature boundary for job execution
- Backwards compatibility with `python_script`

**Report 2:** `mop_validation/reports/apt_package_management.md`
- Hybrid `packages.apt` (structured) + CapabilityMatrix recipes (freeform) for EE
- EE job container architecture: manifest-driven, registry-backed, heartbeat-updated
- Update propagation via `pending_upgrade` heartbeat field (RBAC-gated, digest-verified)
- CE execution model stays unchanged architecturally (node image = job image)
- Supply chain risk: CapabilityMatrix recipes bypass SmelterService — `recipe_approval_flag` needed (HIGH priority EE)
- Private apt mirror + PSGallery (NuGet) mirroring for air-gapped EE deployments

## Solution

1. Read both reports in full before planning
2. Identify CE scope (small, near-term) vs EE workstreams (larger, future phases)
3. Run `/gsd:new-milestone` to create the next milestone, using both reports as primary input
4. CE phase: runtime expansion only — `Containerfile.node` + `node.py` + `models.py` + `Jobs.tsx`
5. EE phases: job container architecture, hybrid apt management, update propagation — each needs its own phase plan (flag as separate workstreams)
6. Feed findings into PROJECT.md and ROADMAP.md
