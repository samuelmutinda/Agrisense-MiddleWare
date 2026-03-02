"""Service layer for KpiMetric operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.kpi_metric import KpiMetric
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.schemas import kpi_metric as kpi_schema


async def create_kpi_metric(session: AsyncSession, data: kpi_schema.KpiMetricCreate, auth: AuthContext):
    metric = KpiMetric(
        tenant_id=auth.tenant_id,
        metric_name=data.metric_name,
        category=data.category.value,
        value=data.value,
        unit=data.unit,
        target_value=data.target_value,
        period_start=data.period_start,
        period_end=data.period_end,
        facility_id=data.facility_id,
        metadata=data.metadata
    )
    session.add(metric)
    await session.commit()
    await session.refresh(metric)
    return await get_kpi_metric_by_id(session, metric.id, auth)


async def get_kpi_metric_by_id(session: AsyncSession, metric_id: uuid.UUID, auth: AuthContext):
    stmt = select(KpiMetric).where(KpiMetric.id == metric_id, KpiMetric.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    metric = result.scalar_one_or_none()
    if not metric:
        raise ValueError(f"KPI metric {metric_id} not found")
    response = kpi_schema.KpiMetricResponse.model_validate(metric)
    if metric.target_value and metric.target_value > 0:
        response.variance_percent = ((metric.value - metric.target_value) / metric.target_value) * 100
    if metric.facility_id:
        facility = await session.get(ColdStorageUnit, metric.facility_id)
        if facility:
            response.facility_name = facility.name
    return response


async def list_kpi_metrics(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 20, category: Optional[str] = None, facility_id: Optional[uuid.UUID] = None, date_from: Optional[date] = None, date_to: Optional[date] = None):
    stmt = select(KpiMetric).where(KpiMetric.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(KpiMetric.id)).where(KpiMetric.tenant_id == auth.tenant_id)
    if category:
        stmt = stmt.where(KpiMetric.category == category)
        count_stmt = count_stmt.where(KpiMetric.category == category)
    if facility_id:
        stmt = stmt.where(KpiMetric.facility_id == facility_id)
        count_stmt = count_stmt.where(KpiMetric.facility_id == facility_id)
    if date_from:
        stmt = stmt.where(KpiMetric.period_start >= date_from)
        count_stmt = count_stmt.where(KpiMetric.period_start >= date_from)
    if date_to:
        stmt = stmt.where(KpiMetric.period_end <= date_to)
        count_stmt = count_stmt.where(KpiMetric.period_end <= date_to)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(KpiMetric.period_start.desc())
    result = await session.execute(stmt)
    metrics = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return kpi_schema.KpiMetricListResponse(items=[kpi_schema.KpiMetricResponse.model_validate(m) for m in metrics], total=total, page=page, page_size=page_size, total_pages=total_pages)
