"""SQLAlchemy model for MaintenanceRecord."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False)
    asset_name = Column(String(100), nullable=False)
    maintenance_type = Column(Enum("preventive", "corrective", "emergency", "calibration", name="maint_type_enum"), nullable=False)
    status = Column(Enum("scheduled", "in_progress", "completed", "cancelled", name="maint_status_enum"), nullable=False, default="scheduled")
    priority = Column(Enum("low", "medium", "high", "critical", name="maint_priority_enum"), nullable=False, default="medium")
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    description = Column(String(500), nullable=False)
    assigned_technician_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    estimated_duration_hours = Column(Float, nullable=True)
    actual_duration_hours = Column(Float, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    parts_required = Column(ARRAY(String), nullable=True)
    parts_used = Column(ARRAY(String), nullable=True)
    notes = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="maintenance_records")
    assigned_technician = relationship("User", back_populates="maintenance_assignments")
