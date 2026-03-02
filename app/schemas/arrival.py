from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models.harvest_inventory_ledger import EventType


class ArrivalCreate(BaseModel):
    customer_id: uuid.UUID
    crop_id: uuid.UUID
    inspected_by_user_id: uuid.UUID
    harvested_at: datetime
    quantity: float = Field(..., gt=0, description="Quantity units added to inventory")
    volume: float = Field(..., gt=0, description="Volume added in liters")
    expected_storage_hrs: Optional[float] = Field(None, gt=0, description="Expected storage duration in hours")
    notes: Optional[str] = None


class ArrivalResponse(BaseModel):
    id: uuid.UUID
    event_type: EventType
    cold_storage_unit_id: uuid.UUID
    crop_id: uuid.UUID
    inspected_by_user_id: uuid.UUID
    arrived_at: datetime
    harvested_at: datetime
    quantity: float
    volume: float
    expected_storage_hrs: Optional[float] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}

