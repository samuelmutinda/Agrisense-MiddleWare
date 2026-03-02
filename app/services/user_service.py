"""Service layer for User management CRUD operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.core.security import AuthContext
from app.db.models.user import User
from app.db.models.user_role import UserRole
from app.schemas import user as user_schema


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


async def create_user(
    session: AsyncSession,
    data: user_schema.UserCreate,
    auth: AuthContext
) -> user_schema.UserResponse:
    """Create a new user."""
    # Check if email already exists
    existing = await session.execute(
        select(User).where(User.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"User with email {data.email} already exists")
    
    # Check if phone already exists
    existing_phone = await session.execute(
        select(User).where(User.phone == data.phone)
    )
    if existing_phone.scalar_one_or_none():
        raise ValueError(f"User with phone {data.phone} already exists")
    
    user = User(
        tenant_id=auth.tenant_id,
        email=data.email,
        password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role_id=data.role_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    # Get role name
    role = await session.get(UserRole, data.role_id)
    
    response = user_schema.UserResponse.model_validate(user)
    response.role_name = role.name if role else None
    return response


async def get_user_by_id(
    session: AsyncSession,
    user_id: uuid.UUID,
    auth: AuthContext
) -> user_schema.UserResponse:
    """Get user by ID."""
    stmt = select(User, UserRole).join(UserRole).where(
        User.id == user_id,
        User.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    
    if not row:
        raise ValueError(f"User with id {user_id} not found or access denied.")
    
    user, role = row
    response = user_schema.UserResponse.model_validate(user)
    response.role_name = role.name
    return response


async def list_users(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    role_id: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None
) -> user_schema.UserListResponse:
    """List users with filtering and pagination."""
    # Base query
    stmt = select(User, UserRole).join(UserRole).where(User.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(User.id)).where(User.tenant_id == auth.tenant_id)
    
    # Apply filters
    if role_id:
        stmt = stmt.where(User.role_id == role_id)
        count_stmt = count_stmt.where(User.role_id == role_id)
    
    if search:
        search_filter = (
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)
    
    # Get total count
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    result = await session.execute(stmt)
    rows = result.all()
    
    total_pages = (total + page_size - 1) // page_size
    
    items = []
    for user, role in rows:
        response = user_schema.UserResponse.model_validate(user)
        response.role_name = role.name
        items.append(response)
    
    return user_schema.UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


async def update_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: user_schema.UserUpdate,
    auth: AuthContext
) -> user_schema.UserResponse:
    """Update a user."""
    stmt = select(User).where(
        User.id == user_id,
        User.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise ValueError(f"User with id {user_id} not found or access denied.")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status":
            continue  # Handle status separately if needed
        setattr(user, field, value)
    
    await session.commit()
    await session.refresh(user)
    
    role = await session.get(UserRole, user.role_id)
    response = user_schema.UserResponse.model_validate(user)
    response.role_name = role.name if role else None
    return response


async def change_password(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: user_schema.UserPasswordChange,
    auth: AuthContext
) -> bool:
    """Change user password."""
    stmt = select(User).where(
        User.id == user_id,
        User.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise ValueError(f"User with id {user_id} not found or access denied.")
    
    if not verify_password(data.current_password, user.password):
        raise ValueError("Current password is incorrect")
    
    user.password = hash_password(data.new_password)
    await session.commit()
    return True


async def delete_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    auth: AuthContext
) -> bool:
    """Delete a user."""
    stmt = select(User).where(
        User.id == user_id,
        User.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise ValueError(f"User with id {user_id} not found or access denied.")
    
    if user.id == auth.user_id:
        raise ValueError("Cannot delete your own account")
    
    await session.delete(user)
    await session.commit()
    return True


async def list_roles(
    session: AsyncSession,
    auth: AuthContext
) -> list[user_schema.UserRoleResponse]:
    """List all user roles."""
    stmt = select(UserRole)
    result = await session.execute(stmt)
    roles = result.scalars().all()
    return [user_schema.UserRoleResponse.model_validate(role) for role in roles]
