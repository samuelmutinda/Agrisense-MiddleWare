"""Service layer for OperatingCost operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.operating_cost import OperatingCost
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.schemas import operating_cost as cost_schema


async def create_operating_cost(session: AsyncSession, data: cost_schema.OperatingCostCreate, auth: AuthContext):
    record = OperatingCost(
        tenant_id=auth.tenant_id,
        facility_id=data.facility_id,
        category=data.category.value,
        description=data.description,
        amount=data.amount,
        currency=data.currency,
        period_start=data.period_start,
        period_end=data.period_end,
        vendor_name=data.vendor_name,
        invoice_reference=data.invoice_reference,
        is_recurring=data.is_recurring,
        extra_metadata=data.metadata
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return await get_operating_cost_by_id(session, record.id, auth)


async def get_operating_cost_by_id(session: AsyncSession, record_id: uuid.UUID, auth: AuthContext):
    stmt = select(OperatingCost).where(OperatingCost.id == record_id, OperatingCost.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Operating cost {record_id} not found")
    response = cost_schema.OperatingCostResponse.model_validate(record)
    if record.facility_id:
        facility = await session.get(ColdStorageUnit, record.facility_id)
        if facility:
            response.facility_name = facility.name
    return response


async def list_operating_costs(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 20, facility_id: Optional[uuid.UUID] = None, category: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None):
    stmt = select(OperatingCost).where(OperatingCost.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(OperatingCost.id)).where(OperatingCost.tenant_id == auth.tenant_id)
    sum_stmt = select(func.sum(OperatingCost.amount)).where(OperatingCost.tenant_id == auth.tenant_id)
    if facility_id:
        stmt = stmt.where(OperatingCost.facility_id == facility_id)
        count_stmt = count_stmt.where(OperatingCost.facility_id == facility_id)
        sum_stmt = sum_stmt.where(OperatingCost.facility_id == facility_id)
    if category:
        stmt = stmt.where(OperatingCost.category == category)
        count_stmt = count_stmt.where(OperatingCost.category == category)
        sum_stmt = sum_stmt.where(OperatingCost.category == category)
    if date_from:
        stmt = stmt.where(OperatingCost.period_start >= date_from)
        count_stmt = count_stmt.where(OperatingCost.period_start >= date_from)
        sum_stmt = sum_stmt.where(OperatingCost.period_start >= date_from)
    if date_to:
        stmt = stmt.where(OperatingCost.period_end <= date_to)
        count_stmt = count_stmt.where(OperatingCost.period_end <= date_to)
        sum_stmt = sum_stmt.where(OperatingCost.period_end <= date_to)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    sum_result = await session.execute(sum_stmt)
    total_amount = sum_result.scalar()
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(OperatingCost.period_start.desc())
    result = await session.execute(stmt)
    records = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return cost_schema.OperatingCostListResponse(
        items=[cost_schema.OperatingCostResponse.model_validate(r) for r in records],
        total=total, page=page, page_size=page_size, total_pages=total_pages, total_amount=total_amount
    )
