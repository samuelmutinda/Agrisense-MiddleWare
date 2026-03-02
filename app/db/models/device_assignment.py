import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey,DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class DeviceAssignment(Base):
    __tablename__ = "device_assignment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dev_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    cs_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=False)

    assigned_at = Column(DateTime, default=datetime.utcnow)
    unassigned_at = Column(DateTime)
