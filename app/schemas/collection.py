from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from app.db.models.harvest_inventory_ledger import EventType


class CollectionCreate(BaseModel):
    intake_id: uuid.UUID
    handled_by_user_id: uuid.UUID
    notes: str = Field(..., description="Notes about the collection")
    cold_storage_unit_id: uuid.UUID
    quantity: float = Field(..., gt=0, description="quantity units collected")
    volume: float = Field(..., gt=0, description="volume collected in liters")


class CollectionResponse(BaseModel):
    id: uuid.UUID
    event_type: EventType
    cold_storage_unit_id: uuid.UUID
    intake_id: uuid.UUID
    handled_by_user_id: uuid.UUID
    collected_at: datetime
    quantity: float
    volume: float
    notes: str

    model_config = {"from_attributes": True}

