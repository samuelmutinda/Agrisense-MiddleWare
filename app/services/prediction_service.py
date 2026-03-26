"""
RSL (Remaining Shelf Life) prediction service.

Implements the AgriSense ML model for shelf life calculation based on:
- Cumulative Thermal History (CTH)
- Cumulative Door Open Time (CDOT)
- Produce type thermal sensitivity

Reference: AgriSense Next Steps 19-3-26 Technical Document
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services import influxdb_service

logger = logging.getLogger(__name__)

# =============================================================================
# PRODUCE THERMAL SENSITIVITY COEFFICIENTS
# =============================================================================

# kp values: produce-specific thermal sensitivity coefficients
# Higher kp = more sensitive to temperature excursions
PRODUCE_COEFFICIENTS: Dict[str, float] = {
    # High sensitivity (kp > 1.0)
    "strawberry": 1.5,
    "raspberry": 1.4,
    "lettuce": 1.3,
    "spinach": 1.3,
    "fresh_herbs": 1.3,
    "milk": 1.2,
    "yogurt": 1.2,
    "fresh_fish": 1.5,
    "seafood": 1.4,
    "roses": 1.1,
    
    # Medium sensitivity (kp 0.7-1.0)
    "mango": 0.9,
    "avocado": 0.85,
    "tomato": 0.8,
    "banana": 0.75,
    "papaya": 0.8,
    "pineapple": 0.75,
    "grapes": 0.85,
    "orange": 0.7,
    "lemon": 0.65,
    "chicken": 0.9,
    "beef": 0.85,
    "pork": 0.85,
    
    # Low sensitivity (kp < 0.7)
    "apple": 0.5,
    "potato": 0.4,
    "onion": 0.35,
    "carrot": 0.5,
    "cabbage": 0.55,
    "squash": 0.45,
    "pumpkin": 0.4,
}

# CDOTmax values: maximum tolerable door-open seconds per 6 hours
CDOT_MAX: Dict[str, int] = {
    "strawberry": 180,
    "raspberry": 180,
    "lettuce": 240,
    "spinach": 240,
    "fresh_herbs": 200,
    "milk": 300,
    "yogurt": 300,
    "fresh_fish": 120,
    "seafood": 150,
    "roses": 360,
    "mango": 420,
    "avocado": 480,
    "tomato": 600,
    "banana": 900,
    "papaya": 480,
    "pineapple": 600,
    "grapes": 360,
    "orange": 900,
    "lemon": 1200,
    "chicken": 240,
    "beef": 300,
    "pork": 300,
    "apple": 1800,
    "potato": 3600,
    "onion": 7200,
    "carrot": 1800,
    "cabbage": 1200,
    "squash": 2400,
    "pumpkin": 3600,
}

# Default values for unknown produce types
DEFAULT_KP = 0.8
DEFAULT_CDOT_MAX = 600

# Canonical aliases aligned with Agrisense-Project-default/physics_engine.py
PRODUCE_ALIASES: Dict[str, str] = {
    "leafy_greens": "lettuce",
    "leafy greens": "lettuce",
    "berries": "strawberry",
    "berry": "strawberry",
    "blueberries": "strawberry",
    "strawberries": "strawberry",
    "oranges": "orange",
    "avocados": "avocado",
    "mangoes": "mango",
}

# Explicitly include taxonomy keys used by frontend and ML module
PRODUCE_COEFFICIENTS.update({
    "leafy_greens": 1.3,
    "berries": 1.5,
})
CDOT_MAX.update({
    "leafy_greens": 240,
    "berries": 180,
})


def _normalize_produce(produce_type: str) -> str:
    normalized = produce_type.lower().replace(" ", "_").replace("-", "_")
    return PRODUCE_ALIASES.get(normalized, normalized)


def get_produce_coefficient(produce_type: str) -> float:
    """Get thermal sensitivity coefficient for produce type."""
    return PRODUCE_COEFFICIENTS.get(_normalize_produce(produce_type), DEFAULT_KP)


def get_cdot_max(produce_type: str) -> int:
    """Get maximum tolerable CDOT for produce type."""
    return CDOT_MAX.get(_normalize_produce(produce_type), DEFAULT_CDOT_MAX)


# =============================================================================
# RSL CALCULATION
# =============================================================================

def compute_rsl(
    cth: float,
    cdot_seconds: int,
    produce_type: str,
    base_shelf_life_hours: float = 168.0,  # 7 days default
) -> Dict[str, Any]:
    """
    Compute Remaining Shelf Life (RSL) index.
    
    Formula:
        RSL_index = 100 - (kp * sqrt(CTH) + 10 * (CDOT / CDOTmax))
    
    Args:
        cth: Cumulative Thermal History in degree-hours
        cdot_seconds: Cumulative Door Open Time in seconds
        produce_type: Type of produce
        base_shelf_life_hours: Expected shelf life under ideal conditions
    
    Returns:
        Dict with RSL metrics
    """
    import math
    
    kp = get_produce_coefficient(produce_type)
    cdot_max = get_cdot_max(produce_type)
    
    # Compute RSL index
    thermal_penalty = kp * math.sqrt(max(0, cth))
    door_penalty = 10 * (cdot_seconds / cdot_max) if cdot_max > 0 else 0
    
    rsl_index = 100 - thermal_penalty - door_penalty
    rsl_index = max(0, min(100, rsl_index))  # Clamp to 0-100
    
    # Estimate remaining hours
    remaining_percent = rsl_index / 100
    remaining_hours = base_shelf_life_hours * remaining_percent
    
    # Risk classification
    if rsl_index >= 80:
        risk_level = "LOW"
        status = "FRESH"
    elif rsl_index >= 50:
        risk_level = "MEDIUM"
        status = "GOOD"
    elif rsl_index >= 20:
        risk_level = "HIGH"
        status = "WARNING"
    else:
        risk_level = "CRITICAL"
        status = "CRITICAL"
    
    return {
        "rsl_index": round(rsl_index, 2),
        "remaining_hours": round(remaining_hours, 1),
        "remaining_days": round(remaining_hours / 24, 2),
        "risk_level": risk_level,
        "status": status,
        "cth": round(cth, 2),
        "cdot_seconds": cdot_seconds,
        "produce_type": produce_type,
        "kp": kp,
        "thermal_penalty": round(thermal_penalty, 2),
        "door_penalty": round(door_penalty, 2),
    }


async def compute_rsl_for_asset(
    asset_id: str,
    produce_type: str,
    setpoint: float = 4.0,
    hours_to_analyze: int = 24,
    base_shelf_life_hours: float = 168.0,
) -> Dict[str, Any]:
    """
    Compute RSL for an asset using live telemetry from InfluxDB.
    
    Args:
        asset_id: Cold storage unit or truck ID
        produce_type: Type of produce
        setpoint: Target temperature in Celsius
        hours_to_analyze: Hours of history to analyze
        base_shelf_life_hours: Expected shelf life under ideal conditions
    
    Returns:
        Dict with RSL metrics and confidence
    """
    # Get CTH from InfluxDB
    cth = await influxdb_service.compute_cth(
        asset_id=asset_id,
        setpoint=setpoint,
        hours=hours_to_analyze,
    )
    
    # Get CDOT from InfluxDB (6-hour window)
    cdot = await influxdb_service.compute_cdot(
        asset_id=asset_id,
        window_minutes=360,
    )
    
    # Get latest reading for context
    latest = await influxdb_service.get_latest_reading(asset_id)
    
    # Compute RSL
    result = compute_rsl(
        cth=cth,
        cdot_seconds=cdot,
        produce_type=produce_type,
        base_shelf_life_hours=base_shelf_life_hours,
    )
    
    # Add context
    result["asset_id"] = asset_id
    result["setpoint"] = setpoint
    result["hours_analyzed"] = hours_to_analyze
    result["computed_at"] = datetime.utcnow().isoformat()
    
    if latest:
        result["current_temperature"] = latest.get("temperature")
        result["current_humidity"] = latest.get("humidity")
        result["last_reading_at"] = latest.get("timestamp")
    
    # Confidence based on data availability
    if cth == 0 and cdot == 0:
        result["confidence"] = 0
        result["confidence_reason"] = "No telemetry data available"
    elif cth == 0:
        result["confidence"] = 50
        result["confidence_reason"] = "No temperature deviation detected"
    else:
        result["confidence"] = 100
        result["confidence_reason"] = "Full telemetry data available"
    
    return result


# =============================================================================
# BATCH PREDICTIONS
# =============================================================================

async def compute_batch_rsl(
    assets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Compute RSL for multiple assets.
    
    Args:
        assets: List of {asset_id, produce_type, setpoint?, base_shelf_life_hours?}
    
    Returns:
        List of RSL results
    """
    import asyncio
    
    async def compute_single(asset: Dict[str, Any]) -> Dict[str, Any]:
        return await compute_rsl_for_asset(
            asset_id=asset["asset_id"],
            produce_type=asset["produce_type"],
            setpoint=asset.get("setpoint", 4.0),
            hours_to_analyze=asset.get("hours_to_analyze", 24),
            base_shelf_life_hours=asset.get("base_shelf_life_hours", 168.0),
        )
    
    return await asyncio.gather(*[compute_single(a) for a in assets])


# =============================================================================
# DIGITAL TWIN FORECAST
# =============================================================================

def digital_twin_forecast(
    current_temp: float,
    external_temp: float,
    compressor_on: bool,
    setpoint: float = 4.0,
    hours_ahead: int = 6,
) -> List[Dict[str, Any]]:
    """
    Forecast temperature evolution using simplified thermal model.
    
    Uses basic thermal dynamics:
    - dT/dt = (T_ext - T) / tau - cooling_rate * compressor_on
    
    Args:
        current_temp: Current internal temperature
        external_temp: External/ambient temperature
        compressor_on: Whether compressor is running
        setpoint: Target temperature
        hours_ahead: Forecast horizon
    
    Returns:
        List of hourly forecasts
    """
    TAU = 8.0  # Thermal time constant (hours)
    COOLING_RATE = 2.0  # °C/hour when compressor on
    
    forecast = []
    temp = current_temp
    
    for hour in range(1, hours_ahead + 1):
        # Simple Euler integration
        dt = 1.0  # 1 hour step
        
        # Natural heat gain from environment
        heat_gain = (external_temp - temp) / TAU * dt
        
        # Cooling from compressor
        cooling = COOLING_RATE * dt if compressor_on else 0
        
        # Net temperature change
        temp = temp + heat_gain - cooling
        
        # Confidence decreases over time
        confidence = max(50, 100 - (hour * 5))
        
        risk_factors = []
        if temp > setpoint + 2:
            risk_factors.append("Temperature above safe range")
        if temp > setpoint + 5:
            risk_factors.append("Critical temperature excursion")
        
        forecast.append({
            "hours_ahead": hour,
            "forecast_temperature": round(temp, 2),
            "confidence": confidence,
            "risk_factors": risk_factors,
        })
    
    return forecast


# =============================================================================
# SPOILAGE RISK ASSESSMENT
# =============================================================================

def assess_spoilage_risk(
    rsl_index: float,
    temperature_variance: float,
    cdot_ratio: float,  # CDOT / CDOTmax
    days_in_storage: int,
    produce_type: str,
) -> Dict[str, Any]:
    """
    Comprehensive spoilage risk assessment.
    
    Returns:
        Dict with risk score and recommendations
    """
    risk_score = 0
    factors = []
    recommendations = []
    
    # RSL contribution
    if rsl_index < 20:
        risk_score += 40
        factors.append(f"Critical RSL ({rsl_index:.1f}%)")
        recommendations.append("Dispatch immediately or dispose")
    elif rsl_index < 50:
        risk_score += 25
        factors.append(f"Low RSL ({rsl_index:.1f}%)")
        recommendations.append("Prioritize for immediate dispatch")
    elif rsl_index < 80:
        risk_score += 10
        factors.append(f"Moderate RSL ({rsl_index:.1f}%)")
    
    # Temperature variance contribution
    if temperature_variance > 3:
        risk_score += 20
        factors.append(f"High temp variance ({temperature_variance:.1f}°C)")
        recommendations.append("Check refrigeration system")
    elif temperature_variance > 1.5:
        risk_score += 10
        factors.append(f"Moderate temp variance ({temperature_variance:.1f}°C)")
    
    # Door open ratio contribution
    if cdot_ratio > 1.0:
        risk_score += 20
        factors.append(f"Excessive door openings ({cdot_ratio:.0%})")
        recommendations.append("Review access protocols")
    elif cdot_ratio > 0.5:
        risk_score += 10
        factors.append(f"Elevated door openings ({cdot_ratio:.0%})")
    
    # Days in storage
    kp = get_produce_coefficient(produce_type)
    max_days = int(7 / kp)  # Rough estimate
    if days_in_storage > max_days:
        risk_score += 20
        factors.append(f"Extended storage ({days_in_storage} days)")
        recommendations.append("Quality inspection recommended")
    
    # Classify risk
    if risk_score >= 60:
        risk_level = "CRITICAL"
    elif risk_score >= 40:
        risk_level = "HIGH"
    elif risk_score >= 20:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    if not recommendations:
        recommendations.append("Continue normal monitoring")
    
    return {
        "risk_score": min(100, risk_score),
        "risk_level": risk_level,
        "factors": factors,
        "recommendations": recommendations,
        "assessed_at": datetime.utcnow().isoformat(),
    }
