"""
InfluxDB telemetry service for time-series data persistence.

This service handles:
- Writing sensor telemetry to InfluxDB
- Querying historical telemetry data
- Computing CTH (Cumulative Thermal History) and CDOT (Cumulative Door Open Time)
- Downsampling for analytics
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Lazy import of influxdb_client to handle missing dependency
_influx_client = None
_write_api = None
_query_api = None


def _get_influx_client():
    """Lazily initialize InfluxDB client."""
    global _influx_client, _write_api, _query_api
    
    if _influx_client is not None:
        return _influx_client, _write_api, _query_api
    
    settings = get_settings()
    if not settings.influxdb_configured:
        logger.warning("InfluxDB not configured - telemetry persistence disabled")
        return None, None, None
    
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS
        
        _influx_client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
        )
        _write_api = _influx_client.write_api(write_options=SYNCHRONOUS)
        _query_api = _influx_client.query_api()
        
        logger.info(f"InfluxDB client initialized: {settings.influxdb_url}")
        return _influx_client, _write_api, _query_api
    except ImportError:
        logger.error("influxdb-client package not installed")
        return None, None, None
    except Exception as e:
        logger.error(f"Failed to initialize InfluxDB client: {e}")
        return None, None, None


async def write_telemetry_point(
    device_id: str,
    asset_id: str,
    asset_type: str,
    temperature: Optional[float] = None,
    humidity: Optional[float] = None,
    door_open: Optional[bool] = None,
    battery_level: Optional[float] = None,
    signal_strength: Optional[int] = None,
    timestamp: Optional[datetime] = None,
    tenant_id: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Write a single telemetry point to InfluxDB.
    
    Args:
        device_id: The sensor device ID
        asset_id: The cold storage unit or truck ID
        asset_type: 'cold_storage_unit' or 'reefer_truck'
        temperature: Temperature in Celsius
        humidity: Relative humidity percentage
        door_open: Door state (True=open, False=closed)
        battery_level: Battery percentage
        signal_strength: RSSI or signal strength
        timestamp: Optional timestamp (defaults to now)
        tenant_id: Tenant/organization ID for multi-tenancy
        extra_fields: Additional custom fields
    
    Returns:
        True if write succeeded, False otherwise
    """
    _, write_api, _ = _get_influx_client()
    if write_api is None:
        return False
    
    try:
        from influxdb_client import Point
        
        settings = get_settings()
        ts = timestamp or datetime.utcnow()
        
        point = (
            Point("sensor_reading")
            .tag("device_id", device_id)
            .tag("asset_id", asset_id)
            .tag("asset_type", asset_type)
        )
        
        if tenant_id:
            point = point.tag("tenant_id", tenant_id)
        
        if temperature is not None:
            point = point.field("temperature", float(temperature))
        if humidity is not None:
            point = point.field("humidity", float(humidity))
        if door_open is not None:
            point = point.field("door_open", door_open)
        if battery_level is not None:
            point = point.field("battery_level", float(battery_level))
        if signal_strength is not None:
            point = point.field("signal_strength", int(signal_strength))
        
        # Add extra fields
        if extra_fields:
            for key, value in extra_fields.items():
                if isinstance(value, (int, float)):
                    point = point.field(key, value)
                elif isinstance(value, bool):
                    point = point.field(key, value)
                elif isinstance(value, str):
                    point = point.field(key, value)
        
        point = point.time(ts)
        
        write_api.write(bucket=settings.influxdb_bucket_raw, record=point)
        logger.debug(f"Wrote telemetry for device {device_id} to InfluxDB")
        return True
        
    except Exception as e:
        logger.error(f"Failed to write telemetry to InfluxDB: {e}")
        return False


async def write_telemetry_batch(
    points: List[Dict[str, Any]],
) -> Tuple[int, int]:
    """
    Write multiple telemetry points in a batch.
    
    Args:
        points: List of dicts with telemetry data
    
    Returns:
        Tuple of (success_count, failure_count)
    """
    success = 0
    failures = 0
    
    for point_data in points:
        result = await write_telemetry_point(
            device_id=point_data.get("device_id", "unknown"),
            asset_id=point_data.get("asset_id", "unknown"),
            asset_type=point_data.get("asset_type", "cold_storage_unit"),
            temperature=point_data.get("temperature"),
            humidity=point_data.get("humidity"),
            door_open=point_data.get("door_open"),
            battery_level=point_data.get("battery_level"),
            signal_strength=point_data.get("signal_strength"),
            timestamp=point_data.get("timestamp"),
            tenant_id=point_data.get("tenant_id"),
            extra_fields=point_data.get("extra_fields"),
        )
        if result:
            success += 1
        else:
            failures += 1
    
    return success, failures


async def get_latest_reading(
    asset_id: str,
    fields: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get the most recent telemetry reading for an asset.
    
    Args:
        asset_id: The cold storage unit or truck ID
        fields: Optional list of fields to retrieve (defaults to all)
    
    Returns:
        Dict with latest readings or None
    """
    _, _, query_api = _get_influx_client()
    if query_api is None:
        return None
    
    try:
        settings = get_settings()
        field_filter = ""
        if fields:
            field_conditions = " or ".join([f'r._field == "{f}"' for f in fields])
            field_filter = f"|> filter(fn: (r) => {field_conditions})"
        
        query = f'''
        from(bucket: "{settings.influxdb_bucket_raw}")
            |> range(start: -1h)
            |> filter(fn: (r) => r.asset_id == "{asset_id}")
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            {field_filter}
            |> last()
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        tables = query_api.query(query)
        
        for table in tables:
            for record in table.records:
                return {
                    "timestamp": record.get_time().isoformat() if record.get_time() else None,
                    "temperature": record.values.get("temperature"),
                    "humidity": record.values.get("humidity"),
                    "door_open": record.values.get("door_open"),
                    "battery_level": record.values.get("battery_level"),
                    "device_id": record.values.get("device_id"),
                    "asset_id": record.values.get("asset_id"),
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to query latest reading: {e}")
        return None


async def get_temperature_history(
    asset_id: str,
    hours: int = 24,
    interval_minutes: int = 5,
) -> List[Dict[str, Any]]:
    """
    Get temperature history for an asset.
    
    Args:
        asset_id: The cold storage unit or truck ID
        hours: Number of hours of history
        interval_minutes: Aggregation window in minutes
    
    Returns:
        List of {timestamp, temperature, humidity} dicts
    """
    _, _, query_api = _get_influx_client()
    if query_api is None:
        return []
    
    try:
        settings = get_settings()
        query = f'''
        from(bucket: "{settings.influxdb_bucket_raw}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r.asset_id == "{asset_id}")
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity")
            |> aggregateWindow(every: {interval_minutes}m, fn: mean, createEmpty: false)
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"])
        '''
        
        tables = query_api.query(query)
        results = []
        
        for table in tables:
            for record in table.records:
                results.append({
                    "timestamp": record.get_time().isoformat() if record.get_time() else None,
                    "temperature": record.values.get("temperature"),
                    "humidity": record.values.get("humidity"),
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to query temperature history: {e}")
        return []


async def compute_cth(
    asset_id: str,
    setpoint: float = 4.0,
    hours: int = 24,
) -> float:
    """
    Compute Cumulative Thermal History (CTH) as degree-hours above setpoint.
    
    CTH = ∫(T - setpoint)dt where T > setpoint
    
    Args:
        asset_id: The cold storage unit or truck ID
        setpoint: Target temperature in Celsius (default 4°C)
        hours: Time window in hours
    
    Returns:
        CTH in degree-hours
    """
    _, _, query_api = _get_influx_client()
    if query_api is None:
        return 0.0
    
    try:
        settings = get_settings()
        # Query to compute CTH using Flux
        query = f'''
        data = from(bucket: "{settings.influxdb_bucket_raw}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r.asset_id == "{asset_id}")
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            |> filter(fn: (r) => r._field == "temperature")
            |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
        
        data
            |> map(fn: (r) => ({{
                r with
                _value: if r._value > {setpoint} then r._value - {setpoint} else 0.0
            }}))
            |> sum()
            |> map(fn: (r) => ({{r with _value: r._value / 60.0}}))
        '''
        
        tables = query_api.query(query)
        
        for table in tables:
            for record in table.records:
                return float(record.get_value() or 0.0)
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Failed to compute CTH: {e}")
        return 0.0


async def compute_cdot(
    asset_id: str,
    window_minutes: int = 360,
) -> int:
    """
    Compute Cumulative Door Open Time (CDOT) in seconds.
    
    Args:
        asset_id: The cold storage unit or truck ID
        window_minutes: Time window in minutes (default 6 hours)
    
    Returns:
        CDOT in seconds
    """
    _, _, query_api = _get_influx_client()
    if query_api is None:
        return 0
    
    try:
        settings = get_settings()
        # Query to compute door open duration
        query = f'''
        from(bucket: "{settings.influxdb_bucket_raw}")
            |> range(start: -{window_minutes}m)
            |> filter(fn: (r) => r.asset_id == "{asset_id}")
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            |> filter(fn: (r) => r._field == "door_open")
            |> filter(fn: (r) => r._value == true)
            |> elapsed(unit: 1s)
            |> sum(column: "elapsed")
        '''
        
        tables = query_api.query(query)
        
        for table in tables:
            for record in table.records:
                return int(record.get_value() or 0)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to compute CDOT: {e}")
        return 0


async def get_thermal_compliance(
    asset_id: str,
    min_temp: float = 2.0,
    max_temp: float = 8.0,
    hours: int = 24,
) -> Dict[str, Any]:
    """
    Calculate thermal compliance percentage for an asset.
    
    Args:
        asset_id: The cold storage unit or truck ID
        min_temp: Minimum acceptable temperature
        max_temp: Maximum acceptable temperature
        hours: Time window in hours
    
    Returns:
        Dict with compliance metrics
    """
    _, _, query_api = _get_influx_client()
    if query_api is None:
        return {"compliance_percent": 0, "total_readings": 0, "compliant_readings": 0}
    
    try:
        settings = get_settings()
        
        # Total readings count
        total_query = f'''
        from(bucket: "{settings.influxdb_bucket_raw}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r.asset_id == "{asset_id}")
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            |> filter(fn: (r) => r._field == "temperature")
            |> count()
        '''
        
        # Compliant readings count
        compliant_query = f'''
        from(bucket: "{settings.influxdb_bucket_raw}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r.asset_id == "{asset_id}")
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            |> filter(fn: (r) => r._field == "temperature")
            |> filter(fn: (r) => r._value >= {min_temp} and r._value <= {max_temp})
            |> count()
        '''
        
        total = 0
        compliant = 0
        
        for table in query_api.query(total_query):
            for record in table.records:
                total = int(record.get_value() or 0)
        
        for table in query_api.query(compliant_query):
            for record in table.records:
                compliant = int(record.get_value() or 0)
        
        compliance_pct = (compliant / total * 100) if total > 0 else 100.0
        
        return {
            "compliance_percent": round(compliance_pct, 2),
            "total_readings": total,
            "compliant_readings": compliant,
            "min_temp": min_temp,
            "max_temp": max_temp,
            "hours": hours,
        }
        
    except Exception as e:
        logger.error(f"Failed to compute thermal compliance: {e}")
        return {"compliance_percent": 0, "total_readings": 0, "compliant_readings": 0}


async def close_client():
    """Close the InfluxDB client connection."""
    global _influx_client, _write_api, _query_api
    
    if _influx_client is not None:
        _influx_client.close()
        _influx_client = None
        _write_api = None
        _query_api = None
        logger.info("InfluxDB client closed")
