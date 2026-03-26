"""SQLAlchemy model for InventoryMovement."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class InventoryMovement(Base):
    """Inventory movement model for tracking stock movements."""
    
    __tablename__ = "inventory_movements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    produce_batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("produce_batches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    movement_type = Column(
        Enum(
            "intake", "outbound", "transfer", "adjustment", "loss", "return",
            name="movement_type_enum"
        ),
        nullable=False
    )
    quantity_kg = Column(Float, nullable=False)
    from_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cold_storage_units.id", ondelete="SET NULL"),
        nullable=True
    )
    to_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cold_storage_units.id", ondelete="SET NULL"),
        nullable=True
    )
    reference_document_id = Column(UUID(as_uuid=True), nullable=True)
    reference_type = Column(String(50), nullable=True)
    executed_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="inventory_movements")
    produce_batch = relationship("ProduceBatch", back_populates="inventory_movements")
    from_location = relationship("ColdStorageUnit", foreign_keys=[from_location_id])
    to_location = relationship("ColdStorageUnit", foreign_keys=[to_location_id])
    executed_by = relationship("User", back_populates="inventory_movements")
    
    def __repr__(self) -> str:
        return f"<InventoryMovement(id={self.id}, type={self.movement_type}, qty={self.quantity_kg}kg)>"
