"""Authentication endpoints: login and token."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.api.deps import get_system_db
from app.core.security import AuthContext, create_access_token, verify_password
from app.db import models

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthContextResponse(BaseModel):
    tenant_id: str
    user_id: str
    role: str
    role_id: str
    email: str | None = None


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_system_db),
):
    """
    OAuth2-compatible token login. Use `username` for email and `password`.

    Returns a JWT access token.
    """
    email = form_data.username
    password = form_data.password

    stmt = (
        select(models.User)
        .options(selectinload(models.User.role))
        .where(models.User.email == email)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no role assigned",
        )

    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role_name=user.role.name,
        role_id=user.role.id,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh_token(
    auth: AuthContext = Depends(deps.get_auth_context),
    session: AsyncSession = Depends(get_system_db),
):
    """Refresh JWT using the current bearer token and live DB role data."""
    stmt = (
        select(models.User)
        .options(selectinload(models.User.role))
        .where(models.User.id == auth.user_id)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication context",
        )

    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role_name=user.role.name,
        role_id=user.role.id,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/context", response_model=AuthContextResponse)
async def get_auth_context(
    auth: AuthContext = Depends(deps.get_auth_context),
    session: AsyncSession = Depends(get_system_db),
):
    """Return backend-authoritative user/tenant/role context for client RBAC sync."""
    stmt = (
        select(models.User)
        .options(selectinload(models.User.role))
        .where(models.User.id == auth.user_id)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication context",
        )

    return AuthContextResponse(
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        role=user.role.name,
        role_id=str(user.role.id),
        email=user.email,
    )
