"""API routes for Certification resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import certification as cert_schema
from app.services import certification_service


router = APIRouter(prefix="/certifications", tags=["certifications"])


@router.post(
    "",
    response_model=cert_schema.CertificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a certification"
)
async def create_certification(
    payload: cert_schema.CertificationCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create a new certification."""
    try:
        return await certification_service.create_certification(
            session=session, data=payload, auth=auth
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=cert_schema.CertificationListResponse,
    summary="List certifications"
)
async def list_certifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    organization_id: Optional[uuid.UUID] = Query(None),
    certification_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    expiring_within_days: Optional[int] = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List certifications with filtering."""
    return await certification_service.list_certifications(
        session=session,
        auth=auth,
        page=page,
        page_size=page_size,
        organization_id=organization_id,
        certification_type=certification_type,
        status=status,
        expiring_within_days=expiring_within_days
    )


@router.get(
    "/{cert_id}",
    response_model=cert_schema.CertificationResponse,
    summary="Get certification by ID"
)
async def get_certification(
    cert_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Get a specific certification by ID."""
    try:
        return await certification_service.get_certification_by_id(
            session=session,
            cert_id=cert_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{cert_id}",
    response_model=cert_schema.CertificationResponse,
    summary="Update certification"
)
async def update_certification(
    cert_id: uuid.UUID,
    payload: cert_schema.CertificationUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update a certification."""
    try:
        return await certification_service.update_certification(
            session=session,
            cert_id=cert_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{cert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete certification"
)
async def delete_certification(
    cert_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Delete a certification."""
    try:
        await certification_service.delete_certification(
            session=session,
            cert_id=cert_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
