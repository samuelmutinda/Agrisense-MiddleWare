"""SQLAlchemy model for Organization."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Organization(Base):
    """Organization model for multi-tenant organization management."""
    
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(200), nullable=False)
    organization_type = Column(
        Enum(
            "farm", "processor", "distributor", "retailer", "cooperative", "exporter",
            name="organization_type_enum"
        ),
        nullable=False
    )
    registration_number = Column(String(100), nullable=True)
    tax_id = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(JSONB, nullable=True)
    status = Column(
        Enum(
            "active", "suspended", "pending_verification",
            name="organization_status_enum"
        ),
        nullable=False,
        default="pending_verification"
    )
    parent_organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True
    )
    extra_metadata = Column(JSONB, nullable=True)
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
    tenant = relationship("Tenant", back_populates="organizations")
    parent_organization = relationship(
        "Organization",
        remote_side=[id],
        backref="child_organizations"
    )
    users = relationship("User", back_populates="organization")
    
    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, type={self.organization_type})>"
