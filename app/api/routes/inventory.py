from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.schemas import inventory as inventory_schema
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/current", response_model=List[inventory_schema.InventoryPosition])
async def current_inventory(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await inventory_service.get_current_inventory(
        session=session, tenant_id=auth.tenant_id
    )


@router.get("/summary", response_model=inventory_schema.InventorySummary)
async def inventory_summary(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await inventory_service.get_inventory_summary(
        session=session, tenant_id=auth.tenant_id
    )

