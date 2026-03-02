from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.schemas import cold_storage_unit as cold_storage_unit_schema
from app.services.helpers import get_or_404


async def get_cold_storage_units(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[cold_storage_unit_schema.ColdStorageUnitResponse]:
    stmt = (
        select(models.ColdStorageUnit)
        .where(models.ColdStorageUnit.tenant_id == tenant_id)
        .order_by(models.ColdStorageUnit.name.asc())
    )
    result = await session.execute(stmt)
    units = result.scalars().all()
    return [cold_storage_unit_schema.ColdStorageUnitResponse.model_validate(u) for u in units]


async def get_cold_storage_unit_by_id(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> cold_storage_unit_schema.ColdStorageUnitResponse:
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    return cold_storage_unit_schema.ColdStorageUnitResponse.model_validate(unit)


async def create_cold_storage_unit(
    session: AsyncSession,
    data: cold_storage_unit_schema.ColdStorageUnitCreate,
    tenant_id: uuid.UUID,
) -> cold_storage_unit_schema.ColdStorageUnitResponse:
    unit = models.ColdStorageUnit(
        tenant_id=tenant_id,
        **data.model_dump(),
    )
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return cold_storage_unit_schema.ColdStorageUnitResponse.model_validate(unit)


async def update_cold_storage_unit(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    data: cold_storage_unit_schema.ColdStorageUnitCreate,
    tenant_id: uuid.UUID,
) -> cold_storage_unit_schema.ColdStorageUnitResponse:
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    unit.name = data.name
    unit.latitude = data.latitude
    unit.longitude = data.longitude
    unit.capacity_volume = data.capacity_volume
    unit.is_active = data.is_active
    await session.commit()
    await session.refresh(unit)
    return cold_storage_unit_schema.ColdStorageUnitResponse.model_validate(unit)


async def delete_cold_storage_unit(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    await session.delete(unit)
    await session.commit()
