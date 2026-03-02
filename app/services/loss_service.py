from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.db.models.harvest_loss import OccurredDuring
from app.db.models.harvest_inventory_ledger import EventType
from app.db.models.harvest_transfer import TransferStatus
from app.core.security import AuthContext
from app.db import models
from app.schemas import loss as loss_schema
from app.ws.events import build_loss_event
from app.ws.manager import manager
from app.services.helpers import get_and_validate_transfer, get_ledger, map_to_response


async def get_losses_with_ledger(
        session: AsyncSession,
        tenant_id: uuid.UUID
) -> list[loss_schema.LossResponse]:
    loss_ledger = aliased(models.HarvestInventoryLedger)
    transfer_ledger = aliased(models.HarvestInventoryLedger)

    stmt = (
        select(models.HarvestLoss, loss_ledger, transfer_ledger)
        .join(loss_ledger, loss_ledger.event_id == models.HarvestLoss.id)
        .join(models.HarvestArrival, models.HarvestArrival.id == models.HarvestLoss.intake_id)
        .outerjoin(
            transfer_ledger,
            (transfer_ledger.event_id == models.HarvestLoss.transfer_id) &
            (transfer_ledger.event_type == EventType.TRANSFER_OUT)
        )
        .where(
            models.HarvestArrival.tenant_id == tenant_id,
            loss_ledger.event_type == EventType.LOSS
        )
        .order_by(models.HarvestLoss.occurred_at.desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    losses = []
    for loss, l_ledger, t_ledger in rows:
        if loss.occurred_during == OccurredDuring.TRANSIT and t_ledger:
            qty, vol = abs(t_ledger.quantity_delta), abs(t_ledger.volume_delta)
        else:
            qty, vol = abs(l_ledger.quantity_delta), abs(l_ledger.volume_delta)

        losses.append(
            map_to_response(loss_schema.LossResponse, loss, l_ledger, quantity=qty, volume=vol)
        )

    return losses


async def get_loss_by_id(
    session: AsyncSession,
    loss_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> loss_schema.LossResponse:
    stmt = (
        select(models.HarvestLoss, models.HarvestInventoryLedger)
        .join(
            models.HarvestInventoryLedger,
            models.HarvestInventoryLedger.event_id == models.HarvestLoss.id
        )
        .join(models.HarvestArrival, models.HarvestArrival.id == models.HarvestLoss.intake_id)
        .where(
            models.HarvestLoss.id == loss_id,
            models.HarvestArrival.tenant_id == tenant_id,
            models.HarvestInventoryLedger.event_type == EventType.LOSS
        )
    )

    result = await session.execute(stmt)
    row = result.one_or_none()

    if not row:
        raise ValueError(f"Loss with id {loss_id} not found or access denied.")

    loss, loss_ledger = row

    qty, vol = abs(loss_ledger.quantity_delta), abs(loss_ledger.volume_delta)
    if loss.occurred_during == OccurredDuring.TRANSIT and loss.transfer_id:
        t_ledger = await get_ledger(session, loss.transfer_id, EventType.TRANSFER_OUT)
        qty, vol = abs(t_ledger.quantity_delta), abs(t_ledger.volume_delta)

    return map_to_response(loss_schema.LossResponse, loss, loss_ledger, quantity=qty, volume=vol)


async def record_transfer_loss(
        session: AsyncSession,
        data: loss_schema.TransferLossCreate,
        auth: AuthContext,
) -> loss_schema.LossResponse:
    loss = models.HarvestLoss(
        intake_id=data.intake_id,
        reported_by_user_id=auth.user_id,
        transfer_id=data.transfer_id,
        occurred_at=data.occurred_at,
        occurred_during=OccurredDuring.TRANSIT,
        loss_reason=data.loss_reason,
        notes=data.notes,
    )
    session.add(loss)

    original_transfer = await get_and_validate_transfer(session, loss.transfer_id)
    original_ledger = await get_ledger(session, loss.transfer_id, EventType.TRANSFER_OUT)

    original_transfer.status = TransferStatus.LOST
    original_transfer.closed_by_user_id = auth.user_id
    original_transfer.closed_at = datetime.utcnow()

    loss_ledger = models.HarvestInventoryLedger(
        executed_by_user_id=auth.user_id,
        event_id=loss.id,
        cold_storage_unit_id=original_transfer.from_cs_id,
        quantity_delta=0,
        volume_delta=0,
        event_type=EventType.LOSS,
    )
    session.add(loss_ledger)

    await session.commit()
    await session.refresh(loss)

    qty_val, vol_val = abs(original_ledger.quantity_delta), abs(original_ledger.volume_delta)
    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload=build_loss_event(loss, qty_val, vol_val),
    )

    return map_to_response(loss_schema.LossResponse, loss, loss_ledger, quantity=qty_val, volume=vol_val)


async def record_storage_loss(
        session: AsyncSession,
        data: loss_schema.StorageLossCreate,
        auth: AuthContext,
) -> loss_schema.LossResponse:
    loss = models.HarvestLoss(
        intake_id=data.intake_id,
        reported_by_user_id=auth.user_id,
        occurred_at=data.occurred_at,
        occurred_during=OccurredDuring.STORAGE,
        loss_reason=data.loss_reason,
        notes=data.notes,
    )
    session.add(loss)

    loss_ledger = models.HarvestInventoryLedger(
        executed_by_user_id=auth.user_id,
        event_id=loss.id,
        cold_storage_unit_id=data.cold_storage_unit_id,
        quantity_delta=-data.quantity,
        volume_delta=-data.volume,
        event_type=EventType.LOSS,
    )

    session.add(loss_ledger)
    await session.commit()
    await session.refresh(loss)

    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload=build_loss_event(loss, data.quantity, data.volume),
    )

    return map_to_response(loss_schema.LossResponse, loss, loss_ledger)