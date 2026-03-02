"""API routes for User management."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import user as user_schema
from app.services import user_service


router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=user_schema.UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user"
)
async def create_user(
    payload: user_schema.UserCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Create a new user within the tenant."""
    try:
        return await user_service.create_user(
            session=session, data=payload, auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=user_schema.UserListResponse,
    summary="List users"
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role_id: Optional[uuid.UUID] = Query(None),
    organization_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List users with pagination and filtering."""
    return await user_service.list_users(
        session=session,
        auth=auth,
        page=page,
        page_size=page_size,
        role_id=role_id,
        organization_id=organization_id,
        search=search
    )


@router.get(
    "/roles",
    response_model=list[user_schema.UserRoleResponse],
    summary="List user roles"
)
async def list_roles(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """List all available user roles."""
    return await user_service.list_roles(session=session, auth=auth)


@router.get(
    "/{user_id}",
    response_model=user_schema.UserResponse,
    summary="Get user by ID"
)
async def get_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Get a specific user by ID."""
    try:
        return await user_service.get_user_by_id(
            session=session,
            user_id=user_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{user_id}",
    response_model=user_schema.UserResponse,
    summary="Update user"
)
async def update_user(
    user_id: uuid.UUID,
    payload: user_schema.UserUpdate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Update a user."""
    try:
        return await user_service.update_user(
            session=session,
            user_id=user_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{user_id}/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change user password"
)
async def change_password(
    user_id: uuid.UUID,
    payload: user_schema.UserPasswordChange,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Change user password."""
    try:
        await user_service.change_password(
            session=session,
            user_id=user_id,
            data=payload,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user"
)
async def delete_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Delete a user."""
    try:
        await user_service.delete_user(
            session=session,
            user_id=user_id,
            auth=auth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
