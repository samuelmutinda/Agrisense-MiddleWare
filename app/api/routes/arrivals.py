from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import arrival as arrival_schema
from app.services import arrival_service, inventory_service

router = APIRouter(prefix="/arrivals", tags=["arrivals"])


@router.post(
    "",
    response_model=arrival_schema.ArrivalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_arrival(
    payload: arrival_schema.ArrivalCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await arrival_service.create_arrival(session=session, data=payload, auth=auth)


@router.get("", response_model=list[arrival_schema.ArrivalResponse])
async def list_arrivals(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await arrival_service.get_arrivals_with_ledger(
        session=session,
        auth=auth
    )


@router.get("/{arrival_id}", response_model=arrival_schema.ArrivalResponse)
async def get_arrival(
    arrival_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await arrival_service.get_arrival_by_id(
        session=session,
        arrival_id=arrival_id,
        tenant_id=auth.tenant_id
    )