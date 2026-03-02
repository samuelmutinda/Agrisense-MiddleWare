from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api import deps
from app.schemas import crop as crop_schema
from app.services import crop_service

router = APIRouter(prefix="/crops", tags=["crops"])

@router.get("", response_model=list[crop_schema.CropResponse])
async def list_crops(
    session: AsyncSession = Depends(deps.get_db),
    _auth = Depends(deps.get_auth_context),
):
    return await crop_service.get_all_crops(session)

@router.get("/{crop_id}", response_model=crop_schema.CropResponse)
async def get_crop(
        crop_id: uuid.UUID,
        session: AsyncSession = Depends(deps.get_db),
        _auth = Depends(deps.get_auth_context)
):
    return await crop_service.get_crop_by_id(session, crop_id)

@router.post("", response_model=crop_schema.CropResponse, status_code=status.HTTP_201_CREATED)
async def create_crop(
    payload: crop_schema.CropCreate,
    session: AsyncSession = Depends(deps.get_db),
    _auth = Depends(deps.get_auth_context),
):
    return await crop_service.create_crop(session, payload)

@router.put("/{crop_id}", response_model=crop_schema.CropResponse)
async def update_crop(
    crop_id: uuid.UUID,
    payload: crop_schema.CropCreate,
    session: AsyncSession = Depends(deps.get_db),
    _auth = Depends(deps.get_auth_context),
):
    return await crop_service.update_crop(session, crop_id, payload)

@router.delete("/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crop(
    crop_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    _auth = Depends(deps.get_auth_context),
):
    await crop_service.delete_crop(session, crop_id)
    return None