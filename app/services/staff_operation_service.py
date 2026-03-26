"""Service layer for StaffOperation operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.staff_operation import StaffOperation
from app.db.models.user import User
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.schemas import staff_operation as staff_schema


async def create_staff_operation(session: AsyncSession, data: staff_schema.StaffOperationCreate, auth: AuthContext):
    record = StaffOperation(
        tenant_id=auth.tenant_id,
        staff_id=data.staff_id,
        operation_type=data.operation_type.value,
        facility_id=data.facility_id,
        shift_type=data.shift_type.value if data.shift_type else None,
        operation_date=data.operation_date,
        start_time=data.start_time,
        end_time=data.end_time,
        task_description=data.task_description,
        area_assigned=data.area_assigned,
        supervisor_id=data.supervisor_id,
        extra_metadata=data.metadata
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return await get_staff_operation_by_id(session, record.id, auth)


async def get_staff_operation_by_id(session: AsyncSession, record_id: uuid.UUID, auth: AuthContext):
    stmt = select(StaffOperation).where(StaffOperation.id == record_id, StaffOperation.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Staff operation {record_id} not found")
    response = staff_schema.StaffOperationResponse.model_validate(record)
    if record.start_time and record.end_time:
        response.duration_hours = (record.end_time - record.start_time).total_seconds() / 3600
    staff = await session.get(User, record.staff_id)
    if staff:
        response.staff_name = f"{staff.first_name} {staff.last_name}"
    if record.supervisor_id:
        supervisor = await session.get(User, record.supervisor_id)
        if supervisor:
            response.supervisor_name = f"{supervisor.first_name} {supervisor.last_name}"
    if record.facility_id:
        facility = await session.get(ColdStorageUnit, record.facility_id)
        if facility:
            response.facility_name = facility.name
    return response


async def update_staff_operation(session: AsyncSession, record_id: uuid.UUID, data: staff_schema.StaffOperationUpdate, auth: AuthContext):
    stmt = select(StaffOperation).where(StaffOperation.id == record_id, StaffOperation.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Staff operation {record_id} not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)
    await session.commit()
    return await get_staff_operation_by_id(session, record_id, auth)


async def list_staff_operations(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 20, staff_id: Optional[uuid.UUID] = None, facility_id: Optional[uuid.UUID] = None, operation_type: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None):
    stmt = select(StaffOperation).where(StaffOperation.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(StaffOperation.id)).where(StaffOperation.tenant_id == auth.tenant_id)
    if staff_id:
        stmt = stmt.where(StaffOperation.staff_id == staff_id)
        count_stmt = count_stmt.where(StaffOperation.staff_id == staff_id)
    if facility_id:
        stmt = stmt.where(StaffOperation.facility_id == facility_id)
        count_stmt = count_stmt.where(StaffOperation.facility_id == facility_id)
    if operation_type:
        stmt = stmt.where(StaffOperation.operation_type == operation_type)
        count_stmt = count_stmt.where(StaffOperation.operation_type == operation_type)
    if date_from:
        stmt = stmt.where(StaffOperation.operation_date >= date_from)
        count_stmt = count_stmt.where(StaffOperation.operation_date >= date_from)
    if date_to:
        stmt = stmt.where(StaffOperation.operation_date <= date_to)
        count_stmt = count_stmt.where(StaffOperation.operation_date <= date_to)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(StaffOperation.operation_date.desc(), StaffOperation.start_time.desc())
    result = await session.execute(stmt)
    records = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    items = []
    for r in records:
        resp = staff_schema.StaffOperationResponse.model_validate(r)
        if r.start_time and r.end_time:
            resp.duration_hours = (r.end_time - r.start_time).total_seconds() / 3600
        items.append(resp)
    total_hours = sum(i.duration_hours or 0 for i in items)
    return staff_schema.StaffOperationListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages, total_hours=total_hours)
