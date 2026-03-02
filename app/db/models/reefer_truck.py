"""SQLAlchemy model for ReeferTruck."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class ReeferTruck(Base):
    """Reefer truck model for refrigerated fleet management."""
    
    __tablename__ = "reefer_trucks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    registration_number = Column(String(20), nullable=False, unique=True)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    capacity_kg = Column(Float, nullable=False)
    capacity_cubic_meters = Column(Float, nullable=False)
    min_temperature_celsius = Column(Float, nullable=False, default=-25.0)
    max_temperature_celsius = Column(Float, nullable=False, default=25.0)
    fuel_type = Column(String(20), nullable=False, default="diesel")
    status = Column(
        Enum(
            "available", "in_transit", "loading", "unloading", "maintenance", "out_of_service",
            name="truck_status_enum"
        ),
        nullable=False,
        default="available"
    )
    vin_number = Column(String(50), nullable=True)
    fleet_id = Column(UUID(as_uuid=True), nullable=True)
    assigned_driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    current_temperature_celsius = Column(Float, nullable=True)
    current_location = Column(JSONB, nullable=True)
    last_service_date = Column(Date, nullable=True)
    next_service_due = Column(Date, nullable=True)
    insurance_expiry = Column(Date, nullable=True)
    total_trips = Column(Integer, nullable=False, default=0)
    total_distance_km = Column(Float, nullable=False, default=0.0)
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
    tenant = relationship("Tenant", back_populates="reefer_trucks")
    assigned_driver = relationship("User", back_populates="assigned_trucks")
    manifests = relationship("Manifest", back_populates="truck")
    
    def __repr__(self) -> str:
        return f"<ReeferTruck(id={self.id}, reg={self.registration_number}, status={self.status})>"
