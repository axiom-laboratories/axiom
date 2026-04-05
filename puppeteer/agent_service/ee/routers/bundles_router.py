"""EE Router: Curated Bundles — pre-built package bundles for bulk approval."""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ...db import get_db, AsyncSession, CuratedBundle, CuratedBundleItem, ApprovedIngredient, User
from ...deps import require_permission, audit
from ...models import (
    CuratedBundleCreate, CuratedBundleResponse, CuratedBundleItemCreate, CuratedBundleItemResponse,
    ApplyBundleResult, ApprovedIngredientCreate,
)
from ...services.smelter_service import SmelterService

bundles_router = APIRouter()


@bundles_router.get("/api/admin/bundles", response_model=List[CuratedBundleResponse], tags=["Bundles"])
async def list_bundles(
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """List all curated bundles (Admin only)."""
    result = await db.execute(
        select(CuratedBundle)
        .options(selectinload(CuratedBundle.items))
        .order_by(CuratedBundle.name)
    )
    bundles = result.scalars().all()
    return bundles


@bundles_router.post("/api/admin/bundles", response_model=CuratedBundleResponse, status_code=201, tags=["Bundles"])
async def create_bundle(
    bundle: CuratedBundleCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new curated bundle (Admin only)."""
    # Check for duplicate name
    existing = await db.execute(
        select(CuratedBundle).where(CuratedBundle.name == bundle.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Bundle '{bundle.name}' already exists")

    db_bundle = CuratedBundle(
        id=str(uuid4()),
        name=bundle.name,
        description=bundle.description,
        ecosystem=bundle.ecosystem,
        os_family=bundle.os_family,
        is_active=True
    )
    db.add(db_bundle)
    await db.commit()
    await db.refresh(db_bundle)

    audit(db, current_user, "bundle:created", bundle.name)
    await db.commit()

    return db_bundle


@bundles_router.get("/api/admin/bundles/{id}", response_model=CuratedBundleResponse, tags=["Bundles"])
async def get_bundle(
    id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific curated bundle by ID (Admin only)."""
    result = await db.execute(
        select(CuratedBundle)
        .where(CuratedBundle.id == id)
        .options(selectinload(CuratedBundle.items))
    )
    bundle = result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return bundle


@bundles_router.patch("/api/admin/bundles/{id}", response_model=CuratedBundleResponse, tags=["Bundles"])
async def update_bundle(
    id: str,
    bundle_update: CuratedBundleCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Update a curated bundle (Admin only)."""
    result = await db.execute(
        select(CuratedBundle)
        .where(CuratedBundle.id == id)
        .options(selectinload(CuratedBundle.items))
    )
    bundle = result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    # Update only provided fields
    if bundle_update.name != bundle.name:
        # Check for duplicate name on rename
        existing = await db.execute(
            select(CuratedBundle).where(
                CuratedBundle.name == bundle_update.name,
                CuratedBundle.id != id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Bundle '{bundle_update.name}' already exists")

    bundle.name = bundle_update.name
    bundle.description = bundle_update.description
    bundle.ecosystem = bundle_update.ecosystem
    bundle.os_family = bundle_update.os_family

    await db.commit()
    await db.refresh(bundle)

    audit(db, current_user, "bundle:updated", bundle.name)
    await db.commit()

    return bundle


@bundles_router.delete("/api/admin/bundles/{id}", tags=["Bundles"])
async def delete_bundle(
    id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete a curated bundle and cascade-delete its items (Admin only)."""
    result = await db.execute(
        select(CuratedBundle).where(CuratedBundle.id == id)
    )
    bundle = result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    bundle_name = bundle.name

    # Delete items (cascade)
    await db.execute(
        select(CuratedBundleItem).where(CuratedBundleItem.bundle_id == id)
    )
    await db.delete(bundle)
    await db.commit()

    audit(db, current_user, "bundle:deleted", bundle_name)
    await db.commit()

    return {"status": "deleted", "id": id}


@bundles_router.post("/api/admin/bundles/{id}/items", response_model=CuratedBundleItemResponse, status_code=201, tags=["Bundles"])
async def add_bundle_item(
    id: str,
    item: CuratedBundleItemCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Add a package item to a curated bundle (Admin only)."""
    # Verify bundle exists
    result = await db.execute(
        select(CuratedBundle).where(CuratedBundle.id == id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Bundle not found")

    db_item = CuratedBundleItem(
        bundle_id=id,
        ingredient_name=item.ingredient_name,
        version_constraint=item.version_constraint,
        ecosystem=item.ecosystem
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    return db_item


@bundles_router.patch("/api/admin/bundles/{id}/items/{item_id}", response_model=CuratedBundleItemResponse, tags=["Bundles"])
async def update_bundle_item(
    id: str,
    item_id: int,
    item_update: CuratedBundleItemCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Update a package item in a curated bundle (Admin only)."""
    # Verify bundle exists
    result = await db.execute(
        select(CuratedBundle).where(CuratedBundle.id == id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Bundle not found")

    # Get the item
    result = await db.execute(
        select(CuratedBundleItem).where(
            CuratedBundleItem.id == item_id,
            CuratedBundleItem.bundle_id == id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.ingredient_name = item_update.ingredient_name
    item.version_constraint = item_update.version_constraint
    item.ecosystem = item_update.ecosystem

    await db.commit()
    await db.refresh(item)

    return item


@bundles_router.delete("/api/admin/bundles/{id}/items/{item_id}", tags=["Bundles"])
async def delete_bundle_item(
    id: str,
    item_id: int,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete a package item from a curated bundle (Admin only)."""
    # Verify bundle exists
    result = await db.execute(
        select(CuratedBundle).where(CuratedBundle.id == id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Bundle not found")

    # Get and delete the item
    result = await db.execute(
        select(CuratedBundleItem).where(
            CuratedBundleItem.id == item_id,
            CuratedBundleItem.bundle_id == id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)
    await db.commit()

    return {"status": "deleted", "item_id": item_id}


@bundles_router.post("/api/foundry/apply-bundle/{bundle_id}", response_model=ApplyBundleResult, tags=["Bundles"])
async def apply_bundle(
    bundle_id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Apply a curated bundle: bulk-approve all items as ingredients (Operator+)."""
    # Get bundle and items
    result = await db.execute(
        select(CuratedBundle)
        .where(CuratedBundle.id == bundle_id)
        .options(selectinload(CuratedBundle.items))
    )
    bundle = result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    approved_count = 0
    skipped_count = 0

    # Loop through items and approve each
    for item in bundle.items:
        # Check if already approved
        existing = await db.execute(
            select(ApprovedIngredient).where(
                ApprovedIngredient.name == item.ingredient_name,
                ApprovedIngredient.ecosystem == item.ecosystem
            )
        )
        if existing.scalar_one_or_none():
            skipped_count += 1
            continue

        # Add as approved ingredient
        try:
            ingredient_create = ApprovedIngredientCreate(
                name=item.ingredient_name,
                version_constraint=item.version_constraint if item.version_constraint != "*" else None,
                ecosystem=item.ecosystem,
                os_family=bundle.os_family
            )
            await SmelterService.add_ingredient(db, ingredient_create)
            approved_count += 1
        except Exception as e:
            # Log error but continue with next item
            import logging
            logging.error(f"Failed to approve ingredient {item.ingredient_name}: {str(e)}")
            continue

    total = approved_count + skipped_count

    audit(
        db,
        current_user,
        "bundle:applied",
        f"{bundle.name} ({approved_count} new, {skipped_count} skipped)"
    )
    await db.commit()

    return ApplyBundleResult(
        bundle_id=bundle.id,
        bundle_name=bundle.name,
        approved=approved_count,
        skipped=skipped_count,
        total=total
    )
