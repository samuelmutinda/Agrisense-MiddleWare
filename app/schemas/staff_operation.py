"""Pydantic schemas for StaffOperation resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    SHIFT = "shift"
    TASK = "task"
    TRAINING = "training"
    OVERTIME = "overtime"


class ShiftType(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"
    ROTATING = "rotating"


class StaffOperationCreate(BaseModel):
    staff_id: uuid.UUID
    operation_type: OperationType
    facility_id: Optional[uuid.UUID] = None
    shift_type: Optional[ShiftType] = None
    operation_date: date
    start_time: datetime
    end_time: Optional[datetime] = None
    task_description: Optional[str] = Field(None, max_length=500)
    area_assigned: Optional[str] = Field(None, max_length=100)
    supervisor_id: Optional[uuid.UUID] = None
    metadata: Optional[dict] = None


class StaffOperationUpdate(BaseModel):
    end_time: Optional[datetime] = None
    task_description: Optional[str] = Field(None, max_length=500)
    performance_notes: Optional[str] = Field(None, max_length=500)
    productivity_score: Optional[float] = Field(None, ge=0, le=100)


class StaffOperationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    staff_id: uuid.UUID
    staff_name: Optional[str] = None
    operation_type: OperationType
    facility_id: Optional[uuid.UUID] = None
    facility_name: Optional[str] = None
    shift_type: Optional[ShiftType] = None
    operation_date: date
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_hours: Optional[float] = None
    task_description: Optional[str] = None
    area_assigned: Optional[str] = None
    supervisor_id: Optional[uuid.UUID] = None
    supervisor_name: Optional[str] = None
    performance_notes: Optional[str] = None
    productivity_score: Optional[float] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class StaffOperationListResponse(BaseModel):
    items: list[StaffOperationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    total_hours: Optional[float] = None
