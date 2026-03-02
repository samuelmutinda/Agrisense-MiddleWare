"""Pydantic schemas for ReeferTruck resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TruckStatus(str, Enum):
    AVAILABLE = "available"
    IN_TRANSIT = "in_transit"
    LOADING = "loading"
    UNLOADING = "unloading"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class ReeferTruckCreate(BaseModel):
    """Schema for creating a new reefer truck."""
    registration_number: str = Field(..., min_length=1, max_length=20)
    make: str = Field(..., max_length=50)
    model: str = Field(..., max_length=50)
    year: int = Field(..., ge=1990, le=2100)
    capacity_kg: float = Field(..., gt=0)
    capacity_cubic_meters: float = Field(..., gt=0)
    min_temperature_celsius: float = Field(default=-25.0)
    max_temperature_celsius: float = Field(default=25.0)
    fuel_type: str = Field(default="diesel", max_length=20)
    vin_number: Optional[str] = Field(None, max_length=50)
    fleet_id: Optional[uuid.UUID] = None
    assigned_driver_id: Optional[uuid.UUID] = None
    last_service_date: Optional[date] = None
    next_service_due: Optional[date] = None
    insurance_expiry: Optional[date] = None
    metadata: Optional[dict] = None


class ReeferTruckUpdate(BaseModel):
    """Schema for updating a reefer truck."""
    registration_number: Optional[str] = Field(None, max_length=20)
    make: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    year: Optional[int] = Field(None, ge=1990, le=2100)
    capacity_kg: Optional[float] = Field(None, gt=0)
    capacity_cubic_meters: Optional[float] = Field(None, gt=0)
    min_temperature_celsius: Optional[float] = None
    max_temperature_celsius: Optional[float] = None
    fuel_type: Optional[str] = Field(None, max_length=20)
    status: Optional[TruckStatus] = None
    assigned_driver_id: Optional[uuid.UUID] = None
    last_service_date: Optional[date] = None
    next_service_due: Optional[date] = None
    insurance_expiry: Optional[date] = None
    metadata: Optional[dict] = None


class ReeferTruckResponse(BaseModel):
    """Schema for reefer truck response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    registration_number: str
    make: str
    model: str
    year: int
    capacity_kg: float
    capacity_cubic_meters: float
    min_temperature_celsius: float
    max_temperature_celsius: float
    fuel_type: str
    status: TruckStatus
    vin_number: Optional[str] = None
    fleet_id: Optional[uuid.UUID] = None
    assigned_driver_id: Optional[uuid.UUID] = None
    assigned_driver_name: Optional[str] = None
    current_temperature_celsius: Optional[float] = None
    current_location: Optional[dict] = None  # {"lat": float, "lng": float}
    last_service_date: Optional[date] = None
    next_service_due: Optional[date] = None
    insurance_expiry: Optional[date] = None
    total_trips: int = 0
    total_distance_km: float = 0.0
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReeferTruckListResponse(BaseModel):
    """Schema for paginated reefer truck list."""
    items: list[ReeferTruckResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TruckLocationUpdate(BaseModel):
    """Schema for updating truck location."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    temperature_celsius: Optional[float] = None
    speed_kmh: Optional[float] = None


class TruckTelemetry(BaseModel):
    """Schema for truck telemetry data."""
    truck_id: uuid.UUID
    timestamp: datetime
    location: dict
    temperature_celsius: float
    fuel_level_percent: Optional[float] = None
    speed_kmh: Optional[float] = None
    engine_running: bool = False
    door_open: bool = False
