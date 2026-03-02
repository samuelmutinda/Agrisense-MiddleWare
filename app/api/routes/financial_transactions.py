"""API routes for FinancialTransaction resource."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import financial_transaction as fin_schema
from app.services import financial_transaction_service

router = APIRouter(prefix="/financial-transactions", tags=["financial-transactions"])


@router.post("", response_model=fin_schema.FinancialTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_financial_transaction(
    payload: fin_schema.FinancialTransactionCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    try:
        return await financial_transaction_service.create_financial_transaction(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=fin_schema.FinancialTransactionListResponse)
async def list_financial_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await financial_transaction_service.list_financial_transactions(
        session=session, auth=auth, page=page, page_size=page_size,
        transaction_type=transaction_type, status=status, customer_id=customer_id,
        date_from=date_from, date_to=date_to
    )


@router.get("/{tx_id}", response_model=fin_schema.FinancialTransactionResponse)
async def get_financial_transaction(
    tx_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    try:
        return await financial_transaction_service.get_financial_transaction_by_id(session=session, tx_id=tx_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
