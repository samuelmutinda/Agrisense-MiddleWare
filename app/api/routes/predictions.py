"""
Prediction API endpoints for RSL and spoilage forecasting.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api import deps
from app.core.security import AuthContext
from app.services import prediction_service, influxdb_service

router = APIRouter(prefix="/predictions", tags=["predictions"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class RSLRequest(BaseModel):
    asset_id: str
    produce_type: str
    setpoint: float = 4.0
    hours_to_analyze: int = 24
    base_shelf_life_hours: float = 168.0


class RSLResponse(BaseModel):
    rsl_index: float
    remaining_hours: float
    remaining_days: float
    risk_level: str
    status: str
    cth: float
    cdot_seconds: int
    produce_type: str
    kp: float
    thermal_penalty: float
    door_penalty: float
    asset_id: str
    setpoint: float
    hours_analyzed: int
    computed_at: str
    current_temperature: Optional[float] = None
    current_humidity: Optional[float] = None
    last_reading_at: Optional[str] = None
    confidence: int
    confidence_reason: str


class BatchRSLRequest(BaseModel):
    assets: List[RSLRequest]


class DigitalTwinForecastRequest(BaseModel):
    current_temp: float
    external_temp: float = 25.0
    compressor_on: bool = True
    setpoint: float = 4.0
    hours_ahead: int = 6


class ForecastPoint(BaseModel):
    hours_ahead: int
    forecast_temperature: float
    confidence: int
    risk_factors: List[str]


class SpoilageRiskRequest(BaseModel):
    rsl_index: float
    temperature_variance: float
    cdot_ratio: float
    days_in_storage: int
    produce_type: str


class SpoilageRiskResponse(BaseModel):
    risk_score: int
    risk_level: str
    factors: List[str]
    recommendations: List[str]
    assessed_at: str


class SpoilageTelemetryRequest(BaseModel):
    asset_id: str
    produce_type: str
    days_in_storage: int = 1
    setpoint: float = 4.0
    hours_to_analyze: int = 24
    base_shelf_life_hours: float = 168.0


class SpoilageTelemetryResponse(BaseModel):
    asset_id: str
    produce_type: str
    risk_score: int
    risk_level: str
    factors: List[str]
    recommendations: List[str]
    assessed_at: str
    rsl_index: float
    remaining_hours: float
    cth: float
    cdot_seconds: int
    cdot_ratio: float
    temperature_variance: float
    confidence: int
    confidence_reason: str


class TelemetryHistoryRequest(BaseModel):
    asset_id: str
    hours: int = 24
    interval_minutes: int = 5


class TelemetryPoint(BaseModel):
    timestamp: Optional[str]
    temperature: Optional[float]
    humidity: Optional[float]


class ThermalComplianceRequest(BaseModel):
    asset_id: str
    min_temp: float = 2.0
    max_temp: float = 8.0
    hours: int = 24


class ThermalComplianceResponse(BaseModel):
    compliance_percent: float
    total_readings: int
    compliant_readings: int
    min_temp: float
    max_temp: float
    hours: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/rsl", response_model=RSLResponse)
async def compute_rsl(
    request: RSLRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Compute Remaining Shelf Life (RSL) for an asset.
    
    Uses real-time telemetry data from InfluxDB to calculate:
    - CTH (Cumulative Thermal History)
    - CDOT (Cumulative Door Open Time)
    - RSL Index (0-100 scale)
    
    Returns risk classification and recommendations.
    """
    result = await prediction_service.compute_rsl_for_asset(
        asset_id=request.asset_id,
        produce_type=request.produce_type,
        setpoint=request.setpoint,
        hours_to_analyze=request.hours_to_analyze,
        base_shelf_life_hours=request.base_shelf_life_hours,
    )
    return RSLResponse(**result)


@router.post("/rsl/batch", response_model=List[RSLResponse])
async def compute_batch_rsl(
    request: BatchRSLRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Compute RSL for multiple assets in parallel.
    
    Optimized for dashboard displays that need to show
    RSL for all assets in a facility.
    """
    assets = [a.model_dump() for a in request.assets]
    results = await prediction_service.compute_batch_rsl(assets)
    return [RSLResponse(**r) for r in results]


@router.post("/forecast", response_model=List[ForecastPoint])
async def digital_twin_forecast(
    request: DigitalTwinForecastRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Forecast temperature evolution using digital twin model.
    
    Simulates thermal dynamics to predict future temperatures
    based on current state and operating conditions.
    """
    forecast = prediction_service.digital_twin_forecast(
        current_temp=request.current_temp,
        external_temp=request.external_temp,
        compressor_on=request.compressor_on,
        setpoint=request.setpoint,
        hours_ahead=request.hours_ahead,
    )
    return [ForecastPoint(**f) for f in forecast]


@router.post("/spoilage-risk", response_model=SpoilageRiskResponse)
async def assess_spoilage_risk(
    request: SpoilageRiskRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Comprehensive spoilage risk assessment.
    
    Combines RSL, temperature variance, door activity,
    and storage duration to assess overall risk.
    """
    result = prediction_service.assess_spoilage_risk(
        rsl_index=request.rsl_index,
        temperature_variance=request.temperature_variance,
        cdot_ratio=request.cdot_ratio,
        days_in_storage=request.days_in_storage,
        produce_type=request.produce_type,
    )
    return SpoilageRiskResponse(**result)


@router.post("/spoilage", response_model=SpoilageTelemetryResponse)
async def assess_spoilage_from_telemetry(
    request: SpoilageTelemetryRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Compute spoilage risk directly from live telemetry for an asset.

    This endpoint is server-authoritative and derives supporting metrics
    from InfluxDB via prediction_service and influxdb_service:
      - RSL index (from CTH + CDOT)
      - temperature variance (history window)
      - CDOT ratio (CDOT / CDOTmax)
      - confidence & confidence_reason
    """
    rsl_result = await prediction_service.compute_rsl_for_asset(
        asset_id=request.asset_id,
        produce_type=request.produce_type,
        setpoint=request.setpoint,
        hours_to_analyze=request.hours_to_analyze,
        base_shelf_life_hours=request.base_shelf_life_hours,
    )

    history = await influxdb_service.get_temperature_history(
        asset_id=request.asset_id,
        hours=request.hours_to_analyze,
        interval_minutes=5,
    )
    temps = [p.get("temperature") for p in history if p.get("temperature") is not None]
    if temps:
        mean_temp = sum(temps) / len(temps)
        variance = sum((t - mean_temp) ** 2 for t in temps) / len(temps)
        temp_variance = variance ** 0.5
    else:
        temp_variance = 0.0

    cdot_seconds = int(rsl_result.get("cdot_seconds", 0))
    cdot_max = prediction_service.get_cdot_max(request.produce_type)
    cdot_ratio = (cdot_seconds / cdot_max) if cdot_max > 0 else 0.0

    spoilage = prediction_service.assess_spoilage_risk(
        rsl_index=float(rsl_result.get("rsl_index", 0.0)),
        temperature_variance=temp_variance,
        cdot_ratio=cdot_ratio,
        days_in_storage=request.days_in_storage,
        produce_type=request.produce_type,
    )

    return SpoilageTelemetryResponse(
        asset_id=request.asset_id,
        produce_type=request.produce_type,
        risk_score=spoilage["risk_score"],
        risk_level=spoilage["risk_level"],
        factors=spoilage["factors"],
        recommendations=spoilage["recommendations"],
        assessed_at=spoilage["assessed_at"],
        rsl_index=float(rsl_result.get("rsl_index", 0.0)),
        remaining_hours=float(rsl_result.get("remaining_hours", 0.0)),
        cth=float(rsl_result.get("cth", 0.0)),
        cdot_seconds=cdot_seconds,
        cdot_ratio=float(cdot_ratio),
        temperature_variance=float(temp_variance),
        confidence=int(rsl_result.get("confidence", 0)),
        confidence_reason=str(rsl_result.get("confidence_reason", "")),
    )


@router.post("/telemetry/history", response_model=List[TelemetryPoint])
async def get_telemetry_history(
    request: TelemetryHistoryRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Get historical telemetry data for an asset.
    
    Returns temperature and humidity readings aggregated
    by the specified interval.
    """
    history = await influxdb_service.get_temperature_history(
        asset_id=request.asset_id,
        hours=request.hours,
        interval_minutes=request.interval_minutes,
    )
    return [TelemetryPoint(**h) for h in history]


@router.post("/telemetry/compliance", response_model=ThermalComplianceResponse)
async def get_thermal_compliance(
    request: ThermalComplianceRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """
    Calculate thermal compliance percentage for an asset.
    
    Returns the percentage of time the temperature stayed
    within the specified range.
    """
    result = await influxdb_service.get_thermal_compliance(
        asset_id=request.asset_id,
        min_temp=request.min_temp,
        max_temp=request.max_temp,
        hours=request.hours,
    )
    return ThermalComplianceResponse(**result)


@router.get("/produce-types")
async def list_produce_types():
    """
    List all supported produce types with their coefficients.
    
    Returns thermal sensitivity (kp) and maximum door-open
    tolerance (CDOTmax) for each produce type.
    """
    produce_list = []
    for produce_type, kp in prediction_service.PRODUCE_COEFFICIENTS.items():
        cdot_max = prediction_service.CDOT_MAX.get(produce_type, 600)
        
        # Classify sensitivity
        if kp > 1.0:
            sensitivity = "HIGH"
        elif kp >= 0.7:
            sensitivity = "MEDIUM"
        else:
            sensitivity = "LOW"
        
        produce_list.append({
            "produce_type": produce_type,
            "display_name": produce_type.replace("_", " ").title(),
            "kp": kp,
            "cdot_max_seconds": cdot_max,
            "sensitivity": sensitivity,
        })
    
    # Sort by kp (most sensitive first)
    produce_list.sort(key=lambda x: -x["kp"])
    
    return {"produce_types": produce_list}
