"""Service layer for RegulatoryCompliance operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.regulatory_compliance import RegulatoryCompliance
from app.db.models.organization import Organization
from app.schemas import regulatory_compliance as reg_schema


async def create_regulatory_compliance(session: AsyncSession, data: reg_schema.RegulatoryComplianceCreate, auth: AuthContext):
    record = RegulatoryCompliance(
        tenant_id=auth.tenant_id,
        compliance_type=data.compliance_type.value,
        organization_id=data.organization_id,
        regulation_name=data.regulation_name,
        authority_name=data.authority_name,
        permit_number=data.permit_number,
        issue_date=data.issue_date,
        expiry_date=data.expiry_date,
        requirements=data.requirements,
        notes=data.notes,
        metadata=data.metadata,
        status="pending_review"
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return await get_regulatory_compliance_by_id(session, record.id, auth)


async def get_regulatory_compliance_by_id(session: AsyncSession, record_id: uuid.UUID, auth: AuthContext):
    stmt = select(RegulatoryCompliance).where(RegulatoryCompliance.id == record_id, RegulatoryCompliance.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Regulatory compliance record {record_id} not found")
    response = reg_schema.RegulatoryComplianceResponse.model_validate(record)
    if record.organization_id:
        org = await session.get(Organization, record.organization_id)
        if org:
            response.organization_name = org.name
    if record.expiry_date:
        response.days_until_expiry = (record.expiry_date - date.today()).days
    return response


async def list_regulatory_compliance(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 20, compliance_type: Optional[str] = None, status: Optional[str] = None, organization_id: Optional[uuid.UUID] = None):
    stmt = select(RegulatoryCompliance).where(RegulatoryCompliance.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(RegulatoryCompliance.id)).where(RegulatoryCompliance.tenant_id == auth.tenant_id)
    if compliance_type:
        stmt = stmt.where(RegulatoryCompliance.compliance_type == compliance_type)
        count_stmt = count_stmt.where(RegulatoryCompliance.compliance_type == compliance_type)
    if status:
        stmt = stmt.where(RegulatoryCompliance.status == status)
        count_stmt = count_stmt.where(RegulatoryCompliance.status == status)
    if organization_id:
        stmt = stmt.where(RegulatoryCompliance.organization_id == organization_id)
        count_stmt = count_stmt.where(RegulatoryCompliance.organization_id == organization_id)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(RegulatoryCompliance.expiry_date.asc())
    result = await session.execute(stmt)
    records = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    items = []
    for r in records:
        response = reg_schema.RegulatoryComplianceResponse.model_validate(r)
        if r.expiry_date:
            response.days_until_expiry = (r.expiry_date - date.today()).days
        items.append(response)
    return reg_schema.RegulatoryComplianceListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


async def update_regulatory_compliance(session: AsyncSession, record_id: uuid.UUID, data: reg_schema.RegulatoryComplianceUpdate, auth: AuthContext):
    stmt = select(RegulatoryCompliance).where(RegulatoryCompliance.id == record_id, RegulatoryCompliance.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Regulatory compliance record {record_id} not found")
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = data.status.value
    for field, value in update_data.items():
        setattr(record, field, value)
    await session.commit()
    return await get_regulatory_compliance_by_id(session, record_id, auth)


async def delete_regulatory_compliance(session: AsyncSession, record_id: uuid.UUID, auth: AuthContext):
    stmt = select(RegulatoryCompliance).where(RegulatoryCompliance.id == record_id, RegulatoryCompliance.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError(f"Regulatory compliance record {record_id} not found")
    await session.delete(record)
    await session.commit()
    return True
