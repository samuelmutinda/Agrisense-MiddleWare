"""Pydantic schemas for RegulatoryCompliance resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class ComplianceType(str, Enum):
    KEPHIS = "kephis"  # Kenya Plant Health Inspectorate Service
    KEBS = "kebs"      # Kenya Bureau of Standards
    NEMA = "nema"      # National Environment Management Authority
    COUNTY = "county"
    EXPORT = "export"
    FOOD_SAFETY = "food_safety"
    OTHER = "other"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    UNDER_REMEDIATION = "under_remediation"


class RegulatoryComplianceCreate(BaseModel):
    compliance_type: ComplianceType
    organization_id: Optional[uuid.UUID] = None
    regulation_name: str = Field(..., max_length=200)
    authority_name: str = Field(..., max_length=200)
    permit_number: Optional[str] = Field(None, max_length=100)
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    requirements: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


class RegulatoryComplianceUpdate(BaseModel):
    status: Optional[ComplianceStatus] = None
    permit_number: Optional[str] = None
    expiry_date: Optional[date] = None
    last_audit_date: Optional[date] = None
    next_audit_date: Optional[date] = None
    findings: Optional[str] = None
    remediation_plan: Optional[str] = None
    metadata: Optional[dict] = None


class RegulatoryComplianceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    compliance_type: ComplianceType
    organization_id: Optional[uuid.UUID] = None
    organization_name: Optional[str] = None
    regulation_name: str
    authority_name: str
    status: ComplianceStatus
    permit_number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    days_until_expiry: Optional[int] = None
    last_audit_date: Optional[date] = None
    next_audit_date: Optional[date] = None
    requirements: Optional[List[str]] = None
    findings: Optional[str] = None
    remediation_plan: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class RegulatoryComplianceListResponse(BaseModel):
    items: list[RegulatoryComplianceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
