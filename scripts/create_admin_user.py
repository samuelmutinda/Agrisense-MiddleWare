#!/usr/bin/env python3
"""
Create a System Admin user and the reserved 'sysadmin' tenant.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)
os.environ.setdefault("ENV_FILE", str(project_root / ".env"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Tenant, User, UserRole


async def ensure_admin_role(session: AsyncSession) -> UserRole:
    """Ensures the 'admin' role exists in the DB."""
    result = await session.execute(select(UserRole).where(UserRole.name == "admin"))
    role = result.scalar_one_or_none()
    if role:
        return role

    print("Creating 'admin' role...")
    role = UserRole(name="admin", description="System-wide administrator with full access")
    session.add(role)
    await session.flush()
    return role


async def ensure_sysadmin_tenant(session: AsyncSession) -> Tenant:
    """
    Ensures the reserved 'sysadmin' tenant exists.
    This is the 'Master Tenant' for your company/platform admins.
    """
    tenant_name = "sysadmin"
    result = await session.execute(select(Tenant).where(Tenant.name == tenant_name))
    tenant = result.scalar_one_or_none()

    if tenant:
        return tenant

    print(f"Initializing master tenant: {tenant_name}...")
    tenant = Tenant(
        name=tenant_name,
        # System tenant usually doesn't need Chirpstack IDs,
        # but they stay nullable=True as per your schema.
    )
    session.add(tenant)
    await session.flush()
    return tenant


async def create_admin_user(
        session: AsyncSession,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: str,
) -> User:
    """Creates an admin inside the 'sysadmin' master tenant."""
    # 1. Get the required parents
    admin_role = await ensure_admin_role(session)
    master_tenant = await ensure_sysadmin_tenant(session)

    # 2. Check if user exists
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        print(f"Updating existing user: {email}")
        user.role_id = admin_role.id
        user.tenant_id = master_tenant.id  # Move them to master tenant if not there
        user.password = hash_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone
    else:
        print(f"Creating new system admin: {email}")
        user = User(
            tenant_id=master_tenant.id,
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
    return user


async def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the System Admin.")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL"), help="Admin email")
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"), help="Admin password")
    args = parser.parse_args()

    # Input handling
    email = args.email or input("Admin email: ").strip()
    password = args.password or getpass.getpass("Admin password: ")

    if not email or not password:
        print("Error: Email and password are required.")
        sys.exit(1)

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_factory() as session:
            user = await create_admin_user(
                session,
                email=email,
                password=password,
                first_name="System",
                last_name="Admin",
                phone="+0000000000",
            )
            await session.commit()
            print("\n" + "=" * 30)
            print("BOOTSTRAP SUCCESSFUL")
            print("=" * 30)
            print(f"User:   {user.email}")
            print(f"Role:   admin")
            print(f"Tenant: sysadmin ({user.tenant_id})")
            print("=" * 30)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())