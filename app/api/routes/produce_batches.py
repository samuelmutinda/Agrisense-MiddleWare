"""API routes for ProduceBatch resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import produce_batch as batch_schema
from app.services import produce_batch_service


router = APIRouter(prefix="/produce-batches", tags=["produce-batches"])


@router.post(
    "",
    response_model=batch_schema.ProduceBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new produce batch"
)
async def create_produce_batch(
    payload: batch_schema.ProduceBatchCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create a new produce batch."""
    try:
        return await produce_batch_service.create_produce_batch(
            session=session, data=payload, auth=auth
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=batch_schema.ProduceBatchListResponse,
    summary="List produce batches"
)
async def list_produce_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    crop_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    storage_unit_id: Optional[uuid.UUID] = Query(None),
    quality_grade: Optional[str] = Query(None),
    expiring_within_days: Optional[int] = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List produce batches with filtering."""
    return await produce_batch_service.list_produce_batches(
        session=session,
        auth=auth,
        page=page,
        page_size=page_size,
        status=status,
        crop_id=crop_id,
        customer_id=customer_id,
        storage_unit_id=storage_unit_id,
        quality_grade=quality_grade,
        expiring_within_days=expiring_within_days
    )


@router.get(
    "/{batch_id}",
    response_model=batch_schema.ProduceBatchResponse,
    summary="Get produce batch by ID"
)
async def get_produce_batch(
    batch_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Get a specific produce batch by ID."""
    try:
        return await produce_batch_service.get_produce_batch_by_id(
            session=session,
            batch_id=batch_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{batch_id}",
    response_model=batch_schema.ProduceBatchResponse,
    summary="Update produce batch"
)
async def update_produce_batch(
    batch_id: uuid.UUID,
    payload: batch_schema.ProduceBatchUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update a produce batch."""
    try:
        return await produce_batch_service.update_produce_batch(
            session=session,
            batch_id=batch_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{batch_id}/quality",
    response_model=batch_schema.ProduceBatchResponse,
    summary="Update batch quality"
)
async def update_batch_quality(
    batch_id: uuid.UUID,
    payload: batch_schema.BatchQualityUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update batch quality grade."""
    try:
        return await produce_batch_service.update_batch_quality(
            session=session,
            batch_id=batch_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete produce batch"
)
async def delete_produce_batch(
    batch_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Delete (reject) a produce batch."""
    try:
        await produce_batch_service.delete_produce_batch(
            session=session,
            batch_id=batch_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
