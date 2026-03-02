"""API routes for Inspection resource."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import inspection as inspection_schema
from app.services import inspection_service


router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post(
    "",
    response_model=inspection_schema.InspectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an inspection"
)
async def create_inspection(
    payload: inspection_schema.InspectionCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create a new inspection."""
    try:
        return await inspection_service.create_inspection(
            session=session, data=payload, auth=auth
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=inspection_schema.InspectionListResponse,
    summary="List inspections"
)
async def list_inspections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    produce_batch_id: Optional[uuid.UUID] = Query(None),
    storage_unit_id: Optional[uuid.UUID] = Query(None),
    inspection_type: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    inspector_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List inspections with filtering."""
    return await inspection_service.list_inspections(
        session=session,
        auth=auth,
        page=page,
        page_size=page_size,
        produce_batch_id=produce_batch_id,
        storage_unit_id=storage_unit_id,
        inspection_type=inspection_type,
        result=result,
        inspector_id=inspector_id,
        date_from=date_from,
        date_to=date_to
    )


@router.get(
    "/{inspection_id}",
    response_model=inspection_schema.InspectionResponse,
    summary="Get inspection by ID"
)
async def get_inspection(
    inspection_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Get a specific inspection by ID."""
    try:
        return await inspection_service.get_inspection_by_id(
            session=session,
            inspection_id=inspection_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{inspection_id}",
    response_model=inspection_schema.InspectionResponse,
    summary="Update inspection"
)
async def update_inspection(
    inspection_id: uuid.UUID,
    payload: inspection_schema.InspectionUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update/complete an inspection."""
    try:
        return await inspection_service.update_inspection(
            session=session,
            inspection_id=inspection_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{inspection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete inspection"
)
async def delete_inspection(
    inspection_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Delete a pending inspection."""
    try:
        await inspection_service.delete_inspection(
            session=session,
            inspection_id=inspection_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
