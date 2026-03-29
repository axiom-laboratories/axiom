---
gsd_state_version: 1.0
milestone: v15.0
milestone_name: — Operator Readiness
status: planning
stopped_at: Completed 84-02-PLAN.md
last_updated: "2026-03-29T14:43:13.376Z"
last_activity: 2026-03-28 — Roadmap created for v15.0
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 7
  completed_plans: 7
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v15.0 — Operator Readiness — Phase 82: Licence Tooling

## Current Position

Phase: 82 of 86 (Licence Tooling)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-28 — Roadmap created for v15.0

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (this milestone)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 82. Licence Tooling | TBD | - | - |
| 83. Node Validation Job Library | TBD | - | - |
| 84. Package Repo Operator Docs | TBD | - | - |
| 85. Screenshot Capture | TBD | - | - |
| 86. Docs Accuracy Validation | TBD | - | - |
| Phase 82-licence-tooling P01 | 3 | 3 tasks | 9 files |
| Phase 82 P02 | 12 | 2 tasks | 4 files |
| Phase 83 P01 | 2 | 2 tasks | 4 files |
| Phase 83 P02 | 3 | 2 tasks | 5 files |
| Phase 83 P03 | 8 | 2 tasks | 4 files |
| Phase 84-package-repo-operator-docs P01 | 8 | 2 tasks | 3 files |
| Phase 84-package-repo-operator-docs P02 | 2 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

- [v15.0 roadmap]: Ed25519 private key must move to private `axiom-laboratories/axiom-licences` repo — public repo retains only the verification public key hardcoded in `licence_service.py`
- [v15.0 roadmap]: `issue_licence.py` must require explicit `--key` path with no default — silent default inside the repo is the primary security gap to close in Phase 82
- [v15.0 roadmap]: Resource limit jobs (JOB-06, JOB-07) included in Phase 83 but must gate on `resource_limits_supported` capability flag — cgroup v2 enforcement is unreliable on LXC nodes
- [v15.0 roadmap]: Network validation job must use Docker-native `--network=none` isolation only — no direct iptables manipulation to avoid residual node-global state (research pitfall 6)
- [v15.0 roadmap]: Phase 84 (Package Repo Docs) depends on Phase 83 — the pip mirror validation job is a corpus member and must use the signing infrastructure established in Phase 83
- [v15.0 roadmap]: Screenshot capture is not a CI gate — it is an operator step on release prep; CI integration deferred to v15.x
- [v15.0 roadmap]: Docs validation uses static OpenAPI snapshot (`docs/docs/api-reference/openapi.json`) — no live stack required, consistent with CLAUDE.md "never use local dev servers" rule
- [v15.0 roadmap]: Phase 84 requires a 15-minute pre-execution devpi verification session — confirm Caddy-proxied URL, index names, and port before writing runbook prose (research flag)
- [Phase 82-01]: Public key PEM captured from keypair generation: MCowBQYDK2VwAyEA4ceile+Eh85kcTaQuI+CZS3qlHX8f+kYYReW7x3heVk= — must be used in licence_service.py (Plan 02 Task 1)
- [Phase 82-01]: list_licences.py sorts ascending by expiry (soonest first) — more operationally useful for renewal tracking despite plan text saying descending
- [Phase 82-01]: keys/licence.key excluded from git via .gitignore *.key rule — private key must only exist in the private axiom-licenses repo
- [Phase 82-02]: New Ed25519 public key MCowBQYDK2VwAyEA4ceile+Eh85kcTaQuI+CZS3qlHX8f+kYYReW7x3heVk= embedded in licence_service.py; tools/generate_licence.py removed from public repo
- [Phase 82-02]: gitleaks [[allowlists]] double-bracket syntax required for v8.25.0+; secret-scan CI job added with full history fetch
- [Phase 83]: Scripts committed unsigned per plan locked decision — no .sig companion files at this stage; signing handled by Plan 03
- [Phase 83]: Wave 0 TDD pattern established: test scaffold committed before scripts exist, tests fail cleanly with pytest.fail() + helpful message
- [Phase 83]: resource_limits_supported capability guard: scripts exit 1 (safe abort) when capability absent, with descriptive message
- [Phase 83]: manifest.yaml required_capabilities values quoted as strings ('1.0') because job_service.py uses packaging.version.Version for comparison
- [Phase 83-03]: README uses awesome-list style with per-job H3 subsections — welcoming to community contributors
- [Phase 83-03]: Runbook includes inversion-logic explanation for validation-memory-hog (FAILED = working correctly)
- [Phase 84-01]: env block omitted from manifest.yaml — PYPI_MIRROR_HOST documented in runbook only (not a standard dispatch field)
- [Phase 84-01]: verify_pypi_mirror.py exits 1 immediately on empty PYPI_MIRROR_HOST before spawning pip — prevents silent false negatives
- [Phase 84-02]: devpi correct URL is http://devpi:3141/root/pypi/+simple/ — root index /+simple/ is empty; documented as critical common issue in runbook
- [Phase 84-02]: apt-cacher-ng: rm /etc/apt/apt.conf.d/01proxy must be in same RUN layer as apt-get install to prevent proxy persisting in final node images
- [Phase 84-02]: BaGet: Install-PSResource preferred over Install-Module on PS 7.4+ — PowerShellGet v2 has partial NuGet v3 compatibility issues

### Pending Todos

8 pending todos. Key items:
- Review competitor pain points report (`2026-03-29-review-competitor-pain-points-report.md`)
- USP — hello world job under 30 mins signing UX
- Add screenshots/marketing images to marketing page
- Create node validation jobs (bash/Python/PWSH)
- Document custom package repo for EE node
- Implement deployment recommendations in Docs stack
- Licence generation tooling and private repo
- Review docs for accuracy and add screenshots

### Blockers/Concerns

- [Phase 82]: Key rotation design decision required before execution — when the signing keypair rotates, previously issued licences signed with the old key become invalid unless a transition window is defined. Parallel public keys vs. re-signing all issued licences must be decided at plan time.
- [Phase 82]: `axiom-push init` signing workflow in CI requires a service principal token injected as a secret — exact mechanism must be defined before Phase 83 `sign_corpus.py` is built.
- [Phase 83]: JOB-06 and JOB-07 (resource limit jobs) require cgroup v2 support on the test node — LXC nodes with `EXECUTION_MODE=direct` will not enforce `--memory`/`--cpus` flags. Gate on capability detection.
- [Phase 84]: Verify live devpi Caddy-proxied URL, index name, and auth config before writing runbook. Risk: documenting wrong URL (research pitfall 8).

## Session Continuity

Last session: 2026-03-29T14:43:13.374Z
Stopped at: Completed 84-02-PLAN.md
Resume file: None
