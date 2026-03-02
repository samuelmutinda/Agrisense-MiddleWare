"""API routes for MaintenanceRecord resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import maintenance_record as maint_schema
from app.services import maintenance_record_service

router = APIRouter(prefix="/maintenance-records", tags=["maintenance-records"])


@router.post("", response_model=maint_schema.MaintenanceRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance_record(payload: maint_schema.MaintenanceRecordCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await maintenance_record_service.create_maintenance_record(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=maint_schema.MaintenanceRecordListResponse)
async def list_maintenance_records(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), asset_id: Optional[uuid.UUID] = None, maintenance_type: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await maintenance_record_service.list_maintenance_records(session=session, auth=auth, page=page, page_size=page_size, asset_id=asset_id, maintenance_type=maintenance_type, status=status, priority=priority)


@router.get("/{record_id}", response_model=maint_schema.MaintenanceRecordResponse)
async def get_maintenance_record(record_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await maintenance_record_service.get_maintenance_record_by_id(session=session, record_id=record_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{record_id}", response_model=maint_schema.MaintenanceRecordResponse)
async def update_maintenance_record(record_id: uuid.UUID, payload: maint_schema.MaintenanceRecordUpdate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await maintenance_record_service.update_maintenance_record(session=session, record_id=record_id, data=payload, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
