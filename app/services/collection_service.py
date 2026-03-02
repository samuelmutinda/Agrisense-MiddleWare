from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import AuthContext
from app.db import models
from app.schemas import collection as collection_schema
from app.services.inventory_service import get_intake_balance
from app.db.models.harvest_inventory_ledger import EventType
from app.ws.events import build_collection_event
from app.ws.manager import manager
from app.services.helpers import map_to_response


async def get_collections_with_ledger(
        session: AsyncSession,
        tenant_id: uuid.UUID
) -> list[collection_schema.CollectionResponse]:
    stmt = (
        select(models.HarvestCollection, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestCollection.id
        )
        .join(
            models.HarvestArrival,
            models.HarvestArrival.id == models.HarvestCollection.intake_id
        )
        .where(
            models.HarvestArrival.tenant_id == tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.COLLECTION
        )
        .order_by(models.HarvestCollection.collected_at.desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        map_to_response(collection_schema.CollectionResponse, col, ledger)
        for col, ledger in rows
    ]


async def get_collection_by_id(
    session: AsyncSession,
    collection_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> collection_schema.CollectionResponse:
    stmt = (
        select(models.HarvestCollection, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestCollection.id
        )
        .join(
            models.HarvestArrival,
            models.HarvestArrival.id == models.HarvestCollection.intake_id
        )
        .where(
            models.HarvestCollection.id == collection_id,
            models.HarvestArrival.tenant_id == tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.COLLECTION
        )
    )

    result = await session.execute(stmt)
    row = result.one_or_none()

    if not row:
        raise ValueError(f"Collection with id {collection_id} not found or access denied.")

    col, ledger = row
    return map_to_response(collection_schema.CollectionResponse, col, ledger)


async def record_collection(
    session: AsyncSession, data: collection_schema.CollectionCreate, auth: AuthContext
) -> collection_schema.CollectionResponse:
    available = await get_intake_balance(
        session=session,
        intake_id=data.intake_id,
        tenant_id=auth.tenant_id,
        cold_storage_unit_id=data.cold_storage_unit_id,
    )
    if available < data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient quantity. Available: {available}, Requested: {data.quantity}"
        )

    collection = models.HarvestCollection(
        intake_id=data.intake_id,
        handled_by_user_id=data.handled_by_user_id,
        notes=data.notes
    )
    session.add(collection)
    await session.flush()

    ledger = models.HarvestInventoryLedger(
        executed_by_user_id=auth.user_id,
        event_id=collection.id,
        cold_storage_unit_id=data.cold_storage_unit_id,
        quantity_delta=-data.quantity,
        volume_delta=-data.volume,
        event_type=EventType.COLLECTION,
    )
    session.add(ledger)
    await session.commit()
    await session.refresh(collection)

    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload=build_collection_event(collection, data.quantity, data.volume, data.cold_storage_unit_id),
    )

    return map_to_response(collection_schema.CollectionResponse, collection, ledger)