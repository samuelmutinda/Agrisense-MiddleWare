from uuid import UUID
from typing import Type, List
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base

async def validate_tenant_entities(
    session: AsyncSession,
    tenant_id: UUID,
    entity_mappings: dict[Type[Base], UUID]
):
    """
    Validates that multiple entities exist and belong to the specific tenant.
    Example mapping: {models.Customer: data.customer_id, models.Crop: data.crop_id}
    """
    for model, entity_id in entity_mappings.items():
        # Build query filtering by both ID and Tenant
        stmt = select(model).where(
            model.id == entity_id,
            model.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()

        if not entity:
            # Raising specific error names for better frontend debugging
            model_name = model.__name__
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model_name} with ID {entity_id} not found for this tenant."
            )