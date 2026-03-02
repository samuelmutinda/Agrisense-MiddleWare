import uuid, enum

from sqlalchemy import Column, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class OccurredDuring(enum.Enum):
    TRANSIT = "transit"
    STORAGE = "storage"

class LossReason(enum.Enum):
    THEFT = "theft"
    TRANSIT_ACCIDENT = "transit accident"
    SPILLAGE = "spillage"
    OTHER = "other"

class HarvestLoss(Base):
    __tablename__ = "harvest_losses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_id = Column(UUID(as_uuid=True), ForeignKey("harvest_arrivals.id"), nullable=False)
    reported_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    transfer_id = Column(UUID(as_uuid=True), ForeignKey("harvest_transfers.id"))

    occurred_during = Column(Enum(OccurredDuring), nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    loss_reason = Column(Enum(LossReason), nullable=False)
    notes = Column(Text, nullable=False)

