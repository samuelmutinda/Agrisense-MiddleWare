import uuid, enum
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Float, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class EventType(enum.Enum):
    ARRIVAL = "arrival"
    TRANSFER_OUT = "transfer out"
    TRANSFER_IN = "transfer in"
    TRANSFER_CANCEL = "transfer cancel"
    LOSS = "loss"
    SPOILAGE = "spoilage"
    COLLECTION = "collection"

class HarvestInventoryLedger(Base):
    __tablename__ = "harvest_inventory_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    executed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    cold_storage_unit_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_units.id"), nullable=True)

    quantity_delta = Column(Float, nullable=False)
    volume_delta = Column(Float, nullable=False)
    event_type = Column(Enum(EventType), nullable=False)

    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

