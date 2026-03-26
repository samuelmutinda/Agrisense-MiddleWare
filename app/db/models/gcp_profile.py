"""SQLAlchemy model for GcpProfile (Good Cold-chain Practice)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base


class GcpProfile(Base):
    __tablename__ = "gcp_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=False, index=True)
    certification_level = Column(Enum("bronze", "silver", "gold", "platinum", name="gcp_level_enum"), nullable=False)
    temperature_compliance_score = Column(Float, nullable=False)
    hygiene_score = Column(Float, nullable=False)
    documentation_score = Column(Float, nullable=False)
    training_score = Column(Float, nullable=False)
    audit_date = Column(DateTime(timezone=True), nullable=False)
    next_audit_date = Column(DateTime(timezone=True), nullable=True)
    auditor_name = Column(String(100), nullable=True)
    recommendations = Column(ARRAY(String), nullable=True)
    extra_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="gcp_profiles")
    facility = relationship("ColdStorageUnit", back_populates="gcp_profiles")
