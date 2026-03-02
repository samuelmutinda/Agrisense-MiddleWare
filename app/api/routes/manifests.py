"""API routes for Manifest resource."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import manifest as manifest_schema
from app.services import manifest_service


router = APIRouter(prefix="/manifests", tags=["manifests"])


@router.post(
    "",
    response_model=manifest_schema.ManifestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new manifest"
)
async def create_manifest(
    payload: manifest_schema.ManifestCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create a new shipping manifest."""
    try:
        return await manifest_service.create_manifest(
            session=session, data=payload, auth=auth
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=manifest_schema.ManifestListResponse,
    summary="List manifests"
)
async def list_manifests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    truck_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List manifests with pagination and filtering."""
    return await manifest_service.list_manifests(
        session=session,
        auth=auth,
        page=page,
        page_size=page_size,
        status=status,
        truck_id=truck_id,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to
    )


@router.get(
    "/{manifest_id}",
    response_model=manifest_schema.ManifestResponse,
    summary="Get manifest by ID"
)
async def get_manifest(
    manifest_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Get a specific manifest by ID."""
    try:
        return await manifest_service.get_manifest_by_id(
            session=session,
            manifest_id=manifest_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{manifest_id}",
    response_model=manifest_schema.ManifestResponse,
    summary="Update manifest"
)
async def update_manifest(
    manifest_id: uuid.UUID,
    payload: manifest_schema.ManifestUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update a manifest."""
    try:
        return await manifest_service.update_manifest(
            session=session,
            manifest_id=manifest_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{manifest_id}/status",
    response_model=manifest_schema.ManifestResponse,
    summary="Update manifest status"
)
async def update_manifest_status(
    manifest_id: uuid.UUID,
    payload: manifest_schema.ManifestStatusUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update manifest status (e.g., in_transit, delivered)."""
    try:
        return await manifest_service.update_manifest_status(
            session=session,
            manifest_id=manifest_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{manifest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete manifest"
)
async def delete_manifest(
    manifest_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Delete a manifest (only draft or cancelled)."""
    try:
        await manifest_service.delete_manifest(
            session=session,
            manifest_id=manifest_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
