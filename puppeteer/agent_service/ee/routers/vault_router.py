"""EE Router: Vault integration configuration (Phase 167)."""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db, VaultConfig, User
from ...deps import require_permission, audit, require_ee
from ...models import VaultConfigResponse, VaultConfigUpdateRequest, VaultTestConnectionRequest, VaultTestConnectionResponse, VaultStatusResponse
from ...security import cipher_suite
from ee.services.vault_service import VaultConfigSnapshot

logger = logging.getLogger(__name__)
vault_router = APIRouter()


@vault_router.get("/admin/vault/config", response_model=VaultConfigResponse, tags=["Vault Configuration"])
async def get_vault_config(
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Get current Vault configuration. Masks secret_id for security."""
    result = await db.execute(select(VaultConfig).where(VaultConfig.enabled == True).limit(1))
    vault_config = result.scalar_one_or_none()

    if not vault_config:
        raise HTTPException(status_code=404, detail="No Vault configuration found")

    return VaultConfigResponse.from_vault_config(vault_config)


@vault_router.patch("/admin/vault/config", response_model=VaultConfigResponse, tags=["Vault Configuration"])
async def update_vault_config(
    req: VaultConfigUpdateRequest,
    request: Request,
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Update Vault configuration and reinitialize service."""
    # Fetch existing config
    result = await db.execute(select(VaultConfig).where(VaultConfig.enabled == True).limit(1))
    vault_config = result.scalar_one_or_none()

    if not vault_config:
        raise HTTPException(status_code=404, detail="No Vault configuration found")

    # Update fields (only non-None values)
    if req.vault_address is not None:
        vault_config.vault_address = req.vault_address
    if req.role_id is not None:
        vault_config.role_id = req.role_id
    if req.secret_id is not None:
        # Encrypt secret_id before storing (D-05)
        vault_config.secret_id = cipher_suite.encrypt(req.secret_id.encode()).decode()
    if req.mount_path is not None:
        vault_config.mount_path = req.mount_path
    if req.namespace is not None:
        vault_config.namespace = req.namespace
    if req.provider_type is not None:
        vault_config.provider_type = req.provider_type
    if req.enabled is not None:
        vault_config.enabled = req.enabled

    # Audit the update
    audit(db, current_user, "vault:config_update", vault_config.id, {
        "vault_address": req.vault_address,
        "role_id": req.role_id is not None,  # Don't log actual role_id
        "secret_id_updated": req.secret_id is not None,
        "mount_path": req.mount_path,
        "namespace": req.namespace,
        "provider_type": req.provider_type,
        "enabled": req.enabled,
    })

    db.add(vault_config)
    await db.commit()
    await db.refresh(vault_config)

    # Reinitialize vault_service with new config (convert to frozen snapshot per D-05)
    try:
        vault_service = getattr(request.app.state, 'vault_service', None)
        if vault_service:
            vault_service.config = VaultConfigSnapshot.from_orm(vault_config)
            await vault_service.startup()
            _status = await vault_service.status()
            logger.info(f"Vault service reinitialized after config update: status={_status}")
    except Exception as e:
        logger.warning(f"Failed to reinitialize Vault service: {e}")
        # Don't fail the response — config was saved; reinit is best-effort

    return VaultConfigResponse.from_vault_config(vault_config)


@vault_router.post("/admin/vault/test-connection", response_model=VaultTestConnectionResponse, tags=["Vault Configuration"])
async def test_vault_connection(
    req: VaultTestConnectionRequest,
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db)
):
    """Test connection to Vault without persisting configuration."""
    try:
        from ee.services.vault_service import VaultService, VaultError
        from ...db import AsyncSessionLocal

        # Create temporary test config (as frozen snapshot per D-05)
        test_config_obj = VaultConfig(
            id="test-connection",
            vault_address=req.vault_address,
            role_id=req.role_id,
            secret_id=cipher_suite.encrypt(req.secret_id.encode()).decode(),
            mount_path=req.mount_path or "secret",
            namespace=req.namespace,
            provider_type="vault",
            enabled=True,
        )
        test_config = VaultConfigSnapshot(
            enabled=test_config_obj.enabled,
            vault_address=test_config_obj.vault_address,
            role_id=test_config_obj.role_id,
            secret_id=test_config_obj.secret_id,
            mount_path=test_config_obj.mount_path,
            namespace=test_config_obj.namespace,
            provider_type=test_config_obj.provider_type,
        )

        # Create test service and attempt connection
        async with AsyncSessionLocal() as test_db:
            test_service = VaultService(test_config, test_db)
            await test_service.startup()
            status = await test_service.status()

            # Audit the test attempt
            audit(db, current_user, "vault:test_connection", req.vault_address, {
                "status": status,
                "success": status == "healthy",
            })
            await db.commit()

            if status == "healthy":
                return VaultTestConnectionResponse(
                    success=True,
                    status=status,
                    message="Connection successful. Vault is healthy and ready."
                )
            else:
                return VaultTestConnectionResponse(
                    success=False,
                    status=status,
                    error_detail=f"Vault status is {status}",
                    message=f"Connection attempted but Vault status is {status}. Check connectivity and credentials."
                )

    except Exception as e:
        logger.error(f"Vault test connection failed: {e}")
        error_msg = str(e)

        # Audit the failed attempt
        audit(db, current_user, "vault:test_connection_failed", req.vault_address, {
            "error": error_msg,
        })
        await db.commit()

        return VaultTestConnectionResponse(
            success=False,
            status="disabled",
            error_detail=error_msg,
            message=f"Connection test failed: {error_msg}"
        )


@vault_router.get("/admin/vault/status", response_model=VaultStatusResponse, tags=["Vault Configuration"])
async def get_vault_status(
    current_user: User = Depends(require_ee()),
    db: AsyncSession = Depends(get_db),
    request: Request = None,  # FastAPI injects; None guard below
):
    """Get current Vault health status with renewal failure tracking."""
    # Fetch vault config
    result = await db.execute(select(VaultConfig).where(VaultConfig.enabled == True).limit(1))
    vault_config = result.scalar_one_or_none()

    if not vault_config:
        raise HTTPException(status_code=404, detail="No Vault configuration found")

    # Get vault_service from app state
    vault_service = getattr(request.app.state, 'vault_service', None)

    if not vault_service:
        raise HTTPException(status_code=503, detail="Vault service not initialized")

    # Get current status and renewal failure count
    status = await vault_service.status()
    renewal_failures = vault_service._consecutive_renewal_failures

    return VaultStatusResponse(
        status=status,
        vault_address=vault_config.vault_address,
        last_checked_at=getattr(vault_service, '_last_checked_at', None),
        error_detail=getattr(vault_service, '_last_error', None),
        renewal_failures=renewal_failures
    )
