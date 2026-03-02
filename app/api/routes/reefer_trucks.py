"""API routes for ReeferTruck resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import reefer_truck as truck_schema
from app.services import reefer_truck_service


router = APIRouter(prefix="/reefer-trucks", tags=["reefer-trucks"])


@router.post(
    "",
    response_model=truck_schema.ReeferTruckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new reefer truck"
)
async def create_reefer_truck(
    payload: truck_schema.ReeferTruckCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create a new reefer truck in the fleet."""
    try:
        return await reefer_truck_service.create_reefer_truck(
            session=session, data=payload, auth=auth
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=truck_schema.ReeferTruckListResponse,
    summary="List reefer trucks"
)
async def list_reefer_trucks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    assigned_driver_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List reefer trucks with pagination and filtering."""
    return await reefer_truck_service.list_reefer_trucks(
        session=session,
        auth=auth,
        page=page,
        page_size=page_size,
        status=status,
        assigned_driver_id=assigned_driver_id,
        search=search
    )


@router.get(
    "/{truck_id}",
    response_model=truck_schema.ReeferTruckResponse,
    summary="Get reefer truck by ID"
)
async def get_reefer_truck(
    truck_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Get a specific reefer truck by ID."""
    try:
        return await reefer_truck_service.get_reefer_truck_by_id(
            session=session,
            truck_id=truck_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{truck_id}",
    response_model=truck_schema.ReeferTruckResponse,
    summary="Update reefer truck"
)
async def update_reefer_truck(
    truck_id: uuid.UUID,
    payload: truck_schema.ReeferTruckUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update a reefer truck."""
    try:
        return await reefer_truck_service.update_reefer_truck(
            session=session,
            truck_id=truck_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/{truck_id}/location",
    response_model=truck_schema.ReeferTruckResponse,
    summary="Update truck location"
)
async def update_truck_location(
    truck_id: uuid.UUID,
    payload: truck_schema.TruckLocationUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update truck location and telemetry."""
    try:
        return await reefer_truck_service.update_truck_location(
            session=session,
            truck_id=truck_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{truck_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete reefer truck"
)
async def delete_reefer_truck(
    truck_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Delete (set out of service) a reefer truck."""
    try:
        await reefer_truck_service.delete_reefer_truck(
            session=session,
            truck_id=truck_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
