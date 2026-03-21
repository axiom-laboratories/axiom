# OSS / Enterprise Split — Axiom CE vs EE

## Context

Master of Puppets is transitioning to **Axiom**, an open-core commercial product. The legal framework is already established: Apache 2.0 for Community Edition (CE), proprietary for Enterprise Edition (EE), `/ee` directory as legal boundary. The `/ee` dir exists but is empty — all features currently live in the OSS codebase. This plan enacts the split.

The sole current user is the author, so no backward-compatibility or migration concerns apply. Clean cut only.

---

## Final Feature Split

### CE (Community Edition — Apache 2.0, public repo)

| Domain | Included |
|--------|----------|
| Jobs | Dispatch, assignment, execution, cancel, retry, dead-letter, DAG dependencies |
| Scheduling | Cron job definitions via APScheduler |
| Nodes | Enroll, heartbeat, work pull, mTLS, CRL, revoke/reinstate, stats history |
| Auth | Local users (username/password), JWT, device auth (RFC 8628) |
| RBAC | **None** — all authenticated users are implicitly admin |
| Signing | Global Ed25519 public key registry (`signatures` table) |
| History | Execution records (output, status, duration) |
| Alerts | Job failure + node offline (no webhook delivery) |
| Signals | Inter-job dependency events |
| Worker | Pre-built standard image from Docker Hub — no custom builds |
| Dashboard | All CE views + upgrade placeholders for EE views |
| Resource limits | None — fixed sensible defaults only, not configurable |

### EE (Enterprise Edition — Proprietary, private repo, compiled .so)

| Domain | Included |
|--------|----------|
| Foundry | Blueprints, Templates, Capability Matrix, Approved OS, BOM, Artifacts/Vault |
| Smelter | Supply chain management, CVE scanning, package mirroring, airgapped support |
| Audit Log | Full security audit trail, retention, export |
| Webhooks | Outbound event delivery (HMAC-signed, retry, event filtering) |
| Triggers | Inbound CI/CD webhook dispatch |
| Service Principals | Machine-to-machine auth (client_id/secret) |
| API Keys | Personal `mop_*` tokens + per-user Ed25519 signing key management |
| RBAC | 3-role model (admin/operator/viewer), DB-backed permissions, role assignment UI |
| Resource Limits | Configurable concurrency/memory/CPU per node and per job, admission checking |
| Attestation | Compliance-grade execution proof bundle export |
| SSO | OIDC/SAML *(future)* |
| Advanced RBAC | Custom roles, fine-grained permissions *(future)* |

### CE DB Tables (13)
`users` (no `role` column), `jobs`, `scheduled_jobs`, `execution_records`, `nodes`, `node_stats`, `signatures`, `alerts`, `revoked_certs`, `tokens`, `config`, `signals`, `pings`

### EE DB Tables (created by EE plugin on startup)
`role_permissions`, `audit_log`, `webhooks`, `triggers`, `service_principals`, `user_api_keys`, `user_signing_keys`, `blueprints`, `puppet_templates`, `capability_matrix`, `approved_os`, `image_boms`, `package_index`, `artifacts`, `approved_ingredients`

---

## Technical Architecture

### Plugin System — Abstract Interface + Entry Points

CE defines ABCs and stub implementations in the public repo. EE implements the ABCs in the private repo, compiled to `.so` files, and registers via Python `entry_points`. CE discovers EE at startup — if absent, stubs serve 402s transparently.

**Public repo plugin scaffold (implemented in Phase 1):**
```
puppeteer/agent_service/ee/
  __init__.py              ← load_ee_plugins(app, engine) — entry_points discovery
  interfaces/
    foundry.py             ← ABC + 402 stub
    audit.py               ← ABC + 402 stub
    webhooks.py            ← ABC + 402 stub
    triggers.py            ← ABC + 402 stub
    auth_ext.py            ← ABC + 402 stub (SP + API keys)
    smelter.py             ← ABC + 402 stub
    rbac.py                ← stub (all users = admin)
    resource_limits.py     ← stub (returns null limits)
  routers/
    foundry_router.py      ← extracted from main.py (Phase 2)
    audit_router.py
    webhook_router.py
    trigger_router.py
    auth_ext_router.py
    users_router.py
    smelter_router.py
```

**EE entry_points (private repo `setup.cfg`):**
```ini
[options.entry_points]
axiom.ee =
    core = ee.plugin:EEPlugin
```

**Feature flags endpoint:**
```
GET /api/features
→ {"audit": false, "foundry": false, "webhooks": false,
   "triggers": false, "rbac": false, "resource_limits": false,
   "service_principals": false, "api_keys": false}
```

---

## Implementation Progress

### Phase 1 — Plugin scaffold + feature flags endpoint ✅ COMPLETE
- Created `agent_service/ee/` with all interface stubs
- Added `GET /api/features` endpoint
- `load_ee_plugins(app, engine)` wired into lifespan startup

### Phase 2 — Extract EE routers from main.py ✅ COMPLETE
- Moved all EE route handlers into `ee/routers/` (7 router files)
- Created `agent_service/deps.py` (shared auth dependencies)
- Pure structural refactor — no logic changes

### Phase 3 — Strip RBAC and resource limits from CE ✅ COMPLETE
- Removed 15 EE DB models from `db.py`
- Stripped `role`, `must_change_password` from `User`
- Stripped `concurrency_limit`, `job_memory_limit` from `Node`
- Stripped `memory_limit`, `cpu_limit` from `Job`
- Replaced all `require_permission()` with `require_auth`
- Removed RBAC + capability matrix seeding from startup
- Webhook service is now a no-op stub in CE

### Phase 4 — Frontend upgrade placeholders ✅ COMPLETE
- `src/hooks/useFeatures.ts` — fetches `/api/features`, caches 5 min
- `src/components/UpgradePlaceholder.tsx` — lock icon + EE upgrade card
- EE views show placeholder when feature is false: Templates, AuditLog, Users, ServicePrincipals, Webhooks
- Sidebar shows lock icons on EE nav items

### Phase 5 — Private repo setup + router migration ⏳ TODO
- Create `axiom-ee` private GitHub repo
- Move extracted router files there
- Configure `setup.cfg` entry_points
- Validate: CE alone = graceful degradation, CE + `pip install axiom-ee` = full functionality

### Phase 6 — Compile EE to `.so` ⏳ TODO
- Set up Cython/Nuitka build pipeline in private repo CI
- Build and test compiled artifacts
- Confirm no `.py` source ships in EE distribution

### Phase 7 — Documentation and licensing ⏳ TODO
- Update in-app docs to distinguish CE vs EE
- Add license key validation to EE plugin
- Publish CE to Docker Hub as `axiom-ce`
- EE distributed as signed Docker layer or pip package

---

## Branch

`feature/axiom-oss-ee-split` (worktree at `.worktrees/axiom-split/`)

---

## Verification Checklist

- [x] CE cold-start: 13 tables created, no EE routes registered
- [x] CE routes return 402: `/api/blueprints`, `/admin/audit-log`, `/api/webhooks`
- [x] CE core works: job dispatch, node heartbeat, cron scheduling, signing
- [x] `GET /api/features` returns all `false` in CE mode
- [x] Frontend shows upgrade placeholders for EE views
- [ ] EE install restores features: `pip install axiom-ee` → features all `true`
- [ ] Compiled `.so`: verify no `.py` source in EE distribution artifact
