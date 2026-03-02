"""SQLAlchemy model for RegulatoryCompliance."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base


class RegulatoryCompliance(Base):
    __tablename__ = "regulatory_compliance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    compliance_type = Column(
        Enum("kephis", "kebs", "nema", "county", "export", "food_safety", "other", name="compliance_type_enum"),
        nullable=False
    )
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    regulation_name = Column(String(200), nullable=False)
    authority_name = Column(String(200), nullable=False)
    status = Column(
        Enum("compliant", "non_compliant", "pending_review", "under_remediation", name="compliance_status_enum"),
        nullable=False, default="pending_review"
    )
    permit_number = Column(String(100), nullable=True)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    last_audit_date = Column(Date, nullable=True)
    next_audit_date = Column(Date, nullable=True)
    requirements = Column(ARRAY(String), nullable=True)
    findings = Column(Text, nullable=True)
    remediation_plan = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="regulatory_compliance")
    organization = relationship("Organization", back_populates="regulatory_compliance")
