"""Service layer for Manifest CRUD operations."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.manifest import Manifest, ManifestItem
from app.db.models.user import User
from app.db.models.customer import Customer
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.db.models.reefer_truck import ReeferTruck
from app.schemas import manifest as manifest_schema


def generate_manifest_number(tenant_id: uuid.UUID) -> str:
    """Generate a unique manifest number."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_tenant = str(tenant_id)[:8]
    return f"MNF-{short_tenant.upper()}-{timestamp}"


async def create_manifest(
    session: AsyncSession,
    data: manifest_schema.ManifestCreate,
    auth: AuthContext
) -> manifest_schema.ManifestResponse:
    """Create a new manifest with items."""
    manifest_number = data.manifest_number or generate_manifest_number(auth.tenant_id)
    
    manifest = Manifest(
        tenant_id=auth.tenant_id,
        manifest_number=manifest_number,
        truck_id=data.truck_id,
        driver_id=data.driver_id,
        origin_facility_id=data.origin_facility_id,
        destination_facility_id=data.destination_facility_id,
        customer_id=data.customer_id,
        scheduled_departure=data.scheduled_departure,
        scheduled_arrival=data.scheduled_arrival,
        temperature_min_celsius=data.temperature_min_celsius,
        temperature_max_celsius=data.temperature_max_celsius,
        special_instructions=data.special_instructions,
        extra_metadata=data.metadata,
        status="draft"
    )
    session.add(manifest)
    await session.flush()
    
    # Add items
    total_weight = 0.0
    for item_data in data.items:
        item = ManifestItem(
            manifest_id=manifest.id,
            produce_batch_id=item_data.produce_batch_id,
            quantity_kg=item_data.quantity_kg,
            quantity_units=item_data.quantity_units,
            unit_type=item_data.unit_type,
            notes=item_data.notes
        )
        session.add(item)
        total_weight += item_data.quantity_kg
    
    manifest.total_weight_kg = total_weight
    manifest.total_items = len(data.items)
    
    await session.commit()
    await session.refresh(manifest)
    
    return await get_manifest_by_id(session, manifest.id, auth)


async def get_manifest_by_id(
    session: AsyncSession,
    manifest_id: uuid.UUID,
    auth: AuthContext
) -> manifest_schema.ManifestResponse:
    """Get manifest by ID with related data."""
    stmt = (
        select(Manifest)
        .options(selectinload(Manifest.items))
        .where(
            Manifest.id == manifest_id,
            Manifest.tenant_id == auth.tenant_id
        )
    )
    result = await session.execute(stmt)
    manifest = result.scalar_one_or_none()
    
    if not manifest:
        raise ValueError(f"Manifest with id {manifest_id} not found or access denied.")
    
    response = manifest_schema.ManifestResponse.model_validate(manifest)
    
    # Enrich with related names
    if manifest.truck_id:
        truck = await session.get(ReeferTruck, manifest.truck_id)
        if truck:
            response.truck_registration = truck.registration_number
    
    if manifest.driver_id:
        driver = await session.get(User, manifest.driver_id)
        if driver:
            response.driver_name = f"{driver.first_name} {driver.last_name}"
    
    customer = await session.get(Customer, manifest.customer_id)
    if customer:
        response.customer_name = customer.name
    
    origin = await session.get(ColdStorageUnit, manifest.origin_facility_id)
    if origin:
        response.origin_facility_name = origin.name
    
    dest = await session.get(ColdStorageUnit, manifest.destination_facility_id)
    if dest:
        response.destination_facility_name = dest.name
    
    response.items = [
        manifest_schema.ManifestItemResponse.model_validate(item) 
        for item in manifest.items
    ]
    
    return response


async def list_manifests(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    truck_id: Optional[uuid.UUID] = None,
    customer_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> manifest_schema.ManifestListResponse:
    """List manifests with filtering and pagination."""
    stmt = select(Manifest).where(Manifest.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(Manifest.id)).where(Manifest.tenant_id == auth.tenant_id)
    
    if status:
        stmt = stmt.where(Manifest.status == status)
        count_stmt = count_stmt.where(Manifest.status == status)
    
    if truck_id:
        stmt = stmt.where(Manifest.truck_id == truck_id)
        count_stmt = count_stmt.where(Manifest.truck_id == truck_id)
    
    if customer_id:
        stmt = stmt.where(Manifest.customer_id == customer_id)
        count_stmt = count_stmt.where(Manifest.customer_id == customer_id)
    
    if date_from:
        stmt = stmt.where(Manifest.scheduled_departure >= date_from)
        count_stmt = count_stmt.where(Manifest.scheduled_departure >= date_from)
    
    if date_to:
        stmt = stmt.where(Manifest.scheduled_departure <= date_to)
        count_stmt = count_stmt.where(Manifest.scheduled_departure <= date_to)
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    stmt = (
        stmt.options(selectinload(Manifest.items))
        .offset(offset)
        .limit(page_size)
        .order_by(Manifest.scheduled_departure.desc())
    )
    
    result = await session.execute(stmt)
    manifests = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    items = []
    for m in manifests:
        response = manifest_schema.ManifestResponse.model_validate(m)
        response.items = [
            manifest_schema.ManifestItemResponse.model_validate(item) 
            for item in m.items
        ]
        items.append(response)
    
    return manifest_schema.ManifestListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


async def update_manifest(
    session: AsyncSession,
    manifest_id: uuid.UUID,
    data: manifest_schema.ManifestUpdate,
    auth: AuthContext
) -> manifest_schema.ManifestResponse:
    """Update a manifest."""
    stmt = select(Manifest).where(
        Manifest.id == manifest_id,
        Manifest.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    manifest = result.scalar_one_or_none()
    
    if not manifest:
        raise ValueError(f"Manifest with id {manifest_id} not found or access denied.")
    
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = data.status.value
    
    for field, value in update_data.items():
        setattr(manifest, field, value)
    
    await session.commit()
    return await get_manifest_by_id(session, manifest_id, auth)


async def update_manifest_status(
    session: AsyncSession,
    manifest_id: uuid.UUID,
    data: manifest_schema.ManifestStatusUpdate,
    auth: AuthContext
) -> manifest_schema.ManifestResponse:
    """Update manifest status."""
    stmt = select(Manifest).where(
        Manifest.id == manifest_id,
        Manifest.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    manifest = result.scalar_one_or_none()
    
    if not manifest:
        raise ValueError(f"Manifest with id {manifest_id} not found or access denied.")
    
    manifest.status = data.status.value
    if data.notes:
        manifest.delivery_notes = data.notes
    if data.actual_departure:
        manifest.actual_departure = data.actual_departure
    if data.actual_arrival:
        manifest.actual_arrival = data.actual_arrival
    
    await session.commit()
    return await get_manifest_by_id(session, manifest_id, auth)


async def delete_manifest(
    session: AsyncSession,
    manifest_id: uuid.UUID,
    auth: AuthContext
) -> bool:
    """Delete a manifest (only if draft or cancelled)."""
    stmt = select(Manifest).where(
        Manifest.id == manifest_id,
        Manifest.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    manifest = result.scalar_one_or_none()
    
    if not manifest:
        raise ValueError(f"Manifest with id {manifest_id} not found or access denied.")
    
    if manifest.status not in ("draft", "cancelled"):
        raise ValueError("Can only delete manifests in draft or cancelled status")
    
    await session.delete(manifest)
    await session.commit()
    return True
