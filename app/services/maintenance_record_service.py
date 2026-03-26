"""Service layer for MaintenanceRecord operations."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.maintenance_record import MaintenanceRecord
from app.db.models.user import User
from app.schemas import maintenance_record as maint_schema


async def create_maintenance_record(session: AsyncSession, data: maint_schema.MaintenanceRecordCreate, auth: AuthContext):
    record = MaintenanceRecord(
        tenant_id=auth.tenant_id,
        asset_id=data.asset_id,
        asset_type=data.asset_type,
        asset_name=data.asset_name,
        maintenance_type=data.maintenance_type.value,
        status="scheduled",
        priority=data.priority.value,
        scheduled_date=data.scheduled_date,
        description=data.description,
        assigned_technician_id=data.assigned_technician_id,
        estimated_duration_hours=data.estimated_duration_hours,
        estimated_cost=data.estimated_cost,
        parts_required=data.parts_required,
        extra_metadata=data.metadata
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return await get_maintenance_record_by_id(session, record.id, auth)


async def get_maintenance_record_by_id(session: AsyncSession, record_id: uuid.UUID, auth: AuthContext):
    stmt = select(MaintenanceRecord).where(MaintenanceRecord.id == record_id, MaintenanceRecord.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Maintenance record {record_id} not found")
    response = maint_schema.MaintenanceRecordResponse.model_validate(record)
    if record.assigned_technician_id:
        tech = await session.get(User, record.assigned_technician_id)
        if tech:
            response.assigned_technician_name = f"{tech.first_name} {tech.last_name}"
    return response


async def update_maintenance_record(session: AsyncSession, record_id: uuid.UUID, data: maint_schema.MaintenanceRecordUpdate, auth: AuthContext):
    stmt = select(MaintenanceRecord).where(MaintenanceRecord.id == record_id, MaintenanceRecord.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Maintenance record {record_id} not found")
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value
    if "priority" in update_data and update_data["priority"]:
        update_data["priority"] = update_data["priority"].value
    for key, value in update_data.items():
        setattr(record, key, value)
    await session.commit()
    return await get_maintenance_record_by_id(session, record_id, auth)


async def list_maintenance_records(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 20, asset_id: Optional[uuid.UUID] = None, maintenance_type: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None):
    stmt = select(MaintenanceRecord).where(MaintenanceRecord.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(MaintenanceRecord.id)).where(MaintenanceRecord.tenant_id == auth.tenant_id)
    if asset_id:
        stmt = stmt.where(MaintenanceRecord.asset_id == asset_id)
        count_stmt = count_stmt.where(MaintenanceRecord.asset_id == asset_id)
    if maintenance_type:
        stmt = stmt.where(MaintenanceRecord.maintenance_type == maintenance_type)
        count_stmt = count_stmt.where(MaintenanceRecord.maintenance_type == maintenance_type)
    if status:
        stmt = stmt.where(MaintenanceRecord.status == status)
        count_stmt = count_stmt.where(MaintenanceRecord.status == status)
    if priority:
        stmt = stmt.where(MaintenanceRecord.priority == priority)
        count_stmt = count_stmt.where(MaintenanceRecord.priority == priority)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(MaintenanceRecord.scheduled_date.asc())
    result = await session.execute(stmt)
    records = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return maint_schema.MaintenanceRecordListResponse(items=[maint_schema.MaintenanceRecordResponse.model_validate(r) for r in records], total=total, page=page, page_size=page_size, total_pages=total_pages)
