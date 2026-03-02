"""Pydantic schemas for GcpProfile resource (Good Cold-chain Practice)."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GcpCertificationLevel(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class GcpProfileCreate(BaseModel):
    facility_id: uuid.UUID
    certification_level: GcpCertificationLevel
    temperature_compliance_score: float = Field(..., ge=0, le=100)
    hygiene_score: float = Field(..., ge=0, le=100)
    documentation_score: float = Field(..., ge=0, le=100)
    training_score: float = Field(..., ge=0, le=100)
    audit_date: datetime
    next_audit_date: Optional[datetime] = None
    auditor_name: Optional[str] = None
    recommendations: Optional[list[str]] = None
    metadata: Optional[dict] = None


class GcpProfileUpdate(BaseModel):
    certification_level: Optional[GcpCertificationLevel] = None
    temperature_compliance_score: Optional[float] = Field(None, ge=0, le=100)
    hygiene_score: Optional[float] = Field(None, ge=0, le=100)
    documentation_score: Optional[float] = Field(None, ge=0, le=100)
    training_score: Optional[float] = Field(None, ge=0, le=100)
    next_audit_date: Optional[datetime] = None
    recommendations: Optional[list[str]] = None
    metadata: Optional[dict] = None


class GcpProfileResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    facility_name: Optional[str] = None
    certification_level: GcpCertificationLevel
    overall_score: float
    temperature_compliance_score: float
    hygiene_score: float
    documentation_score: float
    training_score: float
    audit_date: datetime
    next_audit_date: Optional[datetime] = None
    auditor_name: Optional[str] = None
    recommendations: Optional[list[str]] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class GcpProfileListResponse(BaseModel):
    items: list[GcpProfileResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
