"""Service layer for ReeferTruck CRUD operations."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db.models.reefer_truck import ReeferTruck
from app.db.models.user import User
from app.schemas import reefer_truck as truck_schema
from app.services import influxdb_service, prediction_service


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
        extra_metadata=data.metadata,
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


# =============================================================================
# LIVE TELEMETRY ENDPOINTS
# =============================================================================


async def get_truck_telemetry(
    session: AsyncSession,
    truck_id: uuid.UUID,
    auth: AuthContext
) -> Dict[str, Any]:
    """
    Get current telemetry status for a reefer truck.
    
    Returns latest sensor readings from InfluxDB plus computed metrics.
    """
    stmt = select(ReeferTruck).where(
        ReeferTruck.id == truck_id,
        ReeferTruck.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    truck = result.scalar_one_or_none()
    
    if not truck:
        raise ValueError(f"Reefer truck with id {truck_id} not found or access denied.")
    
    asset_id = str(truck.id)
    
    # Fetch latest reading from InfluxDB
    latest = await influxdb_service.get_latest_reading(asset_id)
    
    # Compute CTH and CDOT from InfluxDB
    cth = await influxdb_service.compute_cth(asset_id, hours=24)
    cdot = await influxdb_service.compute_cdot(asset_id, hours=24)
    
    # Compute thermal compliance
    min_temp = truck.min_temperature_celsius or -20
    max_temp = truck.max_temperature_celsius or 5
    compliance = await influxdb_service.get_thermal_compliance(
        asset_id, min_temp=min_temp, max_temp=max_temp, hours=24
    )
    
    return {
        "truck_id": asset_id,
        "registration_number": truck.registration_number,
        "status": truck.status,
        "telemetry": {
            "temperature_celsius": latest.get("temperature") or truck.current_temperature_celsius,
            "humidity_percent": latest.get("humidity"),
            "door_open": latest.get("door_open"),
            "battery_level": latest.get("battery_level"),
            "last_reading_time": latest.get("time"),
            "current_location": truck.current_location,
        },
        "temperature_range": {
            "min_celsius": min_temp,
            "max_celsius": max_temp,
        },
        "metrics_24h": {
            "cumulative_thermal_history_degC_hours": cth,
            "cumulative_door_open_minutes": cdot,
            "thermal_compliance_percent": compliance.get("compliance_percent"),
            "total_readings": compliance.get("total_readings"),
        },
    }


async def get_truck_temperature_history(
    session: AsyncSession,
    truck_id: uuid.UUID,
    auth: AuthContext,
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """
    Get temperature history for a reefer truck.
    
    Returns time-series data from InfluxDB.
    """
    stmt = select(ReeferTruck).where(
        ReeferTruck.id == truck_id,
        ReeferTruck.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    truck = result.scalar_one_or_none()
    
    if not truck:
        raise ValueError(f"Reefer truck with id {truck_id} not found or access denied.")
    
    asset_id = str(truck.id)
    history = await influxdb_service.get_temperature_history(asset_id, hours=hours)
    return history


async def get_truck_rsl(
    session: AsyncSession,
    truck_id: uuid.UUID,
    auth: AuthContext,
    produce_type: str = "tomatoes",
    manifest_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute Remaining Shelf Life (RSL) for produce in a reefer truck.
    
    Uses live temperature from InfluxDB and RSL model from prediction_service.
    """
    stmt = select(ReeferTruck).where(
        ReeferTruck.id == truck_id,
        ReeferTruck.tenant_id == auth.tenant_id
    )
    result = await session.execute(stmt)
    truck = result.scalar_one_or_none()
    
    if not truck:
        raise ValueError(f"Reefer truck with id {truck_id} not found or access denied.")
    
    asset_id = str(truck.id)
    
    # Get latest temperature
    latest = await influxdb_service.get_latest_reading(asset_id)
    current_temp = latest.get("temperature") or truck.current_temperature_celsius
    
    if current_temp is None:
        return {
            "truck_id": asset_id,
            "error": "No temperature data available",
            "rsl_hours": None,
        }
    
    # Compute CTH
    cth = await influxdb_service.compute_cth(asset_id, hours=24)
    
    # Compute RSL
    rsl_result = prediction_service.compute_rsl(
        produce_type=produce_type,
        current_temp_c=current_temp,
        humidity=latest.get("humidity", 85.0),
        time_since_harvest_hours=0,  # Unknown, assuming fresh
    )
    
    return {
        "truck_id": asset_id,
        "registration_number": truck.registration_number,
        "produce_type": produce_type,
        "manifest_id": manifest_id,
        "current_temperature_c": current_temp,
        "cth_deg_c_hours": cth,
        "rsl_hours": rsl_result.get("rsl_hours"),
        "rsl_days": round(rsl_result.get("rsl_hours", 0) / 24, 1),
        "quality_decay_rate": rsl_result.get("decay_rate"),
        "spoilage_risk": rsl_result.get("spoilage_risk"),
        "last_reading_time": latest.get("time"),
    }
