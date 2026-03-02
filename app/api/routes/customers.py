from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import customer as customer_schema
from app.services import customer_service

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("", response_model=list[customer_schema.CustomerResponse])
async def list_customers(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await customer_service.get_customers(session, auth.tenant_id)

@router.get(path="/{customer_id}", response_model=customer_schema.CustomerResponse)
async def get_customer_by_id(
        customer_id: uuid.UUID,
        session: AsyncSession = Depends(deps.get_db),
        auth: AuthContext = Depends(deps.get_auth_context),
)->customer_schema.CustomerResponse:
    return await customer_service.get_customer_by_id(
        session,
        customer_id,
        tenant_id=auth.tenant_id
    )

@router.post(
    "",
    response_model=customer_schema.CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    payload: customer_schema.CustomerCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await customer_service.create_customer(session, payload, auth.tenant_id)

@router.put("/{customer_id}", response_model=customer_schema.CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    payload: customer_schema.CustomerCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await customer_service.update_customer(
        session, customer_id, payload, auth.tenant_id
    )

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    await customer_service.delete_customer(session, customer_id, auth.tenant_id)
    return None