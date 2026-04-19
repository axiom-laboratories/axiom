# Phase 171-04: Remove Permission Cache & Fix WebSocket Resource Leak

**Status**: Completed

**Date**: 2026-04-19

## Objective
Remove in-memory permission cache from deps.py to fix multi-worker race condition; add WebSocket cleanup try/finally to prevent resource leak in system_router; clean up all invalidation call sites.

## Changes Made

### 1. Remove permission cache from deps.py
- **Deleted**: `_perm_cache: dict[str, set[str]] = {}`
- **Deleted**: `_invalidate_perm_cache(role: str | None = None) -> None` function
- **Updated**: `require_permission()` function to always query DB instead of using cached permissions

**Before**:
```python
if getattr(current_user, 'role', 'viewer') not in _perm_cache:
    # ... fetch from DB into cache
    _perm_cache[current_user.role] = {row[0] for row in result.all()}
if perm not in _perm_cache.get(getattr(current_user, 'role', 'viewer'), set()):
    raise HTTPException(...)
```

**After**:
```python
result = await db.execute(
    select(RolePermission).where(
        RolePermission.role == current_user.role,
        RolePermission.permission == perm
    )
)
if not result.scalars().first():
    raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
```

### 2. Remove _invalidate_perm_cache from users_router.py
- **Removed**: Import of `_invalidate_perm_cache` from deps
- **Removed**: Call to `_invalidate_perm_cache(role)` in `grant_role_permission()` (line 80)
- **Removed**: Call to `_invalidate_perm_cache(role)` in `revoke_role_permission()` (line 93)

### 3. Add try/finally to WebSocket handler in system_router.py
**Before**:
```python
try:
    while True:
        data = await ws.receive_text()
        if data == "ping":
            await ws.send_text("pong")
except WebSocketDisconnect:
    ws_manager.disconnect(ws)
```

**After**:
```python
try:
    while True:
        data = await ws.receive_text()
        if data == "ping":
            await ws.send_text("pong")
except WebSocketDisconnect:
    pass
finally:
    ws_manager.disconnect(ws)
```

This ensures `ws_manager.disconnect()` is called on all exit paths (normal disconnect, exception, timeout, etc.), preventing resource leaks.

### 4. Rewrite test_perm_cache.py
- Removed 4 cache-specific tests that tested cache behavior
- Added 4 new tests:
  1. `test_admin_bypasses_permission_check()` — Admin does not hit DB
  2. `test_operator_with_permission_allowed()` — Operator with permission succeeds
  3. `test_viewer_without_permission_denied()` — Viewer without permission fails with 403
  4. `test_require_permission_queries_db_on_every_request()` — Each call queries DB (no caching)

## Test Results

```
agent_service/tests/test_perm_cache.py: 4 passed (100%)
Full suite: 891 passed, 94 failed, 23 skipped, 7 errors
(Failures/errors are pre-existing, unrelated to these changes)
```

## Verification

All requirements verified:
- ✓ `grep -c "_perm_cache" deps.py` returns `0`
- ✓ `grep -c "_invalidate_perm_cache" users_router.py` returns `0`
- ✓ `grep -n "finally:" system_router.py` shows finally block at line 366 (WebSocket handler)
- ✓ All permission tests pass
- ✓ All new tests verify DB-per-request behavior

## Impact

### Fixes
- **Multi-worker race condition**: Removes possibility of stale cache across worker processes
- **WebSocket resource leak**: Guarantees cleanup even on abnormal connection termination

### Performance
- Small increase in DB queries (one per request instead of cache hits)
- Negligible in production (connection pooling + index on `(role, permission)`)
- Trade-off acceptable for correctness and multi-worker safety

## Files Changed
1. `puppeteer/agent_service/deps.py`
2. `puppeteer/agent_service/ee/routers/users_router.py`
3. `puppeteer/agent_service/routers/system_router.py`
4. `puppeteer/agent_service/tests/test_perm_cache.py`

## Related Issues
- Phase 171: Security Hardening (Authorization, Credential Safety, Vault Recovery)
- Addresses DEBT-03 (cached permission pre-warm) by removing cache entirely
