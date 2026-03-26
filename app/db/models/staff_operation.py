"""SQLAlchemy model for StaffOperation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class StaffOperation(Base):
    __tablename__ = "staff_operations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    operation_type = Column(Enum("shift", "task", "training", "overtime", name="staff_op_type_enum"), nullable=False)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=True)
    shift_type = Column(Enum("morning", "afternoon", "night", "rotating", name="shift_type_enum"), nullable=True)
    operation_date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    task_description = Column(String(500), nullable=True)
    area_assigned = Column(String(100), nullable=True)
    supervisor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    performance_notes = Column(Text, nullable=True)
    productivity_score = Column(Float, nullable=True)
    extra_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="staff_operations")
    staff = relationship("User", foreign_keys=[staff_id], back_populates="staff_operations")
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    facility = relationship("ColdStorageUnit", back_populates="staff_operations")
