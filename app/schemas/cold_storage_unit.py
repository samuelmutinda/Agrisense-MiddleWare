from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

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


class FacilitySupervisorAssignmentCreate(BaseModel):
    supervisor_id: uuid.UUID
    notes: Optional[str] = Field(default=None, max_length=500)


class FacilitySupervisorAssignmentResponse(BaseModel):
    assignment_id: uuid.UUID
    facility_id: uuid.UUID
    supervisor_id: uuid.UUID
    supervisor_name: str
    assigned_at: datetime
    assigned_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class FacilitySupervisorAssignmentListResponse(BaseModel):
    items: list[FacilitySupervisorAssignmentResponse]
    total: int
