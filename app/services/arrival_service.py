from __future__ import annotations
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db import models
from app.schemas import arrival as arrival_schema
from app.ws.events import build_arrival_event
from app.ws.manager import manager
from app.db.models.harvest_inventory_ledger import EventType
from app.services.helpers import map_to_response  # Import the new helper

async def get_arrivals_with_ledger(
    session: AsyncSession,
    auth: AuthContext
) -> list[arrival_schema.ArrivalResponse]:
    stmt = (
        select(models.HarvestArrival, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestArrival.id
        )
        .where(
            models.HarvestArrival.tenant_id == auth.tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.ARRIVAL
        )
        .order_by(models.HarvestArrival.arrived_at.desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        map_to_response(arrival_schema.ArrivalResponse, arrival_obj, ledger_obj)
        for arrival_obj, ledger_obj in rows
    ]

async def get_arrival_by_id(
    session: AsyncSession,
    arrival_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> arrival_schema.ArrivalResponse:
    stmt = (
        select(models.HarvestArrival, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestArrival.id
        )
        .where(
            models.HarvestArrival.id == arrival_id,
            models.HarvestArrival.tenant_id == tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.ARRIVAL
        )
    )

    result = await session.execute(stmt)
    row = result.one_or_none()

    if not row:
        raise ValueError(f"Arrival with id {arrival_id} not found or access denied.")

    arrival, ledger = row
    return map_to_response(arrival_schema.ArrivalResponse, arrival, ledger)

async def create_arrival(
    session: AsyncSession, data: arrival_schema.ArrivalCreate, auth: AuthContext
) -> arrival_schema.ArrivalResponse:
    arrival = models.HarvestArrival(
        tenant_id=auth.tenant_id,
        customer_id=data.customer_id,
        crop_id=data.crop_id,
        inspected_by_user_id=data.inspected_by_user_id,
        harvested_at=data.harvested_at,
        quantity=data.quantity,
        volume=data.volume,
        expected_storage_hrs=data.expected_storage_hrs,
        notes=data.notes,
    )
    session.add(arrival)
    await session.flush()

    ledger = models.HarvestInventoryLedger(
        executed_by_user_id=auth.user_id,
        event_id=arrival.id,
        cold_storage_unit_id=data.cold_storage_unit_id,
        quantity_delta=data.quantity,  # Positive for arrivals
        volume_delta=data.volume,
        event_type=EventType.ARRIVAL,
    )
    session.add(ledger)
    await session.commit()
    await session.refresh(arrival)

    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload=build_arrival_event(arrival, data.quantity, data.volume, data.cold_storage_unit_id),
        customer_id=str(data.customer_id),
    )

    return map_to_response(arrival_schema.ArrivalResponse, arrival, ledger)