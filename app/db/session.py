from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.tenant_context import attach_context_to_session
from app.db import models

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def lifespan_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for app lifespan tasks."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing a tenant-scoped AsyncSession."""
    async with AsyncSessionLocal() as session:
        await attach_context_to_session(session)
        yield session

