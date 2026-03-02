import uuid

from sqlalchemy import Column, ForeignKey, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.models.tenant import Tenant

class ColdStorageUnit(Base):
    __tablename__ = "cold_storage_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_volume = Column(Float, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)

    tenant = relationship(Tenant)

