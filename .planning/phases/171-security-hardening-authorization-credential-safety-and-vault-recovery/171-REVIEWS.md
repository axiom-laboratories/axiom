---
phase: 171
reviewers: [gemini]
reviewed_at: 2026-04-19T00:00:00Z
plans_reviewed:
  - 171-01-PLAN.md
  - 171-02-PLAN.md
  - 171-03-PLAN.md
  - 171-04-PLAN.md
---

# Cross-AI Plan Review — Phase 171

## Gemini Review

# Phase 171: Security Hardening — Review Report

This review covers the four-part implementation plan for **Phase 171: Authorization, Credential Safety, and Vault Recovery**.

---

## 1. Summary Assessment
The proposed plans represent a significant maturation of the Axiom security posture. By shifting from a binary "authenticated/unauthenticated" model to granular RBAC, the project addresses a critical architectural debt. The Vault hardening strategy—specifically the move toward a multi-provider model and the "stuck-degraded" recovery loop—robustly handles common failures in distributed secret management. Overall, the plans are well-sequenced, though the reliance on manual YAML parameter validation over structured serialization represents a minor but manageable risk.

---

## 2. Strengths
*   **Granular RBAC transition:** Moving 26 endpoints to specific permission checks significantly reduces the blast radius of a compromised operator or viewer account.
*   **Stateless Permission Logic:** Removing the `_perm_cache` in Plan 04 is a proactive "win" for horizontal scalability, preventing race conditions and stale cache issues across multi-worker FastAPI deployments.
*   **Resilient Vault Lifecycle:** The `VaultConfigSnapshot` frozen dataclass is an excellent design choice to prevent `DetachedInstanceError`, which is a frequent pain point in long-running background tasks using SQLAlchemy.
*   **Self-Healing Infrastructure:** The auto-retry logic in `renew()` directly addresses "degraded state" deadlocks without requiring manual administrative intervention.
*   **Leak Prevention:** Adding the `finally` block for WebSocket disconnection ensures resource exhaustion is mitigated even during unexpected connection drops or server-side errors.

---

## 3. Concerns

| Severity | Topic | Description |
| :--- | :--- | :--- |
| **MEDIUM** | **YAML Injection Approach** | **Plan 02** uses a regex-based "deny-list" to prevent YAML injection. While effective for simple parameters, f-string interpolation for config generation is inherently more fragile than using `yaml.safe_dump()`. If a new parameter is added later and validation is forgotten, the vector re-opens. |
| **MEDIUM** | **Migration Strategy** | The plan mentions seeding permissions in `db.py`. Since the project explicitly avoids Alembic, there is a risk that existing production databases won't receive these new permissions automatically unless a manual SQL migration script is provided (similar to the Vault migrations mentioned in the context). |
| **LOW** | **Signature Permissions** | Requiring `signatures:write` for `GET /signatures` (Plan 01) is highly restrictive. While the rationale that "key management is privileged" holds, it prevents an "Auditor" role (Viewer) from even verifying that security policies are active. |
| **LOW** | **Vault Exception Scope** | **Plan 03** specifies catching "network errors" in `resolve()`. This needs to be explicitly mapped to `requests.exceptions.RequestException` or the underlying library's equivalent to avoid accidentally catching (and silencing) logic errors or `KeyboardInterrupt`. |

---

## 4. Suggestions

*   **Refactor Compose Generation:** In **Plan 02**, instead of f-string interpolation + regex validation, consider building a dictionary of the compose structure and using `yaml.safe_dump()`. This eliminates the injection class entirely without needing to maintain a list of "unsafe" characters.
*   **Explicit Migration Script:** Create a `migration_v24_permissions.sql` file (following the pattern of earlier migrations) to ensure that `nodes:read` and `system:read` are added to existing roles in environments where the DB is already initialized.
*   **Differentiate Signature Permissions:** Consider adding `signatures:read` for the `GET` endpoint. This allows Viewers to see the *fingerprints* or *existence* of keys without granting the ability to upload or delete them.
*   **Health Check Integration:** In **Plan 03**, expose the `renewal_failures` count to the system health/status endpoint. This allows external monitoring tools (Prometheus/Grafana) to alert on Vault degradation before the "auto-recovery" is even needed.

---

## 5. Risk Assessment

**Overall Risk Level: LOW**

### Justification:
The plans are surgically focused and address well-understood security patterns.
*   **Plan 04** is the only "high-impact" operational change due to the removal of the permission cache, but the trade-off for architectural simplicity and multi-process compatibility is worth the testing effort.
*   The **Vault CRUD** changes are EE-gated and additive, meaning they are unlikely to break core OSS functionality.
*   The dependency ordering (Plan 01 before Plan 04) is correctly identified, ensuring that tests are updated in the correct sequence.

**Verdict:** Proceed with implementation, prioritizing the migration script and considering the transition to structured YAML dumping for the compose generator.

---

## Consensus Summary

Only one reviewer (Gemini) — no multi-reviewer consensus required.

### Agreed Strengths
- VaultConfigSnapshot frozen dataclass prevents DetachedInstanceError
- Permission cache removal is the right call for multi-worker safety
- Auto re-auth recovery in `renew()` elegantly avoids new API surface
- WebSocket try/finally is a clear and correct resource safety fix
- Wave ordering (Plan 01 before Plan 04) correctly sequences dependencies

### Top Concerns
1. **MEDIUM — YAML injection via f-string** (Plan 02): deny-list regex is fragile; new params added later could bypass if validation is forgotten. Gemini suggests `yaml.safe_dump()` as the structurally safer approach — worth considering but CONTEXT.md already chose validation for formatting reasons.
2. **MEDIUM — Migration script missing** (Plan 01): `nodes:read`/`system:read` seeding via `db.py` only works on fresh deployments. Existing prod DBs need an explicit `migration_v24_permissions.sql` — this gap should be addressed in execution.
3. **LOW — GET /signatures requires signatures:write** (Plan 01): locks out Viewers from auditing key existence. Consider `signatures:read` if an auditor use case emerges.
4. **LOW — Vault network error scope** (Plan 03): `ConnectionError/TimeoutError/OSError` is correct for Python stdlib; verify `hvac` doesn't wrap these further.

### Action Items for Execution
- [ ] Add `migration_v24_permissions.sql` covering the new `nodes:read`/`system:read` permission rows (Plan 01)
- [ ] Consider whether `GET /signatures` should use `signatures:read` vs `signatures:write` (current plan uses write-gate)
- [ ] Verify `hvac` network exception hierarchy against the chosen exception list in Plan 03
