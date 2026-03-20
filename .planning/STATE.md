---
gsd_state_version: 1.0
milestone: v11.1
milestone_name: — Stack Validation
status: planning
stopped_at: Completed 39-02-PLAN.md — EE licence generator + install verifier
last_updated: "2026-03-20T21:16:18.929Z"
last_activity: 2026-03-20 — Roadmap created for v11.1 (Phases 38–45)
progress:
  total_phases: 8
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v11.1 Stack Validation — Phase 38: Clean Teardown + Fresh CE Install

## Current Position

Phase: 38 of 45 (Clean Teardown + Fresh CE Install)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-20 — Roadmap created for v11.1 (Phases 38–45)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |
| Phase 38-clean-teardown-fresh-ce-install P01 | 1 | 2 tasks | 2 files |
| Phase 38-clean-teardown-fresh-ce-install P02 | 2 | 1 tasks | 1 files |
| Phase 39-ee-test-keypair-dev-install P01 | 10 | 2 tasks | 5 files |
| Phase 39-ee-test-keypair-dev-install P02 | 3m | 2 tasks | 4 files |

## Accumulated Context

### Decisions

- [Phase 39]: EE public key patching uses editable `pip install -e .` on raw `axiom-ee/` source — no Cython rebuild. Patching compiled `.so` at runtime is impossible (Cython attributes are read-only at C level).
- [Phase 40]: LXC nodes use `incusbr0` bridge host IP for `AGENT_URL`, not Docker's `172.17.0.1`. IP must be discovered dynamically.
- [Phase 40]: One unique JOIN_TOKEN per node generated before provisioning — parallel enrollment races on a shared token.
- [All concurrent tests]: Postgres required. SQLite write locking breaks under 4-node concurrent polling.
- [Phase 38]: Soft teardown uses docker compose down (no -v) + explicit pgdata volume rm — only safe way to preserve certs-volume Root CA between runs
- [Phase 38]: Hard teardown omits global set -e so a stopped LXC node does not abort the script — best-effort per node with [WARN] output
- [Phase 38]: SECRETS_ENV points to MOP_DIR/secrets.env (not mop_validation/secrets.env) — shared credential store between stack and tests
- [Phase 38]: verify_ce_install.py table count excludes apscheduler_jobs — APScheduler internal table is not a CE schema table
- [Phase 38]: INST-04 manual steps embedded as INST_04_MANUAL_TEST_STEPS module constant — accessible via grep/editor without running script
- [Phase 39]: patch_ee_source.py uses lambda replacement in re.sub to prevent \xNN byte sequences in repr(pub_raw) being treated as regex escapes
- [Phase 39]: compose.server.yaml AXIOM_LICENCE_KEY change applied to main puppeteer/ file — the .worktrees/axiom-split/ worktree referenced in plan does not exist
- [Phase 39]: Plan 39-02 verification condition typo: exp > 1700000000*5 (=8.5B) in plan snippet was wrong for 10yr licence (~2.09B); corrected assertion to > int(time.time()). Implementation correct.

### Pending Todos

None.

### Blockers/Concerns

- Phase 39 can start in parallel with Phase 38 (no stack dependency), but must complete before Phase 42.
- Phases 43 and 44 are independent of each other — can run in parallel after Phase 42 completes.
- Air-gap test (FOUNDRY-05) requires real `iptables` network isolation, not just behavioral pip.conf check.

## Session Continuity

Last session: 2026-03-20T21:16:18.927Z
Stopped at: Completed 39-02-PLAN.md — EE licence generator + install verifier
Next action: `/gsd:plan-phase 38`
Resume file: None
