"""API routes for OperatingCost resource."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import operating_cost as cost_schema
from app.services import operating_cost_service

router = APIRouter(prefix="/operating-costs", tags=["operating-costs"])


@router.post("", response_model=cost_schema.OperatingCostResponse, status_code=status.HTTP_201_CREATED)
async def create_operating_cost(payload: cost_schema.OperatingCostCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await operating_cost_service.create_operating_cost(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=cost_schema.OperatingCostListResponse)
async def list_operating_costs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), facility_id: Optional[uuid.UUID] = None, category: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await operating_cost_service.list_operating_costs(session=session, auth=auth, page=page, page_size=page_size, facility_id=facility_id, category=category, date_from=date_from, date_to=date_to)


@router.get("/{record_id}", response_model=cost_schema.OperatingCostResponse)
async def get_operating_cost(record_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await operating_cost_service.get_operating_cost_by_id(session=session, record_id=record_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
