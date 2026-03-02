"""Pydantic schemas for Manifest resource."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class ManifestStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    PARTIAL_DELIVERY = "partial_delivery"


class ManifestItemCreate(BaseModel):
    """Schema for manifest item."""
    produce_batch_id: uuid.UUID
    quantity_kg: float = Field(..., gt=0)
    quantity_units: Optional[int] = None
    unit_type: str = Field(default="kg", max_length=20)
    notes: Optional[str] = None


class ManifestItemResponse(BaseModel):
    """Schema for manifest item response."""
    id: uuid.UUID
    manifest_id: uuid.UUID
    produce_batch_id: uuid.UUID
    crop_name: Optional[str] = None
    quantity_kg: float
    quantity_units: Optional[int] = None
    unit_type: str
    notes: Optional[str] = None
    
    model_config = {"from_attributes": True}


class ManifestCreate(BaseModel):
    """Schema for creating a new manifest."""
    manifest_number: Optional[str] = Field(None, max_length=50)
    truck_id: uuid.UUID
    driver_id: Optional[uuid.UUID] = None
    origin_facility_id: uuid.UUID
    destination_facility_id: uuid.UUID
    customer_id: uuid.UUID
    scheduled_departure: datetime
    scheduled_arrival: datetime
    items: List[ManifestItemCreate] = Field(default_factory=list)
    temperature_min_celsius: float = Field(default=2.0)
    temperature_max_celsius: float = Field(default=8.0)
    special_instructions: Optional[str] = None
    metadata: Optional[dict] = None


class ManifestUpdate(BaseModel):
    """Schema for updating a manifest."""
    truck_id: Optional[uuid.UUID] = None
    driver_id: Optional[uuid.UUID] = None
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    status: Optional[ManifestStatus] = None
    temperature_min_celsius: Optional[float] = None
    temperature_max_celsius: Optional[float] = None
    special_instructions: Optional[str] = None
    delivery_notes: Optional[str] = None
    metadata: Optional[dict] = None


class ManifestResponse(BaseModel):
    """Schema for manifest response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    manifest_number: str
    truck_id: uuid.UUID
    truck_registration: Optional[str] = None
    driver_id: Optional[uuid.UUID] = None
    driver_name: Optional[str] = None
    origin_facility_id: uuid.UUID
    origin_facility_name: Optional[str] = None
    destination_facility_id: uuid.UUID
    destination_facility_name: Optional[str] = None
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    status: ManifestStatus
    scheduled_departure: datetime
    scheduled_arrival: datetime
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    temperature_min_celsius: float
    temperature_max_celsius: float
    items: List[ManifestItemResponse] = Field(default_factory=list)
    total_weight_kg: float = 0.0
    total_items: int = 0
    special_instructions: Optional[str] = None
    delivery_notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ManifestListResponse(BaseModel):
    """Schema for paginated manifest list."""
    items: list[ManifestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ManifestStatusUpdate(BaseModel):
    """Schema for updating manifest status."""
    status: ManifestStatus
    notes: Optional[str] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
