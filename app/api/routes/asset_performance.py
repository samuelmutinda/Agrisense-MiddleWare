"""API routes for AssetPerformance resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import asset_performance as asset_schema
from app.services import asset_performance_service

router = APIRouter(prefix="/asset-performance", tags=["asset-performance"])


@router.post("", response_model=asset_schema.AssetPerformanceResponse, status_code=status.HTTP_201_CREATED)
async def create_asset_performance(payload: asset_schema.AssetPerformanceCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await asset_performance_service.create_asset_performance(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=asset_schema.AssetPerformanceListResponse)
async def list_asset_performance(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), asset_id: Optional[uuid.UUID] = None, asset_type: Optional[str] = None, status: Optional[str] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await asset_performance_service.list_asset_performance(session=session, auth=auth, page=page, page_size=page_size, asset_id=asset_id, asset_type=asset_type, status=status)


@router.get("/{record_id}", response_model=asset_schema.AssetPerformanceResponse)
async def get_asset_performance(record_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await asset_performance_service.get_asset_performance_by_id(session=session, record_id=record_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
