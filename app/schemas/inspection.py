"""Pydantic schemas for Inspection resource."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class InspectionType(str, Enum):
    ARRIVAL = "arrival"
    STORAGE = "storage"
    PRE_SHIPMENT = "pre_shipment"
    QUALITY = "quality"
    SAFETY = "safety"
    REGULATORY = "regulatory"


class InspectionResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"
    PENDING = "pending"


class InspectionCriterion(BaseModel):
    """Single inspection criterion."""
    name: str
    passed: bool
    score: Optional[float] = None
    notes: Optional[str] = None


class InspectionCreate(BaseModel):
    """Schema for creating an inspection."""
    produce_batch_id: Optional[uuid.UUID] = None
    storage_unit_id: Optional[uuid.UUID] = None
    inspection_type: InspectionType
    scheduled_date: Optional[datetime] = None
    criteria: Optional[List[InspectionCriterion]] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


class InspectionUpdate(BaseModel):
    """Schema for updating an inspection."""
    result: Optional[InspectionResult] = None
    criteria: Optional[List[InspectionCriterion]] = None
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    temperature_celsius: Optional[float] = None
    humidity_percent: Optional[float] = None
    findings: Optional[str] = None
    corrective_actions: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class InspectionResponse(BaseModel):
    """Schema for inspection response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    produce_batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    storage_unit_id: Optional[uuid.UUID] = None
    storage_unit_name: Optional[str] = None
    inspection_type: InspectionType
    result: InspectionResult
    inspector_id: uuid.UUID
    inspector_name: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    criteria: Optional[List[dict]] = None
    overall_score: Optional[float] = None
    temperature_celsius: Optional[float] = None
    humidity_percent: Optional[float] = None
    findings: Optional[str] = None
    corrective_actions: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InspectionListResponse(BaseModel):
    """Schema for paginated inspection list."""
    items: list[InspectionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
