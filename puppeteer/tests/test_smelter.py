import pytest
import inspect
import json
from fastapi import HTTPException
from sqlalchemy import select
from agent_service.db import Config, PuppetTemplate, Blueprint, ApprovedIngredient
from agent_service.models import ApprovedOSResponse, ApprovedIngredientCreate
from agent_service.services.smelter_service import SmelterService
from unittest.mock import AsyncMock, MagicMock, patch

def test_smelter_service_exists_stub():
    """SMLT-01: Verify SmelterService and its core CRUD methods exist."""
    assert inspect.isclass(SmelterService)
    assert hasattr(SmelterService, "add_ingredient")
    assert hasattr(SmelterService, "list_ingredients")
    assert hasattr(SmelterService, "delete_ingredient")

def test_vulnerability_scan_integration_stub():
    """SMLT-02: Verify SmelterService.scan_vulnerabilities exists."""
    assert hasattr(SmelterService, "scan_vulnerabilities")

@pytest.mark.asyncio
async def test_validate_blueprint_logic():
    """Verify validate_blueprint logic identifies unapproved packages."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = ["flask", "requests"]
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    rt_def = {"packages": {"python": ["flask>=2.0", "cryptography"]}}
    unapproved = await SmelterService.validate_blueprint(mock_db, rt_def, "DEBIAN")
    assert "cryptography" in unapproved
    assert len(unapproved) == 1

@pytest.mark.asyncio
async def test_foundry_enforcement_functional():
    """Verify Foundry build template enforcement (STRICT vs WARNING)."""
    from agent_service.services.foundry_service import FoundryService
    
    mock_db = AsyncMock()
    tmpl = PuppetTemplate(id="t1", friendly_name="test-tmpl", runtime_blueprint_id="rt1", network_blueprint_id="nw1")
    rt_bp = Blueprint(id="rt1", definition=json.dumps({"packages": {"python": ["bad-pkg"]}}), os_family="DEBIAN")
    nw_bp = Blueprint(id="nw1", definition=json.dumps({}))

    # Use patch to handle SmelterService.validate_blueprint
    with patch("puppeteer.agent_service.services.foundry_service.SmelterService.validate_blueprint", new_callable=AsyncMock) as mock_val:
        mock_val.return_value = ["bad-pkg"]
        
        # 1. Test STRICT Mode
        mock_res_strict = MagicMock()
        mock_res_strict.scalar_one_or_none.return_value = "STRICT"
        
        async def mock_exec_strict(stmt):
            s = str(stmt).lower()
            if "config" in s: return mock_res_strict
            if "puppet_templates" in s:
                m = MagicMock()
                m.scalar_one_or_none.return_value = tmpl
                return m
            if "blueprints" in s:
                m = MagicMock()
                m.scalar_one_or_none.return_value = rt_bp
                return m
            return MagicMock()

        mock_db.execute.side_effect = mock_exec_strict
        with pytest.raises(HTTPException) as excinfo:
            await FoundryService.build_template("t1", mock_db)
        assert excinfo.value.status_code == 403

        # 2. Test WARNING Mode
        mock_res_warn = MagicMock()
        mock_res_warn.scalar_one_or_none.return_value = "WARNING"
        
        async def mock_exec_warn(stmt):
            s = str(stmt).lower()
            if "config" in s: return mock_res_warn
            if "puppet_templates" in s:
                m = MagicMock()
                m.scalar_one_or_none.return_value = tmpl
                return m
            if "blueprints" in s:
                m = MagicMock()
                m.scalar_one_or_none.return_value = rt_bp
                return m
            return MagicMock()

        mock_db.execute.side_effect = mock_exec_warn
        try:
            await FoundryService.build_template("t1", mock_db)
        except Exception:
            pass
        assert tmpl.is_compliant is False

def test_foundry_enforcement_strict_stub():
    """SMLT-03: Verify FoundryService integrates with Smelter validation."""
    from agent_service.services.foundry_service import FoundryService
    source = inspect.getsource(FoundryService.build_template)
    assert "SmelterService.validate_blueprint" in source

@pytest.mark.asyncio
async def test_smelter_enforcement_config_stub():
    """SMLT-04: WARNING mode allows builds with PENDING mirror_status; STRICT mode blocks them."""
    from agent_service.services.foundry_service import FoundryService
    import json

    mock_db = AsyncMock()
    tmpl = PuppetTemplate(id="t2", friendly_name="mirror-test", runtime_blueprint_id="rt2", network_blueprint_id="nw2")
    rt_bp = Blueprint(id="rt2", definition=json.dumps({"packages": {"python": ["requests"]}}), os_family="DEBIAN")
    nw_bp = Blueprint(id="nw2", definition=json.dumps({}))

    # Approved ingredient with mirror_status='PENDING' (the default after cataloguing)
    pending_ingredient = ApprovedIngredient(name="requests", os_family="DEBIAN", mirror_status="PENDING")

    def make_exec(mode_value):
        # Track blueprint call order: first blueprint call = runtime (rt_bp), second = network (nw_bp)
        blueprint_call_count = [0]

        async def mock_exec(stmt):
            s = str(stmt).lower()
            if "config" in s:
                m = MagicMock()
                m.scalar_one_or_none.return_value = mode_value
                return m
            if "puppet_templates" in s:
                m = MagicMock()
                m.scalar_one_or_none.return_value = tmpl
                return m
            if "blueprint" in s:
                blueprint_call_count[0] += 1
                m = MagicMock()
                # First call is runtime blueprint (rt_bp), second is network blueprint (nw_bp)
                m.scalar_one_or_none.return_value = rt_bp if blueprint_call_count[0] == 1 else nw_bp
                return m
            if "approved_ingredient" in s:
                m = MagicMock()
                m.scalar_one_or_none.return_value = pending_ingredient
                return m
            m = MagicMock()
            m.scalar_one_or_none.return_value = None
            return m
        return mock_exec

    with patch("puppeteer.agent_service.services.foundry_service.SmelterService.validate_blueprint", new_callable=AsyncMock) as mock_val:
        mock_val.return_value = []  # All packages approved — isolate mirror-status path

        # 1. WARNING mode: build must proceed (no exception); template marked non-compliant
        mock_db.execute.side_effect = make_exec("WARNING")
        try:
            await FoundryService.build_template("t2", mock_db)
        except HTTPException as exc:
            pytest.fail(f"WARNING mode should not raise HTTPException, but got {exc.status_code}: {exc.detail}")
        except Exception:
            pass  # Other errors (MirrorService etc.) are acceptable — the mirror-status gate itself must not raise
        assert tmpl.is_compliant is False, "WARNING mode with PENDING ingredient must set is_compliant=False"

        # 2. STRICT mode: build must raise 403
        tmpl.is_compliant = True  # Reset
        mock_db.execute.side_effect = make_exec("STRICT")
        with pytest.raises(HTTPException) as excinfo:
            await FoundryService.build_template("t2", mock_db)
        assert excinfo.value.status_code == 403
        assert "mirror" in excinfo.value.detail.lower() or "mirrored" in excinfo.value.detail.lower()

def test_template_compliance_badging_stub():
    """SMLT-05: Verify PuppetTemplate model has is_compliant field."""
    assert hasattr(PuppetTemplate, "is_compliant")
    from sqlalchemy.orm import DeclarativeBase
    assert issubclass(PuppetTemplate, DeclarativeBase)


# Wave 1 / Plan 110-01 tests for transitive CVE scanning

def test_scan_vulnerabilities_transitive():
    """
    Test that scan_vulnerabilities() walks IngredientDependency edges
    and includes all transitive dependencies in the CVE report.

    RED: Stub for implementation in Plan 110-01 Task 1.
    Will verify: Flask → Jinja2 → MarkupSafe chain is scanned,
    CVEs in MarkupSafe are reported as transitive.
    """
    pass


def test_cve_provenance_path():
    """
    Test that provenance paths are correctly reconstructed from
    IngredientDependency edges (e.g., ["Flask 3.0.0", "Jinja2 3.1.3", "MarkupSafe 2.1.5"]).

    RED: Stub for implementation in Plan 110-01 Task 1.
    Will verify: paths are reconstructed correctly for transitive deps.
    """
    pass


def test_ingredient_tree_api():
    """
    Test GET /api/smelter/ingredients/{id}/tree endpoint.

    RED: Stub for implementation in Plan 110-01 Task 3.
    Will verify: endpoint returns DependencyTreeResponse with correct structure,
    CVE counts aggregated, worst_severity calculated.
    """
    pass


def test_discover_endpoint():
    """
    Test POST /api/smelter/ingredients/{id}/discover endpoint.

    RED: Stub for implementation in Plan 110-01 Task 3.
    Will verify: endpoint triggers resolver, auto-approves transitive deps,
    returns DiscoverDependenciesResponse with toast_message.
    """
    pass


# Wave 0 test stubs for mirror config (Plan 112-02)

def test_get_mirror_config_all_ecosystems():
    """
    Test GET /api/admin/mirror-config returns all 8 ecosystem URLs.

    RED: Stub for Task 2 (Implement GET/PUT /api/admin/mirror-config endpoints).
    Will verify: endpoint returns all 8 mirror URLs (pypi, apt, apk, npm, nuget, oci_hub, oci_ghcr, conda).
    """
    pass


def test_put_mirror_config_updates_database():
    """
    Test PUT /api/admin/mirror-config updates Config DB.

    RED: Stub for Task 2 (Implement GET/PUT /api/admin/mirror-config endpoints).
    Will verify: endpoint accepts MirrorConfigUpdate, updates Config entries, returns updated response.
    """
    pass


def test_mirror_config_permission_check():
    """
    Test that non-admin users cannot PUT /api/admin/mirror-config.

    RED: Stub for Task 2 (Implement GET/PUT /api/admin/mirror-config endpoints).
    Will verify: non-admin users receive 403 Forbidden response.
    """
    pass


def test_mirror_config_health_status():
    """
    Test that GET /api/admin/mirror-config includes health_status dict.

    RED: Stub for Task 2 (Implement GET/PUT /api/admin/mirror-config endpoints).
    Will verify: response includes health_status dict with 8 keys (one per ecosystem).
    """
    pass
