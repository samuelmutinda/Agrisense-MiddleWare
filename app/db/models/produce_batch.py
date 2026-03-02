"""SQLAlchemy model for ProduceBatch."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base


class ProduceBatch(Base):
    """Produce batch model for tracking harvested produce."""
    
    __tablename__ = "produce_batches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    batch_number = Column(String(50), nullable=False, unique=True)
    crop_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crops.id", ondelete="RESTRICT"),
        nullable=False
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False
    )
    source_farm_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True
    )
    status = Column(
        Enum(
            "pending", "in_storage", "in_transit", "delivered", "rejected", "spoiled",
            name="batch_status_enum"
        ),
        nullable=False,
        default="pending"
    )
    quantity_kg = Column(Float, nullable=False)
    quantity_units = Column(Integer, nullable=True)
    remaining_quantity_kg = Column(Float, nullable=False)
    unit_type = Column(String(20), nullable=False, default="kg")
    harvest_date = Column(Date, nullable=False)
    expected_expiry_date = Column(Date, nullable=True)
    actual_expiry_date = Column(Date, nullable=True)
    quality_grade = Column(
        Enum(
            "premium", "grade_a", "grade_b", "grade_c", "rejected",
            name="quality_grade_enum"
        ),
        nullable=False,
        default="grade_a"
    )
    storage_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cold_storage_units.id", ondelete="SET NULL"),
        nullable=True
    )
    storage_temperature_celsius = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    gcp_code = Column(String(14), nullable=True)  # GS1 Global Coupon Number
    origin_country = Column(String(2), nullable=False, default="KE")
    certifications = Column(ARRAY(String), nullable=True)
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
    tenant = relationship("Tenant", back_populates="produce_batches")
    crop = relationship("Crop", back_populates="produce_batches")
    customer = relationship("Customer", back_populates="produce_batches")
    source_farm = relationship("Organization", back_populates="produce_batches")
    storage_unit = relationship("ColdStorageUnit", back_populates="stored_batches")
    manifest_items = relationship("ManifestItem", back_populates="produce_batch")
    inspections = relationship("Inspection", back_populates="produce_batch")
    inventory_movements = relationship("InventoryMovement", back_populates="produce_batch")
    
    def __repr__(self) -> str:
        return f"<ProduceBatch(id={self.id}, batch={self.batch_number}, status={self.status})>"
