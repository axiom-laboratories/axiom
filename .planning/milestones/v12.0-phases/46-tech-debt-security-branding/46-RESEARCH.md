# Phase 46: Tech Debt + Security + Branding - Research

**Researched:** 2026-03-22
**Domain:** FastAPI / SQLAlchemy async / Python stdlib / React/TypeScript string sweeps
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **DEBT-01**: Fix NodeStats SQLite pruning subquery incompatibility. Claude's discretion on exact SQL rewrite approach.
- **DEBT-02**: Wrap foundry build logic in try/finally to guarantee cleanup of `/tmp/puppet_build_*` on both success and failure paths.
- **DEBT-03**: Pre-populate `_perm_cache` at startup (in `lifespan()`) so no request ever triggers a live DB query. Cache invalidation on permission change already wired — no changes needed there.
- **DEBT-04**: Sort readdir results in `_load_or_generate_node_id()` before selecting the first cert — one-line fix in `node.py`.
- **SEC-01**: Audit entry for SECURITY_REJECTED using `node_id` as actor. Detail JSON: `script_hash`, `job_id`, `signature_id`, `node_id`. Written in `job_service.py:report_result()` at `new_status = SECURITY_REJECTED` transition. Use existing `audit()` helper with `action="security:rejected"`.
- **SEC-02**: New `signature_hmac` column on `jobs` table (nullable). Key derived from `ENCRYPTION_KEY`. HMAC computed over `signature_payload + signature_id + job_id`. Stamped at job submission/dispatch. Verified before `WorkResponse` is sent. On mismatch: reject + audit log. Startup migration pass backfills existing rows. Both `ALTER TABLE` migration file and `create_all` coverage for fresh installs.
- **BRAND-01**: Full UI label sweep — "Blueprint" → "Image Recipe", "PuppetTemplate"/"Template" (Foundry context) → "Node Image", "CapabilityMatrix entry"/"capability matrix references" → "Tool". Scope: `Templates.tsx`, all Foundry-related components, in-app Docs. Nav "Foundry" label stays. Zero API/DB changes.

### Claude's Discretion

- Exact SQL rewrite approach for DEBT-01 (subselect → JOIN or two-step delete)
- try/finally structure for DEBT-02 cleanup
- HMAC algorithm (HMAC-SHA256 is the obvious choice)
- How to structure the startup migration pass for SEC-02
- Whether to add `signature_hmac` column via ALTER TABLE migration file or via `create_all` on fresh installs (both)

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEBT-01 | NodeStats pruning is SQLite-compatible — removes subquery incompatibility | See: SQLite DELETE subquery section; two-step delete pattern documented |
| DEBT-02 | Foundry service removes temp build directory after both success and failure | See: try/finally pattern; foundry_service.py already has finally block at line 241 |
| DEBT-03 | Permission lookups in `require_permission` do not execute a DB query per request | See: `_perm_cache` pre-warm; `deps.py` cache infrastructure analysis |
| DEBT-04 | Node ID scan uses deterministic (sorted) ordering | See: `node.py` analysis; sort already applied at line 71 |
| SEC-01 | SECURITY_REJECTED job results produce an audit log entry attributed to the reporting node | See: `audit()` helper, `report_result()` transition point |
| SEC-02 | Stored `signature_payload` fields carry an HMAC integrity tag; dispatch verifies before sending to node | See: HMAC-SHA256 approach, `ENCRYPTION_KEY` derivation, startup backfill pattern |
| BRAND-01 | Dashboard displays renamed labels throughout Foundry UI | See: affected files list; rename map; scope analysis |
</phase_requirements>

---

## Summary

Phase 46 is a focused cleanup-and-hardening pass. It touches four distinct code areas: SQLAlchemy async delete SQL (DEBT-01), async file cleanup (DEBT-02), startup cache warming (DEBT-03), a one-liner in node.py (DEBT-04), audit logging at a new transition point (SEC-01), HMAC column addition with startup backfill (SEC-02), and a string-sweep rename across the React dashboard (BRAND-01).

No new API surfaces, no new data models beyond `jobs.signature_hmac`, no frontend routing changes. All backend changes are confined to `job_service.py`, `deps.py`/`main.py`, `foundry_service.py`, `node.py`, and a new migration file. All frontend changes are string renames across `Templates.tsx`, `CreateBlueprintDialog.tsx`, `CreateTemplateDialog.tsx`, `BlueprintWizard.tsx`, and `Admin.tsx`.

**Primary recommendation:** Execute in three plans: (1) the four DEBT items together (all small, self-contained, no risk of interaction), (2) the two SEC items together (both touch `job_service.py` + startup + a new migration), (3) BRAND-01 as a standalone frontend plan.

---

## Standard Stack

### Core (no new dependencies needed)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `sqlalchemy` (async) | existing | ORM + raw text queries for DEBT-01 workaround | `asyncio` delete path already in use |
| `hashlib` (stdlib) | stdlib | `hashlib.hmac` / `hmac.new` for SEC-02 HMAC-SHA256 | Already imported in `job_service.py` for `script_hash` |
| `hmac` (stdlib) | stdlib | Constant-time comparison (`hmac.compare_digest`) for SEC-02 verify | Avoids timing attacks on HMAC check |
| `asyncio.to_thread` | stdlib | Already used in `foundry_service.py` for blocking cleanup | DEBT-02 cleanup already wrapped correctly |
| `shutil.rmtree` | stdlib | Temp dir teardown — DEBT-02 | Already imported in `foundry_service.py` |

**Installation:** No new packages required for any of the seven requirements.

---

## Architecture Patterns

### DEBT-01: SQLite-Compatible NodeStats Pruning

**Problem identified:** Lines 462–470 of `job_service.py` prune NodeStats using a correlated subquery:

```python
subq = (
    select(NodeStats.id)
    .where(NodeStats.node_id == node_id)
    .order_by(desc(NodeStats.recorded_at))
    .offset(60)
    .subquery()
)
await db.execute(delete(NodeStats).where(NodeStats.id.in_(select(subq.c.id))))
```

SQLite does not support `DELETE ... WHERE id IN (SELECT ... FROM (subquery))` with LIMIT/OFFSET. The double-subquery wrapping (`select(subq.c.id)`) triggers SQLite's "subquery not yet implemented" error silently — rows are never pruned.

**Fix — two-step delete (recommended):**

```python
# Step 1: fetch IDs to keep (last 60, ordered newest first)
keep_result = await db.execute(
    select(NodeStats.id)
    .where(NodeStats.node_id == node_id)
    .order_by(desc(NodeStats.recorded_at))
    .limit(60)
)
keep_ids = [row[0] for row in keep_result.all()]

# Step 2: delete everything else for this node
if keep_ids:
    await db.execute(
        delete(NodeStats)
        .where(NodeStats.node_id == node_id)
        .where(NodeStats.id.notin_(keep_ids))
    )
else:
    # No stats yet — nothing to prune
    pass
```

This works on both SQLite and PostgreSQL. The `notin_` with a plain Python list is safe up to the ~60-row limit (no performance concern).

**Alternative — JOIN-based delete (Postgres only, not recommended):**
A `DELETE ... USING` JOIN works in Postgres but not SQLite. Do not use this approach.

### DEBT-02: Foundry Build Directory Cleanup

**Current state:** `foundry_service.py` lines 241–243 already contain a `finally` block that calls `shutil.rmtree`. The existing test (`test_foundry_build_cleanup.py`) already asserts this behaviour for both success and failure paths. Review whether the existing implementation fully satisfies DEBT-02 or whether there was a regression.

The current code structure:
```python
try:
    # ... build logic ...
    return ImageResponse(...)
finally:
    if os.path.exists(build_dir):
        await asyncio.to_thread(shutil.rmtree, build_dir)
```

This is the correct pattern. If tests pass, DEBT-02 is already implemented. The plan should verify via the existing test suite and mark the requirement done if tests green.

**If the test suite is failing:** check whether `asyncio.to_thread(shutil.rmtree, ...)` correctly handles the case where `build_dir` was never created (e.g., early exception before `os.makedirs`). The `os.path.exists` guard handles this correctly.

### DEBT-03: Permission Cache Pre-Warm

**Current state in `deps.py`:**

- `_perm_cache: dict[str, set[str]] = {}` exists (line 83)
- `_invalidate_perm_cache()` exists (line 86)
- `require_permission()` already populates the cache on first miss (lines 107–114)
- Problem: the first request for each role still hits the DB; the cache is populated lazily per role

**Fix — pre-warm at startup in `main.py:lifespan()`, after `init_db()` and before `yield`:**

```python
# Pre-warm permission cache so no request triggers a DB query
async with AsyncSessionLocal() as db:
    from sqlalchemy import text
    result = await db.execute(text("SELECT role, permission FROM role_permissions"))
    rows = result.all()
    from .deps import _perm_cache
    for role, perm in rows:
        _perm_cache.setdefault(role, set()).add(perm)
    logger.info(f"Permission cache pre-warmed: {len(_perm_cache)} roles")
```

**Pitfall:** In CE mode the `role_permissions` table may not exist. The startup call must catch the exception (table-not-found) and proceed silently — exactly as `require_permission` already does by checking `RolePermission = Base.metadata.tables.get("role_permissions")`. Wrap in `try/except Exception: pass` with a debug log.

**Pitfall:** The existing `require_permission()` already guards with `if getattr(current_user, 'role', 'viewer') not in _perm_cache` — this is correct. After the pre-warm, the cache contains all roles, so the guard is never triggered during request handling.

### DEBT-04: Node ID Scan Determinism

**Current state in `node.py` line 71:**

```python
existing = sorted(f[:-4] for f in os.listdir("secrets") if f.endswith(".crt") and f.startswith("node-"))
return existing[0] if existing else f"node-{uuid.uuid4().hex[:8]}"
```

The fix is already present — `sorted()` is called on line 71. Verify this is the live code and the requirement is satisfied. If the fix is present, DEBT-04 is done; the plan should confirm and mark it complete.

**Note for planner:** If the code already contains `sorted()`, DEBT-04 may be a "verify and close" task rather than a code-change task.

### SEC-01: SECURITY_REJECTED Audit Entry

**Where to insert:** `job_service.py:report_result()`, at the point where `new_status = "SECURITY_REJECTED"` is set (line 684). The `node_id` at this point is `job.node_id` (the node that reported the rejection).

**Pattern using existing `audit()` helper:**

```python
# In report_result(), after new_status = "SECURITY_REJECTED" is determined:
if new_status == "SECURITY_REJECTED":
    from ..deps import audit
    # Compute script_hash for the detail (reuse orchestrator_hash if already computed)
    _detail = {
        "script_hash": orchestrator_hash,  # already computed at line 722
        "job_id": guid,
        "signature_id": ...,  # needs to be read from job payload or job model
        "node_id": job.node_id,
    }
    # Create a lightweight user-like object with username = node_id for audit attribution
    class _NodeActor:
        username = job.node_id
    audit(db, _NodeActor(), "security:rejected", resource_id=guid, detail=_detail)
```

**Key insight:** `audit()` in `deps.py` is synchronous (`def`, not `async`). It calls `db.execute(text(...))` — a synchronous call on an `AsyncSession`. The existing code pattern in `deps.py` does this intentionally (it swallows exceptions). The call must remain synchronous.

**`signature_id` sourcing:** The `Job` model currently does not have a `signature_id` column. The `signature_id` is embedded in the job payload JSON as part of `signature_payload`. Either extract it from `job.payload` JSON or accept `None` for jobs without a signature. For HMAC-tagged jobs (SEC-02), the `signature_id` will be available from the payload. Set it to `None` gracefully if absent.

**Ordering:** The audit call should happen before `db.commit()` at line 824 to ensure it's in the same transaction.

### SEC-02: HMAC Integrity on signature_payload

**DB change:** Add `signature_hmac` column to the `jobs` table. Add to `Job` model in `db.py`:

```python
signature_hmac: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
```

**Migration file** — `migration_v37.sql`:

```sql
-- migration_v37: Add signature_hmac column for payload integrity (SEC-02)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS signature_hmac VARCHAR(64);
```

**HMAC key derivation:** Derive from `ENCRYPTION_KEY` using HKDF or simply use it directly as HMAC key (simpler, consistent with existing Fernet key reuse pattern). Direct use is acceptable — `ENCRYPTION_KEY` is already a 32-byte Fernet key (URL-safe base64 encoded), decode it:

```python
import hmac as _hmac
import hashlib

def _compute_hmac(encryption_key_bytes: bytes, signature_payload: str, signature_id: str, job_id: str) -> str:
    message = f"{signature_payload}:{signature_id}:{job_id}".encode("utf-8")
    return _hmac.new(encryption_key_bytes, message, hashlib.sha256).hexdigest()
```

Access the raw key bytes: `ENCRYPTION_KEY` in `security.py` is already `os.getenv("ENCRYPTION_KEY").encode()` — this is the base64-encoded Fernet key. For HMAC, use it as-is (the encoded bytes are fine as a key material).

**Stamp point:** In `job_service.py:create_job()`, after committing the new job, compute and store HMAC if the payload contains a `signature_payload` field. Also compute during `pull_work()` dispatch path (belt-and-suspenders: check at dispatch time).

**Verification point:** In `pull_work()`, before constructing `WorkResponse`, check:
```python
if selected_job.signature_hmac:
    expected = _compute_hmac(encryption_key, payload["signature_payload"], payload["signature_id"], selected_job.guid)
    if not _hmac.compare_digest(selected_job.signature_hmac, expected):
        # Reject dispatch
        selected_job.status = "SECURITY_REJECTED"
        selected_job.completed_at = datetime.utcnow()
        audit(db, _NodeActor(...), "security:hmac_mismatch", ...)
        await db.commit()
        return PollResponse(job=None, ...)
```

**Startup backfill pass** — add after cache pre-warm in `lifespan()`:

```python
# SEC-02: Backfill HMAC tags for existing jobs without them
async with AsyncSessionLocal() as db:
    result = await db.execute(
        select(Job).where(
            Job.signature_hmac == None,
            Job.payload != None
        ).limit(1000)  # batch to avoid huge transaction
    )
    jobs_to_backfill = result.scalars().all()
    backfilled = 0
    for job in jobs_to_backfill:
        try:
            payload = json.loads(job.payload)
            sig_payload = payload.get("signature_payload")
            sig_id = payload.get("signature_id")
            if sig_payload and sig_id:
                job.signature_hmac = _compute_hmac(enc_key, sig_payload, sig_id, job.guid)
                backfilled += 1
        except Exception:
            continue
    if backfilled:
        await db.commit()
    logger.info(f"SEC-02: Backfilled HMAC for {backfilled} existing jobs")
```

**Where to import encryption key for HMAC:** Import `ENCRYPTION_KEY` (already the raw env bytes) from `security.py`. Decode the Fernet base64 key: `import base64; raw_key = base64.urlsafe_b64decode(ENCRYPTION_KEY + b"==")` for consistent 32-byte HMAC key. Or simply use `ENCRYPTION_KEY` bytes directly — either is defensible.

### BRAND-01: UI Label Rename Scope

**Affected files and specific changes needed:**

| File | Legacy Labels to Replace |
|------|-------------------------|
| `Templates.tsx` | Tab labels "Runtime Blueprints"/"Network Blueprints" → "Runtime Image Recipes"/"Network Image Recipes"; `<BlueprintItem>` card headers; "New Runtime Blueprint" / "New Network Blueprint" buttons; "Add Capability Matrix Entry" dialog title; `UpgradePlaceholder` description string; empty state text |
| `CreateBlueprintDialog.tsx` | Dialog title "Create New Blueprint" → "Create New Image Recipe"; "Blueprint Name" label → "Image Recipe Name"; "Creating..." / "Create Blueprint" button text |
| `CreateTemplateDialog.tsx` | Dialog title "Compose Puppet Template" → "Compose Node Image"; "Template Friendly Name" → "Node Image Name"; "Runtime Blueprint" label → "Runtime Image Recipe"; "Create Template" button → "Create Node Image" |
| `BlueprintWizard.tsx` | "Blueprint Name" label → "Image Recipe Name"; "Create Blueprint" / "Save Blueprint" buttons; success toast "Blueprint created successfully" |
| `Admin.tsx` | Tab trigger "Capability Matrix" → "Tools"; `CapabilityMatrixManager` component display text |

**Items that do NOT change:**
- TypeScript interface names (`Blueprint`, `ToolMatrix`) — internal, not visible in UI
- API endpoint paths (`/api/blueprints`, `/api/templates`) — no API changes
- `const BlueprintItem`, `const BlueprintWizard`, `const BlueprintEmptyState` — React component names (internal)
- Nav sidebar "Foundry" label — explicitly locked as correct brand name
- Admin.tsx tab `matrix` — the value string is internal; only the visible label changes

**No Docs.tsx exists** — the in-app Docs view referenced in CONTEXT.md was not found in the codebase. The planner should either skip the docs sweep or verify if docs content exists elsewhere (e.g., inline markdown strings).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Constant-time HMAC comparison | Manual `==` on digest strings | `hmac.compare_digest()` | Prevents timing side-channel attacks |
| HMAC computation | Custom hash schemes | `hmac.new(key, msg, hashlib.sha256)` | NIST-standard; already in stdlib |
| SQLite-safe multi-row delete | Custom iteration | Two-step `SELECT ids then DELETE ... WHERE notin_` | Cross-DB compatible; no SQLite subquery limit issues |
| Async blocking file ops | Direct `shutil.rmtree()` in async context | `await asyncio.to_thread(shutil.rmtree, path)` | Avoids blocking the event loop |

---

## Common Pitfalls

### Pitfall 1: SQLite Subquery DELETE
**What goes wrong:** `DELETE WHERE id IN (SELECT id FROM (SELECT id ... OFFSET N))` silently fails on SQLite — no error raised, no rows deleted.
**Why it happens:** SQLite does not support LIMIT/OFFSET in subqueries used by DELETE WHERE IN.
**How to avoid:** Two-step pattern: SELECT IDs to keep into a Python list, then DELETE WHERE id NOT IN (python list).
**Warning signs:** NodeStats table grows unboundedly in SQLite-backed dev deployments; no logs of pruning occurring.

### Pitfall 2: `audit()` is synchronous
**What goes wrong:** Calling `await audit(...)` raises TypeError since `audit()` is `def`, not `async def`.
**Why it happens:** The helper uses sync `db.execute(text(...))` intentionally, swallowing exceptions from CE mode (no audit_log table).
**How to avoid:** Call as `audit(db, actor, ...)` without `await`. Verify the existing call sites in `main.py` for the pattern.

### Pitfall 3: HMAC Key Encoding Mismatch
**What goes wrong:** HMAC computed at stamp time uses different key encoding than at verify time, causing spurious mismatches on all jobs.
**Why it happens:** `ENCRYPTION_KEY` is stored as base64-encoded bytes in the env var. If you decode before hashing on one path but not the other, the keys differ.
**How to avoid:** Use `ENCRYPTION_KEY` bytes consistently (either always raw env bytes, or always base64-decoded). Centralise the HMAC helper function in one place (e.g., `security.py`) and import it from both `job_service.py` locations.

### Pitfall 4: Startup Backfill with Large Jobs Table
**What goes wrong:** Startup hangs for 30+ seconds when backfilling HMAC for a production database with thousands of jobs.
**Why it happens:** `SELECT * FROM jobs WHERE signature_hmac IS NULL` returns the full table.
**How to avoid:** Add `.limit(1000)` to the startup backfill query. Any remaining unhashed rows will be caught next restart, or can be backfilled by a separate script. Document this batch-size limit.

### Pitfall 5: Permission Cache Pre-Warm in CE Mode
**What goes wrong:** Startup crashes or logs noisy errors when `role_permissions` table does not exist (CE deployment).
**Why it happens:** The `SELECT role, permission FROM role_permissions` query throws an exception in CE mode.
**How to avoid:** Wrap the pre-warm block in `try/except Exception: logger.debug("CE mode: no role_permissions table — cache pre-warm skipped")`.

### Pitfall 6: BRAND-01 Scope Creep vs Missing Coverage
**What goes wrong:** Either (a) renaming TypeScript interface `Blueprint` causes type errors across the file, or (b) missing a visible label in an error toast or empty state.
**Why it happens:** (a) Renaming internal identifiers alongside visible strings is unnecessary. (b) Grep-and-replace misses interpolated strings.
**How to avoid:** (a) Only rename string literals in JSX (`>Blueprint<`, `"Blueprint"`, `` `Blueprint` ``), not TypeScript identifiers. (b) Search all affected files for "Blueprint", "Template" (in Foundry context), and "Capability Matrix" — review every hit before committing.

---

## Code Examples

### DEBT-01: Two-Step SQLite-Compatible Prune
```python
# Source: stdlib SQLAlchemy + SQLite constraint analysis
keep_result = await db.execute(
    select(NodeStats.id)
    .where(NodeStats.node_id == node_id)
    .order_by(desc(NodeStats.recorded_at))
    .limit(60)
)
keep_ids = [row[0] for row in keep_result.all()]
if keep_ids:
    await db.execute(
        delete(NodeStats)
        .where(NodeStats.node_id == node_id)
        .where(NodeStats.id.notin_(keep_ids))
    )
```

### SEC-02: HMAC Computation Helper (place in security.py)
```python
import hmac as _hmac
import hashlib
import base64

def compute_signature_hmac(encryption_key_bytes: bytes, signature_payload: str, signature_id: str, job_id: str) -> str:
    """Compute HMAC-SHA256 over signature_payload:signature_id:job_id."""
    message = f"{signature_payload}:{signature_id}:{job_id}".encode("utf-8")
    return _hmac.new(encryption_key_bytes, message, hashlib.sha256).hexdigest()

def verify_signature_hmac(encryption_key_bytes: bytes, stored_hmac: str, signature_payload: str, signature_id: str, job_id: str) -> bool:
    """Constant-time HMAC verification."""
    expected = compute_signature_hmac(encryption_key_bytes, signature_payload, signature_id, job_id)
    return _hmac.compare_digest(stored_hmac, expected)
```

### SEC-01: Audit Call Pattern (synchronous)
```python
# In job_service.py:report_result(), before db.commit()
if new_status == "SECURITY_REJECTED":
    class _NodeActor:
        username = job.node_id or "unknown-node"
    audit(db, _NodeActor(), "security:rejected", resource_id=guid, detail={
        "script_hash": orchestrator_hash,
        "job_id": guid,
        "signature_id": json.loads(job.payload).get("signature_id"),
        "node_id": job.node_id,
    })
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| SQLite subquery prune (silently fails) | Two-step Python-list prune | Fixes DEBT-01 |
| No cleanup on build failure | try/finally rmtree | Already in foundry_service.py — verify/confirm for DEBT-02 |
| Per-request role_permissions DB query | Pre-warmed cache at startup | DEBT-03 |
| Non-deterministic os.listdir | `sorted()` on listdir | Already applied in node.py — verify/confirm for DEBT-04 |
| No SECURITY_REJECTED audit trail | Audit entry with node attribution | SEC-01 |
| signature_payload stored without integrity check | HMAC-SHA256 tag stamped at submission | SEC-02 |

---

## Open Questions

1. **DEBT-02 and DEBT-04 may already be fixed**
   - What we know: `foundry_service.py` lines 241–243 already have a `finally` block with `shutil.rmtree`. `node.py` line 71 already calls `sorted()`. The existing tests in `test_foundry_build_cleanup.py` cover both success and failure paths.
   - What's unclear: Were these applied in a prior sprint, or are the tests failing? If already fixed, these are "verify and close" tasks.
   - Recommendation: The plan should start each of these with a test run. If green, write a summary noting the requirement is satisfied and move on.

2. **`signature_id` availability in job payload**
   - What we know: The `Job` model has no `signature_id` column. The `ScheduledJob` model does. For manually submitted jobs, the signature_id may or may not be in the payload JSON.
   - What's unclear: Is `signature_id` consistently present in `job.payload` for all signed jobs?
   - Recommendation: For SEC-01 detail JSON, extract `signature_id` from `json.loads(job.payload).get("signature_id")` with a fallback to `None`. For SEC-02 HMAC, skip jobs where `signature_id` is absent from payload — no HMAC needed for unsigned jobs.

3. **Docs page for BRAND-01**
   - What we know: CONTEXT.md references an in-app Docs page but no `Docs.tsx` exists in the codebase.
   - What's unclear: Is the docs content embedded elsewhere (e.g., in `Admin.tsx`, or as inline markdown)?
   - Recommendation: Grep for "Blueprint" and "Template" across all `.tsx` files and the `Admin.tsx` — the sweep will catch any docs-related content. The plan should note that no dedicated `Docs.tsx` was found and the sweep covers all identified occurrences.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend Framework | pytest + pytest-asyncio |
| Backend Config | `puppeteer/pytest.ini` or pyproject.toml (check at run time) |
| Backend Quick Run | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py -x` |
| Backend Full Suite | `cd puppeteer && pytest` |
| Frontend Framework | Vitest |
| Frontend Quick Run | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/` |
| Frontend Full Suite | `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-01 | SQLite prune does not silently fail; NodeStats is pruned after > 60 rows | unit | `cd puppeteer && pytest tests/test_job_service_nodesats_prune.py -x` | ❌ Wave 0 |
| DEBT-02 | build dir cleaned on success and failure | unit | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py -x` | ✅ |
| DEBT-03 | No DB query fired during require_permission after startup | unit | `cd puppeteer && pytest tests/test_perm_cache.py -x` | ❌ Wave 0 |
| DEBT-04 | Node ID selection is deterministic on unsorted dir | unit | `cd puppeteer && pytest tests/test_node_id_determinism.py -x` | ❌ Wave 0 |
| SEC-01 | SECURITY_REJECTED report writes audit entry with node actor and script_hash | unit | `cd puppeteer && pytest tests/test_sec01_audit.py -x` | ❌ Wave 0 |
| SEC-02 | HMAC mismatch on dispatch rejects job; startup backfill tags existing rows | unit | `cd puppeteer && pytest tests/test_sec02_hmac.py -x` | ❌ Wave 0 |
| BRAND-01 | No legacy labels ("Blueprint", "Puppet Template", "Capability Matrix") visible in Foundry UI | smoke | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Templates.test.tsx -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/ -x -q` (backend) or `cd puppeteer/dashboard && npx vitest run` (frontend)
- **Per wave merge:** full suite — `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `puppeteer/tests/test_job_service_nodesats_prune.py` — covers DEBT-01 (SQLite-compatible prune)
- [ ] `puppeteer/tests/test_perm_cache.py` — covers DEBT-03 (no DB query per request after startup)
- [ ] `puppeteer/tests/test_node_id_determinism.py` — covers DEBT-04 (sorted readdir)
- [ ] `puppeteer/tests/test_sec01_audit.py` — covers SEC-01 (SECURITY_REJECTED audit entry)
- [ ] `puppeteer/tests/test_sec02_hmac.py` — covers SEC-02 (HMAC stamp, verify, backfill)
- [ ] `puppeteer/dashboard/src/views/__tests__/Templates.test.tsx` — covers BRAND-01 (no legacy labels)

Existing `test_foundry_build_cleanup.py` covers DEBT-02 — no new test file needed.

---

## Sources

### Primary (HIGH confidence)
- Direct source code inspection: `job_service.py`, `foundry_service.py`, `security.py`, `deps.py`, `db.py`, `node.py` — all patterns verified against live code
- Direct source inspection: `Templates.tsx`, `CreateBlueprintDialog.tsx`, `CreateTemplateDialog.tsx`, `BlueprintWizard.tsx`, `Admin.tsx` — all affected strings identified
- Python stdlib `hmac` module: `hmac.new()`, `hmac.compare_digest()` — standard since Python 3.x
- SQLite documentation: DELETE with subquery LIMIT/OFFSET not supported — confirmed by SQLite known limitations

### Secondary (MEDIUM confidence)
- SQLAlchemy async delete pattern: `delete(Model).where(Model.id.notin_(list))` — standard SQLAlchemy Core expression, works on both SQLite and Postgres

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns are in existing codebase
- Architecture: HIGH — all integration points confirmed by reading live source code
- Pitfalls: HIGH — SQLite subquery failure confirmed by reading the exact failing query; other pitfalls derived from existing code patterns

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable codebase — no fast-moving dependencies involved)
