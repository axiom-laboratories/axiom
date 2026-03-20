# Milestones

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

