"""Pydantic schemas for Invoice resource."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class InvoiceLineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    tax_rate: float = 0.0
    total: Optional[float] = None


class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    manifest_id: Optional[uuid.UUID] = None
    invoice_number: Optional[str] = Field(None, max_length=50)
    issue_date: date
    due_date: date
    currency: str = Field(default="KES", max_length=3)
    line_items: List[InvoiceLineItem]
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    notes: Optional[str] = None
    metadata: Optional[dict] = None


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    due_date: Optional[date] = None
    paid_amount: Optional[float] = None
    paid_date: Optional[date] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_number: str
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    manifest_id: Optional[uuid.UUID] = None
    status: InvoiceStatus
    issue_date: date
    due_date: date
    currency: str
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    paid_amount: float = 0.0
    balance_due: float
    paid_date: Optional[date] = None
    line_items: Optional[List[dict]] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    total_outstanding: float = 0.0
    page: int
    page_size: int
    total_pages: int
