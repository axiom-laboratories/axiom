"""SIEM CE stub router — returns 402 Unavailable for all endpoints.

In CE mode, all SIEM endpoints return HTTP 402 (Payment Required) as per
the HTTP specification for "feature requires paid/enterprise edition".
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/admin/siem", tags=["SIEM Configuration"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "SIEM integration requires Enterprise Edition"}
)


@router.get("/config")
async def get_config_ce():
    """Get SIEM configuration (EE only)."""
    return _EE_RESPONSE


@router.patch("/config")
async def update_config_ce():
    """Update SIEM configuration (EE only)."""
    return _EE_RESPONSE


@router.post("/test-connection")
async def test_connection_ce():
    """Test SIEM connection (EE only)."""
    return _EE_RESPONSE


@router.get("/status")
async def get_status_ce():
    """Get SIEM service status (EE only)."""
    return _EE_RESPONSE
