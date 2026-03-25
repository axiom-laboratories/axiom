---
gsd_state_version: 1.0
milestone: v14.0
milestone_name: — CE/EE Cold-Start Validation
status: completed
stopped_at: Completed 65-01 — friction report synthesis; v14.0 milestone closed
last_updated: "2026-03-25T20:43:41.980Z"
last_activity: 2026-03-25 — Phase 65 Plan 01 complete; cold_start_friction_report.md (274 lines, NOT READY verdict, 5 open product BLOCKERs) produced; operator approved; v14.0 milestone closed
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 14
  completed_plans: 14
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Planning next milestone — address v14.0 BLOCKERs from cold_start_friction_report.md

## Current Position

Phase: 65 of 65 (Friction Report Synthesis) — COMPLETE
Plan: 01 of 01 — Complete
Status: Phase 65 complete — synthesise_friction.py written and run; cold_start_friction_report.md produced and operator-approved; v14.0 milestone closed
Last activity: 2026-03-25 — Phase 65 Plan 01 complete; cold_start_friction_report.md (274 lines, NOT READY verdict, 5 open product BLOCKERs) produced; operator approved; v14.0 milestone closed

Progress: [██████████] 100%

## Accumulated Context

### Decisions

- [v14.0 Kickoff]: Single LXC contains full Axiom Docker stack (orchestrator + nodes) + Gemini tester agent
- [v14.0 Kickoff]: Gemini CLI (Flash model, GEMINI_API_KEY) used as tester; Claude orchestrates via file-based checkpoint protocol
- [v14.0 Kickoff]: Agents constrained to docs-only access — no codebase reads; checkpoint files used when agent is blocked
- [v14.0 Kickoff]: Two runs: CE (no licence) then EE (pre-generated Ed25519 licence); both test install + 3 runtimes
- [v14.0 Roadmap]: Phase 61 must resolve all 8 critical infrastructure pitfalls before Phase 62 starts
- [v14.0 Roadmap]: CE run (Phase 63) precedes EE run (Phase 64) — shared friction identified in CE need not be re-investigated
- [Phase 61-lxc-environment-and-cold-start-compose]: Use raw.apparmor=pivot_root, override in incus launch for Docker-in-LXC on Ubuntu 24.04 kernel 6.8.x (Incus #791 workaround)
- [Phase 61]: Hardcode SERVER_HOSTNAME=172.17.0.1 in cold-start cert-manager to guarantee correct Caddy TLS SAN without evaluator config
- [Phase 61]: PowerShell 7.6.0 LTS direct GitHub releases .deb install replaces silently-failing Microsoft Debian 12 SHA1 apt repo method
- [Phase 61]: 1-year expiry and customer_id axiom-coldstart-test used to distinguish cold-start evaluation licences from developer test licences; AXIOM_EE_LICENCE_KEY written to secrets.env for Phase 64 compose injection
- [Phase 62-01]: HOME isolation uses /root/validation-home with settings.json only — no GEMINI.md, no history/ directory prevents session bleed between runs
- [Phase 62-01]: Docs delivered as static file:///workspace/docs/ snapshot pushed to LXC (167 files); Gemini reads via cat commands on HTML files
- [Phase 62-01]: SCAF-02 and SCAF-04 verifier checks are informational placeholders — not failures, stubs for plans 62-02 and 62-03
- [Phase 62-02]: SCAF-02 automated test does not invoke monitor_checkpoint.py (requires operator input) — procedural 5-step round-trip test used instead
- [Phase 62-02]: check_scaf02_checkpoint_roundtrip is self-contained in verify_phase62_scaf.py with own file transfer helpers — no cross-script imports
- [Phase 62-agent-scaffolding]: Each scenario produces a uniquely named FRICTION file (FRICTION-CE-INSTALL.md etc.) rather than FRICTION.md — prevents silent overwrites
- [Phase 62-agent-scaffolding]: check_scaf04_scenarios() runs host-side via pathlib.Path — scenario files live in mop_validation/scenarios/ on the host, not inside the LXC
- [Phase 63-01]: Pre-load Docker images from host into LXC via docker save | docker load — compose build contexts not available inside LXC
- [Phase 63-01]: reset_stack() uses docker compose up -d (not --build) — images must be pre-loaded via docker save/load before first run
- [Phase 63-02]: FRICTION-CE-INSTALL.md verdict: FAIL — node enrollment blocked by 6 converging doc/code mismatches (EXECUTION_MODE=direct removed, wrong node image, TLS cert mismatch, admin password undiscoverable, JOIN_TOKEN GUI-only, docs path wrong)
- [Phase 63-02]: Gemini free-tier quota insufficient for full scenario run — Tier 1 paid key required (80-120 API calls needed per scenario); verified friction via orchestrator doc-following instead
- [Phase 63-02 Operator Decision]: BLOCKER confirmed — Phase 63 halted at Plan 02; Plan 63-03 will NOT run until 6 node enrollment blockers are resolved; fixes required: EXECUTION_MODE docs, node image docs, TLS cert/AGENT_URL, admin password setup docs, JOIN_TOKEN CLI path, docs site path reference
- [Phase 63]: Used local mkdocs (v1.6.1) for docs rebuild — Docker mkdocs-material image lacks swagger-ui-tag plugin
- [Phase 63]: enroll-node.md Option B Docker socket mount added alongside EXECUTION_MODE=docker change — required for docker mode
- [Phase 63-03]: CE-05 verdict BLOCKER — CLI-only environments cannot complete operator scenario without 6 undocumented fixes; all 3 runtimes DO execute once infrastructure is configured
- [Phase 63-03]: Orchestrator-assisted fallback used when Gemini hit max checkpoint interventions (no browser for guided form); all 3 runtimes verified via API dispatch
- [Phase 63-03]: FRICTION-CE-OPERATOR.md: 5 BLOCKERs (guided form CLI, Docker CLI missing, DinD /tmp mount, wrong image tag, PowerShell missing) + 1 NOTABLE (Ed25519 signing undocumented) — all Phase 65 input
- [Phase 64-01]: Preserve full canonical wheel filename in COPY — pip validates filename format, aliases cause install failure
- [Phase 64-01]: Use --force-recreate (not restart) to propagate new JOIN_TOKEN env vars to node containers after cold reset
- [Phase 64-01]: Add _inject_join_tokens() to reset_stack_ee: generate JOIN_TOKEN_1/2 via API, append to .env, force-recreate node services
- [Phase 64-02]: Orchestrator-assisted friction evaluation used when Gemini MODEL_CAPACITY_EXHAUSTED (free-tier quota 0) — same limitation as Phase 63; FRICTION-EE-INSTALL.md produced via orchestrator doc-following
- [Phase 64-02]: EE operator gate confirmed via API: /api/features all 8 flags true, /api/licence edition=enterprise before Plan 03
- [Phase 64-03]: CE-gating finding: /api/executions returns HTTP 200 in CE mode (not 402) — route is ungated in main.py; CE stubs do not include execution history; product decision for Phase 65
- [Phase 64-03]: confirm_ce_gating() uses docker compose restart (not force-recreate) — env vars not re-read; script bug deferred to Phase 65
- [Phase 64-03]: FRICTION-EE-OPERATOR.md: 2 BLOCKERs (guided form CLI carry-over, CE-gating script restart bug) + 3 NOTABLEs (/api/executions ungated, no signing key pre-registered, signing workflow undocumented) — all Phase 65 input
- [Phase 64-03]: Operator approved Phase 64 complete: all 3 runtimes COMPLETED, Execution History EE feature confirmed accessible, CE-gating finding documented
- [Phase 65-friction-report-synthesis]: Fixed-during-run BLOCKERs count as open for verdict — they expose UX/doc gaps even when orchestrator resolved them at runtime
- [Phase 65-friction-report-synthesis]: synthesise_friction.py uses keyword/category mapping for Fix Target derivation — extensible for future FRICTION files

### Pending Todos

None.

### Blockers/Concerns

- [Phase 61]: Docker-in-LXC AppArmor pivot_root behaviour on Ubuntu 24.04 kernel 6.8.x — verify `docker run --rm hello-world` succeeds before proceeding
- [Phase 61]: Gemini CLI headless hang risk — `ripgrep` install and `GEMINI_API_KEY` env var required; verify with `timeout 30 gemini -p "Say hello"`
- [Phase 62]: Gemini API key tier must be Tier 1 (paid) for a full CE+EE run — free tier 250 RPD is insufficient
- [Phase 63 RESOLVED]: All 6 node enrollment blockers fixed in Plan 63-04; Plan 63-03 ran successfully
- [Phase 64]: `axiom-ee` wheel availability inside LXC — confirm editable install path vs devpi before Phase 64 planning

## Session Continuity

Last session: 2026-03-25T20:36:19.755Z
Stopped at: Completed 65-01 — friction report synthesis; v14.0 milestone closed
Next action: v14.0 milestone complete. Next milestone to be determined by product team based on cold_start_friction_report.md findings.
Resume file: None
