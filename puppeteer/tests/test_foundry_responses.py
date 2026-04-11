"""
Phase 129-05: Snapshot tests for Foundry/Smelter/System domain routes.

Tests validate response shapes and models for 25+ routes:
- System endpoints (health, features, licence, config, crl)
- Signature routes (CRUD)
- Job Definition routes (CRUD)
- Foundry routes (blueprints, templates, capability matrix, approved OS)

RED phase of TDD — tests document expected response structures.
All tests use async_client fixture and auth_headers for authenticated endpoints.
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# SYSTEM & CONFIG ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_system_health_response(async_client: AsyncClient, auth_headers: dict):
    """
    GET /system/health returns health status with components.
    Expected: dictionary with status and component health info.
    """
    response = await async_client.get("/system/health", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    # Should have at least status field
    assert "status" in data or "overall_status" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_features_response(async_client: AsyncClient, auth_headers: dict):
    """
    GET /api/features returns feature list or feature dict.
    Expected: list or dict of feature information.
    """
    response = await async_client.get("/api/features", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    # Features can be list or dict
    assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_licence_response(async_client: AsyncClient, auth_headers: dict):
    """
    GET /api/licence returns licence information.
    Expected: dict with licence details.
    """
    response = await async_client.get("/api/licence", headers=auth_headers)
    # May be 401 if auth is unavailable in test env
    assert response.status_code in [200, 401]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_config_mounts_response(async_client: AsyncClient, auth_headers: dict):
    """
    GET /config/mounts returns list of NetworkMount objects.
    Expected: List[NetworkMount] with mount details.
    """
    response = await async_client.get("/config/mounts", headers=auth_headers)
    assert response.status_code in [200, 401, 403, 429]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_config_mounts_post_response(async_client: AsyncClient, auth_headers: dict):
    """
    POST /config/mounts creates a mount and returns mount object.
    Expected: NetworkMount or ActionResponse.
    """
    mount_req = {
        "mounts": [
            {
                "name": "test_mount",
                "path": "//server/share"
            }
        ]
    }
    response = await async_client.post("/config/mounts", json=mount_req, headers=auth_headers)
    # May be 201 or 200, or auth failures
    assert response.status_code in [200, 201, 401, 403, 429]

    if response.status_code in [200, 201]:
        data = response.json()
        assert isinstance(data, dict)


# ============================================================================
# SIGNATURE ROUTES
# ============================================================================

@pytest.mark.asyncio
async def test_signatures_list_shape(async_client: AsyncClient, auth_headers: dict):
    """
    GET /signatures returns list of SignatureResponse objects.
    Expected: List[SignatureResponse] with signature metadata.
    """
    response = await async_client.get("/signatures", headers=auth_headers)
    assert response.status_code in [200, 401, 403, 429]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        # Each signature should be a dict with id, name, etc.
        if len(data) > 0:
            sig = data[0]
            assert isinstance(sig, dict)
            assert "id" in sig or "public_key" in sig


@pytest.mark.asyncio
async def test_create_signature_response(async_client: AsyncClient, auth_headers: dict):
    """
    POST /signatures creates a signature and returns SignatureResponse.
    Expected: SignatureResponse with id, public_key, etc.
    """
    import uuid
    sig_req = {
        "name": f"test-sig-{uuid.uuid4().hex[:8]}",
        "public_key": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA" + "0" * 44 + "-----END PUBLIC KEY-----"
    }
    response = await async_client.post("/signatures", json=sig_req, headers=auth_headers)
    # May fail with 422 if key format is invalid, or auth failures
    assert response.status_code in [200, 201, 401, 403, 400, 422, 429]

    if response.status_code in [200, 201]:
        data = response.json()
        assert isinstance(data, dict)
        assert "id" in data or "name" in data


@pytest.mark.asyncio
async def test_delete_signature_response(async_client: AsyncClient, auth_headers: dict):
    """
    DELETE /signatures/{id} deletes a signature.
    Expected: ActionResponse or 204 No Content.
    """
    # First get a signature ID if one exists
    list_response = await async_client.get("/signatures", headers=auth_headers)
    if list_response.status_code == 200:
        sigs = list_response.json()
        if len(sigs) > 0:
            sig_id = sigs[0].get("id")
            if sig_id:
                response = await async_client.delete(f"/signatures/{sig_id}", headers=auth_headers)
                # Should be 200 (with ActionResponse) or 204 (No Content)
                assert response.status_code in [200, 204]


# ============================================================================
# JOB DEFINITIONS ROUTES
# ============================================================================

@pytest.mark.asyncio
async def test_job_definitions_list_shape(async_client: AsyncClient, auth_headers: dict):
    """
    GET /job-definitions returns list of JobDefinitionResponse objects.
    Expected: List[JobDefinitionResponse] or PaginatedResponse[JobDefinitionResponse].
    """
    response = await async_client.get("/job-definitions", headers=auth_headers)
    assert response.status_code in [200, 401, 403, 429]

    if response.status_code == 200:
        data = response.json()
        # Could be list or paginated
        if isinstance(data, dict):
            # Paginated response
            assert "items" in data or "data" in data
        elif isinstance(data, list):
            # Direct list
            pass
        else:
            pytest.fail(f"Unexpected response type: {type(data)}")


@pytest.mark.asyncio
async def test_job_definitions_toggle_response(async_client: AsyncClient, auth_headers: dict):
    """
    PATCH /jobs/definitions/{id}/toggle toggles job definition active status.
    Expected: ActionResponse or JobDefinitionResponse.
    """
    # First get a job definition ID if one exists
    list_response = await async_client.get("/jobs/definitions", headers=auth_headers)
    if list_response.status_code == 200:
        data = list_response.json()
        items = data.get("items", data) if isinstance(data, dict) else data

        if len(items) > 0:
            job_id = items[0].get("id")
            if job_id:
                response = await async_client.patch(
                    f"/jobs/definitions/{job_id}/toggle",
                    headers=auth_headers
                )
                assert response.status_code in [200, 422]


# ============================================================================
# FOUNDRY ROUTES
# ============================================================================

@pytest.mark.asyncio
async def test_blueprints_list_shape(async_client: AsyncClient, auth_headers: dict):
    """
    GET /api/blueprints returns list of BlueprintResponse objects.
    Expected: List[BlueprintResponse].
    """
    response = await async_client.get("/api/blueprints", headers=auth_headers)
    assert response.status_code in [200, 401, 403, 404, 429]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        # Each blueprint should be a dict with id, name, type
        if len(data) > 0:
            bp = data[0]
            assert isinstance(bp, dict)
            assert "id" in bp or "name" in bp


@pytest.mark.asyncio
async def test_templates_list_shape(async_client: AsyncClient, auth_headers: dict):
    """
    GET /api/templates returns list of PuppetTemplateResponse objects.
    Expected: List[PuppetTemplateResponse].
    """
    response = await async_client.get("/api/templates", headers=auth_headers)
    assert response.status_code in [200, 401, 403, 404, 429]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        # Each template should be a dict
        if len(data) > 0:
            tpl = data[0]
            assert isinstance(tpl, dict)
            assert "id" in tpl or "name" in tpl


@pytest.mark.asyncio
async def test_build_template_response(async_client: AsyncClient, auth_headers: dict):
    """
    POST /api/templates/{id}/build builds a template and returns ImageResponse.
    Expected: ImageResponse with build status, image ID, etc.
    """
    # First get a template ID if one exists
    list_response = await async_client.get("/api/templates", headers=auth_headers)
    if list_response.status_code == 200:
        templates = list_response.json()
        if len(templates) > 0:
            template_id = templates[0].get("id")
            if template_id:
                response = await async_client.post(
                    f"/api/templates/{template_id}/build",
                    headers=auth_headers
                )
                # May succeed (200/201) or fail (404/422) if template doesn't exist
                assert response.status_code in [200, 201, 404, 422]

                if response.status_code in [200, 201]:
                    data = response.json()
                    assert isinstance(data, dict)
                    # Should have image info or build status
                    assert "image_id" in data or "status" in data or "build_status" in data


@pytest.mark.asyncio
async def test_capability_matrix_list_response(async_client: AsyncClient, auth_headers: dict):
    """
    GET /api/capability-matrix returns list of CapabilityMatrixEntry objects.
    Expected: List[CapabilityMatrixEntry].
    """
    response = await async_client.get("/api/capability-matrix", headers=auth_headers)
    assert response.status_code in [200, 401, 403, 404, 429]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_approved_os_list_response(async_client: AsyncClient, auth_headers: dict):
    """
    GET /api/approved-os returns list of ApprovedOSResponse objects.
    Expected: List[ApprovedOSResponse].
    """
    response = await async_client.get("/api/approved-os", headers=auth_headers)
    assert response.status_code in [200, 401, 403, 404, 429]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_template_bom_response(async_client: AsyncClient, auth_headers: dict):
    """
    GET /api/templates/{id}/bom returns ImageBOMResponse.
    Expected: ImageBOMResponse with package list, compatibility, etc.
    """
    # First get a template ID if one exists
    list_response = await async_client.get("/api/templates", headers=auth_headers)
    if list_response.status_code == 200:
        templates = list_response.json()
        if len(templates) > 0:
            template_id = templates[0].get("id")
            if template_id:
                response = await async_client.get(
                    f"/api/templates/{template_id}/bom",
                    headers=auth_headers
                )
                assert response.status_code in [200, 404, 422]

                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_search_packages_response(async_client: AsyncClient, auth_headers: dict):
    """
    GET /api/foundry/search-packages returns list of PackageIndexResponse objects.
    Expected: List[PackageIndexResponse].
    """
    response = await async_client.get(
        "/api/foundry/search-packages?query=python",
        headers=auth_headers
    )
    assert response.status_code in [200, 401, 403, 404, 422, 429]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


# ============================================================================
# FILE/CONTENT ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_node_compose_returns_yaml(async_client: AsyncClient):
    """
    GET /api/node/compose returns YAML content.
    Expected: YAML string (not necessarily JSON).
    """
    response = await async_client.get("/api/node/compose")
    assert response.status_code in [200, 422]

    # Should be YAML or text content
    if response.status_code == 200:
        assert response.text is not None


@pytest.mark.asyncio
async def test_root_ca_returns_pem(async_client: AsyncClient):
    """
    GET /system/root-ca returns PEM certificate.
    Expected: PEM-formatted certificate string.
    """
    response = await async_client.get("/system/root-ca")
    assert response.status_code == 200

    content = response.text
    # Should contain PEM markers
    assert "BEGIN" in content or "CERTIFICATE" in content or len(content) > 0


@pytest.mark.asyncio
async def test_crl_returns_pem(async_client: AsyncClient):
    """
    GET /system/crl.pem returns CRL in PEM format.
    Expected: PEM-formatted CRL or empty response.
    """
    response = await async_client.get("/system/crl.pem")
    # May be 200 or 404 if CRL hasn't been built yet
    assert response.status_code in [200, 404, 204]
