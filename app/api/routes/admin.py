from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.schemas import admin as admin_schema
from app.services import admin_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(deps.require_admin)]
)

@router.get("/tenants", response_model=list[admin_schema.TenantResponse])
async def list_tenants(session: AsyncSession = Depends(deps.get_system_db)):
    return await admin_service.list_tenants(session)

@router.get("/tenants/{tenant_id}", response_model=admin_schema.TenantResponse)
async def get_tenant(tenant_id: uuid.UUID, session: AsyncSession = Depends(deps.get_system_db)):
    return await admin_service.get_tenant(session, tenant_id)

@router.post("/tenants", response_model=admin_schema.TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(payload: admin_schema.TenantCreate, session: AsyncSession = Depends(deps.get_system_db)):
    return await admin_service.create_tenant(session, payload)

@router.put("/tenants/{tenant_id}", response_model=admin_schema.TenantResponse)
async def update_tenant(tenant_id: uuid.UUID, payload: admin_schema.TenantUpdate, session: AsyncSession = Depends(deps.get_system_db)):
    return await admin_service.update_tenant(session, tenant_id, payload)

@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_id: uuid.UUID, session: AsyncSession = Depends(deps.get_system_db)):
    await admin_service.delete_tenant(session, tenant_id)


@router.get("/users", response_model=list[admin_schema.UserResponse])
async def list_users(session: AsyncSession = Depends(deps.get_system_db)):
    return await admin_service.list_users(session)

@router.post("/users", response_model=admin_schema.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: admin_schema.UserCreate, session: AsyncSession = Depends(deps.get_system_db)):
    return await admin_service.create_user(session, payload)

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, session: AsyncSession = Depends(deps.get_system_db)):
    await admin_service.delete_user(session, user_id)

@router.get("/roles", response_model=list[admin_schema.RoleResponse])
async def list_roles(session: AsyncSession = Depends(deps.get_system_db)):
    return await admin_service.list_roles(session)