from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.schemas import inventory as inventory_schema
from app.db.models.harvest_inventory_ledger import EventType


async def get_intake_balance(
        session: AsyncSession,
        intake_id: uuid.UUID,
        tenant_id: uuid.UUID,
        cold_storage_unit_id: Optional[uuid.UUID] = None,
) -> int:
    # We join the ledger to the arrival through the event_id (for the initial arrival)
    # or subsequent events that reference that specific intake.
    stmt = (
        select(func.coalesce(func.sum(models.HarvestInventoryLedger.quantity_delta), 0))
        .join(
            models.HarvestArrival,
            models.HarvestArrival.id == intake_id
        )
        # We need to filter ledger entries that belong to this intake.
        # Since ledger entries can be Arrivals, Collections, or Transfers,
        # the business logic assumes ledger.event_id links to the specific event.
        # For a specific intake balance, we look for ledger rows where the
        # associated event (Arrival, Collection, Transfer, Loss) points to this intake_id.
    )

    # Logic: Sum all ledger entries where the underlying event belongs to this intake
    # Note: This query structure assumes your ledger/event tables are linked properly.
    # A robust way is to union or filter by events that reference intake_id.

    # Simplified approach based on your current schema:
    # Filter by events that are "Arrivals" for this ID OR "Collections/Transfers" referencing it.

    # This specific query assumes you have a way to link ledger rows to an intake_id.
    # If the ledger doesn't have intake_id, we filter by events.

    # Base query
    stmt = select(func.coalesce(func.sum(models.HarvestInventoryLedger.quantity_delta), 0))

    # Subquery to get all event IDs (Arrivals, Collections, Transfers) related to this intake
    arrival_stmt = select(models.HarvestArrival.id).where(models.HarvestArrival.id == intake_id,
                                                          models.HarvestArrival.tenant_id == tenant_id)
    collection_stmt = select(models.HarvestCollection.id).where(models.HarvestCollection.intake_id == intake_id)
    transfer_stmt = select(models.HarvestTransfer.id).where(models.HarvestTransfer.intake_id == intake_id)
    loss_stmt = select(models.HarvestLoss.id).where(models.HarvestLoss.intake_id == intake_id)
    spoilage_stmt = select(models.HarvestSpoilage.id).where(models.HarvestSpoilage.intake_id == intake_id)

    # Combine these event IDs
    event_ids = (await session.execute(arrival_stmt)).scalars().all()
    event_ids.extend((await session.execute(collection_stmt)).scalars().all())
    event_ids.extend((await session.execute(transfer_stmt)).scalars().all())
    event_ids.extend((await session.execute(loss_stmt)).scalars().all())
    event_ids.extend((await session.execute(spoilage_stmt)).scalars().all())

    stmt = stmt.where(models.HarvestInventoryLedger.event_id.in_(event_ids))

    if cold_storage_unit_id:
        stmt = stmt.where(
            models.HarvestInventoryLedger.cold_storage_unit_id == cold_storage_unit_id
        )

    result = await session.execute(stmt)
    return int(result.scalar() or 0)


async def get_current_inventory(
        session: AsyncSession, tenant_id: uuid.UUID
) -> List[inventory_schema.InventoryPosition]:
    # This query groups current quantity by intake and storage unit
    # It requires joining the ledger back to the original Arrival to get crop/customer info

    # We use a subquery or join to Arrivals because every inventory trace starts with an Arrival.
    # For Transfers and Collections, we still want to know which 'Intake' they belong to.

    # Note: For this to be performant, your Ledger should ideally have an 'intake_id' column.
    # If it doesn't, we must join through the event tables.

    stmt = (
        select(
            models.HarvestArrival.id.label("intake_id"),
            models.HarvestArrival.customer_id,
            models.HarvestArrival.crop_id,
            models.HarvestInventoryLedger.cold_storage_unit_id,
            func.sum(models.HarvestInventoryLedger.quantity_delta).label("quantity"),
        )
        .join(models.HarvestInventoryLedger,
              (models.HarvestInventoryLedger.event_id == models.HarvestArrival.id) |  # Direct Arrival
              (models.HarvestInventoryLedger.event_id.in_(select(models.HarvestCollection.id).where(
                  models.HarvestCollection.intake_id == models.HarvestArrival.id))) |  # Collections
              (models.HarvestInventoryLedger.event_id.in_(select(models.HarvestTransfer.id).where(
                  models.HarvestTransfer.intake_id == models.HarvestArrival.id)))  # Transfers
              )
        .where(models.HarvestArrival.tenant_id == tenant_id)
        .group_by(
            models.HarvestArrival.id,
            models.HarvestArrival.customer_id,
            models.HarvestArrival.crop_id,
            models.HarvestInventoryLedger.cold_storage_unit_id,
        )
        .having(func.sum(models.HarvestInventoryLedger.quantity_delta) > 0)
    )

    result = await session.execute(stmt)
    rows = result.all()
    return [
        inventory_schema.InventoryPosition(
            intake_id=row.intake_id,
            crop_id=row.crop_id,
            customer_id=row.customer_id,
            cold_storage_unit_id=row.cold_storage_unit_id,
            quantity=int(row.quantity),
        )
        for row in rows
    ]


async def get_inventory_summary(
        session: AsyncSession, tenant_id: uuid.UUID
) -> inventory_schema.InventorySummary:
    # Summary of total quantity per storage unit across all intakes for the tenant
    stmt = (
        select(
            models.HarvestInventoryLedger.cold_storage_unit_id,
            func.sum(models.HarvestInventoryLedger.quantity_delta).label("quantity"),
        )
        .join(models.HarvestArrival, models.HarvestArrival.tenant_id == tenant_id)
        # We join to filter by tenant, ensuring we only sum ledger entries related to this tenant's arrivals
        .where(
            (models.HarvestInventoryLedger.event_id == models.HarvestArrival.id) |
            (models.HarvestInventoryLedger.event_id.in_(select(models.HarvestCollection.id).where(
                models.HarvestCollection.intake_id == models.HarvestArrival.id)))
        )
        .group_by(models.HarvestInventoryLedger.cold_storage_unit_id)
    )

    result = await session.execute(stmt)
    rows = result.all()
    by_storage = [
        inventory_schema.InventoryByStorage(
            cold_storage_unit_id=row.cold_storage_unit_id, quantity=int(row.quantity)
        )
        for row in rows
    ]
    total_quantity = sum(item.quantity for item in by_storage)
    return inventory_schema.InventorySummary(
        total_quantity=total_quantity, by_storage=by_storage
    )