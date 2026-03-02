"""API routes for Invoice resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import invoice as inv_schema
from app.services import invoice_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=inv_schema.InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(payload: inv_schema.InvoiceCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await invoice_service.create_invoice(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=inv_schema.InvoiceListResponse)
async def list_invoices(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status: Optional[str] = None, customer_id: Optional[uuid.UUID] = None, overdue_only: bool = False, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await invoice_service.list_invoices(session=session, auth=auth, page=page, page_size=page_size, status=status, customer_id=customer_id, overdue_only=overdue_only)


@router.get("/{invoice_id}", response_model=inv_schema.InvoiceResponse)
async def get_invoice(invoice_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await invoice_service.get_invoice_by_id(session=session, invoice_id=invoice_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{invoice_id}", response_model=inv_schema.InvoiceResponse)
async def update_invoice(invoice_id: uuid.UUID, payload: inv_schema.InvoiceUpdate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await invoice_service.update_invoice(session=session, invoice_id=invoice_id, data=payload, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(invoice_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        await invoice_service.delete_invoice(session=session, invoice_id=invoice_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
