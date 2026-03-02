from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import transfer as transfer_schema
from app.services import transfer_service

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.get("", response_model=list[transfer_schema.TransferResponse])
async def list_transfers(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await transfer_service.get_transfers_with_ledger(
        session=session,
        tenant_id=auth.tenant_id
    )


@router.get("/{transfer_id}", response_model=transfer_schema.TransferResponse)
async def get_transfer(
    transfer_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await transfer_service.get_transfer_by_id(
        session=session,
        transfer_id=transfer_id,
        tenant_id=auth.tenant_id
    )


@router.post(
    "",
    response_model=transfer_schema.TransferResponse,
    status_code=status.HTTP_201_CREATED,
)
async def initiate_transfer(
    payload: transfer_schema.TransferCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await transfer_service.initiate_transfer(
        session=session, data=payload, auth=auth
    )


@router.post("/{transfer_id}/cancel", response_model=transfer_schema.TransferResponse)
async def cancel_transfer(
    transfer_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await transfer_service.cancel_transfer(
        session=session, transfer_id=transfer_id, auth=auth
    )


@router.post("/{transfer_id}/complete", response_model=transfer_schema.TransferResponse)
async def complete_transfer(
    transfer_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await transfer_service.complete_transfer(
        session=session, transfer_id=transfer_id, auth=auth
    )