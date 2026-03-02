import uuid

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DeviceSensorCapability(Base):
    __tablename__ = "device_sensor_capabilities"

    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), primary_key=True)
    sensor_type_id = Column(UUID(as_uuid=True), ForeignKey("sensor_types.id"), primary_key=True)

