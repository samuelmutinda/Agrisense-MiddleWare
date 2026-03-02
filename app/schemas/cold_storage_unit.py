from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ColdStorageUnitCreate(BaseModel):
    name: str
    latitude: float = Field(..., description="Latitude of the unit location")
    longitude: float = Field(..., description="Longitude of the unit location")
    capacity_volume: float = Field(..., gt=0, description="Storage capacity in liters")
    is_active: bool = True


class ColdStorageUnitResponse(BaseModel):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    capacity_volume: float
    is_active: bool

    model_config = {"from_attributes": True}
