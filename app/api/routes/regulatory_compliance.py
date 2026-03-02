"""API routes for RegulatoryCompliance resource."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import regulatory_compliance as reg_schema
from app.services import regulatory_compliance_service

router = APIRouter(prefix="/regulatory-compliance", tags=["regulatory-compliance"])


@router.post("", response_model=reg_schema.RegulatoryComplianceResponse, status_code=status.HTTP_201_CREATED)
async def create_regulatory_compliance(payload: reg_schema.RegulatoryComplianceCreate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await regulatory_compliance_service.create_regulatory_compliance(session=session, data=payload, auth=auth)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=reg_schema.RegulatoryComplianceListResponse)
async def list_regulatory_compliance(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), compliance_type: Optional[str] = None, status: Optional[str] = None, organization_id: Optional[uuid.UUID] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await regulatory_compliance_service.list_regulatory_compliance(session=session, auth=auth, page=page, page_size=page_size, compliance_type=compliance_type, status=status, organization_id=organization_id)


@router.get("/{record_id}", response_model=reg_schema.RegulatoryComplianceResponse)
async def get_regulatory_compliance(record_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await regulatory_compliance_service.get_regulatory_compliance_by_id(session=session, record_id=record_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{record_id}", response_model=reg_schema.RegulatoryComplianceResponse)
async def update_regulatory_compliance(record_id: uuid.UUID, payload: reg_schema.RegulatoryComplianceUpdate, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await regulatory_compliance_service.update_regulatory_compliance(session=session, record_id=record_id, data=payload, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_regulatory_compliance(record_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        await regulatory_compliance_service.delete_regulatory_compliance(session=session, record_id=record_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
