"""
Digital Twin analytics endpoints.

Exposes pre-computed cold-chain simulation data stored in the InfluxDB
`digital_twin` bucket (measurement: `cold_chain`).  Data is populated by
the ingest.py script from the Agrisense-Project-default physics engine CSV.

Route surface:
  GET  /api/digital-twin/crops/summary
  GET  /api/digital-twin/crops/{crop_type}/sensors
  GET  /api/digital-twin/crops/{crop_type}/decay
  GET  /api/digital-twin/spoilage
  GET  /api/digital-twin/mold-risk
  GET  /api/digital-twin/energy
  GET  /api/digital-twin/quality-distribution
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api import deps
from app.core.security import AuthContext
from app.services import digital_twin_service

router = APIRouter(prefix="/digital-twin", tags=["digital-twin"])


# ═════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═════════════════════════════════════════════════════════════════════════════

class CropSummary(BaseModel):
    crop_type: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    quality_index: Optional[float] = None
    rsl_percent: Optional[float] = None


class SpoilageCount(BaseModel):
    crop_type: Optional[str] = None
    spoiled_count: int = 0


class MoldRiskEvent(BaseModel):
    timestamp: Optional[str] = None
    crop_type: Optional[str] = None
    mold_risk_score: Optional[float] = None
    scenario_id: Optional[str] = None
    quality_status: Optional[str] = None


class SensorPoint(BaseModel):
    timestamp: Optional[str] = None
    value: Optional[float] = None


class DecayBreakdown(BaseModel):
    crop_type: str
    decay_temperature: Optional[float] = None
    decay_humidity: Optional[float] = None
    decay_co2: Optional[float] = None
    decay_microbial: Optional[float] = None
    decay_infrastructure: Optional[float] = None
    flu_total: Optional[float] = None


class EnergyStats(BaseModel):
    crop_type: Optional[str] = None
    energy_consumed_kwh: Optional[float] = None
    compressor_power_kw: Optional[float] = None


class QualityDistribution(BaseModel):
    quality_status: Optional[str] = None
    count: int = 0


# ═════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/crops/summary",
    response_model=List[CropSummary],
    summary="Mean sensor + quality stats per crop type",
)
async def crop_summary(
    crop_type: Optional[str] = Query(default=None, description="Filter to a single crop type"),
    hours: int = Query(default=24, ge=1, le=8760, description="Analysis window in hours"),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Returns mean temperature, humidity, quality_index, and rsl_percent for
    every crop type present in the digital-twin bucket.  Optionally filter
    to a single crop.
    """
    data = await digital_twin_service.get_crop_summary(crop_type=crop_type, hours=hours)
    return [CropSummary(**row) for row in data]


@router.get(
    "/crops/{crop_type}/sensors",
    response_model=List[SensorPoint],
    summary="Aggregated sensor time-series for a crop",
)
async def crop_sensor_history(
    crop_type: str,
    field: str = Query(default="temperature", description="Field to retrieve"),
    hours: int = Query(default=24, ge=1, le=720, description="Hours of history"),
    interval_minutes: int = Query(default=5, ge=1, le=60, description="Aggregation window (minutes)"),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Return a downsampled time-series for a specific sensor field and crop.
    Supported fields: temperature, humidity, co2_ppm, ethylene_ppm,
    quality_index, rsl_percent, mold_risk_score, etc.
    """
    allowed_fields = {
        "temperature", "humidity", "co2_ppm", "light_lux", "ethylene_ppm",
        "quality_index", "rsl_hours", "rsl_percent", "mold_risk_score",
        "water_loss_percent", "microbial_load", "energy_consumed_kwh",
        "compressor_power_kw", "flu_total",
    }
    if field not in allowed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field '{field}' not allowed. Choose from: {sorted(allowed_fields)}",
        )

    data = await digital_twin_service.get_sensor_history(
        crop_type=crop_type,
        field_name=field,
        hours=hours,
        interval_minutes=interval_minutes,
    )
    return [SensorPoint(**row) for row in data]


@router.get(
    "/crops/{crop_type}/decay",
    response_model=DecayBreakdown,
    summary="Decay sub-model breakdown for a crop",
)
async def crop_decay_breakdown(
    crop_type: str,
    hours: int = Query(default=24, ge=1, le=720, description="Analysis window in hours"),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Mean value for each decay sub-model (temperature, humidity, CO₂,
    microbial, infrastructure) and cumulative FLU for a crop type.
    """
    data = await digital_twin_service.get_decay_breakdown(crop_type=crop_type, hours=hours)
    if not data:
        return DecayBreakdown(crop_type=crop_type)
    return DecayBreakdown(**data)


@router.get(
    "/spoilage",
    response_model=List[SpoilageCount],
    summary="Spoiled reading counts per crop type",
)
async def spoilage_counts(
    hours: int = Query(default=720, ge=1, le=8760, description="Analysis window in hours"),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Count of readings where is_spoiled == true, grouped by crop_type.
    Useful for the Manager dashboard spoilage bar chart.
    """
    data = await digital_twin_service.get_spoilage_counts(hours=hours)
    return [SpoilageCount(**row) for row in data]


@router.get(
    "/mold-risk",
    response_model=List[MoldRiskEvent],
    summary="Recent high-mold-risk events",
)
async def mold_risk_events(
    threshold: float = Query(default=0.7, ge=0, le=1, description="Mold risk score threshold"),
    hours: int = Query(default=168, ge=1, le=8760, description="Analysis window in hours"),
    limit: int = Query(default=50, ge=1, le=500, description="Max events to return"),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Return the most recent data points where mold_risk_score exceeds
    the given threshold, sorted newest-first.
    """
    data = await digital_twin_service.get_mold_risk_events(
        threshold=threshold, hours=hours, limit=limit,
    )
    return [MoldRiskEvent(**row) for row in data]


@router.get(
    "/energy",
    response_model=List[EnergyStats],
    summary="Energy consumption stats per crop type",
)
async def energy_stats(
    hours: int = Query(default=24, ge=1, le=8760, description="Analysis window in hours"),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Mean energy_consumed_kwh and compressor_power_kw per crop_type.
    Used by the Admin energy-optimisation screen.
    """
    data = await digital_twin_service.get_energy_stats(hours=hours)
    return [EnergyStats(**row) for row in data]


@router.get(
    "/quality-distribution",
    response_model=List[QualityDistribution],
    summary="Quality status distribution",
)
async def quality_distribution(
    crop_type: Optional[str] = Query(default=None, description="Filter by crop type"),
    hours: int = Query(default=168, ge=1, le=8760, description="Analysis window in hours"),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Count of readings per quality_status tag (GOOD, MARGINAL, POOR, SPOILED).
    Powers the quality distribution doughnut chart on the analytics dashboard.
    """
    data = await digital_twin_service.get_quality_distribution(
        crop_type=crop_type, hours=hours,
    )
    return [QualityDistribution(**row) for row in data]
