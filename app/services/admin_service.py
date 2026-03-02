from __future__ import annotations

import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db import models
from app.schemas import admin as admin_schema


async def _get_or_404(session: AsyncSession, model: type, obj_id: uuid.UUID):
    stmt = select(model).where(model.id == obj_id)
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found"
        )
    return obj

async def list_tenants(session: AsyncSession) -> List[admin_schema.TenantResponse]:
    stmt = select(models.Tenant).order_by(models.Tenant.name.asc())
    result = await session.execute(stmt)
    tenants = result.scalars().all()
    return [admin_schema.TenantResponse.model_validate(t) for t in tenants]


async def get_tenant(
        session: AsyncSession,
        tenant_id: uuid.UUID,
) -> admin_schema.TenantResponse:
    tenant = await _get_or_404(session, models.Tenant, tenant_id)
    return admin_schema.TenantResponse.model_validate(tenant)


async def create_tenant(
        session: AsyncSession,
        data: admin_schema.TenantCreate,
) -> admin_schema.TenantResponse:
    tenant = models.Tenant(**data.model_dump())
    session.add(tenant)
    try:
        await session.commit()
        await session.refresh(tenant)
        return admin_schema.TenantResponse.model_validate(tenant)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this configuration already exists"
        )


async def update_tenant(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        data: admin_schema.TenantUpdate,
) -> admin_schema.TenantResponse:
    tenant = await _get_or_404(session, models.Tenant, tenant_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await session.commit()
    await session.refresh(tenant)
    return admin_schema.TenantResponse.model_validate(tenant)


async def delete_tenant(
        session: AsyncSession,
        tenant_id: uuid.UUID,
) -> None:
    tenant = await _get_or_404(session, models.Tenant, tenant_id)
    await session.delete(tenant)
    await session.commit()


# --- User Services ---

async def list_users(session: AsyncSession) -> List[admin_schema.UserResponse]:
    stmt = select(models.User).order_by(models.User.email.asc())
    result = await session.execute(stmt)
    users = result.scalars().all()
    return [admin_schema.UserResponse.model_validate(u) for u in users]


async def get_user(
        session: AsyncSession,
        user_id: uuid.UUID,
) -> admin_schema.UserResponse:
    user = await _get_or_404(session, models.User, user_id)
    return admin_schema.UserResponse.model_validate(user)


async def create_user(
        session: AsyncSession,
        data: admin_schema.UserCreate,
) -> admin_schema.UserResponse:
    await _get_or_404(session, models.Tenant, data.tenant_id)
    await _get_or_404(session, models.UserRole, data.role_id)

    email_stmt = select(models.User).where(models.User.email == data.email)
    email_exists = await session.execute(email_stmt)
    if email_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )

    user = models.User(
        **data.model_dump(exclude={"password"}),
        password=hash_password(data.password),
    )

    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
        return admin_schema.UserResponse.model_validate(user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integrity error during user creation"
        )


async def update_user(
        session: AsyncSession,
        user_id: uuid.UUID,
        data: admin_schema.UserUpdate,
) -> admin_schema.UserResponse:
    user = await _get_or_404(session, models.User, user_id)

    update_data = data.model_dump(exclude_unset=True)

    if "role_id" in update_data:
        await _get_or_404(session, models.UserRole, data.role_id)

    for field, value in update_data.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return admin_schema.UserResponse.model_validate(user)


async def delete_user(
        session: AsyncSession,
        user_id: uuid.UUID,
) -> None:
    user = await _get_or_404(session, models.User, user_id)
    await session.delete(user)
    await session.commit()


async def list_roles(session: AsyncSession) -> List[admin_schema.RoleResponse]:
    stmt = select(models.UserRole).order_by(models.UserRole.name.asc())
    result = await session.execute(stmt)
    roles = result.scalars().all()
    return [admin_schema.RoleResponse.model_validate(r) for r in roles]