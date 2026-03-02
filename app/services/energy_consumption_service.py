"""Service layer for EnergyConsumption operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.energy_consumption import EnergyConsumption
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.schemas import energy_consumption as energy_schema


async def create_energy_consumption(session: AsyncSession, data: energy_schema.EnergyConsumptionCreate, auth: AuthContext):
    record = EnergyConsumption(
        tenant_id=auth.tenant_id,
        facility_id=data.facility_id,
        period_date=data.period_date,
        total_kwh=data.total_kwh,
        refrigeration_kwh=data.refrigeration_kwh,
        lighting_kwh=data.lighting_kwh,
        other_kwh=data.other_kwh,
        peak_demand_kw=data.peak_demand_kw,
        energy_source=data.energy_source.value,
        cost_per_kwh=data.cost_per_kwh,
        total_cost=data.total_cost,
        carbon_footprint_kg=data.carbon_footprint_kg,
        metadata=data.metadata
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return await get_energy_consumption_by_id(session, record.id, auth)


async def get_energy_consumption_by_id(session: AsyncSession, record_id: uuid.UUID, auth: AuthContext):
    stmt = select(EnergyConsumption).where(EnergyConsumption.id == record_id, EnergyConsumption.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Energy consumption record {record_id} not found")
    response = energy_schema.EnergyConsumptionResponse.model_validate(record)
    if record.facility_id:
        facility = await session.get(ColdStorageUnit, record.facility_id)
        if facility:
            response.facility_name = facility.name
    return response


async def list_energy_consumption(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 20, facility_id: Optional[uuid.UUID] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, energy_source: Optional[str] = None):
    stmt = select(EnergyConsumption).where(EnergyConsumption.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(EnergyConsumption.id)).where(EnergyConsumption.tenant_id == auth.tenant_id)
    agg_stmt = select(func.sum(EnergyConsumption.total_kwh), func.sum(EnergyConsumption.total_cost)).where(EnergyConsumption.tenant_id == auth.tenant_id)
    if facility_id:
        stmt = stmt.where(EnergyConsumption.facility_id == facility_id)
        count_stmt = count_stmt.where(EnergyConsumption.facility_id == facility_id)
        agg_stmt = agg_stmt.where(EnergyConsumption.facility_id == facility_id)
    if date_from:
        stmt = stmt.where(EnergyConsumption.period_date >= date_from)
        count_stmt = count_stmt.where(EnergyConsumption.period_date >= date_from)
        agg_stmt = agg_stmt.where(EnergyConsumption.period_date >= date_from)
    if date_to:
        stmt = stmt.where(EnergyConsumption.period_date <= date_to)
        count_stmt = count_stmt.where(EnergyConsumption.period_date <= date_to)
        agg_stmt = agg_stmt.where(EnergyConsumption.period_date <= date_to)
    if energy_source:
        stmt = stmt.where(EnergyConsumption.energy_source == energy_source)
        count_stmt = count_stmt.where(EnergyConsumption.energy_source == energy_source)
        agg_stmt = agg_stmt.where(EnergyConsumption.energy_source == energy_source)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    agg_result = await session.execute(agg_stmt)
    agg_row = agg_result.one()
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(EnergyConsumption.period_date.desc())
    result = await session.execute(stmt)
    records = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return energy_schema.EnergyConsumptionListResponse(
        items=[energy_schema.EnergyConsumptionResponse.model_validate(r) for r in records],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
        total_kwh=agg_row[0], total_cost=agg_row[1]
    )
