from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext
from app.db import models
from app.schemas import cold_storage_unit as cold_storage_unit_schema
from app.services.helpers import get_or_404
from app.services import influxdb_service, prediction_service


async def get_cold_storage_units(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[cold_storage_unit_schema.ColdStorageUnitResponse]:
    stmt = (
        select(models.ColdStorageUnit)
        .where(models.ColdStorageUnit.tenant_id == tenant_id)
        .order_by(models.ColdStorageUnit.name.asc())
    )
    result = await session.execute(stmt)
    units = result.scalars().all()
    return [cold_storage_unit_schema.ColdStorageUnitResponse.model_validate(u) for u in units]


async def get_cold_storage_unit_by_id(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> cold_storage_unit_schema.ColdStorageUnitResponse:
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    return cold_storage_unit_schema.ColdStorageUnitResponse.model_validate(unit)


async def create_cold_storage_unit(
    session: AsyncSession,
    data: cold_storage_unit_schema.ColdStorageUnitCreate,
    tenant_id: uuid.UUID,
) -> cold_storage_unit_schema.ColdStorageUnitResponse:
    unit = models.ColdStorageUnit(
        tenant_id=tenant_id,
        **data.model_dump(),
    )
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return cold_storage_unit_schema.ColdStorageUnitResponse.model_validate(unit)


async def update_cold_storage_unit(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    data: cold_storage_unit_schema.ColdStorageUnitCreate,
    tenant_id: uuid.UUID,
) -> cold_storage_unit_schema.ColdStorageUnitResponse:
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    unit.name = data.name
    unit.latitude = data.latitude
    unit.longitude = data.longitude
    unit.capacity_volume = data.capacity_volume
    unit.is_active = data.is_active
    await session.commit()
    await session.refresh(unit)
    return cold_storage_unit_schema.ColdStorageUnitResponse.model_validate(unit)


async def delete_cold_storage_unit(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    await session.delete(unit)
    await session.commit()


# =============================================================================
# LIVE TELEMETRY ENDPOINTS
# =============================================================================


async def get_unit_telemetry(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Get current telemetry status for a cold storage unit.
    
    Returns latest sensor readings from InfluxDB plus computed metrics like RSL.
    """
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    
    asset_id = str(unit.id)
    
    # Fetch latest reading from InfluxDB
    latest = await influxdb_service.get_latest_reading(asset_id)
    
    # Compute CTH and CDOT from InfluxDB
    cth = await influxdb_service.compute_cth(asset_id, hours=24)
    cdot = await influxdb_service.compute_cdot(asset_id, hours=24)
    
    # Compute thermal compliance
    compliance = await influxdb_service.get_thermal_compliance(
        asset_id, min_temp=-2, max_temp=4, hours=24
    )
    
    return {
        "unit_id": asset_id,
        "unit_name": unit.name,
        "is_active": unit.is_active,
        "telemetry": {
            "temperature_celsius": latest.get("temperature"),
            "humidity_percent": latest.get("humidity"),
            "door_open": latest.get("door_open"),
            "battery_level": latest.get("battery_level"),
            "last_reading_time": latest.get("time"),
        },
        "metrics_24h": {
            "cumulative_thermal_history_degC_hours": cth,
            "cumulative_door_open_minutes": cdot,
            "thermal_compliance_percent": compliance.get("compliance_percent"),
            "total_readings": compliance.get("total_readings"),
        },
    }


async def get_unit_temperature_history(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    tenant_id: uuid.UUID,
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """
    Get temperature history for a cold storage unit.
    
    Returns time-series data from InfluxDB.
    """
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    asset_id = str(unit.id)
    
    history = await influxdb_service.get_temperature_history(asset_id, hours=hours)
    return history


async def get_unit_rsl(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    tenant_id: uuid.UUID,
    produce_type: str = "tomatoes",
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute Remaining Shelf Life (RSL) for produce in a cold storage unit.
    
    Uses live temperature from InfluxDB and RSL model from prediction_service.
    """
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, tenant_id)
    asset_id = str(unit.id)
    
    # Get latest temperature
    latest = await influxdb_service.get_latest_reading(asset_id)
    current_temp = latest.get("temperature")
    
    if current_temp is None:
        return {
            "unit_id": asset_id,
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
        "unit_id": asset_id,
        "unit_name": unit.name,
        "produce_type": produce_type,
        "batch_id": batch_id,
        "current_temperature_c": current_temp,
        "cth_deg_c_hours": cth,
        "rsl_hours": rsl_result.get("rsl_hours"),
        "rsl_days": round(rsl_result.get("rsl_hours", 0) / 24, 1),
        "quality_decay_rate": rsl_result.get("decay_rate"),
        "spoilage_risk": rsl_result.get("spoilage_risk"),
        "last_reading_time": latest.get("time"),
    }


def _is_active_facility_supervisor_assignment(record: models.StaffOperation) -> bool:
    metadata = record.extra_metadata or {}
    return (
        metadata.get("assignment_type") == "facility_supervisor"
        and metadata.get("assignment_status") == "active"
    )


def _build_assignment_response(
    record: models.StaffOperation,
    supervisor_name: str,
) -> cold_storage_unit_schema.FacilitySupervisorAssignmentResponse:
    metadata = record.extra_metadata or {}
    return cold_storage_unit_schema.FacilitySupervisorAssignmentResponse(
        assignment_id=record.id,
        facility_id=record.facility_id,
        supervisor_id=record.staff_id,
        supervisor_name=supervisor_name,
        assigned_at=record.created_at,
        assigned_by=metadata.get("assigned_by"),
        notes=metadata.get("notes"),
    )


async def assign_facility_supervisor(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    data: cold_storage_unit_schema.FacilitySupervisorAssignmentCreate,
    auth: AuthContext,
) -> cold_storage_unit_schema.FacilitySupervisorAssignmentResponse:
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, auth.tenant_id)

    supervisor_stmt = (
        select(models.User, models.UserRole)
        .join(models.UserRole, models.User.role_id == models.UserRole.id)
        .where(
            models.User.id == data.supervisor_id,
            models.User.tenant_id == auth.tenant_id,
        )
    )
    supervisor_result = await session.execute(supervisor_stmt)
    supervisor_row = supervisor_result.one_or_none()
    if not supervisor_row:
        raise ValueError(f"Supervisor {data.supervisor_id} not found")

    supervisor, supervisor_role = supervisor_row
    supervisor_role_name = (supervisor_role.name or "").strip().lower()
    if supervisor_role_name != "operator":
        raise ValueError(
            "Assigned supervisor must be a user with operator role"
        )

    existing_stmt = select(models.StaffOperation).where(
        models.StaffOperation.tenant_id == auth.tenant_id,
        models.StaffOperation.facility_id == unit.id,
        models.StaffOperation.staff_id == data.supervisor_id,
        models.StaffOperation.operation_type == "task",
    )
    existing_result = await session.execute(existing_stmt)
    existing_records = existing_result.scalars().all()
    for record in existing_records:
        if _is_active_facility_supervisor_assignment(record):
            supervisor_name = f"{supervisor.first_name} {supervisor.last_name}".strip()
            return _build_assignment_response(record, supervisor_name)

    record = models.StaffOperation(
        tenant_id=auth.tenant_id,
        staff_id=data.supervisor_id,
        operation_type="task",
        facility_id=unit.id,
        operation_date=date.today(),
        start_time=datetime.now(timezone.utc),
        task_description=f"Facility supervisor assignment for {unit.name}",
        extra_metadata={
            "assignment_type": "facility_supervisor",
            "assignment_status": "active",
            "assigned_by": str(auth.user_id),
            "notes": data.notes,
        },
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    supervisor_name = f"{supervisor.first_name} {supervisor.last_name}".strip()
    return _build_assignment_response(record, supervisor_name)


async def list_facility_supervisors(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    auth: AuthContext,
) -> cold_storage_unit_schema.FacilitySupervisorAssignmentListResponse:
    unit = await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, auth.tenant_id)

    stmt = select(models.StaffOperation).where(
        models.StaffOperation.tenant_id == auth.tenant_id,
        models.StaffOperation.facility_id == unit.id,
        models.StaffOperation.operation_type == "task",
    ).order_by(models.StaffOperation.created_at.desc())
    result = await session.execute(stmt)
    records = result.scalars().all()

    seen_supervisors: set[str] = set()
    items: list[cold_storage_unit_schema.FacilitySupervisorAssignmentResponse] = []

    for record in records:
        if not _is_active_facility_supervisor_assignment(record):
            continue

        supervisor = await session.get(models.User, record.staff_id)
        if not supervisor or supervisor.tenant_id != auth.tenant_id:
            continue

        supervisor_id = str(record.staff_id)
        if supervisor_id in seen_supervisors:
            continue

        seen_supervisors.add(supervisor_id)
        supervisor_name = f"{supervisor.first_name} {supervisor.last_name}".strip()
        items.append(_build_assignment_response(record, supervisor_name))

    return cold_storage_unit_schema.FacilitySupervisorAssignmentListResponse(
        items=items,
        total=len(items),
    )


async def remove_facility_supervisor_assignment(
    session: AsyncSession,
    cold_storage_unit_id: uuid.UUID,
    assignment_id: uuid.UUID,
    auth: AuthContext,
) -> None:
    await get_or_404(session, models.ColdStorageUnit, cold_storage_unit_id, auth.tenant_id)

    stmt = select(models.StaffOperation).where(
        models.StaffOperation.id == assignment_id,
        models.StaffOperation.tenant_id == auth.tenant_id,
        models.StaffOperation.facility_id == cold_storage_unit_id,
    )
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    if not record or not _is_active_facility_supervisor_assignment(record):
        raise ValueError(f"Supervisor assignment {assignment_id} not found")

    metadata = dict(record.extra_metadata or {})
    metadata["assignment_status"] = "removed"
    metadata["removed_at"] = datetime.now(timezone.utc).isoformat()
    metadata["removed_by"] = str(auth.user_id)
    record.extra_metadata = metadata

    if not record.end_time:
        record.end_time = datetime.now(timezone.utc)

    await session.commit()
