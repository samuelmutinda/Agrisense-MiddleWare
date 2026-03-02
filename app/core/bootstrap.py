"""Startup bootstrap: ensure sysadmin user exists when configured."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Tenant, User, UserRole

logger = logging.getLogger(__name__)


async def ensure_admin_role(session: AsyncSession) -> UserRole:
    """Ensure 'admin' role exists; return it."""
    result = await session.execute(select(UserRole).where(UserRole.name == "admin"))
    role = result.scalar_one_or_none()
    if role:
        return role
    role = UserRole(name="admin", description="System-wide administrator with full access")
    session.add(role)
    await session.flush()
    return role


async def ensure_sysadmin_tenant(session: AsyncSession) -> Tenant:
    """Ensure the 'sysadmin' master tenant exists; return it."""
    result = await session.execute(select(Tenant).where(Tenant.name == "sysadmin"))
    tenant = result.scalar_one_or_none()
    if tenant:
        return tenant
    tenant = Tenant(name="sysadmin")
    session.add(tenant)
    await session.flush()
    return tenant


async def ensure_sysadmin_user(
    session: AsyncSession,
    email: str,
    password: str,
    first_name: str = "System",
    last_name: str = "Admin",
    phone: str = "+0000000000",
) -> User:
    """Ensure admin role and sysadmin tenant exist, then create or update sysadmin user."""
    admin_role = await ensure_admin_role(session)
    tenant = await ensure_sysadmin_tenant(session)

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.role_id = admin_role.id
        user.tenant_id = tenant.id
        user.password = hash_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone
        await session.flush()
        await session.refresh(user)
        logger.info("Sysadmin user updated: %s", email)
        return user

    user = User(
        tenant_id=tenant.id,
        role_id=admin_role.id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=hash_password(password),
        phone=phone,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    logger.info("Sysadmin user created: %s", email)
    return user


async def run_sysadmin_bootstrap_if_configured() -> None:
    """
    If SYSADMIN_EMAIL and SYSADMIN_PASSWORD are set, ensure the sysadmin user exists.
    Safe to call on every startup; skips when env vars are unset.
    """
    settings = get_settings()
    if not settings.sysadmin_email or not settings.sysadmin_password:
        return
    if len(settings.sysadmin_password) < 8:
        logger.warning("Sysadmin bootstrap skipped: SYSADMIN_PASSWORD must be at least 8 characters")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        async with async_session_factory() as session:
            await ensure_sysadmin_user(
                session,
                email=settings.sysadmin_email,
                password=settings.sysadmin_password,
            )
            await session.commit()
    except Exception as e:
        logger.exception("Sysadmin bootstrap failed: %s", e)
        raise
    finally:
        await engine.dispose()
