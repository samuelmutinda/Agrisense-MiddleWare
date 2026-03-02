from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.schemas import customer as customer_schema
from app.services.helpers import get_or_404


async def get_customers(
        session: AsyncSession,
        tenant_id: uuid.UUID
) -> list[customer_schema.CustomerResponse]:
    stmt = (
        select(models.Customer)
        .where(models.Customer.tenant_id == tenant_id)
        .order_by(models.Customer.name.asc())
    )
    result = await session.execute(stmt)
    customers = result.scalars().all()

    return [customer_schema.CustomerResponse.model_validate(c) for c in customers]

async def get_customer_by_id(
        session: AsyncSession,
        customer_id: uuid.UUID,
        tenant_id: uuid.UUID
)->customer_schema.CustomerResponse:
    customer = await get_or_404(session, models.Customer, customer_id, tenant_id)
    return customer_schema.CustomerResponse.model_validate(customer)

async def create_customer(
        session: AsyncSession,
        data: customer_schema.CustomerCreate,
        tenant_id: uuid.UUID
) -> customer_schema.CustomerResponse:
    customer = models.Customer(
        tenant_id=tenant_id,
        **data.model_dump()
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer_schema.CustomerResponse.model_validate(customer)


async def update_customer(
        session: AsyncSession,
        customer_id: uuid.UUID,
        data: customer_schema.CustomerCreate,
        tenant_id: uuid.UUID
) -> customer_schema.CustomerResponse:
    customer = await get_or_404(session, models.Customer, customer_id, tenant_id)

    customer.name = data.name

    await session.commit()
    await session.refresh(customer)
    return customer_schema.CustomerResponse.model_validate(customer)


async def delete_customer(
        session: AsyncSession,
        customer_id: uuid.UUID,
        tenant_id: uuid.UUID
) -> None:
    customer = await get_or_404(session, models.Customer, customer_id, tenant_id)

    await session.delete(customer)
    await session.commit()