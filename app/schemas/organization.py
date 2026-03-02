"""Pydantic schemas for Organization resource."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class OrganizationType(str, Enum):
    FARM = "farm"
    PROCESSOR = "processor"
    DISTRIBUTOR = "distributor"
    RETAILER = "retailer"
    COOPERATIVE = "cooperative"
    EXPORTER = "exporter"


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class AddressSchema(BaseModel):
    """Embedded address schema."""
    street: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "Kenya"
    coordinates: Optional[dict] = None  # {"lat": float, "lng": float}


class OrganizationCreate(BaseModel):
    """Schema for creating a new organization."""
    name: str = Field(..., min_length=2, max_length=200)
    organization_type: OrganizationType
    registration_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[AddressSchema] = None
    parent_organization_id: Optional[uuid.UUID] = None
    metadata: Optional[dict] = None


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    organization_type: Optional[OrganizationType] = None
    registration_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[AddressSchema] = None
    status: Optional[OrganizationStatus] = None
    metadata: Optional[dict] = None


class OrganizationResponse(BaseModel):
    """Schema for organization response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    organization_type: OrganizationType
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[dict] = None
    status: OrganizationStatus
    parent_organization_id: Optional[uuid.UUID] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationListResponse(BaseModel):
    """Schema for paginated organization list."""
    items: list[OrganizationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
