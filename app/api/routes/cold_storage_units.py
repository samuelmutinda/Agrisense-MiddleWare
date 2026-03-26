from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext, require_role
from app.schemas import cold_storage_unit as cold_storage_unit_schema
from app.services import cold_storage_unit_service

router = APIRouter(prefix="/cold-storage-units", tags=["cold-storage-units"])


@router.get("", response_model=list[cold_storage_unit_schema.ColdStorageUnitResponse])
async def list_cold_storage_units(
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.get_cold_storage_units(
        session, auth.tenant_id
    )


@router.get(
    "/{cold_storage_unit_id}",
    response_model=cold_storage_unit_schema.ColdStorageUnitResponse,
)
async def get_cold_storage_unit(
    cold_storage_unit_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.get_cold_storage_unit_by_id(
        session, cold_storage_unit_id, auth.tenant_id
    )


@router.get(
    "/{cold_storage_unit_id}/supervisor-assignments",
    response_model=cold_storage_unit_schema.FacilitySupervisorAssignmentListResponse,
)
async def list_facility_supervisors(
    cold_storage_unit_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.list_facility_supervisors(
        session=session,
        cold_storage_unit_id=cold_storage_unit_id,
        auth=auth,
    )


@router.post(
    "/{cold_storage_unit_id}/supervisor-assignments",
    response_model=cold_storage_unit_schema.FacilitySupervisorAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_facility_supervisor(
    cold_storage_unit_id: uuid.UUID,
    payload: cold_storage_unit_schema.FacilitySupervisorAssignmentCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(require_role("supervisor", "manager", "operator")),
):
    try:
        return await cold_storage_unit_service.assign_facility_supervisor(
            session=session,
            cold_storage_unit_id=cold_storage_unit_id,
            data=payload,
            auth=auth,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{cold_storage_unit_id}/supervisor-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_facility_supervisor_assignment(
    cold_storage_unit_id: uuid.UUID,
    assignment_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(require_role("supervisor", "manager", "operator")),
):
    try:
        await cold_storage_unit_service.remove_facility_supervisor_assignment(
            session=session,
            cold_storage_unit_id=cold_storage_unit_id,
            assignment_id=assignment_id,
            auth=auth,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None


@router.post(
    "",
    response_model=cold_storage_unit_schema.ColdStorageUnitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cold_storage_unit(
    payload: cold_storage_unit_schema.ColdStorageUnitCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.create_cold_storage_unit(
        session, payload, auth.tenant_id
    )


@router.put(
    "/{cold_storage_unit_id}",
    response_model=cold_storage_unit_schema.ColdStorageUnitResponse,
)
async def update_cold_storage_unit(
    cold_storage_unit_id: uuid.UUID,
    payload: cold_storage_unit_schema.ColdStorageUnitCreate,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await cold_storage_unit_service.update_cold_storage_unit(
        session, cold_storage_unit_id, payload, auth.tenant_id
    )


@router.delete("/{cold_storage_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cold_storage_unit(
    cold_storage_unit_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    await cold_storage_unit_service.delete_cold_storage_unit(
        session, cold_storage_unit_id, auth.tenant_id
    )
    return None


# =============================================================================
# LIVE TELEMETRY ENDPOINTS
# =============================================================================


@router.get("/{cold_storage_unit_id}/telemetry")
async def get_unit_telemetry(
    cold_storage_unit_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Get current telemetry status for a cold storage unit.
    
    Returns:
    - Latest sensor readings (temperature, humidity, door state)
    - 24h metrics (CTH, CDOT, thermal compliance)
    """
    return await cold_storage_unit_service.get_unit_telemetry(
        session, cold_storage_unit_id, auth.tenant_id
    )


@router.get("/{cold_storage_unit_id}/temperature-history")
async def get_unit_temperature_history(
    cold_storage_unit_id: uuid.UUID,
    hours: int = Query(default=24, ge=1, le=720, description="Hours of history to retrieve"),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Get temperature history for a cold storage unit.
    
    Returns time-series data from InfluxDB.
    """
    return await cold_storage_unit_service.get_unit_temperature_history(
        session, cold_storage_unit_id, auth.tenant_id, hours=hours
    )


@router.get("/{cold_storage_unit_id}/rsl")
async def get_unit_rsl(
    cold_storage_unit_id: uuid.UUID,
    produce_type: str = Query(default="tomatoes", description="Type of produce"),
    batch_id: Optional[str] = Query(default=None, description="Optional batch ID"),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Compute Remaining Shelf Life (RSL) for produce in a cold storage unit.
    
    Uses live temperature from InfluxDB and RSL prediction model.
    """
    return await cold_storage_unit_service.get_unit_rsl(
        session, cold_storage_unit_id, auth.tenant_id,
        produce_type=produce_type, batch_id=batch_id
    )
