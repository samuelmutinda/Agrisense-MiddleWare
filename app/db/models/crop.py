import uuid

from sqlalchemy import Column, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Crop(Base):
    __tablename__ = "crops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    unit_of_measure = Column(String, nullable=False)
    shelf_life_hrs = Column(Float, nullable=False)
    storage_temp_celsius = Column(Float, nullable=False)
    crop_description = Column(Text)
