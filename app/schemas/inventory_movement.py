"""Pydantic schemas for InventoryMovement resource."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MovementType(str, Enum):
    INTAKE = "intake"
    OUTBOUND = "outbound"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    LOSS = "loss"
    RETURN = "return"


class InventoryMovementCreate(BaseModel):
    """Schema for creating an inventory movement."""
    produce_batch_id: uuid.UUID
    movement_type: MovementType
    quantity_kg: float = Field(..., gt=0)
    from_location_id: Optional[uuid.UUID] = None
    to_location_id: Optional[uuid.UUID] = None
    reference_document_id: Optional[uuid.UUID] = None
    reference_type: Optional[str] = Field(None, max_length=50)  # manifest, transfer, etc.
    reason: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


class InventoryMovementResponse(BaseModel):
    """Schema for inventory movement response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    produce_batch_id: uuid.UUID
    batch_number: Optional[str] = None
    movement_type: MovementType
    quantity_kg: float
    from_location_id: Optional[uuid.UUID] = None
    from_location_name: Optional[str] = None
    to_location_id: Optional[uuid.UUID] = None
    to_location_name: Optional[str] = None
    reference_document_id: Optional[uuid.UUID] = None
    reference_type: Optional[str] = None
    executed_by_user_id: uuid.UUID
    executed_by_name: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryMovementListResponse(BaseModel):
    """Schema for paginated inventory movement list."""
    items: list[InventoryMovementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class InventoryAdjustmentCreate(BaseModel):
    """Schema for inventory adjustment (corrections)."""
    produce_batch_id: uuid.UUID
    adjustment_quantity_kg: float  # Can be negative for reductions
    reason: str
    notes: Optional[str] = None
