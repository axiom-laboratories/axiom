---
phase: 46-tech-debt-security-branding
verified: 2026-03-22T15:10:52Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 46: Tech Debt / Security / Branding Verification Report

**Phase Goal:** Close accumulated tech debt (DEBT-01 through DEBT-04), implement two security hardening items (SEC-01, SEC-02), and apply Foundry UI label renaming (BRAND-01).
**Verified:** 2026-03-22T15:10:52Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | NodeStats pruned to last 60 rows per node on SQLite and PostgreSQL without error | VERIFIED | Two-step SELECT+DELETE with `.notin_(keep_ids)` at job_service.py:506-518; scoped by `node_id` |
| 2 | No stale /tmp/puppet_build_* directories remain after any build outcome | VERIFIED | `try/finally` with `asyncio.to_thread(shutil.rmtree, build_dir)` at foundry_service.py:241-243 |
| 3 | No DB query executed by require_permission after startup — roles served from in-memory cache | VERIFIED | `_perm_cache.setdefault` pre-warm in `lifespan()` at main.py:96-107, wrapped in try/except for CE mode |
| 4 | Node ID selection from secrets/ is deterministic regardless of filesystem readdir order | VERIFIED | `sorted(f[:-4] for f in os.listdir(...))` with DEBT-04 comment at node.py:71 |
| 5 | SECURITY_REJECTED outcome writes audit log entry attributed to reporting node with script_hash and job_id | VERIFIED | `audit(db, _NodeActor(), "security:rejected", ...)` at job_service.py:743 before db.commit() |
| 6 | Tampered signature_payload (HMAC mismatch) rejected at dispatch before WorkResponse is sent | VERIFIED | `verify_signature_hmac()` check at job_service.py:376-399, sets status=SECURITY_REJECTED, returns PollResponse(job=None) |
| 7 | HMAC mismatch produces audit log entry with action security:hmac_mismatch | VERIFIED | `audit(db, _SystemActor(), "security:hmac_mismatch", ...)` at job_service.py:394 |
| 8 | Existing jobs with signature_payload but no HMAC tag are backfilled at startup | VERIFIED | SEC-02 backfill block in `lifespan()` at main.py:109-133, up to 1000 rows |
| 9 | Foundry shows "Image Recipe" everywhere "Blueprint" was shown | VERIFIED | Templates.tsx, CreateBlueprintDialog.tsx, BlueprintWizard.tsx all contain "Image Recipe" string literals; tab labels read "Runtime Image Recipes", "Network Image Recipes" |
| 10 | Foundry shows "Node Image" everywhere "Puppet Template" or "Template" (Foundry context) was shown | VERIFIED | CreateTemplateDialog.tsx contains "Compose Node Image", "Node Image Name", "Create Node Image"; Templates.tsx tab renamed to "Node Images" |
| 11 | Admin page Tools tab shows "Tools" where "Capability Matrix" was shown; Nav "Foundry" label unchanged | VERIFIED | Admin.tsx:1351 TabsTrigger shows "Tools"; MainLayout.tsx:98 retains "Foundry" |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|---------|--------|---------|
| `puppeteer/agent_service/services/job_service.py` | SQLite two-step NodeStats prune + SEC-01 audit + SEC-02 HMAC verify | VERIFIED | Contains `notin_(keep_ids)`, `security:rejected`, `verify_signature_hmac` |
| `puppeteer/agent_service/main.py` | Permission cache pre-warm (DEBT-03) + SEC-02 backfill | VERIFIED | Contains `_perm_cache.setdefault`, `SEC-02` backfill block |
| `puppeteer/agent_service/services/foundry_service.py` | Guaranteed build dir cleanup via try/finally | VERIFIED | `shutil.rmtree` at line 243 inside `finally:` block |
| `puppets/environment_service/node.py` | Deterministic node ID via sorted readdir | VERIFIED | `sorted(` at line 71 with DEBT-04 explanatory comment |
| `puppeteer/agent_service/security.py` | `compute_signature_hmac()` and `verify_signature_hmac()` helpers | VERIFIED | Both functions defined at lines 32-41 |
| `puppeteer/agent_service/db.py` | `Job.signature_hmac` column | VERIFIED | `signature_hmac: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)` at line 44 |
| `puppeteer/migration_v37.sql` | ALTER TABLE migration for existing deployments | VERIFIED | `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS signature_hmac VARCHAR(64)` |
| `puppeteer/dashboard/src/views/Templates.tsx` | Renamed tab labels, button text, empty states | VERIFIED | Contains "Image Recipe", "Node Images"; no bare "Blueprint" visible UI strings |
| `puppeteer/dashboard/src/components/CreateBlueprintDialog.tsx` | Renamed dialog title, field label, button text | VERIFIED | "Create New Image Recipe", "Image Recipe Name", "Create Image Recipe" |
| `puppeteer/dashboard/src/components/CreateTemplateDialog.tsx` | Renamed dialog title, labels, button text | VERIFIED | "Compose Node Image", "Node Image Name", "Create Node Image" |
| `puppeteer/dashboard/src/components/foundry/BlueprintWizard.tsx` | Renamed step labels, button text, toast messages | VERIFIED | "Image Recipe Name", "Create Image Recipe", "Save Image Recipe", "Image Recipe created successfully" |
| `puppeteer/dashboard/src/views/Admin.tsx` | "Capability Matrix" tab renamed to "Tools" | VERIFIED | TabsTrigger at line 1351 shows "Tools"; no remaining "Capability Matrix" strings |
| `puppeteer/agent_service/tests/test_job_service_nodesats_prune.py` | DEBT-01 unit tests (4 tests, 206 lines) | VERIFIED | Substantive — tests two-step prune exact 60-row retention, most-recent selection |
| `puppeteer/agent_service/tests/test_perm_cache.py` | DEBT-03 unit tests (4 tests, 187 lines) | VERIFIED | Substantive — tests pre-warm populates cache, no DB query on warm cache, 403 on missing permission, admin bypass |
| `puppeteer/agent_service/tests/test_node_id_determinism.py` | DEBT-04 unit tests (5 tests, 160 lines) | VERIFIED | Substantive — tests alphabetical selection, non-crt filtering, new ID generation, reverse-order filesystem |
| `puppeteer/agent_service/tests/test_sec01_audit.py` | SEC-01 unit tests (121 lines) | VERIFIED | Substantive — tests audit() called with security:rejected, correct actor, detail contains script_hash |
| `puppeteer/agent_service/tests/test_sec02_hmac.py` | SEC-02 unit tests (241 lines) | VERIFIED | Substantive — pure-function HMAC tests, dispatch rejection test, backfill test |
| `puppeteer/dashboard/src/views/__tests__/Templates.test.tsx` | BRAND-01 smoke tests (5 assertions) | VERIFIED | Substantive — asserts "Image Recipe", "Node Image" present; "Puppet Template", "Capability Matrix", "Runtime Blueprints" absent |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `job_service.py:process_heartbeat` | `NodeStats.id.notin_(keep_ids)` | Two-step SELECT then DELETE | WIRED | SELECT LIMIT 60 at line 506, DELETE WHERE notin_ at line 514-518 |
| `main.py:lifespan()` | `_perm_cache` | SELECT role,permission at startup | WIRED | `_perm_cache.setdefault(_role, set()).add(_perm)` at line 104 |
| `job_service.py:report_result()` | `audit(db, _NodeActor(), "security:rejected", ...)` | Sync audit() call before db.commit() at SECURITY_REJECTED transition | WIRED | Lines 733-748: status set, audit() called with script_hash, job_id, signature_id, node_id |
| `job_service.py:pull_work()` | `verify_signature_hmac()` | HMAC check before WorkResponse construction | WIRED | Lines 376-401: check at dispatch point, mismatch sets SECURITY_REJECTED, returns PollResponse(job=None) |
| `main.py:lifespan()` | `compute_signature_hmac()` backfill | Startup batch update for jobs without signature_hmac | WIRED | Lines 109-133: iterates Job rows with signature_hmac IS NULL, backfills up to 1000 |
| `Templates.test.tsx` | `Templates.tsx` rendered output | vitest render assertions | WIRED | Asserts "Runtime Image Recipe", "Node Images"; denies "Runtime Blueprints", "Puppet Template", "Capability Matrix" |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| DEBT-01 | 46-01 | SQLite-compatible NodeStats pruning | SATISFIED | Two-step prune in job_service.py:506-518; test_job_service_nodesats_prune.py passes |
| DEBT-02 | 46-01 | Build dir cleanup after all Foundry build outcomes | SATISFIED | try/finally + shutil.rmtree confirmed at foundry_service.py:241-243 |
| DEBT-03 | 46-01 | Permission cache pre-warmed at startup | SATISFIED | `_perm_cache.setdefault` in lifespan() at main.py:96-107; test_perm_cache.py passes |
| DEBT-04 | 46-01 | Deterministic node ID selection via sorted readdir | SATISFIED | `sorted(` at node.py:71 with comment; test_node_id_determinism.py passes |
| SEC-01 | 46-02 | Audit log entry for SECURITY_REJECTED outcomes attributed to reporting node | SATISFIED | `audit(db, _NodeActor(), "security:rejected", ...)` at job_service.py:743; test_sec01_audit.py passes |
| SEC-02 | 46-02 | HMAC integrity tag on signature_payload; dispatch verification; startup backfill | SATISFIED | security.py helpers, Job.signature_hmac column, migration_v37.sql, stamp/verify/backfill wired; test_sec02_hmac.py passes |
| BRAND-01 | 46-03 | Foundry UI renamed: Blueprint->Image Recipe, Template->Node Image, Capability Matrix->Tools | SATISFIED | All five TSX files updated; no legacy visible strings remain; Templates.test.tsx (5 tests) GREEN |

**All 7 requirements from REQUIREMENTS.md accounted for. No orphaned requirements.**

---

### Anti-Patterns Found

No blockers or warnings detected. Scanned key modified files for:
- TODO/FIXME/placeholder comments: none found in production code
- Empty implementations / stubs: all test files are substantive (121-241 lines each)
- Console.log-only implementations: none
- TypeScript identifier renames (prohibited by BRAND-01): none — only JSX string literals changed, TypeScript interfaces (Blueprint, ToolMatrix, PuppetTemplate) and component names preserved

---

### Human Verification Required

None — all must-haves are verifiable programmatically.

The following items would benefit from a human smoke-test of the live stack after next rebuild, but they do not block phase sign-off:

1. **Visual label correctness in running dashboard** — Load the Foundry page in a browser and confirm tab labels read "Runtime Image Recipes", "Network Image Recipes", "Node Images", and the Admin > Tools tab label is visible.

2. **SECURITY_REJECTED audit entry visible in AuditLog view** — Submit a job that a node rejects on security grounds; verify the AuditLog page shows the entry with node attribution.

---

### Gaps Summary

No gaps. All 11 observable truths are verified. All 18 artifacts exist and are substantive. All 6 key links are wired. All 7 requirement IDs (DEBT-01 through DEBT-04, SEC-01, SEC-02, BRAND-01) are satisfied and covered in REQUIREMENTS.md.

---

_Verified: 2026-03-22T15:10:52Z_
_Verifier: Claude (gsd-verifier)_
