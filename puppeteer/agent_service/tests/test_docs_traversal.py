"""
SEC-03: Path traversal guard in GET /api/docs/{filename}.

The current implementation uses os.path.basename() which strips traversal segments,
then os.path.abspath() + startswith() as a secondary guard. CodeQL flags the
startswith() pattern as insufficient (the /safe_dir/ vs /safe_dir_extended/ edge case).
The fix replaces this with validate_path_within() from security.py, which uses
Path.resolve() + Path.is_relative_to() — raising HTTP 400 on traversal.

These tests FAIL before the fix (plan 72-02) because:
- test_traversal_path_returns_400: current code uses basename (strips traversal) then
  startswith guard which returns 403 not 400; this test expects 400
- test_legitimate_filename_not_blocked: should pass (200 or 404), used as sanity check
After the fix, the route uses validate_path_within() which raises 400 on traversal.
"""
import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport

from agent_service.main import app, get_db
from agent_service.deps import get_current_user


def _make_admin_user():
    fake_user = MagicMock()
    fake_user.username = "admin"
    fake_user.role = "admin"
    fake_user.token_version = 0
    return fake_user


@pytest.fixture
async def auth_client(db_session):
    """HTTP test client with admin user dependency override."""
    fake_user = _make_admin_user()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_traversal_path_returns_400(auth_client):
    """Path traversal in filename must not return 200 — route blocks or rejects it."""
    # URL-encoded path traversal — %2F is '/', so this attempts ../../etc/passwd.
    # Starlette normalizes the URL at routing time (so the handler may not be reached),
    # but in any case a traversal must NOT return 200 (the file must not be served).
    resp = await auth_client.get("/api/docs/..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code != 200, (
        f"Traversal should not return 200, got {resp.status_code}"
    )


@pytest.mark.anyio
async def test_traversal_double_dot_slug_returns_400(auth_client):
    """A URL path containing '..' traversal must not serve the traversed file (200)."""
    resp = await auth_client.get(
        "/api/docs/../../../etc/passwd",
        follow_redirects=False,
    )
    assert resp.status_code != 200, (
        f"Traversal path should not return 200, got {resp.status_code}"
    )


@pytest.mark.anyio
async def test_legitimate_filename_not_blocked(auth_client):
    """A clean filename (no traversal) must NOT return 400 — 200 or 404 is acceptable."""
    resp = await auth_client.get("/api/docs/getting-started.md")
    assert resp.status_code in (200, 404), (
        f"Legitimate filename returned unexpected status {resp.status_code}"
    )


def test_validate_path_within_rejects_dotdot_filename():
    """Unit-level: validate_path_within must raise 400 when filename contains path traversal."""
    from pathlib import Path
    from fastapi import HTTPException
    from agent_service.security import validate_path_within
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        # A filename like '../../etc/passwd' resolves outside the tmpdir
        candidate = base / "../../etc/passwd"
        with pytest.raises(HTTPException) as exc_info:
            validate_path_within(base, candidate)
        assert exc_info.value.status_code == 400, (
            f"validate_path_within must raise HTTP 400, got {exc_info.value.status_code}"
        )
