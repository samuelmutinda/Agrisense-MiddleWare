"""SQLAlchemy model for FinancialTransaction."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class FinancialTransaction(Base):
    """Financial transaction model."""
    
    __tablename__ = "financial_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    transaction_type = Column(
        Enum("sale", "purchase", "refund", "expense", "adjustment", name="fin_transaction_type_enum"),
        nullable=False
    )
    status = Column(
        Enum("pending", "completed", "cancelled", "refunded", name="fin_transaction_status_enum"),
        nullable=False,
        default="pending"
    )
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="KES")
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    manifest_id = Column(UUID(as_uuid=True), ForeignKey("manifests.id"), nullable=True)
    payment_method = Column(
        Enum("cash", "mpesa", "bank_transfer", "credit", "check", name="payment_method_enum"),
        nullable=False
    )
    reference_number = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    processed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    extra_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="financial_transactions")
    customer = relationship("Customer", back_populates="transactions")
    invoice = relationship("Invoice", back_populates="transactions")
    manifest = relationship("Manifest", back_populates="transactions")
    processed_by = relationship("User", back_populates="processed_transactions")
