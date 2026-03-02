"""SQLAlchemy models for Manifest and ManifestItem."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Manifest(Base):
    """Manifest model for shipping documentation."""
    
    __tablename__ = "manifests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    manifest_number = Column(String(50), nullable=False, unique=True)
    truck_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reefer_trucks.id", ondelete="SET NULL"),
        nullable=True
    )
    driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    origin_facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cold_storage_units.id", ondelete="RESTRICT"),
        nullable=False
    )
    destination_facility_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cold_storage_units.id", ondelete="RESTRICT"),
        nullable=False
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False
    )
    status = Column(
        Enum(
            "draft", "pending", "in_transit", "delivered", "cancelled", "partial_delivery",
            name="manifest_status_enum"
        ),
        nullable=False,
        default="draft"
    )
    scheduled_departure = Column(DateTime(timezone=True), nullable=False)
    scheduled_arrival = Column(DateTime(timezone=True), nullable=False)
    actual_departure = Column(DateTime(timezone=True), nullable=True)
    actual_arrival = Column(DateTime(timezone=True), nullable=True)
    temperature_min_celsius = Column(Float, nullable=False, default=2.0)
    temperature_max_celsius = Column(Float, nullable=False, default=8.0)
    total_weight_kg = Column(Float, nullable=False, default=0.0)
    total_items = Column(Integer, nullable=False, default=0)
    special_instructions = Column(Text, nullable=True)
    delivery_notes = Column(Text, nullable=True)
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
    tenant = relationship("Tenant", back_populates="manifests")
    truck = relationship("ReeferTruck", back_populates="manifests")
    driver = relationship("User", back_populates="driven_manifests")
    origin_facility = relationship("ColdStorageUnit", foreign_keys=[origin_facility_id])
    destination_facility = relationship("ColdStorageUnit", foreign_keys=[destination_facility_id])
    customer = relationship("Customer", back_populates="manifests")
    items = relationship("ManifestItem", back_populates="manifest", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Manifest(id={self.id}, number={self.manifest_number}, status={self.status})>"


class ManifestItem(Base):
    """Manifest item model for items within a manifest."""
    
    __tablename__ = "manifest_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manifest_id = Column(
        UUID(as_uuid=True),
        ForeignKey("manifests.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    produce_batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("produce_batches.id", ondelete="RESTRICT"),
        nullable=False
    )
    quantity_kg = Column(Float, nullable=False)
    quantity_units = Column(Integer, nullable=True)
    unit_type = Column(String(20), nullable=False, default="kg")
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    manifest = relationship("Manifest", back_populates="items")
    produce_batch = relationship("ProduceBatch", back_populates="manifest_items")
    
    def __repr__(self) -> str:
        return f"<ManifestItem(id={self.id}, manifest_id={self.manifest_id}, qty={self.quantity_kg}kg)>"
