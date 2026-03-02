import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.models.crop import Crop
from app.db.models.customer import Customer
from app.db.models.tenant import Tenant

class HarvestArrival(Base):
    __tablename__ = "harvest_arrivals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    crop_id = Column(UUID(as_uuid=True), ForeignKey("crops.id"), nullable=False)
    inspected_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    arrived_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    harvested_at = Column(DateTime, nullable=False)
    quantity = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    expected_storage_hrs = Column(Float)
    notes = Column(Text)

    crop = relationship(Crop)
    customer = relationship(Customer)
    tenant = relationship(Tenant)

