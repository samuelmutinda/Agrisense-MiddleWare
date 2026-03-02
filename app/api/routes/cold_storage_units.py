from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import cold_storage_unit as cold_storage_unit_schema
from app.services import cold_storage_unit_service

router = APIRouter(prefix="/cold-storage-units", tags=["cold-storage-units"])


@router.get("", response_model=list[cold_storage_unit_schema.ColdStorageUnitResponse])
async def list_cold_storage_units(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.get_cold_storage_units(
        session, auth.tenant_id
    )


@router.get(
    "/{cold_storage_unit_id}",
    response_model=cold_storage_unit_schema.ColdStorageUnitResponse,
)
async def get_cold_storage_unit(
    cold_storage_unit_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.get_cold_storage_unit_by_id(
        session, cold_storage_unit_id, auth.tenant_id
    )


@router.post(
    "",
    response_model=cold_storage_unit_schema.ColdStorageUnitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cold_storage_unit(
    payload: cold_storage_unit_schema.ColdStorageUnitCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.create_cold_storage_unit(
        session, payload, auth.tenant_id
    )


@router.put(
    "/{cold_storage_unit_id}",
    response_model=cold_storage_unit_schema.ColdStorageUnitResponse,
)
async def update_cold_storage_unit(
    cold_storage_unit_id: uuid.UUID,
    payload: cold_storage_unit_schema.ColdStorageUnitCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.update_cold_storage_unit(
        session, cold_storage_unit_id, payload, auth.tenant_id
    )


@router.delete("/{cold_storage_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cold_storage_unit(
    cold_storage_unit_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    await cold_storage_unit_service.delete_cold_storage_unit(
        session, cold_storage_unit_id, auth.tenant_id
    )
    return None
