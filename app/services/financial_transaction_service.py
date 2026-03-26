"""Service layer for FinancialTransaction operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.financial_transaction import FinancialTransaction
from app.db.models.customer import Customer
from app.db.models.user import User
from app.schemas import financial_transaction as fin_schema


async def create_financial_transaction(
    session: AsyncSession,
    data: fin_schema.FinancialTransactionCreate,
    auth: AuthContext
) -> fin_schema.FinancialTransactionResponse:
    """Create a new financial transaction."""
    tx = FinancialTransaction(
        tenant_id=auth.tenant_id,
        transaction_type=data.transaction_type.value,
        amount=data.amount,
        currency=data.currency,
        customer_id=data.customer_id,
        invoice_id=data.invoice_id,
        manifest_id=data.manifest_id,
        payment_method=data.payment_method.value,
        reference_number=data.reference_number,
        description=data.description,
        processed_by_user_id=auth.user_id,
        extra_metadata=data.metadata,
        status="completed"
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return await get_financial_transaction_by_id(session, tx.id, auth)


async def get_financial_transaction_by_id(
    session: AsyncSession,
    tx_id: uuid.UUID,
    auth: AuthContext
) -> fin_schema.FinancialTransactionResponse:
    """Get financial transaction by ID."""
    stmt = select(FinancialTransaction).where(
        FinancialTransaction.id == tx_id,
        FinancialTransaction.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    tx = result.scalar_one_or_none()
    if not tx:
        raise ValueError(f"Transaction {tx_id} not found")
    
    response = fin_schema.FinancialTransactionResponse.model_validate(tx)
    if tx.customer_id:
        customer = await session.get(Customer, tx.customer_id)
        if customer:
            response.customer_name = customer.name
    user = await session.get(User, tx.processed_by_user_id)
    if user:
        response.processed_by_name = f"{user.first_name} {user.last_name}"
    return response


async def list_financial_transactions(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> fin_schema.FinancialTransactionListResponse:
    """List financial transactions with filtering."""
    stmt = select(FinancialTransaction).where(FinancialTransaction.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(FinancialTransaction.id)).where(FinancialTransaction.tenant_id == auth.tenant_id)
    sum_stmt = select(func.sum(FinancialTransaction.amount)).where(FinancialTransaction.tenant_id == auth.tenant_id)
    
    if transaction_type:
        stmt = stmt.where(FinancialTransaction.transaction_type == transaction_type)
        count_stmt = count_stmt.where(FinancialTransaction.transaction_type == transaction_type)
        sum_stmt = sum_stmt.where(FinancialTransaction.transaction_type == transaction_type)
    if status:
        stmt = stmt.where(FinancialTransaction.status == status)
        count_stmt = count_stmt.where(FinancialTransaction.status == status)
        sum_stmt = sum_stmt.where(FinancialTransaction.status == status)
    if customer_id:
        stmt = stmt.where(FinancialTransaction.customer_id == customer_id)
        count_stmt = count_stmt.where(FinancialTransaction.customer_id == customer_id)
        sum_stmt = sum_stmt.where(FinancialTransaction.customer_id == customer_id)
    if date_from:
        stmt = stmt.where(FinancialTransaction.created_at >= date_from)
        count_stmt = count_stmt.where(FinancialTransaction.created_at >= date_from)
        sum_stmt = sum_stmt.where(FinancialTransaction.created_at >= date_from)
    if date_to:
        stmt = stmt.where(FinancialTransaction.created_at <= date_to)
        count_stmt = count_stmt.where(FinancialTransaction.created_at <= date_to)
        sum_stmt = sum_stmt.where(FinancialTransaction.created_at <= date_to)
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    sum_result = await session.execute(sum_stmt)
    total_amount = sum_result.scalar() or 0.0
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(FinancialTransaction.created_at.desc())
    result = await session.execute(stmt)
    txs = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    return fin_schema.FinancialTransactionListResponse(
        items=[fin_schema.FinancialTransactionResponse.model_validate(t) for t in txs],
        total=total,
        total_amount=total_amount,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
