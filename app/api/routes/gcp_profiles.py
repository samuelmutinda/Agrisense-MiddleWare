"""API routes for GcpProfile resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import gcp_profile as gcp_schema
from app.services import gcp_profile_service

router = APIRouter(prefix="/gcp-profiles", tags=["gcp-profiles"])


@router.post("", response_model=gcp_schema.GcpProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_gcp_profile(payload: gcp_schema.GcpProfileCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await gcp_profile_service.create_gcp_profile(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=gcp_schema.GcpProfileListResponse)
async def list_gcp_profiles(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), facility_id: Optional[uuid.UUID] = None, certification_level: Optional[str] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await gcp_profile_service.list_gcp_profiles(session=session, auth=auth, page=page, page_size=page_size, facility_id=facility_id, certification_level=certification_level)


@router.get("/{profile_id}", response_model=gcp_schema.GcpProfileResponse)
async def get_gcp_profile(profile_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await gcp_profile_service.get_gcp_profile_by_id(session=session, profile_id=profile_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{profile_id}", response_model=gcp_schema.GcpProfileResponse)
async def update_gcp_profile(profile_id: uuid.UUID, payload: gcp_schema.GcpProfileUpdate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await gcp_profile_service.update_gcp_profile(session=session, profile_id=profile_id, data=payload, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
