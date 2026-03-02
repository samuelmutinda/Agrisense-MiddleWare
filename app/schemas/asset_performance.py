"""Pydantic schemas for AssetPerformance resource."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    REFRIGERATION_UNIT = "refrigeration_unit"
    COLD_ROOM = "cold_room"
    REEFER_TRUCK = "reefer_truck"
    CONVEYOR = "conveyor"
    PACKAGING_MACHINE = "packaging_machine"
    FORKLIFT = "forklift"


class PerformanceStatus(str, Enum):
    OPTIMAL = "optimal"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class AssetPerformanceCreate(BaseModel):
    asset_id: uuid.UUID
    asset_type: AssetType
    asset_name: str = Field(..., max_length=100)
    uptime_percent: float = Field(..., ge=0, le=100)
    efficiency_score: float = Field(..., ge=0, le=100)
    performance_status: PerformanceStatus
    measurement_timestamp: datetime
    energy_consumption_kwh: Optional[float] = None
    operating_hours: Optional[float] = None
    error_count: int = 0
    last_maintenance: Optional[datetime] = None
    metadata: Optional[dict] = None


class AssetPerformanceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    asset_id: uuid.UUID
    asset_type: AssetType
    asset_name: str
    uptime_percent: float
    efficiency_score: float
    performance_status: PerformanceStatus
    measurement_timestamp: datetime
    energy_consumption_kwh: Optional[float] = None
    operating_hours: Optional[float] = None
    error_count: int
    last_maintenance: Optional[datetime] = None
    metadata: Optional[dict] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class AssetPerformanceListResponse(BaseModel):
    items: list[AssetPerformanceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
