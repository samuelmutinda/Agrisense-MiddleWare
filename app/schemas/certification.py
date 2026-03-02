"""Pydantic schemas for Certification resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class CertificationType(str, Enum):
    ORGANIC = "organic"
    FAIR_TRADE = "fair_trade"
    GAP = "gap"  # Good Agricultural Practices
    HACCP = "haccp"
    ISO_22000 = "iso_22000"
    GLOBAL_GAP = "global_gap"
    RAINFOREST_ALLIANCE = "rainforest_alliance"
    OTHER = "other"


class CertificationStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING = "pending"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class CertificationCreate(BaseModel):
    """Schema for creating a certification."""
    organization_id: uuid.UUID
    certification_type: CertificationType
    certificate_number: str = Field(..., max_length=100)
    issuing_body: str = Field(..., max_length=200)
    issue_date: date
    expiry_date: date
    scope: Optional[str] = None
    document_url: Optional[str] = None
    metadata: Optional[dict] = None


class CertificationUpdate(BaseModel):
    """Schema for updating a certification."""
    certificate_number: Optional[str] = Field(None, max_length=100)
    status: Optional[CertificationStatus] = None
    expiry_date: Optional[date] = None
    scope: Optional[str] = None
    document_url: Optional[str] = None
    renewal_notes: Optional[str] = None
    metadata: Optional[dict] = None


class CertificationResponse(BaseModel):
    """Schema for certification response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: Optional[str] = None
    certification_type: CertificationType
    certificate_number: str
    issuing_body: str
    status: CertificationStatus
    issue_date: date
    expiry_date: date
    days_until_expiry: Optional[int] = None
    scope: Optional[str] = None
    document_url: Optional[str] = None
    renewal_notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CertificationListResponse(BaseModel):
    """Schema for paginated certification list."""
    items: list[CertificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
