"""Service layer for InventoryMovement operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.inventory_movement import InventoryMovement
from app.db.models.produce_batch import ProduceBatch
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.db.models.user import User
from app.schemas import inventory_movement as movement_schema


async def create_inventory_movement(
    session: AsyncSession,
    data: movement_schema.InventoryMovementCreate,
    auth: AuthContext
) -> movement_schema.InventoryMovementResponse:
    """Create a new inventory movement."""
    # Validate batch exists
    batch = await session.get(ProduceBatch, data.produce_batch_id)
    if not batch or batch.tenant_id != auth.tenant_id:
        raise ValueError(f"Produce batch {data.produce_batch_id} not found")
    
    # Update batch remaining quantity
    if data.movement_type.value in ("outbound", "loss"):
        if batch.remaining_quantity_kg < data.quantity_kg:
            raise ValueError("Insufficient quantity in batch")
        batch.remaining_quantity_kg -= data.quantity_kg
    elif data.movement_type.value in ("intake", "return"):
        batch.remaining_quantity_kg += data.quantity_kg
    
    movement = InventoryMovement(
        tenant_id=auth.tenant_id,
        produce_batch_id=data.produce_batch_id,
        movement_type=data.movement_type.value,
        quantity_kg=data.quantity_kg,
        from_location_id=data.from_location_id,
        to_location_id=data.to_location_id,
        reference_document_id=data.reference_document_id,
        reference_type=data.reference_type,
        executed_by_user_id=auth.user_id,
        reason=data.reason,
        notes=data.notes,
        extra_metadata=data.metadata
    )
    session.add(movement)
    await session.commit()
    await session.refresh(movement)
    
    return await get_inventory_movement_by_id(session, movement.id, auth)


async def get_inventory_movement_by_id(
    session: AsyncSession,
    movement_id: uuid.UUID,
    auth: AuthContext
) -> movement_schema.InventoryMovementResponse:
    """Get inventory movement by ID."""
    stmt = select(InventoryMovement).where(
        InventoryMovement.id == movement_id,
        InventoryMovement.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    movement = result.scalar_one_or_none()
    
    if not movement:
        raise ValueError(f"Inventory movement {movement_id} not found")
    
    response = movement_schema.InventoryMovementResponse.model_validate(movement)
    
    # Enrich with names
    batch = await session.get(ProduceBatch, movement.produce_batch_id)
    if batch:
        response.batch_number = batch.batch_number
    
    user = await session.get(User, movement.executed_by_user_id)
    if user:
        response.executed_by_name = f"{user.first_name} {user.last_name}"
    
    if movement.from_location_id:
        loc = await session.get(ColdStorageUnit, movement.from_location_id)
        if loc:
            response.from_location_name = loc.name
    
    if movement.to_location_id:
        loc = await session.get(ColdStorageUnit, movement.to_location_id)
        if loc:
            response.to_location_name = loc.name
    
    return response


async def list_inventory_movements(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    produce_batch_id: Optional[uuid.UUID] = None,
    movement_type: Optional[str] = None,
    location_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> movement_schema.InventoryMovementListResponse:
    """List inventory movements with filtering."""
    stmt = select(InventoryMovement).where(InventoryMovement.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(InventoryMovement.id)).where(InventoryMovement.tenant_id == auth.tenant_id)
    
    if produce_batch_id:
        stmt = stmt.where(InventoryMovement.produce_batch_id == produce_batch_id)
        count_stmt = count_stmt.where(InventoryMovement.produce_batch_id == produce_batch_id)
    
    if movement_type:
        stmt = stmt.where(InventoryMovement.movement_type == movement_type)
        count_stmt = count_stmt.where(InventoryMovement.movement_type == movement_type)
    
    if location_id:
        stmt = stmt.where(
            (InventoryMovement.from_location_id == location_id) |
            (InventoryMovement.to_location_id == location_id)
        )
        count_stmt = count_stmt.where(
            (InventoryMovement.from_location_id == location_id) |
            (InventoryMovement.to_location_id == location_id)
        )
    
    if date_from:
        stmt = stmt.where(InventoryMovement.created_at >= date_from)
        count_stmt = count_stmt.where(InventoryMovement.created_at >= date_from)
    
    if date_to:
        stmt = stmt.where(InventoryMovement.created_at <= date_to)
        count_stmt = count_stmt.where(InventoryMovement.created_at <= date_to)
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(InventoryMovement.created_at.desc())
    
    result = await session.execute(stmt)
    movements = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return movement_schema.InventoryMovementListResponse(
        items=[movement_schema.InventoryMovementResponse.model_validate(m) for m in movements],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


async def adjust_inventory(
    session: AsyncSession,
    data: movement_schema.InventoryAdjustmentCreate,
    auth: AuthContext
) -> movement_schema.InventoryMovementResponse:
    """Create an inventory adjustment."""
    batch = await session.get(ProduceBatch, data.produce_batch_id)
    if not batch or batch.tenant_id != auth.tenant_id:
        raise ValueError(f"Produce batch {data.produce_batch_id} not found")
    
    new_quantity = batch.remaining_quantity_kg + data.adjustment_quantity_kg
    if new_quantity < 0:
        raise ValueError("Adjustment would result in negative inventory")
    
    batch.remaining_quantity_kg = new_quantity
    
    movement = InventoryMovement(
        tenant_id=auth.tenant_id,
        produce_batch_id=data.produce_batch_id,
        movement_type="adjustment",
        quantity_kg=abs(data.adjustment_quantity_kg),
        executed_by_user_id=auth.user_id,
        reason=data.reason,
        notes=data.notes
    )
    session.add(movement)
    await session.commit()
    await session.refresh(movement)
    
    return await get_inventory_movement_by_id(session, movement.id, auth)
