"""
Telemetry query and ingestion endpoints.

Exposes asset-scoped telemetry data stored in InfluxDB to authenticated
frontend clients. All query endpoints are tenant-scoped — the requesting
user's tenant_id is validated before the asset is resolved.

Ingestion:
  - IoT devices ingest via ChirpStack webhooks (/api/integrations/chirpstack/events)
  - This module adds a direct REST ingest path for manual or test ingestion

Query surface (matches API_Frontend_Integration_Roadmap.md §3.2):
  GET  /api/assets/{asset_id}/telemetry/latest
  GET  /api/assets/{asset_id}/telemetry/history
  GET  /api/assets/{asset_id}/telemetry/cth
  GET  /api/assets/{asset_id}/telemetry/cdot
  GET  /api/assets/{asset_id}/telemetry/compliance
  POST /api/telemetry/ingest
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import AuthContext
from app.db import models
from app.services import influxdb_service
from app.ws.manager import manager

router = APIRouter(tags=["telemetry"])


# =============================================================================
# HELPERS
# =============================================================================


async def _resolve_asset_tenant(
    session: AsyncSession,
    asset_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    """
    Verify the asset belongs to the requesting tenant.

    Checks ColdStorageUnit and ReeferTruck tables in that order.
    Raises 404 when the asset does not exist within the tenant's scope.
    This prevents cross-tenant data leakage at the query layer.
    """
    asset_id_str = str(asset_id)
    tenant_id_str = str(tenant_id)

    # Check cold storage units
    stmt = select(models.ColdStorageUnit).where(
        models.ColdStorageUnit.id == asset_id,
        models.ColdStorageUnit.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        return

    # Check reefer trucks
    stmt = select(models.ReeferTruck).where(
        models.ReeferTruck.id == asset_id,
        models.ReeferTruck.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Asset {asset_id_str} not found in your organisation.",
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class LatestReadingResponse(BaseModel):
    asset_id: str
    timestamp: Optional[str]
    temperature: Optional[float]
    humidity: Optional[float]
    door_open: Optional[bool]
    battery_level: Optional[float]
    device_id: Optional[str]


class TelemetryHistoryPoint(BaseModel):
    timestamp: Optional[str]
    temperature: Optional[float]
    humidity: Optional[float]


class CTHResponse(BaseModel):
    asset_id: str
    cth: float
    setpoint: float
    hours: int
    unit: str = "degree-hours"


class CDOTResponse(BaseModel):
    asset_id: str
    cdot_seconds: int
    window_minutes: int


class ThermalComplianceResponse(BaseModel):
    asset_id: str
    compliance_percent: float
    total_readings: int
    compliant_readings: int
    min_temp: float
    max_temp: float
    hours: int


class TelemetryIngestRequest(BaseModel):
    """
    Direct REST telemetry ingestion payload.

    Intended for manual testing, simulator seeding, and non-ChirpStack devices.
    Production IoT devices should use the ChirpStack webhook path.
    """
    device_id: str
    asset_id: str
    asset_type: str = "cold_storage_unit"
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    door_open: Optional[bool] = None
    battery_level: Optional[float] = None
    signal_strength: Optional[int] = None


class TelemetryIngestResponse(BaseModel):
    accepted: bool
    device_id: str
    asset_id: str


# =============================================================================
# QUERY ENDPOINTS
# =============================================================================


@router.get(
    "/assets/{asset_id}/telemetry/latest",
    response_model=LatestReadingResponse,
    summary="Latest telemetry reading for an asset",
)
async def get_latest_telemetry(
    asset_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Return the most recent telemetry reading recorded for the specified asset.

    Queries the raw InfluxDB bucket (sensor_reading measurement) scoped to
    the asset_id. Tenant ownership is validated before any data is returned.

    Returns null field values when InfluxDB is unconfigured or has no data
    for the asset — the response always includes the asset_id field.
    """
    await _resolve_asset_tenant(session, asset_id, auth.tenant_id)

    reading = await influxdb_service.get_latest_reading(str(asset_id))
    if reading is None:
        return LatestReadingResponse(
            asset_id=str(asset_id),
            timestamp=None,
            temperature=None,
            humidity=None,
            door_open=None,
            battery_level=None,
            device_id=None,
        )

    return LatestReadingResponse(
        asset_id=str(asset_id),
        timestamp=reading.get("timestamp"),
        temperature=reading.get("temperature"),
        humidity=reading.get("humidity"),
        door_open=reading.get("door_open"),
        battery_level=reading.get("battery_level"),
        device_id=reading.get("device_id"),
    )


@router.get(
    "/assets/{asset_id}/telemetry/history",
    response_model=List[TelemetryHistoryPoint],
    summary="Historical telemetry for an asset",
)
async def get_telemetry_history(
    asset_id: uuid.UUID,
    hours: int = Query(default=24, ge=1, le=720, description="Hours of history to return"),
    interval_minutes: int = Query(default=5, ge=1, le=60, description="Aggregation window in minutes"),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Return aggregated temperature and humidity history for an asset.

    Data is aggregated using a mean window of `interval_minutes` minutes.
    Results are sorted oldest-first. Up to 720 hours (30 days) of history
    can be retrieved; larger windows will use wider aggregation intervals
    to stay within practical response sizes.

    Returns an empty list when InfluxDB is unconfigured or has no data.
    """
    await _resolve_asset_tenant(session, asset_id, auth.tenant_id)

    history = await influxdb_service.get_temperature_history(
        asset_id=str(asset_id),
        hours=hours,
        interval_minutes=interval_minutes,
    )

    return [TelemetryHistoryPoint(**point) for point in history]


@router.get(
    "/assets/{asset_id}/telemetry/cth",
    response_model=CTHResponse,
    summary="Cumulative Thermal History for an asset",
)
async def get_cth(
    asset_id: uuid.UUID,
    setpoint: float = Query(default=4.0, description="Target temperature setpoint in °C"),
    hours: int = Query(default=24, ge=1, le=720, description="Analysis window in hours"),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Compute Cumulative Thermal History (CTH) in degree-hours above the setpoint.

    CTH = ∫(T − setpoint) dt  for all readings where T > setpoint.

    Returns 0.0 when InfluxDB is unconfigured or has no readings in the window.
    A higher CTH value indicates more cumulative deviation from the cold chain
    target, which directly reduces Remaining Shelf Life (RSL).
    """
    await _resolve_asset_tenant(session, asset_id, auth.tenant_id)

    cth = await influxdb_service.compute_cth(
        asset_id=str(asset_id),
        setpoint=setpoint,
        hours=hours,
    )

    return CTHResponse(
        asset_id=str(asset_id),
        cth=cth,
        setpoint=setpoint,
        hours=hours,
    )


@router.get(
    "/assets/{asset_id}/telemetry/cdot",
    response_model=CDOTResponse,
    summary="Cumulative Door Open Time for an asset",
)
async def get_cdot(
    asset_id: uuid.UUID,
    window_minutes: int = Query(default=360, ge=1, le=1440, description="Analysis window in minutes"),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Compute Cumulative Door Open Time (CDOT) in seconds over the given window.

    CDOT is the total elapsed time the door sensor reported an open state within
    the specified window. Used as an input to RSL and spoilage risk calculations.

    Returns 0 when InfluxDB is unconfigured, the device has no door sensor, or
    the door was never opened in the analysis window.
    """
    await _resolve_asset_tenant(session, asset_id, auth.tenant_id)

    cdot = await influxdb_service.compute_cdot(
        asset_id=str(asset_id),
        window_minutes=window_minutes,
    )

    return CDOTResponse(
        asset_id=str(asset_id),
        cdot_seconds=cdot,
        window_minutes=window_minutes,
    )


@router.get(
    "/assets/{asset_id}/telemetry/compliance",
    response_model=ThermalComplianceResponse,
    summary="Thermal compliance for an asset",
)
async def get_thermal_compliance(
    asset_id: uuid.UUID,
    min_temp: float = Query(default=2.0, description="Minimum acceptable temperature in °C"),
    max_temp: float = Query(default=8.0, description="Maximum acceptable temperature in °C"),
    hours: int = Query(default=24, ge=1, le=720, description="Analysis window in hours"),
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Calculate the percentage of time an asset stayed within the temperature band.

    Compliance percentage = (readings within [min_temp, max_temp]) / total readings × 100.

    Returns 100% compliance when InfluxDB is unconfigured or has no readings
    (no data = no breach recorded).
    """
    await _resolve_asset_tenant(session, asset_id, auth.tenant_id)

    result = await influxdb_service.get_thermal_compliance(
        asset_id=str(asset_id),
        min_temp=min_temp,
        max_temp=max_temp,
        hours=hours,
    )

    return ThermalComplianceResponse(
        asset_id=str(asset_id),
        compliance_percent=result.get("compliance_percent", 100.0),
        total_readings=result.get("total_readings", 0),
        compliant_readings=result.get("compliant_readings", 0),
        min_temp=min_temp,
        max_temp=max_temp,
        hours=hours,
    )


# =============================================================================
# INGESTION ENDPOINT
# =============================================================================


@router.post(
    "/telemetry/ingest",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Direct telemetry ingestion (manual / simulator)",
)
async def ingest_telemetry(
    payload: TelemetryIngestRequest,
    session: AsyncSession = Depends(deps.get_db),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Accept a single telemetry reading and persist it to InfluxDB.

    This endpoint is designed for:
    - Manual data entry during development and testing
    - Simulator seeding (replaces LiveSimulationService direct writes)
    - Non-LoRaWAN devices that cannot use the ChirpStack webhook path

    **Production IoT devices** should use the ChirpStack webhook path at
    `POST /api/integrations/chirpstack/events` instead.

    The asset_id in the payload does not need to be tenant-verified here
    because the JWT already scopes the write to the authenticated tenant.
    The tenant_id tag is injected automatically from the auth context.
    """
    success = await influxdb_service.write_telemetry_point(
        device_id=payload.device_id,
        asset_id=payload.asset_id,
        asset_type=payload.asset_type,
        temperature=payload.temperature,
        humidity=payload.humidity,
        door_open=payload.door_open,
        battery_level=payload.battery_level,
        signal_strength=payload.signal_strength,
        tenant_id=str(auth.tenant_id),
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="InfluxDB is not configured or unavailable. Telemetry not persisted.",
        )

    # Emit tenant-scoped websocket event so clients can update instantly.
    # This mirrors ChirpStack-derived `sensor_uplink` payload shape.
    await manager.broadcast(
        tenant_id=str(auth.tenant_id),
        payload={
            "type": "sensor_uplink",
            "event": "direct_ingest",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tenant_id": str(auth.tenant_id),
            "device_id": payload.device_id,
            "cold_storage_unit_id": payload.asset_id,
            "cold_storage_unit_name": payload.asset_id,
            "temperature": payload.temperature,
            "humidity": payload.humidity,
            "battery_level": payload.battery_level,
            "decoded_object": {
                "door_open": payload.door_open,
                "asset_type": payload.asset_type,
                "signal_strength": payload.signal_strength,
            },
        },
    )

    return TelemetryIngestResponse(
        accepted=True,
        device_id=payload.device_id,
        asset_id=payload.asset_id,
    )
