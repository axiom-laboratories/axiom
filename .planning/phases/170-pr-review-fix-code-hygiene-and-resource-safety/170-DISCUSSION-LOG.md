# Phase 170: PR Review Fix — Code Hygiene and Resource Safety - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 170-pr-review-fix-code-hygiene-and-resource-safety
**Areas discussed:** Route destinations, Frozen dataclass design

---

## Gray Areas Presented

| Area | Description | Selected |
|------|-------------|----------|
| Route destinations | Retention→admin_router and job-defs→jobs_router are obvious; docs and verification-key less clear; docs path calculation shifts when moved to routers/ | |
| Frozen dataclass design | VaultService stores ORM object directly; background renewal can raise DetachedInstanceError after session closes; design choice on snapshot interface | |
| You decide both | All four fixes are mechanical LOW issues — delegate both to Claude | ✓ |

**User's choice:** "You decide both" — full discretion delegated to Claude for Fix 3 route destinations and Fix 4 frozen dataclass design.

---

## Claude's Discretion — Route Destinations

- `retention` → `admin_router.py` (admin-gated at `/api/admin/retention`, consistent with existing admin endpoints)
- `job-definitions alias` → `jobs_router.py` (alias to canonical `/jobs/definitions` already there)
- `verification-key` → `system_router.py` (tagged "System", unauthenticated utility endpoint — matches existing system health/licence endpoints)
- `docs` → `system_router.py` (tagged "System", auth-required utility — consistent with `/api/features` and `/api/licence` already there)
- Path fix: docs routes use `__file__`-relative resolution; moved from `agent_service/` to `agent_service/routers/` requires one extra `dirname()` level

## Claude's Discretion — Frozen Dataclass Design

- `VaultConfigSnapshot(frozen=True)` defined in `vault_service.py` alongside its consumer
- Fields: enabled, vault_address, role_id, secret_id, mount_path, namespace, provider_type (operational fields only; id/timestamps excluded)
- `VaultService.__init__` keeps `Optional[VaultConfig]` signature; snapshots internally at init time
- Reinit in `vault_router.py`: `vault_service.config = VaultConfigSnapshot.from_orm(vault_config)` (explicit conversion at call site)

## Deferred Ideas

None.
