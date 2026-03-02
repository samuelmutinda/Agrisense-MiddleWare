"""Pydantic schemas for OperatingCost resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CostCategory(str, Enum):
    ENERGY = "energy"
    LABOR = "labor"
    MAINTENANCE = "maintenance"
    SUPPLIES = "supplies"
    INSURANCE = "insurance"
    RENT = "rent"
    TRANSPORT = "transport"
    OTHER = "other"


class OperatingCostCreate(BaseModel):
    facility_id: Optional[uuid.UUID] = None
    category: CostCategory
    description: str = Field(..., max_length=255)
    amount: float = Field(..., ge=0)
    currency: str = Field(default="KES", max_length=3)
    period_start: date
    period_end: date
    vendor_name: Optional[str] = Field(None, max_length=100)
    invoice_reference: Optional[str] = Field(None, max_length=50)
    is_recurring: bool = False
    metadata: Optional[dict] = None


class OperatingCostResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: Optional[uuid.UUID] = None
    facility_name: Optional[str] = None
    category: CostCategory
    description: str
    amount: float
    currency: str
    period_start: date
    period_end: date
    vendor_name: Optional[str] = None
    invoice_reference: Optional[str] = None
    is_recurring: bool
    metadata: Optional[dict] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class OperatingCostListResponse(BaseModel):
    items: list[OperatingCostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    total_amount: Optional[float] = None
