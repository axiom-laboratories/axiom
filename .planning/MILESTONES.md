# Milestones

## v18.0 First-User Experience & E2E Validation (Shipped: 2026-04-01)

**Phases completed:** 6 phases (101–106), 15 plans
**Stats:** 65 files changed, +7,888 / -147 lines | 82 commits | 2 days (2026-03-31 → 2026-04-01)

**Key accomplishments:**
- Phase 101 — CE UX cleanup: 6 EE-only Admin tabs gated behind `isEnterprise`; `+ Enterprise` upgrade panel with `UpgradePlaceholder` cards; no blank pages in CE mode; 4 vitest assertions covering CE/EE tab visibility
- Phase 102 — Linux E2E validation: Fresh LXC cold-start through first completed job following only Quick Start guide; 4 BLOCKERs found and fixed (--env-file removal, countersign wiring, /tmp DinD mount, GHCR node image); `synthesise_friction.py` reusable for cross-platform E2E
- Phase 103 — Windows E2E validation: Dwight SSH cold-start with PowerShell-only docs; 8 BLOCKERs found and fixed across 8 iterative runs; complete PowerShell tabs in enroll-node.md and first-job.md; CRLF normalization in node.py
- Phase 104 — PR merge: PRs #17 (WebSocket fix), #18 (Windows E2E), #19 (Linux E2E) squash-merged; History.test.tsx fixed (missing useFeatures mock); stale branches/worktrees cleaned; full vitest suite 64/64 pass
- Phase 105 — Windows signing pipeline fix: CRLF→LF normalization in main.py create_job before both user-sig verification and countersigning; admin bootstrap always forces password change; CRLF countersign symmetry unit test; PowerShell tabs restored to first-job.md
- Phase 106 — Docs signing pipeline fix: `signature_key_id`→`signature_id` field name corrected in both Linux curl and PowerShell snippets; deprecated TrustAll .NET pattern replaced with `-SkipCertificateCheck`; client-side CRLF normalization in signing script

---

## v17.0 Scale Hardening (Shipped: 2026-03-31)

**Phases completed:** 5 phases, 6 plans, 0 tasks

**Key accomplishments:**
- (none recorded)

---

## v16.1 PR Merge & Backlog Closure (Shipped: 2026-03-30)

**Phases completed:** 6 phases, 7 plans, 3 tasks

**Key accomplishments:**
- (none recorded)

---

## v15.0 Operator Readiness (Shipped: 2026-03-29)

**Phases completed:** 5 phases (82–86), 11 plans
**Stats:** 175 files changed, +27,147 / -1,356 lines | 1 day (2026-03-28 → 2026-03-29)
**Git range:** `v14.4` → `1b49670`

**Key accomplishments:**
- Phase 82 — Licence tooling: `issue_licence.py` offline CLI (JWT signing, YAML audit ledger, GitHub API commit); `list_licences.py` with `--json` flag; `--no-remote` air-gap mode; gitleaks secret-scan CI guard blocking PEM key commits to public repo
- Phase 83 — Node validation job library: Bash/Python/PowerShell hello-world reference jobs; volume mapping, network filtering, memory-hog, and CPU-spin validation scripts; `sign_corpus.py` for corpus signing; `manifest.yaml`; community catalog README + MkDocs runbook
- Phase 84 — Package repo operator docs: devpi PyPI mirror runbook (Caddy-proxied `root/pypi/+simple/`), apt-cacher-ng APT mirror guidance, BaGet PWSH mirror with Install-PSResource; `verify_pypi_mirror.py` signed validation job added to corpus
- Phase 85 — Screenshot capture: `capture_screenshots.py` Playwright script with `seed_demo_data.py` (ephemeral Ed25519 keypair); 11 named PNGs at 1440×900; integrated into getting-started + feature docs pages and marketing homepage showcase
- Phase 86 — Docs accuracy validation: `generate_openapi.py` snapshot tool; `validate_docs.py` (250 PASS / 0 WARN / 0 FAIL against 116-route OpenAPI snapshot); docs-validate CI job in `ci.yml` exits non-zero on FAIL

**Known Gaps:**
- SCR-01: Playwright script checkbox was not ticked in REQUIREMENTS.md (script completed and working — checkbox omission only)
- DOC-03: CI non-zero exit checkbox was not ticked in REQUIREMENTS.md (CI job implemented in Phase 86-02 — checkbox omission only)

---

## v14.4 Go-to-Market Polish (Shipped: 2026-03-28)

**Phases completed:** 5 phases, 7 plans, 0 tasks

**Key accomplishments:**
- (none recorded)

---

## v14.3 Security Hardening + EE Licensing (Shipped: 2026-03-27)

**Phases completed:** 5 phases (72–76), 8 plans
**Stats:** 60 files changed, +7,383 / -688 lines | 2 days (2026-03-26 → 2026-03-27)
**Git range:** `9ae0e18` → `5d4c217`

**Key accomplishments:**
- Phase 72 — Security fixes: All 6 CodeQL alerts resolved — XSS escaping on device-approve endpoint, `validate_path_within()` path traversal guards, bounded email regex to eliminate ReDoS, API_KEY hard crash removed, `X-Content-Type-Options: nosniff` on CSV export; 18 security tests GREEN
- Phase 73 — EE licence system: `licence_service.py` with EdDSA JWT validation, VALID/GRACE/EXPIRED/CE state machine, hash-chained boot-log clock-rollback detection; `tools/generate_licence.py` offline key generator CLI; `/api/licence` endpoint, `enroll_node` node-limit 402 guard, DEGRADED_CE `pull_work` guard; all 7 LIC tests GREEN
- Phase 74 — EE licence display: `useLicence.ts` rewritten to match actual backend response; EE badge and grace/expired banner in MainLayout; Admin licence section with status badge and expiry date; 15 frontend tests GREEN
- Phase 75 — Secrets volume + dead code: `secrets-data` named Docker volume so `boot.log` persists across restarts; `vault_service.py` deleted (dead code); `check_and_record_boot()` takes `licence_status` so EE enforces rollback detection while CE warns only; `main.py.bak` removed from git
- Phase 76 — Tech debt closure: `test_licence.py` updated to current 6-field response shape; dead `API_KEY` removed from `compose.cold-start.yaml`; orphaned `vault_service.cpython-312.pyc` deleted

---

## v14.2 Docs on GitHub Pages (Shipped: 2026-03-26)

**Phases completed:** 1 phases, 2 plans, 0 tasks

**Key accomplishments:**
- (none recorded)

---

## v14.1 First-User Readiness (Shipped: 2026-03-26)

**Phases completed:** 5 phases, 9 plans, 2 tasks

**Key accomplishments:**
- (none recorded)

---

## v14.0 CE/EE Cold-Start Validation (Shipped: 2026-03-25)

**Phases completed:** 5 phases, 14 plans
**Stats:** 178 files changed, +39,323 / -1,614 lines | ~33,600 LOC total | 2 days (2026-03-24 → 2026-03-25)

**Key accomplishments:**
- Phase 61 — LXC cold-start environment: Docker-in-LXC provisioner with AppArmor pivot_root workaround; `compose.cold-start.yaml` with hardcoded `SERVER_HOSTNAME`; PowerShell 7.6 direct .deb install; EE test licence generator with 1-year expiry
- Phase 62 — Agent scaffolding: Tester `GEMINI.md` with docs-only first-user persona; HOME isolation (`/root/validation-home`) preventing session bleed; `monitor_checkpoint.py` file-based checkpoint protocol; CE/EE scenario scripts with per-step PASS/FAIL checklists
- Phase 63 — CE cold-start run: 6 critical doc/code gaps identified and patched (EXECUTION_MODE, node image tag, AGENT_URL, admin password docs, JOIN_TOKEN CLI path, docs site path); all 3 runtimes (Python/Bash/PowerShell) verified to COMPLETED via orchestrator-assisted path
- Phase 64 — EE cold-start run: EE plugin activated with injected licence; all 3 runtimes confirmed COMPLETED; Execution History EE feature verified; CE-gating gap found (`/api/executions` ungated returning HTTP 200 in CE mode)
- Phase 65 — Friction synthesis: `synthesise_friction.py` (stdlib-only, offline); `cold_start_friction_report.md` — NOT READY verdict with 5 open product BLOCKERs, cross-edition comparison table, actionable doc/code recommendations per finding

---

## v13.0 Research & Documentation Foundation (Shipped: 2026-03-24)

**Phases completed:** 4 phases, 8 plans, 2 tasks

**Key accomplishments:**
- (none recorded)

---

## v12.0 Operator Maturity (Shipped: 2026-03-24)

**Phases completed:** 11 phases (46–56), 38 plans
**Stats:** 263 files changed, +31,143 / -17,271 lines | ~23,500 LOC (Python + TypeScript) | 47 feat commits
**Timeline:** 2026-03-22 → 2026-03-24

**Key accomplishments:**
- Phase 46–48 — Security + reliability hardening: HMAC-SHA256 integrity on signature payloads, forensic audit entries for SECURITY_REJECTED outcomes, DRAFT transition safety for scheduled job re-signing, SQLite-portable NodeStats pruning and permission cache pre-warm
- Phase 47 — Multi-runtime job execution: Python, Bash, and PowerShell via unified `script` task type with container isolation, Ed25519 verification; `python_script` legacy alias removed
- Phase 49 — Cursor pagination and 9-axis job filtering: performant filtered views over large job histories with streaming CSV export and compact filter-chip UI
- Phase 50–51 — Operator-grade job management: guided dispatch form, job detail drawer with retry countdown and resubmit traceability, bulk cancel/resubmit/delete with floating action bar
- Phase 52 — Live queue monitoring and node draining: Queue.tsx WebSocket-driven view, DRAINING state machine, per-node detail drawer with dispatch diagnosis callout
- Phase 53 — Scheduling health and data management: APScheduler fire log with LATE/MISSED detection, job templates CRUD, pin/unpin execution records, retention config, CSV export
- Phase 54–56 — Integration bug fixes: all 7/7 E2E integration tests passing (script_content key, Queue URL prefix, CSV export route, retry+provenance fields)

---

## v11.1 Stack Validation (Shipped: 2026-03-22)

**Phases completed:** 8 phases (38–45), 27 plans
**Stats:** 387 files changed, +143,856 / -4,366 lines | 134 commits
**Timeline:** 2026-03-20 → 2026-03-22

**Key accomplishments:**
- Phase 38 — Teardown + CE install: idempotent soft/hard teardown scripts (PKI-preserving soft, true clean-slate hard); CE verification script covers INST-01 through INST-04 including admin re-seed safety
- Phase 39 — EE test infrastructure: Ed25519 test keypair generated; `axiom-ee` installed editable with patched public key — no Cython rebuild required; licence lifecycle edge cases (valid/expired/absent) scripted
- Phase 40 — LXC node provisioning: 4 Incus containers (DEV/TEST/PROD/STAGING) enrolled with unique per-node JOIN_TOKENs via dynamic `incusbr0` bridge IP discovery; revoke/re-enroll cycle verified
- Phase 41/42 — CE + EE validation: CE stub routes return 402 (7 routes confirmed); 13-table CE assertion; EE raises to 28 tables with all feature flags true; licence startup-gating and RBAC on `/api/licence` verified
- Phase 43 — Job test matrix: 8/9 scenarios genuinely PASS with 4 live LXC nodes — fast/slow/concurrent/env-routing/promotion/crash/bad-sig/revoked-definition; JOB-07 retry gap documented as known issue
- Phase 44 — Foundry + Smelter deep pass: STRICT CVE block, bad-base 500, dual-outcome build-dir test, air-gap mirror with iptables isolation, WARNING mode — all 6 scripts correctly SKIP on CE stack
- Phase 45 — Gap synthesis: 11 findings across the validation run (0 critical, 2 major, 9 minor); 4 patched inline with regression tests; v12.0+ backlog seeded with MIN-06/07/08/WARN-08

---

## v11.0 CE/EE Split Completion (Shipped: 2026-03-20)

**Phases completed:** 4 phases (34–37), 15 plans
**Stats:** 48 files changed, +9,883 / -72 lines | 44 commits
**Timeline:** 2026-03-19 → 2026-03-20

**Key accomplishments:**
- Phase 34 — CE isolation: 6 stub routers return 402 (not 404) for all EE routes; `importlib.metadata` replaces deprecated `pkg_resources`; `ee_only` pytest marker auto-skips EE tests in CE runs; CE pytest suite passes cleanly
- Phase 35 — `axiom-ee` private repo: `EEPlugin` wires 7 EE routers + 15 SQLAlchemy tables via `entry_points`; absolute imports throughout; async `load_ee_plugins` correctly awaited in CE lifespan; CE-alone and CE+EE smoke tests pass
- Phase 36 — Cython build pipeline: 12 compiled wheels produced (Python 3.11/3.12/3.13 × amd64/aarch64 × manylinux/musllinux); devpi server for internal wheel hosting; compiled `.so` wheel CE+EE smoke tests pass; zero `.py` source in published wheel
- Phase 37 — Licence + docs: Ed25519 offline licence validation gates all EE features at startup (air-gap safe); CE/EE edition badge in dashboard sidebar; MkDocs `!!! enterprise` admonitions across 5 EE feature pages + new `licensing.md`

### Known Gaps

- **EE-08**: `axiom-ee` stub wheel on PyPI — PyPI name reservation not completed (package reserved via GitHub only; full PyPI publish deferred)
- **DIST-02**: `axiom-ce` image on Docker Hub — explicitly deferred to v12.0+; GHCR covers current deployment scenarios

---

## v10.0 Axiom Commercial Release (Shipped: 2026-03-19)

**Phases completed:** 5 phases (29–33), 21 plans
**Stats:** 100 files changed, +13,079 / -208 lines | ~21,220 LOC (Python + TypeScript) | 92 commits
**Timeline:** 2026-03-18 → 2026-03-19

**Key accomplishments:**
- Phase 29 — Full job execution pipeline: stdout/stderr capture, script hash verification, retry machinery (attempt_number, job_run_id, retry_after, backoff), and timeout enforcement
- Phase 30 — Runtime attestation: Ed25519 bundle signing on node, RSA PKCS1v15 server-side verification, attestation export endpoint and UI verification badge
- Phase 31 — Environment tags end-to-end: DB schema → Pydantic models → node heartbeat → job dispatch → env_tag-aware routing; CI/CD dispatch endpoint (POST /api/dispatch)
- Phase 32 — Dashboard execution history view with filtering, attestation badge, retry state, attempt tabs in ExecutionLogModal, env tag badges on Nodes, DefinitionHistoryPanel
- Phase 33 — Licence compliance audit (Python + Node), GitHub org (`axiom-laboratories/axiom`), PyPI OIDC publishing, release.yml CI/CD, v10.0.0-alpha.1 tagged and published

---

## v7.0 Advanced Foundry & Smelter (Shipped: 2026-03-16)

**Phases completed:** 5 phases (11–15), 34 plans

**Key accomplishments:**
- Compatibility Engine — OS-family tagging on tools, two-pass blueprint validation (OS mismatch + dep confirmation), real-time tool filtering in blueprint creation; 12/12 Playwright checks passed
- Smelter Registry — vetted ingredient catalog with CVE scanning (pip-audit), STRICT/WARNING enforcement, compliance badging on templates; blocks non-compliant builds at Foundry
- Package Repository Mirroring — local PyPI (pypiserver) + APT (Caddy) sidecars, auto-sync on ingredient add, air-gapped manual upload, pip.conf/sources.list injection; fail-fast enforcement at build time
- Foundry Wizard UI — 5-step guided composition wizard (Identity → Base Image → Ingredients → Tools → Review), JSON editor for power users, full Smelter Registry integration for ingredient picking
- Smelt-Check + BOM + Lifecycle — post-build ephemeral validation containers, JSON Bill of Materials capture, package index for fleet-wide BOM search, image lifecycle (ACTIVE/DEPRECATED/REVOKED) enforced at enrollment and work-pull

---

## v8.0 mop-push CLI & Job Staging (Shipped: 2026-03-15)

**Phases completed:** 3 phases (17–19), 14 plans

**Key accomplishments:**
- OAuth Device Flow (RFC 8628) — MoP-native IdP, browser approval page, JWT issuance; no external IdP dependency
- mop-push CLI — login/push/create commands, Ed25519 signing locally, private key never transmitted; installable as SDK package
- Job lifecycle status (DRAFT/ACTIVE/DEPRECATED/REVOKED) — full state machine with REVOKED enforcement at dispatch
- Dashboard Staging view — inspect drafts, finalize scheduling, one-click Publish; operators review before jobs run
- OIDC v2 architecture doc — documents future external IdP integration path

---

## v9.0 Enterprise Documentation (Shipped: 2026-03-17)

**Phases completed:** 9 phases (20–28), 27 plans
**Git range:** `b9796c3` → `110feb8` (134 commits, 173 files, +22,548 / -1,741 lines)

**Key accomplishments:**
- Docs container — MkDocs Material at `/docs/`, two-stage Dockerfile (python:3.12-slim builder + nginx:alpine), Caddy routing, CDN-free (privacy + offline plugins download all Google Fonts/CDN assets at build time)
- Auto-generated API reference — FastAPI OpenAPI schema exported at container build time (no running server), Swagger UI rendered in MkDocs with 17 tag groups
- Developer documentation — architecture guide with Mermaid diagrams, setup & deployment guide, contributing guide with Black/Ruff setup and no-Alembic warning
- Complete operator documentation — end-to-end getting started walkthrough + Foundry, axiom-push CLI, job scheduling, RBAC, OAuth feature guides; mTLS, RBAC hardening, audit log, air-gap security guides
- Runbooks & FAQ — symptom-first troubleshooting for nodes, jobs, and Foundry; unified FAQ with all 4 required gotchas (blueprint dict format, EXECUTION_MODE=direct, JOIN_TOKEN, ADMIN_PASSWORD)
- Axiom rebranding — CLI renamed `axiom-push`, README rewrite (<80 lines, links to docs), CONTRIBUTING + CHANGELOG + GitHub community health files, full MkDocs naming pass across 21 docs files
- CI/CD pipelines — GitHub Actions CI (pytest matrix + vitest + docker-validate) + release workflow (multi-arch GHCR + PyPI OIDC); PyPI Trusted Publisher setup deferred pending org creation

---

