"""
Digital Twin InfluxDB query service.

Queries the `digital_twin` bucket (measurement: `cold_chain`) populated by
the ingest.py script from Agrisense-Project-default's physics-driven CSV.

This service exposes pre-built Flux queries that the digital-twin API routes
call.  All functions follow the same lazy-client pattern as influxdb_service.py.

Schema (mirrors ingest.py):
  Tags  : crop_type, quality_status, temp_profile, humidity_profile,
           initial_condition, scenario_id, compressor_on, door_open,
           is_good, is_spoiled
  Fields: temperature, humidity, co2_ppm, light_lux, ethylene_ppm,
          quality_index, rsl_hours, rsl_percent, mold_risk_score,
          decay_temperature, decay_humidity, decay_co2, decay_microbial,
          decay_infrastructure, flu_total, water_loss_percent,
          microbial_load, energy_consumed_kwh, compressor_power_kw,
          door_cycles_today, door_cycles_cumulative, hour …
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_query_api():
    """Return the shared InfluxDB query API (lazy-init via influxdb_service)."""
    from app.services.influxdb_service import _get_influx_client
    _, _, query_api = _get_influx_client()
    return query_api


# ─── Tag catalogue ────────────────────────────────────────────────────────────

VALID_CROP_TYPES = {"avocado", "mango", "orange", "leafy_greens", "berries",
                    "tomato", "banana", "papaya", "pineapple", "grapes"}

VALID_QUALITY_STATUSES = {"GOOD", "MARGINAL", "POOR", "SPOILED"}


# ─── Query helpers ────────────────────────────────────────────────────────────

async def get_crop_summary(
    crop_type: Optional[str] = None,
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """
    Mean temperature, humidity, quality_index, rsl_percent per crop_type.

    When *crop_type* is supplied, filters to that single crop.
    """
    query_api = _get_query_api()
    if query_api is None:
        return []

    settings = get_settings()
    bucket = settings.influxdb_bucket_digital_twin

    crop_filter = ""
    if crop_type:
        crop_filter = f'|> filter(fn: (r) => r.crop_type == "{crop_type}")'

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "cold_chain")
      |> filter(fn: (r) =>
           r._field == "temperature" or
           r._field == "humidity" or
           r._field == "quality_index" or
           r._field == "rsl_percent"
         )
      {crop_filter}
      |> group(columns: ["crop_type", "_field"])
      |> mean()
      |> pivot(rowKey: ["crop_type"], columnKey: ["_field"], valueColumn: "_value")
    '''

    try:
        tables = query_api.query(query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "crop_type": record.values.get("crop_type"),
                    "temperature": record.values.get("temperature"),
                    "humidity": record.values.get("humidity"),
                    "quality_index": record.values.get("quality_index"),
                    "rsl_percent": record.values.get("rsl_percent"),
                })
        return results
    except Exception as e:
        logger.error(f"digital_twin get_crop_summary failed: {e}")
        return []


async def get_spoilage_counts(
    hours: int = 720,
) -> List[Dict[str, Any]]:
    """Count spoiled readings per crop_type (is_spoiled == "true")."""
    query_api = _get_query_api()
    if query_api is None:
        return []

    settings = get_settings()
    bucket = settings.influxdb_bucket_digital_twin

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "cold_chain" and r.is_spoiled == "true")
      |> filter(fn: (r) => r._field == "temperature")
      |> group(columns: ["crop_type"])
      |> count()
    '''

    try:
        tables = query_api.query(query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "crop_type": record.values.get("crop_type"),
                    "spoiled_count": int(record.get_value() or 0),
                })
        return results
    except Exception as e:
        logger.error(f"digital_twin get_spoilage_counts failed: {e}")
        return []


async def get_mold_risk_events(
    threshold: float = 0.7,
    hours: int = 168,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return recent high-mold-risk data points above *threshold*."""
    query_api = _get_query_api()
    if query_api is None:
        return []

    settings = get_settings()
    bucket = settings.influxdb_bucket_digital_twin

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "cold_chain")
      |> filter(fn: (r) => r._field == "mold_risk_score")
      |> filter(fn: (r) => r._value > {threshold})
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit})
    '''

    try:
        tables = query_api.query(query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "timestamp": record.get_time().isoformat() if record.get_time() else None,
                    "crop_type": record.values.get("crop_type"),
                    "mold_risk_score": record.get_value(),
                    "scenario_id": record.values.get("scenario_id"),
                    "quality_status": record.values.get("quality_status"),
                })
        return results
    except Exception as e:
        logger.error(f"digital_twin get_mold_risk_events failed: {e}")
        return []


async def get_sensor_history(
    crop_type: str,
    field_name: str = "temperature",
    hours: int = 24,
    interval_minutes: int = 5,
) -> List[Dict[str, Any]]:
    """
    Aggregated time-series for a specific sensor field, filtered by crop_type.
    Commonly used for temperature, humidity, co2_ppm, ethylene_ppm.
    """
    query_api = _get_query_api()
    if query_api is None:
        return []

    settings = get_settings()
    bucket = settings.influxdb_bucket_digital_twin

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "cold_chain")
      |> filter(fn: (r) => r.crop_type == "{crop_type}")
      |> filter(fn: (r) => r._field == "{field_name}")
      |> aggregateWindow(every: {interval_minutes}m, fn: mean, createEmpty: false)
      |> sort(columns: ["_time"])
    '''

    try:
        tables = query_api.query(query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "timestamp": record.get_time().isoformat() if record.get_time() else None,
                    "value": record.get_value(),
                })
        return results
    except Exception as e:
        logger.error(f"digital_twin get_sensor_history failed: {e}")
        return []


async def get_decay_breakdown(
    crop_type: str,
    hours: int = 24,
) -> Dict[str, Any]:
    """
    Mean value for each decay sub-model field for a given crop.
    Returns { crop_type, decay_temperature, decay_humidity, decay_co2,
              decay_microbial, decay_infrastructure, flu_total }.
    """
    query_api = _get_query_api()
    if query_api is None:
        return {}

    settings = get_settings()
    bucket = settings.influxdb_bucket_digital_twin

    decay_fields = [
        "decay_temperature", "decay_humidity", "decay_co2",
        "decay_microbial", "decay_infrastructure", "flu_total",
    ]
    field_filter = " or ".join([f'r._field == "{f}"' for f in decay_fields])

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "cold_chain")
      |> filter(fn: (r) => r.crop_type == "{crop_type}")
      |> filter(fn: (r) => {field_filter})
      |> group(columns: ["_field"])
      |> mean()
    '''

    try:
        tables = query_api.query(query)
        result: Dict[str, Any] = {"crop_type": crop_type}
        for table in tables:
            for record in table.records:
                result[record.values.get("_field", "unknown")] = round(record.get_value() or 0, 4)
        return result
    except Exception as e:
        logger.error(f"digital_twin get_decay_breakdown failed: {e}")
        return {}


async def get_energy_stats(
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """
    Mean energy_consumed_kwh and compressor_power_kw per crop_type.
    """
    query_api = _get_query_api()
    if query_api is None:
        return []

    settings = get_settings()
    bucket = settings.influxdb_bucket_digital_twin

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "cold_chain")
      |> filter(fn: (r) =>
           r._field == "energy_consumed_kwh" or
           r._field == "compressor_power_kw"
         )
      |> group(columns: ["crop_type", "_field"])
      |> mean()
      |> pivot(rowKey: ["crop_type"], columnKey: ["_field"], valueColumn: "_value")
    '''

    try:
        tables = query_api.query(query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "crop_type": record.values.get("crop_type"),
                    "energy_consumed_kwh": record.values.get("energy_consumed_kwh"),
                    "compressor_power_kw": record.values.get("compressor_power_kw"),
                })
        return results
    except Exception as e:
        logger.error(f"digital_twin get_energy_stats failed: {e}")
        return []


async def get_quality_distribution(
    crop_type: Optional[str] = None,
    hours: int = 168,
) -> List[Dict[str, Any]]:
    """
    Count of readings per quality_status (tag), optionally filtered by crop_type.
    Returns [{ quality_status, count }, …].
    """
    query_api = _get_query_api()
    if query_api is None:
        return []

    settings = get_settings()
    bucket = settings.influxdb_bucket_digital_twin

    crop_filter = ""
    if crop_type:
        crop_filter = f'|> filter(fn: (r) => r.crop_type == "{crop_type}")'

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "cold_chain")
      |> filter(fn: (r) => r._field == "quality_index")
      {crop_filter}
      |> group(columns: ["quality_status"])
      |> count()
    '''

    try:
        tables = query_api.query(query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "quality_status": record.values.get("quality_status"),
                    "count": int(record.get_value() or 0),
                })
        return results
    except Exception as e:
        logger.error(f"digital_twin get_quality_distribution failed: {e}")
        return []
