"""Service layer for Organization CRUD operations."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.organization import Organization
from app.schemas import organization as org_schema


async def create_organization(
    session: AsyncSession,
    data: org_schema.OrganizationCreate,
    auth: AuthContext
) -> org_schema.OrganizationResponse:
    """Create a new organization."""
    org = Organization(
        tenant_id=auth.tenant_id,
        name=data.name,
        organization_type=data.organization_type.value,
        registration_number=data.registration_number,
        tax_id=data.tax_id,
        email=data.email,
        phone=data.phone,
        address=data.address.model_dump() if data.address else None,
        parent_organization_id=data.parent_organization_id,
        extra_metadata=data.metadata,
        status="pending_verification"
    )
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org_schema.OrganizationResponse.model_validate(org)


async def get_organization_by_id(
    session: AsyncSession,
    organization_id: uuid.UUID,
    auth: AuthContext
) -> org_schema.OrganizationResponse:
    """Get organization by ID."""
    stmt = select(Organization).where(
        Organization.id == organization_id,
        Organization.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise ValueError(f"Organization with id {organization_id} not found or access denied.")
    
    return org_schema.OrganizationResponse.model_validate(org)


async def list_organizations(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    organization_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> org_schema.OrganizationListResponse:
    """List organizations with filtering and pagination."""
    # Base query
    stmt = select(Organization).where(Organization.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(Organization.id)).where(Organization.tenant_id == auth.tenant_id)
    
    # Apply filters
    if organization_type:
        stmt = stmt.where(Organization.organization_type == organization_type)
        count_stmt = count_stmt.where(Organization.organization_type == organization_type)
    
    if status:
        stmt = stmt.where(Organization.status == status)
        count_stmt = count_stmt.where(Organization.status == status)
    
    if search:
        search_filter = Organization.name.ilike(f"%{search}%")
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)
    
    # Get total count
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(Organization.created_at.desc())
    
    result = await session.execute(stmt)
    organizations = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return org_schema.OrganizationListResponse(
        items=[org_schema.OrganizationResponse.model_validate(org) for org in organizations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


async def update_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    data: org_schema.OrganizationUpdate,
    auth: AuthContext
) -> org_schema.OrganizationResponse:
    """Update an organization."""
    stmt = select(Organization).where(
        Organization.id == organization_id,
        Organization.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise ValueError(f"Organization with id {organization_id} not found or access denied.")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    if "address" in update_data and update_data["address"]:
        update_data["address"] = data.address.model_dump()
    if "organization_type" in update_data and update_data["organization_type"]:
        update_data["organization_type"] = data.organization_type.value
    if "status" in update_data and update_data["status"]:
        update_data["status"] = data.status.value
    
    for field, value in update_data.items():
        setattr(org, field, value)
    
    await session.commit()
    await session.refresh(org)
    return org_schema.OrganizationResponse.model_validate(org)


async def delete_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    auth: AuthContext
) -> bool:
    """Delete an organization (soft delete by setting status to suspended)."""
    stmt = select(Organization).where(
        Organization.id == organization_id,
        Organization.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise ValueError(f"Organization with id {organization_id} not found or access denied.")
    
    org.status = "suspended"
    await session.commit()
    return True
