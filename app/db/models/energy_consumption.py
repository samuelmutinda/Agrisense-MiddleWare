"""SQLAlchemy model for EnergyConsumption."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class EnergyConsumption(Base):
    __tablename__ = "energy_consumption"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=False, index=True)
    period_date = Column(Date, nullable=False)
    total_kwh = Column(Float, nullable=False)
    refrigeration_kwh = Column(Float, nullable=True)
    lighting_kwh = Column(Float, nullable=True)
    other_kwh = Column(Float, nullable=True)
    peak_demand_kw = Column(Float, nullable=True)
    energy_source = Column(Enum("grid", "solar", "generator", "hybrid", name="energy_source_enum"), nullable=False)
    cost_per_kwh = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    carbon_footprint_kg = Column(Float, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="energy_consumption_records")
    facility = relationship("ColdStorageUnit", back_populates="energy_consumption_records")
