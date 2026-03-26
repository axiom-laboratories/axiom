"""
SEC-01: XSS in GET /auth/device/approve — user_code must be HTML-escaped in output.

These tests FAIL before the fix (plan 72-02) because the current implementation
interpolates user_code directly into the HTML template with no escaping.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from agent_service.main import app


@pytest.mark.anyio
async def test_xss_user_code_escaped_in_display(engine):
    """Raw <script> tag in user_code must NOT appear unescaped in the display div."""
    payload = "<script>alert(1)</script>"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/auth/device/approve", params={"user_code": payload})
    assert resp.status_code == 200
    # The user-supplied payload must not appear verbatim in the response (would execute as script)
    assert payload not in resp.text, "XSS: raw user-supplied <script> payload present unescaped in page"
    assert "&lt;script&gt;" in resp.text, "Expected HTML-escaped &lt;script&gt; in response"


@pytest.mark.anyio
async def test_xss_user_code_escaped_in_hidden_inputs(engine):
    """Attribute-breaking payload in user_code must not appear raw in hidden input value attributes."""
    payload = '"><img src=x onerror=alert(1)>'
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/auth/device/approve", params={"user_code": payload})
    assert resp.status_code == 200
    # The raw payload must not appear unescaped in any attribute value
    assert 'value="' + payload + '"' not in resp.text, (
        "XSS: unescaped attribute-breaking payload found in hidden input value"
    )
