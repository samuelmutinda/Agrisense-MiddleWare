"""Service layer for ReeferTruck CRUD operations."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.reefer_truck import ReeferTruck
from app.db.models.user import User
from app.schemas import reefer_truck as truck_schema


async def create_reefer_truck(
    session: AsyncSession,
    data: truck_schema.ReeferTruckCreate,
    auth: AuthContext
) -> truck_schema.ReeferTruckResponse:
    """Create a new reefer truck."""
    truck = ReeferTruck(
        tenant_id=auth.tenant_id,
        registration_number=data.registration_number,
        make=data.make,
        model=data.model,
        year=data.year,
        capacity_kg=data.capacity_kg,
        capacity_cubic_meters=data.capacity_cubic_meters,
        min_temperature_celsius=data.min_temperature_celsius,
        max_temperature_celsius=data.max_temperature_celsius,
        fuel_type=data.fuel_type,
        vin_number=data.vin_number,
        fleet_id=data.fleet_id,
        assigned_driver_id=data.assigned_driver_id,
        last_service_date=data.last_service_date,
        next_service_due=data.next_service_due,
        insurance_expiry=data.insurance_expiry,
        metadata=data.metadata,
        status="available"
    )
    session.add(truck)
    await session.commit()
    await session.refresh(truck)
    
    response = truck_schema.ReeferTruckResponse.model_validate(truck)
    
    # Get driver name if assigned
    if data.assigned_driver_id:
        driver = await session.get(User, data.assigned_driver_id)
        if driver:
            response.assigned_driver_name = f"{driver.first_name} {driver.last_name}"
    
    return response


async def get_reefer_truck_by_id(
    session: AsyncSession,
    truck_id: uuid.UUID,
    auth: AuthContext
) -> truck_schema.ReeferTruckResponse:
    """Get reefer truck by ID."""
    stmt = select(ReeferTruck).where(
        ReeferTruck.id == truck_id,
        ReeferTruck.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    truck = result.scalar_one_or_none()
    
    if not truck:
        raise ValueError(f"Reefer truck with id {truck_id} not found or access denied.")
    
    response = truck_schema.ReeferTruckResponse.model_validate(truck)
    
    if truck.assigned_driver_id:
        driver = await session.get(User, truck.assigned_driver_id)
        if driver:
            response.assigned_driver_name = f"{driver.first_name} {driver.last_name}"
    
    return response


async def list_reefer_trucks(
    session: AsyncSession,
    auth: AuthContext,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    assigned_driver_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None
) -> truck_schema.ReeferTruckListResponse:
    """List reefer trucks with filtering and pagination."""
    stmt = select(ReeferTruck).where(ReeferTruck.tenant_id == auth.tenant_id)
    count_stmt = select(func.count(ReeferTruck.id)).where(ReeferTruck.tenant_id == auth.tenant_id)
    
    if status:
        stmt = stmt.where(ReeferTruck.status == status)
        count_stmt = count_stmt.where(ReeferTruck.status == status)
    
    if assigned_driver_id:
        stmt = stmt.where(ReeferTruck.assigned_driver_id == assigned_driver_id)
        count_stmt = count_stmt.where(ReeferTruck.assigned_driver_id == assigned_driver_id)
    
    if search:
        search_filter = (
            ReeferTruck.registration_number.ilike(f"%{search}%") |
            ReeferTruck.make.ilike(f"%{search}%") |
            ReeferTruck.model.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(ReeferTruck.created_at.desc())
    
    result = await session.execute(stmt)
    trucks = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return truck_schema.ReeferTruckListResponse(
        items=[truck_schema.ReeferTruckResponse.model_validate(t) for t in trucks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


async def update_reefer_truck(
    session: AsyncSession,
    truck_id: uuid.UUID,
    data: truck_schema.ReeferTruckUpdate,
    auth: AuthContext
) -> truck_schema.ReeferTruckResponse:
    """Update a reefer truck."""
    stmt = select(ReeferTruck).where(
        ReeferTruck.id == truck_id,
        ReeferTruck.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    truck = result.scalar_one_or_none()
    
    if not truck:
        raise ValueError(f"Reefer truck with id {truck_id} not found or access denied.")
    
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = data.status.value
    
    for field, value in update_data.items():
        setattr(truck, field, value)
    
    await session.commit()
    await session.refresh(truck)
    return truck_schema.ReeferTruckResponse.model_validate(truck)


async def update_truck_location(
    session: AsyncSession,
    truck_id: uuid.UUID,
    data: truck_schema.TruckLocationUpdate,
    auth: AuthContext
) -> truck_schema.ReeferTruckResponse:
    """Update truck location and temperature telemetry."""
    stmt = select(ReeferTruck).where(
        ReeferTruck.id == truck_id,
        ReeferTruck.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    truck = result.scalar_one_or_none()
    
    if not truck:
        raise ValueError(f"Reefer truck with id {truck_id} not found or access denied.")
    
    truck.current_location = {"lat": data.latitude, "lng": data.longitude}
    if data.temperature_celsius is not None:
        truck.current_temperature_celsius = data.temperature_celsius
    
    await session.commit()
    await session.refresh(truck)
    return truck_schema.ReeferTruckResponse.model_validate(truck)


async def delete_reefer_truck(
    session: AsyncSession,
    truck_id: uuid.UUID,
    auth: AuthContext
) -> bool:
    """Delete (set out of service) a reefer truck."""
    stmt = select(ReeferTruck).where(
        ReeferTruck.id == truck_id,
        ReeferTruck.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    truck = result.scalar_one_or_none()
    
    if not truck:
        raise ValueError(f"Reefer truck with id {truck_id} not found or access denied.")
    
    truck.status = "out_of_service"
    await session.commit()
    return True
