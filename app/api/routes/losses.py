from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import loss as loss_schema
from app.services import loss_service

router = APIRouter(prefix="/losses", tags=["losses"])


@router.get("", response_model=list[loss_schema.LossResponse])
async def list_losses(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await loss_service.get_losses_with_ledger(session, auth.tenant_id)


@router.get("/{loss_id}", response_model=loss_schema.LossResponse)
async def get_loss(
    loss_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await loss_service.get_loss_by_id(session, loss_id, auth.tenant_id)


@router.post("/transfer", response_model=loss_schema.LossResponse, status_code=status.HTTP_201_CREATED)
async def record_transfer_loss(
    payload: loss_schema.TransferLossCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await loss_service.record_transfer_loss(session, payload, auth)


@router.post("/storage", response_model=loss_schema.LossResponse, status_code=status.HTTP_201_CREATED)
async def record_storage_loss(
    payload: loss_schema.StorageLossCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await loss_service.record_storage_loss(session, payload, auth)