import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class HarvestCollection(Base):
    __tablename__ = "harvest_collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_id = Column(UUID(as_uuid=True), ForeignKey("harvest_arrivals.id"), nullable=False)
    handled_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=False)

