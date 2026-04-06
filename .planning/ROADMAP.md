# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v7.0 — Advanced Foundry & Smelter** — Phases 11–15 (shipped 2026-03-16)
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- ✅ **v9.0 — Enterprise Documentation** — Phases 20–28 (shipped 2026-03-17)
- ✅ **v10.0 — Axiom Commercial Release** — Phases 29–33 (shipped 2026-03-19)
- ✅ **v11.0 — CE/EE Split Completion** — Phases 34–37 (shipped 2026-03-20)
- ✅ **v11.1 — Stack Validation** — Phases 38–45 (shipped 2026-03-22)
- ✅ **v12.0 — Operator Maturity** — Phases 46–56 (shipped 2026-03-24)
- ✅ **v13.0 — Research & Documentation Foundation** — Phases 57–60 (shipped 2026-03-24)
- ✅ **v14.0 — CE/EE Cold-Start Validation** — Phases 61–65 (shipped 2026-03-25)
- ✅ **v14.1 — First-User Readiness** — Phases 66–70 (shipped 2026-03-26)
- ✅ **v14.2 — Docs on GitHub Pages** — Phase 71 (shipped 2026-03-26)
- ✅ **v14.3 — Security Hardening + EE Licensing** — Phases 72–76 (shipped 2026-03-27)
- ✅ **v14.4 — Go-to-Market Polish** — Phases 77–81 (shipped 2026-03-28)
- ✅ **v15.0 — Operator Readiness** — Phases 82–86 (shipped 2026-03-29)
- ✅ **v16.0 — Competitive Observability** — Phases 87–91 (shipped 2026-03-30)
- ✅ **v16.1 — PR Merge & Backlog Closure** — Phases 92–95 (shipped 2026-03-30)
- ✅ **v17.0 — Scale Hardening** — Phases 96–100 (shipped 2026-03-31)
- ✅ **v18.0 — First-User Experience & E2E Validation** — Phases 101–106 (shipped 2026-04-01)
- ✅ **v19.0 — Foundry Improvements** — Phases 107–114, 116–119 (shipped 2026-04-05)
- **v20.0 — Node Capacity & Isolation Validation** — Phases 120–128 (in planning)

## Phases

<details>
<summary>✅ v7.0 — Advanced Foundry & Smelter (Phases 11–15) — SHIPPED 2026-03-16</summary>

- [x] **Phase 11: Compatibility Engine** — OS family tagging, runtime deps, API/UI enforcement (completed 2026-03-11)
- [x] **Phase 12: Smelter Registry** — Vetted ingredient catalog, CVE scanning, STRICT/WARNING enforcement (completed 2026-03-15)
- [x] **Phase 13: Package Management & Custom Repos** — Local PyPI + APT mirror sidecars, auto-sync, air-gapped upload, pip.conf/sources.list injection, fail-fast enforcement (completed 2026-03-15)
- [x] **Phase 14: Foundry Wizard UI** — 5-step guided composition wizard with real-time OS filtering and Smelter integration (completed 2026-03-16)
- [x] **Phase 15: Smelt-Check, BOM & Lifecycle** — Post-build ephemeral validation, JSON BOM, package index, image ACTIVE/DEPRECATED/REVOKED lifecycle (completed 2026-03-16)

Archive: `.planning/milestones/v7.0-ROADMAP.md`

</details>

<details>
<summary>✅ v8.0 — mop-push CLI & Job Staging (Phases 17–19) — SHIPPED 2026-03-15</summary>

- [x] **Phase 17: Backend — OAuth Device Flow & Job Staging** — RFC 8628 device flow, ScheduledJob status field, /api/jobs/push with dual-token verification, REVOKED enforcement at dispatch (completed 2026-03-12)
- [x] **Phase 18: mop-push CLI** — mop-push login/push/create commands, Ed25519 signing locally, installable SDK package (completed 2026-03-12)
- [x] **Phase 19: Dashboard Staging View & Governance Doc** — Staging tab, script inspection, one-click Publish, status badges, OIDC v2 architecture doc (completed 2026-03-15)

Archive: `.planning/milestones/v8.0-ROADMAP.md`

</details>

<details>
<summary>✅ v9.0–v19.0 (Phases 20–119) — SHIPPED</summary>

See `.planning/milestones/` for detailed archive of each milestone.

- ✅ v9.0 Enterprise Documentation — Phases 20–28 (shipped 2026-03-17)
- ✅ v10.0 Axiom Commercial Release — Phases 29–33 (shipped 2026-03-19)
- ✅ v11.0 CE/EE Split Completion — Phases 34–37 (shipped 2026-03-20)
- ✅ v11.1 Stack Validation — Phases 38–45 (shipped 2026-03-22)
- ✅ v12.0 Operator Maturity — Phases 46–56 (shipped 2026-03-24)
- ✅ v13.0 Research & Documentation Foundation — Phases 57–60 (shipped 2026-03-24)
- ✅ v14.0 CE/EE Cold-Start Validation — Phases 61–65 (shipped 2026-03-25)
- ✅ v14.1 First-User Readiness — Phases 66–70 (shipped 2026-03-26)
- ✅ v14.2 Docs on GitHub Pages — Phase 71 (shipped 2026-03-26)
- ✅ v14.3 Security Hardening + EE Licensing — Phases 72–76 (shipped 2026-03-27)
- ✅ v14.4 Go-to-Market Polish — Phases 77–81 (shipped 2026-03-28)
- ✅ v15.0 Operator Readiness — Phases 82–86 (shipped 2026-03-29)
- ✅ v16.0 Competitive Observability — Phases 87–91 (shipped 2026-03-30)
- ✅ v16.1 PR Merge & Backlog Closure — Phases 92–95 (shipped 2026-03-30)
- ✅ v17.0 Scale Hardening — Phases 96–100 (shipped 2026-03-31)
- ✅ v18.0 First-User Experience & E2E Validation — Phases 101–106 (shipped 2026-04-01)
- ✅ v19.0 Foundry Improvements — Phases 107–114, 116–119 (shipped 2026-04-05)

</details>

<details>
<summary>v20.0 — Node Capacity & Isolation Validation (Phases 120–128) — IN PLANNING</summary>

- [x] **Phase 120: Database & API Contract** — Add job limit schema + API models for end-to-end traceability (completed 2026-04-06)
- [ ] **Phase 121: Job Service & Admission Control** — Memory limit persistence and API admission checks
- [ ] **Phase 122: Node-Side Limit Integration** — Extract limits from work queue and pass to runtime
- [ ] **Phase 123: Cgroup Detection Backend** — Node detects cgroup v1 vs v2 at startup and heartbeat
- [ ] **Phase 124: Ephemeral Execution Guarantee** — Block direct execution; flag EXECUTION_MODE=direct as unsafe
- [ ] **Phase 125: Stress Test Corpus** — CPU, memory, and noisy-neighbour scripts in Python, Bash, PowerShell
- [ ] **Phase 126: Limit Enforcement Validation** — CPU limits, both Docker and Podman job execution runtimes
- [ ] **Phase 127: Cgroup Dashboard & Monitoring** — Dashboard cgroup badges and operator warnings
- [ ] **Phase 128: Concurrent Isolation Verification** — Memory isolation and latency monitoring under load

Archive: `.planning/milestones/v20.0-ROADMAP.md`

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 107. Schema Foundation + CRUD Completeness | v19.0 | 3/3 | Complete | 2026-04-03 |
| 108. Transitive Dependency Resolution | v19.0 | 2/2 | Complete | 2026-04-03 |
| 109. APT + apk Mirrors + Compose Profiles | v19.0 | 4/4 | Complete | 2026-04-03 |
| 110. CVE Transitive Scan + Dependency Tree UI | v19.0 | 3/3 | Complete | 2026-04-04 |
| 111. npm + NuGet + OCI Mirrors | v19.0 | 3/3 | Complete | 2026-04-04 |
| 112. Conda Mirror + Mirror Admin UI | v19.0 | 4/4 | Complete | 2026-04-04 |
| 113. Script Analyzer | v19.0 | 2/2 | Complete | 2026-04-04 |
| 114. Curated Bundles + Starter Templates | v19.0 | 3/3 | Complete | 2026-04-05 |
| 116. DB Migration + EE Licence Hot-Reload | v19.0 | 2/2 | Complete | 2026-04-04 |
| 117. Light/Dark Mode Toggle | v19.0 | 5/5 | Complete | 2026-04-04 |
| 118. UI Polish and Verification | v19.0 | 4/4 | Complete | 2026-04-04 |
| 119. v19.0 Traceability Closure | v19.0 | 2/2 | Complete | 2026-04-05 |
| 120. Database & API Contract | v20.0 | 3/3 | Complete | 2026-04-06 |
| 121. Job Service & Admission Control | v20.0 | 0/? | Not started | — |
| 122. Node-Side Limit Integration | v20.0 | 0/? | Not started | — |
| 123. Cgroup Detection Backend | v20.0 | 0/? | Not started | — |
| 124. Ephemeral Execution Guarantee | v20.0 | 0/? | Not started | — |
| 125. Stress Test Corpus | v20.0 | 0/? | Not started | — |
| 126. Limit Enforcement Validation | v20.0 | 0/? | Not started | — |
| 127. Cgroup Dashboard & Monitoring | v20.0 | 0/? | Not started | — |
| 128. Concurrent Isolation Verification | v20.0 | 0/? | Not started | — |

## Archived

- ✅ **v19.0 — Foundry Improvements** (Phases 107–114, 116–119) — shipped 2026-04-05 → `.planning/milestones/v19.0-ROADMAP.md`
- ✅ **v18.0 — First-User Experience & E2E Validation** (Phases 101–106) — shipped 2026-04-01 → `.planning/milestones/v18.0-ROADMAP.md`
- ✅ **v16.1 — PR Merge & Backlog Closure** (Phases 92–95) — shipped 2026-03-30 → `.planning/milestones/v16.1-ROADMAP.md`
- ✅ **v14.3 — Security Hardening + EE Licensing** (Phases 72–76) — shipped 2026-03-27 → `.planning/milestones/v14.3-ROADMAP.md`
- ✅ **v14.2 — Docs on GitHub Pages** (Phase 71) — shipped 2026-03-26 → `.planning/milestones/v14.2-ROADMAP.md`
