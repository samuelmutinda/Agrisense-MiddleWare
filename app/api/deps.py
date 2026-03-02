from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends

from app.core import tenant_context
from app.core.security import AuthContext, get_current_principal, require_admin
from app.db.session import get_session


async def get_db(
    auth: AuthContext = Depends(get_current_principal),
) -> AsyncGenerator:
    """
    Provide a tenant-scoped DB session.

    The tenant context is set per-request to support RLS-friendly behavior.
    Requires user authentication.
    """
    tenant_context.set_tenant_context(auth)
    try:
        async for session in get_session():
            yield session
    finally:
        tenant_context.clear_tenant_context()


async def get_system_db() -> AsyncGenerator:
    """
    Provide a system-level DB session without user authentication.

    Used for system-to-system integrations (e.g., ChirpStack webhooks)
    that need database access but don't have user credentials.
    No tenant context is set, so queries must explicitly filter by tenant.
    """
    async for session in get_session():
        yield session


def get_auth_context(
    auth: AuthContext = Depends(get_current_principal),
) -> AuthContext:
    return auth

