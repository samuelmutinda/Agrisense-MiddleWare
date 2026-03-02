"""SQLAlchemy model for Certification."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Certification(Base):
    """Certification model for organization certifications."""
    
    __tablename__ = "certifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    certification_type = Column(
        Enum(
            "organic", "fair_trade", "gap", "haccp", "iso_22000", 
            "global_gap", "rainforest_alliance", "other",
            name="certification_type_enum"
        ),
        nullable=False
    )
    certificate_number = Column(String(100), nullable=False)
    issuing_body = Column(String(200), nullable=False)
    status = Column(
        Enum(
            "active", "expired", "pending", "suspended", "revoked",
            name="certification_status_enum"
        ),
        nullable=False,
        default="pending"
    )
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    scope = Column(Text, nullable=True)
    document_url = Column(String(500), nullable=True)
    renewal_notes = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="certifications")
    organization = relationship("Organization", back_populates="certifications")
    
    def __repr__(self) -> str:
        return f"<Certification(id={self.id}, type={self.certification_type}, status={self.status})>"
