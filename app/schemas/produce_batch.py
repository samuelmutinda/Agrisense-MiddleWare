"""Pydantic schemas for ProduceBatch resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class BatchStatus(str, Enum):
    PENDING = "pending"
    IN_STORAGE = "in_storage"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    REJECTED = "rejected"
    SPOILED = "spoiled"


class QualityGrade(str, Enum):
    PREMIUM = "premium"
    GRADE_A = "grade_a"
    GRADE_B = "grade_b"
    GRADE_C = "grade_c"
    REJECTED = "rejected"


class ProduceBatchCreate(BaseModel):
    """Schema for creating a new produce batch."""
    batch_number: Optional[str] = Field(None, max_length=50)
    crop_id: uuid.UUID
    customer_id: uuid.UUID
    source_farm_id: Optional[uuid.UUID] = None
    quantity_kg: float = Field(..., gt=0)
    quantity_units: Optional[int] = None
    unit_type: str = Field(default="kg", max_length=20)
    harvest_date: date
    expected_expiry_date: Optional[date] = None
    quality_grade: QualityGrade = QualityGrade.GRADE_A
    storage_unit_id: Optional[uuid.UUID] = None
    storage_temperature_celsius: Optional[float] = None
    humidity_percent: Optional[float] = None
    gcp_code: Optional[str] = Field(None, max_length=14)
    origin_country: str = Field(default="KE", max_length=2)
    certifications: Optional[List[str]] = None
    metadata: Optional[dict] = None


class ProduceBatchUpdate(BaseModel):
    """Schema for updating a produce batch."""
    quantity_kg: Optional[float] = Field(None, gt=0)
    quantity_units: Optional[int] = None
    status: Optional[BatchStatus] = None
    quality_grade: Optional[QualityGrade] = None
    storage_unit_id: Optional[uuid.UUID] = None
    storage_temperature_celsius: Optional[float] = None
    humidity_percent: Optional[float] = None
    expected_expiry_date: Optional[date] = None
    actual_expiry_date: Optional[date] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


class ProduceBatchResponse(BaseModel):
    """Schema for produce batch response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    batch_number: str
    crop_id: uuid.UUID
    crop_name: Optional[str] = None
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    source_farm_id: Optional[uuid.UUID] = None
    source_farm_name: Optional[str] = None
    status: BatchStatus
    quantity_kg: float
    quantity_units: Optional[int] = None
    remaining_quantity_kg: float
    unit_type: str
    harvest_date: date
    expected_expiry_date: Optional[date] = None
    actual_expiry_date: Optional[date] = None
    days_until_expiry: Optional[int] = None
    quality_grade: QualityGrade
    storage_unit_id: Optional[uuid.UUID] = None
    storage_unit_name: Optional[str] = None
    storage_temperature_celsius: Optional[float] = None
    humidity_percent: Optional[float] = None
    gcp_code: Optional[str] = None
    origin_country: str
    certifications: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProduceBatchListResponse(BaseModel):
    """Schema for paginated produce batch list."""
    items: list[ProduceBatchResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BatchQualityUpdate(BaseModel):
    """Schema for updating batch quality."""
    quality_grade: QualityGrade
    inspection_notes: Optional[str] = None
    inspector_id: Optional[uuid.UUID] = None
