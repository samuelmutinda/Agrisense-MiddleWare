from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from app.db.models.harvest_inventory_ledger import EventType


class TransferCreate(BaseModel):
    intake_id: uuid.UUID
    from_cs_id: uuid.UUID
    to_cs_id: uuid.UUID
    notes: Optional[str] = None
    quantity: float = Field(..., gt=0, description="Quantity units to transfer")
    volume: float = Field(..., gt=0, description="Volume to transfer in liters")

class TransferResponse(BaseModel):
    id: uuid.UUID
    intake_id: uuid.UUID
    event_type: EventType
    from_cs_id: uuid.UUID
    to_cs_id: uuid.UUID
    initiated_by_user_id: uuid.UUID
    closed_by_user_id: Optional[uuid.UUID] = None
    initiated_at: datetime
    closed_at: Optional[datetime] = None
    notes: Optional[str] = None
    quantity: float
    volume: float

    model_config = {"from_attributes": True}

