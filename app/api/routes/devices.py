from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import device as device_schema
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[device_schema.DeviceResponse])
async def list_devices(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await device_service.get_devices(session, auth.tenant_id)


@router.get(
    "/{device_id}",
    response_model=device_schema.DeviceResponse,
)
async def get_device(
    device_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await device_service.get_device_by_id(
        session, device_id, auth.tenant_id
    )


@router.post(
    "",
    # Response now includes automated dev_eui and app_key
    # so the user can configure their hardware
    response_model=device_schema.DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device(
    payload: device_schema.DeviceCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await device_service.create_device(
        session, payload, auth.tenant_id
    )


# The set_device_keys (PUT /keys) endpoint is removed
# as keys are now generated automatically during creation.


@router.put(
    "/{device_id}",
    response_model=device_schema.DeviceResponse,
)
async def update_device(
    device_id: uuid.UUID,
    payload: device_schema.DeviceUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await device_service.update_device(
        session, device_id, payload, auth.tenant_id
    )


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    await device_service.delete_device(session, device_id, auth.tenant_id)
    return None