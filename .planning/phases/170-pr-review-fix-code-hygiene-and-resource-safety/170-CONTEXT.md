# Phase 170: PR Review Fix — Code Hygiene and Resource Safety - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix four LOW-severity issues from PR #24 code review:
1. Replace deprecated `asyncio.get_event_loop()` with `asyncio.get_running_loop()` in `deps.py`
2. Expose a public `renewal_failures` property on `VaultService` (currently private `_consecutive_renewal_failures`)
3. Move residual route groups (retention, verification-key, docs, job-definitions alias) out of `main.py` into their appropriate routers
4. Snapshot `VaultService.config` into a frozen dataclass at init time to prevent `DetachedInstanceError` when background lease renewal accesses config fields after the originating DB session has closed

No new features. No UI changes. No schema changes. Pure correctness and hygiene fixes.

</domain>

<decisions>
## Implementation Decisions

### Fix 1 — asyncio.get_event_loop() → get_running_loop()
- **D-01:** In `deps.py` at line ~171, replace `asyncio.get_event_loop()` with `asyncio.get_running_loop()`.
- `get_running_loop()` is the correct call from async context — returns the running loop or raises `RuntimeError` if called outside one (which is the right failure mode). `get_event_loop()` is deprecated in Python 3.10+ and emits a `DeprecationWarning` when no running loop exists.
- No other occurrences of `get_event_loop()` need changing (this is the only one in the non-test codebase).

### Fix 2 — Public renewal_failures property on VaultService
- **D-02:** Add a `@property renewal_failures(self) -> int` to `VaultService` that returns `self._consecutive_renewal_failures`.
- Name matches the PR review finding exactly. No richer wrapper needed — raw count is what consumers (status endpoints, tests) need.

### Fix 3 — Route migration out of main.py

**Destinations:**
- **D-03:** `GET /api/admin/retention` + `POST /api/admin/retention` → `admin_router.py` (already handles admin endpoints; retention is admin-gated)
- **D-04:** `GET /job-definitions` (alias) → `jobs_router.py` (sibling alias to the canonical `/jobs/definitions` already there)
- **D-05:** `GET /verification-key` → `system_router.py` (already tagged "System"; unauthenticated utility endpoint)
- **D-06:** `GET /api/docs` + `GET /api/docs/{filename}` → `system_router.py` (already tagged "System"; utility endpoint for in-app docs)

**Docs path calculation fix (required):**
- **D-07:** The docs routes currently compute `base_dir` using `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` from `main.py` (`agent_service/main.py → agent_service/ → puppeteer/`). When moved to `system_router.py` at `agent_service/routers/system_router.py`, one extra `os.path.dirname()` call is needed to reach the same `puppeteer/` root. Use three levels: `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`.

### Fix 4 — Frozen dataclass for VaultService config

**Claude's Discretion (user delegated):**
- **D-08:** Define `VaultConfigSnapshot` as a `@dataclass(frozen=True)` in `vault_service.py` (co-located with its only consumer). Fields: `enabled: bool`, `vault_address: str`, `role_id: str`, `secret_id: str`, `mount_path: str`, `namespace: Optional[str]`, `provider_type: str`. Exclude metadata fields (`id`, `created_at`, `updated_at`) — VaultService never reads those.
- **D-09:** Add a `@classmethod from_orm(cls, vc: VaultConfig) -> VaultConfigSnapshot` to `VaultConfigSnapshot` for clean ORM→snapshot conversion.
- **D-10:** `VaultService.__init__` keeps its current signature `(config: Optional[VaultConfig], db: AsyncSession)` for backward compatibility. Internally it snapshots immediately: `self.config: Optional[VaultConfigSnapshot] = VaultConfigSnapshot.from_orm(config) if config else None`. The stored type changes from `Optional[VaultConfig]` to `Optional[VaultConfigSnapshot]`.
- **D-11:** In `vault_router.py`, the reinit line `vault_service.config = vault_config` must be updated to `vault_service.config = VaultConfigSnapshot.from_orm(vault_config)`. Import `VaultConfigSnapshot` at the top of `vault_router.py` alongside the existing `VaultService` import.
- **D-12:** No changes needed to `main.py` startup — `VaultService(_vault_config, _db)` continues to work because `__init__` now snapshots internally.

### Claude's Discretion
- Fix ordering within a single plan: do Fix 1 and Fix 2 first (trivial), then Fix 3 (route moves), then Fix 4 (frozen dataclass). Each is independently testable.
- The `VaultConfigSnapshot.from_orm` classmethod approach was chosen over a property setter or `reconfigure()` method because it's the simplest and most explicit — callers remain straightforward and the conversion intent is visible at the call site.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Files to Modify
- `puppeteer/agent_service/deps.py` — line ~171: `asyncio.get_event_loop()` → `get_running_loop()`
- `puppeteer/ee/services/vault_service.py` — add `renewal_failures` property; define `VaultConfigSnapshot` frozen dataclass; update `__init__` to snapshot at init
- `puppeteer/agent_service/main.py` — remove 4 route groups (retention, verification-key, docs, job-defs alias) after migrating
- `puppeteer/agent_service/routers/admin_router.py` — add retention routes
- `puppeteer/agent_service/routers/jobs_router.py` — add job-definitions alias route
- `puppeteer/agent_service/routers/system_router.py` — add verification-key and docs routes (with adjusted path calculation)
- `puppeteer/agent_service/ee/routers/vault_router.py` — update reinit line + import `VaultConfigSnapshot`

### Files for Reference Only (no changes needed)
- `puppeteer/agent_service/db.py` — `VaultConfig` ORM model fields to snapshot (enabled, vault_address, role_id, secret_id, mount_path, namespace, provider_type)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `VaultService._consecutive_renewal_failures: int` (line ~41) — backing field for the new `renewal_failures` property
- `VaultService.status()` — pattern reference for a simple async accessor; `renewal_failures` follows same style but as sync `@property`
- `VaultConfig` ORM model in `db.py` — defines all 9 fields; snapshot only the 7 operational ones
- `system_router.py` — already has no-auth endpoints (`/system/health`) and auth-required endpoints; verification-key is no-auth, docs are auth-required (consistent pattern)

### Established Patterns
- EE router imports: `vault_router.py` currently imports `VaultService` inline (lazy import). `VaultConfigSnapshot` should be importable at top-level since it has no circular dependencies.
- All routers use `router = APIRouter()` with no prefix; full path comes from the route decorator (consistent with existing style)
- Retention routes already require `users:write` permission — keep that guard when migrating

### Integration Points
- `main.py` currently registers all 4 route groups via `@app.get`/`@app.post` directly. After migration, routes are auto-registered via `app.include_router()` which is already called for all target routers (admin, jobs, system).
- No test files reference the removed `main.py` direct route functions by name — they call the HTTP endpoints, so migration is transparent to tests.

</code_context>

<specifics>
## Specific Ideas

No specific references beyond the PR #24 review findings and the codebase analysis above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 170-pr-review-fix-code-hygiene-and-resource-safety*
*Context gathered: 2026-04-18*
