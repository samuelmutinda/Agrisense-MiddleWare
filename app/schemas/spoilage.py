from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from app.db.models.harvest_spoilage import SpoilageReason
from app.db.models.harvest_inventory_ledger import EventType


class SpoilageCreate(BaseModel):
    intake_id: uuid.UUID
    reported_by_user_id: uuid.UUID
    cold_storage_unit_id: uuid.UUID

    detected_at: datetime
    spoilage_reason: SpoilageReason = Field(..., description="Reason for spoilage: ")
    notes: str = Field(..., description="Notes about the spoilage")
    quantity: float = Field(..., gt=0, description="Quantity units spoilt")
    volume: float = Field(..., gt=0, description="Volume spoilt in Liters")

class SpoilageResponse(BaseModel):
    id: uuid.UUID
    event_type: EventType
    cold_storage_unit_id: uuid.UUID
    intake_id: uuid.UUID
    reported_by_user_id: uuid.UUID
    spoilage_reason: SpoilageReason
    detected_at: datetime
    quantity: float
    volume: float
    notes: str

    model_config = {"from_attributes": True}

