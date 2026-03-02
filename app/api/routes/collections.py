from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import collection as collection_schema
from app.services import collection_service

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("", response_model=list[collection_schema.CollectionResponse])
async def list_collections(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await collection_service.get_collections_with_ledger(
        session=session,
        tenant_id=auth.tenant_id
    )


@router.post(
    "",
    response_model=collection_schema.CollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_collection(
    payload: collection_schema.CollectionCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await collection_service.record_collection(
        session=session, data=payload, auth=auth
    )

@router.get("/{collection_id}", response_model=collection_schema.CollectionResponse)
async def get_collection(
    collection_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await collection_service.get_collection_by_id(
        session=session,
        collection_id=collection_id,
        tenant_id=auth.tenant_id
    )
