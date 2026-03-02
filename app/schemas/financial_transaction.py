"""Pydantic schemas for FinancialTransaction resource."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    SALE = "sale"
    PURCHASE = "purchase"
    REFUND = "refund"
    EXPENSE = "expense"
    ADJUSTMENT = "adjustment"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CASH = "cash"
    MPESA = "mpesa"
    BANK_TRANSFER = "bank_transfer"
    CREDIT = "credit"
    CHECK = "check"


class FinancialTransactionCreate(BaseModel):
    """Schema for creating a financial transaction."""
    transaction_type: TransactionType
    amount: float = Field(..., gt=0)
    currency: str = Field(default="KES", max_length=3)
    customer_id: Optional[uuid.UUID] = None
    invoice_id: Optional[uuid.UUID] = None
    manifest_id: Optional[uuid.UUID] = None
    payment_method: PaymentMethod
    reference_number: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    metadata: Optional[dict] = None


class FinancialTransactionResponse(BaseModel):
    """Schema for financial transaction response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    transaction_type: TransactionType
    status: TransactionStatus
    amount: float
    currency: str
    customer_id: Optional[uuid.UUID] = None
    customer_name: Optional[str] = None
    invoice_id: Optional[uuid.UUID] = None
    invoice_number: Optional[str] = None
    manifest_id: Optional[uuid.UUID] = None
    payment_method: PaymentMethod
    reference_number: Optional[str] = None
    description: Optional[str] = None
    processed_by_user_id: uuid.UUID
    processed_by_name: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FinancialTransactionListResponse(BaseModel):
    """Schema for paginated financial transaction list."""
    items: list[FinancialTransactionResponse]
    total: int
    total_amount: float = 0.0
    page: int
    page_size: int
    total_pages: int
