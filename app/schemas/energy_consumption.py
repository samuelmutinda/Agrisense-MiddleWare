"""Pydantic schemas for EnergyConsumption resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EnergySource(str, Enum):
    GRID = "grid"
    SOLAR = "solar"
    GENERATOR = "generator"
    HYBRID = "hybrid"


class EnergyConsumptionCreate(BaseModel):
    facility_id: uuid.UUID
    period_date: date
    total_kwh: float = Field(..., ge=0)
    refrigeration_kwh: Optional[float] = Field(None, ge=0)
    lighting_kwh: Optional[float] = Field(None, ge=0)
    other_kwh: Optional[float] = Field(None, ge=0)
    peak_demand_kw: Optional[float] = Field(None, ge=0)
    energy_source: EnergySource
    cost_per_kwh: Optional[float] = Field(None, ge=0)
    total_cost: Optional[float] = Field(None, ge=0)
    carbon_footprint_kg: Optional[float] = Field(None, ge=0)
    metadata: Optional[dict] = None


class EnergyConsumptionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    facility_name: Optional[str] = None
    period_date: date
    total_kwh: float
    refrigeration_kwh: Optional[float] = None
    lighting_kwh: Optional[float] = None
    other_kwh: Optional[float] = None
    peak_demand_kw: Optional[float] = None
    energy_source: EnergySource
    cost_per_kwh: Optional[float] = None
    total_cost: Optional[float] = None
    carbon_footprint_kg: Optional[float] = None
    metadata: Optional[dict] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class EnergyConsumptionListResponse(BaseModel):
    items: list[EnergyConsumptionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    total_kwh: Optional[float] = None
    total_cost: Optional[float] = None
