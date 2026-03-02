from __future__ import annotations

import uuid
from typing import Type, TypeVar, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.base import Base
from app.db.models.harvest_inventory_ledger import EventType
from app.db.models.harvest_transfer import TransferStatus

ModelT = TypeVar("ModelT", bound=Base)

async def get_or_404(
    session: AsyncSession,
    model: Type[ModelT],
    obj_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = None,
) -> ModelT:
    stmt = select(model).where(model.id == obj_id)
    if tenant_id and hasattr(model, "tenant_id"):
        stmt = stmt.where(model.tenant_id == tenant_id)

    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()

    if not obj:
        raise ValueError(f"{model.__name__} with id {obj_id} not found.")

    return obj

async def get_event_by_id_secured(
    session: AsyncSession,
    model: Type[ModelT],
    obj_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> ModelT:
    stmt = (
        select(model)
        .join(models.HarvestArrival, models.HarvestArrival.id == model.intake_id)
        .where(
            model.id == obj_id,
            models.HarvestArrival.tenant_id == tenant_id
        )
    )
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        raise ValueError(f"{model.__name__} not found or access denied.")
    return obj

async def get_and_validate_transfer(
    session: AsyncSession,
    transfer_id: uuid.UUID
) -> models.HarvestTransfer:
    transfer = await get_or_404(session, models.HarvestTransfer, transfer_id)

    if transfer.status != TransferStatus.IN_TRANSIT:
        raise ValueError(
            f"Transfer {transfer_id} is not in transit (status: {transfer.status.value})"
        )

    return transfer

async def get_ledger(
    session: AsyncSession,
    event_id: uuid.UUID,
    event_type: EventType
) -> models.HarvestInventoryLedger:
    stmt = (
        select(models.HarvestInventoryLedger)
        .where(
            models.HarvestInventoryLedger.event_id == event_id,
            models.HarvestInventoryLedger.event_type == event_type
        )
        .order_by(models.HarvestInventoryLedger.recorded_at.desc())
    )

    result = await session.execute(stmt)
    ledger = result.scalar_one_or_none()

    if not ledger:
        raise ValueError(f"Ledger entry for event {event_id} ({event_type.value}) not found.")

    return ledger


from typing import Type, TypeVar, Any
from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


def map_to_response(
        schema: Type[ResponseT],
        event: Any,
        ledger: Any,
        **extra_fields: Any
) -> ResponseT:
    data = {k: v for k, v in vars(event).items() if k != "_sa_instance_state"}

    ledger_data = {
        "event_type": ledger.event_type,
        "cold_storage_unit_id": ledger.cold_storage_unit_id,
        "quantity": abs(ledger.quantity_delta) if ledger.quantity_delta is not None else 0,
        "volume": abs(ledger.volume_delta) if ledger.volume_delta is not None else 0,
    }

    return schema(**{**data, **ledger_data, **extra_fields})