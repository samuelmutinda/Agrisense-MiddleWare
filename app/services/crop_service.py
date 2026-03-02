from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import models
from app.schemas import crop as crop_schema
from app.services.helpers import get_or_404


async def get_all_crops(session: AsyncSession) -> list[crop_schema.CropResponse]:
    stmt = select(models.Crop).order_by(models.Crop.name.asc())
    result = await session.execute(stmt)
    crops = result.scalars().all()
    return [crop_schema.CropResponse.model_validate(c) for c in crops]

async def get_crop_by_id(
        session: AsyncSession,
        crop_id: uuid.UUID
) -> crop_schema.CropResponse:
    crop = await get_or_404(session, models.Crop, crop_id)
    return crop_schema.CropResponse.model_validate(crop)

async def create_crop(
        session: AsyncSession,
        data: crop_schema.CropCreate
) -> crop_schema.CropResponse:
    crop = models.Crop(**data.model_dump())
    session.add(crop)
    await session.commit()
    await session.refresh(crop)
    return crop_schema.CropResponse.model_validate(crop)


async def update_crop(
        session: AsyncSession,
        crop_id: uuid.UUID,
        data: crop_schema.CropCreate
) -> crop_schema.CropResponse:
    crop = await get_or_404(session, models.Crop, crop_id)

    for key, value in data.model_dump().items():
        setattr(crop, key, value)

    await session.commit()
    await session.refresh(crop)
    return crop_schema.CropResponse.model_validate(crop)


async def delete_crop(
        session: AsyncSession,
        crop_id: uuid.UUID
) -> None:
    crop = await get_or_404(session, models.Crop, crop_id)
    await session.delete(crop)
    await session.commit()
