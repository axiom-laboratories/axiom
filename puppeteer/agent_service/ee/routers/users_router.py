"""EE Router: User management and RBAC."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select

from ...db import get_db, AsyncSession, User, RolePermission
from ...deps import require_permission, audit
from ...auth import get_password_hash
from ...models import UserCreate, UserResponse, PermissionGrant

users_router = APIRouter()


@users_router.get("/admin/users", response_model=List[UserResponse], tags=["User Management"])
async def list_users(current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.username, "username": u.username, "role": u.role, "created_at": u.created_at} for u in users]


@users_router.post("/admin/users", response_model=UserResponse, status_code=201, tags=["User Management"])
async def create_user(req: UserCreate, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")
    new_user = User(username=req.username, password_hash=get_password_hash(req.password), role=req.role)
    db.add(new_user)
    audit(db, current_user, "user:create", req.username, {"role": req.role})
    await db.commit()
    return {"id": new_user.username, "username": new_user.username, "role": new_user.role, "created_at": new_user.created_at}


@users_router.delete("/admin/users/{username}", tags=["User Management"])
async def delete_user(username: str, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    audit(db, current_user, "user:delete", username)
    await db.delete(user)
    await db.commit()
    return {"status": "deleted", "username": username}


@users_router.patch("/admin/users/{username}", response_model=UserResponse, tags=["User Management"])
async def update_user_role(username: str, req: dict, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if "role" in req:
        user.role = req["role"]
    audit(db, current_user, "user:role_change", username, {"role": req.get("role")})
    await db.commit()
    return {"id": user.username, "username": user.username, "role": user.role, "created_at": user.created_at}


# --- Role Permission Management ---

@users_router.get("/admin/roles/{role}/permissions", tags=["User Management"])
async def list_role_permissions(role: str, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role))
    perms = result.scalars().all()
    return [{"id": p.id, "role": p.role, "permission": p.permission} for p in perms]


@users_router.post("/admin/roles/{role}/permissions", status_code=201, tags=["User Management"])
async def grant_role_permission(role: str, req: PermissionGrant, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role, RolePermission.permission == req.permission))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Permission already granted")
    db.add(RolePermission(role=role, permission=req.permission))
    audit(db, current_user, "permission:grant", role, {"permission": req.permission})
    await db.commit()
    return {"status": "granted", "role": role, "permission": req.permission}


@users_router.delete("/admin/roles/{role}/permissions/{permission}", tags=["User Management"])
async def revoke_role_permission(role: str, permission: str, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role, RolePermission.permission == permission))
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    audit(db, current_user, "permission:revoke", role, {"permission": permission})
    await db.delete(perm)
    await db.commit()
    return {"status": "revoked", "role": role, "permission": permission}


@users_router.patch("/admin/users/{username}/reset-password", tags=["User Management"])
async def admin_reset_password(username: str, req: dict, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    """Admin sets a new password for any user."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_password = req.get("password", "").strip()
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user.password_hash = get_password_hash(new_password)
    user.token_version = (user.token_version or 0) + 1  # invalidate all existing sessions
    audit(db, current_user, "user:password_reset", detail={"target": username, "by": current_user.username})
    await db.commit()
    return {"status": "ok"}


@users_router.patch("/admin/users/{username}/force-password-change", tags=["User Management"])
async def admin_force_password_change(username: str, req: dict, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    """Set or clear the must_change_password flag for a user."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    enabled = bool(req.get("enabled", True))
    user.must_change_password = enabled
    action = "user:force_password_change_set" if enabled else "user:force_password_change_cleared"
    audit(db, current_user, action, detail={"target": username})
    await db.commit()
    return {"status": "ok", "must_change_password": enabled}
