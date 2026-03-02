import uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    chirpstack_application_id = Column(UUID(as_uuid=True), nullable=True)
    chirpstack_device_profile_id = Column(UUID(as_uuid=True), nullable=True)

