from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import spoilage as spoilage_schema
from app.services import spoilage_service

router = APIRouter(prefix="/spoilages", tags=["spoilages"])


@router.get("", response_model=list[spoilage_schema.SpoilageResponse])
async def list_spoilages(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await spoilage_service.get_spoilages_with_ledger(
        session=session,
        tenant_id=auth.tenant_id
    )


@router.get("/{spoilage_id}", response_model=spoilage_schema.SpoilageResponse)
async def get_spoilage(
    spoilage_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await spoilage_service.get_spoilage_by_id(
        session=session,
        spoilage_id=spoilage_id,
        tenant_id=auth.tenant_id
    )


@router.post(
    "",
    response_model=spoilage_schema.SpoilageResponse,
    status_code=status.HTTP_201_CREATED
)
async def record_spoilage(
    payload: spoilage_schema.SpoilageCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await spoilage_service.record_spoilage(
        session=session,
        data=payload,
        auth=auth
    )