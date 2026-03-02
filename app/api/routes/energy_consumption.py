"""API routes for EnergyConsumption resource."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import energy_consumption as energy_schema
from app.services import energy_consumption_service

router = APIRouter(prefix="/energy-consumption", tags=["energy-consumption"])


@router.post("", response_model=energy_schema.EnergyConsumptionResponse, status_code=status.HTTP_201_CREATED)
async def create_energy_consumption(payload: energy_schema.EnergyConsumptionCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await energy_consumption_service.create_energy_consumption(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=energy_schema.EnergyConsumptionListResponse)
async def list_energy_consumption(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), facility_id: Optional[uuid.UUID] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, energy_source: Optional[str] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await energy_consumption_service.list_energy_consumption(session=session, auth=auth, page=page, page_size=page_size, facility_id=facility_id, date_from=date_from, date_to=date_to, energy_source=energy_source)


@router.get("/{record_id}", response_model=energy_schema.EnergyConsumptionResponse)
async def get_energy_consumption(record_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await energy_consumption_service.get_energy_consumption_by_id(session=session, record_id=record_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
