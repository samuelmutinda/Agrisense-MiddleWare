from __future__ import annotations

import contextvars
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext

tenant_id_ctx: contextvars.ContextVar[Optional[uuid.UUID]] = contextvars.ContextVar(
    "tenant_id", default=None
)
user_id_ctx: contextvars.ContextVar[Optional[uuid.UUID]] = contextvars.ContextVar(
    "user_id", default=None
)


def set_tenant_context(auth: AuthContext) -> None:
    tenant_id_ctx.set(auth.tenant_id)
    user_id_ctx.set(auth.user_id)


def clear_tenant_context() -> None:
    tenant_id_ctx.set(None)
    user_id_ctx.set(None)


def get_tenant_id() -> Optional[uuid.UUID]:
    return tenant_id_ctx.get()


def get_user_id() -> Optional[uuid.UUID]:
    return user_id_ctx.get()


async def attach_context_to_session(session: AsyncSession) -> None:
    session.info["tenant_id"] = get_tenant_id()
    session.info["user_id"] = get_user_id()

