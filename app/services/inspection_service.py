"""Service layer for Inspection operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.inspection import Inspection
from app.db.models.produce_batch import ProduceBatch
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.db.models.user import User
from app.schemas import inspection as inspection_schema


async def create_inspection(
    session: AsyncSession,
    data: inspection_schema.InspectionCreate,
    auth: AuthContext
) -> inspection_schema.InspectionResponse:
    """Create a new inspection."""
    inspection = Inspection(
        tenant_id=auth.tenant_id,
        produce_batch_id=data.produce_batch_id,
        storage_unit_id=data.storage_unit_id,
        inspection_type=data.inspection_type.value,
        inspector_id=auth.user_id,
        scheduled_date=data.scheduled_date,
        criteria=[c.model_dump() for c in data.criteria] if data.criteria else None,
        notes=data.notes,
        metadata=data.metadata,
        result="pending"
    )
    session.add(inspection)
    await session.commit()
    await session.refresh(inspection)
    
    return await get_inspection_by_id(session, inspection.id, auth)


async def get_inspection_by_id(
    session: AsyncSession,
    inspection_id: uuid.UUID,
    auth: AuthContext
) -> inspection_schema.InspectionResponse:
    """Get inspection by ID."""
    stmt = select(Inspection).where(
        Inspection.id == inspection_id,
        Inspection.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    inspection = result.scalar_one_or_none()
    
    if not inspection:
        raise ValueError(f"Inspection {inspection_id} not found")
    
    response = inspection_schema.InspectionResponse.model_validate(inspection)
    
    # Enrich with names
    user = await session.get(User, inspection.inspector_id)
    if user:
        response.inspector_name = f"{user.first_name} {user.last_name}"
    
    if inspection.produce_batch_id:
        batch = await session.get(ProduceBatch, inspection.produce_batch_id)
        if batch:
            response.batch_number = batch.batch_number
    
    if inspection.storage_unit_id:
        unit = await session.get(ColdStorageUnit, inspection.storage_unit_id)
        if unit:
            response.storage_unit_name = unit.name
    
    return response


async def list_inspections(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    produce_batch_id: Optional[uuid.UUID] = None,
    storage_unit_id: Optional[uuid.UUID] = None,
    inspection_type: Optional[str] = None,
    result: Optional[str] = None,
    inspector_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> inspection_schema.InspectionListResponse:
    """List inspections with filtering."""
    stmt = select(Inspection).where(Inspection.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(Inspection.id)).where(Inspection.tenant_id == auth.tenant_id)
    
    if produce_batch_id:
        stmt = stmt.where(Inspection.produce_batch_id == produce_batch_id)
        count_stmt = count_stmt.where(Inspection.produce_batch_id == produce_batch_id)
    
    if storage_unit_id:
        stmt = stmt.where(Inspection.storage_unit_id == storage_unit_id)
        count_stmt = count_stmt.where(Inspection.storage_unit_id == storage_unit_id)
    
    if inspection_type:
        stmt = stmt.where(Inspection.inspection_type == inspection_type)
        count_stmt = count_stmt.where(Inspection.inspection_type == inspection_type)
    
    if result:
        stmt = stmt.where(Inspection.result == result)
        count_stmt = count_stmt.where(Inspection.result == result)
    
    if inspector_id:
        stmt = stmt.where(Inspection.inspector_id == inspector_id)
        count_stmt = count_stmt.where(Inspection.inspector_id == inspector_id)
    
    if date_from:
        stmt = stmt.where(Inspection.created_at >= date_from)
        count_stmt = count_stmt.where(Inspection.created_at >= date_from)
    
    if date_to:
        stmt = stmt.where(Inspection.created_at <= date_to)
        count_stmt = count_stmt.where(Inspection.created_at <= date_to)
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(Inspection.created_at.desc())
    
    result = await session.execute(stmt)
    inspections = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return inspection_schema.InspectionListResponse(
        items=[inspection_schema.InspectionResponse.model_validate(i) for i in inspections],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


async def update_inspection(
    session: AsyncSession,
    inspection_id: uuid.UUID,
    data: inspection_schema.InspectionUpdate,
    auth: AuthContext
) -> inspection_schema.InspectionResponse:
    """Update an inspection (complete it)."""
    stmt = select(Inspection).where(
        Inspection.id == inspection_id,
        Inspection.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    inspection = result.scalar_one_or_none()
    
    if not inspection:
        raise ValueError(f"Inspection {inspection_id} not found")
    
    update_data = data.model_dump(exclude_unset=True)
    if "result" in update_data and update_data["result"]:
        update_data["result"] = data.result.value
    if "criteria" in update_data and data.criteria:
        update_data["criteria"] = [c.model_dump() for c in data.criteria]
    
    for field, value in update_data.items():
        setattr(inspection, field, value)
    
    await session.commit()
    return await get_inspection_by_id(session, inspection_id, auth)


async def delete_inspection(
    session: AsyncSession,
    inspection_id: uuid.UUID,
    auth: AuthContext
) -> bool:
    """Delete an inspection (only pending ones)."""
    stmt = select(Inspection).where(
        Inspection.id == inspection_id,
        Inspection.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    inspection = result.scalar_one_or_none()
    
    if not inspection:
        raise ValueError(f"Inspection {inspection_id} not found")
    
    if inspection.result != "pending":
        raise ValueError("Can only delete pending inspections")
    
    await session.delete(inspection)
    await session.commit()
    return True
