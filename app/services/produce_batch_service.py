"""Service layer for ProduceBatch CRUD operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.produce_batch import ProduceBatch
from app.db.models.crop import Crop
from app.db.models.customer import Customer
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.schemas import produce_batch as batch_schema


def generate_batch_number(tenant_id: uuid.UUID, crop_id: uuid.UUID) -> str:
    """Generate a unique batch number."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_crop = str(crop_id)[:4]
    return f"BTH-{short_crop.upper()}-{timestamp}"


async def create_produce_batch(
    session: AsyncSession,
    data: batch_schema.ProduceBatchCreate,
    auth: AuthContext
) -> batch_schema.ProduceBatchResponse:
    """Create a new produce batch."""
    batch_number = data.batch_number or generate_batch_number(auth.tenant_id, data.crop_id)
    
    batch = ProduceBatch(
        tenant_id=auth.tenant_id,
        batch_number=batch_number,
        crop_id=data.crop_id,
        customer_id=data.customer_id,
        source_farm_id=data.source_farm_id,
        quantity_kg=data.quantity_kg,
        quantity_units=data.quantity_units,
        remaining_quantity_kg=data.quantity_kg,
        unit_type=data.unit_type,
        harvest_date=data.harvest_date,
        expected_expiry_date=data.expected_expiry_date,
        quality_grade=data.quality_grade.value,
        storage_unit_id=data.storage_unit_id,
        storage_temperature_celsius=data.storage_temperature_celsius,
        humidity_percent=data.humidity_percent,
        gcp_code=data.gcp_code,
        origin_country=data.origin_country,
        certifications=data.certifications,
        extra_metadata=data.metadata,
        status="pending" if not data.storage_unit_id else "in_storage"
    )
    session.add(batch)
    await session.commit()
    await session.refresh(batch)
    
    return await get_produce_batch_by_id(session, batch.id, auth)


async def get_produce_batch_by_id(
    session: AsyncSession,
    batch_id: uuid.UUID,
    auth: AuthContext
) -> batch_schema.ProduceBatchResponse:
    """Get produce batch by ID with related data."""
    stmt = select(ProduceBatch).where(
        ProduceBatch.id == batch_id,
        ProduceBatch.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise ValueError(f"Produce batch with id {batch_id} not found or access denied.")
    
    response = batch_schema.ProduceBatchResponse.model_validate(batch)
    
    # Enrich with related names
    crop = await session.get(Crop, batch.crop_id)
    if crop:
        response.crop_name = crop.name
    
    customer = await session.get(Customer, batch.customer_id)
    if customer:
        response.customer_name = customer.name
    
    if batch.storage_unit_id:
        storage = await session.get(ColdStorageUnit, batch.storage_unit_id)
        if storage:
            response.storage_unit_name = storage.name
    
    # Calculate days until expiry
    if batch.expected_expiry_date:
        delta = batch.expected_expiry_date - date.today()
        response.days_until_expiry = delta.days
    
    return response


async def list_produce_batches(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    crop_id: Optional[uuid.UUID] = None,
    customer_id: Optional[uuid.UUID] = None,
    storage_unit_id: Optional[uuid.UUID] = None,
    quality_grade: Optional[str] = None,
    expiring_within_days: Optional[int] = None
) -> batch_schema.ProduceBatchListResponse:
    """List produce batches with filtering and pagination."""
    stmt = select(ProduceBatch).where(ProduceBatch.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(ProduceBatch.id)).where(ProduceBatch.tenant_id == auth.tenant_id)
    
    if status:
        stmt = stmt.where(ProduceBatch.status == status)
        count_stmt = count_stmt.where(ProduceBatch.status == status)
    
    if crop_id:
        stmt = stmt.where(ProduceBatch.crop_id == crop_id)
        count_stmt = count_stmt.where(ProduceBatch.crop_id == crop_id)
    
    if customer_id:
        stmt = stmt.where(ProduceBatch.customer_id == customer_id)
        count_stmt = count_stmt.where(ProduceBatch.customer_id == customer_id)
    
    if storage_unit_id:
        stmt = stmt.where(ProduceBatch.storage_unit_id == storage_unit_id)
        count_stmt = count_stmt.where(ProduceBatch.storage_unit_id == storage_unit_id)
    
    if quality_grade:
        stmt = stmt.where(ProduceBatch.quality_grade == quality_grade)
        count_stmt = count_stmt.where(ProduceBatch.quality_grade == quality_grade)
    
    if expiring_within_days:
        target_date = date.today()
        from datetime import timedelta
        expiry_limit = target_date + timedelta(days=expiring_within_days)
        stmt = stmt.where(ProduceBatch.expected_expiry_date <= expiry_limit)
        count_stmt = count_stmt.where(ProduceBatch.expected_expiry_date <= expiry_limit)
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(ProduceBatch.created_at.desc())
    
    result = await session.execute(stmt)
    batches = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    items = []
    for b in batches:
        response = batch_schema.ProduceBatchResponse.model_validate(b)
        if b.expected_expiry_date:
            delta = b.expected_expiry_date - date.today()
            response.days_until_expiry = delta.days
        items.append(response)
    
    return batch_schema.ProduceBatchListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


async def update_produce_batch(
    session: AsyncSession,
    batch_id: uuid.UUID,
    data: batch_schema.ProduceBatchUpdate,
    auth: AuthContext
) -> batch_schema.ProduceBatchResponse:
    """Update a produce batch."""
    stmt = select(ProduceBatch).where(
        ProduceBatch.id == batch_id,
        ProduceBatch.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise ValueError(f"Produce batch with id {batch_id} not found or access denied.")
    
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = data.status.value
    if "quality_grade" in update_data and update_data["quality_grade"]:
        update_data["quality_grade"] = data.quality_grade.value
    
    for field, value in update_data.items():
        setattr(batch, field, value)
    
    await session.commit()
    return await get_produce_batch_by_id(session, batch_id, auth)


async def update_batch_quality(
    session: AsyncSession,
    batch_id: uuid.UUID,
    data: batch_schema.BatchQualityUpdate,
    auth: AuthContext
) -> batch_schema.ProduceBatchResponse:
    """Update batch quality grade."""
    stmt = select(ProduceBatch).where(
        ProduceBatch.id == batch_id,
        ProduceBatch.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise ValueError(f"Produce batch with id {batch_id} not found or access denied.")
    
    batch.quality_grade = data.quality_grade.value
    if data.inspection_notes:
        batch.notes = data.inspection_notes
    
    await session.commit()
    return await get_produce_batch_by_id(session, batch_id, auth)


async def delete_produce_batch(
    session: AsyncSession,
    batch_id: uuid.UUID,
    auth: AuthContext
) -> bool:
    """Delete (mark as rejected) a produce batch."""
    stmt = select(ProduceBatch).where(
        ProduceBatch.id == batch_id,
        ProduceBatch.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise ValueError(f"Produce batch with id {batch_id} not found or access denied.")
    
    batch.status = "rejected"
    await session.commit()
    return True
