from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db import models
from app.schemas import spoilage as spoilage_schema
from app.ws.events import build_spoilage_event
from app.ws.manager import manager

from app.db.models.harvest_inventory_ledger import EventType
from app.services.helpers import map_to_response

async def get_spoilages_with_ledger(
        session: AsyncSession,
        tenant_id: uuid.UUID
) -> list[spoilage_schema.SpoilageResponse]:
    stmt = (
        select(models.HarvestSpoilage, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestSpoilage.id
        )
        .join(
            models.HarvestArrival,
            models.HarvestArrival.id == models.HarvestSpoilage.intake_id
        )
        .where(
            models.HarvestArrival.tenant_id == tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.SPOILAGE
        )
        .order_by(models.HarvestSpoilage.detected_at.desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        map_to_response(spoilage_schema.SpoilageResponse, spoilage, ledger)
        for spoilage, ledger in rows
    ]


async def get_spoilage_by_id(
    session: AsyncSession,
    spoilage_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> spoilage_schema.SpoilageResponse:
    stmt = (
        select(models.HarvestSpoilage, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestSpoilage.id
        )
        .join(
            models.HarvestArrival,
            models.HarvestArrival.id == models.HarvestSpoilage.intake_id
        )
        .where(
            models.HarvestSpoilage.id == spoilage_id,
            models.HarvestArrival.tenant_id == tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.SPOILAGE
        )
    )

    result = await session.execute(stmt)
    row = result.one_or_none()

    if not row:
        raise ValueError(f"Spoilage with id {spoilage_id} not found or access denied.")

    spoilage, ledger = row
    return map_to_response(spoilage_schema.SpoilageResponse, spoilage, ledger)


async def record_spoilage(
    session: AsyncSession, data: spoilage_schema.SpoilageCreate, auth: AuthContext
) -> spoilage_schema.SpoilageResponse:
    spoilage = models.HarvestSpoilage(
        intake_id=data.intake_id,
        reported_by_user_id=data.reported_by_user_id,
        spoilage_reason=data.spoilage_reason,
        detected_at=data.detected_at,
        notes=data.notes,
    )
    session.add(spoilage)
    await session.flush()

    ledger = models.HarvestInventoryLedger(
        event_id=spoilage.id,
        executed_by_user_id=auth.user_id,
        cold_storage_unit_id=data.cold_storage_unit_id,
        quantity_delta=-data.quantity,
        volume_delta=-data.volume,
        event_type=EventType.SPOILAGE,
    )
    session.add(ledger)
    await session.commit()
    await session.refresh(spoilage)

    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload=build_spoilage_event(spoilage, data.quantity, data.volume, data.cold_storage_unit_id),
    )

    return map_to_response(spoilage_schema.SpoilageResponse, spoilage, ledger)