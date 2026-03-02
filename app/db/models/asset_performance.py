"""SQLAlchemy model for AssetPerformance."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class AssetPerformance(Base):
    __tablename__ = "asset_performance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    asset_type = Column(Enum("refrigeration_unit", "cold_room", "reefer_truck", "conveyor", "packaging_machine", "forklift", name="asset_type_enum"), nullable=False)
    asset_name = Column(String(100), nullable=False)
    uptime_percent = Column(Float, nullable=False)
    efficiency_score = Column(Float, nullable=False)
    performance_status = Column(Enum("optimal", "degraded", "critical", "offline", name="perf_status_enum"), nullable=False)
    measurement_timestamp = Column(DateTime(timezone=True), nullable=False)
    energy_consumption_kwh = Column(Float, nullable=True)
    operating_hours = Column(Float, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    last_maintenance = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="asset_performance_records")
