from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, Field, AfterValidator
from app.db.models.harvest_loss import OccurredDuring, LossReason
from app.db.models.harvest_inventory_ledger import EventType

def validate_past_date(v: datetime) -> datetime:
    if v > datetime.utcnow():
        raise ValueError("Date cannot be in the future")
    return v

PastDatetime = Annotated[datetime, AfterValidator(validate_past_date)]

class LossBase(BaseModel):
    intake_id: uuid.UUID
    occurred_at: PastDatetime
    loss_reason: LossReason
    notes: str

class StorageLossCreate(LossBase):
    quantity: float = Field(..., gt=0)
    volume: float = Field(..., gt=0)
    cold_storage_unit_id: uuid.UUID

class TransferLossCreate(LossBase):
    transfer_id: uuid.UUID

class LossResponse(BaseModel):
    id: uuid.UUID
    intake_id: uuid.UUID
    event_type: EventType
    quantity: float
    volume: float
    reported_by_user_id: uuid.UUID
    occurred_during: OccurredDuring
    transfer_id: Optional[uuid.UUID] = None
    cold_storage_unit_id: Optional[uuid.UUID] = None
    occurred_at: datetime
    loss_reason: LossReason
    notes: str

    model_config = {"from_attributes": True}

