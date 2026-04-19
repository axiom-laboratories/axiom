"""
Shared FastAPI dependencies used by both main.py and EE routers.

Moved here to avoid circular imports between main.py and ee/routers/*.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.future import select

from .db import get_db, AsyncSession, User
from .security import oauth2_scheme
from .auth import verify_password


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """JWT auth only (CE mode). EE plugin extends this with API key / SP token branches."""
    from jose import jwt, JWTError
    from .auth import SECRET_KEY, ALGORITHM
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    # Regular user JWT
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    # Reject tokens issued before a password change (token_version mismatch)
    if payload.get("tv", 0) != user.token_version:
        raise credentials_exception
    return user


# CE alias — all CE routes use this (no RBAC, just authentication)
require_auth = get_current_user


async def get_current_user_optional(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Optional JWT User Auth."""
    if not token:
        return None

    from jose import jwt, JWTError
    from .auth import SECRET_KEY, ALGORITHM

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# EE-only helpers — kept here so ee/routers/* can import them without
# circular-import issues.  In CE mode these are never called because
# the EE routes return 402 stubs.
# ---------------------------------------------------------------------------

_perm_cache: dict[str, set[str]] = {}


def _invalidate_perm_cache(role: str | None = None) -> None:
    """Clear cached permissions for a role (or all roles)."""
    if role:
        _perm_cache.pop(role, None)
    else:
        _perm_cache.clear()


def require_ee():
    """Dependency factory that enforces EE licence requirement.
    Raises HTTP 403 if EE is not active (CE mode or expired licence).
    Phase 167 - EE gating for Vault integration.

    Usage in route:
        async def some_route(current_user = Depends(require_ee()), request: Request = None):
    """
    async def _check(current_user = Depends(get_current_user), request: Request = None) -> User:
        # Check if EE licence is active via app state
        if request is None:
            raise HTTPException(
                status_code=403,
                detail="EE licence required for this feature"
            )

        licence_state = getattr(request.app.state, 'licence_state', None)
        if licence_state is None or not licence_state.is_ee_active:
            raise HTTPException(
                status_code=403,
                detail="EE licence required for this feature"
            )

        return current_user
    return _check


def require_permission(perm: str):
    """Dependency factory that enforces a named permission via DB-backed RBAC.
    Used by EE routers only — CE routes use require_auth instead."""
    async def _check(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        # EE tables (RolePermission) must exist for this to work.
        # In CE mode this code path is never reached.
        if getattr(current_user, 'role', None) == "admin":
            return current_user
        from .db import Base
        RolePermission = Base.metadata.tables.get("role_permissions")
        if RolePermission is None:
            # CE mode — no RBAC table, just authenticate
            return current_user
        if getattr(current_user, 'role', 'viewer') not in _perm_cache:
            from sqlalchemy import select as sa_select, text
            result = await db.execute(
                sa_select(text("permission")).select_from(text("role_permissions")).where(
                    text(f"role = :role")
                ), {"role": current_user.role}
            )
            _perm_cache[current_user.role] = {row[0] for row in result.all()}
        if perm not in _perm_cache.get(getattr(current_user, 'role', 'viewer'), set()):
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
        return current_user
    return _check


def audit(db: AsyncSession, user, action: str, resource_id: str = None, detail: dict = None):
    """Append an audit entry. No-op in CE (table absent — exception swallowed).
    Works in EE regardless of which SQLAlchemy metadata AuditLog is registered in.

    Intentionally sync so callers don't need await. The DB write is scheduled as
    a background task on the running event loop so the coroutine is properly awaited.
    Also enqueues to SIEM service if enabled (fire-and-forget, never blocks).
    Per Phase 168 — D-03, D-09.
    """
    import asyncio

    async def _insert():
        try:
            from sqlalchemy import text
            await db.execute(
                text("INSERT INTO audit_log (username, action, resource_id, detail) VALUES (:u, :a, :r, :d)"),
                {"u": user.username, "a": action, "r": resource_id, "d": json.dumps(detail) if detail else None}
            )
        except Exception:
            # In CE mode the table doesn't exist — silently ignore.
            pass

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_insert())
    except RuntimeError:
        # Called outside async context
        pass

    # Fire-and-forget SIEM enqueue (Phase 168 — D-03, D-09)
    try:
        from ee.services.siem_service import get_siem_service

        siem = get_siem_service()
        if siem:
            event = {
                "username": user.username,
                "action": action,
                "resource_id": resource_id,
                "detail": detail,
                "timestamp": datetime.utcnow().isoformat(),
            }
            siem.enqueue(event)
    except Exception:
        # Never block audit path due to SIEM errors (D-03)
        pass
