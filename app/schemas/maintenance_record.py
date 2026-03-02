"""Pydantic schemas for MaintenanceRecord resource."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MaintenanceType(str, Enum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    EMERGENCY = "emergency"
    CALIBRATION = "calibration"


class MaintenanceStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenancePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MaintenanceRecordCreate(BaseModel):
    asset_id: uuid.UUID
    asset_type: str = Field(..., max_length=50)
    asset_name: str = Field(..., max_length=100)
    maintenance_type: MaintenanceType
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    scheduled_date: datetime
    description: str = Field(..., max_length=500)
    assigned_technician_id: Optional[uuid.UUID] = None
    estimated_duration_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    parts_required: Optional[list[str]] = None
    metadata: Optional[dict] = None


class MaintenanceRecordUpdate(BaseModel):
    status: Optional[MaintenanceStatus] = None
    priority: Optional[MaintenancePriority] = None
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    actual_duration_hours: Optional[float] = None
    actual_cost: Optional[float] = None
    notes: Optional[str] = None
    parts_used: Optional[list[str]] = None


class MaintenanceRecordResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    asset_id: uuid.UUID
    asset_type: str
    asset_name: str
    maintenance_type: MaintenanceType
    status: MaintenanceStatus
    priority: MaintenancePriority
    scheduled_date: datetime
    completed_date: Optional[datetime] = None
    description: str
    assigned_technician_id: Optional[uuid.UUID] = None
    assigned_technician_name: Optional[str] = None
    estimated_duration_hours: Optional[float] = None
    actual_duration_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    parts_required: Optional[list[str]] = None
    parts_used: Optional[list[str]] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class MaintenanceRecordListResponse(BaseModel):
    items: list[MaintenanceRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
