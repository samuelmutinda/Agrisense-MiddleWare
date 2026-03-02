"""SQLAlchemy model for OperatingCost."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class OperatingCost(Base):
    __tablename__ = "operating_costs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=True, index=True)
    category = Column(Enum("energy", "labor", "maintenance", "supplies", "insurance", "rent", "transport", "other", name="cost_category_enum"), nullable=False)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="KES")
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    vendor_name = Column(String(100), nullable=True)
    invoice_reference = Column(String(50), nullable=True)
    is_recurring = Column(Boolean, nullable=False, default=False)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="operating_costs")
    facility = relationship("ColdStorageUnit", back_populates="operating_costs")
