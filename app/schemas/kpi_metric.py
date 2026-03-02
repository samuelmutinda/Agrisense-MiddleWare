"""Pydantic schemas for KpiMetrics resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MetricCategory(str, Enum):
    OPERATIONS = "operations"
    FINANCIAL = "financial"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    SUSTAINABILITY = "sustainability"


class KpiMetricCreate(BaseModel):
    metric_name: str = Field(..., max_length=100)
    category: MetricCategory
    value: float
    unit: str = Field(..., max_length=20)
    target_value: Optional[float] = None
    period_start: date
    period_end: date
    facility_id: Optional[uuid.UUID] = None
    metadata: Optional[dict] = None


class KpiMetricResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    metric_name: str
    category: MetricCategory
    value: float
    unit: str
    target_value: Optional[float] = None
    variance_percent: Optional[float] = None
    period_start: date
    period_end: date
    facility_id: Optional[uuid.UUID] = None
    facility_name: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class KpiMetricListResponse(BaseModel):
    items: list[KpiMetricResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
