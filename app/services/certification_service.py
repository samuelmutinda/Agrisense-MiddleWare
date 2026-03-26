"""Service layer for Certification operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.certification import Certification
from app.db.models.organization import Organization
from app.schemas import certification as cert_schema


async def create_certification(
    session: AsyncSession,
    data: cert_schema.CertificationCreate,
    auth: AuthContext
) -> cert_schema.CertificationResponse:
    """Create a new certification."""
    cert = Certification(
        tenant_id=auth.tenant_id,
        organization_id=data.organization_id,
        certification_type=data.certification_type.value,
        certificate_number=data.certificate_number,
        issuing_body=data.issuing_body,
        issue_date=data.issue_date,
        expiry_date=data.expiry_date,
        scope=data.scope,
        document_url=data.document_url,
        extra_metadata=data.metadata,
        status="active" if data.expiry_date >= date.today() else "expired"
    )
    session.add(cert)
    await session.commit()
    await session.refresh(cert)
    
    return await get_certification_by_id(session, cert.id, auth)


async def get_certification_by_id(
    session: AsyncSession,
    cert_id: uuid.UUID,
    auth: AuthContext
) -> cert_schema.CertificationResponse:
    """Get certification by ID."""
    stmt = select(Certification).where(
        Certification.id == cert_id,
        Certification.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    cert = result.scalar_one_or_none()
    
    if not cert:
        raise ValueError(f"Certification {cert_id} not found")
    
    response = cert_schema.CertificationResponse.model_validate(cert)
    
    org = await session.get(Organization, cert.organization_id)
    if org:
        response.organization_name = org.name
    
    response.days_until_expiry = (cert.expiry_date - date.today()).days
    
    return response


async def list_certifications(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    organization_id: Optional[uuid.UUID] = None,
    certification_type: Optional[str] = None,
    status: Optional[str] = None,
    expiring_within_days: Optional[int] = None
) -> cert_schema.CertificationListResponse:
    """List certifications with filtering."""
    stmt = select(Certification).where(Certification.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(Certification.id)).where(Certification.tenant_id == auth.tenant_id)
    
    if organization_id:
        stmt = stmt.where(Certification.organization_id == organization_id)
        count_stmt = count_stmt.where(Certification.organization_id == organization_id)
    
    if certification_type:
        stmt = stmt.where(Certification.certification_type == certification_type)
        count_stmt = count_stmt.where(Certification.certification_type == certification_type)
    
    if status:
        stmt = stmt.where(Certification.status == status)
        count_stmt = count_stmt.where(Certification.status == status)
    
    if expiring_within_days:
        from datetime import timedelta
        expiry_limit = date.today() + timedelta(days=expiring_within_days)
        stmt = stmt.where(Certification.expiry_date <= expiry_limit)
        count_stmt = count_stmt.where(Certification.expiry_date <= expiry_limit)
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(Certification.expiry_date.asc())
    
    result = await session.execute(stmt)
    certs = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    items = []
    for c in certs:
        response = cert_schema.CertificationResponse.model_validate(c)
        response.days_until_expiry = (c.expiry_date - date.today()).days
        items.append(response)
    
    return cert_schema.CertificationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


async def update_certification(
    session: AsyncSession,
    cert_id: uuid.UUID,
    data: cert_schema.CertificationUpdate,
    auth: AuthContext
) -> cert_schema.CertificationResponse:
    """Update a certification."""
    stmt = select(Certification).where(
        Certification.id == cert_id,
        Certification.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    cert = result.scalar_one_or_none()
    
    if not cert:
        raise ValueError(f"Certification {cert_id} not found")
    
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = data.status.value
    
    for field, value in update_data.items():
        setattr(cert, field, value)
    
    await session.commit()
    return await get_certification_by_id(session, cert_id, auth)


async def delete_certification(
    session: AsyncSession,
    cert_id: uuid.UUID,
    auth: AuthContext
) -> bool:
    """Delete a certification."""
    stmt = select(Certification).where(
        Certification.id == cert_id,
        Certification.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    cert = result.scalar_one_or_none()
    
    if not cert:
        raise ValueError(f"Certification {cert_id} not found")
    
    await session.delete(cert)
    await session.commit()
    return True
