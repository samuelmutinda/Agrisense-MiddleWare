"""API routes for AuditTrail resource (read-only)."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import audit_trail as audit_schema
from app.services import audit_trail_service

router = APIRouter(prefix="/audit-trail", tags=["audit-trail"])


@router.get("", response_model=audit_schema.AuditTrailListResponse)
async def list_audit_entries(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), user_id: Optional[uuid.UUID] = None, action: Optional[str] = None, resource_type: Optional[str] = None, resource_id: Optional[uuid.UUID] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    return await audit_trail_service.list_audit_entries(session=session, auth=auth, page=page, page_size=page_size, user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id, date_from=date_from, date_to=date_to)


@router.get("/{entry_id}", response_model=audit_schema.AuditTrailResponse)
async def get_audit_entry(entry_id: uuid.UUID, session: AsyncSession = Depends(deps.get_db), auth: AuthContext = Depends(deps.get_auth_context)):
    try:
        return await audit_trail_service.get_audit_entry_by_id(session=session, entry_id=entry_id, auth=auth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
