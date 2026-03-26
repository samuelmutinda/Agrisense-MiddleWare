"""Service layer for GcpProfile operations."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.gcp_profile import GcpProfile
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.schemas import gcp_profile as gcp_schema


async def create_gcp_profile(session: AsyncSession, data: gcp_schema.GcpProfileCreate, auth: AuthContext):
    profile = GcpProfile(
        tenant_id=auth.tenant_id,
        facility_id=data.facility_id,
        certification_level=data.certification_level.value,
        temperature_compliance_score=data.temperature_compliance_score,
        hygiene_score=data.hygiene_score,
        documentation_score=data.documentation_score,
        training_score=data.training_score,
        audit_date=data.audit_date,
        next_audit_date=data.next_audit_date,
        auditor_name=data.auditor_name,
        recommendations=data.recommendations,
        extra_metadata=data.metadata
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return await get_gcp_profile_by_id(session, profile.id, auth)


async def get_gcp_profile_by_id(session: AsyncSession, profile_id: uuid.UUID, auth: AuthContext):
    stmt = select(GcpProfile).where(GcpProfile.id == profile_id, GcpProfile.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise ValueError(f"GCP profile {profile_id} not found")
    response = gcp_schema.GcpProfileResponse.model_validate(profile)
    response.overall_score = (profile.temperature_compliance_score + profile.hygiene_score + profile.documentation_score + profile.training_score) / 4
    if profile.facility_id:
        facility = await session.get(ColdStorageUnit, profile.facility_id)
        if facility:
            response.facility_name = facility.name
    return response


async def update_gcp_profile(session: AsyncSession, profile_id: uuid.UUID, data: gcp_schema.GcpProfileUpdate, auth: AuthContext):
    stmt = select(GcpProfile).where(GcpProfile.id == profile_id, GcpProfile.tenant_id == auth.tenant_id)
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise ValueError(f"GCP profile {profile_id} not found")
    update_data = data.model_dump(exclude_unset=True)
    if "certification_level" in update_data and update_data["certification_level"]:
        update_data["certification_level"] = update_data["certification_level"].value
    for key, value in update_data.items():
        setattr(profile, key, value)
    await session.commit()
    return await get_gcp_profile_by_id(session, profile_id, auth)


async def list_gcp_profiles(session: AsyncSession, auth: AuthContext, page: int = 1, page_size: int = 20, facility_id: Optional[uuid.UUID] = None, certification_level: Optional[str] = None):
    stmt = select(GcpProfile).where(GcpProfile.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(GcpProfile.id)).where(GcpProfile.tenant_id == auth.tenant_id)
    if facility_id:
        stmt = stmt.where(GcpProfile.facility_id == facility_id)
        count_stmt = count_stmt.where(GcpProfile.facility_id == facility_id)
    if certification_level:
        stmt = stmt.where(GcpProfile.certification_level == certification_level)
        count_stmt = count_stmt.where(GcpProfile.certification_level == certification_level)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(GcpProfile.audit_date.desc())
    result = await session.execute(stmt)
    profiles = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    items = []
    for p in profiles:
        resp = gcp_schema.GcpProfileResponse.model_validate(p)
        resp.overall_score = (p.temperature_compliance_score + p.hygiene_score + p.documentation_score + p.training_score) / 4
        items.append(resp)
    return gcp_schema.GcpProfileListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)
