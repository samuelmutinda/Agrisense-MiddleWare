"""API routes for Organization resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import organization as org_schema
from app.services import organization_service


router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post(
    "",
    response_model=org_schema.OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization"
)
async def create_organization(
    payload: org_schema.OrganizationCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create a new organization within the tenant."""
    try:
        return await organization_service.create_organization(
            session=session, data=payload, auth=auth
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=org_schema.OrganizationListResponse,
    summary="List organizations"
)
async def list_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    organization_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List organizations with pagination and filtering."""
    return await organization_service.list_organizations(
        session=session,
        auth=auth,
        page=page,
        page_size=page_size,
        organization_type=organization_type,
        status=status,
        search=search
    )


@router.get(
    "/{organization_id}",
    response_model=org_schema.OrganizationResponse,
    summary="Get organization by ID"
)
async def get_organization(
    organization_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Get a specific organization by ID."""
    try:
        return await organization_service.get_organization_by_id(
            session=session,
            organization_id=organization_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{organization_id}",
    response_model=org_schema.OrganizationResponse,
    summary="Update organization"
)
async def update_organization(
    organization_id: uuid.UUID,
    payload: org_schema.OrganizationUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update an organization."""
    try:
        return await organization_service.update_organization(
            session=session,
            organization_id=organization_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization"
)
async def delete_organization(
    organization_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Delete (suspend) an organization."""
    try:
        await organization_service.delete_organization(
            session=session,
            organization_id=organization_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
