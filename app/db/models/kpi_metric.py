"""SQLAlchemy model for KpiMetric."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class KpiMetric(Base):
    __tablename__ = "kpi_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)
    category = Column(Enum("operations", "financial", "quality", "efficiency", "sustainability", name="kpi_category_enum"), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    target_value = Column(Float, nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="kpi_metrics")
    facility = relationship("ColdStorageUnit", back_populates="kpi_metrics")
