"""Service layer for AuditTrail operations (read-only + create for internal use)."""
from __future__ import annotations

import uuid
from typing import Optional, Any
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.audit_trail import AuditTrail
from app.db.models.user import User
from app.schemas import audit_trail as audit_schema


async def create_audit_entry(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, action: str, resource_type: str, resource_id: Optional[uuid.UUID] = None, resource_name: Optional[str] = None, changes: Optional[dict[str, Any]] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None, metadata: Optional[dict] = None):
    """Create an audit trail entry. This is used internally by other services."""
    entry = AuditTrail(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_audit_entry_by_id(session: AsyncSession, entry_id: uuid.UUID, auth: AuthContext):
    stmt = select(AuditTrail).where(AuditTrail.id == entry_id, AuditTrail.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise ValueError(f"Audit entry {entry_id} not found")
    response = audit_schema.AuditTrailResponse.model_validate(entry)
    user = await session.get(User, entry.user_id)
    if user:
        response.user_email = user.email
        response.user_name = f"{user.first_name} {user.last_name}"
    return response


async def list_audit_entries(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 50, user_id: Optional[uuid.UUID] = None, action: Optional[str] = None, resource_type: Optional[str] = None, resource_id: Optional[uuid.UUID] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None):
    stmt = select(AuditTrail).where(AuditTrail.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(AuditTrail.id)).where(AuditTrail.tenant_id == auth.tenant_id)
    if user_id:
        stmt = stmt.where(AuditTrail.user_id == user_id)
        count_stmt = count_stmt.where(AuditTrail.user_id == user_id)
    if action:
        stmt = stmt.where(AuditTrail.action == action)
        count_stmt = count_stmt.where(AuditTrail.action == action)
    if resource_type:
        stmt = stmt.where(AuditTrail.resource_type == resource_type)
        count_stmt = count_stmt.where(AuditTrail.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditTrail.resource_id == resource_id)
        count_stmt = count_stmt.where(AuditTrail.resource_id == resource_id)
    if date_from:
        stmt = stmt.where(AuditTrail.timestamp >= date_from)
        count_stmt = count_stmt.where(AuditTrail.timestamp >= date_from)
    if date_to:
        stmt = stmt.where(AuditTrail.timestamp <= date_to)
        count_stmt = count_stmt.where(AuditTrail.timestamp <= date_to)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(AuditTrail.timestamp.desc())
    result = await session.execute(stmt)
    entries = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    items = []
    for e in entries:
        resp = audit_schema.AuditTrailResponse.model_validate(e)
        user = await session.get(User, e.user_id)
        if user:
            resp.user_email = user.email
            resp.user_name = f"{user.first_name} {user.last_name}"
        items.append(resp)
    return audit_schema.AuditTrailListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)
