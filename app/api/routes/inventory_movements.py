"""API routes for InventoryMovement resource."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import inventory_movement as movement_schema
from app.services import inventory_movement_service


router = APIRouter(prefix="/inventory-movements", tags=["inventory-movements"])


@router.post(
    "",
    response_model=movement_schema.InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create inventory movement"
)
async def create_inventory_movement(
    payload: movement_schema.InventoryMovementCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create a new inventory movement (intake, outbound, transfer, etc.)."""
    try:
        return await inventory_movement_service.create_inventory_movement(
            session=session, data=payload, auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=movement_schema.InventoryMovementListResponse,
    summary="List inventory movements"
)
async def list_inventory_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    produce_batch_id: Optional[uuid.UUID] = Query(None),
    movement_type: Optional[str] = Query(None),
    location_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List inventory movements with filtering."""
    return await inventory_movement_service.list_inventory_movements(
        session=session,
        auth=auth,
        page=page,
        page_size=page_size,
        produce_batch_id=produce_batch_id,
        movement_type=movement_type,
        location_id=location_id,
        date_from=date_from,
        date_to=date_to
    )


@router.get(
    "/{movement_id}",
    response_model=movement_schema.InventoryMovementResponse,
    summary="Get inventory movement by ID"
)
async def get_inventory_movement(
    movement_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Get a specific inventory movement by ID."""
    try:
        return await inventory_movement_service.get_inventory_movement_by_id(
            session=session,
            movement_id=movement_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/adjust",
    response_model=movement_schema.InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adjust inventory"
)
async def adjust_inventory(
    payload: movement_schema.InventoryAdjustmentCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create an inventory adjustment (corrections)."""
    try:
        return await inventory_movement_service.adjust_inventory(
            session=session, data=payload, auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
