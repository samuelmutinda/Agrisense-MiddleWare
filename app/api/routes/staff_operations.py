"""API routes for StaffOperation resource."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import staff_operation as staff_schema
from app.services import staff_operation_service

router = APIRouter(prefix="/staff-operations", tags=["staff-operations"])


@router.post("", response_model=staff_schema.StaffOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_staff_operation(payload: staff_schema.StaffOperationCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await staff_operation_service.create_staff_operation(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=staff_schema.StaffOperationListResponse)
async def list_staff_operations(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), staff_id: Optional[uuid.UUID] = None, facility_id: Optional[uuid.UUID] = None, operation_type: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await staff_operation_service.list_staff_operations(session=session, auth=auth, page=page, page_size=page_size, staff_id=staff_id, facility_id=facility_id, operation_type=operation_type, date_from=date_from, date_to=date_to)


@router.get("/{record_id}", response_model=staff_schema.StaffOperationResponse)
async def get_staff_operation(record_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await staff_operation_service.get_staff_operation_by_id(session=session, record_id=record_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{record_id}", response_model=staff_schema.StaffOperationResponse)
async def update_staff_operation(record_id: uuid.UUID, payload: staff_schema.StaffOperationUpdate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await staff_operation_service.update_staff_operation(session=session, record_id=record_id, data=payload, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
