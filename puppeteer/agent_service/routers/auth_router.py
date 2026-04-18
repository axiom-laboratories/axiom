"""
Authentication domain router: device auth, JWT token, password management.

Endpoints:
- POST /auth/device - RFC 8628 device authorization request
- POST /auth/device/token - RFC 8628 device access token exchange
- GET /auth/device/approve - Device approval page
- POST /auth/device/approve - Process device approval
- POST /auth/device/deny - Process device denial
- POST /auth/login - Standard JWT login
- GET /auth/me - Get current user profile
- PATCH /auth/me - Update current user (password change)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional
import logging
import html as _html
import secrets as _secrets
from datetime import datetime, timedelta, UTC

from ..db import get_db, AsyncSession, User
from ..deps import get_current_user, get_current_user_optional, audit
from ..models import TokenResponse, DeviceCodeResponse, UserResponse
from ..auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_token
from ..security import oauth2_scheme
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Device authorization flow state (RFC 8628)
_device_codes: dict[str, dict] = {}
_user_code_index: dict[str, str] = {}  # user_code -> device_code (reverse index)
_USER_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # excludes 0,O,1,I,L
_DEVICE_TTL_SECONDS = 300   # 5 minutes
_POLL_INTERVAL_SECONDS = 5


def _generate_user_code() -> str:
    """Generate a user-readable code for RFC 8628 device flow (format: XXXX-XXXX)."""
    p1 = "".join(_secrets.choice(_USER_CODE_ALPHABET) for _ in range(4))
    p2 = "".join(_secrets.choice(_USER_CODE_ALPHABET) for _ in range(4))
    return f"{p1}-{p2}"


@router.post("/auth/device", response_model=DeviceCodeResponse, tags=["Authentication"])
async def device_authorization():
    """RFC 8628 Device Authorization Request — issues device_code and user_code."""
    now = datetime.utcnow()
    # Lazy cleanup: evict expired entries (2x TTL = 10 min grace)
    expired_keys = [k for k, v in list(_device_codes.items()) if v["expiry"] < now]
    for k in expired_keys:
        uc = _device_codes.pop(k, {}).get("user_code")
        if uc:
            _user_code_index.pop(uc, None)

    device_code = _secrets.token_urlsafe(32)
    user_code = _generate_user_code()
    expiry = now + timedelta(seconds=_DEVICE_TTL_SECONDS)

    _device_codes[device_code] = {
        "user_code": user_code,
        "expiry": expiry,
        "status": "pending",
        "approved_by": None,
        "last_poll": None,
    }
    _user_code_index[user_code] = device_code

    import os
    agent_url = os.getenv("AGENT_URL", "https://localhost:8001")
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": f"{agent_url}/auth/device/approve",
        "verification_uri_complete": f"{agent_url}/auth/device/approve?user_code={user_code}",
        "expires_in": _DEVICE_TTL_SECONDS,
        "interval": _POLL_INTERVAL_SECONDS,
    }


class DeviceTokenRequest(BaseModel):
    device_code: str
    grant_type: str = "urn:ietf:params:oauth:grant-type:device_code"


@router.post("/auth/device/token", response_model=TokenResponse, tags=["Authentication"])
async def device_token_exchange(req: DeviceTokenRequest, db: AsyncSession = Depends(get_db)):
    """RFC 8628 Device Access Token Request — exchange device_code for JWT."""
    entry = _device_codes.get(req.device_code)
    now = datetime.utcnow()

    if not entry:
        raise HTTPException(400, detail={"error": "expired_token"})
    if entry["expiry"] < now:
        uc = _device_codes.pop(req.device_code, {}).get("user_code")
        if uc:
            _user_code_index.pop(uc, None)
        raise HTTPException(400, detail={"error": "expired_token"})
    if entry["status"] == "denied":
        raise HTTPException(400, detail={"error": "access_denied"})

    # RFC 8628 slow_down: if polled again before interval
    last_poll = entry.get("last_poll")
    if last_poll and (now - last_poll).total_seconds() < _POLL_INTERVAL_SECONDS:
        entry["last_poll"] = now
        raise HTTPException(400, detail={"error": "slow_down"})
    entry["last_poll"] = now

    if entry["status"] == "pending":
        raise HTTPException(400, detail={"error": "authorization_pending"})

    # status == "approved"
    username = entry["approved_by"]
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, detail={"error": "access_denied"})

    token = create_access_token(
        data={"sub": user.username, "tv": user.token_version, "type": "device_flow"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # Consume code — one-time use
    _device_codes.pop(req.device_code, None)
    _user_code_index.pop(entry["user_code"], None)

    audit(db, user, "device_flow:token_issued", None, {"username": user.username})
    await db.commit()
    return TokenResponse(access_token=token, token_type="bearer", must_change_password=user.must_change_password)


@router.get("/auth/device/approve", response_class=HTMLResponse, tags=["Authentication"])
async def device_approve_page(user_code: str = ""):
    """Serve the device authorization approval page (inline HTML, no build step)."""
    # SEC-01: escape user_code before inserting into HTML to prevent XSS
    escaped_code = _html.escape(user_code or "")
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Authorize Device — Master of Puppets</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 80px auto; padding: 0 1rem; color: #1a1a1a; }}
    .card {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 2rem; text-align: center; }}
    .code {{ font-family: monospace; font-size: 2rem; font-weight: bold; letter-spacing: 0.2em; color: #0d6efd; margin: 1rem 0; }}
    .btn {{ display: inline-block; padding: 0.6rem 1.6rem; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; margin: 0.3rem; }}
    .btn-approve {{ background: #198754; color: white; }}
    .btn-deny {{ background: #dc3545; color: white; }}
    .btn-approve:hover {{ background: #157347; }}
    .btn-deny:hover {{ background: #bb2d3b; }}
    .msg {{ margin-top: 1rem; font-size: 0.9rem; color: #6c757d; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>Authorize Device</h2>
    <p>A CLI device is requesting access to <strong>Master of Puppets</strong>.</p>
    <p>Confirm that your terminal displays this code:</p>
    <div class="code" id="display-code">{escaped_code or "(no code provided)"}</div>
    <form id="approve-form" method="POST" action="/auth/device/approve">
      <input type="hidden" name="user_code" value="{escaped_code}">
      <input type="hidden" name="token" id="token-field" value="">
      <button type="submit" class="btn btn-approve">Approve</button>
    </form>
    <form id="deny-form" method="POST" action="/auth/device/deny">
      <input type="hidden" name="user_code" value="{escaped_code}">
      <input type="hidden" name="token" id="deny-token-field" value="">
      <button type="submit" class="btn btn-deny">Deny</button>
    </form>
    <p class="msg" id="auth-msg"></p>
  </div>
  <script>
    document.addEventListener('DOMContentLoaded', function() {{
      var token = localStorage.getItem('access_token') || '';
      document.getElementById('token-field').value = token;
      document.getElementById('deny-token-field').value = token;
      if (!token) {{
        document.getElementById('auth-msg').textContent = 'You must be logged in to authorize a device.';
        document.getElementById('auth-msg').style.color = '#dc3545';
        var next = encodeURIComponent(window.location.href);
        setTimeout(function() {{ window.location.href = '/login?next=' + next; }}, 2000);
      }}
    }});
  </script>
</body>
</html>""")


@router.post("/auth/device/approve", response_class=HTMLResponse, tags=["Authentication"])
async def device_approve_submit(
    user_code: str = Form(...),
    token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Process device approval — sets status='approved' on matching device code."""
    # Validate the user's JWT from the form
    try:
        payload = verify_token(token)
        username = payload.get("sub")
    except Exception:
        return HTMLResponse(content="<h2>Error: Invalid or missing session token. Please log in and try again.</h2>", status_code=401)

    device_code = _user_code_index.get(user_code)
    if not device_code or device_code not in _device_codes:
        return HTMLResponse(content="<h2>Error: Device code not found or expired.</h2>", status_code=404)

    entry = _device_codes[device_code]
    if entry["expiry"] < datetime.utcnow():
        return HTMLResponse(content="<h2>Error: Device code has expired.</h2>", status_code=410)

    entry["status"] = "approved"
    entry["approved_by"] = username

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        audit(db, user, "device_flow:approved", None, {"user_code": user_code})
        await db.commit()

    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>Authorized</title>
<style>body{font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center;}</style>
</head><body><h2 style="color:#198754">Device authorized.</h2>
<p>You may close this tab. Your CLI session is now active.</p></body></html>""")


@router.post("/auth/device/deny", response_class=HTMLResponse, tags=["Authentication"])
async def device_deny_submit(
    user_code: str = Form(...),
    token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Process device denial — sets status='denied' on matching device code."""
    try:
        payload = verify_token(token)
        username = payload.get("sub")
    except Exception:
        username = "unknown"

    device_code = _user_code_index.get(user_code)
    if device_code and device_code in _device_codes:
        _device_codes[device_code]["status"] = "denied"

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        audit(db, user, "device_flow:denied", None, {"user_code": user_code})
        await db.commit()

    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>Denied</title>
<style>body{font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center;}</style>
</head><body><h2 style="color:#dc3545">Device authorization denied.</h2>
<p>The CLI request has been rejected. You may close this tab.</p></body></html>""")


@router.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Standard JWT login with username/password."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "tv": user.token_version, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "must_change_password": user.must_change_password}


@router.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(id=current_user.username, username=current_user.username, role=current_user.role, created_at=current_user.created_at)


@router.patch("/auth/me", response_model=TokenResponse, tags=["Authentication"])
async def update_self(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Allow a logged-in user to change their own password.
    Returns a fresh access token so the current session continues uninterrupted."""
    new_password = req.get("password", "").strip()
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    # Skip current_password check only when user is in force-change mode (they just authenticated)
    if not current_user.must_change_password:
        current_password = req.get("current_password", "")
        if not current_password or not verify_password(current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = get_password_hash(new_password)
    current_user.must_change_password = False
    current_user.token_version = (current_user.token_version or 0) + 1
    audit(db, current_user, "user:password_changed", detail={"username": current_user.username})
    await db.commit()
    # Issue a new token for the current session (old tokens for other sessions are now invalid)
    new_token = create_access_token(
        data={"sub": current_user.username, "tv": current_user.token_version, "role": current_user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return TokenResponse(access_token=new_token, token_type="bearer", must_change_password=False)
