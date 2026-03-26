"""Service layer for Invoice operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.invoice import Invoice
from app.db.models.customer import Customer
from app.schemas import invoice as inv_schema


def generate_invoice_number(tenant_id: uuid.UUID) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"INV-{str(tenant_id)[:4].upper()}-{timestamp}"


async def create_invoice(
    session: AsyncSession,
    data: inv_schema.InvoiceCreate,
    auth: AuthContext
) -> inv_schema.InvoiceResponse:
    invoice_number = data.invoice_number or generate_invoice_number(auth.tenant_id)
    
    subtotal = sum(item.quantity * item.unit_price for item in data.line_items)
    total_amount = subtotal + data.tax_amount - data.discount_amount
    
    invoice = Invoice(
        tenant_id=auth.tenant_id,
        invoice_number=invoice_number,
        customer_id=data.customer_id,
        manifest_id=data.manifest_id,
        issue_date=data.issue_date,
        due_date=data.due_date,
        currency=data.currency,
        subtotal=subtotal,
        tax_amount=data.tax_amount,
        discount_amount=data.discount_amount,
        total_amount=total_amount,
        line_items=[item.model_dump() for item in data.line_items],
        notes=data.notes,
        extra_metadata=data.metadata,
        status="draft"
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)
    return await get_invoice_by_id(session, invoice.id, auth)


async def get_invoice_by_id(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    auth: AuthContext
) -> inv_schema.InvoiceResponse:
    stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")
    
    response = inv_schema.InvoiceResponse.model_validate(invoice)
    response.balance_due = invoice.total_amount - invoice.paid_amount
    
    customer = await session.get(Customer, invoice.customer_id)
    if customer:
        response.customer_name = customer.name
    return response


async def list_invoices(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None,
    overdue_only: bool = False
) -> inv_schema.InvoiceListResponse:
    stmt = select(Invoice).where(Invoice.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(Invoice.id)).where(Invoice.tenant_id == auth.tenant_id)
    outstanding_stmt = select(func.sum(Invoice.total_amount - Invoice.paid_amount)).where(
        Invoice.tenant_id == auth.tenant_id,
        Invoice.status.in_(["sent", "overdue", "partial"])
    )
    
    if status:
        stmt = stmt.where(Invoice.status == status)
        count_stmt = count_stmt.where(Invoice.status == status)
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
        count_stmt = count_stmt.where(Invoice.customer_id == customer_id)
    if overdue_only:
        stmt = stmt.where(Invoice.due_date < date.today(), Invoice.status.in_(["sent", "partial"]))
        count_stmt = count_stmt.where(Invoice.due_date < date.today(), Invoice.status.in_(["sent", "partial"]))
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    outstanding_result = await session.execute(outstanding_stmt)
    total_outstanding = outstanding_result.scalar() or 0.0
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(Invoice.due_date.asc())
    result = await session.execute(stmt)
    invoices = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    items = []
    for inv in invoices:
        response = inv_schema.InvoiceResponse.model_validate(inv)
        response.balance_due = inv.total_amount - inv.paid_amount
        items.append(response)
    
    return inv_schema.InvoiceListResponse(
        items=items, total=total, total_outstanding=total_outstanding,
        page=page, page_size=page_size, total_pages=total_pages
    )


async def update_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    data: inv_schema.InvoiceUpdate,
    auth: AuthContext
) -> inv_schema.InvoiceResponse:
    stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")
    
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = data.status.value
    for field, value in update_data.items():
        setattr(invoice, field, value)
    
    # Auto-update status based on payment
    if invoice.paid_amount >= invoice.total_amount:
        invoice.status = "paid"
    elif invoice.paid_amount > 0:
        invoice.status = "partial"
    
    await session.commit()
    return await get_invoice_by_id(session, invoice_id, auth)


async def delete_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    auth: AuthContext
) -> bool:
    stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")
    if invoice.status not in ("draft", "cancelled"):
        raise ValueError("Can only delete draft or cancelled invoices")
    await session.delete(invoice)
    await session.commit()
    return True
