import uuid, enum
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Boolean, Text, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class TransferStatus(enum.Enum):
    IN_TRANSIT = "in transit"
    CANCELED = "canceled"
    COMPLETED = "completed"
    LOST = "lost"

class HarvestTransfer(Base):
    __tablename__ = "harvest_transfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_id = Column(UUID(as_uuid=True), ForeignKey("harvest_arrivals.id"), nullable=False)
    from_cs_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=False)
    to_cs_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=False)
    initiated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    closed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    initiated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime)
    status = Column(Enum(TransferStatus), nullable=False, default=TransferStatus.IN_TRANSIT)
    notes = Column(Text)

