import uuid

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SensorType(Base):
    __tablename__ = "sensor_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    unit = Column(String, nullable=False)
    description = Column(Text)

