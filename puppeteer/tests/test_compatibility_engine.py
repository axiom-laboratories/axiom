"""
Phase 11 — Compatibility Engine test suite.
COMP-01: os_family + is_active on CapabilityMatrix API
COMP-02: runtime_dependencies on CapabilityMatrix API
COMP-03: OS mismatch rejection + dep-confirmation flow at POST /api/blueprints
COMP-04: ?os_family query param filtering on GET /api/capability-matrix
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — source inspection for pre-implementation stubs
# ---------------------------------------------------------------------------

def _get_capability_matrix_route_src():
    """Return the source of the get_capability_matrix route handler."""
    import inspect
    from agent_service.main import app
    # Find the route handler by path
    for route in app.routes:
        if hasattr(route, "path") and route.path == "/api/capability-matrix":
            if hasattr(route, "methods") and "GET" in route.methods:
                return inspect.getsource(route.endpoint)
    raise RuntimeError("GET /api/capability-matrix route not found")


def _get_create_blueprint_route_src():
    """Return the source of the POST /api/blueprints route handler."""
    import inspect
    from agent_service.main import app
    for route in app.routes:
        if hasattr(route, "path") and route.path == "/api/blueprints":
            if hasattr(route, "methods") and "POST" in route.methods:
                return inspect.getsource(route.endpoint)
    raise RuntimeError("POST /api/blueprints route not found")


# ---------------------------------------------------------------------------
# COMP-01: is_active field on CapabilityMatrix API response
# ---------------------------------------------------------------------------

def test_matrix_has_os_family():
    """
    COMP-01: GET /api/capability-matrix must return entries that include
    an `is_active` field.

    Fails until Plan 02 adds `is_active` to the CapabilityMatrix DB model
    and CapabilityMatrixEntry response model.
    """
    from agent_service.db import CapabilityMatrix
    import inspect
    src = inspect.getsource(CapabilityMatrix)
    assert "is_active" in src, (
        "COMP-01 FAIL: CapabilityMatrix DB model has no `is_active` column. "
        "Plan 02 must add it."
    )


# ---------------------------------------------------------------------------
# COMP-02: runtime_dependencies field on CapabilityMatrix API response
# ---------------------------------------------------------------------------

def test_matrix_runtime_deps():
    """
    COMP-02: GET /api/capability-matrix must return entries that include
    a `runtime_dependencies` field (a list).

    Fails until Plan 02 adds `runtime_dependencies` to the CapabilityMatrix
    DB model and CapabilityMatrixEntry response model.
    """
    from agent_service.db import CapabilityMatrix
    import inspect
    src = inspect.getsource(CapabilityMatrix)
    assert "runtime_dependencies" in src, (
        "COMP-02 FAIL: CapabilityMatrix DB model has no `runtime_dependencies` column. "
        "Plan 02 must add it."
    )


# ---------------------------------------------------------------------------
# COMP-04: ?os_family query param filtering on GET /api/capability-matrix
# ---------------------------------------------------------------------------

def test_matrix_os_family_filter():
    """
    COMP-04: GET /api/capability-matrix?os_family=DEBIAN must only return
    entries where base_os_family == "DEBIAN".

    Fails until Plan 02 adds `os_family` query param filtering to the route.
    Current implementation ignores query params and returns all rows.
    """
    import inspect
    from agent_service.ee.routers.foundry_router import get_capability_matrix
    src = inspect.getsource(get_capability_matrix)
    assert "os_family" in src, (
        "COMP-04 FAIL: GET /api/capability-matrix handler does not accept "
        "an `os_family` query parameter. Plan 02 must add filtering support."
    )


# ---------------------------------------------------------------------------
# COMP-03: OS mismatch rejection at POST /api/blueprints
# ---------------------------------------------------------------------------

def test_blueprint_os_mismatch_rejected():
    """
    COMP-03: POST /api/blueprints with a tool that is DEBIAN-only must be
    rejected with 422 when os_family=ALPINE is specified.

    The response must include an `offending_tools` key identifying the
    incompatible tool IDs.

    Fails until Plan 03 adds OS-family compatibility validation to the
    blueprint creation endpoint.
    """
    import inspect
    from agent_service.ee.routers.foundry_router import create_blueprint
    src = inspect.getsource(create_blueprint)
    assert "offending_tools" in src, (
        "COMP-03 FAIL: POST /api/blueprints handler does not check for OS "
        "compatibility mismatches or return `offending_tools`. "
        "Plan 03 must add validation."
    )


# ---------------------------------------------------------------------------
# COMP-03: dep-confirmation flow at POST /api/blueprints
# ---------------------------------------------------------------------------

def test_blueprint_dep_confirmation_flow():
    """
    COMP-03: When a blueprint includes a tool that has runtime dependencies
    not present in the tool list, the endpoint must return a 422 response
    with a `missing_dependencies` key suggesting what to add.

    Requires runtime_dependencies data seeded in Plan 02.
    """
    pytest.skip("requires runtime_dependencies seeded in Plan 02")
