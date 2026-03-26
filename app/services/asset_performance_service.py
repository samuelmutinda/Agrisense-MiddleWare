"""Service layer for AssetPerformance operations."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.asset_performance import AssetPerformance
from app.schemas import asset_performance as asset_schema


async def create_asset_performance(session: AsyncSession, data: asset_schema.AssetPerformanceCreate, auth: AuthContext):
    record = AssetPerformance(
        tenant_id=auth.tenant_id,
        asset_id=data.asset_id,
        asset_type=data.asset_type.value,
        asset_name=data.asset_name,
        uptime_percent=data.uptime_percent,
        efficiency_score=data.efficiency_score,
        performance_status=data.performance_status.value,
        measurement_timestamp=data.measurement_timestamp,
        energy_consumption_kwh=data.energy_consumption_kwh,
        operating_hours=data.operating_hours,
        error_count=data.error_count,
        last_maintenance=data.last_maintenance,
        extra_metadata=data.metadata
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return asset_schema.AssetPerformanceResponse.model_validate(record)


async def get_asset_performance_by_id(session: AsyncSession, record_id: uuid.UUID, auth: AuthContext):
    stmt = select(AssetPerformance).where(AssetPerformance.id == record_id, AssetPerformance.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Asset performance record {record_id} not found")
    return asset_schema.AssetPerformanceResponse.model_validate(record)


async def list_asset_performance(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 20, asset_id: Optional[uuid.UUID] = None, asset_type: Optional[str] = None, status: Optional[str] = None):
    stmt = select(AssetPerformance).where(AssetPerformance.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(AssetPerformance.id)).where(AssetPerformance.tenant_id == auth.tenant_id)
    if asset_id:
        stmt = stmt.where(AssetPerformance.asset_id == asset_id)
        count_stmt = count_stmt.where(AssetPerformance.asset_id == asset_id)
    if asset_type:
        stmt = stmt.where(AssetPerformance.asset_type == asset_type)
        count_stmt = count_stmt.where(AssetPerformance.asset_type == asset_type)
    if status:
        stmt = stmt.where(AssetPerformance.performance_status == status)
        count_stmt = count_stmt.where(AssetPerformance.performance_status == status)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(AssetPerformance.measurement_timestamp.desc())
    result = await session.execute(stmt)
    records = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return asset_schema.AssetPerformanceListResponse(items=[asset_schema.AssetPerformanceResponse.model_validate(r) for r in records], total=total, page=page, page_size=page_size, total_pages=total_pages)
