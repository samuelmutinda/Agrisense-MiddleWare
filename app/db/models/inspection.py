"""SQLAlchemy model for Inspection."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Inspection(Base):
    """Inspection model for quality and safety inspections."""
    
    __tablename__ = "inspections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    produce_batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("produce_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    storage_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cold_storage_units.id", ondelete="SET NULL"),
        nullable=True
    )
    inspection_type = Column(
        Enum(
            "arrival", "storage", "pre_shipment", "quality", "safety", "regulatory",
            name="inspection_type_enum"
        ),
        nullable=False
    )
    result = Column(
        Enum(
            "pass", "fail", "conditional", "pending",
            name="inspection_result_enum"
        ),
        nullable=False,
        default="pending"
    )
    inspector_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    criteria = Column(JSONB, nullable=True)  # List of criteria results
    overall_score = Column(Float, nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    findings = Column(Text, nullable=True)
    corrective_actions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="inspections")
    produce_batch = relationship("ProduceBatch", back_populates="inspections")
    storage_unit = relationship("ColdStorageUnit", back_populates="inspections")
    inspector = relationship("User", back_populates="inspections")
    
    def __repr__(self) -> str:
        return f"<Inspection(id={self.id}, type={self.inspection_type}, result={self.result})>"
