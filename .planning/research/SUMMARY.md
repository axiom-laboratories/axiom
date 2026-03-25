# Project Research Summary

**Project:** Axiom v14.1 — First-User Readiness
**Domain:** Self-hosted job orchestration platform — remediation milestone (docs + code fixes)
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

Axiom v14.1 is a focused remediation milestone, not a feature release. The v14.0 CE/EE cold-start validation produced a friction report with 12 open BLOCKERs, 4 NOTABLEs, and several rough edges that prevent a first-time user from completing the getting-started flow using only the published docs. All four research areas confirm the same conclusion: the underlying platform architecture is sound and already partially fixed (Containerfile.node and compose.cold-start.yaml were patched during the v14.0 run), but the docs have not caught up to the code, and one CE/EE gating gap remains open in the backend.

The recommended approach treats this milestone as two parallel work tracks: a code track (CE stub for `/api/executions`, verifying Containerfile.node fixes) and a docs track (rewriting three getting-started guides with correct commands, CLI alternatives, and the signing walkthrough). All code work requires zero new dependencies — the CE stub pattern, FastAPI routing, and MkDocs extensions are already in place. The docs track is the larger effort by volume but the lowest technical risk. The single most impactful fix across all four research areas is restructuring `first-job.md` to surface Ed25519 signing as an explicit prerequisite rather than buried mid-flow context.

The primary risk is the FastAPI route shadow problem: adding a CE stub for `/api/executions` will silently fail unless the existing `@app.get("/api/executions")` definition is removed from `main.py` first. This is counterintuitive — adding a new stub file appears to be the whole change, but the stub is never reached without the removal. A second risk is the PowerShell architecture guard — the current `amd64.deb` URL in Containerfile.node will silently break on arm64 build hosts. Both risks are well-understood and have clear prevention steps documented in the research.

## Key Findings

### Recommended Stack

The existing stack requires no changes. All four fix areas resolve to configuration edits, content edits, and moving routes between files — zero new packages, zero new infrastructure. The relevant tooling is already in place.

**Core technologies:**
- FastAPI `APIRouter` + `JSONResponse(402)`: CE stub routing — already used for 6 other EE features; new stub for executions follows identical pattern to `ee/interfaces/audit.py`
- MkDocs Material `pymdownx.tabbed`: content tabs for CLI/dashboard alternatives — already installed as mkdocs-material transitive dependency; requires only one config line in `mkdocs.yml`
- `docker:cli` multi-stage COPY: Docker CLI binary in node image — already in Containerfile.node; no further code change required
- `/tmp:/tmp` host bind mount in `compose.cold-start.yaml`: DinD job script path resolution — already present in both node services from the v14.0 run

The only new file required is `puppeteer/agent_service/ee/interfaces/executions.py` — a stub router using the exact same structure as the six existing interface files.

### Expected Features

This milestone is defined entirely by remediation of known gaps. Every item maps directly to a friction-report finding. There is no speculative feature development.

**Must have (P1 — required for READY verdict):**
- Admin password setup step in install.md before `docker compose up`
- CLI (curl) JOIN_TOKEN path promoted as a primary alternative in enroll-node.md
- Correct node image (`localhost/master-of-puppets-node:latest`) in Option B compose snippet
- `EXECUTION_MODE=docker` replacing the removed `direct` mode in all doc examples
- AGENT_URL table corrected — remove `172.17.0.1:8001` as primary recommendation; add `https://agent:8001` for cold-start compose scenario
- Full curl dispatch path added to first-job.md (signed job POST with base64 signature)
- Ed25519 signing key setup restructured as numbered prerequisites before the dispatch step
- Pre-dispatch key registration callout in first-job.md
- All Containerfile.node fixes verified in source (docker CLI binary, node image tag, PowerShell)
- `/tmp` mount verified in compose.cold-start.yaml for both node services
- `/api/admin/features` reference replaced with `/api/features` in EE docs

**Should have (P2 — eliminates friction, not hard blockers):**
- GitHub clone alternative documented for users with pre-built tarballs
- Docker socket volume note in enroll-node.md Option B
- `AXIOM_EE_LICENCE_KEY` naming audit in licensing.md
- AXIOM_LICENCE_KEY injection consistency note (`.env` vs `secrets.env` context differences)
- `/api/executions` CE-gated via EE stub (correctness gap; not a first-user blocker)

**Defer:**
- Nothing — every item in this milestone is remediation of a known BLOCKER or NOTABLE; deferring any P1 item leaves a confirmed first-user failure unresolved

### Architecture Approach

The architecture is not changing. All fix work lands in four well-bounded areas: the CE/EE stub layer (`ee/interfaces/`), the execution routes in `main.py`, the `docs/docs/getting-started/` content files, and `docs/mkdocs.yml`. The CE/EE gating mechanism operates entirely at startup: a valid licence key loads EE routers via `load_ee_plugins()`; no key mounts CE stubs via `_mount_ce_stubs()`. Adding an executions stub follows the exact same pattern as the six existing stub routers — no architectural decision is required.

**Major components affected by v14.1:**
1. `puppeteer/agent_service/main.py` — remove 7 execution route handlers (move responsibility to EE plugin + CE stub)
2. `puppeteer/agent_service/ee/interfaces/executions.py` — new CE stub returning 402 for all execution paths
3. `puppeteer/agent_service/ee/__init__.py` — register executions stub in `_mount_ce_stubs()`
4. `docs/docs/getting-started/*.md` — content edits on install.md, enroll-node.md, first-job.md
5. `docs/mkdocs.yml` — add `pymdownx.tabbed: alternate_style: true`

### Critical Pitfalls

1. **FastAPI route shadow blocks CE stub** — Adding `ee/interfaces/executions.py` is not enough. The `@app.get("/api/executions")` definitions in `main.py` register at import time and shadow any lifespan-registered stub. The routes must be removed from `main.py` before the stub can be reached. Verify with `test_ce_smoke.py` — all execution paths must return 402 in CE mode, not 200.

2. **PowerShell `.deb` is amd64-only with no platform guard** — Containerfile.node downloads `_amd64.deb` with no `--platform linux/amd64` guard. On arm64 hosts (Apple Silicon, Graviton), the build either fails or produces a container where PowerShell silently fails at runtime. Add `--platform linux/amd64` or an arch-conditional URL before v14.1 ships.

3. **MkDocs heading renames break deep links silently** — When rewriting getting-started docs, renamed headings invalidate anchor-based cross-references. MkDocs does not warn about broken anchor links even with `--strict`. Grep for existing `#anchor-name` references before renaming headings; run `mkdocs build --strict` after every doc change.

4. **`docker:cli` floating tag breaks air-gapped builds** — `COPY --from=docker:cli` requires pulling from Docker Hub at build time. Air-gapped operators must mirror `docker:cli` to their local registry and update the Containerfile reference. The current docs do not mention this requirement.

5. **Separate EE doc files drift from the actual API** — The stale `/api/admin/features` reference is a direct consequence of EE content living in a separate file. All EE getting-started content should use `!!! enterprise` admonitions within shared files. Do not create separate `ee-install.md` files that accumulate stale endpoint references.

## Implications for Roadmap

All four research areas converge on a two-phase implementation. The feature dependency graph in FEATURES.md is fully mapped — there are no unresolved ordering questions.

### Phase 1: Backend Code Fixes

**Rationale:** Code changes must land before docs are finalised. If the executions CE gate is not in place before docs are published, CE users following the EE docs will see 200 from `/api/executions`, contradicting the documented EE-only framing. Code first eliminates this contradiction and establishes the stable API surface the docs can accurately describe.

**Delivers:** Correct CE/EE boundary for Execution History; all code fixes verified in running stack

**Addresses:** B-05 (`/api/executions` CE gate), B-01/B-02/B-03 (Containerfile.node verification), B-04 (compose.cold-start.yaml verification)

**Avoids:** Pitfall 1 (FastAPI route shadow must be resolved in this phase); Pitfall 2 (PowerShell arch guard)

**Verification:** `test_ce_smoke.py` confirms 402 for all execution paths in CE mode; `docker --version` and `pwsh --version` run successfully inside a built and running node container; end-to-end job dispatch completes before phase closes

### Phase 2: Documentation Fixes

**Rationale:** All doc fixes are independent of each other and can be parallelised, but must follow Phase 1 so the code state is stable and all curl examples can be validated against the live stack.

**Delivers:** Complete, accurate getting-started flow from fresh install through first job dispatch, for both dashboard and CLI users; zero BLOCKERs remaining from the friction report

**Addresses:** All Category A fixes (A-01 through A-13), Category C fixes (C-01, C-02)

**Avoids:** Pitfall 3 (heading rename anchor breakage); Pitfall 5 (EE content in separate files); UX pitfall (admin password buried)

**Sub-ordering within Phase 2:**
- Add `pymdownx.tabbed: alternate_style: true` to `mkdocs.yml` before writing tab syntax into any content page
- install.md first — admin password setup is a prerequisite for every subsequent doc step
- enroll-node.md second — depends on install being correct
- first-job.md last — depends on node enrollment being documented correctly
- Run `mkdocs build --strict` after each file to catch broken nav and anchor issues immediately

### Phase Ordering Rationale

- Code before docs: publishing docs describing CE/EE behaviour before the code enforces that boundary creates a live correctness contradiction
- Sequential order within docs: the getting-started flow is a user journey — each page's instructions depend on the previous page being accurate
- Verification gating inside each phase: the PITFALLS.md "looks done but isn't" checklist identifies specific runtime checks (not just build checks) — `curl` returning 402, `pwsh --version` in container, end-to-end job dispatch — these should gate phase completion, not be deferred to a final QA pass

### Research Flags

Both phases have clear, fully-researched implementation paths. No additional research is required before either phase begins.

**Phase 1 (Backend):** The exact stub file contents, `ee/__init__.py` registration call, and `main.py` route lines to remove are fully specified in STACK.md. Implementation can proceed directly.

**Phase 2 (Docs):** All fix targets are mapped to specific files with line-level changes. The curl examples, signing workflow sequence, and AGENT_URL corrections are fully specified in FEATURES.md. Implementation can proceed directly.

No phases require `/gsd:research-phase` — this is a narrow, well-scoped remediation milestone against a fully-inspected codebase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All fix areas verified against live source files; no new dependencies introduced; all implementation details confirmed at file+line level |
| Features | HIGH | Derived from 24-finding friction report with reproduction steps; all P1 fix targets identified at file level with exact content changes specified |
| Architecture | HIGH | CE/EE stub pattern verified across 6 existing interface files; FastAPI route registration order confirmed via source analysis of lifespan and module-level decorators |
| Pitfalls | HIGH | Route shadow, PowerShell arch gap, and MkDocs anchor breakage all verified against actual current codebase state |

**Overall confidence:** HIGH

### Gaps to Address

- **PowerShell `.deb` architecture fix approach:** Research confirms the risk and two valid fixes (`--platform linux/amd64` flag vs runtime arch detection). The `--platform` flag is simpler and matches the platform's stated amd64 focus. Confirm this choice at the start of Phase 1 before touching the Containerfile.

- **`/api/executions` route scope decision:** STACK.md identifies 7 execution-related routes in `main.py` beyond the 3 called out in the NOTABLE finding — `pin`, `unpin`, and CSV export endpoints also lack CE gating. Recommend gating all 7 for consistency, but this should be confirmed before Phase 1 execution to ensure the stub file is complete on the first pass.

- **`ee-install.md` existence:** ARCHITECTURE.md notes this file "may not exist." If it does not exist, it must be created along with a nav entry in `mkdocs.yml`. If it exists with stale content, it needs updating. Verify file existence before Phase 2 begins to accurately size the doc work.

## Sources

### Primary (HIGH confidence)
- `mop_validation/reports/cold_start_friction_report.md` — 24 concrete findings with reproduction steps; primary source for all fix targets
- Live source: `puppeteer/agent_service/main.py`, `ee/__init__.py`, `ee/interfaces/*.py`, `deps.py` — CE/EE routing architecture
- Live source: `puppets/Containerfile.node`, `puppeteer/compose.cold-start.yaml` — node image and DinD compose state
- Live source: `docs/mkdocs.yml`, `docs/docs/getting-started/*.md` — current doc state
- [MkDocs Material Content Tabs](https://squidfunk.github.io/mkdocs-material/reference/content-tabs/) — `alternate_style: true` requirement and tab syntax confirmed
- [Docker Hub docker:cli tags](https://hub.docker.com/_/docker/tags?name=cli) — `cli` and `27-cli` tag existence confirmed

### Secondary (MEDIUM confidence)
- [Docker official Debian install docs](https://docs.docker.com/engine/install/debian/) — `docker.io` vs `docker-ce-cli` distinction on Debian 13
- [Docker bind mounts official docs](https://docs.docker.com/engine/storage/bind-mounts/) — host-path bind mount resolution behaviour; DinD path resolution inferred from source + friction report

### Tertiary (LOW confidence)
- FastAPI lifecycle route registration order — confirmed via source inspection; community references add supporting context only

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
