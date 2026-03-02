"""API routes for KpiMetric resource."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import kpi_metric as kpi_schema
from app.services import kpi_metric_service

router = APIRouter(prefix="/kpi-metrics", tags=["kpi-metrics"])


@router.post("", response_model=kpi_schema.KpiMetricResponse, status_code=status.HTTP_201_CREATED)
async def create_kpi_metric(payload: kpi_schema.KpiMetricCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await kpi_metric_service.create_kpi_metric(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=kpi_schema.KpiMetricListResponse)
async def list_kpi_metrics(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), category: Optional[str] = None, facility_id: Optional[uuid.UUID] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await kpi_metric_service.list_kpi_metrics(session=session, auth=auth, page=page, page_size=page_size, category=category, facility_id=facility_id, date_from=date_from, date_to=date_to)


@router.get("/{metric_id}", response_model=kpi_schema.KpiMetricResponse)
async def get_kpi_metric(metric_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await kpi_metric_service.get_kpi_metric_by_id(session=session, metric_id=metric_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
