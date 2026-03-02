import uuid, enum

from sqlalchemy import Column, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class SpoilageReason(enum.Enum):
    FUNGAL_GROWTH = "fungal_growth"
    BACTERIAL_DECAY = "bacterial_decay"
    OXIDATION = "oxidation"
    EXCESSIVE_MOISTURE = "excessive_moisture"
    OVERHEATING = "overheating"
    INADEQUATE_VENTILATION = "inadequate_ventilation"
    FERMENTATION = "fermentation"
    CHEMICAL_REACTION = "chemical_reaction"
    NATURAL_SENESCENCE = "natural_senescence"
    OTHER = "other"

class HarvestSpoilage(Base):
    __tablename__ = "harvest_spoilages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_id = Column(UUID(as_uuid=True), ForeignKey("harvest_arrivals.id"), nullable=False)
    reported_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    spoilage_reason = Column(Enum(SpoilageReason), nullable=False)
    detected_at = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=False)

