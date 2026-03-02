from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db import models
from app.schemas import transfer as transfer_schema
from app.db.models.harvest_inventory_ledger import EventType
from app.db.models.harvest_transfer import TransferStatus
from app.ws.events import build_transfer_event
from app.ws.manager import manager
from app.services.helpers import (
    map_to_response,
    get_ledger,
    get_and_validate_transfer
)


async def get_transfers_with_ledger(
        session: AsyncSession,
        tenant_id: uuid.UUID
) -> list[transfer_schema.TransferResponse]:
    stmt = (
        select(models.HarvestTransfer, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestTransfer.id
        )
        .join(
            models.HarvestArrival,
            models.HarvestArrival.id == models.HarvestTransfer.intake_id
        )
        .where(
            models.HarvestArrival.tenant_id == tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.TRANSFER_OUT
        )
        .order_by(models.HarvestTransfer.initiated_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    return [
        map_to_response(transfer_schema.TransferResponse, transfer, ledger)
        for transfer, ledger in rows
    ]


async def get_transfer_by_id(
        session: AsyncSession,
        transfer_id: uuid.UUID,
        tenant_id: uuid.UUID
) -> transfer_schema.TransferResponse:
    stmt = (
        select(models.HarvestTransfer, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestTransfer.id
        )
        .join(
            models.HarvestArrival,
            models.HarvestArrival.id == models.HarvestTransfer.intake_id
        )
        .where(
            models.HarvestTransfer.id == transfer_id,
            models.HarvestArrival.tenant_id == tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.TRANSFER_OUT
        )
    )
    result = await session.execute(stmt)
    row = result.one_or_none()

    if not row:
        raise ValueError(f"Transfer with id {transfer_id} not found or access denied.")

    transfer, ledger = row
    return map_to_response(transfer_schema.TransferResponse, transfer, ledger)


async def initiate_transfer(
        session: AsyncSession, data: transfer_schema.TransferCreate, auth: AuthContext
) -> transfer_schema.TransferResponse:
    transfer = models.HarvestTransfer(
        intake_id=data.intake_id,
        from_cs_id=data.from_cs_id,
        to_cs_id=data.to_cs_id,
        initiated_by_user_id=auth.user_id,
        status=TransferStatus.IN_TRANSIT,
        notes=data.notes,
    )
    session.add(transfer)
    await session.flush()

    ledger = models.HarvestInventoryLedger(
        executed_by_user_id=auth.user_id,
        event_id=transfer.id,
        cold_storage_unit_id=data.from_cs_id,
        quantity_delta=-data.quantity,
        volume_delta=-data.volume,
        event_type=EventType.TRANSFER_OUT,
    )
    session.add(ledger)

    await session.commit()
    await session.refresh(transfer)

    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload=build_transfer_event(transfer, data.quantity, data.volume),
    )

    return map_to_response(transfer_schema.TransferResponse, transfer, ledger)


async def cancel_transfer(
        session: AsyncSession, transfer_id: uuid.UUID, auth: AuthContext
) -> transfer_schema.TransferResponse:
    transfer = await get_and_validate_transfer(session, transfer_id)
    original_ledger = await get_ledger(session, transfer_id, EventType.TRANSFER_OUT)

    quantity = abs(original_ledger.quantity_delta)
    volume = abs(original_ledger.volume_delta)

    transfer.status = TransferStatus.CANCELED
    transfer.closed_at = datetime.utcnow()
    transfer.closed_by_user_id = auth.user_id

    cancel_ledger = models.HarvestInventoryLedger(
        executed_by_user_id=auth.user_id,
        event_id=transfer.id,
        cold_storage_unit_id=original_ledger.cold_storage_unit_id,
        quantity_delta=quantity,
        volume_delta=volume,
        event_type=EventType.TRANSFER_CANCEL,
    )
    session.add(cancel_ledger)

    await session.commit()
    await session.refresh(transfer)

    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload=build_transfer_event(transfer, quantity, volume),
    )

    return map_to_response(transfer_schema.TransferResponse, transfer, cancel_ledger)


async def complete_transfer(
        session: AsyncSession, transfer_id: uuid.UUID, auth: AuthContext
) -> transfer_schema.TransferResponse:
    transfer = await get_and_validate_transfer(session, transfer_id)
    original_ledger = await get_ledger(session, transfer_id, EventType.TRANSFER_OUT)

    quantity = abs(original_ledger.quantity_delta)
    volume = abs(original_ledger.volume_delta)

    transfer.status = TransferStatus.COMPLETED
    transfer.closed_at = datetime.utcnow()
    transfer.closed_by_user_id = auth.user_id

    complete_ledger = models.HarvestInventoryLedger(
        executed_by_user_id=auth.user_id,
        event_id=transfer.id,
        cold_storage_unit_id=transfer.to_cs_id,
        quantity_delta=quantity,
        volume_delta=volume,
        event_type=EventType.TRANSFER_IN
    )
    session.add(complete_ledger)

    await session.commit()
    await session.refresh(transfer)

    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload=build_transfer_event(transfer, quantity, volume),
    )

    return map_to_response(transfer_schema.TransferResponse, transfer, complete_ledger)